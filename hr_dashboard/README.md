# HR Dashboard for Odoo 19 Enterprise

A modern, interactive analytics dashboard for the Odoo 19 Enterprise Human Resources suite. Provides HR managers with a single-pane-of-glass view of workforce metrics, real-time attendance, leave and expense pipelines, payroll summaries, and performance appraisal status — all visualized through a polished glassmorphism interface with full theme customization, drill-downs to underlying records, and inline approval workflows.

---

## Overview

The HR Dashboard consolidates information from across the Odoo 19 HR stack — Employees, Attendances, Time Off, Expenses, Payroll, and Appraisals — into a single live dashboard. It is designed for HR managers, department heads, and executives who need to monitor workforce health and process pending approvals without navigating multiple apps.

The module is built natively on Odoo 19's OWL component framework, uses Chart.js 4.4 for visualizations, and supports right-to-left layouts with a complete Arabic translation included out of the box.

## Key Features

### Real-Time KPI Cards
Ten interactive KPI cards display the most critical HR metrics:

- **Total Employees** — Active workforce headcount
- **Present Today** — Live attendance count with 14-day trend sparkline
- **Pending Leaves** — Leave requests awaiting first or second approval
- **New Hires** — Employees onboarded within the selected date range
- **Pending Expenses** — Expenses in draft or submitted state, with breakdown by stage
- **Employee Versions** — Active contract versions (Odoo 19's replacement for `hr.contract`)
- **Pending Appraisals** — Performance reviews in Draft or Ongoing state
- **Completed Appraisals** — Reviews finalized within the selected period
- **Payslips** — Payroll runs in the selected period, broken down by status
- **Net Wage Total** — Aggregated net wage payout in range

Every card is click-through: selecting any KPI opens the underlying Odoo record list, pre-filtered to match the metric, with create/delete actions disabled by default to preserve dashboard intent.

### Interactive Charts
Eight Chart.js visualizations render data shape at a glance:

- Attendance Trend (last 14 days, line)
- Gender Distribution (active employees, doughnut)
- Employees by Department (clickable bar)
- Leaves by Type (pie)
- Employee Growth (last 6 months, area)
- Expenses by Category (horizontal bar)
- Appraisals by Status (bar)
- Appraisal Distribution (doughnut)

Charts inherit the configured theme colors and resize responsively. The department chart supports drill-through: clicking a bar opens the employees of that department.

### Employee Spotlight Section
An expandable section (toggle switch) lets a manager pick any employee from a searchable picker and view a unified profile card containing:

- Personal and contact information
- Manager hierarchy
- Current HR Version (wage, contract type, schedule, resource calendar)
- Per-employee leave, attendance, expense, payslip counts
- Latest payslip card with print action
- Drill-downs to each related record set

### Approvals Center
A second toggleable section centralizes pending requests across three tabs:

- **Leaves** — Pending time-off requests with one-click Approve/Refuse buttons, supporting both single and double-validation workflows
- **Expenses** — Expenses needing review (draft and submitted states), with smart approve that submits drafts and approves submitted items in one click
- **Appraisals** — Performance reviews in Draft or Ongoing state, with state-aware buttons (Confirm for Draft, Mark Done for Ongoing) and a Reset action for returning records to Draft

Each row displays the employee avatar, request details, due date, and current state. Actions execute against the actual Odoo workflow methods (action_approve, action_confirm, action_validate) and respect existing access rights — managers without time-off approval permissions will see standard Odoo access errors surfaced as inline notifications. After every approval action, the dashboard KPIs refresh automatically.

### Glassmorphism Theme System
Every visual element is driven by CSS custom properties bound to configuration records. Out of the box the dashboard ships with an earthy palette (olive, copper, caramel, walnut), but every color, gradient stop, glass opacity, blur intensity, and border radius is editable from a single configuration form. Changes take effect on next dashboard load without requiring a module upgrade.

### Internationalization
The module includes a complete Arabic translation (`i18n/ar_001.po`) covering all 158 user-facing strings. The SCSS includes a dedicated `[dir="rtl"]` block that flips directional properties, embeds numeric values as LTR within RTL text (financial best practice), and adjusts typography for Arabic. Switching the user's language to Arabic instantly renders the dashboard in RTL with translated labels.

## Requirements

| Component | Requirement |
|-----------|-------------|
| Odoo | 19.0 Enterprise |
| Python | 3.10 or higher |
| Required modules | `base`, `web`, `hr`, `hr_attendance`, `hr_holidays`, `hr_expense` |
| Optional modules | `hr_payroll` (enables Payslips KPIs and Net Wage Total), `hr_appraisal` (enables Appraisals KPIs, charts, and approval tab) |
| Browser | Modern evergreen (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+) |

The dashboard degrades gracefully when optional modules are not installed — Payslip and Appraisal sections simply hide rather than producing errors.

## Installation

1. Copy the `hr_dashboard` directory into your Odoo `addons` path:
   ```
   cp -r hr_dashboard /path/to/odoo/addons/
   ```
2. Restart the Odoo server:
   ```
   ./odoo-bin -c odoo.conf -u all
   ```
3. Activate developer mode in Odoo, then go to **Apps**, click **Update Apps List**, search for "HR Dashboard", and install.

Alternatively, install directly from the command line:
```
./odoo-bin -d <database> -i hr_dashboard --stop-after-init
```

After installation, the **HR Dashboard** application appears in the main app menu.

## Usage

### Opening the Dashboard
Click the **HR Dashboard** app from the main Odoo menu. The dashboard loads with data covering the last 30 days by default. Use the date range selector in the header to switch between presets (Today, Last 7 days, Last 30 days, This month, This quarter, This year) or pick a custom range.

### Drilling Down
Every KPI card and most chart elements are interactive:

- Click a **KPI card** to open the filtered list of underlying records
- Click a **department bar** to see the employees in that department
- Click the **Refresh** button in the header to force a data reload

### Employee Spotlight
Toggle the **Employee Spotlight** switch (below the charts) to enable the profile drill-down. Use the search box to filter by employee name, job title, or department, then click a card to view that employee's full data. The Spotlight remains active until toggled off.

### Approvals Center
Toggle the **Approvals Center** switch to see pending items. Choose a tab (Leaves, Expenses, or Appraisals) and use the inline Approve/Refuse buttons on each row. Actions execute immediately and refresh the relevant counters.

## Configuration

The dashboard's appearance is driven by configuration records in the `hr.dashboard.config` model. To customize the theme:

1. Navigate to **HR Dashboard** in the main menu, then open **Configuration → Dashboard Theme** from the submenu
2. Open the active configuration record (one is pre-created on install)
3. Adjust any of the fields below and save
4. Reload the dashboard tab to see changes

### Branding

| Field | Description |
|-------|-------------|
| **Configuration Name** | Internal label for the configuration record |
| **Active** | Only the active configuration is used by the dashboard |
| **Dashboard Title** | Main heading shown in the dashboard header (default: HR Analytics) |
| **Subtitle** | Secondary heading line below the title |
| **Dashboard Logo** | Binary image displayed in the header (PNG/JPG/SVG) |
| **Show Logo** | Toggle logo visibility without removing the image |

### Theme Colors

All colors accept standard CSS color values (hex, rgb, hsl). Defaults shown reflect the shipped earthy palette.

| Field | Default | Used For |
|-------|---------|----------|
| **Primary Color** | `#606C38` (Olive Leaf) | Buttons, links, primary accents |
| **Secondary Color** | `#BC6C25` (Copper) | Section badges, secondary highlights |
| **Accent Color** | `#DDA15E` (Light Caramel) | Hover states, focus rings |
| **Text Color** | `#283618` (Black Forest) | Primary text |
| **Muted Text Color** | `#606C38` (Olive Leaf) | Labels, secondary text |

### Background Gradient

The dashboard background uses a three-stop linear gradient:

| Field | Default |
|-------|---------|
| **Background Gradient Start** | `#FEFAE0` (Cornsilk) |
| **Background Gradient Middle** | `#F5EFC9` |
| **Background Gradient End** | `#E9D9A8` |

### Card Colors

Each KPI card category has a dedicated accent color. These also propagate to the matching charts.

| Field | Default | Bound To |
|-------|---------|----------|
| **Card Color 1** | `#606C38` (Olive) | Employees |
| **Card Color 2** | `#283618` (Black Forest) | Attendance |
| **Card Color 3** | `#DDA15E` (Light Caramel) | Leaves |
| **Card Color 4** | `#BC6C25` (Copper) | Payroll |
| **Card Color 5** | `#A0522D` (Sienna) | Expenses |
| **Card Color 6** | `#8B7355` (Walnut) | Contracts/Versions |

### Effects

| Field | Default | Description |
|-------|---------|-------------|
| **Glass Opacity** | `0.55` | Card translucency (0.0–1.0). Higher values are more opaque |
| **Blur Intensity (px)** | `18` | Backdrop blur radius behind glass cards |
| **Border Radius (px)** | `18` | Corner roundness across cards and panels |
| **Enable Animations** | `True` | Toggle entrance animations and hover transitions |

### Multiple Configurations

You can create multiple configuration records (e.g. for different companies, themes, or experiments). Only the record with **Active** checked is rendered. To switch themes, deactivate the current record and activate another.

## Architecture

### File Layout
```
hr_dashboard/
├── __manifest__.py
├── controllers/
│   └── main.py                          JSON-RPC endpoints for dashboard data
├── models/
│   └── dashboard_config.py              hr.dashboard.config model + data methods
├── views/
│   ├── dashboard_config_views.xml       Configuration form view
│   └── dashboard_menu.xml               Top-level app menu and submenu
├── data/
│   └── dashboard_config_data.xml        Default configuration record
├── security/
│   └── ir.model.access.csv              Access rights for hr.dashboard.config
├── i18n/
│   └── ar_001.po                        Arabic translation (158 strings)
└── static/
    ├── description/                     App icon and manifest banner
    ├── lib/
    │   └── chart.umd.min.js             Chart.js 4.4 bundled locally
    └── src/
        ├── scss/
        │   └── dashboard.scss           Theme variables, layout, RTL support
        └── components/
            ├── dashboard.js/xml         Main dashboard component
            ├── kpi_card.js/xml          KPI card with sparkline and tilt effect
            ├── chart_card.js/xml        Chart.js wrapper
            ├── employee_spotlight.js/xml  Employee profile section
            └── approvals_center.js/xml  Approval workflow section
```

### Data Flow
The dashboard component loads on app open and calls the JSON endpoint `/hr_dashboard/data` with the active date range. The endpoint returns a single payload containing all KPI counts, chart datasets, sparkline series, and module-availability flags. The component renders synchronously from this payload. User actions (approval, refresh, date change) call narrow endpoints that return only the affected slice and trigger a partial re-render.

### Defensive Patterns
All data fetching is wrapped in try/except blocks with structured logging. Per-feature checks (`'hr.appraisal' in self.env`, `_has_field`) detect optional modules at runtime, allowing the same module to install cleanly on databases with or without Payroll and Appraisal. Field name candidates are tried in order (e.g. `total_amount` → `total_amount_currency` → `untaxed_amount`) to accommodate minor variations across Odoo localizations.

## Internationalization

### Activating Arabic
1. Go to **Settings → Translations → Languages** and activate Arabic (Standard)
2. Upgrade the module to load translations:
   ```
   ./odoo-bin -u hr_dashboard
   ```
3. In your user preferences, set Language to Arabic and refresh

The dashboard renders in RTL with all 158 strings translated.

### Adding More Languages
Create a new file at `i18n/<language_code>.po` (for example `fr_FR.po` for French) using `ar_001.po` as a template. Fill in the `msgstr` values, then upgrade the module. Odoo auto-discovers and loads all `.po` files in the `i18n/` directory.

## Troubleshooting

**Dashboard loads but shows no data.** Confirm the date range covers a period with actual records. Use the developer console to check for failed RPC calls to `/hr_dashboard/data`.

**KPI shows 0 when records exist.** The metric counts records in specific workflow states (e.g. Pending Leaves counts `confirm` and `validate1` only). If all your leaves are already in `validate` state, "Pending Leaves" is correctly zero — check "Approved Leaves total" in the subtitle for the full picture.

**Approve button does nothing.** Check the browser console for an Odoo notification. The most common cause is a missing prerequisite (e.g. an Appraisal needs a Final Rating before it can be moved to Done — the module auto-assigns one when possible, but if no `hr.appraisal.note` records exist, you'll need to create one in **Appraisals → Configuration → Ratings**).

**Charts don't render.** Verify the `chart.umd.min.js` library was copied to `static/lib/` and the asset bundle was rebuilt. Hard refresh the browser (Ctrl+Shift+R) after a module upgrade.

**Arabic text doesn't appear.** Confirm the language is activated AND assigned to your user preferences AND the module has been upgraded (not just restarted) after activating the language.

## License

LGPL-3.0. See `LICENSE` for full text.

## Compatibility Notes

This module targets **Odoo 19.0 Enterprise exclusively**. It uses several Odoo 19-specific APIs that are not backward compatible:

- `hr.version` (replaces `hr.contract`, which was renamed in Odoo 19)
- `hr.expense` direct approval workflow (`hr.expense.sheet` was removed in Odoo 19)
- `hr.appraisal` state codes `1_new`/`2_pending`/`3_done` (renamed from `new`/`pending`/`done`)
- `hr.employee.sex` field (renamed from `gender`)
- `hr.payslip` states `draft`/`validated`/`paid` (renamed from `draft`/`verify`/`done`)
- OWL 3 component framework and the new `@web/core/network/rpc` module
- The mandatory `views` array in client-side `doAction` calls

The module will not install or run correctly on Odoo 17, 18, or earlier.
