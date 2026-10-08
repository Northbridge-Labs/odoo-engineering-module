# -*- coding: utf-8 -*-
"""Engineering test suite.

All test classes are imported here so that Odoo's test runner picks
them up when the module is installed with ``--test-enable``.
"""

from ...tests import test_engineering_project
from ...tests import test_engineering_bom
from ...tests import test_engineering_boq
from ...tests import test_quotation_markup
from ...tests import test_approval_generates_mo
from ...tests import test_rfq_on_shortage
from ...tests import test_reject_requote
from ...tests import test_project_timeline
from ...tests import test_revision_flow