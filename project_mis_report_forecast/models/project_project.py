# © 2026 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.addons.mis_builder.models.accounting_none import AccountingNone
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# Convention: a budgeted KPI (mis.budget.item -> kpi_expression_id.kpi_id)
# is named "ppto_<real_name>". Its real accounting counterpart is exposed
# under <real_name> in the dict returned by mis.report.evaluate().
BUDGET_KPI_PREFIX = "ppto_"

# Some budgeted expense KPIs are not fully represented by their own real
# counterpart alone: additional real components must be added to obtain
# the true real consumption for that budget line. Keyed by the *real*
# KPI name (i.e. the budget name with the "ppto_" prefix stripped).
# Extend this mapping whenever a new such relationship is identified.
EXPENSE_REAL_VALUE_EXTRA_COMPONENTS = {
    "materiales": ("variacion_existencias",),
}


class ProjectProject(models.Model):
    _inherit = "project.project"

    mis_report_forecast_template_id = fields.Many2one(
        "mis.report",
        string="MIS Forecast Report Template",
        copy=False,
    )
    mis_report_forecast_instance_id = fields.Many2one(
        "mis.report.instance",
        string="MIS Forecast Report",
        copy=False,
    )

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def auto_create_mis_forecast_instance(self):
        self.ensure_one()
        if not self.analytic_account_id:
            raise ValidationError(_("The Analytical Account field must be covered"))
        if not self.date_start or not self.date:
            raise ValidationError(
                _("The Dates field must be covered before generating the MIS report.")
            )
        if not self.mis_report_forecast_template_id:
            raise ValidationError(
                _("You must set a MIS Forecast Report Template before generating the report.")
            )

        instance = self.env["mis.report.instance"].create(
            {
                "name": _("Forecast: %s") % self.name,
                "report_id": self.mis_report_forecast_template_id.id,
                "comparison_mode": True,
                "date": self.date_start,
                "analytic_account_id": self.analytic_account_id.id,
            }
        )

        months_range = self.generate_monthly_dates()
        for count_month, month in enumerate(months_range):
            instance.period_ids.create(
                {
                    "report_instance_id": instance.id,
                    "name": "%s/%s" % (month.strftime("%m"), month.strftime("%Y")),
                    "source": "actuals",
                    "mode": "relative",
                    "type": "m",
                    "offset": count_month,
                    "duration": 1,
                }
            )

        total_period_id = instance.period_ids.create(
            {
                "report_instance_id": instance.id,
                "name": "TOTAL",
                "source": "sumcol",
                "mode": "none",
            }
        )
        for period in instance.period_ids.filtered(lambda x: x.source == "actuals"):
            self.env["mis.report.instance.period.sum"].create(
                {
                    "sign": "+",
                    "period_id": total_period_id.id,
                    "period_to_sum_id": period.id,
                }
            )
        self.mis_report_forecast_instance_id = instance

    # ------------------------------------------------------------------
    # write()
    # ------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)

        if "date" in vals and vals["date"]:
            for project in self.filtered(lambda x: x.mis_report_forecast_instance_id):
                instance = project.mis_report_forecast_instance_id
                if (
                    instance.period_ids
                    and len(instance.period_ids) >= 2
                    and project.date + relativedelta(months=1) > instance.period_ids[-2].date_to
                ):
                    instance.period_ids.filtered(lambda x: x.source == "sumcol").unlink()
                    instance.unlink()
                    project.auto_create_mis_forecast_instance()

        if "last_close_date" in vals and vals["last_close_date"]:
            self._update_budget_item_closed_month()
            self._update_budget_item_forecast_value()

        return res

    def action_mis_report_forecast_preview(self):
        self.ensure_one()
        return self.mis_report_forecast_instance_id.preview()

    # ------------------------------------------------------------------
    # Closed month flag
    # ------------------------------------------------------------------
    def _update_budget_item_closed_month(self):
        for project in self.filtered(lambda p: p.analytic_account_id and p.last_close_date):
            all_items = self.env["mis.budget.item"].search(
                [("analytic_account_id", "=", project.analytic_account_id.id)]
            )
            if not all_items:
                continue

            closed_items = all_items.filtered(
                lambda i: i.date_to and project.last_close_date >= i.date_to
            )
            open_items = all_items - closed_items

            if closed_items:
                closed_items.write({"closed_month": True, "forecast_value": 0.0})
            if open_items:
                open_items.write({"closed_month": False})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_float(raw_val):
        if raw_val is AccountingNone or raw_val is None or type(raw_val).__name__ == "DataError":
            return 0.0
        try:
            return float(raw_val)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _real_kpi_name(budget_kpi_name):
        """'ppto_materiales' -> 'materiales'. Falls back to the name as-is
        for budget KPIs that don't follow the 'ppto_' convention."""
        if budget_kpi_name.startswith(BUDGET_KPI_PREFIX):
            return budget_kpi_name[len(BUDGET_KPI_PREFIX):]
        return budget_kpi_name

    @classmethod
    def _real_expense_value(cls, values, budget_kpi_name):
        """Real consumption for one expense budget KPI: its own real value
        plus any additional components mapped in
        EXPENSE_REAL_VALUE_EXTRA_COMPONENTS (e.g. materiales also pulls in
        variacion_existencias, since stock variation is part of the real
        material cost even though it is a separate KPI)."""
        real_name = cls._real_kpi_name(budget_kpi_name)
        total = cls._safe_float(values.get(real_name, AccountingNone))
        for extra_name in EXPENSE_REAL_VALUE_EXTRA_COMPONENTS.get(real_name, ()):
            total += cls._safe_float(values.get(extra_name, AccountingNone))
        return total

    @staticmethod
    def _income_from_margin(expense, margin_pct):
        if expense is AccountingNone or expense is None or type(expense).__name__ == "DataError":
            return 0.0
        if margin_pct is AccountingNone or margin_pct is None or type(margin_pct).__name__ == "DataError":
            return 0.0
        try:
            expense = float(expense)
            margin_pct = float(margin_pct)
        except (TypeError, ValueError):
            return 0.0
        if margin_pct < -100:
            return 0.0
        denominator = 1 - (margin_pct / 100)
        if denominator == 0:
            return 0.0
        return abs(expense / denominator)

    # ------------------------------------------------------------------
    # Forecast calculation
    # ------------------------------------------------------------------
    def _update_budget_item_forecast_value(self):
        for project in self.filtered(lambda p: p.analytic_account_id and p.last_close_date):
            _logger.info(
                "[MIS-FORECAST] === Project %s (id=%s) | analytic=%s | last_close_date=%s ===",
                project.name, project.id, project.analytic_account_id.name, project.last_close_date,
            )

            all_items = self.env["mis.budget.item"].search(
                [("budget_id.project_id.id", "=", project.id)]
            )
            if not all_items:
                _logger.info("[MIS-FORECAST] No budget items for project %s, skipping.", project.name)
                continue

            report = project.mis_report_forecast_template_id
            if not report:
                _logger.info("[MIS-FORECAST] No forecast report template on %s, skipping.", project.name)
                continue

            company = project.analytic_account_id.company_id or self.env.company
            aep = report._prepare_aep(company)
            analytic_id = project.analytic_account_id.id

            def get_additional_move_line_filter(rec=project):
                return [("analytic_account_id", "=", analytic_id)]

            def get_additional_query_filter(query, rec=project):
                model = query.model_id.model
                model_fields = self.env[model]._fields
                if "analytic_account_id" in model_fields:
                    return [("analytic_account_id", "=", analytic_id)]
                if model == "account.analytic.line":
                    return [("account_id", "=", analytic_id)]
                if "analytic_distribution" in model_fields:
                    return [("analytic_distribution", "like", '"%s"' % analytic_id)]
                return []

            valid_items = all_items.filtered(
                lambda i: i.kpi_expression_id.kpi_id.kpi_type in ("expense", "income", "margin")
            )

            # Margin: no computation, just mirror the budgeted amount.
            margin_items = valid_items.filtered(
                lambda i: i.kpi_expression_id.kpi_id.kpi_type == "margin"
            )
            for item in margin_items:
                item.write({"actual_expense_value": item.amount, "forecast_value": item.amount})
            _logger.info("[MIS-FORECAST] margin KPI -> %s items set to their own amount", len(margin_items))

            expense_expressions = valid_items.filtered(
                lambda i: i.kpi_expression_id.kpi_id.kpi_type == "expense"
            ).mapped("kpi_expression_id")
            income_expressions = valid_items.filtered(
                lambda i: i.kpi_expression_id.kpi_id.kpi_type == "income"
            ).mapped("kpi_expression_id")

            # Full catalog of budgetable expense KPIs defined on the report,
            # regardless of whether any mis.budget.item was actually created
            # for them. Used for the income/margin derivation below, so a
            # category without budget lines (e.g. "mano de obra" never
            # budgeted for this project) is not silently dropped from the
            # real total expense.
            expense_kpi_catalog = report.kpi_ids.filtered(
                lambda k: k.kpi_type == "expense" and k.budgetable
            )
            closed_expense_by_kpi_name = {kpi.name: 0.0 for kpi in expense_kpi_catalog}

            margin_closed_items = margin_items.filtered(lambda i: i.closed_month).sorted(
                key=lambda i: i.date_from
            )

            # Both expense and income are recalculated month by month for
            # every closed period, instead of a single aggregate evaluate()
            # call: this is what makes the "expense wasn't being
            # recalculated on close" issue go away, and keeps expense/income
            # consistent with each other.
            total_income_closed = 0.0

            for margin_item in margin_closed_items:
                month_values = report.evaluate(
                    aep,
                    margin_item.date_from,
                    margin_item.date_to,
                    get_additional_move_line_filter=get_additional_move_line_filter,
                    get_additional_query_filter=get_additional_query_filter,
                )

                total_expense_month = 0.0
                for kpi in expense_kpi_catalog:
                    real_value = self._real_expense_value(month_values, kpi.name)
                    closed_expense_by_kpi_name[kpi.name] += real_value
                    total_expense_month += real_value

                income_month = self._income_from_margin(total_expense_month, margin_item.amount)
                total_income_closed += income_month

                _logger.info(
                    "[MIS-FORECAST] closed %s..%s -> total_expense=%s margin=%s income=%s",
                    margin_item.date_from, margin_item.date_to,
                    total_expense_month, margin_item.amount, income_month,
                )

            _logger.info(
                "[MIS-FORECAST] accumulated real income (sum of %s closed months)=%s",
                len(margin_closed_items), total_income_closed,
            )

            # Expense: shortfall per budget KPI, using that KPI's own
            # accumulated real consumption (materiales includes
            # variacion_existencias, per EXPENSE_REAL_VALUE_EXTRA_COMPONENTS).
            for kpi_expression in expense_expressions:
                budget_kpi_name = kpi_expression.kpi_id.name
                items_for_kpi = valid_items.filtered(lambda i: i.kpi_expression_id == kpi_expression)
                open_items = items_for_kpi.filtered(lambda i: not i.closed_month)
                closed_items = items_for_kpi.filtered(lambda i: i.closed_month)

                _logger.info(
                    "[MIS-FORECAST] --- expense KPI '%s' | items=%s (open=%s, closed=%s)",
                    budget_kpi_name, len(items_for_kpi), len(open_items), len(closed_items),
                )

                if closed_items:
                    closed_items.write({"forecast_value": 0.0})

                actual_value = closed_expense_by_kpi_name.get(budget_kpi_name, 0.0)
                items_for_kpi.write({"actual_expense_value": actual_value})

                total_budget = sum(items_for_kpi.mapped("amount"))
                shortfall = total_budget - actual_value
                _logger.info(
                    "[MIS-FORECAST] expense KPI '%s' -> actual=%s | total_budget=%s | shortfall=%s",
                    budget_kpi_name, actual_value, total_budget, shortfall,
                )

                if not open_items or shortfall <= 0.0:
                    open_items.write({"forecast_value": 0.0})
                    continue

                open_budget = sum(open_items.mapped("amount"))
                if open_budget > 0.0:
                    for item in open_items:
                        item.forecast_value = shortfall * item.amount / open_budget
                        _logger.info(
                            "[MIS-FORECAST]   item %s (date_from=%s, amount=%s) -> forecast_value=%s",
                            item.id, item.date_from, item.amount, item.forecast_value,
                        )
                else:
                    share = shortfall / len(open_items)
                    for item in open_items:
                        item.forecast_value = share

            expense_open_items = valid_items.filtered(
                lambda i: i.kpi_expression_id.kpi_id.kpi_type == "expense" and not i.closed_month
            )
            total_open_expense_forecast = sum(expense_open_items.mapped("forecast_value"))
            _logger.info(
                "[MIS-FORECAST] remaining expense (sum of open months' forecast_value)=%s",
                total_open_expense_forecast,
            )

            # Income: closed months use the margin-derived total; open
            # months are prorated proportionally to each month's expense
            # forecast (falling back to an even split with no expense).
            for kpi_expression in income_expressions:
                budget_kpi_name = kpi_expression.kpi_id.name
                items_for_kpi = valid_items.filtered(lambda i: i.kpi_expression_id == kpi_expression)
                open_items = items_for_kpi.filtered(lambda i: not i.closed_month)
                closed_items = items_for_kpi.filtered(lambda i: i.closed_month)

                _logger.info(
                    "[MIS-FORECAST] --- income KPI '%s' | items=%s (open=%s, closed=%s)",
                    budget_kpi_name, len(items_for_kpi), len(open_items), len(closed_items),
                )

                if closed_items:
                    closed_items.write({"forecast_value": 0.0})

                actual_value = total_income_closed
                items_for_kpi.write({"actual_expense_value": actual_value})

                total_budget = sum(items_for_kpi.mapped("amount"))
                shortfall = total_budget - actual_value
                _logger.info(
                    "[MIS-FORECAST] income KPI '%s' -> actual=%s | total_budget=%s | shortfall=%s",
                    budget_kpi_name, actual_value, total_budget, shortfall,
                )

                if not open_items or shortfall <= 0.0:
                    open_items.write({"forecast_value": 0.0})
                    continue

                if total_open_expense_forecast > 0.0:
                    proportion = shortfall / total_open_expense_forecast
                    for item in open_items:
                        month_expense = sum(
                            expense_open_items.filtered(
                                lambda e: e.date_from == item.date_from
                            ).mapped("forecast_value")
                        )
                        item.forecast_value = month_expense * proportion
                        _logger.info(
                            "[MIS-FORECAST]   item %s (date_from=%s) month_expense=%s -> forecast_value=%s",
                            item.id, item.date_from, month_expense, item.forecast_value,
                        )
                else:
                    share = shortfall / len(open_items)
                    for item in open_items:
                        item.forecast_value = share
