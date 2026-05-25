/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class EmployeeSpotlight extends Component {
    static template = "msn_hr_dashboard.EmployeeSpotlight";
    static props = {
        dateFrom: String,
        dateTo: String,
    };

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            employees: [],
            search: "",
            selectedId: null,
            spotlight: null,
            loading: false,
            loadingDetail: false,
        });

        onWillStart(async () => {
            await this._loadEmployees();
        });
    }

    async _loadEmployees() {
        this.state.loading = true;
        try {
            this.state.employees = await rpc("/msn_hr_dashboard/employees", {});
        } catch (e) {
            console.error("employee list failed", e);
            this.notification.add(_t("Could not load employees"), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    get filteredEmployees() {
        const q = (this.state.search || "").trim().toLowerCase();
        if (!q) return this.state.employees;
        return this.state.employees.filter((e) =>
            (e.name || "").toLowerCase().includes(q) ||
            (e.job_title || "").toLowerCase().includes(q) ||
            (e.department || "").toLowerCase().includes(q)
        );
    }

    async onSelectEmployee(empId) {
        this.state.selectedId = empId;
        this.state.loadingDetail = true;
        try {
            this.state.spotlight = await rpc("/msn_hr_dashboard/employee_spotlight", {
                employee_id: empId,
                date_from: this.props.dateFrom,
                date_to: this.props.dateTo,
            });
            if (this.state.spotlight && this.state.spotlight.error) {
                this.notification.add(this.state.spotlight.error, { type: "warning" });
            }
        } catch (e) {
            console.error("spotlight failed", e);
            this.notification.add(_t("Could not load employee data"), { type: "danger" });
        } finally {
            this.state.loadingDetail = false;
        }
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value;
    }

    onClearSelection() {
        this.state.selectedId = null;
        this.state.spotlight = null;
    }

    _noCreateCtx() {
        return { create: false, delete: false, duplicate: false };
    }

    openEmployeeForm() {
        if (!this.state.spotlight || !this.state.spotlight.profile) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.employee",
            res_id: this.state.spotlight.profile.id,
            views: [[false, "form"]],
            view_mode: "form",
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openLeaves() {
        if (!this.state.spotlight) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Leaves"),
            res_model: "hr.leave",
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            domain: [["employee_id", "=", this.state.spotlight.profile.id]],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openAttendances() {
        if (!this.state.spotlight) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Attendances"),
            res_model: "hr.attendance",
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            domain: [["employee_id", "=", this.state.spotlight.profile.id]],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openExpenses() {
        if (!this.state.spotlight) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Expenses"),
            res_model: "hr.expense",
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            domain: [["employee_id", "=", this.state.spotlight.profile.id]],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openPayslips() {
        if (!this.state.spotlight || !this.state.spotlight.payroll_installed) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Payslips"),
            res_model: "hr.payslip",
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            domain: [["employee_id", "=", this.state.spotlight.profile.id]],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openVersions() {
        if (!this.state.spotlight) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Employee Versions"),
            res_model: "hr.version",
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            domain: [["employee_id", "=", this.state.spotlight.profile.id]],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    async printPayslip() {
        const slip = this.state.spotlight && this.state.spotlight.last_payslip;
        if (!slip || !slip.id) {
            this.notification.add(_t("No payslip available to print"), { type: "warning" });
            return;
        }
        try {
            const action = await rpc("/msn_hr_dashboard/print_payslip", { payslip_id: slip.id });
            if (action && action.type) {
                await this.action.doAction(action);
            } else {
                this.notification.add(_t("Payslip report not available"), { type: "warning" });
            }
        } catch (e) {
            console.error("payslip print failed", e);
            this.notification.add(_t("Could not print payslip"), { type: "danger" });
        }
    }

    fmtCurrency(v) {
        if (v == null) return "—";
        try {
            return new Intl.NumberFormat(undefined, {
                maximumFractionDigits: 2,
            }).format(v);
        } catch {
            return String(v);
        }
    }
}
