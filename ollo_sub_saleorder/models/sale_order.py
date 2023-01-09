# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons.sale_subscription.models.sale_order import SaleOrder as SaleOrderSub
from odoo.exceptions import UserError
from odoo.fields import Command


@api.constrains('recurrence_id', 'state', 'is_subscription', 'is_abo_source_sale_order')
def _constraint_subscription_recurrence(self):
    """Enforce constraints on subscriptions in a sale order.

    A sale order with a recurring product must have a recurrence set, and a sale order
    with a recurrence must have at least one recurring product in its order lines.
    """
    recurring_product_orders = self.order_line.filtered(lambda l: l.product_id.recurring_invoice).order_id
    for so in self:
        if so.state in ['draft', 'cancel'] or so.subscription_management == 'upsell':
            continue
        if so in recurring_product_orders and not so.is_abo_source_sale_order and not so.recurrence_id:
            raise UserError(_('You cannot save a sale order with recurring product and no recurrence.'))
        if so.recurrence_id and so.order_line and so not in recurring_product_orders and not so.is_abo_source_sale_order:
            raise UserError(_('You cannot save a sale order with a recurrence and no recurring product.'))


SaleOrderSub._constraint_subscription_recurrence = _constraint_subscription_recurrence


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sub_sale_order_ids = fields.Many2many('sale.order', 'sale_order_sub_sale_order_rel', 'sale_order_id',
                                          'sub_sale_order_id', string='Sub sale Order', copy=False)
    is_abo_source_sale_order = fields.Boolean('Abo Source sale order', copy=False, )
    is_abo_sub_sale_order = fields.Boolean('Abo Sub sale order', copy=False, )
    # abo_sub_sale_order_ids = fields.Many2many('sale.order', 'abo_sub_sale_order_sale_order_rel', 'abo_sub_order_id',
    #                                           'order_id', string='Abo Sub Sale order', copy=False)
    subsale_order_count = fields.Integer(string='Sub sale order ', compute='_compute_subsale_order_count')
    source_sale_order_count = fields.Integer(string='Source sale order ', compute='_compute_source_sale_order_count')

    def _compute_subsale_order_count(self):
        """
            count sub sale order count
        """
        for rec in self:
            rec.subsale_order_count = len(rec.sub_sale_order_ids)

    def _compute_source_sale_order_count(self):
        """
            count subsale order count
        """
        for rec in self:
            rec.source_sale_order_count = self.search_count(
                [('sub_sale_order_ids', 'in', self.ids), ('is_abo_source_sale_order', '=', True)])

    @api.depends('recurrence_id', 'subscription_management', 'is_abo_source_sale_order')
    def _compute_is_subscription(self):
        """Compute the `is_subscription` field for sale orders.

        The `is_subscription` field is set to True if the sale order has a recurrence set
        and is not an upsell or an abo source sale order. Otherwise, it is set to False.
        """
        super(SaleOrder, self)._compute_is_subscription()
        for order in self:
            if not order.recurrence_id or order.subscription_management == 'upsell':
                order.is_subscription = False
                continue
            if not order.is_abo_source_sale_order:
                order.is_subscription = True
            else:
                order.is_subscription = False

    def update_source_sale_order(self):
        """Update the abo source sale order when a new subscription sale order is created.

        This function resets the `subscription_management` field and sets the stage to
        the `Draft` stage for the abo source sale order.
        """
        for rec in self:
            if rec.is_abo_source_sale_order:
                rec.write({
                    'subscription_management': '',
                    'next_invoice_date': fields.Date.today(),
                    'stage_id': self.env.ref('sale_subscription.sale_subscription_stage_draft').id,
                })

    def _create_sub_sale_order(self, line):
        """Create a new subscription sale order from the given line.

        The new sale order is created with the same partner, invoice, shipping, date,
        pricelist, payment term, user, team, website, and company as the current sale
        order, and with a recurrence set to monthly. The given line is added to the
        new sale order as a new order line. The new sale order is then confirmed, and
        the `sub_sale_order_ids` field of the current sale order is updated with a link
        to the new sale order. The `update_source_sale_order` function is then called
        to update the abo source sale order.
        """
        order_id = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'partner_invoice_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'date_order': self.date_order,
            'pricelist_id': self.pricelist_id.id,
            'payment_term_id': self.payment_term_id.id,
            'user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'website_id': self.website_id.id,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'recurrence_id': self.env.ref('sale_temporal.recurrence_monthly').id,
            'is_subscription': True,
            'is_abo_source_sale_order': False,
        })
        line_id = self.env['sale.order.line'].with_context(skip_starting_fees=True).create({
            'product_id': line.product_id.id,
            'product_uom_qty': line.product_uom_qty,
            'price_unit': line.price_unit,
            'product_uom': line.product_uom.id,
            'discount': line.discount,
            'tax_id': [Command.link(tax.id) for tax in line.tax_id] if line.tax_id else [],
            'order_id': order_id.id
        })
        order_id.action_confirm()
        self.sub_sale_order_ids = [Command.link(order_id.id)]
        self.update_source_sale_order()

    def action_confirm(self):
        """Confirm the sale order and create any necessary subscription sale orders.

        If the sale order has any order lines with the `is_starting_fees` field set to
        True, the `is_abo_source_sale_order` field is set to True. If the sale order
        has the `is_abo_source_sale_order` field set to True, a new subscription sale
        order is created for each order line with a product that has an ABO product line
        with the `is_abo_product` field set to True, using the `_create_sub_sale_order`
        function.
        """
        res = super().action_confirm()
        if self.order_line.filtered(lambda x: x.is_starting_fees):
            self.is_abo_source_sale_order = True
        if self.is_abo_source_sale_order:
            for line in self.order_line.filtered(
                    lambda x: x.product_id.linked_product_line.filtered(lambda x: x.is_abo_product)):
                self._create_sub_sale_order(line)
        return res

    def action_open_subsale_order(self):
        """Open a window to view the subscription sale orders of the current sale order.

        The window will contain a list and form view of the subscription sale orders,
        and will only show sale orders with the `is_subscription` field set to True.
        """
        self.ensure_one()
        if self.sub_sale_order_ids:
            view_id_list = self.env.ref('sale_subscription.sale_subscription_view_tree').id
            view_id_form = self.env.ref('sale_subscription.sale_subscription_primary_form_view').id
            return {
                'type': 'ir.actions.act_window',
                'name': _('Odoo Subscription'),
                'res_model': 'sale.order',
                'target': 'current',
                'domain': [('id', 'in', self.sub_sale_order_ids.ids), ('is_subscription', '=', True)],
                'views': [[view_id_list, 'list'], [view_id_form, 'form']],
                'context': {'default_is_subscription': 1}
            }

    def action_open_source_sale_order(self):
        """Open a window to view the abo source sale order of the current sale order.

        The window will contain a list and form view of the abo source sale order,
        and will only show sale orders with the `is_abo_source_sale_order` field set to True
        and with the current sale order in their `sub_sale_order_ids` field.
        """
        self.ensure_one()
        view_id_list = self.env.ref('sale.view_order_tree').id
        view_id_form = self.env.ref('sale.view_order_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Source Subscription'),
            'res_model': 'sale.order',
            'target': 'current',
            'domain': [('sub_sale_order_ids', 'in', self.ids), ('is_abo_source_sale_order', '=', True)],
            'views': [[view_id_list, 'list'], [view_id_form, 'form']],
        }

    def action_view_subscription(self):
        """Open a window to view the Mollie subscriptions of the current sale order.

        If the sale order is not an ABO source sale order, a window with a tree and form
        view of the Mollie subscriptions will be opened, and will only show subscriptions
        with a matching `order_id` field to the current sale order.
        """
        if not self.is_abo_source_sale_order:
            action = {
                'name': 'Mollie Subscription',
                'view_mode': 'tree,form',
                'res_model': 'molliesubscriptions.subscription',
                'type': 'ir.actions.act_window',
                'domain': [('order_id', '=', self.id)]
            }
            return action

    def action_create_delivery(self):
        """
            create abbo product delivery
        """
        for rec in self:
            abo_delivery_count = self.env['stock.picking'].sudo().search_count(
                [('abo_sale_id', '=', rec.id), ('is_abo_picking', '=', True), ('state', '!=', 'cancel')])
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
            'state': 'assigned',
            'abo_sale_id': self.id,
        })
        # self.write({'picking_ids': [(4, picking.id)]})

    def action_view_abo_delivery(self):
        """Open a window to view the ABO deliveries of the current sale order.

        A window with a tree and form view of the stock pickings will be opened,
        and will only show pickings with a matching `abo_sale_id` field to the current
        sale order and with the `is_abo_picking` field set to True.
        """
        self.ensure_one()
        action = {
            'name': 'Abo Delivery',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'domain': [('abo_sale_id', '=', self.id), ('is_abo_picking', '=', True)]
        }
        return action
