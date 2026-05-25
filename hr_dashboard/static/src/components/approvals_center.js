/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class ApprovalsCenter extends Component {
    static template = "hr_dashboard.ApprovalsCenter";
    static props = {
        onApproved: { type: Function, optional: true },
    };

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: false,
            data: {
                leaves: [],
                expense_sheets: [],
                appraisals: [],
                has_leave_module: true,
                has_expense_module: true,
                has_appraisal_module: true,
            },
            tab: "leaves",          // 'leaves' | 'expenses' | 'appraisals'
            processingId: null,
        });

        onWillStart(async () => {
            await this._loadApprovals();
        });
    }

    async _loadApprovals() {
        this.state.loading = true;
        try {
            this.state.data = await rpc("/hr_dashboard/pending_approvals", { limit: 20 });
        } catch (e) {
            console.error("approvals fetch failed", e);
            this.notification.add(_t("Could not load pending approvals"), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    onSwitchTab(tab) {
        this.state.tab = tab;
    }

    async onApproveLeave(leaveId) {
        this.state.processingId = `leave-${leaveId}`;
        try {
            const result = await rpc("/hr_dashboard/approve_leave", { leave_id: leaveId });
            this._handleResult(result, "approved");
        } catch (e) {
            console.error(e);
            this.notification.add(_t("Approval failed"), { type: "danger" });
        } finally {
            this.state.processingId = null;
        }
    }

    async onRefuseLeave(leaveId) {
        this.state.processingId = `leave-${leaveId}`;
        try {
            const result = await rpc("/hr_dashboard/refuse_leave", { leave_id: leaveId });
            this._handleResult(result, "refused");
        } catch (e) {
            console.error(e);
            this.notification.add(_t("Refusal failed"), { type: "danger" });
        } finally {
            this.state.processingId = null;
        }
    }

    async onApproveExpense(sheetId) {
        this.state.processingId = `expense-${sheetId}`;
        try {
            const result = await rpc("/hr_dashboard/approve_expense_sheet", { sheet_id: sheetId });
            this._handleResult(result, "approved");
        } catch (e) {
            console.error(e);
            this.notification.add(_t("Approval failed"), { type: "danger" });
        } finally {
            this.state.processingId = null;
        }
    }

    async onRefuseExpense(sheetId) {
        this.state.processingId = `expense-${sheetId}`;
        try {
            const result = await rpc("/hr_dashboard/refuse_expense_sheet", {
                sheet_id: sheetId,
                reason: "Refused from dashboard",
            });
            this._handleResult(result, "refused");
        } catch (e) {
            console.error(e);
            this.notification.add(_t("Refusal failed"), { type: "danger" });
        } finally {
            this.state.processingId = null;
        }
    }

    async _handleResult(result, verb) {
        if (result && result.ok) {
            this.notification.add(result.message || _t(`Request ${verb}`), { type: "success" });
            await this._loadApprovals();
            if (this.props.onApproved) {
                this.props.onApproved();
            }
        } else {
            this.notification.add(
                (result && result.error) || _t("Operation failed"),
                { type: "danger" }
            );
        }
    }

    openLeave(leaveId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.leave",
            res_id: leaveId,
            views: [[false, "form"]],
            view_mode: "form",
            context: { create: false, delete: false, duplicate: false },
            target: "current",
        });
    }

    openExpenseSheet(sheetId) {
        // Odoo 19: hr.expense.sheet removed, use hr.expense directly
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.expense",
            res_id: sheetId,
            views: [[false, "form"]],
            view_mode: "form",
            context: { create: false, delete: false, duplicate: false },
            target: "current",
        });
    }

    openAppraisal(appraisalId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.appraisal",
            res_id: appraisalId,
            views: [[false, "form"]],
            view_mode: "form",
            context: { create: false, delete: false, duplicate: false },
            target: "current",
        });
    }

    async onApproveAppraisal(appraisalId) {
        this.state.processingId = `appraisal-${appraisalId}`;
        try {
            const result = await rpc("/hr_dashboard/approve_appraisal", { appraisal_id: appraisalId });
            this._handleResult(result, "completed");
        } catch (e) {
            console.error(e);
            this.notification.add(_t("Approval failed"), { type: "danger" });
        } finally {
            this.state.processingId = null;
        }
    }

    async onCancelAppraisal(appraisalId) {
        this.state.processingId = `appraisal-${appraisalId}`;
        try {
            const result = await rpc("/hr_dashboard/cancel_appraisal", { appraisal_id: appraisalId });
            this._handleResult(result, "cancelled");
        } catch (e) {
            console.error(e);
            this.notification.add(_t("Cancellation failed"), { type: "danger" });
        } finally {
            this.state.processingId = null;
        }
    }

    get totalCount() {
        return (
            (this.state.data.leaves || []).length +
            (this.state.data.expense_sheets || []).length +
            (this.state.data.appraisals || []).length
        );
    }

    fmtNumber(v, digits) {
        if (v == null) return "0";
        try {
            return new Intl.NumberFormat(undefined, { maximumFractionDigits: digits ?? 2 }).format(v);
        } catch {
            return String(v);
        }
    }
}
