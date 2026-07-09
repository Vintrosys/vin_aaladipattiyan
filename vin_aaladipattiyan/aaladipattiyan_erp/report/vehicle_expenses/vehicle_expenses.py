import frappe
from frappe import _
from frappe.utils import flt, getdate, get_first_day, get_last_day
from datetime import timedelta, date


def execute(filters=None):
    filters = frappe._dict(filters or {})

    start_date, end_date = get_period_dates(filters)
    if not start_date or not end_date:
        frappe.throw(_("Please set a valid Fiscal Year or Date Range."))

    report_period = filters.get("report_period", "Monthly")
    group_by = filters.get("group_by", "")
    expense_type = filters.get("expense_type", "Both")

    # Fetch raw data using efficient single SQL query
    raw_data = get_vehicle_log_data(filters, start_date, end_date)

    if group_by == "Vehicle":
        columns = get_grouped_columns()
        data = aggregate_by_vehicle(raw_data, expense_type)
    else:
        columns = get_columns()
        data = apply_expense_type_filter(raw_data, expense_type)

    # Generate periods and chart
    periods = generate_periods(start_date, end_date, report_period)
    chart = get_chart_data(raw_data, periods, report_period, expense_type)

    return columns, data, None, chart


# ──────────────────────────────────────────────
# Columns
# ──────────────────────────────────────────────

def get_columns():
    """Standard detail-level columns."""
    return [
        {
            "fieldname": "vehicle",
            "fieldtype": "Link",
            "label": _("Vehicle"),
            "options": "Vehicle",
            "width": 150,
        },
        {"fieldname": "make", "fieldtype": "Data", "label": _("Make"), "width": 100},
        {"fieldname": "model", "fieldtype": "Data", "label": _("Model"), "width": 80},
        {"fieldname": "location", "fieldtype": "Data", "label": _("Location"), "width": 100},
        {
            "fieldname": "log_name",
            "fieldtype": "Link",
            "label": _("Vehicle Log"),
            "options": "Vehicle Log",
            "width": 100,
        },
        {"fieldname": "odometer", "fieldtype": "Int", "label": _("Odometer Value"), "width": 120},
        {"fieldname": "date", "fieldtype": "Date", "label": _("Date"), "width": 100},
        {"fieldname": "fuel_qty", "fieldtype": "Float", "label": _("Fuel Qty"), "width": 80},
        {"fieldname": "fuel_price", "fieldtype": "Float", "label": _("Fuel Price"), "width": 100},
        {"fieldname": "fuel_expense", "fieldtype": "Currency", "label": _("Fuel Expense"), "width": 150},
        {
            "fieldname": "service_expense",
            "fieldtype": "Currency",
            "label": _("Service Expense"),
            "width": 150,
        },
        {
            "fieldname": "driver_wages",
            "fieldtype": "Currency",
            "label": _("Driver Wages"),
            "width": 150,
        },
        {
            "fieldname": "fastag_amount",
            "fieldtype": "Currency",
            "label": _("Fastag Amount"),
            "width": 150,
        },
        {
            "fieldname": "total_expense",
            "fieldtype": "Currency",
            "label": _("Total Expense"),
            "width": 150,
        },
        {
            "fieldname": "employee",
            "fieldtype": "Link",
            "label": _("Employee"),
            "options": "Employee",
            "width": 150,
        },
    ]


def get_grouped_columns():
    """Columns for grouped/aggregated view (by Vehicle)."""
    return [
        {
            "fieldname": "vehicle",
            "fieldtype": "Link",
            "label": _("Vehicle"),
            "options": "Vehicle",
            "width": 180,
        },
        {"fieldname": "make", "fieldtype": "Data", "label": _("Make"), "width": 100},
        {"fieldname": "model", "fieldtype": "Data", "label": _("Model"), "width": 100},
        {"fieldname": "location", "fieldtype": "Data", "label": _("Location"), "width": 120},
        {"fieldname": "fuel_expense", "fieldtype": "Currency", "label": _("Fuel Expense"), "width": 150},
        {
            "fieldname": "service_expense",
            "fieldtype": "Currency",
            "label": _("Service Expense"),
            "width": 150,
        },
        {
            "fieldname": "driver_wages",
            "fieldtype": "Currency",
            "label": _("Driver Wages"),
            "width": 150,
        },
        {
            "fieldname": "fastag_amount",
            "fieldtype": "Currency",
            "label": _("Fastag Amount"),
            "width": 150,
        },
        {
            "fieldname": "total_expense",
            "fieldtype": "Currency",
            "label": _("Total Expense"),
            "width": 170,
        },
    ]


# ──────────────────────────────────────────────
# Data Fetching — single efficient SQL query
# ──────────────────────────────────────────────

