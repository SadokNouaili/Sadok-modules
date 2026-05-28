# -*- coding: utf-8 -*-
from odoo import api, fields, models

# Operations exposed individually in Settings.
AUDIT_OPERATIONS = [
    ("create", "Created"),
    ("write", "Updated"),
    ("unlink", "Deleted"),
    ("archive", "Archived / Restored"),
    ("lock", "Locked / Unlocked"),
    ("download", "Downloaded"),
    ("preview_open", "Preview"),
    ("share", "Shared"),
    ("split_source", "Split"),
    ("replace", "Replaced"),
    ("sign_request", "Signature events"),
]


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    document_audit_enabled = fields.Boolean(
        string="Enable Document Audit Trail",
        config_parameter="doc.audit.trail.enabled", default=True,
    )
    document_audit_retention_days = fields.Integer(
        string="Log Retention (days)",
        config_parameter="doc.audit.trail.retention_days", default=0,
        help="Logs older than this are removed by the daily cron. "
             "0 disables automatic cleanup.",
    )

    # --- per-operation toggles -------------------------------------------
    audit_op_create = fields.Boolean(
        "Track Creation", config_parameter="doc.audit.trail.op.create", default=True)
    audit_op_write = fields.Boolean(
        "Track Updates", config_parameter="doc.audit.trail.op.write", default=True)
    audit_op_unlink = fields.Boolean(
        "Track Deletions", config_parameter="doc.audit.trail.op.unlink", default=True)
    audit_op_archive = fields.Boolean(
        "Track Archive/Restore", config_parameter="doc.audit.trail.op.archive", default=True)
    audit_op_unarchive = fields.Boolean(
        "Track Restore", config_parameter="doc.audit.trail.op.unarchive", default=True)
    audit_op_lock = fields.Boolean(
        "Track Lock", config_parameter="doc.audit.trail.op.lock", default=True)
    audit_op_unlock = fields.Boolean(
        "Track Unlock", config_parameter="doc.audit.trail.op.unlock", default=True)
    audit_op_download = fields.Boolean(
        "Track Downloads", config_parameter="doc.audit.trail.op.download", default=True)
    audit_op_preview_open = fields.Boolean(
        "Track Preview Open", config_parameter="doc.audit.trail.op.preview_open", default=True)
    audit_op_preview_close = fields.Boolean(
        "Track Preview Close", config_parameter="doc.audit.trail.op.preview_close", default=True)
    audit_op_share = fields.Boolean(
        "Track Sharing", config_parameter="doc.audit.trail.op.share", default=True)
    audit_op_split_source = fields.Boolean(
        "Track Split", config_parameter="doc.audit.trail.op.split_source", default=True)
    audit_op_split_result = fields.Boolean(
        "Track Split Results", config_parameter="doc.audit.trail.op.split_result", default=True)
    audit_op_replace = fields.Boolean(
        "Track Replace", config_parameter="doc.audit.trail.op.replace", default=True)
    audit_op_restore_version = fields.Boolean(
        "Track Version Restore", config_parameter="doc.audit.trail.op.restore_version", default=True)
    audit_op_sign_request = fields.Boolean(
        "Track Signature Requested", config_parameter="doc.audit.trail.op.sign_request", default=True)
    audit_op_sign_completed = fields.Boolean(
        "Track Signature Completed", config_parameter="doc.audit.trail.op.sign_completed", default=True)
    audit_op_sign_item_added = fields.Boolean(
        "Track Field Added", config_parameter="doc.audit.trail.op.sign_item_added", default=True)
    audit_op_sign_item_removed = fields.Boolean(
        "Track Field Removed", config_parameter="doc.audit.trail.op.sign_item_removed", default=True)
    audit_op_sign_item_signed = fields.Boolean(
        "Track Field Signed", config_parameter="doc.audit.trail.op.sign_item_signed", default=True)
