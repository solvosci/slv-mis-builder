# © 2024 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    expense_account_ids = fields.Many2many(
        related="company_id.expense_account_ids", readonly=False
    )
    expense_debit_account_ids = fields.Many2many(
        related="company_id.expense_debit_account_ids", readonly=False
    )

class ResCompany(models.Model):
    _inherit = "res.company"

    expense_account_ids = fields.Many2many(
        'account.account',
    )
    expense_debit_account_ids = fields.Many2many(
        'account.account',
        'expense_debit_account_rel',
    )
