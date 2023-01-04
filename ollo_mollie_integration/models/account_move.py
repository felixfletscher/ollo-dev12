# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime, date

from dateutil.relativedelta import relativedelta
from odoo import fields, models, api
from odoo.addons.ollo_mollie_integration.models.mollie import send_mollie_request
from odoo.addons.payment_mollie.const import SUPPORTED_LOCALES
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    mollie_payment_state = fields.Selection([
        ('paid', 'Paid'),
        ('pending', 'Pending in Mollie'), ('canceled', 'Cancel'), ('expires', 'Expires'),
        ('failed', 'Failed')], string='Mollie Payment State', default='pending')
    mollie_payment = fields.Char(string='Mollie Payment', copy=False)
    mollie_refund_done = fields.Boolean(string="Mollie refund done successfully")
    sale_order_line = fields.Many2many(comodel_name='sale.order.line')
    is_recharge_invoice = fields.Boolean(string="Is recharge invoice")
    recharge_done = fields.Boolean(string="Recharge done in Mollie")
    invoice_type = fields.Char(string="Invoice Type", copy=False,default="Recharge Invoice")

    def create_customer_recharge(self):
        try:
            mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
            url = 'https://api.mollie.com/v2/payments'
            if not mollie_key:
                raise ValidationError("Mollie Api Key not Found.")
            response = send_mollie_request(url, mollie_key)
            sale_id = self.env['sale.order'].search([('name', '=', self.invoice_origin)], limit=1)
            if response and response.get('status_code', False) == 200:
                line_ids = sale_id.order_line.filtered(lambda x: not x.is_starting_fees)
                # value = sum(line_ids.mapped('price_subtotal')) + sum(line_ids.mapped('price_tax'))
                user_lang = self.env.context.get('lang')
                data = {
                    "amount": {
                        "value": str(self.amount_total),
                        "currency": self.currency_id.name,
                    },
                    'sequenceType': 'recurring',
                    'customerId': self.partner_id.mollie_contact_id,
                    'description': 'Recharge' + ' - ' + self.partner_id.name,
                    "locale": user_lang if user_lang in SUPPORTED_LOCALES else 'en_US',
                }
                response = send_mollie_request(url, mollie_key, data=json.dumps(data))
                if response and response.get('status_code', False) == 201:
                    message = {
                        'value': response['data']['amount']['value'],
                        'sequenceType': response['data']['sequenceType'],
                        'customerId': response['data']['customerId'],
                    }
                    self.recharge_done = True
                    self.message_post(body='Recharge is created. %s' % message)
                else:
                    self.message_post(body='Recharge is not created !!!! %s' % response)
            else:
                raise ValidationError("Getting Error %s." % response.get('message', ''))
        except Exception as error:
            _logger.exception(error)
        return True

    def create_refund(self):
        """
            create refund in mollie
        """
        try:
            if self.move_type == 'out_refund' and self.reversed_entry_id:
                account_payment_ids = self.env['account.payment'].search([('partner_id', '=', self.partner_id.id)])
                account_payment_id = account_payment_ids.filtered(
                    lambda x: self.reversed_entry_id in x.reconciled_invoice_ids)
                if account_payment_id:
                    transaction = account_payment_id.mollie_transaction
                    if not transaction:
                        transaction = account_payment_id.ref.split('-')[-1].strip()
                    url = f'https://api.mollie.com/v2/payments/{transaction}/refunds'
                    mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
                    if not mollie_key:
                        raise ValidationError("Mollie Api Key not Found.")
                    data = {
                        "amount": {
                            "value": f"{self.amount_total:.2f}",
                            "currency": self.currency_id.name,
                        }
                    }
                    response = send_mollie_request(url, mollie_key, data=json.dumps(data))
                    if response and response.get('status_code', False) == 201:
                        self.mollie_refund_done = True
                        message = {
                            'value': response['data']['amount']['value'],
                            'currency': response['data']['amount']['currency'],
                        }
                        self.message_post(body='Credit note successfully created of %s' % message)
                    else:
                        self.message_post(body='Credit note is not created!!!! %s' % response)
        except Exception as error:
            _logger.exception(error)
        return True

    @api.model
    def cron_update_mollie_payment_state(self):
        try:
            invoice_ids = self.env['account.move'].sudo().search(
                [('state', '=', 'posted'), ('mollie_payment_state', '!=', 'paid')])
            for rec in invoice_ids:
                subscription = rec.line_ids.sale_line_ids.order_id.mollie_subscription_line.filtered(
                    lambda x: x.status == 'active')
                if subscription:
                    mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
                    url = f'https://api.mollie.com/v2/customers/{rec.partner_id.mollie_contact_id}/subscriptions/{subscription[0].subscription_id}/payments'
                    if not mollie_key:
                        raise ValidationError("Mollie Api Key not Found.")
                    response = send_mollie_request(url, mollie_key)
                    if response and response.get('status_code', False) == 200:
                        for payment in response['data']['_embedded']['payments']:
                            if 'paidAt' in payment:
                                mollie_date = payment['paidAt']
                                paid_at = datetime.fromisoformat(mollie_date).date()
                                first_date = date.today().replace(day=1)
                                next_month = relativedelta(months=+1, day=1, days=-1)
                                last_date = first_date + next_month
                                if first_date <= paid_at <= last_date:
                                    rec.mollie_payment_state = 'paid'
                                else:
                                    rec.mollie_payment_state = 'pending'
                                rec.mollie_payment = payment['status']
                            else:
                                rec.mollie_payment_state = 'pending'
                                rec.mollie_payment = payment['status']

        except Exception as error:
            _logger.exception(error)
