# Document Audit Trail for Odoo 19 Enterprise

A complete, standalone audit-logging solution for the Odoo 19 Enterprise
**Documents** app. It records every standard action performed on any document,
links all of a document's actions into a single timeline that survives even
deletion, and ships with an animated analytics dashboard plus an admin
follow-up workflow.

---

## Overview

Document Audit Trail captures everything that happens to your documents and
presents it three ways: a chronological **per-document timeline**, a filterable
**list of all actions** (with graph and pivot views), and a live, animated
**dashboard**. It is built natively on Odoo 19's OWL framework and uses
Chart.js for the dashboard visualizations.

The module is fully self-contained — it does **not** depend on any custom
module — and every tracked operation can be switched on or off from Settings.

## What It Tracks

### Server-side (ORM)
- **Created** — a document is added
- **Updated** — field-level diff of what changed (name, folder, owner, tags, etc.)
- **Archived / Restored**
- **Deleted** — the entry survives the deletion
- **Locked / Unlocked**
- **Replaced** — a new version is uploaded
- **Version restored**

### Front-end
- **Downloaded**
- **Preview opened / closed**
- **Shared**
- **Split**

### E-signature (Sign)
- **Signature requested**
- **Signature completed**
- **Signature field added / removed** in the editor (with field type)
- **Field signed** — one entry per field, capturing the field type, the signer
  and the entered value (drawn signatures are stored as a placeholder, not raw
  image data)

## Key Features

### Animated Dashboard
A custom OWL client action (**Document Audit → Dashboard**) with:
- Six KPI cards (period actions, all-time total, signature events, deletions,
  open follow-ups, active users) with count-up animation
- Activity-over-time bar chart and by-operation doughnut (Chart.js)
- "Most active users" and "most active documents" ranked bars
- A live recent-activity feed
- Date-range presets (7d / 30d / 90d / 1y)
- Every card, bar and feed item drills into the underlying records

### Per-Document Trail
Every action on a document is linked to a single `audit.trail` record, so the
full history stays connected across days. The trail keeps a stored document
name, so the timeline remains available even after the document is deleted.
Browse trails as cards or a list under **Document Trails**.

### Admin Follow-up Workflow
Flag any action for review, assign it to a user, add review notes and resolve
it via a status bar (Not Flagged → Needs Review → In Progress → Resolved).
A dedicated **Follow-ups** view lists everything awaiting attention.

### Configuration & Retention
From **Settings**, toggle the master switch, enable/disable each individual
operation, and set an automatic log-retention period (a daily cron removes
entries older than N days; 0 keeps everything).

### Security
Two roles ship with the module:
- **Document Audit: Read Own** — users see only their own actions
- **Document Audit: Manager** — sees everything and owns the follow-up workflow

## Requirements

| Component | Requirement |
|-----------|-------------|
| Odoo | 19.0 Enterprise |
| Required apps | Documents, Sign |
| Depends on | `base`, `web`, `documents`, `sign` |

## Installation

1. Copy the `odoo_document_audit_trail` directory into your Odoo addons path.
2. Restart the Odoo server and update the apps list.
3. Open **Apps**, search for "Document Audit Trail", and install.

Or from the command line:
```
./odoo-bin -d <database> -i odoo_document_audit_trail --stop-after-init
```

After installation the **Document Audit** application appears in the main menu.

## Usage

- **Dashboard** — open `Document Audit → Dashboard` for the live overview.
- **Document Trails** — one entry per document with its action count and full
  timeline.
- **All Actions** — the complete log, with list / graph / pivot views and
  group-by filters.
- **Follow-ups** — manager view of flagged items.

From any audit entry you can open the document, open the related sign request,
view the document's full timeline, or run the follow-up actions.

## Configuration

Open **Settings**, find the **Audit Trail** section, and adjust:

| Setting | Description |
|---------|-------------|
| Enable Document Audit Trail | Master on/off switch |
| Log Retention (days) | Daily cron deletes older logs; 0 = keep forever |
| Tracked Operations | Individual on/off switches for each operation |

## Architecture

```
odoo_document_audit_trail/
├── __manifest__.py
├── models/
│   ├── audit_trail.py            Per-document trail (timeline + stats)
│   ├── audit_trail_entry.py      The audit log entry + dashboard data
│   ├── documents_document.py     ORM hooks + JS RPC entry points
│   ├── sign_request.py           Signature field-level hooks
│   └── res_config_settings.py    Settings toggles
├── views/
│   ├── audit_trail_entry_views.xml
│   ├── audit_trail_views.xml
│   ├── dashboard_action.xml
│   ├── documents_document_views.xml
│   ├── res_config_settings_views.xml
│   └── menu.xml
├── security/
│   ├── document_audit_security.xml
│   └── ir.model.access.csv
├── data/
│   ├── ir_config_parameter_data.xml
│   └── ir_cron_data.xml
└── static/
    ├── description/              Icon, banner, store page, screenshots
    └── src/
        ├── js/                   Dashboard component + logger service + patch
        ├── xml/                  Dashboard OWL template
        └── css/                  Dashboard + list styling
```

## Compatibility Notes

Targets **Odoo 19.0 Enterprise** exclusively. It uses Odoo 19 APIs that are not
backward compatible:
- `res.groups.privilege` (replaces the removed `res.groups.category_id`)
- `group_ids` on `res.users` (renamed from `groups_id`)
- The OWL 3 component framework

It will not install or run on Odoo 18 or earlier.

## Support

Email **msnsupport0@gmail.com** for installation help, configuration questions,
or bug fixes.

## License

Odoo Proprietary License v1.0 (OPL-1). See `LICENSE` for full text.
