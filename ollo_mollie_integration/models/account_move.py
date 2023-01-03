# -*- coding: utf-8 -*-

import json
import logging

from odoo import models, api, fields, _
from odoo.addons.ollo_mollie_integration.models.mollie import send_mollie_request
from odoo.addons.payment_mollie.const import SUPPORTED_LOCALES
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    mollie_payment_state = fields.Selection([
        ('paid', 'Paid in Mollie'),
        ('pending', 'Pending in Mollie')], string='Mollie Payment State')

    def create_refund(self):
        """
            create refund in mollie
        """
        try:
            transaction_id = self.env['payment.transaction'].sudo().search(
                [('reference', '=', self.line_ids.sale_line_ids.order_id.name),
                 ('partner_id', '=', self.line_ids.sale_line_ids.order_id.partner_id.id)])
            payment_id = transaction_id.provider_reference
            url = f'https://api.mollie.com/v2/payments/{payment_id}/refunds'
            mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
            if not mollie_key:
                raise ValidationError("Mollie Api Key not Found.")
            data = {
                "amount": {
                    "value": f"{self.amount_total:.2f}",
                    "currency": "EUR",
                }
            }
            response = send_mollie_request(url, mollie_key, data=json.dumps(data))
        except Exception as error:
            _logger.exception(error)
        return True

    @api.model
    def cron_update_mollie_payment_state(self):
        try:
            for rec in self:
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
                                mollie_date = payment['createdAt']
                                paid_at = datetime.fromisoformat(mollie_date).date()
                                first_date = date.today().replace(day=1)
                                next_month = relativedelta(months=+1, day=1, days=-1)
                                last_date = first_date + next_month
                                if first_date <= paid_at <= last_date:
                                    rec.mollie_payment_state = 'paid'
                                else:
                                    rec.mollie_payment_state = 'pending'
                            else:
                                rec.mollie_payment_state = 'pending'
        except Exception as error:
            _logger.exception(error)
