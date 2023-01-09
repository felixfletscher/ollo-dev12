# -*- coding: utf-8 -*-
import logging

from odoo import models, _

_logger = logging.getLogger(__name__)


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def create_returns(self):
        """Creates a new stock picking and sets its ABO sale ID to match the original picking's ABO sale ID.
        Returns:
        dict: An action dictionary for opening the new picking in form, tree, and calendar view.
    """
        res = super(ReturnPicking, self).create_returns()
        picking = self.env['stock.picking'].browse(self._context.get('active_id'))
        if picking.is_abo_picking:
            new_picking = self.env['stock.picking'].browse(res.get('res_id'))
            new_picking.abo_sale_id = picking.abo_sale_id.id
            new_picking.is_abo_picking = True
        return res


    # def create_returns(self):
    #     """Creates a new stock picking and sets its ABO sale ID to match the original picking's ABO sale ID.
    #     Returns:
    #     dict: An action dictionary for opening the new picking in form, tree, and calendar view.
    # """
    #     picking = self.env['stock.picking'].browse(self._context.get('active_id'))
    #     for wizard in self:
    #         new_picking_id, pick_type_id = wizard._create_returns()
    #
    #
    #     # Override the context to disable all the potential filters that could have been set previously
    #     ctx = dict(self.env.context)
    #     ctx.update({
    #         'default_partner_id': self.picking_id.partner_id.id,
    #         'search_default_picking_type_id': pick_type_id,
    #         'search_default_draft': False,
    #         'search_default_assigned': False,
    #         'search_default_confirmed': False,
    #         'search_default_ready': False,
    #         'search_default_planning_issues': False,
    #         'search_default_available': False,
    #     })
    #     return {
    #         'name': _('Returned Picking'),
    #         'view_mode': 'form,tree,calendar',
    #         'res_model': 'stock.picking',
    #         'res_id': new_picking_id,
    #         'type': 'ir.actions.act_window',
    #         'context': ctx,
    #     }