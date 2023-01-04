# -*- coding: utf-8 -*-
import logging
from werkzeug import urls
import pprint
from odoo.addons.ollo_mollie_integration.models.mollie import send_mollie_request
from odoo.exceptions import ValidationError
from odoo import fields, models

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    mollie_payment_method = fields.Char(string='Mollie Payment Method')
    customer_account = fields.Char(string='Mollie Customer Account')
    paypal_agreement = fields.Char(string='Mollie Paypal')
    card_number = fields.Char(string='Mollie Customer card')
    customer_bic = fields.Char(string='Mollie Customer BIC')

    def _mollie_prepare_payment_request_payload(self):
        """
            create customer in mollie while checkout from shop
        """
        res = super(PaymentTransaction, self)._mollie_prepare_payment_request_payload()
        order_lines = self.sale_order_ids.mapped('order_line')
        abo_product_line = order_lines.filtered(
            lambda x: x.product_id.linked_product_line.filtered(lambda x: x.is_abo_product))
        if abo_product_line:
            self.partner_id.sudo()._create_customer()
            res.update({
                "customerId": self.partner_id.mollie_contact_id,
                "sequenceType": "first",
                # 'method': 'paypal'
            })
        return res

    def _create_payment(self, **extra_create_values):
        """
            Pass provider Ref to account.payment
        """
        res = super(PaymentTransaction, self)._create_payment(**extra_create_values)
        res.write({
            'mollie_transaction': self.provider_reference,
            'mollie_payment_method': self.mollie_payment_method
        })
        return res
