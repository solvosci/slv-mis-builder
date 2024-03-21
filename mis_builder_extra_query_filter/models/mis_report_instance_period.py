# © 2022 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3 - See https://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, models


class MisReportInstancePeriod(models.Model):
    _inherit = "mis.report.instance.period"

    def _get_additional_query_filter(self, query):
        self.ensure_one()
        # TODO refactor to expression.AND
        return self._get_additional_query_filter_dict(
            self.report_instance_id.analytic_account_id.id
        ).get(query.model_id.id, []) + super()._get_additional_query_filter(query)

    @api.model
    def _get_additional_query_filter_dict(self, analytic_account_id):
        """
        Add/extends when new models should be covered
        """
        ret_dict = {
            self.env.ref("mis_builder_budget.model_mis_budget_item").id: [("analytic_account_id", "=", analytic_account_id)],
            self.env.ref("analytic.model_account_analytic_line").id: [("account_id", "=", analytic_account_id)],
        }
        pol = self.env.ref("purchase.model_purchase_order_line", raise_if_not_found=False)
        if pol:
            ret_dict.update({pol.id: [("account_analytic_id", "=", analytic_account_id)]})
        return ret_dict
