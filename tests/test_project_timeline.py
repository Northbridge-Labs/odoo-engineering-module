# -*- coding: utf-8 -*-
"""Tests for US4: Project module manages construction timeline.

Covers:
- After approval, engineering.project.project_id is set and
  project.project.engineering_project_id back-link is set (T053).
- One project.task exists per BoQ service line (count == BoQ line
  count) with matching product/qty; NO tasks seeded from BoM material
  lines (T053).
- Idempotency: re-calling _create_or_link_project() when project_id is
  set and tasks already seeded raises UserError (T054).
- Reachability: the engineering project form exposes a smart button to
  project_id (SC-006) (T055).
"""

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestProjectTimeline(TransactionCase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.partner = self.env['res.partner'].create({'name': 'Cust'})
        self.project = self.env['engineering.project'].create({
            'partner_id': self.partner.id,
        })
        self.material = self.env['product.product'].create({
            'name': 'Steel Beam', 'type': 'consu', 'standard_price': 50.0,
        })
        self.service1 = self.env['product.product'].create({
            'name': 'Welding', 'type': 'service', 'standard_price': 30.0,
        })
        self.service2 = self.env['product.product'].create({
            'name': 'Painting', 'type': 'service', 'standard_price': 20.0,
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
            'product_id': self.service1.id,
            'product_qty': 4.0,
            'product_uom_id': self.uom_hour.id,
        })
        self.env['engineering.boq.line'].create({
            'boq_id': self.boq.id,
            'product_id': self.service2.id,
            'product_qty': 2.0,
            'product_uom_id': self.uom_hour.id,
        })
        self.project.action_send_to_commercial()
        self.order = self.project.sale_order_id

    def test_project_linked_on_approval(self):
        """T053: after approval, engineering.project.project_id is set
        and project.project.engineering_project_id back-link is set."""
        self.order.action_confirm()
        self.assertTrue(self.project.project_id)
        self.assertEqual(self.project.project_id.engineering_project_id,
                         self.project)

    def test_one_task_per_boq_service_line(self):
        """T053: one project.task exists per BoQ service line (count ==
        BoQ line count); NO tasks seeded from BoM material lines.

        Note: Odoo 18 project.task has no product_id field; the service
        product name is embedded in the task name."""
        self.order.action_confirm()
        tasks = self.env['project.task'].search([
            ('project_id', '=', self.project.project_id.id),
        ])
        self.assertEqual(len(tasks), 2)  # 2 BoQ service lines
        task_names = tasks.mapped('name')
        # Each task name contains the service product name.
        self.assertTrue(any('Welding' in n for n in task_names))
        self.assertTrue(any('Painting' in n for n in task_names))
        # No tasks seeded from BoM material lines.
        self.assertFalse(any('Steel Beam' in n for n in task_names))

    def test_create_or_link_project_idempotent(self):
        """T054: re-calling _create_or_link_project() when project_id
        is set and tasks already seeded raises UserError."""
        self.order.action_confirm()
        with self.assertRaises(UserError):
            self.project._create_or_link_project()

    def test_project_smart_button_reachable(self):
        """T055/SC-006: the engineering project form exposes a smart
        button to project_id (one navigation step). Verified by the
        project_id field being set and accessible via action_open_project."""
        self.order.action_confirm()
        self.assertTrue(self.project.project_id)
        action = self.project.action_open_project()
        self.assertEqual(action['res_model'], 'project.project')
        self.assertEqual(action['res_id'], self.project.project_id.id)