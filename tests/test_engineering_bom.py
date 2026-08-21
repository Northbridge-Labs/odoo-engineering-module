# -*- coding: utf-8 -*-
"""Tests for engineering.bom / engineering.bom.line (Foundational).

Covers: line create blocked when project state != draft (FR-014);
material product only (service product rejected); qty>0 enforced;
total_standard_cost computes from line costs.
"""

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged

# Odoo's TransactionCase.assertRaises only accepts a single exception
# class (its _assertRaises calls issubclass(exception, AccessError)).
# Use the most likely exception per test instead of a tuple.


@tagged('post_install', '-at_install')
class TestEngineeringBom(TransactionCase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.partner = self.env['res.partner'].create({'name': 'Cust'})
        self.project = self.env['engineering.project'].create({
            'partner_id': self.partner.id,
        })
        # Material (non-service) product with standard cost.
        self.material = self.env['product.product'].create({
            'name': 'Steel Beam',
            'type': 'consu',
            'standard_price': 50.0,
        })
        # Service product (must be rejected on BoM lines).
        self.service = self.env['product.product'].create({
            'name': 'Welding',
            'type': 'service',
            'standard_price': 30.0,
        })
        self.uom_unit = self.env.ref('uom.product_uom_unit')

    def _create_bom(self):
        return self.env['engineering.bom'].create({
            'project_id': self.project.id,
        })

    def test_line_create_blocked_when_not_draft(self):
        """Cannot add BoM lines once project leaves draft (FR-014)."""
        bom = self._create_bom()
        self.project.state = 'sent_to_commercial'
        with self.assertRaises(UserError):
            self.env['engineering.bom.line'].create({
                'bom_id': bom.id,
                'product_id': self.material.id,
                'product_qty': 2.0,
                'product_uom_id': self.uom_unit.id,
            })

    def test_service_product_rejected_on_bom_line(self):
        """A service product cannot be added to a BoM line."""
        bom = self._create_bom()
        with self.assertRaises(UserError):
            self.env['engineering.bom.line'].create({
                'bom_id': bom.id,
                'product_id': self.service.id,
                'product_qty': 1.0,
                'product_uom_id': self.uom_unit.id,
            })

    def test_qty_must_be_positive(self):
        """product_qty must be > 0."""
        bom = self._create_bom()
        with self.assertRaises(ValidationError):
            self.env['engineering.bom.line'].create({
                'bom_id': bom.id,
                'product_id': self.material.id,
                'product_qty': 0.0,
                'product_uom_id': self.uom_unit.id,
            })

    def test_total_standard_cost_computes(self):
        """total_standard_cost == sum of line.line_cost."""
        bom = self._create_bom()
        self.env['engineering.bom.line'].create({
            'bom_id': bom.id,
            'product_id': self.material.id,
            'product_qty': 3.0,
            'product_uom_id': self.uom_unit.id,
        })
        # 3 * 50.0 = 150.0
        self.assertEqual(bom.total_standard_cost, 150.0)

    def test_line_cost_compute(self):
        """line_cost == product_qty * standard_cost."""
        bom = self._create_bom()
        line = self.env['engineering.bom.line'].create({
            'bom_id': bom.id,
            'product_id': self.material.id,
            'product_qty': 4.0,
            'product_uom_id': self.uom_unit.id,
        })
        self.assertEqual(line.standard_cost, 50.0)
        self.assertEqual(line.line_cost, 200.0)

    # --- US1 tests (T023/T024) ---

    def test_action_send_to_commercial_rejects_empty_scope(self):
        """FR-013: send with both BoM and BoQ empty raises UserError."""
        with self.assertRaises(UserError):
            self.project.action_send_to_commercial()

    def test_action_send_to_commercial_succeeds_and_locks(self):
        """FR-014: send with >=1 line transitions to sent_to_commercial
        and locks the BoM (further line create raises)."""
        bom = self._create_bom()
        self.env['engineering.bom.line'].create({
            'bom_id': bom.id,
            'product_id': self.material.id,
            'product_qty': 2.0,
            'product_uom_id': self.uom_unit.id,
        })
        self.project.action_send_to_commercial()
        self.assertEqual(self.project.state, 'sent_to_commercial')
        # Lock: line create now blocked.
        with self.assertRaises(UserError):
            self.env['engineering.bom.line'].create({
                'bom_id': bom.id,
                'product_id': self.material.id,
                'product_qty': 1.0,
                'product_uom_id': self.uom_unit.id,
            })