# Copyright (c) 2026, Ascra Technologies LLP and contributors
# For license information, please see license.txt

"""Seed MCX Helpdesk FAQ categories and published knowledge base articles."""

from __future__ import annotations

from datetime import datetime

import frappe

from mcx_helpdesk.mcx_helpdesk.ai_chatbot import FAQ_CATEGORY_PREFIX

FAQ_CATEGORIES = [
	"Getting Started",
	"Tickets & Support",
	"Account & Portal",
	"Trading & Operations",
	"Clearing & Settlement",
	"SLA & Escalation",
]

DEFAULT_FAQS: dict[str, list[dict]] = {
	"Getting Started": [
		{
			"title": "What is the MCX Helpdesk portal?",
			"content": """
<p>The MCX Helpdesk portal is your self-service channel for member firms, brokers, and registered clients to raise support requests, track ticket status, and browse FAQs.</p>
<p>You can log in with your registered email to view open tickets, add replies, upload attachments, and search the knowledge base without calling the support desk.</p>
<p>For urgent trading or clearing issues during market hours, raise a ticket with priority <strong>Urgent</strong> or use the escalation path described in our SLA articles.</p>
""",
		},
		{
			"title": "How do I contact MCX support?",
			"content": """
<p>The fastest way to reach MCX support is through this Helpdesk portal:</p>
<ol>
<li>Sign in to the customer portal.</li>
<li>Click <strong>New Ticket</strong> and describe your issue.</li>
<li>Select the relevant department (Trading, Clearing, IT, or Compliance) if known.</li>
</ol>
<p>Each ticket receives a unique reference number. You will receive email updates when an agent replies or when the status changes.</p>
<p>For password or login emergencies, choose issue type <strong>IT - Portal Access</strong> so your request is routed to the IT team.</p>
""",
		},
		{
			"title": "What are MCX support hours?",
			"content": """
<p>Helpdesk agents monitor tickets during exchange business days. Trading-related queries are prioritised during live market hours.</p>
<p>IT portal and login issues are handled on a best-effort basis outside market hours; urgent system outages are escalated immediately.</p>
<p>Clearing and settlement queries are typically addressed on business days aligned with the settlement cycle (T+1).</p>
<p>Check your ticket for SLA targets based on priority and agreement type assigned to your account.</p>
""",
		},
	],
	"Tickets & Support": [
		{
			"title": "How do I raise a support ticket?",
			"content": """
<p>To raise a ticket:</p>
<ol>
<li>Log in to the Helpdesk customer portal.</li>
<li>Click <strong>New Ticket</strong>.</li>
<li>Enter a clear subject line and detailed description.</li>
<li>Attach screenshots, error messages, or contract details if applicable.</li>
<li>Submit the ticket — you will see it under <strong>My Tickets</strong>.</li>
</ol>
<p>Tickets created by email are also logged automatically when sent from your registered address.</p>
""",
		},
		{
			"title": "What information should I include in a ticket?",
			"content": """
<p>Include as much of the following as possible to avoid delays:</p>
<ul>
<li>Member / client code and registered email</li>
<li>Contract symbol, expiry, and side (buy/sell) for trading issues</li>
<li>Exact error message or rejection reason from the terminal</li>
<li>Date and time (with timezone) when the issue occurred</li>
<li>Order ID, settlement ID, or payout reference for clearing queries</li>
<li>Screenshots or log excerpts (attach as files)</li>
</ul>
<p>Vague descriptions such as "system not working" require follow-up and may breach SLA while we gather details.</p>
""",
		},
		{
			"title": "How can I check my ticket status?",
			"content": """
<p>Open <strong>My Tickets</strong> in the customer portal. Each ticket shows its current status, last reply, and assigned department.</p>
<p>You will also receive email notifications when an agent responds or when the ticket is resolved.</p>
<p>Click the ticket to view the full conversation thread and add a reply.</p>
""",
		},
		{
			"title": "What do ticket statuses mean?",
			"content": """
<p>Common ticket statuses:</p>
<ul>
<li><strong>Open</strong> — Ticket received; awaiting agent action.</li>
<li><strong>Replied</strong> — An agent has responded; may await your input.</li>
<li><strong>Resolved</strong> — Issue addressed; please confirm or reopen if needed.</li>
<li><strong>Closed</strong> — Ticket completed; no further action unless reopened.</li>
</ul>
<p>SLA indicators on the ticket show whether response or resolution targets are on track.</p>
""",
		},
		{
			"title": "How do I reply or add attachments to a ticket?",
			"content": """
<p>Open the ticket from <strong>My Tickets</strong>, scroll to the reply area, type your message, and click <strong>Send</strong>.</p>
<p>Use the attachment icon to upload files (screenshots, statements, logs). Supported formats include PDF, PNG, JPG, and common document types.</p>
<p>Replies are visible to assigned agents and update the ticket timestamp for SLA tracking.</p>
""",
		},
		{
			"title": "Can I reopen a closed or resolved ticket?",
			"content": """
<p>Yes. If the issue persists after a ticket is marked <strong>Resolved</strong> or <strong>Closed</strong>, reply on the same ticket thread explaining what is still wrong.</p>
<p>The ticket will reopen and route back to the assigned team. For a unrelated new issue, create a fresh ticket instead of reopening an old one.</p>
""",
		},
		{
			"title": "How do I provide feedback on a resolved ticket?",
			"content": """
<p>When a ticket is resolved, you may receive a feedback request by email or see a feedback option on the ticket page.</p>
<p>Your rating helps us improve response quality and routing. Optional comments are shared with the team lead.</p>
""",
		},
	],
	"Account & Portal": [
		{
			"title": "I forgot my password — how do I reset it?",
			"content": """
<p>On the login page, click <strong>Forgot Password</strong> and enter your registered email address.</p>
<p>You will receive a reset link valid for a limited time. Follow the link to set a new password.</p>
<p>If you do not receive the email, check spam folders or raise a ticket under <strong>IT - Portal Access</strong> with subject "Password Reset".</p>
""",
		},
		{
			"title": "Why am I unable to log in to the portal?",
			"content": """
<p>Common causes:</p>
<ul>
<li>Incorrect email or password — use Forgot Password to reset.</li>
<li>Account not yet activated — contact your firm's admin or raise an IT ticket.</li>
<li>Browser cache — try incognito mode or clear cookies.</li>
<li>Account locked after failed attempts — wait 15 minutes or contact support.</li>
</ul>
<p>Include the exact error message when raising a ticket for faster resolution.</p>
""",
		},
		{
			"title": "How do I update my registered email or mobile number?",
			"content": """
<p>Registered contact details are tied to your member or client profile for security.</p>
<p>Request changes through your authorised signatory or compliance contact, or raise a ticket under <strong>Compliance - KYC</strong> with supporting documentation.</p>
<p>IT cannot change registered details without compliance approval.</p>
""",
		},
		{
			"title": "Who can access the customer portal?",
			"content": """
<p>Access is granted to users linked to an MCX member firm or registered client organisation.</p>
<p>Each user sees only tickets they created or that belong to their organisation, depending on portal permissions.</p>
<p>Contact your firm administrator to add or remove portal users.</p>
""",
		},
	],
	"Trading & Operations": [
		{
			"title": "Why was my order rejected?",
			"content": """
<p>Orders may be rejected for several reasons:</p>
<ul>
<li>Insufficient margin or limits</li>
<li>Price outside the allowed circuit or tick size</li>
<li>Invalid contract or expired series</li>
<li>Trading halt or session not open</li>
<li>Risk or compliance blocks on the account</li>
</ul>
<p>Check the rejection message on your terminal. Raise a ticket under <strong>Trading - Order Entry</strong> with order ID, contract, and the exact rejection text.</p>
""",
		},
		{
			"title": "How do I report a trading system or terminal outage?",
			"content": """
<p>For live market disruptions:</p>
<ol>
<li>Raise a ticket immediately with priority <strong>Urgent</strong>.</li>
<li>Select <strong>IT - System Downtime</strong> and sub-issue <strong>System Outage</strong>.</li>
<li>State affected terminals, error codes, and start time.</li>
</ol>
<p>Outage tickets are escalated automatically per MCX escalation rules during market hours.</p>
""",
		},
		{
			"title": "What are MCX trading hours?",
			"content": """
<p>Trading hours vary by commodity segment and contract. Refer to the official MCX circulars and contract calendar on the exchange website for the current schedule.</p>
<p>Pre-open and closing session timings differ by product. Helpdesk can clarify session status if you attach the contract symbol and date of the issue.</p>
""",
		},
		{
			"title": "How do margin requirements work?",
			"content": """
<p>Initial and exposure margin depend on contract, open position, and SPAN parameters set by the clearing corporation.</p>
<p>Margin shortfall may block new orders or trigger square-off. For margin disputes or utilisation queries, raise a ticket under <strong>Trading - Margin Query</strong> with client code and date.</p>
""",
		},
		{
			"title": "Where can I find contract specifications?",
			"content": """
<p>Contract specifications (lot size, tick size, delivery logic) are published on the MCX website under each commodity's product page.</p>
<p>If you need help interpreting a specification for a support ticket, mention the contract symbol and expiry month in your request.</p>
""",
		},
	],
	"Clearing & Settlement": [
		{
			"title": "When will my settlement amount be credited?",
			"content": """
<p>Settlement follows the exchange clearing cycle (typically T+1 for applicable segments). Funds are credited after clearing processing and bank cut-off times.</p>
<p>Delays may occur on bank holidays or if there are holds on the account. Raise a ticket under <strong>Clearing - Settlement</strong> with settlement date and reference ID if credit is overdue.</p>
""",
		},
		{
			"title": "My payout is pending — what should I do?",
			"content": """
<p>Verify that bank details on file are correct and that there are no compliance holds.</p>
<p>Raise a ticket under <strong>Clearing - Payout</strong> with sub-issue <strong>Payout Pending</strong>, including payout date, amount, and bank account last four digits.</p>
""",
		},
		{
			"title": "What is the settlement cycle (T+1)?",
			"content": """
<p>T+1 means transactions executed on trade date (T) are settled on the next business day (T+1), subject to segment rules and holidays.</p>
<p>Clearing statements and ledgers are updated after end-of-day processing. Contact Clearing support for discrepancies between expected and actual settlement.</p>
""",
		},
		{
			"title": "How do I query a settlement discrepancy?",
			"content": """
<p>Attach your clearing statement, highlight the line item in question, and note the trade date and contract.</p>
<p>Select <strong>Clearing - Settlement</strong> and sub-issue <strong>Settlement Delay</strong> or describe the mismatch in the description field.</p>
""",
		},
	],
	"SLA & Escalation": [
		{
			"title": "What are L1, L2, and L3? Teams vs escalation levels",
			"content": """
<h3>Quick answer</h3>
<p><strong>L1, L2, and L3 are not teams.</strong> They are <strong>escalation levels</strong> — steps in a supervisor chain used when a ticket’s SLA is breached or needs senior attention.</p>
<p>A <strong>team</strong> is the department that owns the ticket (for example IT, Trading, Clearing, or Compliance). <strong>L1 / L2 / L3</strong> are <strong>people</strong> (supervisors and executives) who receive the ticket when it is escalated.</p>

<h3>Teams vs escalation levels</h3>
<table class="table table-bordered">
<thead>
<tr><th>Term</th><th>What it is</th><th>Example</th></tr>
</thead>
<tbody>
<tr><td><strong>Team</strong></td><td>Department that handles the ticket (<code>agent_group</code>)</td><td>Trading, Clearing, IT, Compliance</td></tr>
<tr><td><strong>L1</strong></td><td>First-level supervisor for that team</td><td>Trading team lead / shift supervisor</td></tr>
<tr><td><strong>L2</strong></td><td>Department head for that team</td><td>Trading department head</td></tr>
<tr><td><strong>L3</strong></td><td>Top-level escalation (same person for all teams)</td><td>Country head</td></tr>
</tbody>
</table>

<h3>How escalation flows</h3>
<p>When a ticket on a given team breaches SLA (or is re-escalated while still breached), ownership moves up this chain:</p>
<ol>
<li><strong>Level 1 (L1)</strong> — Ticket is assigned to the <strong>L1 Supervisor</strong> configured for that team.</li>
<li><strong>Level 2 (L2)</strong> — If the breach continues, the ticket moves to the team’s <strong>L2 Department Head</strong>.</li>
<li><strong>Level 3 (L3)</strong> — If still unresolved, the ticket is assigned to the global <strong>Country Head (L3)</strong>.</li>
</ol>
<p>Example for a <strong>Trading</strong> ticket:</p>
<ul>
<li>Team = <strong>Trading</strong> (where the work belongs)</li>
<li>L1 → Trading Supervisor (team-specific user)</li>
<li>L2 → Trading Department Head (team-specific user)</li>
<li>L3 → Country Head (global user, all teams)</li>
</ul>

<h3>Simple analogy</h3>
<ul>
<li><strong>Team</strong> — “Which department is working on this?”</li>
<li><strong>L1</strong> — “Who is the first manager notified when it is overdue?”</li>
<li><strong>L2</strong> — “Who is their boss if it is still not fixed?”</li>
<li><strong>L3</strong> — “Who is the senior executive if it remains stuck?”</li>
</ul>

<h3>What triggers escalation?</h3>
<ul>
<li>SLA breach (<code>agreement_status</code> becomes <strong>Failed</strong>)</li>
<li>Re-escalation while the ticket is still open and breached (after the configured re-escalation interval)</li>
<li>Automated workflows (for example Urgent tickets or SLA critical alerts)</li>
</ul>
<p>Proactive SLA warnings (before breach) may notify the team’s <strong>L1 supervisor</strong> without changing escalation level.</p>

<h3>For agents and administrators — where to configure</h3>
<p>Escalation supervisors are configured in Desk, not in code:</p>
<p><strong>Desk → MCX Escalation Settings</strong></p>
<ul>
<li><strong>Team Escalation Rules</strong> (table) — one row per team with <strong>L1 Supervisor</strong> and <strong>L2 Department Head</strong> (User links)</li>
<li><strong>Country Head (L3)</strong> — global top-level assignee for all teams</li>
<li><strong>Deputy Country Head</strong> — optional; receives critical alerts when a ticket is stuck at L3</li>
<li><strong>Re-escalation Interval (Hours)</strong> — how long to wait before moving to the next level if SLA remains breached</li>
</ul>
<p>Each configured user should exist as a <strong>User</strong> and ideally as an <strong>HD Agent</strong> so tickets can be assigned to them.</p>

<h3>Related features</h3>
<ul>
<li><strong>Supervisor Board</strong> — live queue for Agent Managers; shows at-risk tickets (does not define who L1/L2/L3 are)</li>
<li><strong>MCX SLA Alert Settings</strong> — warning/critical thresholds before SLA breach</li>
<li><strong>HD Team</strong> — defines departments for routing; separate from the L1/L2/L3 people matrix</li>
</ul>
""",
		},
		{
			"title": "What are your response time commitments (SLA)?",
			"content": """
<p>SLA targets depend on ticket priority and your service agreement. Typical priorities are Low, Medium, High, and Urgent.</p>
<p>The portal displays SLA status on each ticket (e.g. first response due, resolution due). Proactive alerts warn agents before a breach.</p>
<p>Urgent and High priority tickets receive faster initial response, especially during market hours.</p>
""",
		},
		{
			"title": "What happens if my ticket is not resolved in time?",
			"content": """
<p>When SLA thresholds are approached, tickets are flagged internally and supervisors are notified.</p>
<p>Automatic escalation may reassign the ticket to L2 or country head per MCX escalation rules. You can add a reply requesting escalation if you have not received an update.</p>
""",
		},
		{
			"title": "How does ticket escalation work?",
			"content": """
<p>Escalation is triggered by SLA breach, manual supervisor action, or workflow rules (e.g. unresolved Urgent tickets).</p>
<p>Escalated tickets appear in the supervisor queue with SLA risk indicators. The assigned agent or team lead will take ownership.</p>
""",
		},
		{
			"title": "When should I mark a ticket as urgent?",
			"content": """
<p>Use <strong>Urgent</strong> priority only for:</p>
<ul>
<li>Live market trading blocks affecting multiple users</li>
<li>Clearing or payout failures with immediate financial impact</li>
<li>Complete portal or authentication outage</li>
</ul>
<p>Routine queries should use Medium or High to ensure urgent queues remain available for critical incidents.</p>
""",
		},
		{
			"title": "How do I submit KYC or compliance updates?",
			"content": """
<p>Raise a ticket under <strong>Compliance - KYC</strong> with sub-issue <strong>KYC Update</strong>.</p>
<p>Attach approved forms, board resolutions, or identity documents as required by MCX compliance circulars. Do not send sensitive ID numbers in plain email — use secure attachments on the ticket.</p>
""",
		},
		{
			"title": "How is my data kept secure on the portal?",
			"content": """
<p>The Helpdesk portal uses encrypted connections (HTTPS) and role-based access. Tickets and attachments are visible only to authorised agents and your organisation's users.</p>
<p>Do not share login credentials. Report suspected unauthorised access immediately under <strong>IT - Portal Access</strong>.</p>
""",
		},
	],
}


