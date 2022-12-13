# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    mollie_contact_id = fields.Char(string='Mollie Contact')
    mollie_mandate_id = fields.Char(string='Mollie Mandate')
