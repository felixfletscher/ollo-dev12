# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)


class SaleOrderTemplateLine(models.Model):
    _inherit = 'sale.order.template.line'

    @api.model_create_multi
    def create(self, vals):
        """
            Super Create with Multi add linked product to template line
        """
        res = super(SaleOrderTemplateLine, self).create(vals)
        if res.product_id:
            pact = self.env['product.product'].browse(res.product_id.id)
            for linked_product in pact.linked_product_line:
                self.env['sale.order.template.line'].create({
                    'product_uom_qty': linked_product.product_qty * res.product_uom_qty,
                    'product_id': linked_product.product_linked.product_variant_id.id,
                    'name': linked_product.product_linked.display_name,
                    'sale_order_template_id': res.sale_order_template_id.id
                })
        return res

    def write(self, vals):
        """
            Super Write with update(qty) linked product to template line
        """
        res = super(SaleOrderTemplateLine, self).write(vals)
        if 'product_uom_qty' in vals:
            pact = self.env['product.product'].browse(self.product_id.id)
            for linked_product in pact.linked_product_line:
                quotation_template_id = self.env['sale.order.template.line'].search([
                    ('product_id', '=', linked_product.product_linked.product_variant_id.id),
                    ('sale_order_template_id', '=', self.sale_order_template_id.id)
                ], limit=1)
                if quotation_template_id:
                    quotation_template_id.product_uom_qty = linked_product.product_qty * self.product_uom_qty
                else:
                    self.env['sale.order.template.line'].create({
                        'product_uom_qty': linked_product.product_qty * self.product_uom_qty,
                        'product_id': linked_product.product_linked.product_variant_id.id,
                        'name': linked_product.product_linked.display_name,
                        'sale_order_template_id': self.sale_order_template_id.id
                    })
        return res

