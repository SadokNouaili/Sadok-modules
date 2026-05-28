# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class AuditTrail(models.Model):
    """A persistent per-document trail.

    One trail exists per documents.document (keyed by document_id, with a
    stored name fallback). Every audit.trail.entry for that document points
    to the same trail, so the complete action history stays linked together
    across time even after the underlying document is deleted.
    """
    _name = "audit.trail"
    _description = "Document Audit Trail"
    _order = "last_activity desc, id desc"

    name = fields.Char(string="Document", required=True, index=True)
    document_id = fields.Many2one(
        "documents.document", string="Current Document",
        ondelete="set null", index=True,
    )
    document_active = fields.Boolean(
        string="Document Exists", compute="_compute_document_active",
    )
    entry_ids = fields.One2many(
        "audit.trail.entry", "trail_id", string="Actions",
    )
    entry_count = fields.Integer(
        string="Action Count", compute="_compute_stats", store=True,
    )
    first_activity = fields.Datetime(
        string="First Action", compute="_compute_stats", store=True,
    )
    last_activity = fields.Datetime(
        string="Last Action", compute="_compute_stats", store=True, index=True,
    )
    last_operation = fields.Char(
        string="Latest Operation", compute="_compute_stats", store=True,
    )
    open_followups = fields.Integer(
        string="Open Follow-ups", compute="_compute_stats", store=True,
    )

    @api.depends("entry_ids", "entry_ids.operation_date",
                 "entry_ids.followup_state", "entry_ids.display_name")
    def _compute_stats(self):
        for trail in self:
            entries = trail.entry_ids.sorted("operation_date")
            trail.entry_count = len(entries)
            trail.first_activity = entries[:1].operation_date or False
            last = entries[-1:] if entries else entries
            trail.last_activity = last.operation_date or False
            trail.last_operation = last.display_name or False
            trail.open_followups = len(entries.filtered(
                lambda e: e.followup_state in ("open", "in_progress")
            ))

    def _compute_document_active(self):
        for trail in self:
            trail.document_active = bool(
                trail.document_id and trail.document_id.exists()
            )

    # ------------------------------------------------------------------
    # Trail resolution: get-or-create one trail per document
    # ------------------------------------------------------------------
    @api.model
    def _get_or_create_for_document(self, document):
        """Return the trail for a documents.document, creating it if needed."""
        if not document:
            return self.browse()
        trail = self.sudo().search([("document_id", "=", document.id)], limit=1)
        if not trail:
            trail = self.sudo().create({
                "name": document.name or _("Untitled"),
                "document_id": document.id,
            })
        elif document.name and trail.name != document.name:
            trail.sudo().write({"name": document.name})
        return trail

    @api.model
    def _get_or_create_for_name(self, name):
        """Trail resolution for entries with no live document (e.g. sign
        requests that can't be mapped, or deletions)."""
        if not name:
            return self.browse()
        trail = self.sudo().search(
            [("name", "=", name), ("document_id", "=", False)], limit=1)
        if not trail:
            trail = self.sudo().create({"name": name})
        return trail

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_open_timeline(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Timeline: %s") % self.name,
            "res_model": "audit.trail.entry",
            "view_mode": "list,form",
            "domain": [("trail_id", "=", self.id)],
            "context": {"create": False, "search_default_group_op": 0},
            "target": "current",
        }

    def action_view_document(self):
        self.ensure_one()
        if not self.document_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Document"),
            "res_model": "documents.document",
            "view_mode": "form",
            "res_id": self.document_id.id,
            "target": "current",
        }
