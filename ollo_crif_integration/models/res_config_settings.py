from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    buffer_days = fields.Integer('Buffer Days', config_parameter='ollo_crif_integration.buffer_days')
