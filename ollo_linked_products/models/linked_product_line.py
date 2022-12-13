# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class LinkedProductLine(models.Model):
    _name = 'linked.product.line'
    _description = 'Linked Product Line'

    product_linked = fields.Many2one('product.template', string='Produkt')
    product_qty = fields.Integer('Menge', default=1)
    product_id = fields.Many2one('product.template', string='Produkt Template')
    product_variant_id = fields.Many2one('product.product', string='Produkt Variant')
    is_abo_product = fields.Boolean(string='Is abo Product?')
    is_starting_fees = fields.Boolean(string='Is starting Fees?')

    @api.onchange('product_linked', 'product_variant_id')
    def _onchange_product_linked(self):
        res = {
            'domain': {
                'product_variant_id': [('id', 'in', self.product_linked.product_variant_ids.ids)]
            }
        }
        return res

    # @api.onchange('is_starting_fees')
    # def _onchange_starting_fees(self):
    #     if self.product_id.is_starting_fees:
    #         raise ValidationError('Starting Fees Already Selected.')

    # @api.constrains('is_starting_fees')
    # def staring_fees_check(self):
    #     """
    #     Check starting Fees
    #     """
    #     if self.search_count([('is_starting_fees', '=', True)]) > 1:
    #         raise ValidationError('Starting Fees Already Selected.')
    #
    # @api.onchange('is_starting_fees')
    # def make_abo(self):
    #     if self.is_starting_fees:
    #         self.is_abo_product = False
