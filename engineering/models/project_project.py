# -*- coding: utf-8 -*-
"""Project module extension: link project.project to engineering.project.

Adds a back-link field engineering_project_id on project.project so the
construction timeline is reachable from both sides. The engineering
project's _create_or_link_project() (US4/T057) creates the project and
seeds one project.task per BoQ service line.
"""

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    _inherit = 'project.project'

    engineering_project_id = fields.Many2one(
        'engineering.project', string='Engineering Project', copy=False,
    )

    def action_open_engineering_project(self):
        """Smart button: open the linked engineering project."""
        self.ensure_one()
        if not self.engineering_project_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'engineering.project',
            'res_id': self.engineering_project_id.id,
            'view_mode': 'form',
            'target': 'current',
        }