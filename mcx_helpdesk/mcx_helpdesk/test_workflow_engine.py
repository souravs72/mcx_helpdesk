# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestWorkflowEngine(FrappeTestCase):
	def test_default_workflows_exist_after_sync(self):
		from mcx_helpdesk.setup.sync import sync_mcx_helpdesk

		sync_mcx_helpdesk()
		if not frappe.db.exists("DocType", "MCX Service Workflow"):
			self.skipTest("MCX Service Workflow DocType not migrated yet")
		workflows = frappe.get_all("MCX Service Workflow", filters={"enabled": 1})
		self.assertGreaterEqual(len(workflows), 2)
