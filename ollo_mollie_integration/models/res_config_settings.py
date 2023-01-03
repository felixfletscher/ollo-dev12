# -*- coding: utf-8 -*-
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    buffer_days = fields.Integer('Buffer Days', config_parameter='ollo_mollie_integration.buffer_days')
