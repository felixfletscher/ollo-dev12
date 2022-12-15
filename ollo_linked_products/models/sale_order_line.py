# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_starting_fees = fields.Boolean('Starting Fess', default=False)
    starting_fees_line_id = fields.Many2one("sale.order.line", "Starting Product Line")

    def _is_not_sellable_line(self):
        return self.is_starting_fees or super(SaleOrderLine, self)._is_not_sellable_line()

    @api.depends('product_id.display_name')
    def _compute_name_short(self):
        """ If the sale order line concerns a ticket, we don't want the product name, but the ticket name instead.
        """
        super(SaleOrderLine, self)._compute_name_short()

        for record in self:
            if record.is_starting_fees:
                record.name_short = record.name

    @api.model_create_multi
    def create(self, vals):
        """
            Super Create with Multi add linked product to order line
        """
        res = super(SaleOrderLine, self).create(vals)
        for linked_product in res.product_id.linked_product_line.filtered(lambda x: x.is_starting_fees):
            line_id = self.env['sale.order.line'].sudo().create({
                'product_uom_qty': linked_product.product_qty * res.product_uom_qty,
                'product_id': linked_product.product_linked.product_variant_id.id,
                'name': linked_product.product_linked.display_name + '(' + res.name + ')',
                'order_id': res.order_id.id,
                'is_starting_fees': True,
            })
            res.starting_fees_line_id = line_id.id
        return res

    def write(self, vals):
        """
            Super Write with update(qty) linked product to order line
        """
        res = super(SaleOrderLine, self).write(vals)
        if 'product_uom_qty' in vals:
            for rec in self:
                pact = self.env['product.product'].sudo().browse(rec.product_id.id)
                for linked_product in pact.linked_product_line.filtered(lambda x: x.is_starting_fees):
                    if rec.starting_fees_line_id:
                        rec.starting_fees_line_id.product_uom_qty = linked_product.product_qty * rec.product_uom_qty
                    else:
                        line_id = self.env['sale.order.line'].sudo().create({
                            'product_uom_qty': linked_product.product_qty * rec.product_uom_qty,
                            'product_id': linked_product.product_linked.product_variant_id.id,
                            'name': linked_product.product_linked.display_name + '(' + rec.name + ')',
                            'order_id': rec.order_id.id,
                            'is_starting_fees': True,
                        })
                        rec.starting_fees_line_id = line_id.id
        return res

    def unlink(self):
        for rec in self:
            if rec.starting_fees_line_id:
                rec.starting_fees_line_id.unlink()
        return super(SaleOrderLine, self).unlink()
