import frappe


def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": "Module",
            "fieldname": "module",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Document Type",
            "fieldname": "doctype_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Document",
            "fieldname": "document",
            "fieldtype": "Dynamic Link",
            "options": "doctype_name",
            "width": 180,
        },
        {
            "label": "Date",
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Party",
            "fieldname": "party",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": "Company",
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 180,
        },
        {
            "label": "Owner",
            "fieldname": "owner",
            "fieldtype": "Data",
            "width": 180,
        },
    ]


def get_data(filters):
    data = []

    module_filter = filters.get("module")

    if not module_filter or module_filter == "Purchase":
        data.extend(get_purchase_orders(filters))
        data.extend(get_purchase_receipts(filters))
        data.extend(get_purchase_invoices(filters))

    if not module_filter or module_filter == "Sales":
        data.extend(get_sales_orders(filters))
        data.extend(get_delivery_notes(filters))
        data.extend(get_sales_invoices(filters))

    if not module_filter or module_filter == "Accounts":
        data.extend(get_payment_entries(filters))

    return sorted(
        data,
        key=lambda x: x.get("posting_date") or "",
        reverse=True,
    )

def get_purchase_orders(filters):
    conditions = get_date_condition(
        "transaction_date",
        filters
    )

    return frappe.db.sql(
        f"""
        SELECT
            'Purchase' AS module,
            'Purchase Order' AS doctype_name,
            name AS document,
            transaction_date AS posting_date,
            supplier AS party,
            company,
            owner
        FROM `tabPurchase Order`
        WHERE docstatus = 0
        {conditions}
        """,
        as_dict=True,
    )


def get_purchase_receipts(filters):
    conditions = get_date_condition(
        "posting_date",
        filters
    )

    return frappe.db.sql(
        f"""
        SELECT
            'Purchase' AS module,
            'Purchase Receipt' AS doctype_name,
            name AS document,
            posting_date,
            supplier AS party,
            company,
            owner
        FROM `tabPurchase Receipt`
        WHERE docstatus = 0
        {conditions}
        """,
        as_dict=True,
    )


def get_purchase_invoices(filters):
    conditions = get_date_condition(
        "posting_date",
        filters
    )

    return frappe.db.sql(
        f"""
        SELECT
            'Purchase' AS module,
            'Purchase Invoice' AS doctype_name,
            name AS document,
            posting_date,
            supplier AS party,
            company,
            owner
        FROM `tabPurchase Invoice`
        WHERE docstatus = 0
        {conditions}
        """,
        as_dict=True,
    )


def get_sales_orders(filters):
    conditions = get_date_condition(
        "transaction_date",
        filters
    )

    return frappe.db.sql(
        f"""
        SELECT
            'Sales' AS module,
            'Sales Order' AS doctype_name,
            name AS document,
            transaction_date AS posting_date,
            customer AS party,
            company,
            owner
        FROM `tabSales Order`
        WHERE docstatus = 0
        {conditions}
        """,
        as_dict=True,
    )


def get_delivery_notes(filters):
    conditions = get_date_condition(
        "posting_date",
        filters
    )

    return frappe.db.sql(
        f"""
        SELECT
            'Sales' AS module,
            'Delivery Note' AS doctype_name,
            name AS document,
            posting_date,
            customer AS party,
            company,
            owner
        FROM `tabDelivery Note`
        WHERE docstatus = 0
        {conditions}
        """,
        as_dict=True,
    )


def get_sales_invoices(filters):
    conditions = get_date_condition(
        "posting_date",
        filters
    )

    return frappe.db.sql(
        f"""
        SELECT
            'Sales' AS module,
            'Sales Invoice' AS doctype_name,
            name AS document,
            posting_date,
            customer AS party,
            company,
            owner
        FROM `tabSales Invoice`
        WHERE docstatus = 0
        {conditions}
        """,
        as_dict=True,
    )


def get_payment_entries(filters):
    conditions = get_date_condition(
        "posting_date",
        filters
    )

    return frappe.db.sql(
        f"""
        SELECT
            'Accounts' AS module,
            'Payment Entry' AS doctype_name,
            name AS document,
            posting_date,
            party_name AS party,
            company,
            owner
        FROM `tabPayment Entry`
        WHERE docstatus = 0
        {conditions}
        """,
        as_dict=True,
    )


def get_date_condition(date_field, filters):
    conditions = ""

    if filters.get("from_date"):
        conditions += (
            f" AND {date_field} >= "
            f"'{filters.get('from_date')}'"
        )

    if filters.get("to_date"):
        conditions += (
            f" AND {date_field} <= "
            f"'{filters.get('to_date')}'"
        )

    return conditions