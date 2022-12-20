from odoo import models, api, fields, _
import requests
import json
import logging

_logger = logging.getLogger(__name__)
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_abo_picking = fields.Boolean(string='Abo picking')
