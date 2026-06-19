# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from mcx_helpdesk.mcx_helpdesk.ai_chatbot import (
	_score_article,
	answer_faq_question,
	get_chatbot_config,
	search_faq_articles,
)
from mcx_helpdesk.setup.faq import ensure_faq_setup


class TestFaqChatbot(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from mcx_helpdesk.setup.sync import sync_mcx_helpdesk

		sync_mcx_helpdesk()
		ensure_faq_setup()
		frappe.db.commit()

	def test_faq_seed_creates_articles(self):
		if not frappe.db.exists("DocType", "HD Article"):
			self.skipTest("HD Article not available")
		self.assertGreaterEqual(
			frappe.db.count(
				"HD Article",
				filters={
					"status": "Published",
					"title": "How do I raise a support ticket?",
				},
			),
			1,
		)

	def test_search_faq_articles_password(self):
		if not frappe.db.exists("DocType", "HD Article"):
			self.skipTest("HD Article not available")
		results = search_faq_articles("forgot password reset")
		self.assertTrue(results)
		titles = [r["title"].lower() for r in results]
		self.assertTrue(any("password" in t for t in titles))

	def test_score_article_prefers_title_match(self):
		row = frappe._dict(title="Password Reset Guide", content="Other text")
		score = _score_article(row, "password reset")
		self.assertGreater(score, 0)

	def test_answer_without_ai(self):
		if not frappe.db.exists("DocType", "MCX AI Settings"):
			self.skipTest("MCX AI Settings not migrated")
		settings = frappe.get_single("MCX AI Settings")
		settings.enabled = 0
		settings.enable_customer_chatbot = 1
		settings.save(ignore_permissions=True)

		result = answer_faq_question("How do I raise a support ticket?")
		self.assertIn("answer", result)
		self.assertTrue(result["answer"])
		self.assertFalse(result.get("ai_mode"))

	def test_get_chatbot_config_enabled_by_default(self):
		config = get_chatbot_config()
		self.assertTrue(config.get("enabled"))
		self.assertIn("welcome_message", config)
		self.assertIsInstance(config.get("suggested_questions"), list)
