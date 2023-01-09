# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_starting_fees = fields.Boolean('Starting Fess', default=False)
    starting_fees_line_id = fields.Many2one("sale.order.line", "Starting Product Line")

    def _is_not_sellable_line(self):
        """Determine if the sale order line is not sellable.

        A line is considered not sellable if it is a starting fee line or if it is not sellable
         according to the base implementation.
        """
        return self.is_starting_fees or super(SaleOrderLine, self)._is_not_sellable_line()

    @api.depends('product_id.display_name')
    def _compute_name_short(self):
        """Compute the short name for the sale order line.

        If the sale order line concerns a ticket, the short name will be the ticket name instead of the product name.
        """
        super(SaleOrderLine, self)._compute_name_short()
        for record in self:
            if record.is_starting_fees:
                record.name_short = record.name

    @api.model_create_multi
    def create(self, vals):
        """Create sale order lines and add linked products if necessary.

        If a linked product is marked as a starting fee, it will be added to the sale order line as a separate line.
        """
        res = super(SaleOrderLine, self).create(vals)
        for line in res:
            if not self._context.get('skip_starting_fees', False):
                pact = self.env['product.product'].sudo().browse(line.product_id.id)
                for linked_product in pact.linked_product_line.filtered(lambda x: x.is_starting_fees):
                    if line.starting_fees_line_id:
                        line.starting_fees_line_id.product_uom_qty = linked_product.product_qty * line.product_uom_qty
                    else:
                        line_id = self.env['sale.order.line'].sudo().create({
                            'product_uom_qty': linked_product.product_qty * line.product_uom_qty,
                            'product_id': linked_product.product_linked.product_variant_id.id,
                            'name': linked_product.product_linked.display_name + '(' + line.name + ')',
                            'order_id': line.order_id.id,
                            'is_starting_fees': True,
                        })
                        line.starting_fees_line_id = line_id.id
        return res

    def write(self, vals):
        """
        Update the values of the `SaleOrderLine` record.

        Args:
            vals (dict): A dictionary containing the field names and new values to update.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        res = super(SaleOrderLine, self).write(vals)
        if 'product_uom_qty' in vals and not self._context.get('skip_starting_fees', False):
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
        """
        Delete the `SaleOrderLine` records from the database.

        If the record has a `starting_fees_line_id`, it will also be deleted.

        Returns:
            bool: True if the delete was successful, False otherwise.
        """
        for rec in self:
            if rec.starting_fees_line_id:
                rec.starting_fees_line_id.unlink()
        return super(SaleOrderLine, self).unlink()
