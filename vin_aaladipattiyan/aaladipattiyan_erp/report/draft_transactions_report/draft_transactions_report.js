frappe.query_reports["Draft Transactions Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "module",
            label: __("Module"),
            fieldtype: "Select",
            options: [
                "",
                "Sales",
                "Purchase",
                "Accounts"
            ]
        }
    ]
};