# © 2026 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
from odoo.addons.mis_builder.models.accounting_none import AccountingNone
from odoo import fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

class ProjectProject(models.Model):
    _inherit = "project.project"

    mis_report_forecast_template_id = fields.Many2one(
        'mis.report', string="MIS Forecast Report Template",
        copy=False,
        )
    mis_report_forecast_instance_id = fields.Many2one(
        'mis.report.instance', string="MIS Forecast Report",
        copy=False,
        )

    def auto_create_mis_forecast_instance(self):
        self.ensure_one()
        if not self.analytic_account_id:
            raise ValidationError(
                _('The Analytical Account field must be covered')
            )
        if not self.date_start or not self.date:
            raise ValidationError(
                _('The Dates field must be covered before generating the MIS report.')
            )
        if not self.mis_report_forecast_template_id:
            raise ValidationError(
                _('You must set a MIS Forecast Report Template before generating the report.')
            )

        instance = self.env['mis.report.instance'].create({
            'name': _('Forecast: %s') % self.name,
            'report_id': self.mis_report_forecast_template_id.id,
            'comparison_mode': True,
            'date': self.date_start,
            'analytic_account_id': self.analytic_account_id.id,
        })

        months_range = self.generate_monthly_dates()
        count_month = 0
        for month in months_range:
            instance.period_ids.create({
                'report_instance_id': instance.id,
                'name': '%s/%s' % (month.strftime("%m"), month.strftime("%Y")),
                'source': 'actuals',
                'mode': 'relative',
                'type': 'm',
                'offset': count_month,
                'duration': 1,
            })
            count_month += 1

        total_period_id = instance.period_ids.create({
            'report_instance_id': instance.id,
            'name': 'TOTAL',
            'source': 'sumcol',
            'mode': 'none',
        })
        for period in instance.period_ids.filtered(
                lambda x: x.source == 'actuals'):
            self.env['mis.report.instance.period.sum'].create({
                'sign': '+',
                'period_id': total_period_id.id,
                'period_to_sum_id': period.id,
            })
        self.mis_report_forecast_instance_id = instance

    def write(self, vals):
        res = super().write(vals)
        if 'date' in vals and vals['date']:
            for record in self.filtered(
                    lambda x: x.mis_report_forecast_instance_id):
                instance = record.mis_report_forecast_instance_id
                if (
                    instance.period_ids
                    and len(instance.period_ids) >= 2
                    and record.date + relativedelta(months=1) > instance.period_ids[-2].date_to
                ):
                    instance.period_ids.filtered(
                        lambda x: x.source == 'sumcol').unlink()
                    instance.unlink()
                    record.auto_create_mis_forecast_instance()

        if "last_close_date" in vals and vals["last_close_date"]:
            self._update_budget_item_closed_month()
            self._update_budget_item_forecast_value()

        return res

    def action_mis_report_forecast_preview(self):
        self.ensure_one()
        return self.mis_report_forecast_instance_id.preview()

    def _update_budget_item_closed_month(self):
        for record in self.filtered(
            lambda p: p.analytic_account_id and p.last_close_date
        ):
            all_items = self.env["mis.budget.item"].search(
                [("analytic_account_id", "=", record.analytic_account_id.id)]
            )
            if not all_items:
                continue

            closed_items = all_items.filtered(
                lambda i: i.date_to and record.last_close_date >= i.date_to
            )
            open_items = all_items - closed_items

            if closed_items:
                closed_items.write({
                    "closed_month": True,
                    "forecast_value": 0.0,
                })
            if open_items:
                open_items.write({"closed_month": False})

    @staticmethod
    def _forecast_safe_float(raw_val):
        if raw_val is AccountingNone or raw_val is None or type(raw_val).__name__ == "DataError":
            return 0.0
        try:
            return abs(float(raw_val))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _forecast_income_from_margin(gastos, margen):
        if gastos is AccountingNone or gastos is None or type(gastos).__name__ == "DataError":
            return 0.0
        if margen is AccountingNone or margen is None or type(margen).__name__ == "DataError":
            return 0.0
        try:
            gastos = float(gastos)
            margen = float(margen)
        except (TypeError, ValueError):
            return 0.0
        if margen < -100:
            return 0.0
        denom = 1 - (margen / 100)
        if denom == 0:
            return 0.0
        return abs(gastos / denom)

    def _update_budget_item_forecast_value(self):
        for record in self.filtered(lambda p: p.analytic_account_id and p.last_close_date):
            _logger.info(
                "[MIS-FORECAST] === Proyecto %s (id=%s) | analytic=%s | last_close_date=%s ===",
                record.name, record.id, record.analytic_account_id.name, record.last_close_date,
            )

            all_items = self.env["mis.budget.item"].search(
                [("budget_id.project_id.id", "=", record.id)]
            )
            if not all_items:
                _logger.info("[MIS-FORECAST] Sin budget items para el proyecto %s, se omite.", record.name)
                continue

            report = record.mis_report_forecast_template_id
            if not report:
                _logger.info("[MIS-FORECAST] Sin plantilla MIS forecast en %s, se omite.", record.name)
                continue

            company = record.analytic_account_id.company_id or self.env.company
            aep = report._prepare_aep(company)
            analytic_id = record.analytic_account_id.id

            def _get_additional_move_line_filter(rec=record):
                return [("analytic_account_id", "=", analytic_id)]

            def _get_additional_query_filter(query, rec=record):
                model = query.model_id.model
                fields_on_model = self.env[model]._fields
                if "analytic_account_id" in fields_on_model:
                    return [("analytic_account_id", "=", analytic_id)]
                if model == "account.analytic.line":
                    return [("account_id", "=", analytic_id)]
                if "analytic_distribution" in fields_on_model:
                    return [("analytic_distribution", "like", '"%s"' % analytic_id)]
                return []

            real_data_cutoff = fields.Date.today()
            _logger.info(
                "[MIS-FORECAST] last_close_date=%s | real_data_cutoff (gasto)=%s",
                record.last_close_date, real_data_cutoff,
            )

            real_values = report.evaluate(
                aep,
                record.date_start,
                real_data_cutoff,
                get_additional_move_line_filter=_get_additional_move_line_filter,
                get_additional_query_filter=_get_additional_query_filter,
            )
            _logger.info(
                "[MIS-FORECAST] real_values (gasto, hasta hoy): gastos=%s materiales=%s",
                real_values.get("gastos"), real_values.get("materiales"),
            )

            real_values_closed = report.evaluate(
                aep,
                record.date_start,
                record.last_close_date,
                get_additional_move_line_filter=_get_additional_move_line_filter,
                get_additional_query_filter=_get_additional_query_filter,
            )
            gastos_closed = real_values_closed.get("gastos", AccountingNone)
            margen_closed = real_values_closed.get("margen", AccountingNone)
            _logger.info(
                "[MIS-FORECAST] real_values_closed (ingreso, solo hasta last_close_date): gastos=%s margen=%s",
                gastos_closed, margen_closed,
            )

            valid_items = all_items.filtered(
                lambda i: i.kpi_expression_id.kpi_id.kpi_type in ("expense", "income", "margin")
            )

            for kpi_expression in valid_items.mapped("kpi_expression_id"):
                kpi_type = kpi_expression.kpi_id.kpi_type
                ppto_kpi_name = kpi_expression.kpi_id.name
                real_kpi_name = (
                    ppto_kpi_name[len("ppto_"):]
                    if ppto_kpi_name.startswith("ppto_")
                    else ppto_kpi_name
                )

                items_for_kpi = valid_items.filtered(lambda i: i.kpi_expression_id == kpi_expression)
                open_items_for_kpi = items_for_kpi.filtered(lambda i: not i.closed_month)
                closed_items_for_kpi = items_for_kpi.filtered(lambda i: i.closed_month)

                _logger.info(
                    "[MIS-FORECAST] --- KPI '%s' (%s) | items=%s (abiertos=%s, cerrados=%s)",
                    ppto_kpi_name, kpi_type, len(items_for_kpi), len(open_items_for_kpi), len(closed_items_for_kpi),
                )

                if kpi_type == "margin":
                    for item in items_for_kpi:
                        item.write({
                            "actual_expense_value": item.amount,
                            "forecast_value": item.amount,
                        })
                        _logger.info(
                            "[MIS-FORECAST] KPI margin '%s' -> item %s (date_from=%s) actual_expense_value=forecast_value=amount=%s",
                            ppto_kpi_name, item.id, item.date_from, item.amount,
                        )
                    continue

                if closed_items_for_kpi:
                    closed_items_for_kpi.write({"forecast_value": 0.0})

                if kpi_type == "expense":
                    raw_val = real_values.get(real_kpi_name, AccountingNone)
                    actual_val = self._forecast_safe_float(raw_val)
                    _logger.info(
                        "[MIS-FORECAST] KPI expense '%s' -> raw_val=%r actual_val=%s",
                        ppto_kpi_name, raw_val, actual_val,
                    )
                else:
                    actual_val = self._forecast_income_from_margin(gastos_closed, margen_closed)
                    _logger.info(
                        "[MIS-FORECAST] KPI income '%s' -> gastos_closed=%s margen_closed=%s actual_val=%s",
                        ppto_kpi_name, gastos_closed, margen_closed, actual_val,
                    )

                items_for_kpi.write({"actual_expense_value": actual_val})

                total_budget = sum(items_for_kpi.mapped("amount"))
                shortfall = total_budget - actual_val
                _logger.info(
                    "[MIS-FORECAST] KPI '%s' -> actual_val=%s | total_budget=%s | shortfall=%s",
                    ppto_kpi_name, actual_val, total_budget, shortfall,
                )

                if not open_items_for_kpi or shortfall <= 0.0:
                    _logger.info(
                        "[MIS-FORECAST] KPI '%s' sin meses abiertos o sin shortfall -> forecast_value=0.0",
                        ppto_kpi_name,
                    )
                    open_items_for_kpi.write({"forecast_value": 0.0})
                    continue

                if kpi_type == "expense":
                    open_budget = sum(open_items_for_kpi.mapped("amount"))
                    if open_budget > 0.0:
                        for item in open_items_for_kpi:
                            item.forecast_value = shortfall * item.amount / open_budget
                    else:
                        open_items_for_kpi.write({"forecast_value": 0.0})

                else:
                    open_count = len(open_items_for_kpi)
                    for item in open_items_for_kpi:
                        item.forecast_value = shortfall / open_count
                        _logger.info(
                            "[MIS-FORECAST]   item %s (date_from=%s) -> forecast_value=%s",
                            item.id, item.date_from, item.forecast_value,
                        )
