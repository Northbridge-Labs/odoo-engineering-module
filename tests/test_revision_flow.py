# -*- coding: utf-8 -*-
"""Tests for the revision flow (FR-014, R13).

Covers:
- From sent_to_commercial, engineering user write on BoM line raises
  UserError (locked, FR-014/SC-007).
- Commercial user runs action_request_revision() → revision_number
  increments, previous project revision is_current_revision=False, the
  previous revision's sale.order is cancelled (R13), new project
  revision state='draft', is_current_revision=True,
  sale_order_id=False, BoM/BoQ editable (T060).
- Access control: only group_commercial_user can call
  action_request_revision(); engineering user gets AccessError (T061).
"""

from odoo.exceptions import UserError, AccessError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRevisionFlow(TransactionCase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.partner = self.env['res.partner'].create({'name': 'Cust'})
        self.project = self.env['engineering.project'].create({
            'partner_id': self.partner.id,
        })
        self.material = self.env['product.product'].create({
            'name': 'Steel Beam', 'type': 'consu', 'standard_price': 50.0,
        })
        self.service = self.env['product.product'].create({
            'name': 'Welding', 'type': 'service', 'standard_price': 30.0,
        })
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        self.uom_hour = self.env.ref('uom.product_uom_hour')

        self.bom = self.env['engineering.bom'].create({
            'project_id': self.project.id,
        })
        self.env['engineering.bom.line'].create({
            'bom_id': self.bom.id,
            'product_id': self.material.id,
            'product_qty': 2.0,
            'product_uom_id': self.uom_unit.id,
        })
        self.boq = self.env['engineering.boq'].create({
            'project_id': self.project.id,
        })
        self.env['engineering.boq.line'].create({
            'boq_id': self.boq.id,
            'product_id': self.service.id,
            'product_qty': 4.0,
            'product_uom_id': self.uom_hour.id,
        })
        self.project.action_send_to_commercial()
        self.order = self.project.sale_order_id

        # Set up user groups for access tests.
        self.engineering_user = self.env['res.users'].create({
            'name': 'Eng User', 'login': 'eng_user_rev',
            'groups_id': [(4, self.env.ref('engineering.group_engineering_user').id)],
        })
        self.commercial_user = self.env['res.users'].create({
            'name': 'Comm User', 'login': 'comm_user_rev',
            'groups_id': [(4, self.env.ref('engineering.group_commercial_user').id)],
        })
        # Grant admin (default test user) the commercial group so the
        # non-access tests can call action_request_revision() directly.
        self.env.user.groups_id = [
            (4, self.env.ref('engineering.group_commercial_user').id),
        ]

    def test_engineering_edit_blocked_after_send(self):
        """FR-014/SC-007: from sent_to_commercial, engineering user
        cannot edit a BoM line (scope locked)."""
        self.assertEqual(self.project.state, 'sent_to_commercial')
        with self.assertRaises(UserError):
            self.env['engineering.bom.line'].create({
                'bom_id': self.bom.id,
                'product_id': self.material.id,
                'product_qty': 1.0,
                'product_uom_id': self.uom_unit.id,
            })

    def test_open_request_revision_wizard(self):
        action = self.project.action_open_request_revision_wizard()

        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'engineering.request.revision.wizard')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'new')
        self.assertEqual(action['context'], {'default_project_id': self.project.id})

    def test_request_revision_creates_new_draft(self):
        """T060/R13: commercial user runs action_request_revision() →
        revision_number increments, previous revision's sale.order is
        cancelled, new revision state='draft',
        is_current_revision=True, sale_order_id=False, BoM/BoQ
        editable."""
        old_revision_number = self.project.revision_number
        old_order = self.project.sale_order_id
        # Commercial user requests revision.
        new_project = self.project.action_request_revision()
        # The original project is no longer current.
        self.assertFalse(self.project.is_current_revision)
        # The old sale.order is cancelled.
        self.assertEqual(old_order.state, 'cancel')
        # A new revision exists.
        self.assertTrue(new_project)
        self.assertEqual(new_project.revision_number, old_revision_number + 1)
        self.assertTrue(new_project.is_current_revision)
        self.assertEqual(new_project.state, 'draft')
        self.assertFalse(new_project.sale_order_id)
        # The new revision's BoM/BoQ are editable (state=draft).
        new_bom = new_project.bom_ids[0]
        self.env['engineering.bom.line'].create({
            'bom_id': new_bom.id,
            'product_id': self.material.id,
            'product_qty': 5.0,
            'product_uom_id': self.uom_unit.id,
        })

    def test_only_commercial_can_request_revision(self):
        """T061: only group_commercial_user can call
        action_request_revision(); engineering user gets AccessError."""
        # Engineering user attempt should raise AccessError.
        eng_project = self.project.with_user(self.engineering_user)
        with self.assertRaises(AccessError):
            eng_project.action_request_revision()
        # Commercial user can call it.
        comm_project = self.project.with_user(self.commercial_user)
        new_project = comm_project.action_request_revision()
        self.assertTrue(new_project)