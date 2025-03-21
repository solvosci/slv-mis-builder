# © 2025 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, _


class MisReportKpi(models.Model):
    _inherit = "mis.report.kpi"

    drill_expression_id = fields.Many2one("mis.report.query")
    drill_model_id = fields.Many2one("ir.model", related="drill_expression_id.model_id")
    drill_model_name = fields.Char(related="drill_model_id.model")
    drill_view_id = fields.Many2one("ir.ui.view")
    drill_field_account_id = fields.Many2one("ir.model.fields")
