# -*- coding: utf-8 -*-
"""Engineering Manufacturing Order extensions.

Contains:
- engineering.mo.service.line: non-stock work lines for BoQ services
  attached to an MO (FR-011). Tracked separately from mrp.bom.line
  components (which are stockable materials).
- mrp.production extension: adds engineering_service_line_ids One2many
  and engineering_project_id back-link.
"""

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class EngineeringMoServiceLine(models.Model):
    _name = 'engineering.mo.service.line'
    _description = 'Engineering MO Service Line'
    _order = 'id'
    _rec_name = 'product_id'

    production_id = fields.Many2one(
        'mrp.production', string='Manufacturing Order',
        required=True, ondelete='cascade',
    )
    boq_line_id = fields.Many2one(
        'engineering.boq.line', string='Source BoQ Line',
        copy=False,
    )
    product_id = fields.Many2one(
        'product.product', string='Service Product', required=True,
    )
    product_qty = fields.Float(
        string='Quantity', default=1.0, required=True,
    )
    product_uom_id = fields.Many2one(
        'uom.uom', string='Unit of Measure', required=True,
    )
    state = fields.Selection(
        [('to_do', 'To Do'), ('done', 'Done')],
        string='State', default='to_do', required=True, copy=False,
    )


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    engineering_service_line_ids = fields.One2many(
        'engineering.mo.service.line', 'production_id',
        string='Engineering Service Lines',
    )
    engineering_project_id = fields.Many2one(
        'engineering.project', string='Engineering Project', copy=False,
    )