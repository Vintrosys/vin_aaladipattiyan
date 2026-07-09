/**
 * Vehicle Expenses Report — Custom Filter Patch
 *
 * Injects additional filters into the standard HRMS Vehicle Expenses report
 * at runtime via monkey-patching frappe.views.QueryReport.
 *
 * New filters added:
 *   - Location (Data)
 *   - Report Period (Select: Daily / Weekly / Monthly)
 *   - Group By (Select: None / Vehicle)
 *   - Expense Type (Select: Both / Fuel / Maintenance)
 */

console.log("Vehicle Expenses Monkey Patch Loaded");

(function () {
    const original = frappe.views.QueryReport.prototype.get_report_settings;

    frappe.views.QueryReport.prototype.get_report_settings = function () {
        return original.apply(this, arguments).then(() => {
            if (this.report_name !== "Vehicle Expenses") {
                return;
            }

            console.log("Patching Vehicle Expenses Filters");

            const filters = this.report_settings.filters;

            const exists = (name) =>
                filters.some((df) => df.fieldname === name);

            // ─── Location filter ───
            if (!exists("location")) {
                filters.push({
                    fieldname: "location",
                    label: __("Location"),
                    fieldtype: "Data",
                });
            }

            // ─── Report Period filter ───
            if (!exists("report_period")) {
                filters.push({
                    fieldname: "report_period",
                    label: __("Report Period"),
                    fieldtype: "Select",
                    options: "\nDaily\nWeekly\nMonthly",
                    default: "Monthly",
                });
            }

            // ─── Group By filter ───
            if (!exists("group_by")) {
                filters.push({
                    fieldname: "group_by",
                    label: __("Group By"),
                    fieldtype: "Select",
                    options: "\nVehicle",
                    default: "",
                });
            }

            // ─── Expense Type filter ───
            if (!exists("expense_type")) {
                filters.push({
                    fieldname: "expense_type",
                    label: __("Expense Type"),
                    fieldtype: "Select",
                    options: "\nBoth\nFuel\nMaintenance",
                    default: "Both",
                });
            }

            // Remove old filters that are no longer needed
            // (maintenance_only, report_type — replaced by the new ones above)
            const removeFilters = ["maintenance_only", "report_type"];
            for (let i = filters.length - 1; i >= 0; i--) {
                if (removeFilters.includes(filters[i].fieldname)) {
                    filters.splice(i, 1);
                }
            }

            console.log("Patched filters:", filters.map((f) => f.fieldname));
        });
    };
})();