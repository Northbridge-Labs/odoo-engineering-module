# -*- coding: utf-8 -*-
"""Tests for the engineering quotation (extends sale.order).

Covers (US2):
- _compute_internal_cost: sums BoM+BoQ standard costs; raises on
  zero-cost products (FR-015).
- _compute_final_estimate_price: internal_cost * (1 + markup/100)
  (FR-006).
- sale.order.line: exactly ONE summary line referencing the shared
  engineering product, qty=1, price_unit=final_estimate_price (R14).
- Customer-facing QWeb report renders ONLY project name, customer,
  final_estimate_price (SC-003).
"""

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestQuotationMarkup(TransactionCase):

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

        # Build a BoM and BoQ with lines, then send to commercial.
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
        # Send to commercial creates the sale.order.
        self.project.action_send_to_commercial()
        self.order = self.project.sale_order_id

    def test_internal_cost_sums_bom_and_boq(self):
        """_compute_internal_cost == BoM total + BoQ total."""
        # BoM: 2 * 50 = 100; BoQ: 4 * 30 = 120; total = 220.
        self.assertEqual(self.order.internal_cost, 220.0)

    def test_internal_cost_warns_on_zero_standard_price(self):
        """FR-015: a product with standard_price=0 raises a warning
        when internal cost is computed (at send-to-commercial time),
        does NOT silently total zero."""
        zero_material = self.env['product.product'].create({
            'name': 'Free Steel', 'type': 'consu', 'standard_price': 0.0,
        })
        project2 = self.env['engineering.project'].create({
            'partner_id': self.partner.id,
        })
        bom2 = self.env['engineering.bom'].create({'project_id': project2.id})
        self.env['engineering.bom.line'].create({
            'bom_id': bom2.id,
            'product_id': zero_material.id,
            'product_qty': 1.0,
            'product_uom_id': self.uom_unit.id,
        })
        # The warning fires at send time (internal cost is computed
        # during action_send_to_commercial).
        with self.assertRaises(UserError):
            project2.action_send_to_commercial()

    def test_final_estimate_price_formula(self):
        """FR-006: final = internal_cost * (1 + markup/100)."""
        self.order.markup_percent = 15.0
        # 220 * 1.15 = 253.0
        self.assertAlmostEqual(self.order.final_estimate_price, 253.0, places=4)

    def test_final_estimate_price_recomputes_on_markup_change(self):
        """Changing markup_percent recomputes final_estimate_price."""
        self.order.markup_percent = 10.0
        self.assertAlmostEqual(self.order.final_estimate_price, 220.0 * 1.10, places=4)
        self.order.markup_percent = 20.0
        self.assertAlmostEqual(self.order.final_estimate_price, 220.0 * 1.20, places=4)

    def test_single_summary_sale_order_line(self):
        """R14: exactly ONE sale.order.line referencing the shared
        engineering product, qty=1, price_unit=final_estimate_price."""
        self.order.markup_percent = 15.0
        lines = self.order.order_line
        self.assertEqual(len(lines), 1)
        line = lines[0]
        eng_product = self.env.ref('engineering.product_engineering_project_template')
        # The line's product should be a variant of the shared template.
        self.assertEqual(line.product_id.product_tmpl_id, eng_product)
        self.assertEqual(line.product_uom_qty, 1.0)
        self.assertAlmostEqual(line.price_unit, self.order.final_estimate_price, places=4)

    def test_no_per_product_lines_on_sale_order(self):
        """No per-product BoM/BoQ detail on sale.order.line (SC-003
        structural non-exposure)."""
        line_products = self.order.order_line.mapped('product_id')
        self.assertNotIn(self.material, line_products)
        self.assertNotIn(self.service, line_products)