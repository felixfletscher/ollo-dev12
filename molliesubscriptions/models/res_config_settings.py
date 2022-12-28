from odoo import fields, models
import requests
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mollie_api_key = fields.Char(string='Mollie API Key', config_parameter='molliesubscriptions.mollie_api_key')

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

    def test_mollie_api_key(self):

        if not self.mollie_api_key:
            return self._get_notification_message(message=f'No API Key has been set.', message_type='warning')

        url = 'https://api.mollie.com/v2/payments?limit=1'
        headers = {"Authorization": f"Bearer {self.mollie_api_key}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return self._get_notification_message(message=f'API Key is valid.', message_type='success')
        else:
            return self._get_notification_message(message=f'API Key is invalid: {response.text}', message_type='error')
