# © 2024 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class MisReportKpi(models.Model):
    _inherit = "mis.report.kpi"

    is_margin = fields.Boolean()

    @api.onchange('is_margin')
    def _onchange_is_margin(self):
        if self.is_margin and not self.budgetable:
            raise ValidationError(_("KPI must be budgetable"))
        if  self.is_margin and len(self.report_id.kpi_ids.filtered(lambda x: x.is_margin)) > 1:
            raise ValidationError(_("Only one KPI can be margin"))
