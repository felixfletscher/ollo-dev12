# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime, date

from dateutil.relativedelta import relativedelta
from odoo import fields, models, api
from odoo.addons.ollo_mollie_integration.utils.mollie import send_mollie_request
from odoo.addons.payment_mollie.const import SUPPORTED_LOCALES
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    mollie_subscription_line = fields.One2many('molliesubscriptions.subscription', 'order_id')
    abo_delivery_count = fields.Integer(compute="compute_abo_delivery", copy=False, default=0)
    is_abo_sale_order = fields.Boolean('Abo sale order', default=False, compute="compute_abo_order", store=True)
    cirf_result = fields.Selection([
        ('normal', 'Normal'),
        ('done', 'Success'),
        ('blocked', 'Fail')], string='CIRF result', default='normal')

    @api.depends('order_line')
    def compute_abo_order(self):
        """
            Check if the sale order contains a product from the ABO product line, and
            set the `is_abo_sale_order` field to True if it does.
        """
        for rec in self:
            abo_product_line = rec.order_line.filtered(
                lambda x: x.product_id.linked_product_line.filtered(lambda x: x.is_abo_product))
            if abo_product_line:
                rec.is_abo_sale_order = True

    def compute_abo_delivery(self):
        """
           Compute the number of deliveries made for this subscription sale.

           A delivery is counted if it is associated with this subscription sale and is marked as an 'abo_picking'.
           The count of such deliveries is stored in the 'abo_delivery_count' field of this record.
        """
        for rec in self:
            abo_delivery_count = self.env['stock.picking'].sudo().search_count(
                [('abo_sale_id', '=', self.id), ('is_abo_picking', '=', True)])
            rec.abo_delivery_count = abo_delivery_count

    # override base method for hide abo delivery
    def action_view_delivery(self):
        """
            open normal product delivery
        """
        return self._get_action_view_picking(self.picking_ids.filtered(lambda picking: not picking.is_abo_picking))

    def action_run_crif_check(self):
        pass

    # override base method for hide abo delivery count
    @api.depends('picking_ids')
    def _compute_picking_ids(self):
        """
            remove abo product delivery count from normal product delivery
        """
        for order in self:
            order.delivery_count = len(order.picking_ids.filtered(lambda picking: not picking.is_abo_picking))

    def update_subscription(self):
        """
           Update the interval of the active subscription associated with this subscription sale.

           The interval is set to '1 months'.
           If the subscription is not found or there is an error in the process, the method logs the error
           and continues.
        """
        try:
            subscription = self.mollie_subscription_line.filtered(lambda x: x.status == 'active')
            if subscription:
                mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
                url = f'https://api.mollie.com/v2/customers/{self.partner_id.mollie_contact_id}/subscriptions/{subscription[0].subscription_id}'
                if not mollie_key:
                    raise ValidationError("Mollie Api Key not Found.")
                response = send_mollie_request(url, mollie_key)
                if response and response.get('status_code', False) == 200:
                    data = {
                        'interval': "1 months"
                    }
                    response = send_mollie_request(url, mollie_key, data=json.dumps(data), r_type='patch')
        except Exception as error:
            _logger.exception(error)

        return True

    def get_subscription_payment(self):
        """
           Retrieve and process the payments made for the active subscription associated with this subscription sale.

           If a payment is found, it is checked to see if it was made within the current month. If it was, a payment
           record
           is created in the system, and the associated invoice (if any) is marked as paid.
           If the subscription is not found or there is an error in the process, the method logs the error and
           continues.
        """
        # self.update_subscription()
        subscription = self.mollie_subscription_line.filtered(lambda x: x.status == 'active')
        if subscription:
            mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
            url = f'https://api.mollie.com/v2/customers/{self.partner_id.mollie_contact_id}/subscriptions/{subscription[0].subscription_id}/payments'
            if not mollie_key:
                raise ValidationError("Mollie Api Key not Found.")
            response = send_mollie_request(url, mollie_key)
            try:
                if response and response.get('status_code', False) == 200:
                    for payment in response['data']['_embedded']['payments']:
                        if payment['status'] == 'paid':
                            mollie_date = payment['paidAt']
                            amount = float(payment['amount']['value'])
                            paid_at = datetime.fromisoformat(mollie_date).date()
                            first_date = date.today().replace(day=1)
                            next_month = relativedelta(months=+1, day=1, days=-1)
                            last_date = first_date + next_month
                            if first_date <= paid_at <= last_date:
                                invoice_ids = self.invoice_ids.filtered(
                                    lambda x: first_date <= x.invoice_date <= last_date and x.payment_state != 'paid'
                                              and x.invoice_origin == self.name and x.state == 'posted')
                                for inv in invoice_ids:
                                    mollie_payment_provider_id = self.env.ref('payment.payment_provider_mollie')
                                    account_pay_line = self.env['account.payment.method.line'].sudo().search(
                                        [('payment_provider_state', '=', 'enabled'),
                                         ('payment_provider_id', '=', mollie_payment_provider_id.id)], limit=1)
                                    if amount > 0.0:
                                        payment_values = {
                                            'amount': abs(amount),
                                            # A tx may have a negative amount, but a payment must >= 0
                                            'payment_type': 'inbound' if amount > 0 else 'outbound',
                                            'currency_id': self.currency_id.id,
                                            'partner_id': self.partner_id.commercial_partner_id.id,
                                            'partner_type': 'customer',
                                            'journal_id': mollie_payment_provider_id.journal_id.id,
                                            'company_id': mollie_payment_provider_id.company_id.id,
                                            'payment_method_line_id': account_pay_line.id,
                                            'ref': f'{self.name} - {self.partner_id.name} - {payment["id"] or ""}',
                                            'mollie_transaction': payment['id'],
                                            'mollie_payment_method': payment['method'],
                                        }
                                        payment = self.env['account.payment'].create(payment_values)
                                        payment.action_post()
                                        if inv:
                                            inv.filtered(lambda inv: inv.state == 'draft').action_post()

                                            (payment.line_ids + inv.line_ids).filtered(
                                                lambda line: line.account_id == payment.destination_account_id
                                                             and not line.reconciled
                                            ).reconcile()
            except Exception as error:
                _logger.exception(error)
        return True

    @api.model
    def cron_create_subscription_payment(self):
        """
               Retrieve and process the payments made for the subscriptions of all sale orders that meet the
               following conditions:
               - have a recurrence
               - are associated with a Mollie subscription
               - have a posted invoice that is not yet paid

               This method is intended to be run as a cron job.
        """
        sale_order_ids = self.env['sale.order'].search(
            [('recurrence_id', '!=', False), ('mollie_subscription_line', '!=', False),
             ('invoice_ids.state', '=', 'posted'), ('invoice_ids.payment_state', '!=', 'paid')])
        for order in sale_order_ids:
            order.get_subscription_payment()

    def create_recharge_invoice(self):
        """
           Create invoices and mark them as recharge invoices.

           A recharge invoice is a special type of invoice that is used to recharge the customer's account balance.
           The invoices created by this method will be marked as recharge invoices and their invoice type will be set to 'Recharge Invoice'.

           Returns:
               list[int]: A list of the created invoice ids.
        """
        invoice_ids = self._create_invoices()
        invoice_ids.write({
            'is_recharge_invoice': True,
            'invoice_type': 'Recharge Invoice',
        })

    def create_customer_recharge(self):
        """
           Create a customer recharge using Mollie API.
           The recharge will be based on the order lines in self and the amount will be
          the sum of their subtotals and taxes.
           The recharge will be associated with the partner in self.
           The description of the recharge will be "Recharge - Partner Name".
           The locale for the recharge will be based on the current context's 'lang' value, or default to
            'en_US' if the 'lang' value is not supported.
           If the Mollie API key is not found or the request to Mollie API fails, a ValidationError will be raised.
           If the request to Mollie API is successful, a message will be posted on self with the details of
           the recharge.
        """
        mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
        url = 'https://api.mollie.com/v2/payments'
        if not mollie_key:
            raise ValidationError("Mollie Api Key not Found.")
        response = send_mollie_request(url, mollie_key)
        try:
            if response and response.get('status_code', False) == 200:
                line_ids = self.order_line.filtered(lambda x: not x.is_starting_fees)
                value = sum(line_ids.mapped('price_subtotal')) + sum(line_ids.mapped('price_tax'))
                user_lang = self.env.context.get('lang')
                data = {
                    "amount": {
                        "value": str(value),
                        "currency": self.currency_id.name,
                    },
                    'sequenceType': 'recurring',
                    'customerId': self.partner_id.mollie_contact_id,
                    'description': 'Recharge' + ' - ' + self.partner_id.name,
                    "locale": user_lang if user_lang in SUPPORTED_LOCALES else 'en_US',
                }
                response = send_mollie_request(url, mollie_key, data=json.dumps(data))
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@",response)
                if response and response.get('status_code', False) == 201:
                    message = {
                        'value': response['data']['amount']['value'],
                        'sequenceType': response['data']['sequenceType'],
                        'customerId': response['data']['customerId'],
                    }
                    self.message_post(body='Recharge is created. %s' % message)
                else:
                    self.message_post(body='Recharge is not created !!!! %s' % response)
            else:
                raise ValidationError("Getting Error %s." % response.get('message', ''))
        except Exception as error:
            _logger.exception(error)
        return True

