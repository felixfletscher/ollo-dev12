# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import requests
from odoo import _, api, models, service
from odoo.exceptions import ValidationError
from werkzeug import urls

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    @api.model
    def _is_tokenization_required(self, sale_order_id=None, **kwargs):
        """ Override of `payment` to force tokenization when paying for a subscription.

        :param int sale_order_id: The sales order to be paid, as a `sale.order` id.
        :return: Whether tokenization is required.
        :rtype: bool
        """
        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id).exists()
            if sale_order.is_subscription or sale_order.subscription_id.is_subscription:
                return False
        return super()._is_tokenization_required(sale_order_id=sale_order_id, **kwargs)

    def _mollie_make_request(self, endpoint, data=None, method='POST'):
        """ Make a request at mollie endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request
        :param dict data: The payload of the request
        :param str method: The HTTP method of the request
        :return The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """
        res = super(PaymentProvider, self)._mollie_make_request(endpoint, data=data, method=method)
        if res and res.get('id', False) and res.get('status', '') and res['status'] == 'paid':
            transaction_id = self.env['payment.transaction'].search([('provider_reference', '=', res.get('id'))],
                                                                    limit=1)
            if transaction_id:
                transaction_id.partner_id.mollie_mandate_id = res.get('mandateId', '')
        return res
