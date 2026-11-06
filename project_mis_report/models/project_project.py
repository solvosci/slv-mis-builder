# © 2024 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class ProjectProject(models.Model):
    _inherit = "project.project"

    mis_report_template_id = fields.Many2one('mis.report', string="Mis Report Template")
    pl_report_template_id = fields.Many2one('mis.report', string="Profit and Loss Report Template")
    mis_report_instance_id = fields.Many2one('mis.report.instance', string="Mis Report")
    pl_report_instance_id = fields.Many2one('mis.report.instance', string="Profit and Loss Report Instance")
    is_group_account_manager = fields.Boolean(compute='_compute_is_group_account_manager')
    is_group_project_manager = fields.Boolean(compute='_compute_is_group_project_manager')

    def _compute_is_group_project_manager(self):
        for record in self:
            record.is_group_project_manager = record.user_has_groups("project.group_project_manager")

    def _compute_is_group_account_manager(self):
        for record in self:
            record.is_group_account_manager = record.user_has_groups("account.group_account_manager")
    def generate_monthly_dates(self):
        result = []
        current_date = self.date_start.replace(day=1)
        end_date = self.date.replace(day=1)
        end_date += relativedelta(months=1)

        while current_date <= end_date:
            result.append(current_date)
            current_date += relativedelta(months=1)
        return result

    def _create_mis_report_instance_helper(self, template_id, name_prefix):
        self.ensure_one()
        if not self.analytic_account_id:
            raise ValidationError(
                _('The Analytical Account field must be covered')
            )
        if not self.date_start or not self.date:
            raise ValidationError(_('The Dates field must be covered before generating the MIS report.'))

        instance_id = self.env['mis.report.instance'].create({
            'name': _('%s: %s') % (name_prefix, self.name),
            'report_id': template_id.id,
            'comparison_mode': True,
            'date': self.date_start,
            'analytic_account_id': self.analytic_account_id.id,
        })

        months_range = self.generate_monthly_dates()

        for count_month, month in enumerate(months_range):
            self.env['mis.report.instance.period'].create({
                'report_instance_id': instance_id.id,
                'name': '%s/%s' % (month.strftime("%m"), month.strftime("%Y")),
                'source': 'actuals',
                'mode': 'relative',
                'type': 'm',
                'offset': count_month,
                'duration': 1,
            })

        total_period_id = self.env['mis.report.instance.period'].create({
            'report_instance_id': instance_id.id,
            'name': 'TOTAL',
            'source': 'sumcol',
            'mode': 'none'
        })
        for period_id in instance_id.period_ids.filtered(lambda x: x.source == 'actuals'):
            self.env['mis.report.instance.period.sum'].create({
                'sign': '+',
                'period_id': total_period_id.id,
                'period_to_sum_id': period_id.id,
            })

        return instance_id

    def auto_create_mis_instance(self):
        self.ensure_one()
        self.mis_report_instance_id = self._create_mis_report_instance_helper(
            self.mis_report_template_id, _('Project')
        )

    def auto_create_pl_instance(self):
        self.ensure_one()
        self.pl_report_instance_id = self._create_mis_report_instance_helper(
            self.pl_report_template_id, _('Profit and Loss')
        )

    def write(self, vals):
        res = super().write(vals)
        if 'date' in vals and vals['date']:
            for record in self:
                if record.mis_report_instance_id and record.date + relativedelta(months=1) > record.mis_report_instance_id.period_ids[-2].date_to:
                    record.mis_report_instance_id.period_ids.filtered(lambda x: x.source == 'sumcol').unlink()
                    record.mis_report_instance_id.unlink()
                    record.auto_create_mis_instance()
                if record.pl_report_instance_id and record.date + relativedelta(months=1) > record.pl_report_instance_id.period_ids[-2].date_to:
                    record.pl_report_instance_id.period_ids.filtered(lambda x: x.source == 'sumcol').unlink()
                    record.pl_report_instance_id.unlink()
                    record.auto_create_pl_instance()
        return res

    def action_mis_report_preview(self):
        self.ensure_one()
        return self.mis_report_instance_id.preview()
