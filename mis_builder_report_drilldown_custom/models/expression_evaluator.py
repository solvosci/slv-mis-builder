# © 2025 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.mis_builder.models.expression_evaluator import ExpressionEvaluator
from odoo.addons.mis_builder.models.mis_safe_eval import mis_safe_eval


class ProjectKpiExpressionEvaluator(ExpressionEvaluator):
    def __init__(self, aep, date_from, date_to, additional_move_line_filter=None, aml_model=None, ):
        super().__init__(
            aep=aep,
            date_from=date_from,
            date_to=date_to,
            additional_move_line_filter=additional_move_line_filter,
            aml_model=aml_model,
        )

    def eval_expressions(self, expressions, locals_dict):
        vals = []
        drilldown_args = []
        name_error = False
        custom = False
        for expression in expressions:
            expr = expression and expression.name or "AccountingNone"
            if self.aep:
                replaced_expr = self.aep.replace_expr(expr)
            else:
                replaced_expr = expr
            val = mis_safe_eval(replaced_expr, locals_dict)
            vals.append(val)
            if expression and expression.kpi_id and expression.kpi_id.drill_expression_id:
                custom = True
                drilldown_args.append({"expr": "custom"})
        if custom:
            return vals, drilldown_args, name_error
        else:
            return super().eval_expressions(expressions, locals_dict)
