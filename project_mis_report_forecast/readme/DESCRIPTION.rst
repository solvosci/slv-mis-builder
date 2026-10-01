This module automates the calculation and synchronization of project budget forecasts using **MIS Builder** reports.

Key Capabilities:
* Dynamically manages budget line status (open vs. closed) based on the project's last closing date (``last_close_date``).
* Evaluates closed periods period-by-period to retrieve accurate historical expenses and revenues.
* Calculates shortfalls between original budget and real actuals, prorating remaining forecast values across open future months.
* Automatically updates or generates forecast report instances (``mis.report.instance``) upon project changes.
