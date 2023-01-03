# -*- coding: utf-8 -*-

import json
import logging

from odoo import fields, models
from odoo.addons.ollo_mollie_integration.models.mollie import send_mollie_request
from odoo.addons.payment_mollie.const import SUPPORTED_LOCALES
from odoo.exceptions import ValidationError
from datetime import datetime

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    mollie_contact_id = fields.Char(string='Mollie Contact')
    mollie_mandate_id = fields.Char(string='Mollie Mandate')
    mollie_payment_method = fields.Char(string='Mollie Payment Method')


    def action_send_customer(self):
        self._create_customer()
        # self._create_mandate()

    def _create_customer(self):
        """
            create customer in mollie
        """
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

    def update_customer(self):
        """
            update customer details in mollie
        """
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

    def get_customer_payment(self):
        """
            get customer payment from Mollie
        """
        try:
            url = f'https://api.mollie.com/v2/customers/{self.mollie_contact_id}/payments'
            mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
            if not mollie_key:
                raise ValidationError("Mollie Api Key not Found.")
            response = send_mollie_request(url, mollie_key)

            if response and response.get('status_code', False) == 200:
                for payment in response['data']['_embedded']['payments']:
                    transaction_id = self.env['payment.transaction'].sudo().search([('provider_reference', '=', payment['id']),
                                                                                    ('partner_id', '=', self.id),
                                                                                    ('mollie_payment_method', '=', False)])
                    if transaction_id:
                        self.mollie_payment_method = payment['method']
                        transaction_id.mollie_payment_method = payment['method']
                        if transaction_id.mollie_payment_method != 'paypal':
                            transaction_id.customer_account = payment['details']['cardNumber']
                        else:
                            transaction_id.paypal_agreement = payment['details']['paypalReference']
                        # self.create_mandate(transaction_id)
            else:
                raise ValidationError("Getting Error %s." % response.get('message', ''))

        except Exception as error:
            _logger.exception(error)

        return True

    def create_mandate(self):
        """
            create mandate
        """
        try:
            if self.mollie_mandate_id:
                return self.mollie_mandate_id
            if not self.mollie_contact_id:
                self._create_customer()
            # url = 'https://api.mollie.com/v2/payments'

            mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
            url = f'https://api.mollie.com/v2/customers/{self.mollie_contact_id}/payments'
            if not mollie_key:
                raise ValidationError("Mollie Api Key not Found.")
            response = send_mollie_request(url, mollie_key)

            if response and response.get('status_code', False) == 200:
                for payment in response['data']['_embedded']['payments']:
                    transaction_id = self.env['payment.transaction'].sudo().search(
                        [('provider_reference', '=', payment['id']),
                         ('partner_id', '=', self.id),
                         ('mollie_payment_method', '!=', False)])
                    data = {}
                    if transaction_id:
                        if transaction_id.mollie_payment_method == 'paypal':
                            data.update({
                                "method": 'paypal',  # required
                                "consumerName": self.name,  # required
                                'paypalBillingAgreementId': transaction_id.paypal_agreement,
                                'consumerEmail': self.email,
                                # "consumerAccount": "NL55INGB0000000000",
                                # "consumerBic": "INGBNL2A",
                                # "signatureDate": datetime.today().strftime('%Y-%m-%d'),
                                # "mandateReference": "YOUR-COMPANY-MD13804",
                            })
                        else:
                            data.update({
                                "method": 'directdebit',
                                "consumerName": self.name,  # required
                                "consumerAccount":  "NL55INGB0000000000",  # conditional
                                "signatureDate": datetime.today().strftime('%Y-%m-%d'),
                                'consumerEmail': self.email
                            })
                        url = 'https://api.mollie.com/v2/customers/{id}/mandates'.format(id=self.mollie_contact_id)
                        response = send_mollie_request(url, mollie_key, data=json.dumps(data))
                        if response and response.get('status_code', False) == 201:
                            if response and response.get('data', False) and response['data'].get('id', False):
                                self.mollie_mandate_id = response['data']['id']
                                return self.mollie_mandate_id
                        else:
                            self.message_post(body='Mandate in not created!!!! %s' % response)
                            raise ValidationError("Getting Error %s." % response.get('message', ''))
        except Exception as error:
            _logger.exception(error)

        return True
