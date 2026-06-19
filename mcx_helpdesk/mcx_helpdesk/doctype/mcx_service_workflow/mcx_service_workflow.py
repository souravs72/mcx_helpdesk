# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MCXServiceWorkflow(Document):
	def validate(self):
		if self.condition:
			try:
				temp_doc = frappe.new_doc("HD Ticket")
				frappe.safe_eval(self.condition, None, {"doc": temp_doc})
			except Exception as exc:
				frappe.throw(_("Workflow condition is invalid: {0}").format(exc))
