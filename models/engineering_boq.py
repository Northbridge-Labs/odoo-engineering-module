# -*- coding: utf-8 -*-
"""Engineering Bill of Quantities (service scope) and lines.

Holds service products with quantity and UoM per project. Lines are
locked (no create/write/unlink) when the parent project state != draft
(FR-014). Service-only: material products are rejected (materials
belong on the BoM).
"""

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class EngineeringBoq(models.Model):
    _name = 'engineering.boq'
    _description = 'Engineering Bill of Quantities'
    _rec_name = 'name'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    project_id = fields.Many2one(
        'engineering.project', string='Project', required=True, ondelete='cascade',
    )
    line_ids = fields.One2many(
        'engineering.boq.line', 'boq_id', string='Service Lines', copy=True,
    )
    total_standard_cost = fields.Float(
        string='Total Standard Cost', compute='_compute_total_standard_cost',
        store=True, help='Sum of service line costs (Standard Cost basis).',
    )
    company_id = fields.Many2one(
        related='project_id.company_id', store=True, string='Company',
    )
    state = fields.Selection(
        related='project_id.state', string='Project State', store=True,
    )

    @api.depends('line_ids', 'line_ids.line_cost')
    def _compute_total_standard_cost(self):
        for boq in self:
            boq.total_standard_cost = sum(boq.line_ids.mapped('line_cost'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('eng.boq')
                vals['name'] = seq or _('BOQ/%s/0001' % fields.Date.today().year)
        return super().create(vals_list)


class EngineeringBoqLine(models.Model):
    _name = 'engineering.boq.line'
    _description = 'Engineering BoQ Line'
    _order = 'id'
    _rec_name = 'product_id'

    boq_id = fields.Many2one(
        'engineering.boq', string='BoQ', required=True, ondelete='cascade',
    )
    project_id = fields.Many2one(
        related='boq_id.project_id', store=True, string='Project',
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
                    "Quantity must be greater than zero on BoQ line %s."
                ) % line.display_name)

    @api.constrains('product_id')
    def _check_product_is_service(self):
        """Service-only: material products belong on the BoM."""
        for line in self:
            if line.product_id.type != 'service':
                raise UserError(_(
                    "Product %s is not a service and cannot be added to "
                    "a Bill of Quantities. Material products belong on "
                    "the Bill of Materials."
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
            if line.boq_id and line.boq_id.project_id:
                line.boq_id.project_id._check_scope_editable()