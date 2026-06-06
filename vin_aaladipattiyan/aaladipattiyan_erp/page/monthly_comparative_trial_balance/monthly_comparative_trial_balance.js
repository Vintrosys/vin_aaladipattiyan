frappe.pages['monthly-comparative-trial-balance'].on_page_load = function(wrapper) {

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Monthly Comparative Trial Balance',
		single_column: true
	});

	const company = page.add_field({
		label: 'Company',
		fieldname: 'company',
		fieldtype: 'Link',
		options: 'Company',
		reqd: 1
	});

	const from_date = page.add_field({
		label: 'From Date',
		fieldname: 'from_date',
		fieldtype: 'Date'
	});

	const to_date = page.add_field({
		label: 'To Date',
		fieldname: 'to_date',
		fieldtype: 'Date'
	});

	page.set_primary_action('Load', () => {
		load_report();
	});

	page.add_menu_item(__('Export Excel'), () => {
		export_excel();
	});

	page.add_menu_item(__('Export CSV'), () => {
		export_csv();
	});

	page.add_menu_item(__('Print'), () => {
		print_report();
	});

	// page.add_inner_button(__('Export Excel'), () => {
	// 	export_excel();
	// });

	// page.add_inner_button(__('Export CSV'), () => {
	// 	export_csv();
	// });

	// page.add_inner_button(__('Print'), () => {
	// 	print_report();
	// });

	$(page.body).append(`
		<div id="report_area" style="margin-top:20px;"></div>
	`);



$(`<style>

.report-table-wrapper{
	max-height:700px;
	overflow:auto;
	border:1px solid #d1d8dd;
}

.report-table-wrapper table{
	min-width:max-content;
	border-collapse:separate;
	border-spacing:0;
}

/* HEADER ROW 1 */
#monthly_tb_table thead tr:nth-child(1) th{
	position:sticky;
	top:0;
	background:#f8f9fa;
	z-index:50;
}

/* HEADER ROW 2 */
#monthly_tb_table thead tr:nth-child(2) th{
	position:sticky;
	top:42px;
	background:#f8f9fa;
	z-index:49;
}

/* HEADER ROW 3 */
#monthly_tb_table thead tr:nth-child(3) th{
	position:sticky;
	top:84px;
	background:#f8f9fa;
	z-index:48;
}

/* HEADER ROW 4 */
#monthly_tb_table thead tr:nth-child(4) th{
	position:sticky;
	top:126px;
	background:#f8f9fa;
	z-index:47;
}

/* CLASSIFICATION COLUMN */

.classification-col{
	position:sticky;
	left:0;
	background:white;
	min-width:220px;
	z-index:30;
}

/* PARTICULARS COLUMN */

.particulars-col{
	position:sticky;
	left:220px;
	background:white;
	min-width:300px;
	z-index:29;
}

/* TOTAL ROW */

.total-row td{
	background:#fff2cc !important;
	font-weight:bold;
	font-size:14px;
}

/* BETTER LOOK */

#monthly_tb_table th,
#monthly_tb_table td{
	white-space:nowrap;
	vertical-align:middle;
}

.sticky-header-left{
	position: sticky !important;
	left: 0;
	top: 0;
	z-index: 100;
	background: #f8f9fa !important;
	min-width: 220px;
	vertical-align: middle !important;
}

.sticky-header-left-2{
	position: sticky !important;
	left: 220px;
	top: 0;
	z-index: 99;
	background: #f8f9fa !important;
	min-width: 300px;
	vertical-align: middle !important;
}


</style>`).appendTo("head");

	function load_report() {

		if (!company.get_value()) {
			frappe.msgprint("Please select Company");
			return;
		}

		frappe.call({
			method: "vin_aaladipattiyan.aaladipattiyan_erp.page.monthly_comparative_trial_balance.monthly_comparative_trial_balance.get_report",
			args: {
				company: company.get_value(),
				from_date: from_date.get_value(),
				to_date: to_date.get_value()
			},
			freeze: true,
			callback: function(r) {

				if (!r.message) {
					frappe.msgprint("No Data Found");
					return;
				}

				render_report(r.message);
			}
		});
	}


