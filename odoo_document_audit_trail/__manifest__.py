# -*- coding: utf-8 -*-
{
    "name": "Document Audit Trail",
    "version": "19.0.1.0.0",
    "category": "Document Management",
    "summary": "Audit log & dashboard for Odoo Documents: track create, edit, "
               "archive, delete, lock, download, share, split, replace and "
               "every e-signature field event \u2014 with follow-up workflow.",
    "description": """
Document Audit Trail
====================
A complete, standalone audit-logging solution for Odoo 19 Enterprise
*Documents*. Records every standard action performed on any document, links
all actions of a document into one timeline, and ships with an animated
analytics dashboard plus an admin follow-up workflow.

What it tracks
--------------
* Server-side: create, update (field-level diff), archive / unarchive,
  delete, lock / unlock, replace (new version), restore from history.
* Front-end: download, preview, share, split.
* E-signature: signature requested, signature completed, signature field
  added / removed, and each field signed (with field type and value).

Highlights
----------
* Animated OWL dashboard (KPIs, charts, top users/documents, live feed).
* Per-document trail that links every action together across time, and
  survives document deletion.
* Admin follow-up workflow: flag, assign, resolve, with review notes.
* Per-operation on/off switches and log retention in Settings.
* No dependency on any custom module.
    """,
    "author": "Msn",
    "maintainer": "Msn",
    "support": "msnsupport0@gmail.com",
    "website": "",
    "license": "OPL-1",
    "price": 150.00,
    "currency": "USD",
    "category": "Document Management",
    "depends": ["base", "web", "documents", "sign"],
    "data": [
        "security/document_audit_security.xml",
        "security/ir.model.access.csv",
        "data/ir_config_parameter_data.xml",
        "data/ir_cron_data.xml",
        "views/audit_trail_entry_views.xml",
        "views/audit_trail_views.xml",
        "views/dashboard_action.xml",
        "views/res_config_settings_views.xml",
        "views/documents_document_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "odoo_document_audit_trail/static/src/js/audit_logger_service.js",
            "odoo_document_audit_trail/static/src/js/documents_controller_patch.js",
            "odoo_document_audit_trail/static/src/js/audit_dashboard.js",
            "odoo_document_audit_trail/static/src/xml/audit_dashboard.xml",
            "odoo_document_audit_trail/static/src/css/audit_trail.css",
            "odoo_document_audit_trail/static/src/css/audit_dashboard.css",
        ],
    },
    "images": ["static/description/banner.gif"],
    "application": True,
    "installable": True,
    "auto_install": False,
}
