# © 2024 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class MisBudget(models.Model):
    _inherit = "mis.budget"

    project_id = fields.Many2one('project.project')
    analytic_account_project_id = fields.Many2one('account.analytic.account', related='project_id.analytic_account_id')
    is_margin = fields.Boolean(readonly=True)

    def action_duplicate(self):
        budget_id = self.copy()
        budget_id.action_draft()
