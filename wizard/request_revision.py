# -*- coding: utf-8 -*-
"""Request Revision wizard.

A commercial user invokes this wizard from a sent_to_commercial
engineering project to request a revision. The wizard captures an
optional reason and calls project.action_request_revision(), which
cancels the old sale.order, creates a new draft revision, and returns
the new project.
"""

import logging

from odoo import fields, models
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class EngineeringRequestRevisionWizard(models.Model):
    _name = 'engineering.request.revision.wizard'
    _description = 'Engineering Request Revision Wizard'

    project_id = fields.Many2one(
        'engineering.project', string='Engineering Project', required=True,
    )
    reason = fields.Text(string='Reason for Revision')

    def action_confirm_request_revision(self):
        """Confirm: call project.action_request_revision() and open the
        new revision."""
        self.ensure_one()
        new_project = self.project_id.action_request_revision()
        if self.reason:
            new_project.message_post = None  # placeholder; mail.thread not enabled
        _logger.info(
            "Revision wizard confirmed for project %s: new revision %s.",
            self.project_id.display_name, new_project.display_name,
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'engineering.project',
            'res_id': new_project.id,
            'view_mode': 'form',
            'target': 'current',
        }