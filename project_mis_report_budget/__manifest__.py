# © 2024 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Project Mis Report Budget",
    "summary": """
        Link Project with Mis Report Budget
    """,
    "author": "Solvos",
    "license": "AGPL-3",
    "version": "15.0.2.2.4",
    "category": "Project",
    "website": "https://github.com/solvosci/slv-mis-builder",
    "depends": [
        "project_mis_report",
        "mis_builder_budget",
        "project_profitability_fields",
        "mrp_project_analytic"
    ],
    "data": [
        "views/mis_budget_views.xml",
        "views/project_project_views.xml",
        "views/mis_report_kpi_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
}
