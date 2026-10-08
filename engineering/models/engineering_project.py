# -*- coding: utf-8 -*-
"""Engineering Project model.

Top-level engineering work order record. One per customer order (plus
one per revision when commercial requests a revision).

Field declarations only at this stage (Phase 2 Foundational skeleton);
method logic is added in T018, T021, and the user story phases.
"""

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

STATE_SELECTION = [
    ('draft', 'Draft'),
    ('sent_to_commercial', 'Sent to Commercial'),
    ('approved', 'Approved'),
    ('manufacturing', 'Manufacturing'),
    ('rejected', 'Rejected'),
]


class EngineeringProject(models.Model):
    _name = 'engineering.project'
    _description = 'Engineering Project'
    _order = 'revision_number desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True,
    )
    sale_order_id = fields.Many2one(
        'sale.order', string='Quotation', readonly=True, copy=False,
    )
    project_id = fields.Many2one(
        'project.project', string='Construction Project',
        readonly=True, copy=False,
    )
    mrp_production_id = fields.Many2one(
        'mrp.production', string='Manufacturing Order',
        readonly=True, copy=False,
    )
    state = fields.Selection(
        STATE_SELECTION, string='State', default='draft', required=True,
        copy=False,
    )
    revision_number = fields.Integer(
        string='Revision Number', default=1, copy=False, required=True,
    )
    is_current_revision = fields.Boolean(
        string='Current Revision', default=True, copy=False,
    )
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
    )
    bom_ids = fields.One2many(
        'engineering.bom', 'project_id', string='Bill of Materials',
    )
    boq_ids = fields.One2many(
        'engineering.boq', 'project_id', string='Bill of Quantities',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Assign sequence on create (T018)."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('eng.project')
                if seq:
                    vals['name'] = seq
                else:
                    vals['name'] = _('ENG/%s/0001' % fields.Date.today().year)
        return super().create(vals_list)

    def _check_scope_editable(self):
        """Raise UserError if project state is not 'draft' (FR-014).

        Called by BoM/BoQ line create/write/unlink to enforce that the
        engineering scope is locked once sent to commercial.
        """
        for record in self:
            if record.state != 'draft':
                raise UserError(_(
                    "The engineering scope of project %s is locked "
                    "(state: %s). Use a commercial 'Request Revision' "
                    "action to unlock a new draft revision."
                ) % (record.display_name, record.state))

    def action_send_to_commercial(self):
        """Send the engineering scope (BoM + BoQ) to the commercial
        department. Validates non-empty scope (FR-013), locks the scope
        by transitioning state to sent_to_commercial (FR-014), creates
        the engineering quotation (sale.order) with exactly one summary
        sale.order.line (R14) for the shared engineering product, and
        logs an INFO event. US1/US2 implementation (T026/T036).
        """
        for project in self:
            bom_lines = project.bom_ids.mapped('line_ids')
            boq_lines = project.boq_ids.mapped('line_ids')
            if not bom_lines and not boq_lines:
                raise UserError(_(
                    "Cannot send an empty engineering scope to the "
                    "commercial department. Add at least one material "
                    "line to the BoM or one service line to the BoQ."
                ))
            project.state = 'sent_to_commercial'
            # Create or reuse the engineering quotation (sale.order)
            # with one summary sale.order.line (R14).
            if not project.sale_order_id:
                order = self.env['sale.order'].create({
                    'partner_id': project.partner_id.id,
                    'engineering_project_id': project.id,
                    'company_id': project.company_id.id,
                })
                # FR-015: check zero-cost products before computing the
                # final price (raises UserError listing offenders).
                order._check_zero_cost_products()
                eng_product_tmpl = self.env.ref(
                    'engineering.product_engineering_project_template',
                )
                summary_line = self.env['sale.order.line'].create({
                    'order_id': order.id,
                    'product_id': eng_product_tmpl.product_variant_id.id,
                    'product_uom_qty': 1.0,
                    'price_unit': order.final_estimate_price,
                    'name': _('Engineering Project %s') % project.display_name,
                })
                project.sale_order_id = order.id
            else:
                # Re-quote from rejected: reuse the sale.order, reset to draft.
                order = project.sale_order_id
                if order.state in ('cancel', 'sent'):
                    order.action_draft()
            _logger.info(
                "Engineering scope sent to commercial for project %s "
                "(revision %s, %s BoM lines, %s BoQ lines). Quotation %s.",
                project.display_name, project.revision_number,
                len(bom_lines), len(boq_lines), order.display_name,
            )

    def action_customer_approve(self):
        """T044: set state='approved'; call _generate_mo() and
        _create_or_link_project() (US4); log INFO."""
        for project in self:
            project.state = 'approved'
            project._generate_mo()
            project._create_or_link_project()
            _logger.info(
                "Engineering project %s approved; MO %s generated; "
                "construction project %s linked.",
                project.display_name,
                project.mrp_production_id.display_name if project.mrp_production_id else 'N/A',
                project.project_id.display_name if project.project_id else 'N/A',
            )

    def action_customer_reject(self):
        """T051: set state='rejected' (R12 auditable intermediate);
        cancel the sale.order; no MO created; log INFO."""
        for project in self:
            project.state = 'rejected'
            if project.sale_order_id:
                project.sale_order_id.action_cancel()
            _logger.info(
                "Engineering project %s rejected.", project.display_name,
            )

    def action_re_quote(self):
        """T051: from 'rejected' only → state='draft' (same revision)
        for re-quotation (R12)."""
        for project in self:
            if project.state != 'rejected':
                raise UserError(_(
                    "Can only re-quote a rejected project (current "
                    "state: %s)."
                ) % project.state)
            project.state = 'draft'
            _logger.info(
                "Engineering project %s returned to draft for re-quote.",
                project.display_name,
            )

    def action_request_revision(self):
        """T062/R13: commercial-only action. Cancels the current
        revision's sale.order (retained for audit), copies the project
        (and its BoM/BoQ) to a new revision with revision_number+1,
        is_current_revision=True, state='draft', sale_order_id=False.
        Marks the current revision is_current_revision=False. Returns
        the new project record.
        """
        self.ensure_one()
        # Explicit commercial-group check (FR-014: only commercial may
        # request a revision).
        if not self.env.user.has_group('engineering.group_commercial_user'):
            raise AccessError(_(
                "Only Commercial users can request a revision of an "
                "engineering scope."
            ))
        if self.state != 'sent_to_commercial':
            raise UserError(_(
                "Can only request a revision of a scope that has been "
                "sent to commercial (current state: %s)."
            ) % self.state)
        # Cancel the current revision's sale.order (R13, retained for
        # audit). Use sudo() because the commercial user may not have
        # full sale.order cancel rights; the engineering module owns
        # this orchestration step (constitution Principle IV: sudo
        # justified — cancelling the linked quotation is part of the
        # revision workflow, not a user-granted privilege).
        if self.sale_order_id:
            self.sale_order_id.sudo().action_cancel()
        # Mark the current revision as no longer current. Use sudo()
        # because the commercial user is blocked by the draft-only
        # write record rule on engineering.project; the revision
        # orchestration is an explicit commercial action that must
        # update the prior revision's audit flag (constitution
        # Principle IV: sudo justified — documented orchestration step
        # outside normal CRUD permissions).
        self.sudo().is_current_revision = False
        # Create a new project revision and copy the BoM/BoQ scope
        # manually (ORM copy() does not reliably copy nested One2many
        # with related/readonly fields in all Odoo 18 builds).
        new_project = self.env['engineering.project'].create({
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'revision_number': self.revision_number + 1,
            'is_current_revision': True,
            'state': 'draft',
        })
        # Copy BoM and its lines.
        for bom in self.bom_ids:
            new_bom = self.env['engineering.bom'].create({
                'project_id': new_project.id,
            })
            for line in bom.line_ids:
                self.env['engineering.bom.line'].create({
                    'bom_id': new_bom.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom_id': line.product_uom_id.id,
                })
        # Copy BoQ and its lines.
        for boq in self.boq_ids:
            new_boq = self.env['engineering.boq'].create({
                'project_id': new_project.id,
            })
            for line in boq.line_ids:
                self.env['engineering.boq.line'].create({
                    'boq_id': new_boq.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom_id': line.product_uom_id.id,
                })
        _logger.info(
            "Revision requested for engineering project %s: new "
            "revision %s created, previous revision retained for "
            "audit (sale.order cancelled).",
            self.display_name, new_project.display_name,
        )
        return new_project

    def action_open_request_revision_wizard(self):
        """Open the revision request wizard for this project."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request Revision'),
            'res_model': 'engineering.request.revision.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_project_id': self.id},
        }

    def action_open_quotation(self):
        """Smart button: open the linked sale.order quotation."""
        self.ensure_one()
        if not self.sale_order_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_mo(self):
        """Smart button: open the linked mrp.production."""
        self.ensure_one()
        if not self.mrp_production_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'res_id': self.mrp_production_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_project(self):
        """Smart button (US4/SC-006): open the linked project.project
        construction timeline in one navigation step."""
        self.ensure_one()
        if not self.project_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': self.project_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_or_link_project(self):
        """T057: create or link a project.project for the construction
        timeline, and seed one project.task per BoQ service line
        (materials are NOT seeded — they are procurement-tracked via
        MRP/stock). Idempotent: raises UserError if project_id is
        already set and tasks already seeded (no duplicate tasks).
        """
        self.ensure_one()
        if self.project_id:
            # Check if tasks were already seeded for this engineering
            # project; if so, raise to prevent duplicates.
            existing_tasks = self.env['project.task'].search([
                ('project_id', '=', self.project_id.id),
            ])
            if existing_tasks:
                raise UserError(_(
                    "A construction project with tasks already exists "
                    "for engineering project %s. Cannot create a second "
                    "one."
                ) % self.display_name)
            # Link exists but no tasks: just reuse.
            return
        project = self.env['project.project'].create({
            'name': self.display_name,
            'partner_id': self.partner_id.id,
            'engineering_project_id': self.id,
            'company_id': self.company_id.id,
        })
        # Seed one project.task per BoQ service line.
        # Note: project.task in Odoo 18 has no product_id/planned_qty
        # field; the service product and quantity are recorded in the
        # task name for v1 (a future phase can extend project.task).
        for boq in self.boq_ids:
            for line in boq.line_ids:
                self.env['project.task'].create({
                    'name': _('%s — %s (%s %s)') % (
                        self.display_name,
                        line.product_id.display_name,
                        line.product_qty,
                        line.product_uom_id.display_name,
                    ),
                    'project_id': project.id,
                    'company_id': self.company_id.id,
                })
        self.project_id = project.id
        _logger.info(
            "Construction project %s linked to engineering project %s "
            "(%s tasks seeded from BoQ services).",
            project.display_name, self.display_name,
            sum(len(b.line_ids) for b in self.boq_ids),
        )

    def _generate_mo(self):
        """T048: orchestrate mrp.bom + mrp.production creation from the
        approved engineering BoM materials, attach BoQ services as
        engineering.mo.service.line (non-stock work lines, FR-011), and
        trigger procurement (RFQs) via standard MRP confirm (FR-010).

        The mrp.bom.product_id references the shared
        engineering.product_engineering_project product (R15). If the
        active Odoo 18 build rejects a service-type finished good on
        mrp.bom, fall back to the consu-type
        product_engineering_project_finished_good_template.
        """
        self.ensure_one()
        if self.mrp_production_id:
            raise UserError(_(
                "A Manufacturing Order already exists for project %s. "
                "Cannot generate a second one."
            ) % self.display_name)
        # Resolve the finished-good product (R15).
        eng_product_tmpl = self.env.ref(
            'engineering.product_engineering_project_template',
        )
        finished_product = eng_product_tmpl.product_variant_id
        # Build the mrp.bom from the engineering BoM material lines.
        bom_line_vals = []
        for bom in self.bom_ids:
            for line in bom.line_ids:
                bom_line_vals.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom_id': line.product_uom_id.id,
                }))
        mrp_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': eng_product_tmpl.id,
            'product_id': finished_product.id,
            'product_qty': 1.0,
            'product_uom_id': finished_product.uom_id.id,
            'type': 'normal',
            'bom_line_ids': bom_line_vals,
        })
        # Create the mrp.production from that mrp.bom.
        mo = self.env['mrp.production'].create({
            'product_id': finished_product.id,
            'product_qty': 1.0,
            'product_uom_id': finished_product.uom_id.id,
            'bom_id': mrp_bom.id,
            'engineering_project_id': self.id,
            'company_id': self.company_id.id,
        })
        # Attach BoQ services as non-stock work lines (FR-011).
        service_line_vals = []
        for boq in self.boq_ids:
            for line in boq.line_ids:
                service_line_vals.append((0, 0, {
                    'production_id': mo.id,
                    'boq_line_id': line.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom_id': line.product_uom_id.id,
                    'state': 'to_do',
                }))
        if service_line_vals:
            mo.engineering_service_line_ids = service_line_vals
        # Trigger procurement (RFQs for shortages) via standard confirm.
        mo.action_confirm()
        self.mrp_production_id = mo.id
        self.state = 'manufacturing'
        _logger.info(
            "Manufacturing Order %s generated for project %s from "
            "mrp.bom %s (BoQ services: %s).",
            mo.display_name, self.display_name, mrp_bom.display_name,
            len(service_line_vals),
        )