# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LinkedProductLine(models.Model):
    _name = 'linked.product.line'
    _description = 'Linked Product Line'

    product_linked = fields.Many2one('product.template', string='Produkt')
    product_template_id = fields.Many2one(
        'product.template', string='Produkt Template',
        related='product_id.product_tmpl_id', store=True
    )
    product_qty = fields.Integer('Menge', default=1)
    product_id = fields.Many2one('product.product', string='Produkt Template')
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
