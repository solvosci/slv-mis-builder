# © 2024 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, _
from dateutil.relativedelta import relativedelta


class ProjectProject(models.Model):
    _inherit = "project.project"

    mis_budget_ids = fields.One2many('mis.budget', 'project_id', string="Budgets")
    last_margin = fields.Float()

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
            budget_id.action_confirm()

    def write(self, vals):
        res = super().write(vals)
        if 'last_close_date' in vals and vals['last_close_date']:
            for record in self:
                real_expenses = 0
                real_debit_expenses = 0
                expenses = 0
                hour_expenses = 0

                budget_ids = record.mis_budget_ids.filtered(lambda x: x.state == 'confirmed')
                incomes = sum(budget_ids.item_ids.filtered(lambda x: x.kpi_expression_id.kpi_id.kpi_type == 'income').mapped('amount'))
                expenses = sum(budget_ids.item_ids.filtered(lambda x: x.kpi_expression_id.kpi_id.kpi_type == 'expense').mapped('amount'))
                past_expenses = sum(budget_ids.item_ids.filtered(lambda x: x.date_to <= record.last_close_date and x.kpi_expression_id.kpi_id.kpi_type == 'expense').mapped('amount'))
                expenses -= past_expenses

                hour_expenses = -(sum(self.env['account.analytic.line'].search(['&',
                                                    ('date', '<=', record.last_close_date),
                                                    ('project_id', '=', record.id),
                ]).mapped('amount')))

                line_ids = self.env['account.move.line'].sudo().search(['&', '&',
                                                    ('account_id', 'in', record.company_id.expense_account_ids.ids),
                                                    ('date', '<=', record.last_close_date),
                                                    ('analytic_account_id', '=', record.analytic_account_id.id),
                ])
                line_debit_ids = self.env['account.move.line'].sudo().search([
                                                    ('account_id', 'in', record.company_id.expense_debit_account_ids.ids),
                                                    ('date', '<=', record.last_close_date),
                                                    ('analytic_account_id', '=', record.analytic_account_id.id),
                                                    ('analytic_mrp_from_child', '!=', True),
                ])
                real_expenses = sum(line_ids.mapped('debit')) - sum(line_ids.mapped('credit'))
                real_debit_expenses = sum(line_debit_ids.mapped('debit'))
                all_expenses = real_expenses + real_debit_expenses + expenses + hour_expenses

                if incomes:
                    record.last_margin = ((incomes - all_expenses) / incomes)
                    new_margin = round(100 * record.last_margin, 2)

                    budget_item_id = budget_ids.item_ids.search(['&', ('kpi_expression_id.kpi_id.kpi_type', '=', 'margin'), ('date_to', '>=', record.last_close_date)])
                    budget_item_id.sudo().write({
                        'amount': new_margin
                    })
        return res
