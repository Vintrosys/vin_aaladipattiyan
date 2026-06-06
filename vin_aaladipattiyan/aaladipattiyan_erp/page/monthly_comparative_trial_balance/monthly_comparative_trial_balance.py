import frappe

from frappe.utils import (
    getdate,
    add_months,
    get_first_day,
    get_last_day
)


@frappe.whitelist()
def get_report(company=None, from_date=None, to_date=None):

    if not company:
        return {
            "company": "",
            "months": [],
            "rows": []
        }

    from_date, to_date = get_report_dates(
        from_date,
        to_date
    )

    months = build_months(
        from_date,
        to_date
    )

    account_map = get_account_classifications()

    gl_entries = get_gl_entries(
        company,
        from_date,
        to_date
    )

    rows = build_account_rows(
        gl_entries,
        months,
        account_map
    )

    return {
        "company": company,
        "months": months,
        "rows": rows
    }


def get_report_dates(from_date=None, to_date=None):

    if from_date and to_date:
        return (
            getdate(from_date),
            getdate(to_date)
        )

    fiscal_year = frappe.defaults.get_user_default(
        "fiscal_year"
    )

    fy = None

    if fiscal_year:

        fy = frappe.db.get_value(
            "Fiscal Year",
            fiscal_year,
            [
                "year_start_date",
                "year_end_date"
            ],
            as_dict=True
        )

    if not fy:

        fy = frappe.get_all(
            "Fiscal Year",
            fields=[
                "year_start_date",
                "year_end_date"
            ],
            order_by="year_start_date desc",
            limit=1
        )[0]

    return (
        getdate(fy["year_start_date"]),
        getdate(fy["year_end_date"])
    )


def build_months(from_date, to_date):

    months = []

    current = get_first_day(from_date)

    while current <= to_date:

        months.append({
            "key": current.strftime("%b").lower(),
            "label": (
                f"{get_first_day(current).strftime('%d-%m-%Y')} "
                f"to "
                f"{get_last_day(current).strftime('%d-%m-%Y')}"
            )
        })

        current = add_months(
            current,
            1
        )

    return months


def get_gl_entries(company, from_date, to_date):

    return frappe.db.sql("""

        SELECT
            account,
            posting_date,
            debit,
            credit

        FROM `tabGL Entry`

        WHERE
            company = %(company)s
            AND posting_date <= %(to_date)s
            AND docstatus = 1

        ORDER BY
            account,
            posting_date

    """, {
        "company": company,
        "to_date": to_date
    }, as_dict=True)


def get_account_classifications():

    accounts = frappe.get_all(
        "Account",
        fields=[
            "name",
            "parent_account",
            "root_type",
            "account_type",
            "is_group"
        ],
        limit=0
    )

    account_dict = {
        d.name: d
        for d in accounts
    }

    classification_map = {}

    for account in accounts:

        # REAL CASH ACCOUNTS ONLY
        if (
            account.account_type == "Cash"
            and (
                "Cash In Hand" in account.name
                or account.name.startswith("Cash -")
            )
        ):
            classification = "Cash"

        else:

            current = account.name
            classification = account.root_type

            while current:

                row = account_dict.get(current)

                if not row:
                    break

                parent = row.parent_account

                if not parent:
                    break

                parent_row = account_dict.get(parent)

                if (
                    parent_row
                    and parent_row.is_group
                    and parent_row.parent_account
                ):
                    classification = parent.split(" - ")[0]

                current = parent

        classification_map[
            account.name
        ] = classification

    return classification_map

def build_account_rows(
    gl_entries,
    months,
    account_map
):

    rows = {}

    gl_entries = sorted(
        gl_entries,
        key=lambda d: (
            d.account,
            d.posting_date
        )
    )

    for entry in gl_entries:

        account = entry.account

        if account not in rows:

            rows[account] = {
                "classification": account_map.get(account),
                "account": account,
                "_balance": 0
            }

            for month in months:

                rows[account][month["key"]] = {
                    "debit": 0,
                    "credit": 0
                }

        rows[account]["_balance"] += (
            (entry.debit or 0)
            -
            (entry.credit or 0)
        )

        entry_date = getdate(
            entry.posting_date
        )

        for month in months:

            month_end = get_last_day(
                getdate(month["label"].split(" to ")[1])
            )

            if entry_date <= month_end:

                balance = rows[account]["_balance"]

                if balance >= 0:

                    rows[account][month["key"]]["debit"] = balance
                    rows[account][month["key"]]["credit"] = 0

                else:

                    rows[account][month["key"]]["debit"] = 0
                    rows[account][month["key"]]["credit"] = abs(balance)

    for row in rows.values():

        row.pop("_balance", None)

    return list(rows.values())