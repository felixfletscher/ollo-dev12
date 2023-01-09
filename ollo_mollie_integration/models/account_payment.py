# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    mollie_transaction = fields.Char(string='Mollie Transaction', copy=False)
    mollie_payment_method = fields.Char(string='Mollie Payment Method', copy=False)
