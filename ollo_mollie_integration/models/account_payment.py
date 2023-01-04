# -*- coding: utf-8 -*-

import json
import logging

from odoo import models, api, fields, _
from odoo.addons.ollo_mollie_integration.models.mollie import send_mollie_request
from odoo.addons.payment_mollie.const import SUPPORTED_LOCALES
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    mollie_transaction = fields.Char(string='Mollie Transaction', copy=False)
    mollie_payment_method = fields.Char(string='Mollie Payment Method', copy=False)
