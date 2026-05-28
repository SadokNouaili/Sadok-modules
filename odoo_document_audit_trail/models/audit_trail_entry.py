# -*- coding: utf-8 -*-
import json
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class AuditTrailEntry(models.Model):
    _name = "audit.trail.entry"
    _description = "Document Audit Trail Entry"
    _order = "operation_date desc, id desc"
    _rec_name = "display_name"

    # ------------------------------------------------------------------
    # Core fields
    # ------------------------------------------------------------------
    document_id = fields.Many2one(
        "documents.document", string="Document",
        ondelete="set null", index=True,
    )
    # Stored separately so the log survives deletion of the document.
    document_name = fields.Char(string="Document Name", readonly=True)
    folder_name = fields.Char(string="Workspace / Folder", readonly=True)

    # Persistent per-document trail. Every entry for the same document is
    # linked to the same trail, so the full history stays connected even
    # after the document itself is deleted (trail keeps a stored name key).
    trail_id = fields.Many2one(
        "audit.trail", string="Document Trail",
        ondelete="set null", index=True,
    )

    operation_type = fields.Selection(
        selection="_selection_operation_type",
        string="Operation", required=True, readonly=True, index=True,
    )
    user_id = fields.Many2one(
        "res.users", string="User", required=True, readonly=True, index=True,
        default=lambda self: self.env.user,
    )
    operation_date = fields.Datetime(
        string="Date", required=True, readonly=True, index=True,
        default=fields.Datetime.now,
    )
    ip_address = fields.Char(string="IP Address", readonly=True)

    old_values = fields.Text(string="Old Values", readonly=True)
    new_values = fields.Text(string="New Values", readonly=True)
    field_changes = fields.Text(
        string="Changes", readonly=True,
        compute="_compute_field_changes", store=True,
    )
    notes = fields.Text(string="Notes", readonly=True)

    display_name = fields.Char(
        string="Summary", compute="_compute_display_name_field", store=True,
    )

    # ------------------------------------------------------------------
    # Signature-related (only meaningful when the `sign` app is installed)
    # ------------------------------------------------------------------
    sign_request_id = fields.Many2one(
        "sign.request", string="Sign Request",
        readonly=True, ondelete="set null",
    )
    signer_id = fields.Many2one(
        "res.partner", string="Signer", readonly=True, ondelete="set null",
    )
    sign_item_id = fields.Many2one(
        "sign.item", string="Signature Field",
        readonly=True, ondelete="set null",
    )
    sign_item_type = fields.Char(
        string="Field Type", readonly=True,
        help="Type of the signature field: signature, initials, text, "
             "date, checkbox, etc.",
    )
    sign_item_value = fields.Text(
        string="Field Value", readonly=True,
        help="The value entered/signed in this field.",
    )

    # ------------------------------------------------------------------
    # Follow-up / review workflow (admin)
    # ------------------------------------------------------------------
    followup_state = fields.Selection(
        [
            ("none", "Not Flagged"),
            ("open", "Needs Review"),
            ("in_progress", "In Progress"),
            ("resolved", "Resolved"),
        ],
        string="Follow-up", default="none", index=True,
    )
    assigned_user_id = fields.Many2one(
        "res.users", string="Assigned To",
    )
    review_note = fields.Text(string="Review Note")

    # ------------------------------------------------------------------
    # Auto-link to a per-document trail
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        Trail = self.env["audit.trail"].sudo()
        for vals in vals_list:
            if vals.get("trail_id"):
                continue
            trail = self.browse()
            doc_id = vals.get("document_id")
            if doc_id:
                doc = self.env["documents.document"].sudo().browse(doc_id)
                if doc.exists():
                    trail = Trail._get_or_create_for_document(doc)
            if not trail:
                trail = Trail._get_or_create_for_name(
                    vals.get("document_name"))
            if trail:
                vals["trail_id"] = trail.id
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Selection / helpers
    # ------------------------------------------------------------------
    @api.model
    def _selection_operation_type(self):
        return [
            ("create", _("Created")),
            ("write", _("Updated")),
            ("unlink", _("Deleted")),
            ("archive", _("Archived")),
            ("unarchive", _("Restored")),
            ("lock", _("Locked")),
            ("unlock", _("Unlocked")),
            ("download", _("Downloaded")),
            ("preview_open", _("Preview Opened")),
            ("preview_close", _("Preview Closed")),
            ("share", _("Shared")),
            ("split_source", _("Split - Source")),
            ("split_result", _("Split - Result")),
            ("replace", _("Replaced (New Version)")),
            ("restore_version", _("Version Restored")),
            ("sign_request", _("Signature Requested")),
            ("sign_completed", _("Signature Completed")),
            ("sign_item_added", _("Signature Field Added")),
            ("sign_item_removed", _("Signature Field Removed")),
            ("sign_item_signed", _("Field Signed")),
        ]

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("operation_type", "old_values", "new_values", "signer_id",
                 "sign_item_type", "sign_item_value")
    def _compute_field_changes(self):
        simple = {
            "create": _("Document created"),
            "unlink": _("Document deleted"),
            "archive": _("Document archived"),
            "unarchive": _("Document restored"),
            "lock": _("Document locked"),
            "unlock": _("Document unlocked"),
            "download": _("Document downloaded"),
            "preview_open": _("Preview opened"),
            "preview_close": _("Preview closed"),
            "share": _("Document shared"),
            "replace": _("Document replaced with a new version"),
            "restore_version": _("A previous version was restored"),
            "sign_request": _("Signature requested"),
            "sign_completed": _("All signatures completed"),
        }
        for rec in self:
            op = rec.operation_type
            if op in simple:
                rec.field_changes = simple[op]
            elif op == "sign_item_added":
                ftype = rec.sign_item_type or _("field")
                rec.field_changes = _("Added '%s' field to the document") % ftype
            elif op == "sign_item_removed":
                ftype = rec.sign_item_type or _("field")
                rec.field_changes = _("Removed '%s' field from the document") % ftype
            elif op == "sign_item_signed":
                signer = rec.signer_id.name or _("Unknown")
                ftype = rec.sign_item_type or _("field")
                val = rec.sign_item_value
                if val:
                    rec.field_changes = _("'%(type)s' filled by %(who)s: %(val)s") % {
                        "type": ftype, "who": signer, "val": val,
                    }
                else:
                    rec.field_changes = _("'%(type)s' field signed by %(who)s") % {
                        "type": ftype, "who": signer,
                    }
            elif op == "split_source":
                rec.field_changes = rec._split_source_label()
            elif op == "split_result":
                rec.field_changes = rec._split_result_label()
            elif op == "write":
                rec.field_changes = rec._diff_label()
            else:
                rec.field_changes = ""

    def _split_source_label(self):
        self.ensure_one()
        try:
            data = json.loads(self.new_values or "{}")
            count = data.get("new_document_count", 0)
            return _("Document split into %s new document(s)") % count
        except Exception:
            return _("Document split")

    def _split_result_label(self):
        self.ensure_one()
        try:
            data = json.loads(self.new_values or "{}")
            src = data.get("source_document_name", _("Unknown"))
            return _("Created from split of: %s") % src
        except Exception:
            return _("Created from a split")

    def _diff_label(self):
        self.ensure_one()
        try:
            old = json.loads(self.old_values or "{}")
            new = json.loads(self.new_values or "{}")
        except Exception:
            return _("Unable to parse changes")
        changes = []
        for field, new_val in new.items():
            old_val = old.get(field, "")
            if old_val != new_val:
                changes.append("%s: '%s' \u2192 '%s'" % (field, old_val, new_val))
        return "\n".join(changes) if changes else _("No tracked changes")

    @api.depends("operation_type", "document_name", "user_id", "operation_date")
    def _compute_display_name_field(self):
        labels = dict(self._fields["operation_type"]._description_selection(self.env))
        for rec in self:
            op_label = labels.get(rec.operation_type, rec.operation_type or "")
            doc = rec.document_name or _("(deleted)")
            rec.display_name = "%s - %s" % (op_label, doc)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
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

    def action_view_sign_request(self):
        self.ensure_one()
        if not self.sign_request_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Sign Request"),
            "res_model": "sign.request",
            "view_mode": "form",
            "res_id": self.sign_request_id.id,
            "target": "current",
        }

    def action_view_trail(self):
        """Open the full timeline of every action on this document's trail."""
        self.ensure_one()
        if self.trail_id:
            return self.trail_id.action_open_timeline()
        # Fallback: filter by document if no trail (e.g. legacy entries).
        domain = ([("document_id", "=", self.document_id.id)]
                  if self.document_id
                  else [("document_name", "=", self.document_name)])
        return {
            "type": "ir.actions.act_window",
            "name": _("Document Timeline"),
            "res_model": "audit.trail.entry",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"create": False},
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Follow-up workflow
    # ------------------------------------------------------------------
    def action_flag_review(self):
        self.write({"followup_state": "open"})

    def action_assign_me(self):
        self.write({
            "followup_state": "in_progress",
            "assigned_user_id": self.env.user.id,
        })

    def action_resolve(self):
        self.write({"followup_state": "resolved"})

    def action_reset_followup(self):
        self.write({
            "followup_state": "none",
            "assigned_user_id": False,
        })

    # ------------------------------------------------------------------
    # Dashboard data (consumed by the OWL client action)
    # ------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self, days=30):
        """Aggregate stats for the custom dashboard.

        Returns a dict with KPIs, per-operation counts, per-day activity,
        top users, top documents and the latest activity feed.
        """
        from datetime import datetime, timedelta

        now = fields.Datetime.now()
        since = now - timedelta(days=days or 30)
        domain = [("operation_date", ">=", since)]

        labels = dict(self._fields["operation_type"]._description_selection(self.env))

        total = self.search_count(domain)
        total_all_time = self.search_count([])

        # --- KPIs ----------------------------------------------------------
        deletions = self.search_count(domain + [("operation_type", "=", "unlink")])
        signatures = self.search_count(domain + [
            ("operation_type", "in", (
                "sign_request", "sign_completed", "sign_item_added",
                "sign_item_removed", "sign_item_signed"))])
        open_followups = self.search_count([
            ("followup_state", "in", ("open", "in_progress"))])

        # --- By operation --------------------------------------------------
        by_op = []
        for op, count in self._read_group(
                domain, groupby=["operation_type"], aggregates=["__count"]):
            by_op.append({
                "key": op,
                "label": labels.get(op, op or ""),
                "count": count,
            })
        by_op.sort(key=lambda r: r["count"], reverse=True)

        # --- Activity per day ---------------------------------------------
        by_day = []
        for day, count in self._read_group(
                domain, groupby=["operation_date:day"],
                aggregates=["__count"], order="operation_date:day asc"):
            by_day.append({
                "label": day.strftime("%Y-%m-%d") if day else "",
                "count": count,
            })

        # --- Top users -----------------------------------------------------
        top_users = []
        for user, count in self._read_group(
                domain, groupby=["user_id"], aggregates=["__count"],
                order="__count desc", limit=8):
            if user:
                top_users.append({"name": user.name, "count": count})
        active_users = len(self._read_group(
            domain, groupby=["user_id"], aggregates=["__count"]))

        # --- Top documents (by trail) -------------------------------------
        top_docs = []
        for trail, count in self._read_group(
                domain, groupby=["trail_id"], aggregates=["__count"],
                order="__count desc", limit=8):
            if trail:
                top_docs.append({
                    "id": trail.id, "name": trail.name, "count": count,
                })

        # --- Recent feed ---------------------------------------------------
        recent = []
        for rec in self.search(domain, limit=12, order="operation_date desc"):
            recent.append({
                "id": rec.id,
                "operation": rec.operation_type,
                "operation_label": labels.get(rec.operation_type,
                                              rec.operation_type),
                "document": rec.document_name or _("(deleted)"),
                "user": rec.user_id.name,
                "date": rec.operation_date and
                        fields.Datetime.to_string(rec.operation_date),
                "summary": rec.field_changes or "",
                "followup": rec.followup_state,
            })

        return {
            "days": days,
            "kpis": {
                "total": total,
                "total_all_time": total_all_time,
                "deletions": deletions,
                "signatures": signatures,
                "open_followups": open_followups,
                "active_users": active_users,
            },
            "by_operation": by_op,
            "by_day": by_day,
            "top_users": top_users,
            "top_documents": top_docs,
            "recent": recent,
        }

    @api.model
    def action_open_filtered(self, operation_type=None, followup=False):
        """Helper for dashboard cards to drill into the list view."""
        domain = []
        if operation_type:
            domain.append(("operation_type", "=", operation_type))
        if followup:
            domain.append(("followup_state", "in", ("open", "in_progress")))
        return {
            "type": "ir.actions.act_window",
            "name": _("Audit Trail"),
            "res_model": "audit.trail.entry",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"create": False},
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Cron - retention
    # ------------------------------------------------------------------
    @api.model
    def _cron_delete_old_audit_logs(self):
        """Delete logs older than the configured retention window.

        ``doc.audit.trail.retention_days`` <= 0 disables cleanup.
        """
        from datetime import datetime, timedelta

        param = self.env["ir.config_parameter"].sudo()
        retention_days = int(param.get_param("doc.audit.trail.retention_days", "0") or 0)
        if retention_days <= 0:
            return True

        limit_date = datetime.now() - timedelta(days=retention_days)
        old_logs = self.sudo().search([("operation_date", "<", limit_date)])
        count = len(old_logs)
        if count:
            old_logs.unlink()
            _logger.info("Document Audit Trail: %s old log(s) deleted "
                         "(older than %s days)", count, retention_days)
        return True
