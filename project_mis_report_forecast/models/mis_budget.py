# © 2026 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class MisBudgetItem(models.Model):
    _inherit = "mis.budget.item"

    closed_month = fields.Boolean(
        string="Closed Month",
        default=False,
        help="True if this budget item's period has been closed "
            "(date_to <= project last_close_date). "
            "Updated automatically when last_close_date changes on the project.",
    )
    forecast_value = fields.Float(
        string="Forecast Value",
        help="Forecast value for this budget item.",
    )

    actual_expense_value = fields.Float(
        string="Actual Expense Value",
        help="Actual expense value for this budget item.",
    )

