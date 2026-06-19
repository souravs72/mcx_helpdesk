# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from mcx_helpdesk.mcx_helpdesk.classification_rules import clear_classification_rules_cache


class MCXClassificationRule(Document):
	def validate(self):
		if self.rule_type == "Ticket Routing" and not self.issue_type:
			frappe.throw(_("Issue Type is required for Ticket Routing rules."))
		if self.rule_type == "Customer Match" and not self.customer:
			frappe.throw(_("Customer is required for Customer Match rules."))
		if not (self.keywords or "").strip():
			frappe.throw(_("Add at least one keyword (one per line)."))

	def on_update(self):
		clear_classification_rules_cache()

	def on_trash(self):
		clear_classification_rules_cache()
