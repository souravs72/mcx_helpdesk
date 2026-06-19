# MCX Helpdesk — Client Demo Guide

This is a walkthrough script for presenting everything we've built. Read it once beforehand so the flow feels natural — you shouldn't need to glance at it during the demo.

---

## What you're showing them (the big picture)

We've taken the standard Frappe Helpdesk and turned it into an MCX-specific support platform. The main themes to land with the client:

- **Customers** get a self-service portal — FAQ chatbot, ticket creation with proper classification, SLA visibility, and escalation transparency.
- **Agents** land on a real operations dashboard, see SLA risk on every ticket, and get AI help drafting replies.
- **Supervisors and managers** get a live queue board, org-wide analytics, and proactive SLA alerts — not just reports after things have already gone wrong.
- **Everything is configurable in Desk** — routing rules, escalation matrix, workflows, SLA thresholds, AI settings. No code deploys needed to change business logic.

---

## Before the demo — quick checklist

Run through this the day before (or morning of). Nothing kills a demo faster than a blank screen.

### Environment

- Site is up, `bench migrate` has been run, scheduler is running (`bench schedule` or your production workers).
- Desk frontend is built: from `desk/`, run the build so all UI overrides are live.
- You have three browser profiles or incognito windows ready:
  - **Customer** — a portal user (HD Customer linked)
  - **Agent** — someone with the HD Agent role
  - **Manager** — someone with Agent Manager role (for Live Queue and org dashboard views)

### Demo data

If this is a fresh install with demo mode on (default), you already have:

- Departments: **Trading, Clearing, IT, Compliance**
- Demo agents like `mcx.trading.agent@demo.com`, `mcx.clearing.agent@demo.com`, etc. (password: `demo@123`)
- Escalation chain users (supervisors, dept heads, country head) seeded automatically
- ~25 FAQ articles across 6 categories
- 13 classification rules (password reset → IT, payout pending → Clearing, order rejection → Trading, etc.)
- Default workflows (SLA warning, SLA critical, system outage → urgent, KYC → compliance ToDo)

For a convincing SLA/escalation segment, prepare a few tickets beforehand:

- One ticket at **Warning** level (~75% SLA elapsed)
- One at **Critical** (~90%)
- One that's **breached** or escalated to L1/L2

If you don't have those yet, create urgent tickets with short SLAs and let the scheduler run for a few minutes — proactive alerts fire every 5 minutes, breach escalations every 15.

### AI (optional but impressive)

Open **MCX AI Settings** in Frappe Desk (`/app/mcx-ai-settings`):

