# © 2025 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.mis_builder_report_drilldown_custom.models.expression_evaluator import ProjectKpiExpressionEvaluator

from odoo import models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    # Duplicated code https://github.com/OCA/mis-builder/blob/093fdb95a6fb06c35215bb8306c4a4554a5f6e64/mis_builder/models/mis_report_instance.py#L785
    # with the only difference that we are using ProjectKpiExpressionEvaluator instead of ExpressionEvaluator
    def _add_column_custom(self, aep, kpi_matrix, period, label, description):
        if not period.date_from or not period.date_to:
            raise UserError(
                _("Column %s with move lines source must have from/to dates.")
                % (period.name,)
            )
        expression_evaluator = ProjectKpiExpressionEvaluator(
            aep,
            period.date_from,
            period.date_to,
            period._get_additional_move_line_filter(),
            period._get_aml_model_name(),
        )
        self.report_id._declare_and_compute_period(
            expression_evaluator,
            kpi_matrix,
            period.id,
            label,
            description,
            period.subkpi_ids,
            period._get_additional_query_filter,
            no_auto_expand_accounts=self.no_auto_expand_accounts,
        )

    def _add_column(self, aep, kpi_matrix, period, label, description):
        if period.source == 'actuals':
            return self._add_column_custom(
                aep, kpi_matrix, period, label, description
            )
        return super()._add_column(aep, kpi_matrix, period, label, description)

    def drilldown(self, arg):
        self.ensure_one()
        expr = arg.get("expr")
        kpi_id = self.env['mis.report.kpi'].sudo().browse(arg.get("kpi_id")).exists()
        if expr == 'custom':
            period_id = arg.get("period_id")
            account_id = self.analytic_account_id
            if period_id:
                period = self.env["mis.report.instance.period"].browse(period_id)
                domain = eval(kpi_id.drill_expression_id.domain)
                domain = expression.AND(
                    [
                        domain,
                        [
                            (kpi_id.drill_field_account_id.name, '=', account_id.id),
                            (kpi_id.drill_expression_id.date_field.name, '>=', period.date_from),
                            (kpi_id.drill_expression_id.date_field.name, '<=', period.date_to),
                        ]
                    ]
                )

                return {
                    "name": 'Custom',
                    "domain": domain,
                    "type": "ir.actions.act_window",
                    "res_model": kpi_id.drill_model_id.model,
                    "views": [[kpi_id.drill_view_id.id, "list"], [False, "form"]],
                    "view_mode": "list",
                    "target": "current",
                    "context": {"active_test": False},
                }
            else:
                return False
        return super().drilldown(arg)
