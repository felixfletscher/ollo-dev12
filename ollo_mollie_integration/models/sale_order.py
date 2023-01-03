# -*- coding: utf-8 -*-
import logging
import json
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
from odoo.addons.ollo_mollie_integration.models.mollie import send_mollie_request
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    mollie_subscription_line = fields.One2many('molliesubscriptions.subscription', 'order_id')
    abo_delivery_count = fields.Integer(compute="compute_abo_delivery", copy=False, default=0)
    is_starting_fees = fields.Boolean('Starting Fess', default=False)

    # mollie_subscription_id = fields.Char(related='mollie_id.subscription_id')
    cirf_result = fields.Selection([
        ('normal', 'Normal'),
        ('done', 'Success'),
        ('blocked', 'Fail')], string='CIRF result', default='normal')

    def action_create_delivery(self):
        """
            create abbo product delivery
        """
        for rec in self:
            abo_delivery_count = self.env['stock.picking'].sudo().search_count(
                [('abo_sale_id', '=', rec.id), ('is_abo_picking', '=', True), ('state', '!=', 'cancel')])
            if abo_delivery_count == 0:
                stock_move = self.env['stock.move']
                # Create an empty list to store stock moves
                product_list = []
                # Find the default picking type for outgoing shipments
                picking_type_id = self.env['stock.picking.type'].sudo().search(
                    [('code', '=', 'outgoing'), ('company_id', '=', self.company_id.id)], limit=1)
                # Loop through the order lines
                for rec in self.order_line:
                    # Loop through the linked products of the current order line product
                    for record in rec.product_id.linked_product_line.filtered(lambda x: x.is_abo_product):
                        # Create a stock move for the current linked product
                        move_vals = {
                            'product_id': record.product_variant_id.id,
                            'product_uom_qty': record.product_qty * rec.product_uom_qty,
                            'location_id': picking_type_id.default_location_src_id.id,
                            'name': _('Auto processed move : %s') % record.product_variant_id.display_name,
                            'location_dest_id': self.env.ref('stock.stock_location_customers').sudo().id
                        }
                        values = stock_move.create(move_vals)
                        # Add the created stock move to the product list
                        product_list.append(values.id)
                # If there are any products in the list, create a picking for them
                if product_list:
                    self.create_picking(product_list)

    def create_picking(self, product_list):
        """This static method will confirm the sale
         order and this will also validate the picking"""
        picking_type_id = self.env['stock.picking.type'].sudo().search(
            [('code', '=', 'outgoing'), ('company_id', '=', self.company_id.id)], limit=1)
        picking = self.env['stock.picking'].sudo().create({
            'is_abo_picking': True,
            'location_dest_id': self.env.ref('stock.stock_location_customers').sudo().id,
            'location_id': picking_type_id.default_location_src_id.id,
            'move_ids_without_package': [(6, 0, product_list)],
            'move_type': 'direct',
            'origin': self.name,
            'partner_id': self.partner_id.id,
            'picking_type_id': picking_type_id.id,
            'state': 'assigned',
            'abo_sale_id': self.id,
        })
        # self.write({'picking_ids': [(4, picking.id)]})

    # abo view abo delivery
    def action_view_abo_delivery(self):
        """
            action for view abo delivery
        """
        self.ensure_one()
        action = {
            'name': 'Abo Delivery',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'domain': [('abo_sale_id', '=', self.id), ('is_abo_picking', '=', True)]
        }
        return action

    # abo delivery count
    def compute_abo_delivery(self):
        """
            get abo delivery count
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

    def action_create_mollib_subscription(self):
        pass

    def action_create_refund(self):
        pass

    def action_run_crif_check(self):
        pass

    def action_update_mollib_subscription(self):
        pass

    def action_end_mollib_subscription(self):
        pass

    def action_view_subscription(self):
        """
            smart button for show customer subscription
        """
        self.ensure_one()
        action = {
            'name': 'Mollie Subscription',
            'view_mode': 'tree,form',
            'res_model': 'molliesubscriptions.subscription',
            'type': 'ir.actions.act_window',
            'domain': [('order_id', '=', self.id)]
        }
        return action

    # override base method for hide abo delivery count
    @api.depends('picking_ids')
    def _compute_picking_ids(self):
        """
            remove abo product delivery count from normal product delivery
        """
        for order in self:
            order.delivery_count = len(order.picking_ids.filtered(lambda picking: not picking.is_abo_picking))

    # @api.depends('is_subscription', 'state', 'start_date', 'subscription_management', 'date_order')
    # def _compute_next_invoice_date(self):
    #     """
    #         add buffer days in next invoice date
    #     """
    #     super(SaleOrder, self)._compute_next_invoice_date()
    #     buffer_days = self.env['ir.config_parameter'].sudo().get_param('ollo_mollie_integration.buffer_days')
    #     converted_num = int(buffer_days)
    #
    #     for rec in self:
    #         rec.next_invoice_date = rec.start_date or fields.Date.today()
    #         if converted_num > 0:
    #             rec.next_invoice_date = rec.next_invoice_date + timedelta(converted_num)

    def update_subscription(self):
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
        self.update_subscription()
        try:
            subscription = self.mollie_subscription_line.filtered(lambda x: x.status == 'active')
            if subscription:
                mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
                url = f'https://api.mollie.com/v2/customers/{self.partner_id.mollie_contact_id}/subscriptions/{subscription[0].subscription_id}/payments'
                if not mollie_key:
                    raise ValidationError("Mollie Api Key not Found.")
                response = send_mollie_request(url, mollie_key)
                if response and response.get('status_code', False) == 200:
                    for payment in response['data']['_embedded']['payments']:
                        if payment['status'] == 'pending':
                            mollie_date = payment['createdAt']
                            amount = float(payment['amount']['value'])
                            paid_at = datetime.fromisoformat(mollie_date).date()
                            first_date = date.today().replace(day=1)
                            next_month = relativedelta(months=+1, day=1, days=-1)
                            last_date = first_date + next_month
                            if first_date <= paid_at <= last_date:
                                invoice_ids = self.invoice_ids.filtered(
                                    lambda x: first_date <= x.invoice_date <= last_date and x.payment_state != 'paid'
                                              and x.invoice_origin == self.name)
                                for inv in invoice_ids:
                                    # lines = self.env['account.move'].browse(inv.id).line_ids
                                    # account_pay = self.env['account.payment.method'].sudo().search(
                                    #     [('code', '=', 'mollie'), ('payment_type', '=', 'inbound')], limit=1)

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
        sale_order_ids = self.env['sale.order'].search(
            [('recurrence_id', '!=', False), ('mollie_subscription_line', '!=', False),
             ('invoice_ids.state','=','posted'),('invoice_ids.payment_state','!=','paid')])
        for order in sale_order_ids:
            order.get_subscription_payment()

    # def create_subscription_payment(self):
    #     try:
    #
    #         mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
    #         url = f'https://api.mollie.com/v2/customers/{self.partner_id.mollie_contact_id}/payments'
    #         if not mollie_key:
    #             raise ValidationError("Mollie Api Key not Found.")
    #         response = send_mollie_request(url, mollie_key)
    #         if response and response.get('status_code', False) == 200:
    #             print("*******************************", response)
    #
    #         data = {
    #             "amount": {
    #                 "value": "100.00",
    #                 "currency": "EUR",
    #             },
    #             'sequenceType': 'first',
    #             # 'method': 'directdebit',
    #             # "email": self.email,
    #             'description': 'test payment for sub',
    #             "redirectUrl": "https://webshop.example.org/order/12345/",
    #             "webhookUrl": "https://webshop.example.org/payments/webhook/",
    #             "subscriptionId": 'sub_NXJ6fgkrpQ',
    #         }
    #         response = send_mollie_request(url, mollie_key, data=json.dumps(data))
    #         print("************** iiiiiiiiiiiiiii *****************", response)
    #         if response and response.get('status_code', False) == 201:
    #             print("************** send *****************", response)
    #     #         if response and response.get('data', False) and response['data'].get('id', False):
    #     #             self.mollie_contact_id = response['data']['id']
    #     #             return self.mollie_contact_id
    #     #     else:
    #     #         raise ValidationError("Getting Error %s." % response.get('message', ''))
    #     except Exception as error:
    #         _logger.exception(error)
    #
    #     return True
