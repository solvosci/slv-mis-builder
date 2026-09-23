**KPI Naming Conventions**
To correlate budgeted amounts with actual accounting data, the forecasting engine relies on a strict naming convention between budget KPIs and report KPIs:

* **Budget KPI Prefix**: All budget KPIs should be prefixed with ``ppto_`` (defined by ``BUDGET_KPI_PREFIX``).
* **Automatic Mapping**: The system automatically strips the prefix to find the corresponding actual expense or revenue KPI.

Examples:
* A budget KPI named ``ppto_materiales`` automatically maps to the actual expense KPI ``materiales``.
* A budget KPI named ``ppto_viajes_y_otros`` maps to ``viajes_y_otros``.

Fallback Behavior:
If a budget KPI does not follow the ``ppto_`` convention, the function ``_real_kpi_name`` falls back to using the exact string as the target KPI name without modifications.

Handling Unbudgeted vs. Open Months
* **Proportional Prorating**: Shortfalls are distributed across open months that have a budgeted amount (``amount > 0.0``).
* **Zero-Budget Months**: Open months with ``amount = 0.0`` are reset to ``0.0`` forecast value.
* **Unbudgeted Target Allocation**: If no future open months contain a specific budget for a given KPI, the engine assigns the total remaining shortfall to the first open month with project activity, ensuring no unconsumed budget is lost in the forecast calculation.