def ensure_faq_setup():
	if "helpdesk" not in frappe.get_installed_apps():
		return
	if not frappe.db.exists("DocType", "HD Article"):
		return

	for category_label in FAQ_CATEGORIES:
		category_name = f"{FAQ_CATEGORY_PREFIX} — {category_label}"
		category_id = _ensure_category(category_name)
		for article in DEFAULT_FAQS.get(category_label, []):
			_ensure_article(category_id, article["title"], article["content"])


def _ensure_category(category_name: str) -> str:
	existing = frappe.db.get_value("HD Article Category", {"category_name": category_name})
	if existing:
		return existing

	doc = frappe.get_doc({"doctype": "HD Article Category", "category_name": category_name})
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_article(category_id: str, title: str, content: str):
	existing = frappe.db.get_value("HD Article", {"title": title, "category": category_id})
	if existing:
		current_content = frappe.db.get_value("HD Article", existing, "content")
		if (current_content or "").strip() != content.strip():
			frappe.db.set_value("HD Article", existing, {"content": content.strip(), "status": "Published"})
		return

	author = frappe.session.user if frappe.session.user != "Guest" else "Administrator"
	doc = frappe.get_doc(
		{
			"doctype": "HD Article",
			"title": title,
			"category": category_id,
			"content": content.strip(),
			"status": "Published",
			"published_on": datetime.now(),
			"author": author,
		}
	)
	doc.insert(ignore_permissions=True)
