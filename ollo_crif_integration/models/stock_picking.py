# -*- coding: utf-8 -*-
import logging

from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_abo_picking = fields.Boolean(string='Abo picking')
    abo_sale_id = fields.Many2one('sale.order', string='Abo Sale order')
    is_subscription_created = fields.Boolean(string='Subscription Generated', copy=False)
    mollie_subscription_line = fields.One2many('molliesubscriptions.subscription', 'picking_id')

    def action_create_subscription(self):
        """
            create subscription
        """
        products_name = ', '.join(line.product_id.display_name for line in self.move_ids_without_package)
        if self.is_abo_picking:
            sale_id = self.env['sale.order'].search([('name', '=', self.origin)], limit=1)

            next_days = (sale_id.next_invoice_date - fields.Date.today()).days
            next_invoice_days = str(next_days) + ' ' + 'days'
            interval_id = self.env['mollie.interval'].search([('display_name', '=', next_invoice_days)], limit=1)
            if not interval_id:
                interval_id = self.env['mollie.interval'].create({
                    'name': str(next_days),
                    'interval_type': 'days'
                })

            if sale_id:
                line_ids = sale_id.order_line.filtered(lambda x: not x.is_starting_fees)
                subscription = self.env['molliesubscriptions.subscription'].sudo().create({
                    'partner_id': self.partner_id.id,
                    'value': sum(line_ids.mapped('price_subtotal')) + sum(line_ids.mapped('price_tax')),
                    'description': products_name,
                    'start_date': fields.Date.today(),
                    'interval_id': interval_id.id,
                    'order_id': sale_id.id,
                    'picking_id': self.id,
                })
                subscription.sudo().create_subscription()
                if subscription and subscription.status == 'active':
                    self.is_subscription_created = True

    @api.model
    def cron_delivery_validated_create_subscription(self):
        """
            cron for create subscription
        """
        picking_ids = self.env['stock.picking'].search([('picking_type_code', '=', 'outgoing'),
                                                        ('is_abo_picking', '=', True),
                                                        ('sale_id', '!=', False),
                                                        ('is_subscription_created', '=', False),
                                                        ('state', '=', 'done')])
        for picking in picking_ids:
            picking.action_create_subscription()
