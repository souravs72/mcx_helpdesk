app_name = "mcx_helpdesk"
app_title = "MCX Helpdesk"
app_publisher = "Ascra Technologies LLP"
app_description = "MCX Helpdesk customizations for RFP demo (classification and routing)"
app_email = "info@ascra.com"
app_license = "mit"

required_apps = ["helpdesk"]

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [["name", "in", ["HD Ticket-sub_issue_type"]]],
	},
	{
		"dt": "Property Setter",
		"filters": [
			[
				"name",
				"in",
				[
					"HD Ticket-ticket_type-label",
					"HD Ticket-agent_group-label",
					"HD Team-team_name-label",
				],
			]
		],
	},
	{
		"dt": "HD Form Script",
		"filters": [["name", "=", "Field Dependency-ticket_type-sub_issue_type"]],
	},
	{"dt": "HD Ticket Template", "filters": [["name", "=", "Default"]]},
	{
		"dt": "HD Sub Issue Type",
		"filters": [
			[
				"sub_issue_name",
				"in",
				[
					"Order Rejection",
					"Price Mismatch",
					"Settlement Delay",
					"Payout Pending",
					"Login Issue",
					"Password Reset",
					"System Outage",
					"Regulatory Filing",
					"KYC Update",
				],
			]
		],
	},
	{
		"dt": "HD Ticket Type",
		"filters": [
			[
				"name",
				"in",
				[
					"Trading - Order Entry",
					"Trading - Margin Query",
					"Clearing - Settlement",
					"Clearing - Payout",
					"IT - Portal Access",
					"IT - System Downtime",
					"Compliance - Reporting",
					"Compliance - KYC",
				],
			]
		],
	},
	{
		"dt": "Translation",
		"filters": [
			[
				"source_text",
				"in",
				[
					"Team",
					"Teams",
					"Team Name",
					"Ticket Type",
					"Tickets by Team",
					"Tickets by Type",
					"No Team",
					"No team data",
					"Tickets will be grouped by team once available.",
					"No ticket type data",
					"Tickets will be categorized by type once created.",
					"Percentage of total tickets by team",
					"Total tickets by team",
					"Percentage of total tickets by type",
					"Total tickets by type",
				],
			]
		],
	},
]

after_install = "mcx_helpdesk.setup.sync.after_install"

after_migrate = ["mcx_helpdesk.setup.sync.after_migrate"]

override_whitelisted_methods = {
	"helpdesk.api.dashboard.get_dashboard_data": "mcx_helpdesk.api.dashboard.get_dashboard_data",
}

doc_events = {
	"HD Ticket": {
		"before_validate": "mcx_helpdesk.mcx_helpdesk.ticket_classifier.classify_ticket",
		"after_insert": "mcx_helpdesk.mcx_helpdesk.ticket_classifier.apply_classified_assignee",
	}
}
