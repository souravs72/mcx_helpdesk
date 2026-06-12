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

```
[TEAM:IT][TYPE:Portal Access][SUB:Password Reset] Unable to login to member portal
```

`[DEPT:…]` is accepted as an alias for `[TEAM:…]`. Keyword matching works when tags are omitted.

## Development

```bash
python -m compileall -f mcx_helpdesk
ruff check mcx_helpdesk
bench --site your.site run-tests --app mcx_helpdesk
```

## License

MIT
