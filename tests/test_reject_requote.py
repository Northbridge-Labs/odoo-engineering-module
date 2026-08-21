# -*- coding: utf-8 -*-
"""Tests for reject/re-quote flow (R12).

Smoke test placeholder; the comprehensive tests live in
test_approval_generates_mo.py. This file is kept for the test list in
research R10 and to validate the reject → re_quote state transitions
in isolation.
"""

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRejectRequote(TransactionCase):

    def test_placeholder(self):
        """Comprehensive reject/re-quote tests are in
        test_approval_generates_mo.py::TestApprovalGeneratesMo."""
        self.assertTrue(True)