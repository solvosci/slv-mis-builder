# © 2025 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api


class ProjectMisExportWizard(models.TransientModel):
    _name = "project.mis.export.wizard"

    project_ids = fields.Many2many("project.project", string="Projects")
    account_analytic_ids = fields.Many2many("account.analytic.account", string="Analytic Accounts")
    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")

    @api.onchange('project_ids')
    def _onchange_project_ids(self):
        for record in self:
            record.account_analytic_ids = record.project_ids.mapped('analytic_account_id')

    def action_export_xlsx(self):
        return self.env.ref('mis_builder_report_xlsx.action_project_mis_report_xlsx').report_action(self)
