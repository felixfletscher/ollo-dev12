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


class AccountMove(models.Model):
    _inherit = 'account.move'

    mollie_payment_states = fields.Char(string='Mollie Payment State', copy=False)
    mollie_refund_done = fields.Boolean(string='Mollie refund done successfully', copy=False)
    is_recharge_invoice = fields.Boolean(string='Is recharge invoice', copy=False)
    recharge_done = fields.Boolean(string='Recharge done in Mollie', copy=False)
    invoice_type = fields.Char(string='Invoice Type', copy=False)

    def create_customer_recharge(self):
        """
            Create a customer recharge for the given invoice using the Mollie API.
            If the recharge is successful, the `recharge_done` flag is set to True.
            If the recharge fails, a message is posted with the response from the Mollie API.
        """
        mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
        url = 'https://api.mollie.com/v2/payments'
        if not mollie_key:
            raise ValidationError("Mollie Api Key not Found.")
        response = send_mollie_request(url, mollie_key)
        sale_id = self.env['sale.order'].search([('name', '=', self.invoice_origin)], limit=1)
        try:
            if response and response.get('status_code', False) == 200:
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
            Create a refund for the given invoice using the Mollie API.
            If the refund is successful, the `mollie_refund_done` flag is set to True.
            If the refund fails, a message is posted with the response from the Mollie API.
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
                        },
                        "description": self.name + ' - ' + self.invoice_origin,
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
    def cron_update_mollie_subscription_payment_state(self):
        """
         This method is used to update the payment state for invoices that are paid through Mollie subscriptions.
         It is intended to be run as a cron job.

         It will search for posted invoices with a non-empty Mollie contact ID and a `mollie_payment_states`
         value other than "paid",
         and will update their payment state by calling `update_mollie_subscription_payment_state()` on those invoices.
         It will also search for posted refund invoices with a non-empty Mollie contact ID and a `mollie_payment_states
         ` value other than "refunded",
         and will update their payment state by calling `update_mollie_refund_payment_state()` on those invoices.
         """
        invoice_ids = self.env['account.move'].sudo().search(
            [('state', '=', 'posted'), ('mollie_payment_states', '!=', 'paid'),
             ('partner_id.mollie_contact_id', '!=', False), ('move_type', 'in', ['out_invoice'])])

        refund_invoice_ids = self.env['account.move'].sudo().search(
            [('state', '=', 'posted'), ('mollie_payment_states', '!=', 'refunded'),
             ('partner_id.mollie_contact_id', '!=', False), ('move_type', 'in', ['out_refund'])])

        invoice_ids.update_mollie_first_payment_state()
        invoice_ids.update_mollie_subscription_payment_state()
        refund_invoice_ids.update_mollie_refund_payment_state()

    def update_mollie_subscription_payment_state(self):
        """
             Update the payment status of the Mollie subscription associated with the
             invoice.

             This function retrieves the active Mollie subscription for the invoice and
             retrieves a list of payments for the subscription using the Mollie API. It
             then updates the `mollie_payment_states` field of the invoice with the
             status of the payment made within the current month. If an error occurs
             during the process, it is logged.
        """
        for rec in self:
            subscription = rec.line_ids.sale_line_ids.order_id.mollie_subscription_line.filtered(
                lambda x: x.status == 'active')
            if subscription:
                mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
                url = f'https://api.mollie.com/v2/customers/{rec.partner_id.mollie_contact_id}/subscriptions/{subscription[0].subscription_id}/payments'
                if not mollie_key:
                    raise ValidationError("Mollie Api Key not Found.")
                try:
                    response = send_mollie_request(url, mollie_key, limit=10)
                    if response and response.get('status_code', False) == 200:
                        for payment in response['data']['_embedded']['payments']:
                            if 'paidAt' in payment:
                                mollie_date = payment['paidAt']
                                paid_at = datetime.fromisoformat(mollie_date).date()
                                first_date = date.today().replace(day=1)
                                next_month = relativedelta(months=+1, day=1, days=-1)
                                last_date = first_date + next_month
                                if first_date <= paid_at <= last_date:
                                    rec.mollie_payment_states = payment['status']
                                else:
                                    rec.mollie_payment_states = payment['status']
                            else:
                                rec.mollie_payment_states = payment['status']
                    self._cr.commit()
                except Exception as error:
                    _logger.exception(error)

    def update_mollie_first_payment_state(self):
        """
         Update the payment status of the first payment for the Mollie subscription
         for the invoice.

         This function retrieves the Mollie API key from the Odoo configuration
         parameters and uses it to make a request to the Mollie API to retrieve a
         list of payments for the customer associated with the invoice. It then
         loops through the payments and checks whether the payment was made within
         the current month. If it was, it updates the `mollie_payment_states`
         field of the invoice with the status of the payment. If an error occurs
         during the process, it is logged.
         """
        for rec in self:
            mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
            url = f'https://api.mollie.com/v2/customers/{rec.partner_id.mollie_contact_id}/payments'
            if not mollie_key:
                raise ValidationError("Mollie Api Key not Found.")
            try:
                response = send_mollie_request(url, mollie_key, limit=10)
                if response and response.get('status_code', False) == 200:
                    for payment in response['data']['_embedded']['payments']:
                        if 'paidAt' in payment:
                            mollie_date = payment['paidAt']
                            paid_at = datetime.fromisoformat(mollie_date).date()
                            first_date = date.today().replace(day=1)
                            next_month = relativedelta(months=+1, day=1, days=-1)
                            last_date = first_date + next_month
                            if first_date <= paid_at <= last_date:
                                rec.mollie_payment_states = payment['status']
                            else:
                                rec.mollie_payment_states = payment['status']
                        else:
                            rec.mollie_payment_states = payment['status']
                self._cr.commit()
            except Exception as error:
                _logger.exception(error)

    def update_mollie_refund_payment_state(self):
        """Updates the 'mollie_payment_states' field for records in the model with refund payment data from Mollie's API.

          This function retrieves refund payment data for the current record's partner from Mollie's API and updates the
          'mollie_payment_states' field with the status of the refund payment. It only updates the field if the refund
          payment was created within the current month.

          """
        for rec in self:
            if rec.move_type == 'out_refund' and rec.reversed_entry_id:
                account_payment_ids = self.env['account.payment'].search([('partner_id', '=', rec.partner_id.id)])
                account_payment_id = account_payment_ids.filtered(
                    lambda x: rec.reversed_entry_id in x.reconciled_invoice_ids)
                if account_payment_id:
                    mollie_key = self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')
                    transaction = account_payment_id.mollie_transaction
                    if not transaction:
                        transaction = account_payment_id.ref.split('-')[-1].strip()
                    url = f'https://api.mollie.com/v2/payments/{transaction}/refunds'
                    if not mollie_key:
                        raise ValidationError("Mollie Api Key not Found.")
                    try:
                        response = send_mollie_request(url, mollie_key, limit=10)
                        if response and response.get('status_code', False) == 200:
                            for payment in response['data']['_embedded']['refunds']:
                                if 'createdAt' in payment:
                                    mollie_date = payment['createdAt']
                                    paid_at = datetime.fromisoformat(mollie_date).date()
                                    first_date = date.today().replace(day=1)
                                    next_month = relativedelta(months=+1, day=1, days=-1)
                                    last_date = first_date + next_month
                                    if first_date <= paid_at <= last_date:
                                        rec.mollie_payment_states = payment['status']
                                    else:
                                        rec.mollie_payment_states = payment['status']
                                else:
                                    rec.mollie_payment_states = payment['status']
                        self._cr.commit()
                    except Exception as error:
                        _logger.exception(error)
        return True
