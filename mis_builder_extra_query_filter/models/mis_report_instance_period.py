# © 2022 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3 - See https://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, models


class MisReportInstancePeriod(models.Model):
    _inherit = "mis.report.instance.period"

    @api.multi
    def _get_additional_query_filter(self, query):
        self.ensure_one()
        return self._get_additional_query_filter_dict(
            self.report_instance_id.analytic_account_id.id
        ).get(query.model_id.id, [])

    @api.model
    def _get_additional_query_filter_dict(self, analytic_account_id):
        """
        Add/extends when new models should be covered
        """
        return {
            self.env.ref("mis_builder_budget.model_mis_budget_item").id: [("analytic_account_id", "=", analytic_account_id)],
            self.env.ref("analytic.model_account_analytic_line").id: [("account_id", "=", analytic_account_id)],
        }
