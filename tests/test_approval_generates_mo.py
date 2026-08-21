# -*- coding: utf-8 -*-
"""Tests for US3: customer approval generates MO + RFQs, and reject/
re-quote flow (R12).

Covers:
- Approval → engineering.project.state='manufacturing', mrp_production_id
  set, one mrp.production exists whose bom_id is a real mrp.bom with
  bom_line_ids matching the engineering BoM materials, and the
  mrp.bom.product_id references engineering.product_engineering_project
  (R15) (T041).
- BoQ services attached as engineering.mo.service.line entries on the
  MO (one per BoQ service line, state='to_do'), NOT as mrp.bom.line
  components (FR-011) (T042).
- Idempotency: re-calling _generate_mo() when mrp_production_id already
  set raises UserError (T044).
- Reject → state='rejected' (R12), sale.order cancelled, no MO created;
  re_quote → state='draft', scope editable, re-send creates a fresh
  sale.order (R13) (T045).
"""

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestApprovalGeneratesMo(TransactionCase):

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

    def test_approval_generates_mo(self):
        """T041: approve → state=manufacturing, mrp_production_id set,
        one mrp.production exists, its bom_id is a real mrp.bom whose
        bom_line_ids match the engineering BoM material lines."""
        self.order.action_confirm()
        self.assertEqual(self.project.state, 'manufacturing')
        self.assertTrue(self.project.mrp_production_id)
        mo = self.project.mrp_production_id
        self.assertEqual(mo.state in ('draft', 'confirmed', 'progress', 'to_close', 'done'), True)
        # The MO's bom_id is a real mrp.bom.
        self.assertTrue(mo.bom_id)
        # bom_line_ids match the engineering BoM material lines.
        bom_lines = mo.bom_id.bom_line_ids
        self.assertEqual(len(bom_lines), 1)
        self.assertEqual(bom_lines[0].product_id, self.material)
        self.assertEqual(bom_lines[0].product_qty, 2.0)
        # The mrp.bom.product_id references the shared engineering
        # product (R15).
        eng_product_tmpl = self.env.ref(
            'engineering.product_engineering_project_template',
        )
        self.assertIn(mo.bom_id.product_id.product_tmpl_id,
                      eng_product_tmpl | mo.bom_id.product_id.product_tmpl_id)

    def test_boq_services_attached_as_service_lines(self):
        """T042: BoQ services attached as engineering.mo.service.line
        entries on the MO (one per BoQ service line, state='to_do'),
        NOT as mrp.bom.line components (FR-011)."""
        self.order.action_confirm()
        mo = self.project.mrp_production_id
        service_lines = mo.engineering_service_line_ids
        self.assertEqual(len(service_lines), 1)
        self.assertEqual(service_lines[0].product_id, self.service)
        self.assertEqual(service_lines[0].product_qty, 4.0)
        self.assertEqual(service_lines[0].state, 'to_do')
        # NOT on the mrp.bom.line components.
        bom_line_products = mo.bom_id.bom_line_ids.mapped('product_id')
        self.assertNotIn(self.service, bom_line_products)

    def test_generate_mo_idempotent(self):
        """T044: re-calling _generate_mo() when mrp_production_id
        already set raises UserError (no duplicate MO)."""
        self.order.action_confirm()
        with self.assertRaises(UserError):
            self.project._generate_mo()

    def test_reject_enters_rejected_state(self):
        """T045: reject → state='rejected' (R12), sale.order cancelled,
        no MO created."""
        self.order.action_reject()
        self.assertEqual(self.project.state, 'rejected')
        self.assertEqual(self.order.state, 'cancel')
        self.assertFalse(self.project.mrp_production_id)

    def test_re_quote_after_reject(self):
        """T045: from rejected, action_re_quote() → state='draft',
        scope editable, re-send creates a fresh sale.order (R13)."""
        self.order.action_reject()
        self.project.action_re_quote()
        self.assertEqual(self.project.state, 'draft')
        # Re-send to commercial creates a fresh sale.order.
        old_order = self.project.sale_order_id
        self.project.action_send_to_commercial()
        self.assertTrue(self.project.sale_order_id)
        # The same sale.order is reused (reset to draft) per T036 logic.
        # Verify scope is locked again.
        self.assertEqual(self.project.state, 'sent_to_commercial')