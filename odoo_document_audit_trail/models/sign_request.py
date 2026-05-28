# -*- coding: utf-8 -*-
"""Signature-related audit hooks.

Captures detailed, field-level signature activity:
* sign_request      - a signature is requested for a document
* sign_completed    - all signatures on a request are done
* sign_item_added   - a field (signature / text / date / checkbox ...) is
                      placed on the document in the editor
* sign_item_removed - a field is removed from the document
* sign_item_signed  - a field is actually filled/signed, with its value

Everything is written defensively (getattr / hasattr) so that small
differences in the Sign data model between Odoo point releases degrade
gracefully instead of raising.
"""
import logging

from odoo import api, models, _

_logger = logging.getLogger(__name__)


def _resolve_document(env, sign_request):
    """Best-effort mapping from a sign.request back to a documents.document."""
    Doc = env["documents.document"].sudo()
    attachment_ids = []
    for fname in ("completed_document_attachment_ids",
                  "completed_document", "attachment_ids"):
        val = getattr(sign_request, fname, None)
        if val is not None and hasattr(val, "ids"):
            attachment_ids += val.ids
    template = getattr(sign_request, "template_id", None)
    if template is not None and getattr(template, "attachment_id", False):
        attachment_ids.append(template.attachment_id.id)
    if not attachment_ids:
        return Doc.browse()
    return Doc.search([("attachment_id", "in", attachment_ids)], limit=1)


def _item_type_label(sign_item):
    """Human label for a sign.item's field type ('Signature', 'Text', ...)."""
    try:
        type_rec = getattr(sign_item, "type_id", False)
        if type_rec:
            return (getattr(type_rec, "name", False)
                    or getattr(type_rec, "item_type", False)
                    or _("Field"))
    except Exception:
        pass
    return _("Field")


class SignRequest(models.Model):
    _inherit = "sign.request"

    def _audit_log_sign(self, operation_type, signer=None,
                        sign_item=None, value=None):
        Doc = self.env["documents.document"].sudo()
        if not Doc._audit_operation_enabled(operation_type):
            return
        Log = self.env["audit.trail.entry"].sudo()
        for req in self:
            doc = _resolve_document(self.env, req)
            ref = (getattr(req, "reference", False)
                   or req.display_name or _("Signature Request"))
            Log.create({
                "document_id": doc.id if doc else False,
                "document_name": doc.name if doc else ref,
                "folder_name": (doc.folder_id.display_name
                                if doc and doc.folder_id else False),
                "operation_type": operation_type,
                "user_id": self.env.user.id,
                "sign_request_id": req.id,
                "signer_id": signer.id if signer else False,
                "sign_item_id": sign_item.id if sign_item else False,
                "sign_item_type": (_item_type_label(sign_item)
                                   if sign_item else False),
                "sign_item_value": value,
            })

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        requests._audit_log_sign("sign_request")
        return requests

    def write(self, vals):
        done_states = ("signed", "done", "completed")
        was_done = {req.id: (req.state in done_states) for req in self}
        res = super().write(vals)
        if "state" in vals:
            newly_done = self.filtered(
                lambda r: r.state in done_states and not was_done.get(r.id)
            )
            newly_done._audit_log_sign("sign_completed")
        return res


def _request_for_item(sign_item):
    """Find a sign.request linked to a sign.item via its template."""
    template = getattr(sign_item, "template_id", False)
    if not template:
        return sign_item.env["sign.request"].browse()
    reqs = getattr(template, "sign_request_ids", False)
    return reqs[:1] if reqs else sign_item.env["sign.request"].browse()


class SignItem(models.Model):
    _inherit = "sign.item"

    @api.model_create_multi
    def create(self, vals_list):
        items = super().create(vals_list)
        Doc = self.env["documents.document"].sudo()
        if Doc._audit_operation_enabled("sign_item_added"):
            for item in items:
                req = _request_for_item(item)
                if req:
                    req._audit_log_sign("sign_item_added", sign_item=item)
        return items

    def unlink(self):
        Doc = self.env["documents.document"].sudo()
        if Doc._audit_operation_enabled("sign_item_removed"):
            for item in self:
                req = _request_for_item(item)
                if req:
                    req._audit_log_sign("sign_item_removed", sign_item=item)
        return super().unlink()


class SignRequestItem(models.Model):
    _inherit = "sign.request.item"

    def write(self, vals):
        was_signed = {it.id: it.state == "completed" for it in self}
        res = super().write(vals)
        Doc = self.env["documents.document"].sudo()
        if not Doc._audit_operation_enabled("sign_item_signed"):
            return res
        for it in self:
            if it.state == "completed" and not was_signed.get(it.id):
                self._audit_log_signed_values(it)
        return res

    def _audit_log_signed_values(self, request_item):
        """Emit one audit record per field filled by this signer."""
        request = request_item.sign_request_id
        signer = request_item.partner_id
        values = getattr(request_item, "sign_item_value_ids", False)
        if values:
            for val in values:
                sign_item = getattr(val, "sign_item_id", False)
                raw = getattr(val, "value", False)
                request._audit_log_sign(
                    "sign_item_signed",
                    signer=signer,
                    sign_item=sign_item or None,
                    value=self._format_value(sign_item, raw),
                )
        else:
            request._audit_log_sign("sign_item_signed", signer=signer)

    def _format_value(self, sign_item, raw):
        """Truncate / redact value for storage. Signature images are binary,
        so we store a placeholder instead of the raw data."""
        if not raw:
            return False
        type_label = _item_type_label(sign_item) if sign_item else ""
        if isinstance(type_label, str) and "sign" in type_label.lower():
            return _("[signature drawn]")
        text = str(raw)
        return text[:500] + "\u2026" if len(text) > 500 else text
