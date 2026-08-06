# © 2026 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
from odoo.addons.mis_builder.models.accounting_none import AccountingNone
from odoo import fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class ProjectProject(models.Model):
    _inherit = "project.project"

    mis_report_forecast_template_id = fields.Many2one(
        'mis.report', string="MIS Forecast Report Template")
    mis_report_forecast_instance_id = fields.Many2one(
        'mis.report.instance', string="MIS Forecast Report")

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
                lambda i: i.date_to <= record.last_close_date
            )
            open_items = all_items - closed_items

            if closed_items:
                closed_items.write({"closed_month": True})
            if open_items:
                open_items.write({"closed_month": False})

    def _update_budget_item_forecast_value(self):
        for record in self.filtered(lambda p: p.analytic_account_id):
            all_items = self.env["mis.budget.item"].search(
                [("budget_id.project_id.id", "=", record.id)]
            )
            if not all_items:
                continue

            report = record.mis_report_forecast_template_id
            if not report:
                continue

            company = record.analytic_account_id.company_id or self.env.company
            aep = report._prepare_aep(company)

            analytic_id = record.analytic_account_id.id

            def _get_additional_move_line_filter(rec=record):
                return [("analytic_account_id", "=", analytic_id)]

            def _get_additional_query_filter(query, rec=record):
                if "analytic_account_id" in self.env[query.model_id.model]._fields:
                    return [("analytic_account_id", "=", analytic_id)]
                if query.model_id.model == "account.analytic.line":
                    return [("account_id", "=", analytic_id)]
                return []

            date_to_eval = record.date or record.last_close_date
            real_values = report.evaluate(
                aep,
                record.date_start,
                date_to_eval,
                get_additional_move_line_filter=_get_additional_move_line_filter,
                get_additional_query_filter=_get_additional_query_filter,
            )

            for kpi_expression in all_items.mapped("kpi_expression_id"):
                items_for_kpi = all_items.filtered(
                    lambda i: i.kpi_expression_id == kpi_expression
                )
                open_items_for_kpi = items_for_kpi.filtered(
                    lambda i: not i.closed_month
                )

                ppto_kpi_name = kpi_expression.kpi_id.name
                real_kpi_name = (
                    ppto_kpi_name.replace("ppto_", "", 1)
                    if ppto_kpi_name.startswith("ppto_")
                    else ppto_kpi_name
                )
                actual_expense = real_values.get(real_kpi_name, AccountingNone)
                if actual_expense is AccountingNone or actual_expense is None:
                    actual_expense = 0.0

                actual_expense = abs(actual_expense)
                items_for_kpi.write({"actual_expense_value": actual_expense})

                total_budget = sum(items_for_kpi.mapped("amount"))
                expense_shortfall = total_budget - actual_expense
                open_budget_shortfall = sum(open_items_for_kpi.mapped("amount"))

                if not open_items_for_kpi:
                    continue
                if expense_shortfall > 0.0 and open_budget_shortfall > 0.0:
                    for item in open_items_for_kpi:
                        item.forecast_value = (
                            expense_shortfall * item.amount / open_budget_shortfall
                        )
                else:
                    open_items_for_kpi.write({"forecast_value": 0.0})
