# -*- coding: utf-8 -*-

import json
import logging

from odoo import fields, models
from odoo.addons.ollo_mollie_integration.utils.mollie import send_mollie_request
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

    def _create_customer(self):
        """
            Create a customer in Mollie for the current record.
            A Mollie customer is created using the name, email, and language of the current record.
            The Mollie API key is read from the system configuration.
            If the customer is successfully created, the Mollie contact ID is stored in the `mollie_contact_id`
            field of the current record.
            If an error occurs, a ValidationError is raised.
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
            Update a customer in Mollie for the current record.
            The Mollie customer is updated with the name, email, and language of the current record.
            The Mollie API key is read from the system configuration.
            If the Mollie contact ID is not set for the current record, a ValidationError is raised.
            If the customer is successfully updated, a ValidationError with the message "Contact Successfully
            updated in mollie." is raised.
            If an error occurs, a ValidationError is raised with the error message received from Mollie.
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
            Retrieve payment information for a customer from Mollie.

           The payment information includes the payment method used for each payment made by the customer.
           The Mollie API key is read from the system configuration.
           If payment information is successfully retrieved, the payment method is stored in the
           `mollie_payment_method` field of the current record and the corresponding payment transaction records.
           If an error occurs, a ValidationError is raised with the error message received from Mollie.
           """
        try:
            url = f'https://api.mollie.com/v2/customers/{self.mollie_contact_id}/payments'
            mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
            if not mollie_key:
                raise ValidationError("Mollie Api Key not Found.")
            response = send_mollie_request(url, mollie_key)

            if response and response.get('status_code', False) == 200:
                for payment in response['data']['_embedded']['payments']:
                    transaction_id = self.env['payment.transaction'].sudo().search(
                        [('provider_reference', '=', payment['id']),
                         ('partner_id', '=', self.id),
                         ('mollie_payment_method', '=', False)])
                    if transaction_id:
                        self.mollie_payment_method = payment['method']
                        transaction_id.mollie_payment_method = payment['method']
            else:
                raise ValidationError("Getting Error %s." % response.get('message', ''))

        except Exception as error:
            _logger.exception(error)

        return True
