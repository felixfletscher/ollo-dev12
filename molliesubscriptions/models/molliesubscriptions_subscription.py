
import logging
import requests
import json
from datetime import datetime

from odoo import _, api, fields, models


_logger = logging.getLogger(__name__)



class MollieSubscriptionsSubscription(models.Model):
    _name = 'molliesubscriptions.subscription'
    _description = 'Mollie Subscriptions'
    _rec_name = 'subscription_id'

    # Mollie Required
    customer_id = fields.Char(string='Customer ID', required=True)
    value = fields.Float(string='Amount', required=True)
    interval = fields.Selection(
        selection=[('1 month', 'monthly')], required=True, default='1 month'
    )
    description = fields.Char(string='Description', required=True)
    
    # Mollie Optional
    start_date = fields.Date(string='Start Date', default=datetime.today())

    # Readonly
    subscription_id = fields.Char(string='Subscription ID', readonly = True, copy=False)
    status = fields.Char(string='Status', readonly = True, copy=False)
    next_payment_date = fields.Date(string='Next Payment Date', readonly = True, copy=False)
    
    mollie_created_at = fields.Datetime(string='Created at', readonly = True, copy=False)
    mollie_canceled_at = fields.Datetime(string='Canceled at', readonly = True, copy=False)

    payment_ids = fields.One2many("molliesubscriptions.payment", "subscription_id", string="Payments")

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


    def test_api_key(self):
        return


    # https://docs.mollie.com/reference/v2/subscriptions-api/create-subscription
    def create_subscription(self):

        if self.subscription_id:
            notification = self._get_notification_message(message=f'Error, Subscription already created: {self.subscription_id}', message_type='error')
            return notification

        url = f'https://api.mollie.com/v2/customers/{self.customer_id}/subscriptions'
        headers = {"Authorization": f"Bearer {self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')}"}
        
        # Required
        data = {
            'amount': {'currency': 'EUR', 'value': f"{self.value:.2f}"},
            'interval': self.interval,
            'description': self.description
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
            return self._get_notification_message(message=f"Subscription {response_dict['id']} successfully created.", message_type='success')
        else:
            return self._get_notification_message(message=f"Error, subscription was not created: {response.text}", message_type='error')


    # https://docs.mollie.com/reference/v2/subscriptions-api/get-subscription
    def update_subscription_data(self):

        if not self.subscription_id:
            notification = self._get_notification_message(message=f'Error, Subscription was not yet created.', message_type='error')
            return notification

        url = f'https://api.mollie.com/v2/customers/{self.customer_id}/subscriptions/{self.subscription_id}'
        headers = {"Authorization": f"Bearer {self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')}"}
        
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
                    record.mollie_canceled_at = datetime.strptime(response_dict['canceledAt'], '%Y-%m-%dT%H:%M:%S+00:00')

                record.interval = response_dict['interval']
            return self._get_notification_message(message=f"Subscription Data {response_dict['id']} successfully updated.", message_type='success')
        else:
            return self._get_notification_message(message=f"Error, Subscription Data was not retrieved: {response.text}", message_type='error')


    # https://docs.mollie.com/reference/v2/subscriptions-api/update-subscription
    def update_subscription(self):

        if not self.subscription_id:
            notification = self._get_notification_message(message=f'Error, Subscription was not yet created.', message_type='error')
            return notification

        url = f'https://api.mollie.com/v2/customers/{self.customer_id}/subscriptions/{self.subscription_id}'
        headers = {"Authorization": f"Bearer {self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')}"}

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
                record.interval = response_dict['interval']
                record.value = response_dict['amount']['value']
                record.next_payment_date = response_dict['nextPaymentDate']
                record.description = response_dict['description']
            return self._get_notification_message(message=f"Subscription {response_dict['id']} successfully updated.", message_type='success')
        else:
            return self._get_notification_message(message=f"Error, subscription was not updated: {response.text}", message_type='error')


    # https://docs.mollie.com/reference/v2/subscriptions-api/cancel-subscription
    def cancel_subscription(self):

        if not self.subscription_id:
            notification = self._get_notification_message(message=f'Error, Subscription was not yet created.', message_type='error')
            return notification

        if self.status == 'canceled':
            notification = self._get_notification_message(message=f'Error, Subscription was already canceled.', message_type='error')
            return notification

        url = f'https://api.mollie.com/v2/customers/{self.customer_id}/subscriptions/{self.subscription_id}'
        headers = {"Authorization": f"Bearer {self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')}"}

        response = requests.delete(url, headers=headers)
        response_dict = response.json()

        _logger.info(response.status_code)
        _logger.info(response.text)

        if response.status_code == 200:
            for record in self:
                record.status = response_dict['status']
                record.mollie_canceled_at = datetime.strptime(response_dict['canceledAt'], '%Y-%m-%dT%H:%M:%S+00:00')
            return self._get_notification_message(message=f"Subscription {response_dict['id']} successfully canceled.", message_type='success')
        else:
            return self._get_notification_message(message=f"Error, subscription was not canceled: {response.text}", message_type='error')

    # https://docs.mollie.com/reference/v2/subscriptions-api/list-subscription-payments
    def update_payments(self):

        if not self.subscription_id:
            notification = self._get_notification_message(message=f'Error, Subscription was not yet created.', message_type='error')
            return notification

        url = f'https://api.mollie.com/v2/customers/{self.customer_id}/subscriptions/{self.subscription_id}/payments'
        headers = {"Authorization": f"Bearer {self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')}"}

        response = requests.get(url, headers=headers)
        response_dict = response.json()

        _logger.info(response.status_code)
        _logger.info(response.text)

        # check if payment already exists, if yes, only update

        if response.status_code == 200:
            for payment in response_dict['_embedded']['payments']:
                self.env['molliesubscriptions.payment'].create({
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
            return self._get_notification_message(message=f"Error, payments were not updated: {response.text}", message_type='error')


    # https://docs.mollie.com/reference/v2/mandates-api/create-mandate
    # https://docs.mollie.com/payments/recurring#payments-recurring-first-payment
    def update_payment_method(self):

        if not self.subscription_id:
            notification = self._get_notification_message(message=f'Error, Subscription was not yet created.', message_type='error')
            return notification

        # Create new payment
        url = 'https://api.mollie.com/v2/payments'
        headers = {"Authorization": f"Bearer {self.env['ir.config_parameter'].sudo().get_param('molliesubscriptions.mollie_api_key')}"}

        data = {
            "amount": {
                "currency": "EUR",
                # For some Payment Methods, value can't be 0.00, 1.00 works for all used payment methods
                "value": "1.00"
            },
            "customerId": self.customer_id,
            "sequenceType": "first",
            "description": "Payment Method Change",
            # create url for success/error message to customer
            "redirectUrl": "https://www.ollo.de",
            # create a odoo webhook url (controller?), that is called by mollie after the customer finished first payment
            "webhookUrl": "https://webhook-odoo.ollo.de",
            "metadata": {
                "serialnumber": "SN1234"
            }
        }

        _logger.info(data)

        response = requests.post(url, headers=headers, json=data)
        response_dict = response.json()

        _logger.info(response.status_code)
        _logger.info(response.text)

        if response.status_code == 201:
            # get url of mollie checkout and redirect customer to that url
            checkout_url = response_dict['_links']['checkout']['href']

            # https://www.odoo.com/documentation/16.0/developer/reference/backend/actions.html#url-actions-ir-actions-act-url
            return {                  
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': checkout_url
            }

        else:
            return self._get_notification_message(message=f"Error, first payment can't be created: {response.text}", message_type='error')

    
        # possibly write function that is used with the data from the webhook url