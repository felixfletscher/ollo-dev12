# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class MollieInterval(models.Model):
    _name = 'mollie.interval'
    _description = 'Mollie Interval'
    _rec_name = 'display_name'

    name = fields.Char('No.')
    interval_type = fields.Selection([('months', 'Months'), ('weeks', 'Weeks'), ('days', 'Days')],
                                     default='months', string='Interval Type')
    display_name = fields.Char(string='Display Name', compute="compute_display_name", store=True)

    @api.depends('name', 'interval_type')
    def compute_display_name(self):
        """
            Compute on Display name
        """
        for rec in self:
            rec.display_name = rec.name + ' ' + rec.interval_type
