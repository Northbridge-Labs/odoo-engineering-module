# -*- coding: utf-8 -*-
"""Engineering test suite.

All test classes are imported here so that Odoo's test runner picks
them up when the module is installed with ``--test-enable``.
"""

from . import test_engineering_project
from . import test_engineering_bom
from . import test_engineering_boq
from . import test_quotation_markup
from . import test_approval_generates_mo
from . import test_rfq_on_shortage
from . import test_reject_requote
from . import test_project_timeline
from . import test_revision_flow