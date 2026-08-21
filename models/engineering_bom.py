# -*- coding: utf-8 -*-
"""Engineering Bill of Materials (material specifications) and lines.

Holds material products with quantity and UoM per project. Lines are
locked (no create/write/unlink) when the parent project state != draft
(FR-014). Material-only: service products are rejected (services
belong on the BoQ).
"""

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class EngineeringBom(models.Model):
    _name = 'engineering.bom'
    _description = 'Engineering Bill of Materials'
    _rec_name = 'name'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    project_id = fields.Many2one(
        'engineering.project', string='Project', required=True, ondelete='cascade',
    )
    line_ids = fields.One2many(
        'engineering.bom.line', 'bom_id', string='Material Lines', copy=True,
    )
    total_standard_cost = fields.Float(
        string='Total Standard Cost', compute='_compute_total_standard_cost',
        store=True, help='Sum of line costs (Standard Cost basis).',
    )
    company_id = fields.Many2one(
        related='project_id.company_id', store=True, string='Company',
    )
    state = fields.Selection(
        related='project_id.state', string='Project State', store=True,
    )

    @api.depends('line_ids', 'line_ids.line_cost')
    def _compute_total_standard_cost(self):
        for bom in self:
            bom.total_standard_cost = sum(bom.line_ids.mapped('line_cost'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('eng.bom')
                vals['name'] = seq or _('BOM/%s/0001' % fields.Date.today().year)
        return super().create(vals_list)


class EngineeringBomLine(models.Model):
    _name = 'engineering.bom.line'
    _description = 'Engineering BoM Line'
    _order = 'id'
    _rec_name = 'product_id'

    bom_id = fields.Many2one(
        'engineering.bom', string='BoM', required=True, ondelete='cascade',
    )
    project_id = fields.Many2one(
        related='bom_id.project_id', store=True, string='Project',
    )
    product_id = fields.Many2one(
        'product.product', string='Product', required=True,
    )
    product_qty = fields.Float(
        string='Quantity', default=1.0, required=True,
    )
    product_uom_id = fields.Many2one(
        'uom.uom', string='Unit of Measure', required=True,
    )
    standard_cost = fields.Float(
        string='Standard Cost', compute='_compute_standard_cost', store=True,
    )
    line_cost = fields.Float(
        string='Line Cost', compute='_compute_line_cost', store=True,
    )

    @api.depends('product_id', 'product_id.standard_price')
    def _compute_standard_cost(self):
        for line in self:
            line.standard_cost = line.product_id.standard_price or 0.0

    @api.depends('product_qty', 'standard_cost')
    def _compute_line_cost(self):
        for line in self:
            line.line_cost = line.product_qty * line.standard_cost

    @api.constrains('product_qty')
    def _check_qty_positive(self):
        for line in self:
            if line.product_qty <= 0:
                raise ValidationError(_(
                    "Quantity must be greater than zero on BoM line %s."
                ) % line.display_name)

    @api.constrains('product_id')
    def _check_product_not_service(self):
        """Material-only: service products belong on the BoQ."""
        for line in self:
            if line.product_id.type == 'service':
                raise UserError(_(
                    "Product %s is a service and cannot be added to a "
                    "Bill of Materials. Service products belong on the "
                    "Bill of Quantities."
                ) % line.product_id.display_name)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_scope_editable()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._check_scope_editable()
        return res

    def unlink(self):
        self._check_scope_editable()
        return super().unlink()

    def _check_scope_editable(self):
        """Delegate to the parent project's lock check (FR-014)."""
        for line in self:
            if line.bom_id and line.bom_id.project_id:
                line.bom_id.project_id._check_scope_editable()