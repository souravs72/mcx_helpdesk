# MCX Helpdesk

Custom Frappe app extending [Frappe Helpdesk](https://github.com/frappe/helpdesk) for MCX-style multi-level ticket classification and email routing.

## Features

- **Multi-level classification**: Department (`agent_group` / HD Team), Issue Type (`ticket_type`), Sub Issue Type (`sub_issue_type`)
- **Email auto-classification**: Parses `[TEAM:…][TYPE:…][SUB:…]` tags and keyword rules from inbound emails
- **Assignment routing**: Uses native HD Team assignment rules (round-robin per department)
- **Cascading filters**: Sub Issue Type filtered by Issue Type on the ticket form
- **UI relabeling**: Team → Department, Ticket Type → Issue Type (Property Setters, Translations, dashboard API)

## Requirements

- Frappe v16+
- Helpdesk app (`required_apps` in hooks)

## Install

```bash
bench get-app https://github.com/souravs72/mcx_helpdesk
bench --site your.site install-app mcx_helpdesk
bench --site your.site migrate
```

### Production vs demo

| Behaviour | Production (default after upgrade) | Demo (fresh install default) |
|-----------|-----------------------------------|------------------------------|
| Custom fields, labels, masters | Yes — every install/migrate | Yes |
| Demo users / passwords | No | Yes (on `install-app` only) |
| Email account → HD Ticket | No | Yes |
| HD Teams with demo agents | No — create your own | Yes |

Disable demo seed on install by adding to `site_config.json`:

```json
{
  "mcx_helpdesk_demo_mode": false
}
```

Re-enable demo seed manually:

```bash
bench --site your.site execute mcx_helpdesk.setup.demo.setup_demo_site
```

## Sync architecture

Following ERPNext/Telephony patterns:

- **`sync_mcx_helpdesk()`** — production-safe, idempotent; runs on install and every migrate
- **`setup_demo_site()`** — demo users, teams, email; runs only on `after_install` when demo mode is enabled
- **Patches** — versioned under `patches/v1_0/`, listed in `patches.txt` with `[post_model_sync]`
- **Fixtures** — tightly filtered exports (Custom Field, Property Setters, masters, translations)

Export fixtures after site changes:

```bash
bench --site your.site export-fixtures
```

## Email subject format

Put **classification tags in the subject** (recommended) or on the **first line of the email body**. Tags are stripped from the stored ticket subject.

### Full format (sets all fields)

```
[DEPT:IT][TYPE:Portal Access][SUB:Password Reset][CUSTOMER:MCX Member Corp][ASSIGN:agent@yourcompany.com] Unable to login to portal
```

### Tag reference

| Tag | Sets field | Example value | Notes |
|-----|------------|---------------|-------|
| `[DEPT:…]` or `[TEAM:…]` | Department | `IT`, `Trading`, `Clearing`, `Compliance` | Must match an **HD Team** name on your site |
| `[TYPE:…]` | Issue Type | `Portal Access` | Partial match OK → e.g. `IT - Portal Access` |
| `[SUB:…]` | Sub Issue Type | `Password Reset` | Partial match; filtered by Issue Type |
| `[CUSTOMER:…]` or `[CUST:…]` | Customer | `MCX Member Corp` | Matches **HD Customer** name or domain |
| `[ASSIGN:…]` or `[ASSIGNEE:…]` | Assignee | `agent@yourcompany.com` | Must be an **HD Agent** user email or name |

### Ready-to-send examples

**IT login issue (keyword fallback also works without tags):**
```
Subject: [DEPT:IT][TYPE:Portal Access][SUB:Password Reset] Unable to login to member portal

Body:
Dear Support,
I cannot reset my password on the trading portal.
Regards,
Member
```

**Trading order rejection with customer and assignee:**
```
Subject: [DEPT:Trading][TYPE:Order Entry][SUB:Order Rejection][CUSTOMER:ABC Brokers][ASSIGN:trading.agent@demo.com] Order rejected on MCX

Body:
My order ORD-9921 was rejected. Please investigate.
```

**Tags in body instead of subject:**
```
Subject: Login problem on portal

Body:
[DEPT:IT][TYPE:Portal Access][SUB:Login Issue]

I am unable to sign in since this morning.
```

### Keyword-only (no tags)

If you omit tags, the system matches keywords in subject + body:

| Keywords in email | Auto-routed to |
|-------------------|----------------|
| login, password, portal access | IT → Portal Access → Login Issue |
| system down, outage, downtime | IT → System Downtime → System Outage |
| settlement, clearing delay | Clearing → Settlement |
| payout, payment pending | Clearing → Payout |
| order reject, order entry | Trading → Order Entry |
| margin, price mismatch | Trading → Margin Query |
| kyc | Compliance → KYC |
| regulatory, compliance report | Compliance → Reporting |

### Prerequisites on your site

1. **Departments** — create HD Teams (Trading, Clearing, IT, Compliance) with agents
2. **Customers** — create **HD Customer** records for `[CUSTOMER:…]` tags
3. **Agents** — assignee email must exist as **HD Agent**
4. **Email account** — incoming mail appended to **HD Ticket** (IMAP INBOX)

## Development

```bash
python -m compileall -f mcx_helpdesk
ruff check mcx_helpdesk
bench --site your.site run-tests --app mcx_helpdesk
```

## License

MIT