def get_vehicle_log_data(filters, start_date, end_date):
    """
    Fetch all vehicle log data in a single SQL query using LEFT JOIN
    to aggregate service expenses. Avoids N+1 query problem.
    """
    conditions = ""
    values = {
        "start_date": start_date,
        "end_date": end_date,
    }

    if filters.get("employee"):
        conditions += " AND log.employee = %(employee)s"
        values["employee"] = filters.employee

    if filters.get("vehicle"):
        conditions += " AND vhcl.license_plate = %(vehicle)s"
        values["vehicle"] = filters.vehicle

    if filters.get("location"):
        conditions += " AND vhcl.location = %(location)s"
        values["location"] = filters.location

    if filters.get("maintenance_only"):
        conditions += """
        AND EXISTS (
            SELECT 1
            FROM `tabVehicle Service` s
            WHERE s.parent = log.name
        )
        """

    data = frappe.db.sql(
        f"""
        SELECT
            vhcl.license_plate AS vehicle,
            vhcl.make,
            vhcl.model,
            vhcl.location,
            log.name AS log_name,
            log.odometer,
            log.date,
            log.employee,
            log.fuel_qty,
            log.price AS fuel_price,
            (log.fuel_qty * log.price) AS fuel_expense,
            IFNULL(log.custom_driver_wages, 0) AS driver_wages,
            IFNULL(log.custom_fastag_amount, 0) AS fastag_amount,
            IFNULL(svc.service_total, 0) AS service_expense
        FROM
            `tabVehicle Log` log
        INNER JOIN
            `tabVehicle` vhcl ON vhcl.license_plate = log.license_plate
        LEFT JOIN (
            SELECT
                parent,
                SUM(expense_amount) AS service_total
            FROM `tabVehicle Service`
            GROUP BY parent
        ) svc ON svc.parent = log.name
        WHERE
            log.docstatus = 1
            AND log.date BETWEEN %(start_date)s AND %(end_date)s
            {conditions}
        ORDER BY log.date
        """,
        values,
        as_dict=1,
    )

    # Calculate total_expense for each row
    for row in data:
        row["total_expense"] = (
            flt(row.fuel_expense)
            + flt(row.service_expense)
            + flt(row.driver_wages)
            + flt(row.fastag_amount)
        )

    return data


# ──────────────────────────────────────────────
# Expense Type Filtering
# ──────────────────────────────────────────────

def apply_expense_type_filter(data, expense_type):
    """
    Filter and adjust data based on Expense Type selection.
    - Fuel: Show only fuel-related expenses, zero out maintenance columns
    - Maintenance: Show only maintenance-related expenses, zero out fuel columns
    - Both: Show everything (default)
    """
    if expense_type == "Fuel":
        result = []
        for row in data:
            if flt(row.fuel_expense) > 0:
                row = frappe._dict(row)
                row.service_expense = 0
                row.total_expense = flt(row.fuel_expense) + flt(row.driver_wages) + flt(row.fastag_amount)
                result.append(row)
        return result

    elif expense_type == "Maintenance":
        result = []
        for row in data:
            if flt(row.service_expense) > 0:
                row = frappe._dict(row)
                row.fuel_expense = 0
                row.fuel_qty = 0
                row.fuel_price = 0
                row.total_expense = flt(row.service_expense) + flt(row.driver_wages) + flt(row.fastag_amount)
                result.append(row)
        return result

    # "Both" — return as-is
    return data


# ──────────────────────────────────────────────
# Aggregation — Group By Vehicle
# ──────────────────────────────────────────────

def aggregate_by_vehicle(data, expense_type):
    """
    Aggregate all expense totals grouped by Vehicle (license_plate).
    """
    vehicle_map = {}

    for row in data:
        key = row.vehicle
        if key not in vehicle_map:
            vehicle_map[key] = {
                "vehicle": row.vehicle,
                "make": row.make,
                "model": row.model,
                "location": row.location,
                "fuel_expense": 0,
                "service_expense": 0,
                "driver_wages": 0,
                "fastag_amount": 0,
                "total_expense": 0,
            }

        entry = vehicle_map[key]
        entry["fuel_expense"] += flt(row.fuel_expense)
        entry["service_expense"] += flt(row.service_expense)
        entry["driver_wages"] += flt(row.driver_wages)
        entry["fastag_amount"] += flt(row.fastag_amount)

    # Apply expense type filter and recalculate totals
    result = []
    for key, entry in vehicle_map.items():
        if expense_type == "Fuel":
            entry["service_expense"] = 0
        elif expense_type == "Maintenance":
            entry["fuel_expense"] = 0

        entry["total_expense"] = (
            flt(entry["fuel_expense"])
            + flt(entry["service_expense"])
            + flt(entry["driver_wages"])
            + flt(entry["fastag_amount"])
        )

        # Only include rows that actually have expenses after filtering
        if entry["total_expense"] > 0:
            result.append(entry)

    # Sort by vehicle name
    result.sort(key=lambda x: x["vehicle"])
    return result


# ──────────────────────────────────────────────
# Period Generation (Custom — no get_period_list)
# ──────────────────────────────────────────────

