# MCX Helpdesk

Custom app for the MCX RFP Helpdesk demo on Frappe Helpdesk.

## Features

- **Multi-level classification**: Team (`agent_group`), Issue Type (`ticket_type`), Sub Issue Type (`sub_issue_type`)
- **Email auto-classification**: Parses `[TEAM:…][TYPE:…][SUB:…]` tags and keyword rules from inbound emails
- **Assignment routing**: Uses native HD Team assignment rules (round-robin per team)
- **Cascading filters**: Sub Issue Type filtered by Issue Type on the ticket form

## Install

```bash
bench get-app https://github.com/ascra-tech/mcx_helpdesk  # when published
bench --site mcx.site install-app mcx_helpdesk
bench --site mcx.site migrate
```

## Email subject format (demo)

```
[TEAM:IT][TYPE:Portal Access][SUB:Password Reset] Unable to login to member portal
```

Keyword matching also works when tags are omitted, e.g. subject containing "login" routes to IT.

## Fixtures

Configuration is exported via `bench --site mcx.site export-fixtures` and synced on migrate.
