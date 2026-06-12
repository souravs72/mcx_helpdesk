# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""MCX Helpdesk demo master data — run explicitly on any site."""

from __future__ import annotations

import frappe

from mcx_helpdesk.constants import TEAMS
from mcx_helpdesk.setup.install import ensure_agent, ensure_team, ensure_user

AGENTS = [
	{"email": "souravsingh2609@gmail.com", "full_name": "Sourav Singh", "team": "IT"},
	{"email": "mcx.it.agent@demo.com", "full_name": "MCX IT Agent", "team": "IT"},
	{"email": "mcx.trading.agent@demo.com", "full_name": "MCX Trading Agent", "team": "Trading"},
	{"email": "mcx.clearing.agent@demo.com", "full_name": "MCX Clearing Agent", "team": "Clearing"},
	{"email": "mcx.compliance.agent@demo.com", "full_name": "MCX Compliance Agent", "team": "Compliance"},
]

CUSTOMERS = [
	{"customer_name": "Ascra Technologies", "domain": "ascra.com"},
	{"customer_name": "Alpha Brokers", "domain": "alphabrokers.com"},
	{"customer_name": "Silver Trading Co", "domain": "silvertrading.com"},
	{"customer_name": "Golden Commodities Ltd", "domain": "goldencommodities.com"},
]

CONTACTS = [
	{
		"first_name": "Ahmad",
		"last_name": "Rehan",
		"email": "ahmadrehan610@gmail.com",
		"customer": "Ascra Technologies",
	},
	{
		"first_name": "Priya",
		"last_name": "Sharma",
		"email": "priya@alphabrokers.com",
		"customer": "Alpha Brokers",
	},
	{
		"first_name": "Rajesh",
		"last_name": "Mehta",
		"email": "rajesh@silvertrading.com",
		"customer": "Silver Trading Co",
	},
	{
		"first_name": "Fatima",
		"last_name": "Khan",
		"email": "fatima@goldencommodities.com",
		"customer": "Golden Commodities Ltd",
	},
]

ARTICLE_CATEGORIES = [
	{"category_name": "IT Support", "description": "Portal access, login, and system issues"},
	{"category_name": "Trading Operations", "description": "Order entry, margin, and trading queries"},
	{"category_name": "Clearing & Settlement", "description": "Settlement, payout, and clearing processes"},
	{"category_name": "Compliance", "description": "KYC, regulatory reporting, and compliance"},
]

ARTICLES = [
	{
		"title": "How to Reset Your MCX Member Portal Password",
		"category": "IT Support",
		"status": "Published",
		"content": """
<h3>Steps to reset your password</h3>
<ol>
<li>Go to the MCX Member Portal login page.</li>
<li>Click <strong>Forgot Password</strong>.</li>
<li>Enter your registered email and submit.</li>
<li>Follow the link in the email within 30 minutes.</li>
</ol>
<p>If you still cannot login, email support with subject tags:
<code>[DEPT:IT][TYPE:Portal Access][SUB:Password Reset]</code></p>
""",
	},
	{
		"title": "Understanding Order Rejections on MCX",
		"category": "Trading Operations",
		"status": "Published",
		"content": """
<h3>Common order rejection reasons</h3>
<ul>
<li><strong>Insufficient margin</strong> — fund your account or reduce quantity.</li>
<li><strong>Price out of range</strong> — order price exceeds the daily price band.</li>
<li><strong>Session closed</strong> — order placed outside trading hours.</li>
</ul>
<p>For support, use: <code>[DEPT:Trading][TYPE:Order Entry][SUB:Order Rejection]</code></p>
""",
	},
	{
		"title": "Settlement and Payout Timelines",
		"category": "Clearing & Settlement",
		"status": "Published",
		"content": """
<h3>Standard timelines</h3>
<ul>
<li><strong>T+1 settlement</strong> for most commodity contracts.</li>
<li><strong>Payouts</strong> are processed within 2 business days after settlement.</li>
<li>Delays may occur on bank holidays or pending KYC verification.</li>
</ul>
<p>Report delays with: <code>[DEPT:Clearing][TYPE:Settlement][SUB:Settlement Delay]</code></p>
""",
	},
	{
		"title": "KYC Document Submission Guide",
		"category": "Compliance",
		"status": "Published",
		"content": """
<h3>Required documents</h3>
<ul>
<li>PAN card (mandatory)</li>
<li>Address proof (Aadhaar / utility bill)</li>
<li>Bank account proof (cancelled cheque)</li>
<li>Authorized signatory list (for corporates)</li>
</ul>
<p>Submit updates via email: <code>[DEPT:Compliance][TYPE:KYC][SUB:KYC Update]</code></p>
""",
	},
]


