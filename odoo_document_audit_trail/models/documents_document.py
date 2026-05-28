# -*- coding: utf-8 -*-
import json
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# Front-end / JS operation types that may be created via RPC.
_JS_ALLOWED_OPERATIONS = {
    "download", "preview_open", "preview_close", "share",
    "split_source", "split_result", "replace", "restore_version",
    "lock", "unlock",
}


class DocumentsDocument(models.Model):
    _inherit = "documents.document"

    audit_log_ids = fields.One2many(
        "audit.trail.entry", "document_id", string="Audit Logs",
    )
    audit_log_count = fields.Integer(
        string="Audit Log Count", compute="_compute_audit_log_count",
    )

    # ==================================================================
    # Settings helpers
    # ==================================================================
    @api.model
    def _audit_enabled(self):
        """Master switch read from system parameters."""
        return self.env["ir.config_parameter"].sudo().get_param(
            "doc.audit.trail.enabled", "True"
        ) in ("True", "true", "1", True)

    @api.model
    def _audit_operation_enabled(self, operation_type):
        """Per-operation switch. Defaults to True when the param is absent."""
        if not self._audit_enabled():
            return False
        param = self.env["ir.config_parameter"].sudo().get_param(
            "doc.audit.trail.op.%s" % operation_type, "True"
        )
        return param in ("True", "true", "1", True)

    @api.model
    def _audit_trackable_fields(self):
        """Fields whose changes generate a 'write' audit entry."""
        candidate = [
            "name", "folder_id", "owner_id", "active", "tag_ids",
            "attachment_id", "lock_uid", "type", "url",
        ]
        return [f for f in candidate if f in self._fields]

    # ==================================================================
    # Low-level log writer
    # ==================================================================
    def _get_request_ip(self):
        try:
            from odoo.http import request
            if request and getattr(request, "httprequest", None):
                return request.httprequest.remote_addr
        except Exception:
            pass
        return None

    def _audit_doc_vals(self, record, operation_type,
                        old_values=None, new_values=None, notes=None,
                        extra=None):
        vals = {
            "document_id": record.id if record else False,
            "document_name": record.name if record else False,
            "folder_name": (record.folder_id.display_name
                            if record and record.folder_id else False),
            "operation_type": operation_type,
            "user_id": self.env.user.id,
            "operation_date": fields.Datetime.now(),
            "ip_address": self._get_request_ip(),
            "notes": notes,
        }
        if old_values:
            vals["old_values"] = json.dumps(old_values, default=str)
        if new_values:
            vals["new_values"] = json.dumps(new_values, default=str)
        if extra:
            vals.update(extra)
        return vals

    def _create_audit_log(self, operation_type, old_values=None,
                          new_values=None, notes=None, extra=None):
        """Create one log per record in self. Always runs with sudo so that
        a low-privilege user editing a shared document still produces a log.
        """
        if not self._audit_operation_enabled(operation_type):
            return
        log_vals = [
            self._audit_doc_vals(rec, operation_type, old_values,
                                 new_values, notes, extra)
            for rec in self
        ]
        if log_vals:
            self.env["audit.trail.entry"].sudo().create(log_vals)

    # ==================================================================
    # Value preparation for diffs
    # ==================================================================
    def _audit_read_field(self, record, field):
        val = getattr(record, field, False)
        if hasattr(val, "mapped") and hasattr(val, "_name"):
            # x2many / many2one recordset
            names = val.mapped("display_name") if val else []
            return ", ".join(names)
        return str(val)

    def _audit_snapshot(self, records, fields_list):
        return {
            rec.id: {f: self._audit_read_field(rec, f) for f in fields_list}
            for rec in records
        }

    # ==================================================================
    # ORM overrides
    # ==================================================================
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self._audit_operation_enabled("create"):
            is_split = self.env.context.get("audit_is_split", False)
            for rec in records:
                if is_split:
                    src = self.env.context.get("audit_split_source_name")
                    rec._create_audit_log(
                        "split_result",
                        new_values={"source_document_name": src},
                    )
                else:
                    snap = {f: self._audit_read_field(rec, f)
                            for f in self._audit_trackable_fields()}
                    rec._create_audit_log("create", new_values=snap)
        return records

    def write(self, vals):
        tracked = self._audit_trackable_fields()
        changed = [f for f in tracked if f in vals]

        # Detect specific operations before the write.
        is_archive = "active" in vals
        is_lock = "lock_uid" in vals

        old_snapshot = {}
        if changed and self._audit_enabled():
            old_snapshot = self._audit_snapshot(self, changed)

        res = super().write(vals)

        if not self._audit_enabled():
            return res

        new_snapshot = self._audit_snapshot(self, changed) if changed else {}

        for rec in self:
            # Archive / unarchive take precedence as a dedicated op.
            if is_archive:
                op = "unarchive" if rec.active else "archive"
                rec._create_audit_log(op)
            elif is_lock:
                op = "lock" if rec.lock_uid else "unlock"
                rec._create_audit_log(op)

            # Generic field diff (skip pure active/lock-only writes already logged)
            generic_changed = [f for f in changed
                               if f not in ("active", "lock_uid")]
            if generic_changed:
                rec._create_audit_log(
                    "write",
                    old_values={f: old_snapshot.get(rec.id, {}).get(f, "")
                                for f in generic_changed},
                    new_values={f: new_snapshot.get(rec.id, {}).get(f, "")
                                for f in generic_changed},
                )
        return res

    def unlink(self):
        snapshots = []
        if self._audit_operation_enabled("unlink"):
            for rec in self:
                snapshots.append(self._audit_doc_vals(
                    rec, "unlink",
                    old_values={f: self._audit_read_field(rec, f)
                                for f in self._audit_trackable_fields()},
                    notes=_("Document deleted"),
                ))
                # Detach the document_id since the document is going away.
                snapshots[-1]["document_id"] = False
        res = super().unlink()
        if snapshots:
            self.env["audit.trail.entry"].sudo().create(snapshots)
        return res

    # ==================================================================
    # JS-callable RPC entry points
    # ==================================================================
    @api.model
    def audit_log_js_operation(self, document_ids, operation_type, data=None):
        """Generic entry point called from the front-end.

        :param document_ids: list of documents.document ids
        :param operation_type: one of _JS_ALLOWED_OPERATIONS
        :param data: optional dict stored as new_values
        """
        if operation_type not in _JS_ALLOWED_OPERATIONS:
            _logger.warning("Audit: rejected JS operation '%s'", operation_type)
            return False
        if not self._audit_operation_enabled(operation_type):
            return False
        docs = self.browse([d for d in (document_ids or []) if d]).exists()
        if not docs:
            return False
        docs._create_audit_log(
            operation_type,
            new_values=data or None,
        )
        return True

    # ==================================================================
    # Computes / actions
    # ==================================================================
    @api.depends("audit_log_ids")
    def _compute_audit_log_count(self):
        groups = self.env["audit.trail.entry"]._read_group(
            [("document_id", "in", self.ids)],
            groupby=["document_id"], aggregates=["__count"],
        )
        mapping = {doc.id: count for doc, count in groups}
        for rec in self:
            rec.audit_log_count = mapping.get(rec.id, 0)

    def action_view_audit_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Audit Trail"),
            "res_model": "audit.trail.entry",
            "view_mode": "list,form",
            "domain": [("document_id", "=", self.id)],
            "context": {"create": False},
            "target": "current",
        }
