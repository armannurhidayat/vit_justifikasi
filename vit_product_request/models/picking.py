from odoo import api, fields, models, _
import time
from collections import namedtuple
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class picking(models.Model):
    _name = 'stock.picking'
    _inherit = 'stock.picking'

    department_id = fields.Many2one(comodel_name="hr.department", string="Department", copy=False, )
    request_id = fields.Many2one(comodel_name="vit.new.product.request", string="Request", copy=False, )





