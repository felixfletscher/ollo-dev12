# -*- coding: utf-8 -*-

from odoo import api
from odoo.addons.sale_subscription.models.sale_order_line import SaleOrderLine as SaleOrderLineSub


@api.depends('product_template_id', 'order_id.recurrence_id', 'order_id.is_abo_source_sale_order')
def _compute_temporal_type(self):
    """Compute the temporal type of the sale order line.

    If the product template of the line is marked as recurring and the sale order has a recurrence and is not
    an ABO source sale order, the temporal type will be set to 'subscription'.
    """
    super(SaleOrderLineSub, self)._compute_temporal_type()
    for line in self:
        if line.product_template_id.recurring_invoice and line.order_id.recurrence_id \
                and not line.order_id.is_abo_source_sale_order:
            line.temporal_type = 'subscription'


SaleOrderLineSub._compute_temporal_type = _compute_temporal_type
