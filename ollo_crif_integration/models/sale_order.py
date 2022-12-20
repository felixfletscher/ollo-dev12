from odoo import models, api, fields, _
import requests
import json
import logging

_logger = logging.getLogger(__name__)
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    abo_delivery_count = fields.Integer(compute="compute_abo_delivery", copy=False, default=0)
    is_starting_fees = fields.Boolean('Starting Fess', default=False)
    mollie_subscription_id = fields.Char('Mollie Subscription id')
    cirf_result = fields.Selection([
        ('normal', 'Normal'),
        ('done', 'Success'),
        ('blocked', 'Fail')], string='CIRF result', default='normal')

    def action_create_delivery(self):
        for rec in self:
            abo_delivery_count = self.env['stock.picking'].sudo().search_count(
                [('sale_id', '=', rec.id,), ('is_abo_picking', '=', True), ('state', '!=', 'cancel')])
            if abo_delivery_count == 0:
                stock_move = self.env['stock.move']
                # Create an empty list to store stock moves
                product_list = []
                # Find the default picking type for outgoing shipments
                picking_type_id = self.env['stock.picking.type'].sudo().search(
                    [('code', '=', 'outgoing'), ('company_id', '=', self.company_id.id)], limit=1)
                # Loop through the order lines
                for rec in self.order_line:
                    # Loop through the linked products of the current order line product
                    for record in rec.product_id.linked_product_line.filtered(lambda x: x.is_abo_product):
                        # Create a stock move for the current linked product
                        move_vals = {
                            'product_id': record.product_variant_id.id,
                            'product_uom_qty': record.product_qty * rec.product_uom_qty,
                            'location_id': picking_type_id.default_location_src_id.id,
                            'name': _('Auto processed move : %s') % record.product_variant_id.display_name,
                            'location_dest_id': self.env.ref('stock.stock_location_customers').sudo().id
                        }
                        values = stock_move.create(move_vals)
                        # Add the created stock move to the product list
                        product_list.append(values.id)
                # If there are any products in the list, create a picking for them
                if product_list:
                    self.create_picking(product_list)

    def create_picking(self, product_list):
        """This static method will confirm the sale
         order and this will also validate the picking"""
        picking_type_id = self.env['stock.picking.type'].sudo().search(
            [('code', '=', 'outgoing'), ('company_id', '=', self.company_id.id)], limit=1)
        picking = self.env['stock.picking'].sudo().create({
            'is_abo_picking': True,
            'location_dest_id': self.env.ref('stock.stock_location_customers').sudo().id,
            'location_id': picking_type_id.default_location_src_id.id,
            'move_ids_without_package': [(6, 0, product_list)],
            'move_type': 'direct',
            'origin': self.name,
            'partner_id': self.partner_id.id,
            'picking_type_id': picking_type_id.id,
            'sale_id': self.id,
            'state': 'assigned',
        })

        self.write({'picking_ids': [(4, picking.id)]})

    # abo view abo delivery
    def action_view_abo_delivery(self):
        action = {
            'name': 'Abo Delivery',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'domain': [('sale_id', '=', self.id), ('is_abo_picking', '=', True)]
        }
        return action

    # abo delivery count
    def compute_abo_delivery(self):
        for rec in self:
            abo_delivery_count = self.env['stock.picking'].sudo().search_count(
                [('sale_id', '=', self.id,), ('is_abo_picking', '=', True)])
            rec.abo_delivery_count = abo_delivery_count

    # override base method for hide abo delivery
    def action_view_delivery(self):
        return self._get_action_view_picking(self.picking_ids.filtered(lambda picking: not picking.is_abo_picking))

    def action_create_mollib_subscription(self):
        pass

    def action_create_refund(self):
        pass

    def action_run_crif_check(self):
        pass

    def action_update_mollib_subscription(self):
        pass

    def action_end_mollib_subscription(self):
        pass

    # override base method for hide abo delivery count
    @api.depends('picking_ids')
    def _compute_picking_ids(self):
        for order in self:
            order.delivery_count = len(order.picking_ids.filtered(lambda picking: not picking.is_abo_picking))
