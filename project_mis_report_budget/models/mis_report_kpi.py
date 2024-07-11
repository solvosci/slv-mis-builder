# © 2024 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class MisReportKpi(models.Model):
    _inherit = "mis.report.kpi"

    # TODO: Remove field
    is_margin = fields.Boolean()
    kpi_type = fields.Selection([
        ('margin', 'Margin'),
        ('expense', 'Expense'),
        ('income', 'Income'),
    ],)

    @api.onchange('kpi_type')
    def _onchange_kpi_type(self):
        if self.kpi_type == 'margin' and not self.budgetable:
            raise ValidationError(_("KPI must be budgetable"))
        if self.kpi_type == 'margin' and len(self.report_id.kpi_ids.filtered(lambda x: x.kpi_type == 'margin')) > 1:
            raise ValidationError(_("Only one KPI can be margin"))
