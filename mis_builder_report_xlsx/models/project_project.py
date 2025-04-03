# © 2025 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models, _


class ProjectProject(models.Model):
    _inherit = "project.project"

    def action_project_export_xlsx(self):
        Wizard = self.env['project.mis.export.wizard']
        new = Wizard.create({})

        return {
            'name': _('Cumulative Total'),
            'res_model': 'project.mis.export.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': new.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
