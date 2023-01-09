# -*- coding: utf-8 -*-
import logging

from odoo import models, api, fields
from datetime import datetime, date, timedelta
from dateutil import relativedelta


_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_abo_picking = fields.Boolean(string='Abo picking')
    abo_sale_id = fields.Many2one('sale.order', string='Abo Sale order')
    is_subscription_created = fields.Boolean(string='Subscription Generated', copy=False)
    mollie_subscription_line = fields.One2many('molliesubscriptions.subscription', 'picking_id')

    def action_create_subscription(self):
        """
           Create a subscription using Mollie API.
           The subscription will be based on the order lines in self that are marked as abo products, and the
           amount will be the sum of their subtotals and taxes.
           The subscription will be associated with the partner in self and the order in self.
           The description of the subscription will be "Order Line Name - Order Name".
           The start date of the subscription will be based on the current date, with an additional buffer
           period specified in the ir.config_parameter table.
           The interval for the subscription will be based on the 'ollo_mollie_integration.mollie_interval_1month'
           reference.
           If the request to Mollie API fails, a ValidationError will be raised.
           If the request to Mollie API is successful and the subscription is active, the 'is_subscription_created'
           field on self will be set to True.
        """
        if self.is_abo_picking:
            sale_id = self.abo_sale_id
            interval_id = self.env.ref('ollo_mollie_integration.mollie_interval_1month')
            self.partner_id.sudo().get_customer_payment()
            line_ids = sale_id.order_line.filtered(
                lambda x: x.product_id.linked_product_line.filtered(lambda x: x.is_abo_product))
            buffer_days = self.env['ir.config_parameter'].sudo().get_param('ollo_mollie_integration.buffer_days')
            converted_num = int(buffer_days)
            today = date.today()
            next_invoice_date = today + relativedelta.relativedelta(months=1) + timedelta(converted_num)
            subscription = self.env['molliesubscriptions.subscription'].sudo().create({
                'partner_id': self.partner_id.id,
                'value': sum(line_ids.mapped('price_subtotal')) + sum(line_ids.mapped('price_tax')),
                'description': line_ids.name + ' - ' + sale_id.name,
                'start_date': next_invoice_date,
                'interval_id': interval_id.id,
                'order_id': self.abo_sale_id.id,
                'picking_id': self.id,
            })
            subscription.sudo().create_subscription()
            self.abo_sale_id.next_invoice_date = next_invoice_date
            if subscription and subscription.status == 'active':
                self.is_subscription_created = True

    @api.model
    def cron_delivery_validated_create_subscription(self):
        """Create subscriptions for deliveries that have been validated and are part of an ABO sale.
           This method is intended to be run as a cron job. It searches for stock pickings that meet
           the following criteria:
           - Picking type is 'outgoing'
           - Is an ABO picking (field 'is_abo_picking' is set to True)
           - Has an associated ABO sale (field 'abo_sale_id' is not False)
           - Has not yet had a subscription created for it (field 'is_subscription_created' is False)
           - State is 'done'

           For each of the matching pickings, the method calls the `action_create_subscription` method.
        """
        picking_ids = self.env['stock.picking'].search(
            [('picking_type_code', '=', 'outgoing'), ('is_abo_picking', '=', True), ('abo_sale_id', '!=', False),
             ('is_subscription_created', '=', False), ('state', '=', 'done')])
        for picking in picking_ids:
            picking.action_create_subscription()
