# © 2025 Solvos Consultoría Informática (<http://www.solvos.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "MIS Builder Report Export Xlsx",
    "summary": """
        Adds new XLSX export options to the MIS Builder module.
    """,
    "author": "Solvos",
    "license": "AGPL-3",
    "version": "15.0.1.3.0",
    "category": "Project",
    "website": "https://github.com/solvosci/slv-mis-builder",
    "depends": [
        "mis_builder",
        "mrp_project_analytic",
        "project_close_forecast_date",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "reports/report_view.xml",
        "views/project_project_menu.xml",
        "wizards/project_mis_export_wizard_views.xml",
    ],
    "installable": True,
}
