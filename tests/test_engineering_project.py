# -*- coding: utf-8 -*-
"""Tests for engineering.project (Foundational).

Covers: create defaults (state=draft, revision_number=1,
is_current_revision=True), name sequence assignment, partner_id
required. Phase 2 Foundational tests; expected to FAIL until T018
implements the create/sequence logic.
"""

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import AccessError


@tagged('post_install', '-at_install')
class TestEngineeringProject(TransactionCase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
        })

    def test_create_defaults(self):
        """A new project has state=draft, revision_number=1,
        is_current_revision=True."""
        project = self.env['engineering.project'].create({
            'partner_id': self.partner.id,
        })
        self.assertEqual(project.state, 'draft')
        self.assertEqual(project.revision_number, 1)
        self.assertTrue(project.is_current_revision)

    def test_name_sequence_assigned(self):
        """On create, name gets a sequence value (not 'New')."""
        project = self.env['engineering.project'].create({
            'partner_id': self.partner.id,
        })
        self.assertNotEqual(project.name, 'New')
        self.assertTrue(project.name.startswith('ENG/'))

    def test_partner_required(self):
        """Creating a project without a partner raises."""
        # Odoo's assertRaises only accepts a single exception class.
        # Missing required field surfaces as a psycopg/AccessError.
        with self.assertRaises(Exception):
            self.env['engineering.project'].create({})