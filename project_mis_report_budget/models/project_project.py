# © 2024 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, _
from dateutil.relativedelta import relativedelta


class ProjectProject(models.Model):
    _inherit = "project.project"

    mis_budget_ids = fields.One2many('mis.budget', 'project_id', string="Budgets")

    def auto_create_mis_instance(self):
        super().auto_create_mis_instance()

        margin_kpi_ids = self.mis_report_template_id.kpi_ids.filtered(lambda x: x.kpi_type == 'margin')
        expression_id = margin_kpi_ids and margin_kpi_ids.expression_ids[0].id or False

        if expression_id:
            budget_id = self.env['mis.budget'].create({
                'name': '%s - %s' % (self.name, _('MARGINS')),
                'project_id': self.id,
                'report_id': self.mis_report_template_id.id,
                'date_from': self.date_start.replace(day=1),
                'date_to': self.date.replace(day=1) + relativedelta(months=2) - relativedelta(days=1),
            })

            months = self.generate_monthly_dates()

            for month in months:
                month_end = month.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)

                budget_id.item_ids.create({
                    'name': _('MARGINS'),
                    'budget_id': budget_id.id,
                    'kpi_expression_id': expression_id,
                    'date_from': month,
                    'date_to': month_end,
                    'amount': self.margin * 100,
                    'analytic_account_id': self.analytic_account_id.id
                })
