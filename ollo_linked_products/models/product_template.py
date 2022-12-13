# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.website_sale_subscription.models.product_template import ProductTemplate
import logging

_logger = logging.getLogger(__name__)


def _get_combination_info(
            self, combination=False, product_id=False, add_qty=1, pricelist=False,
            parent_combination=False, only_template=False
    ):
        """Override to add the information about subscription for recurring products

        If the product is recurring_invoice, this override adds the following information about the subscription :
            - is_subscription: Whether combination create a subscription,
            - subscription_duration: The recurrence duration
            - subscription_unit: The recurrence unit
            - price: The recurring price
        """
        self.ensure_one()

        combination_info = super(ProductTemplate, self)._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty, pricelist=pricelist,
            parent_combination=parent_combination, only_template=only_template
        )
        combination_info.update(is_subscription=False)
        return combination_info


ProductTemplate._get_combination_info = _get_combination_info


class productTemplate(models.Model):
    _inherit = 'product.template'

    linked_product_line = fields.One2many('linked.product.line', 'product_id', string='Verlinkte Produkte')
    is_abo_product = fields.Boolean(string='Is abo Product?')
    is_starting_fees = fields.Boolean(string='Is starting Fees?')

    @api.constrains('linked_product_line')
    def staring_fees_check(self):
        """
        Check starting Fees
        """
        for rec in self:
            is_starting_fees = rec.linked_product_line.filtered(lambda x: x.is_starting_fees)
            if len(is_starting_fees) > 1:
                raise ValidationError('Starting Fees Already Selected.')
