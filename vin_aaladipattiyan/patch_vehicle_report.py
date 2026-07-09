"""
Monkey-patch the HRMS Vehicle Expenses report to use our custom implementation.

This module is imported from hooks.py at app load time to override
the standard execute function.
"""
import hrms.hr.report.vehicle_expenses.vehicle_expenses as original
import vin_aaladipattiyan.aaladipattiyan_erp.report.vehicle_expenses.vehicle_expenses as custom

original.execute = custom.execute