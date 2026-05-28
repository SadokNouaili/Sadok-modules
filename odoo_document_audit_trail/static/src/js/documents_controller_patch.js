/** @odoo-module **/
/**
 * Document Audit Trail - Documents controller patch.
 *
 * Intercepts front-end-only actions on documents (download, preview,
 * share, split) and records them through the audit logger service.
 *
 * DESIGN NOTE
 * -----------
 * Odoo's Documents OWL controllers expose action handlers whose exact
 * names can change between point releases. To stay resilient we:
 *   1. only wrap a method if it actually exists on the prototype, and
 *   2. always call the original first, then log (never block the action).
 *
 * If Odoo renames an internal handler, auditing for that one action simply
 * stops silently instead of throwing - the rest keeps working, and the
 * server-side ORM hooks (create/write/archive/delete/lock) are unaffected.
 */
import { patch } from "@web/core/utils/patch";
import { DocumentsListController } from "@documents/views/list/documents_list_controller";
import { DocumentsKanbanController } from "@documents/views/kanban/documents_kanban_controller";

// Map a controller handler name -> audit operation type.
// These are the common Odoo 19 Documents action handlers. Unknown ones are
// skipped automatically by `wrapIfExists`.
const HANDLER_MAP = {
    onClickDownload: "download",
    download: "download",
    downloadSelectedDocuments: "download",
    onClickShare: "share",
    createShare: "share",
    onClickPreview: "preview_open",
    openPreview: "preview_open",
    onClickSplitPDF: "split_source",
    splitPDF: "split_source",
    onClickToggleLock: "lock",
    toggleLock: "lock",
};

function selectedIds(ctrl) {
    try {
        const records =
            ctrl.model?.root?.selection?.length
                ? ctrl.model.root.selection
                : ctrl.model?.root?.records || [];
        return records.map((r) => r.resId).filter(Boolean);
    } catch (e) {
        return [];
    }
}

function buildPatch(ControllerClass) {
    const proto = ControllerClass.prototype;
    const overrides = {};

    for (const [handler, operation] of Object.entries(HANDLER_MAP)) {
        if (typeof proto[handler] !== "function") {
            continue; // method not present in this version: skip silently
        }
        // Capture the ORIGINAL reference now, before patch() mutates proto,
        // otherwise calling it inside the override would recurse forever.
        const original = proto[handler];
        overrides[handler] = function (...args) {
            const ids = selectedIds(this);
            const result = original.apply(this, args);
            // Log after the original handler runs. Fire-and-forget.
            const auditSvc = this.env?.services?.documentAuditTrail;
            if (auditSvc && ids.length) {
                Promise.resolve(result).finally(() => {
                    auditSvc.log(ids, operation, {});
                });
            }
            return result;
        };
    }
    return overrides;
}

patch(DocumentsListController.prototype, buildPatch(DocumentsListController));
patch(DocumentsKanbanController.prototype, buildPatch(DocumentsKanbanController));
