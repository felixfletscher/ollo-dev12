# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.website_sale_subscription.models.product_template import ProductTemplate
import logging

_logger = logging.getLogger(__name__)

class productTemplate(models.Model):
    _inherit = 'product.template'

    linked_product_line = fields.One2many('linked.product.line', 'product_id', string='Verlinkte Produkte')
    is_abo_product = fields.Boolean(string='Is abo Product?')
    is_starting_fees = fields.Boolean(string='Is starting Fees?')


class productProduct(models.Model):
    _inherit = 'product.product'

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
