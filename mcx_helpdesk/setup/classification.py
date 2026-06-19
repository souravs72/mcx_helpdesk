# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Seed and sync MCX Classification Rules and issue-type department links."""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from mcx_helpdesk.constants import ISSUE_TYPES
from mcx_helpdesk.mcx_helpdesk.classification_rules import clear_classification_rules_cache

# Install-time seed only — runtime always reads MCX Classification Rule from desk.
DEFAULT_CLASSIFICATION_RULES = [
	{
		"rule_name": "Password Reset",
		"rule_type": "Ticket Routing",
		"priority": 10,
		"keywords": "password reset\nreset my password\nforgot password",
		"department": "IT",
		"issue_type": "IT - Portal Access",
		"sub_issue_type": "Password Reset",
	},
	{
		"rule_name": "Login Issue",
		"rule_type": "Ticket Routing",
		"priority": 20,
		"keywords": "login\nunable to login\nportal access\nsign in\nsign-in",
		"department": "IT",
		"issue_type": "IT - Portal Access",
		"sub_issue_type": "Login Issue",
	},
	{
		"rule_name": "System Outage",
		"rule_type": "Ticket Routing",
		"priority": 30,
		"keywords": "system down\noutage\ndowntime\nterminal disconnect\nnot working",
		"department": "IT",
		"issue_type": "IT - System Downtime",
		"sub_issue_type": "System Outage",
		"set_priority": "Urgent",
	},
	{
		"rule_name": "Payout Pending",
		"rule_type": "Ticket Routing",
		"priority": 40,
		"keywords": "payout\npayment pending\ncpo settlement",
		"department": "Clearing",
		"issue_type": "Clearing - Payout",
		"sub_issue_type": "Payout Pending",
	},
	{
		"rule_name": "Settlement Delay",
		"rule_type": "Ticket Routing",
		"priority": 50,
		"keywords": "settlement\nclearing delay\nt+1\nbank credit",
		"department": "Clearing",
		"issue_type": "Clearing - Settlement",
		"sub_issue_type": "Settlement Delay",
	},
	{
		"rule_name": "Order Rejection",
		"rule_type": "Ticket Routing",
		"priority": 60,
		"keywords": "order reject\norder rejected\norder entry\ntrade reject\ngoldm",
		"department": "Trading",
		"issue_type": "Trading - Order Entry",
		"sub_issue_type": "Order Rejection",
	},
	{
		"rule_name": "Price Mismatch",
		"rule_type": "Ticket Routing",
		"priority": 70,
		"keywords": "margin\nprice mismatch\npeak margin\nsilverm",
		"department": "Trading",
		"issue_type": "Trading - Margin Query",
		"sub_issue_type": "Price Mismatch",
	},
	{
		"rule_name": "KYC Update",
		"rule_type": "Ticket Routing",
		"priority": 80,
		"keywords": "kyc\nknow your customer\npan document",
		"department": "Compliance",
		"issue_type": "Compliance - KYC",
		"sub_issue_type": "KYC Update",
	},
	{
		"rule_name": "Regulatory Filing",
		"rule_type": "Ticket Routing",
		"priority": 90,
		"keywords": "regulatory\ncompliance report\nopen interest\nreporting",
		"department": "Compliance",
		"issue_type": "Compliance - Reporting",
		"sub_issue_type": "Regulatory Filing",
	},
	{
		"rule_name": "Alpha Brokers",
		"rule_type": "Customer Match",
		"priority": 10,
		"keywords": "alpha brokers\nalphabrokers.com\nalphabrokers",
		"customer": "Alpha Brokers",
	},
	{
		"rule_name": "Silver Trading Co",
		"rule_type": "Customer Match",
		"priority": 20,
		"keywords": "silver trading\nsilvertrading.com\nsilvertrading",
		"customer": "Silver Trading Co",
	},
	{
		"rule_name": "Golden Commodities Ltd",
		"rule_type": "Customer Match",
		"priority": 30,
		"keywords": "golden commodities\ngoldencommodities.com\ngoldencommodities",
		"customer": "Golden Commodities Ltd",
	},
	{
		"rule_name": "Ascra Technologies",
		"rule_type": "Customer Match",
		"priority": 40,
		"keywords": "ascra technologies\nascra.com",
		"customer": "Ascra Technologies",
	},
]


def ensure_issue_type_department_field():
	create_custom_fields(
		{
			"HD Ticket Type": [
				{
					"fieldname": "default_department",
					"label": "Default Department",
					"fieldtype": "Link",
					"options": "HD Team",
					"insert_after": "priority",
					"description": "Used when a ticket is classified by issue type without an explicit department",
				}
			]
		},
		ignore_validate=True,
	)


def sync_issue_type_departments():
	"""Set default_department on issue types from install seed (idempotent)."""
	if not frappe.db.exists("DocType", "HD Ticket Type"):
		return
	for name, _priority, team in ISSUE_TYPES:
		if not frappe.db.exists("HD Ticket Type", name):
			continue
		if not frappe.db.exists("HD Team", team):
			continue
		current = frappe.db.get_value("HD Ticket Type", name, "default_department")
		if current != team:
			frappe.db.set_value("HD Ticket Type", name, "default_department", team, update_modified=False)


def ensure_default_classification_rules():
	if not frappe.db.exists("DocType", "MCX Classification Rule"):
		return

	created = False
	for spec in DEFAULT_CLASSIFICATION_RULES:
		if frappe.db.exists("MCX Classification Rule", spec["rule_name"]):
			continue
		if not _seed_rule_is_valid(spec):
			continue
		frappe.get_doc({"doctype": "MCX Classification Rule", **spec}).insert(ignore_permissions=True)
		created = True

	if created:
		clear_classification_rules_cache()


def _seed_rule_is_valid(spec: dict) -> bool:
	if spec.get("rule_type") == "Customer Match":
		return bool(spec.get("customer") and frappe.db.exists("HD Customer", spec["customer"]))
	if spec.get("issue_type") and not frappe.db.exists("HD Ticket Type", spec["issue_type"]):
		return False
	if spec.get("department") and not frappe.db.exists("HD Team", spec["department"]):
		return False
	if spec.get("sub_issue_type") and not frappe.db.exists("HD Sub Issue Type", spec["sub_issue_type"]):
		return False
	return True


def ensure_classification_setup():
	if "helpdesk" not in frappe.get_installed_apps():
		return
	ensure_issue_type_department_field()
	sync_issue_type_departments()
	ensure_default_classification_rules()
