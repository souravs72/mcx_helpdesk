# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""DocType permission fixes for Helpdesk roles used on MCX sites."""

from __future__ import annotations

import frappe

HD_NOTIFICATION_PERM_TYPES = (
	"select",
	"read",
	"write",
	"create",
	"delete",
	"export",
	"print",
	"email",
	"share",
	"report",
)


def ensure_hd_notification_permissions():
	"""
	HD Notification ships with Agent + System Manager perms only.
	Agent Manager users need access; Agent needs select for list views (Frappe 16).
	"""
	doctype = "HD Notification"
	if not frappe.db.exists("DocType", doctype):
		return

	_ensure_custom_docperm(doctype, "Agent Manager")
	_ensure_agent_select(doctype)


def _ensure_agent_select(doctype: str):
	from frappe.permissions import add_permission

	if frappe.db.get_value(
		"Custom DocPerm", {"parent": doctype, "role": "Agent", "permlevel": 0}, "select"
	):
		return
	if frappe.db.get_value("DocPerm", {"parent": doctype, "role": "Agent", "permlevel": 0}, "select"):
		return
	add_permission(doctype, "Agent", 0, "select")


HELPDESK_REPORT_ROLES = ("Agent", "Agent Manager")


def ensure_helpdesk_report_roles():
	"""Grant desk agents access to standard Helpdesk query reports."""
	for report_name in frappe.get_all(
		"Report", filters={"module": "Helpdesk", "disabled": 0}, pluck="name"
	):
		for role in HELPDESK_REPORT_ROLES:
			_ensure_report_role(report_name, role)


def _ensure_report_role(report_name: str, role: str):
	if not frappe.db.exists("Role", role):
		return
	if frappe.db.exists(
		"Has Role", {"parent": report_name, "parenttype": "Report", "role": role}
	):
		return
	frappe.get_doc(
		{
			"doctype": "Has Role",
			"parent": report_name,
			"parenttype": "Report",
			"parentfield": "roles",
			"role": role,
		}
	).insert(ignore_permissions=True)


def _ensure_custom_docperm(doctype: str, role: str):
	if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
		_ensure_perm_flags(doctype, role)
		return

	doc = frappe.get_doc(
		{
			"doctype": "Custom DocPerm",
			"parent": doctype,
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": role,
			"permlevel": 0,
			**{perm: 1 for perm in HD_NOTIFICATION_PERM_TYPES},
		}
	)
	doc.insert(ignore_permissions=True)


def _ensure_perm_flags(doctype: str, role: str):
	"""Backfill any missing permission flags on an existing Custom DocPerm row."""
	from frappe.permissions import update_permission_property

	name = frappe.db.get_value(
		"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}, "name"
	)
	if not name:
		return

	for perm in HD_NOTIFICATION_PERM_TYPES:
		if frappe.db.get_value("Custom DocPerm", name, perm):
			continue
		try:
			update_permission_property(doctype, role, 0, perm, 1)
		except Exception:
			frappe.log_error(
				title="MCX HD Notification permission update failed",
				message=frappe.get_traceback(),
			)
