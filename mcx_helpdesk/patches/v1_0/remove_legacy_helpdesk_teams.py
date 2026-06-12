# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

import frappe


def execute():
	for team in ["Billing", "Product Experts"]:
		if not frappe.db.exists("HD Team", team):
			continue
		frappe.db.set_value("HD Team", team, "disabled", 1)
		assignment_rule = frappe.db.get_value("HD Team", team, "assignment_rule")
		if assignment_rule:
			frappe.db.set_value("Assignment Rule", assignment_rule, "disabled", 1)