def seed_mcx_demo_data():
	"""Create teams, agents, customers, contacts, and knowledge base articles."""
	if "helpdesk" not in frappe.get_installed_apps():
		frappe.throw("Helpdesk app is not installed on this site")

	seed_teams_and_agents()
	seed_customers()
	seed_contacts()
	seed_knowledge_base()

	frappe.db.commit()
	frappe.clear_cache()
	return {
		"teams": len(TEAMS),
		"agents": len(AGENTS),
		"customers": len(CUSTOMERS),
		"contacts": len(CONTACTS),
		"articles": len(ARTICLES),
	}


def seed_teams_and_agents():
	team_users: dict[str, list[str]] = {team: [] for team in TEAMS}

	for agent in AGENTS:
		ensure_user(agent["email"], agent["full_name"])
		ensure_agent(agent["email"], agent["full_name"])
		if agent["team"] in team_users:
			team_users[agent["team"]].append(agent["email"])

	for team in TEAMS:
		users = team_users.get(team, [])
		if users:
			ensure_team(team, users)


def seed_customers():
	for row in CUSTOMERS:
		name = row["customer_name"]
		if frappe.db.exists("HD Customer", name):
			frappe.db.set_value("HD Customer", name, "domain", row["domain"])
			continue
		doc = frappe.get_doc(
			{
				"doctype": "HD Customer",
				"customer_name": name,
				"domain": row["domain"],
			}
		)
		doc.insert(ignore_permissions=True)


def seed_contacts():
	for row in CONTACTS:
		email = row["email"]
		existing = frappe.db.get_value("Contact", {"email_id": email}, "name")
		if existing:
			_ensure_contact_customer_link(existing, row["customer"])
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": row["first_name"],
				"last_name": row["last_name"],
				"email_id": email,
			}
		)
		doc.insert(ignore_permissions=True)
		_ensure_contact_customer_link(doc.name, row["customer"])


def _ensure_contact_customer_link(contact_name: str, customer_name: str):
	if not frappe.db.exists("HD Customer", customer_name):
		return
	contact = frappe.get_doc("Contact", contact_name)
	if any(link.link_name == customer_name for link in contact.links):
		return
	contact.append("links", {"link_doctype": "HD Customer", "link_name": customer_name})
	contact.save(ignore_permissions=True)


def seed_knowledge_base():
	category_map: dict[str, str] = {}

	for cat in ARTICLE_CATEGORIES:
		existing = frappe.db.get_value("HD Article Category", {"category_name": cat["category_name"]}, "name")
		if existing:
			category_map[cat["category_name"]] = existing
			continue
		doc = frappe.get_doc(
			{
				"doctype": "HD Article Category",
				"category_name": cat["category_name"],
				"description": cat.get("description"),
			}
		)
		doc.insert(ignore_permissions=True)
		category_map[cat["category_name"]] = doc.name

	for article in ARTICLES:
		if frappe.db.exists("HD Article", {"title": article["title"]}):
			continue
		frappe.get_doc(
			{
				"doctype": "HD Article",
				"title": article["title"],
				"category": category_map[article["category"]],
				"status": article["status"],
				"content": article["content"].strip(),
			}
		).insert(ignore_permissions=True)
