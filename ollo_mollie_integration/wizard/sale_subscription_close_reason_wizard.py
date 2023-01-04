# -*- coding: utf-8 -*-

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SaleSubscriptionCloseReasonWizard(models.TransientModel):
    _inherit = 'sale.subscription.close.reason.wizard'

    def set_close(self):
        res = super().set_close()
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        for subscription in sale_order.mollie_subscription_line:
            subscription.cancel_subscription()
        return res



