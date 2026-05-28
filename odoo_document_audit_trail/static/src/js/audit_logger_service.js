/** @odoo-module **/
/**
 * Document Audit Trail - front-end logger service.
 *
 * Provides a single `auditLog` service that records front-end-only
 * document actions (download, preview, share, split, restore) by calling
 * the generic server method `documents.document.audit_log_js_operation`.
 *
 * It deliberately swallows errors: an audit failure must never break the
 * user's actual action.
 */
import { registry } from "@web/core/registry";

export const auditLogService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        async function log(documentIds, operationType, data = {}) {
            const ids = (documentIds || []).filter(Boolean);
            if (!ids.length) {
                return false;
            }
            try {
                return await orm.call(
                    "documents.document",
                    "audit_log_js_operation",
                    [ids, operationType, data]
                );
            } catch (error) {
                console.warn("[DocAudit] log failed:", operationType, error);
                return false;
            }
        }
        return { log };
    },
};

registry.category("services").add("documentAuditTrail", auditLogService);
