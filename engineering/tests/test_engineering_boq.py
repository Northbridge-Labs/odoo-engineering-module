# -*- coding: utf-8 -*-
"""Tests for engineering.boq / engineering.boq.line (Foundational).

Covers: service product only (material rejected); qty>0;
total_standard_cost; lock on send (BoQ line creation blocked when
project state != draft).
"""

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged

# Odoo's TransactionCase.assertRaises only accepts a single exception
# class (its _assertRaises calls issubclass(exception, AccessError)).
# Use the most likely exception per test instead of a tuple.


@tagged('post_install', '-at_install')
class TestEngineeringBoq(TransactionCase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.partner = self.env['res.partner'].create({'name': 'Cust'})
        self.project = self.env['engineering.project'].create({
            'partner_id': self.partner.id,
        })
        self.material = self.env['product.product'].create({
            'name': 'Steel Beam',
            'type': 'consu',
            'standard_price': 50.0,
        })
        self.service = self.env['product.product'].create({
            'name': 'Welding',
            'type': 'service',
            'standard_price': 30.0,
        })
        self.uom_hour = self.env.ref('uom.product_uom_hour')

    def _create_boq(self):
        return self.env['engineering.boq'].create({
            'project_id': self.project.id,
        })

    def test_service_product_only(self):
        """A material (non-service) product cannot be added to a BoQ line."""
        boq = self._create_boq()
        with self.assertRaises(UserError):
            self.env['engineering.boq.line'].create({
                'boq_id': boq.id,
                'product_id': self.material.id,
                'product_qty': 1.0,
                'product_uom_id': self.uom_hour.id,
            })

    def test_qty_must_be_positive(self):
        """product_qty must be > 0 on BoQ lines."""
        boq = self._create_boq()
        with self.assertRaises(ValidationError):
            self.env['engineering.boq.line'].create({
                'boq_id': boq.id,
                'product_id': self.service.id,
                'product_qty': 0.0,
                'product_uom_id': self.uom_hour.id,
            })

    def test_total_standard_cost_computes(self):
        """total_standard_cost == sum of service line.line_cost."""
        boq = self._create_boq()
        self.env['engineering.boq.line'].create({
            'boq_id': boq.id,
            'product_id': self.service.id,
            'product_qty': 5.0,
            'product_uom_id': self.uom_hour.id,
        })
        # 5 * 30.0 = 150.0
        self.assertEqual(boq.total_standard_cost, 150.0)

    def test_lock_on_send(self):
        """BoQ lines cannot be added once project leaves draft (FR-014)."""
        boq = self._create_boq()
        self.project.state = 'sent_to_commercial'
        with self.assertRaises(UserError):
            self.env['engineering.boq.line'].create({
                'boq_id': boq.id,
                'product_id': self.service.id,
                'product_qty': 1.0,
                'product_uom_id': self.uom_hour.id,
            })

    # --- US1 test (T025) ---

    def test_boq_line_rejects_material_product(self):
        """BoQ line with product_id.type != service raises UserError."""
        boq = self._create_boq()
        with self.assertRaises(UserError):
            self.env['engineering.boq.line'].create({
                'boq_id': boq.id,
                'product_id': self.material.id,
                'product_qty': 1.0,
                'product_uom_id': self.uom_hour.id,
            })