- Turn on **Enable AI Assistance**
- Add your API key (OpenAI-compatible)
- Enable: classify on create, suggest reply, summarize ticket
- For the chatbot: enable customer chatbot; turn on `chatbot_use_ai` if you want the fancier answers (works without AI too — it'll pull FAQ excerpts)

The chatbot and classification rules work without AI. AI is the cherry on top.

---

## How to open things

| Who | Where |
|-----|-------|
| Agent desk | `/helpdesk/` → lands on Dashboard |
| Manager live queue | `/helpdesk/supervisor-board` (sidebar: **Live Queue**) |
| Customer portal | `/helpdesk/my-tickets` |
| Frappe Desk (admin config) | `/app` → search for MCX doctypes |

From the agent user menu (bottom of sidebar), there's a **Customer portal** link that opens the portal in a new tab — handy for switching perspectives mid-demo.

---

## The demo — how to walk through it

Aim for 35–45 minutes. Adjust based on what the client cares about most.

---

### Part 1 — Customer experience (~10 min)

*Start here. This is what their members and brokers will actually use.*

**Open the customer portal** (`/helpdesk/my-tickets`).

"So this is what your customers see when they log in. Clean, simple — their tickets and the knowledge base. No agent clutter."

**Show the FAQ chatbot** — bottom-right floating button.

"Before they even raise a ticket, they can ask questions. We've loaded about 25 articles covering trading, clearing, portal access, SLAs — all MCX-specific content."

Click it, try something like:
- *"How do I reset my password?"*
- *"What is the settlement cycle?"*

Point out the suggested questions, the source article links at the bottom of answers, and the **Create a support ticket** button when the bot can't help enough.

"This runs off your own knowledge base. You edit articles in Desk, the chatbot picks them up. If you turn on AI mode, it synthesizes answers from those articles — but it won't make things up; it stays grounded in what you've published."

**Create a new ticket** (`/helpdesk/my-tickets/new`).

"Watch the form — when they pick an Issue Type, the Sub Issue Type unlocks and filters to relevant options. That structure is what drives your routing and reporting."

Create something like:
- Subject: *"Unable to reset my password on the trading portal"*
- Issue Type: IT - Portal Access → Sub Issue Type: Password Reset

Submit it.

"Behind the scenes, our classification engine picked this up — keyword rules matched 'password reset' and routed it to IT automatically. No agent had to triage it."

**Open the ticket detail.**

Show the sidebar: ticket ID, status, SLA badges (first response + resolution targets).

"If this ticket is getting close to breaching SLA, they'll see a yellow warning banner. If it's breached, they see red. And if it's been escalated, they see the escalation level — L1 Supervisor, L2 Department Head, L3 Country Head — without exposing your internal org chart."

**Reply in the conversation**, then maybe close and reopen the ticket to show the reopen flow.

"Customers only see the conversation thread. Internal agent notes, escalation history, assignment changes — all of that stays hidden on the agent side. We've locked that down at the API level, not just the UI."

---

### Part 2 — Agent workflow (~10 min)

*Switch to the agent browser.*

**Land on the Dashboard** (`/helpdesk/dashboard`).

"When an agent logs in, they don't land on a generic home page anymore — they land here. This is their operational view."

Walk through:
- Period filter (Today, Last 7 days, etc.)
- Personal KPIs: open tickets, SLA at risk, escalated count
- The **Needs Attention** tabs — SLA Alerts, Awaiting Response, My Open, Recently Assigned
- Click a ticket from the list to jump straight into it

"Everything they need to act on is right here. No hunting through ticket lists."

**Open a ticket** (`/helpdesk/tickets/{id}`).

Go to the **Details** tab in the right sidebar.

"Agents see SLA risk right on the ticket — warning at 75%, critical at 90%. If it's been escalated, there's a banner showing the level. And down here is AI Assist."

**Demo AI Assist** (if configured):

- Click **Suggest reply** — show the draft
- Click **Use in reply** — it drops into the email composer at the bottom
- Optionally **Summarize** for a handoff summary

"This pulls from the ticket thread and your knowledge base articles. One click to use the draft. Agents stay in their workflow — no copy-pasting between tools."

Show the **Issue Type / Sub Issue Type** fields on the Details tab too — same cascading behaviour as the customer form.

**Send a reply** from the conversation area at the bottom.

"Standard reply, comment, call log tabs — all the usual Helpdesk stuff, just wired so AI plugs straight in."

---

### Part 3 — Manager and supervisor view (~10 min)

*Switch to the manager browser.*

**Dashboard — Overview tab.**

"As a manager, you get the org-wide picture. Same dashboard, different tabs."

Show:
- Org KPIs across all departments
- Trend charts
- Action lists: Unassigned, SLA Warning, SLA Critical, Breached, Escalated
- Click into a list, open a ticket

**By Department tab.**

"Capacity and SLA performance broken down by department — Trading, Clearing, IT, Compliance. You can see who's overloaded and where SLA is slipping."

**By Agent tab** (or the leaderboard on Overview).

"Drill into any agent's performance. Useful for 1-on-1s and workload balancing."

**Live Queue** (`/helpdesk/supervisor-board`).

"This is the piece supervisors will live in during market hours."

Walk through:
- The table of open tickets sorted by nearest SLA deadline
- Live countdown timers (they tick every second)
- Risk badges — green, yellow at 75%, red at 90%
- Department filter
- Click a row to jump to the ticket

"Auto-refreshes every 30 seconds, and it also listens for real-time updates. No exporting to Excel to figure out what's about to breach."

---

### Part 4 — The intelligence behind it (~8 min)

*This is where you show it's not magic — it's configurable.*

Switch to **Frappe Desk** (`/app`).

**MCX Classification Rule**

"We've seeded 13 rules, but your team can add more anytime."

Open a rule like "Password Reset" — show keywords, department, issue type, sub-issue, priority.

"Keywords in the subject or body match, ticket gets routed. Priority order controls which rule wins. Your ops team edits these in Desk — no developer needed."

Quickly mention the other layers:
- Email tags: `[DEPT:Trading][TYPE:Order Entry][SUB:Order Rejection]` in the subject
- AI classification when rules don't match (if enabled)
- Round-robin assignment within the department

**MCX Escalation Settings**

"Three-level escalation chain per department."

Show the matrix: L1 Supervisor, L2 Department Head, L3 Country Head. Re-escalation interval. Country Head for critical alerts.

"When SLA breaches, the ticket doesn't just sit there. It escalates through the chain — reassignment, priority bump, customer notification, activity log entry. And if it's still stuck at L3 after the interval, it fires a critical alert."

**MCX SLA Alert Settings**

"Proactive, not reactive. Warning at 75%, critical at 90%. Emails to assignee and supervisor. Triggers workflows."

**MCX Service Workflow**

"Automation rules your admins control."

Show a couple:
- SLA Warning → notify assignee + internal comment
- SLA Critical → bump priority + notify supervisor
- System Outage ticket → set Urgent + notify supervisor

"Trigger on ticket created, status changed, first response, resolved, or SLA events. Actions: assign, set fields, send email, create ToDo, trigger escalation. All editable."

**MCX AI Settings**

"One place to control AI — provider, model, API key, which features are on. Agent assist and customer chatbot from the same settings."

---

### Part 5 — Email routing (bonus, if they care) (~5 min)

"If your customers email support instead of using the portal, the same engine kicks in."

Show the README examples or send a test email:

```
Subject: [DEPT:Clearing][TYPE:Payout][SUB:Payout Pending] CPO settlement not received for member 12345
```

"Tags in the subject set department, type, sub-issue, customer, even assignee. Tags get stripped from the stored subject so agents see a clean title. And if someone just writes 'password reset' with no tags, keyword rules catch it."

---

## Demo users (demo mode)

| Role | Example email | Password |
|------|---------------|----------|
| Trading Agent | `mcx.trading.agent@demo.com` | `demo@123` |
| Clearing Agent | `mcx.clearing.agent@demo.com` | `demo@123` |
| Trading Supervisor (L1) | `mcx.trading.supervisor@demo.com` | `demo@123` |
| Trading Dept Head (L2) | `mcx.trading.head@demo.com` | `demo@123` |
| Country Head (L3) | `mcx.country.head@demo.com` | `demo@123` |

Create a customer user linked to an HD Customer record for the portal demo.

---

## If something goes wrong

| Problem | Fix |
|---------|-----|
| AI buttons greyed out | Check MCX AI Settings — enabled + API key |
| Chatbot says nothing useful | FAQ articles must be published under categories starting with "MCX FAQ —" |
| SLA risk not updating | Scheduler must be running; wait up to 5 min or trigger manually |
| Escalation didn't fire | Check MCX Escalation Settings is enabled; ticket must have breached SLA |
| Dashboard looks like stock Helpdesk | Rebuild desk frontend (`desk/` build) |
| Classification didn't route | Check rule is enabled, keywords match, priority order |
| Customer sees internal notes | Shouldn't happen — if it does, flag it; API strips those fields |

---

## Closing lines (say these naturally)

"We've built this in layers — self-service for customers, productivity tools for agents, real-time visibility for supervisors, and a configuration layer your ops team owns."

"Nothing here is hardcoded. Routing rules, escalation matrix, workflows, SLA thresholds, FAQ content, AI toggles — all editable in Desk."

"The scheduler runs proactive SLA monitoring every 5 minutes and breach escalations every 15. Your team gets warned before things break, not after."

"Happy to go deeper on any piece — or we can set up a sandbox with your actual department structure and escalation contacts."

---

## Quick reference — what's new in this release

### Customer-facing
- Dedicated customer portal with FAQ chatbot (floating on every page)
- SLA warning/breach banners on ticket detail
- Escalation level visible to customers (L1/L2/L3)
- Issue Type → Sub Issue Type on ticket creation
- Reopen closed tickets
- Portal API hides internal comments and history

### Agent-facing
- Dashboard-first landing (not generic Home)
- MCX analytics dashboard with personal KPIs and action lists
- SLA risk banners on ticket Details tab
- Escalation status on ticket Details tab
- AI Assist panel — suggest reply, summarize, inject into composer
- Sub Issue Type field with cascading filter

### Manager / supervisor
- Live Queue board with real-time SLA countdowns
- Org dashboard: Overview, By Agent, By Department tabs
- Agent leaderboard
- Action lists: unassigned, SLA warning/critical/breached, escalated

### Backend / automation
- Keyword classification rules (13 seeded, editable)
- Email tag parsing (`[DEPT:…][TYPE:…][SUB:…][CUSTOMER:…][ASSIGN:…]`)
- AI classification, reply suggestion, ticket summary
- Proactive SLA alerts (75% / 90% thresholds)
- Three-level SLA breach escalation (L1 → L2 → L3)
- Configurable service workflows (8 trigger events, 9 action types)
- ~25 FAQ articles across 6 MCX categories
- Scheduler jobs for SLA monitoring and escalations

### Admin doctypes (Frappe Desk)
- MCX AI Settings
- MCX Classification Rule
- MCX Escalation Settings + MCX Escalation Rule
- MCX SLA Alert Settings
- MCX Service Workflow + MCX Workflow Action
