# -*- coding: utf-8 -*-
"""Engineering Quotation: extends sale.order.

Adds engineering-specific fields and behavior to sale.order:
- engineering_project_id: back-link to the engineering scope.
- internal_cost: sum of linked BoM + BoQ Standard Costs (FR-005).
- markup_percent: commercial-entered percentage (FR-006).
- final_estimate_price: internal_cost * (1 + markup/100) (FR-006).
- _compute_internal_cost raises a warning if any line product has
  standard_price == 0 (FR-015).
- The sale.order carries exactly ONE summary sale.order.line for the
  shared "Engineering Project" product (R14); no per-product BoM/BoQ
  detail is written to sale.order.line (SC-003 structural non-exposure).
"""

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    engineering_project_id = fields.Many2one(
        'engineering.project', string='Engineering Project',
        readonly=True, copy=False,
    )
    internal_cost = fields.Float(
        string='Internal Cost', compute='_compute_internal_cost',
        store=True, help='Sum of linked BoM and BoQ Standard Costs.',
    )
    markup_percent = fields.Float(
        string='Markup (%)', default=0.0,
        help='Percentage applied to the internal cost to obtain the '
             'final project estimate price.',
    )
    final_estimate_price = fields.Float(
        string='Final Estimate Price',
        compute='_compute_final_estimate_price', store=True,
        help='internal_cost * (1 + markup_percent / 100).',
    )

    @api.depends(
        'engineering_project_id',
        'engineering_project_id.bom_ids.total_standard_cost',
        'engineering_project_id.boq_ids.total_standard_cost',
    )
    def _compute_internal_cost(self):
        """Pure compute: sum BoM + BoQ Standard Costs (FR-005).

        Does NOT raise on zero-cost products — the FR-015 warning is
        raised explicitly by _check_zero_cost_products() at send/approve
        time, not in the compute (raising in an automatic compute would
        break normal CRUD on related records).
        """
        for order in self:
            if not order.engineering_project_id:
                order.internal_cost = 0.0
                continue
            project = order.engineering_project_id
            bom_total = sum(project.bom_ids.mapped('total_standard_cost'))
            boq_total = sum(project.boq_ids.mapped('total_standard_cost'))
            order.internal_cost = bom_total + boq_total

    def _check_zero_cost_products(self):
        """FR-015: raise UserError if any BoM/BoQ line product has
        standard_price == 0. Called explicitly at send-to-commercial
        and approval time — not in the compute.
        """
        for order in self:
            if not order.engineering_project_id:
                continue
            project = order.engineering_project_id
            zero_products = []
            for line in project.bom_ids.mapped('line_ids'):
                if (line.product_id.standard_price or 0.0) == 0.0:
                    zero_products.append(line.product_id.display_name)
            for line in project.boq_ids.mapped('line_ids'):
                if (line.product_id.standard_price or 0.0) == 0.0:
                    zero_products.append(line.product_id.display_name)
            if zero_products:
                raise UserError(_(
                    "Cannot compute the internal cost: the following "
                    "products have a Standard Cost of zero. Set a "
                    "Standard Cost before continuing.\n%s"
                ) % '\n'.join(zero_products))

    @api.depends('internal_cost', 'markup_percent')
    def _compute_final_estimate_price(self):
        for order in self:
            order.final_estimate_price = order.internal_cost * (
                1.0 + (order.markup_percent or 0.0) / 100.0
            )

    def _sync_summary_line_price(self):
        """Keep the single summary sale.order.line.price_unit in sync
        with final_estimate_price (R14/T037)."""
        eng_product_tmpl = self.env.ref(
            'engineering.product_engineering_project_template',
            raise_if_not_found=False,
        )
        for order in self:
            if not eng_product_tmpl:
                continue
            summary_line = order.order_line.filtered(
                lambda l: l.product_id.product_tmpl_id == eng_product_tmpl
            )
            if summary_line:
                summary_line.write({
                    'price_unit': order.final_estimate_price,
                })

    def write(self, vals):
        res = super().write(vals)
        # Keep summary line price in sync with final_estimate_price.
        if 'final_estimate_price' in vals or 'markup_percent' in vals:
            self._sync_summary_line_price()
        return res

    def action_confirm(self):
        """T049: extend sale's action_confirm to trigger the engineering
        project approval flow (→ _generate_mo). NO runtime dependency
        guard — FR-016 is enforced at install time via hard `depends`
        (R11), so mrp/purchase/stock are always present.
        """
        res = super().action_confirm()
        for order in self:
            if order.engineering_project_id:
                order.engineering_project_id.action_customer_approve()
        return res

    def action_reject(self):
        """T051: reject the engineering quotation — set the linked
        engineering project to 'rejected' (R12) and cancel the
        sale.order. No MO is created."""
        for order in self:
            if order.engineering_project_id:
                order.engineering_project_id.action_customer_reject()
            else:
                order.action_cancel()
        return True