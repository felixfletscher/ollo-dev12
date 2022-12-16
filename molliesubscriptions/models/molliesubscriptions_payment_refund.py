from odoo import _, api, fields, models
from datetime import datetime
import requests
import logging

_logger = logging.getLogger(__name__)

class MollieSubscriptionsPaymentRefund(models.Model):
    _name = 'molliesubscriptions.payment.refund'
    _description = 'Mollie Subscription Payment Refund'
    _rec_name = 'payment_id'


    refund_id = fields.Char(string='Refund ID', readonly=True)
    amount_value = fields.Float(string='Amount Value', required=True)
    amount_currency = fields.Selection(
        selection=[('EUR', 'EUR')], required=True, default='EUR'
    )
    status = fields.Char(string='Status', readonly=True)
    created_at = fields.Datetime(string='Created at', readonly=True)
    description = fields.Char(string='Description')

    settlement_amount_value = fields.Float(string='Settlement Amount Value', readonly=True)
    settlement_amount_currency = fields.Char(string='Settlement Amount Currency', readonly=True)
    
    payment_id = fields.Many2one("molliesubscriptions.payment", string="Payment")


    def _get_notification_message(self, message, message_type='success'):

        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': message_type.title(),
                'message': message,
                'type': message_type,  # types: success,warning,danger,info
                # 'fadeout': 'slow',
                'sticky': True
                # 'next': {'type': 'ir.actions.client', 'tag': 'reload'}
            },
            
        }
        return notification

    # https://docs.mollie.com/reference/v2/refunds-api/create-payment-refund
    def create_payment_refund(self):

        if self.refund_id or not self.payment_id or not self.amount_value or not self.amount_currency:
            notification = self._get_notification_message(message=f'Refund can not be created.', message_type='error')
            return notification

        url = f'https://api.mollie.com/v2/payments/{self.payment_id.payment_id}/refunds'
        headers = {"Authorization": f"Bearer {self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')}"}

        data = {
            'amount': {'currency': self.amount_currency, 'value': f"{self.amount_value:.2f}"},
        }

        if self.description: data['description'] = self.description

        response = requests.post(url, headers=headers, json=data)
        response_dict = response.json()

        _logger.info(response.status_code)
        _logger.info(response.text)

        if response.status_code == 201:
            for record in self:
                record.refund_id = response_dict['id']
                record.status = response_dict['status']
                record.created_at = datetime.strptime(response_dict['createdAt'], '%Y-%m-%dT%H:%M:%S+00:00')
                record.settlement_amount_value = response_dict['settlementAmount']['value']
                record.settlement_amount_currency = response_dict['settlementAmount']['currency']
            return self._get_notification_message(message=f"Refund {response_dict['id']} successfully created.", message_type='success')
        else:
            return self._get_notification_message(message=f"Error, refund was not created: {response.text}", message_type='error')

        return