function render_report(data) {

	let html = `
<div class="report-table-wrapper">
	<table
		class="table table-bordered"
		id="monthly_tb_table">

	<thead>

	<tr>

<th rowspan="4"
	class="classification-col sticky-header-left">
	Classification
</th>

<th rowspan="4"
	class="particulars-col sticky-header-left-2">
	Particulars
</th>
	`;

	data.months.forEach(month => {

		html += `
			<th colspan="2"
				class="text-center">
				${data.company}
			</th>
		`;
	});

	html += `</tr><tr>`;

	data.months.forEach(month => {

		html += `
			<th colspan="2"
				class="text-center">
				${month.label}
			</th>
		`;
	});

	html += `</tr><tr>`;

	data.months.forEach(month => {

		html += `
			<th colspan="2"
				class="text-center">
				Closing Balance
			</th>
		`;
	});

	html += `</tr><tr>`;

	data.months.forEach(month => {

		html += `
			<th>Debit</th>
			<th>Credit</th>
		`;
	});

	html += `
		</tr>
		</thead>
		<tbody>
	`;

	data.rows.forEach(row => {

		html += `
			<tr>

<td class="classification-col">
	${row.classification || ""}
</td>

<td class="particulars-col">
	${row.account}
</td>
		`;

		data.months.forEach(month => {

			let debit =
				row[month.key]?.debit || 0;

			let credit =
				row[month.key]?.credit || 0;

			html += `

				<td class="text-end">
					${format_currency(debit)}
				</td>

				<td class="text-end">
					${format_currency(credit)}
				</td>
			`;
		});

		html += `
			</tr>
		`;
	});

	// BLANK SEPARATOR ROW

html += `
	<tr>
		<td colspan="${(data.months.length * 2) + 2}"
			style="
				height:15px;
				background:white;
				border:none;
			">
		</td>
	</tr>
`;


// TOTAL ROW

html += `
<tr class="total-row">

<td class="classification-col">
	GRAND TOTAL
</td>

<td class="particulars-col"></td>
`;

data.months.forEach(month => {

	let total_debit = 0;
	let total_credit = 0;

	data.rows.forEach(row => {

		total_debit += (
			row[month.key]?.debit || 0
		);

		total_credit += (
			row[month.key]?.credit || 0
		);
	});

	html += `
		<td class="text-end">
			${format_currency(total_debit)}
		</td>

		<td class="text-end">
			${format_currency(total_credit)}
		</td>
	`;
});

html += `</tr>`;

	html += `
		</tbody>
		</table>
		</div>
	`;

	$("#report_area").html(html);
}



	function format_currency(value) {

		return format_currency_inr(value);
	}

function format_currency_inr(x) {

	return new Intl.NumberFormat('en-IN', {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2
	}).format(x || 0);
}


	function export_excel() {

		let table = document.querySelector("#monthly_tb_table");

		if (!table) {
			frappe.msgprint("No data available");
			return;
		}

		let html = table.outerHTML;

		let url = 'data:application/vnd.ms-excel,' + encodeURIComponent(html);

		let link = document.createElement("a");

		link.href = url;

		link.download = "Monthly Comparative Trial Balance.xls";

		document.body.appendChild(link);

		link.click();

		document.body.removeChild(link);
	}

	// EXPORT CSV

	function export_csv() {

		let rows = [];

		$("#monthly_tb_table tr").each(function() {

			let cols = [];

			$(this).find("th, td").each(function() {

				cols.push(
					$(this).text().trim().replace(/,/g, "")
				);
			});

			rows.push(cols.join(","));
		});

		let csv = rows.join("\n");

		let blob = new Blob([csv], {
			type: 'text/csv'
		});

		let link = document.createElement("a");

		link.href = window.URL.createObjectURL(blob);

		link.download = "Monthly Comparative Trial Balance.csv";

		link.click();
	}

	// PRINT

	function print_report() {

		let printContents = document.getElementById("report_area").innerHTML;

		let win = window.open('', '', 'height=900,width=1200');

		win.document.write(`
			<html>
				<head>
					<title>Monthly Comparative Trial Balance</title>

					<style>

						body {
							font-family: Arial;
							padding: 20px;
						}

						table {
							width: 100%;
							border-collapse: collapse;
						}

						table, th, td {
							border: 1px solid #ccc;
						}

						th, td {
							padding: 8px;
							font-size: 12px;
						}

						th {
							background: #f5f5f5;
						}

						.text-end {
							text-align: right;
						}

						.text-center {
							text-align: center;
						}

					</style>

				</head>

				<body>

					<h2>
						Monthly Comparative Trial Balance
					</h2>

					${printContents}

				</body>

			</html>
		`);

		win.document.close();

		win.print();
	}
};