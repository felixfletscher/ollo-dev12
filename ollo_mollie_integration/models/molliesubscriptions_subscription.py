# -*- coding: utf-8 -*-
import logging
from datetime import datetime

import requests
from odoo import fields, models
from odoo.addons.molliesubscriptions.models.molliesubscriptions_subscription import \
    MollieSubscriptionsSubscription as MollieSubscriptionsSubscriptionExt

_logger = logging.getLogger(__name__)


def create_subscription(self):
    if self.subscription_id:
        notification = self._get_notification_message(
            message=f'Error, Subscription already created: {self.subscription_id}', message_type='danger')
        return notification

    url = f'https://api.mollie.com/v2/customers/{self.customer_id}/subscriptions'
    headers = {
        "Authorization": f"Bearer {self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')}"}

    # Required
    data = {
        'amount': {'currency': 'EUR', 'value': f"{self.value:.2f}"},
        'interval': self.interval_id.display_name,
        'description': self.description,
        # 'startDate': self.start_date.strftime('%Y-%m-%d'),
        # 'method': 'directdebit',#'paypal',
        # '': 'PpwIiDeRpMQsW090Q',
    }

    # Optional
    if self.start_date: data['startDate'] = self.start_date.strftime('%Y-%m-%d')

    _logger.info(str(data))

    response = requests.post(url, headers=headers, json=data)
    response_dict = response.json()

    _logger.info(response.status_code)
    _logger.info(response.text)

    if response.status_code == 201:
        for record in self:
            record.subscription_id = response_dict['id']
            record.status = response_dict['status']
            record.next_payment_date = response_dict['nextPaymentDate']
            record.mollie_created_at = datetime.strptime(response_dict['createdAt'], '%Y-%m-%dT%H:%M:%S+00:00')
        return self._get_notification_message(message=f"Subscription {response_dict['id']} successfully created.",
                                              message_type='success')
    else:
        return self._get_notification_message(message=f"Error, subscription was not created: {response.text}",
                                              message_type='danger')


def update_subscription_data(self):
    if not self.subscription_id:
        notification = self._get_notification_message(message=f'Error, Subscription was not yet created.',
                                                      message_type='danger')
        return notification

    url = f'https://api.mollie.com/v2/customers/{self.customer_id}/subscriptions/{self.subscription_id}'
    headers = {
        "Authorization": f"Bearer {self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')}"}

    response = requests.get(url, headers=headers)
    response_dict = response.json()

    _logger.info(response.status_code)
    _logger.info(response.text)

    if response.status_code == 200:
        for record in self:
            record.value = response_dict['amount']['value']
            record.description = response_dict['description']
            record.status = response_dict['status']
            record.mollie_created_at = datetime.strptime(response_dict['createdAt'], '%Y-%m-%dT%H:%M:%S+00:00')

            if record.status != 'canceled':
                record.next_payment_date = response_dict['nextPaymentDate']
            else:
                record.next_payment_date = None
                record.mollie_canceled_at = datetime.strptime(response_dict['canceledAt'],
                                                              '%Y-%m-%dT%H:%M:%S+00:00')

            # interval_mollie = response_dict['interval'].split(' ')
            interval_id = self.env.ref('ollo_mollie_integration.mollie_interval_1month')
            #self.get_interval_type(response_dict['interval'], interval_mollie=interval_mollie)
            record.interval_id = interval_id.id  # response_dict['interval']
        return self._get_notification_message(
            message=f"Subscription Data {response_dict['id']} successfully updated.", message_type='success')
    else:
        return self._get_notification_message(
            message=f"Error, Subscription Data was not retrieved: {response.text}", message_type='danger')


def update_subscription(self):
    if not self.subscription_id:
        notification = self._get_notification_message(message=f'Error, Subscription was not yet created.',
                                                      message_type='danger')
        return notification

    url = f'https://api.mollie.com/v2/customers/{self.customer_id}/subscriptions/{self.subscription_id}'
    headers = {
        "Authorization": f"Bearer {self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')}"}

    data = {
        'amount': {'currency': 'EUR', 'value': f"{self.value:.2f}"},
        'description': self.description
    }

    _logger.info(data)

    response = requests.patch(url, headers=headers, json=data)
    response_dict = response.json()

    _logger.info(response.status_code)
    _logger.info(response.text)

    if response.status_code == 200:
        for record in self:
            # interval_mollie = response_dict['interval'].split(' ')
            # interval_id = self.get_interval_type(response_dict['interval'], interval_mollie=interval_mollie)
            interval_id = self.env.ref('ollo_mollie_integration.mollie_interval_1month')
            record.interval_id = interval_id.id
            record.value = response_dict['amount']['value']
            record.next_payment_date = response_dict['nextPaymentDate']
            record.description = response_dict['description']
        return self._get_notification_message(message=f"Subscription {response_dict['id']} successfully updated.",
                                              message_type='success')
    else:
        return self._get_notification_message(message=f"Error, subscription was not updated: {response.text}",
                                              message_type='danger')


