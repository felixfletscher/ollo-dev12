# -*- coding: utf-8 -*-

import json
import requests
from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.ollo_crif_integration.models.mollie import send_mollie_request
from odoo.addons.payment_mollie.const import SUPPORTED_LOCALES
import logging
from operator import itemgetter

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    mollie_contact_id = fields.Char(string='Mollie Contact')
    mollie_mandate_id = fields.Char(string='Mollie Mandate')

    def action_get_mollib_info(self):
        pass

    def action_send_customer(self):
        self._create_customer()
        # self._create_mandate()

    def _create_customer(self):
        try:
            if self.mollie_contact_id:
                return self.mollie_contact_id
            url = 'https://api.mollie.com/v2/customers'
            mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
            if not mollie_key:
                raise ValidationError("Mollie Api Key not Found.")
            user_lang = self.env.context.get('lang')
            data = {
                "name": self.name,
                "email": self.email,
                "locale": user_lang if user_lang in SUPPORTED_LOCALES else 'en_US',
            }
            response = send_mollie_request(url, mollie_key, data=json.dumps(data))
            if response and response.get('status_code', False) == 201:
                if response and response.get('data', False) and response['data'].get('id', False):
                    self.mollie_contact_id = response['data']['id']
                    return self.mollie_contact_id
            else:
                raise ValidationError("Getting Error %s." % response.get('message', ''))

        except Exception as error:
            _logger.exception(error)

        return True

    def _create_mandate(self):
        try:
            if self.mollie_mandate_id:
                return self.mollie_mandate_id
            if not self.mollie_contact_id:
                self._create_customer()
            url = 'https://api.mollie.com/v2/payments'
            # url = 'https://api.mollie.com/v2/customers/cst_2BJqxziENi/payments'
            mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
            response = send_mollie_request(url, mollie_key)
            data = {
                "method": "directdebit",  # required
                "consumerName": self.name,  # required
                "consumerAccount": "NL55INGB0000000000",  # conditional
                "consumerBic": "INGBNL2A",  # optional
                "signatureDate": "2020-04-23",  # optional
                "mandateReference": "YOUR-COMPANY-MD13804",  # optional
            }
            response = send_mollie_request(url, mollie_key, data=json.dumps(data))
            if response and response.get('status_code', False) == 201:
                if response and response.get('data', False) and response['data'].get('id', False):
                    self.mollie_mandate_id = response['data']['id']
                    return self.mollie_mandate_id
            else:
                raise ValidationError("Getting Error %s." % response.get('message', ''))
        except Exception as error:
            _logger.exception(error)

        return True

    def update_customer(self):
        try:
            if not self.mollie_contact_id:
                raise ValidationError("Mollie contact id not set. please create first.")
            url = 'https://api.mollie.com/v2/customers/{id}'.format(id=self.mollie_contact_id)
            mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
            user_lang = self.env.context.get('lang')
            response = send_mollie_request(url, mollie_key)
            if response and response.get('status_code', False) == 200:
                if response['data']['id'] == self.mollie_contact_id:
                    if response['data']['email'] != self.email or response['data']['name'] != self.name:
                        data = {
                            "email": self.email,
                            "name": self.name,
                            "locale": user_lang if user_lang in SUPPORTED_LOCALES else 'en_US',
                        }
                        update_data_response = send_mollie_request(url, mollie_key, data=json.dumps(data))
                        if update_data_response and update_data_response.get('status_code', False) == 200:
                            raise ValidationError("Contact Successfully updated in mollie.")
            else:
                raise ValidationError("Getting Error %s." % response.get('message', ''))
        except Exception as error:
            _logger.exception(error)

        return True
