# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _mollie_prepare_payment_request_payload(self):
        res = super(PaymentTransaction, self)._mollie_prepare_payment_request_payload()
        order_lines = self.sale_order_ids.mapped('order_line')
        abo_product_line = order_lines.filtered(
            lambda x: x.product_id.linked_product_line.filtered(lambda x: x.is_abo_product))
        if abo_product_line:
            self.partner_id.sudo()._create_customer()
            res.update({
                "customerId": self.partner_id.mollie_contact_id,
                "sequenceType": "first",
            })
        return res