def update_payments(self):
    if not self.subscription_id:
        notification = self._get_notification_message(message=f'Error, Subscription was not yet created.',
                                                      message_type='danger')
        return notification

    url = f'https://api.mollie.com/v2/customers/{self.customer_id}/subscriptions/{self.subscription_id}/payments'
    headers = {
        "Authorization": f"Bearer {self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')}"}

    response = requests.get(url, headers=headers)
    response_dict = response.json()

    _logger.info(response.status_code)
    _logger.info(response.text)

    # check if payment already exists, if yes, only update

    if response.status_code == 200:
        for payment in response_dict['_embedded']['payments']:
            payment_id = self.env['molliesubscriptions.payment'].search([('subscription_id', '=', self.id),
                                                                         ('payment_id', '=', payment['id'])])
            if not payment_id and payment.get('paidAt'):
                payment_id = self.env['molliesubscriptions.payment'].create({
                    'subscription_id': self.id,
                    'payment_id': payment['id'],
                    'created_at': datetime.strptime(payment['createdAt'], '%Y-%m-%dT%H:%M:%S+00:00'),
                    'amount_value': payment['amount']['value'],
                    'amount_currency': payment['amount']['currency'],
                    'method': payment['method'],
                    'status': payment['status'],
                    'paid_at': datetime.strptime(payment['paidAt'], '%Y-%m-%dT%H:%M:%S+00:00'),
                    'amount_refunded_value': payment['amountRefunded']['value'],
                    'amount_refunded_currency': payment['amountRefunded']['currency'],
                    'amount_remaining_value': payment['amountRemaining']['value'],
                    'amount_remaining_currency': payment['amountRemaining']['currency'],
                    'locale': payment['locale'],
                    'profile_id': payment['profileId'],
                    'mandate_id': payment['mandateId'],
                    'sequence_type': payment['sequenceType'],
                    'settlement_amount_value': payment['settlementAmount']['value'],
                    'settlement_amount_currency': payment['settlementAmount']['currency']
                })
        return self._get_notification_message(message=f"Payments successfully updated.", message_type='success')
    else:
        return self._get_notification_message(message=f"Error, payments were not updated: {response.text}",
                                              message_type='danger')


MollieSubscriptionsSubscriptionExt.create_subscription = create_subscription
MollieSubscriptionsSubscriptionExt.update_subscription_data = update_subscription_data
MollieSubscriptionsSubscriptionExt.update_subscription = update_subscription
MollieSubscriptionsSubscriptionExt.update_payments = update_payments


class MollieSubscriptionsSubscription(models.Model):
    _inherit = 'molliesubscriptions.subscription'

    order_id = fields.Many2one('sale.order', string='Sale Order', ondelete='cascade')
    partner_id = fields.Many2one("res.partner")
    customer_id = fields.Char(related='partner_id.mollie_contact_id', store=True)
    picking_id = fields.Many2one('stock.picking', string='Picking', ondelete='cascade')
    interval_id = fields.Many2one('mollie.interval', string='Interval.')

    def get_interval_type(self, name, interval_mollie=[]):
        """
            Get interval for subscription
        """
        interval_id = self.env['mollie.interval'].sudo().search([('display_name', '=', name)], limit=1)
        if interval_id:
            return interval_id
        else:
            if interval_mollie:
                interval_id = self.env['mollie.interval'].create({
                    'name': interval_mollie[0],
                    'interval_type': interval_mollie[1]
                })
                return interval_id

    def cron_create_customer_subscription(self):
        """
            cron for create subscription
        """
        partner = self.env['res.partner'].search([
            ('mollie_mandate_id', '!=', False),
        ])
        if partner:
            for rec in partner:
                rec.create_subscription()