def generate_periods(start_date, end_date, report_period):
    """
    Generate custom period list based on report_period selection.

    Returns list of dicts:
        [{"label": "01-Jul-2025", "from_date": date(...), "to_date": date(...)}, ...]
    """
    start_date = getdate(start_date)
    end_date = getdate(end_date)
    periods = []

    if report_period == "Daily":
        current = start_date
        while current <= end_date:
            periods.append({
                "label": current.strftime("%d-%b-%Y"),
                "from_date": current,
                "to_date": current,
            })
            current += timedelta(days=1)

    elif report_period == "Weekly":
        # ISO week-based periods
        current = start_date
        while current <= end_date:
            # Find the Monday of the current week
            week_start = current - timedelta(days=current.weekday())
            week_end = week_start + timedelta(days=6)

            # Clamp to report date range
            actual_start = max(week_start, start_date)
            actual_end = min(week_end, end_date)

            iso_week = current.isocalendar()[1]
            periods.append({
                "label": f"Week {iso_week}",
                "from_date": actual_start,
                "to_date": actual_end,
            })

            # Move to next Monday
            current = week_end + timedelta(days=1)

    elif report_period == "Monthly":
        current = start_date
        while current <= end_date:
            month_start = get_first_day(current)
            month_end = get_last_day(current)

            # Clamp to report date range
            actual_start = max(month_start, start_date)
            actual_end = min(month_end, end_date)

            periods.append({
                "label": current.strftime("%b %Y"),
                "from_date": actual_start,
                "to_date": actual_end,
            })

            # Move to first day of next month
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)

    else:
        # Default: Monthly
        return generate_periods(start_date, end_date, "Monthly")

    return periods


# ──────────────────────────────────────────────
# Chart Generation (Custom — no get_period_list)
# ──────────────────────────────────────────────

def get_chart_data(data, periods, report_period, expense_type):
    """
    Build chart data by aggregating expenses into the generated periods.
    Chart is ALWAYS visible for every filter combination.
    When no data exists, it shows an empty chart with zero values.
    """
    if not periods:
        # No periods means no date range — show a minimal empty chart
        return {
            "data": {
                "labels": [_("No Data")],
                "datasets": [{"name": _("Total Expense"), "values": [0]}],
            },
            "type": "line",
            "fieldtype": "Currency",
        }

    fuel_values = []
    service_values = []
    driver_wages_values = []
    fastag_values = []

    for period in periods:
        total_fuel = 0
        total_service = 0
        total_wages = 0
        total_fastag = 0

        for row in data:
            row_date = getdate(row.date)
            if period["from_date"] <= row_date <= period["to_date"]:
                total_fuel += flt(row.fuel_expense)
                total_service += flt(row.service_expense)
                total_wages += flt(row.driver_wages)
                total_fastag += flt(row.fastag_amount)

        fuel_values.append(total_fuel)
        service_values.append(total_service)
        driver_wages_values.append(total_wages)
        fastag_values.append(total_fastag)

    labels = [p["label"] for p in periods]
    datasets = []

    # Always include expense datasets based on expense_type filter
    # Show them even if all values are zero so chart remains visible
    if expense_type in ("Fuel", "Both", "", None):
        datasets.append({
            "name": _("Fuel Expenses"),
            "values": fuel_values,
        })

    if expense_type in ("Maintenance", "Both", "", None):
        datasets.append({
            "name": _("Service Expenses"),
            "values": service_values,
        })

    # Always show Driver Wages and Fastag lines in chart
    datasets.append({
        "name": _("Driver Wages"),
        "values": driver_wages_values,
    })

    datasets.append({
        "name": _("Fastag"),
        "values": fastag_values,
    })

    # Limit daily labels if too many (prevent chart overflow)
    max_labels = 90
    if len(labels) > max_labels and report_period == "Daily":
        # Sample every N-th label to keep chart readable
        step = len(labels) // max_labels + 1
        sampled_labels = []
        for i, label in enumerate(labels):
            if i % step == 0:
                sampled_labels.append(label)
            else:
                sampled_labels.append("")
        labels = sampled_labels

    return {
        "data": {
            "labels": labels,
            "datasets": datasets,
        },
        "type": "line",
        "fieldtype": "Currency",
        "colors": ["#5e64ff", "#ff5858", "#ffc107", "#28a745"],
    }


# ──────────────────────────────────────────────
# Period Date Resolution
# ──────────────────────────────────────────────

def get_period_dates(filters):
    """
    Resolve the start and end dates from filters.
    Supports 'Fiscal Year' and 'Date Range' modes.
    """
    if filters.get("filter_based_on") == "Fiscal Year" and filters.get("fiscal_year"):
        fy = frappe.db.get_value(
            "Fiscal Year",
            filters.fiscal_year,
            ["year_start_date", "year_end_date"],
            as_dict=True,
        )
        if fy:
            return fy.year_start_date, fy.year_end_date

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    if from_date and to_date:
        return from_date, to_date

    # Fallback: current fiscal year
    fy = frappe.db.get_value(
        "Fiscal Year",
        {"disabled": 0},
        ["year_start_date", "year_end_date"],
        as_dict=True,
        order_by="year_start_date desc",
    )
    if fy:
        return fy.year_start_date, fy.year_end_date

    return None, None