# © 2026 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Project Mis Reports Forecast",
    "summary": """
        This module automates the calculation and
        synchronization of project budget forecasts using MIS Builder reports.
    """,
    "author": "Solvos",
    "license": "AGPL-3",
    "version": "15.0.1.0.1",
    "category": "Project",
    "website": "https://github.com/solvosci/slv-mis-builder",
    "depends": ["project_mis_report_budget"],
    "data": [
        "views/project_project_views.xml",
        "views/mis_budget.xml",
    ],
    "installable": True,
}
