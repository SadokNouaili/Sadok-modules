/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { KpiCard } from "./kpi_card";
import { ChartCard } from "./chart_card";
import { EmployeeSpotlight } from "./employee_spotlight";
import { ApprovalsCenter } from "./approvals_center";

export class HRDashboard extends Component {
    static template = "msn_hr_dashboard.Dashboard";
    static components = { KpiCard, ChartCard, EmployeeSpotlight, ApprovalsCenter };

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.rootRef = useRef("root");

        const today = new Date();
        const monthAgo = new Date();
        monthAgo.setDate(today.getDate() - 30);

        this.state = useState({
            loading: true,
            data: null,
            dateFrom: this._fmtDate(monthAgo),
            dateTo: this._fmtDate(today),
            preset: "30d",
            showSpotlight: false,
            showApprovals: false,
        });

        // Pre-translated UI strings. Using _t() here marks them as translatable
        // so they get extracted to the .pot/.po file, and looked up at render time
        // against the active user's language.
        this.labels = {
            // KPI labels
            totalEmployees: _t("Total Employees"),
            presentToday: _t("Present Today"),
            pendingLeaves: _t("Pending Leaves"),
            newHires: _t("New Hires"),
            pendingExpenses: _t("Pending Expenses"),
            employeeVersions: _t("Employee Versions"),
            pendingAppraisals: _t("Pending Appraisals"),
            completedAppraisals: _t("Completed Appraisals"),
            payslips: _t("Payslips"),
            netWageTotal: _t("Net Wage Total"),
            // KPI trend suffixes
            trendNew: _t("new"),
            trendLive: _t("Live"),
            trendApprovedTotal: _t("approved total"),
            trendInRange: _t("In range"),
            trendDraft: _t("draft"),
            trendSubmitted: _t("submitted"),
            trendApproved: _t("approved"),
            trendActive: _t("Active"),
            trendUpcoming: _t("upcoming"),
            trendDone: _t("done"),
            // Chart titles
            chartAttendanceTrend: _t("Attendance Trend"),
            chartLast14Days: _t("Last 14 days"),
            chartGenderDistribution: _t("Gender Distribution"),
            chartActiveEmployees: _t("Active employees"),
            chartEmployeesByDept: _t("Employees by Department"),
            chartTop8Depts: _t("Top 8 departments"),
            chartLeavesByType: _t("Leaves by Type"),
            chartInSelectedRange: _t("In selected range"),
            chartEmployeeGrowth: _t("Employee Growth"),
            chartLast6Months: _t("Last 6 months"),
            chartExpensesByCategory: _t("Expenses by Category"),
            chartTop6: _t("Top 6"),
            chartAppraisalsByStatus: _t("Appraisals by Status"),
            chartPerformancePipeline: _t("Performance review pipeline"),
            chartAppraisalDistribution: _t("Appraisal Distribution"),
            chartCurrentSnapshot: _t("Current snapshot"),
            // Gender legend labels (for the doughnut data)
            genderMale: _t("Male"),
            genderFemale: _t("Female"),
            genderOther: _t("Other"),
        };

        onWillStart(async () => {
            await this._loadData();
        });

        onMounted(() => {
            // Reapply theme once the dashboard root element is fully in the DOM —
            // _applyThemeFromConfig only sets variables on :root before this point
            // because rootRef.el doesn't exist yet during onWillStart.
            this._applyTheme();
        });

        onWillUnmount(() => {
            // cleanup if needed
        });
    }

    _fmtDate(d) {
        return d.toISOString().split("T")[0];
    }

    /**
     * Build an inline-style string that declares every theme CSS variable directly
     * on the dashboard root element. This is critical for child charts to see the
     * right colors — `t-att-style` is applied DURING render, before any child
     * onMounted fires, so when ChartCard reads getComputedStyle on its closest
     * .msn_hr_dashboard ancestor, the configured colors are already there.
     *
     * Using a getter (not a stored value) means it re-evaluates whenever the
     * component re-renders, so config changes apply automatically on refresh.
     */
    get themeStyle() {
        const cfg = this.state.data && this.state.data.config;
        if (!cfg) return "";
        const parts = [];
        const set = (name, value) => {
            if (value !== undefined && value !== null && value !== "") {
                parts.push(`${name}: ${value}`);
            }
        };
        set("--hr-primary", cfg.primary_color);
        set("--hr-secondary", cfg.secondary_color);
        set("--hr-accent", cfg.accent_color);
        set("--hr-bg-1", cfg.bg_gradient_start);
        set("--hr-bg-2", cfg.bg_gradient_mid);
        set("--hr-bg-3", cfg.bg_gradient_end);
        set("--hr-text", cfg.text_color);
        set("--hr-text-muted", cfg.text_muted_color);
        if (cfg.glass_opacity != null) set("--hr-glass-opacity", cfg.glass_opacity);
        if (cfg.blur_intensity != null) set("--hr-blur", `${cfg.blur_intensity}px`);
        if (cfg.border_radius != null) set("--hr-radius", `${cfg.border_radius}px`);
        if (Array.isArray(cfg.card_colors)) {
            cfg.card_colors.forEach((c, i) => {
                if (c) set(`--hr-card-${i + 1}`, c);
            });
        }
        return parts.join("; ");
    }

    async _loadData() {
        this.state.loading = true;
        try {
            const result = await rpc("/msn_hr_dashboard/data", {
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
            });
            // CRITICAL: apply theme to :root BEFORE we set state.data.
            // Setting state.data triggers the re-render that mounts ChartCard children,
            // and ChartCard.onMounted reads --hr-card-* via getComputedStyle. If we apply
            // the theme to a local element AFTER children mount, charts render with the
            // SCSS default palette instead of the configured colors.
            this._applyThemeFromConfig(result && result.config);
            this.state.data = result;
        } catch (e) {
            this.notification.add(_t("Could not load dashboard data"), { type: "danger" });
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }

    _applyThemeFromConfig(cfg) {
        if (!cfg) return;
        // Critical: CSS variables follow inheritance. The SCSS declares defaults inside
        // the `.msn_hr_dashboard { ... }` selector, which means any descendant of .msn_hr_dashboard
        // resolves --hr-* from that scope FIRST, shadowing values we set on :root.
        //
        // The fix is to set the variables ON the .msn_hr_dashboard element itself (via inline
        // style), which has higher precedence than the SCSS-declared values on the same
        // selector. We also set them on documentElement as a fallback for any elements
        // rendered outside the dashboard subtree (popovers, dialogs, etc.).
        const targets = [];
        if (this.rootRef && this.rootRef.el) {
            targets.push(this.rootRef.el);
        }
        targets.push(document.documentElement);

        const setVar = (name, value) => {
            for (const el of targets) {
                el.style.setProperty(name, value);
            }
        };

        if (cfg.primary_color)        setVar("--hr-primary", cfg.primary_color);
        if (cfg.secondary_color)      setVar("--hr-secondary", cfg.secondary_color);
        if (cfg.accent_color)         setVar("--hr-accent", cfg.accent_color);
        if (cfg.bg_gradient_start)    setVar("--hr-bg-1", cfg.bg_gradient_start);
        if (cfg.bg_gradient_mid)      setVar("--hr-bg-2", cfg.bg_gradient_mid);
        if (cfg.bg_gradient_end)      setVar("--hr-bg-3", cfg.bg_gradient_end);
        if (cfg.text_color)           setVar("--hr-text", cfg.text_color);
        if (cfg.text_muted_color)     setVar("--hr-text-muted", cfg.text_muted_color);
        if (cfg.glass_opacity != null) setVar("--hr-glass-opacity", String(cfg.glass_opacity));
        if (cfg.blur_intensity != null) setVar("--hr-blur", cfg.blur_intensity + "px");
        if (cfg.border_radius != null) setVar("--hr-radius", cfg.border_radius + "px");
        if (Array.isArray(cfg.card_colors)) {
            cfg.card_colors.forEach((c, i) => {
                if (c) setVar(`--hr-card-${i + 1}`, c);
            });
        }
    }

    // Legacy alias retained in case other code paths call _applyTheme
    _applyTheme() {
        if (!this.state.data || !this.state.data.config) return;
        this._applyThemeFromConfig(this.state.data.config);
    }

    async onPresetClick(preset) {
        this.state.preset = preset;
        const today = new Date();
        const from = new Date();
        if (preset === "7d") from.setDate(today.getDate() - 7);
        else if (preset === "30d") from.setDate(today.getDate() - 30);
        else if (preset === "90d") from.setDate(today.getDate() - 90);
        else if (preset === "1y") from.setFullYear(today.getFullYear() - 1);
        else if (preset === "ytd") {
            from.setMonth(0);
            from.setDate(1);
        }
        this.state.dateFrom = this._fmtDate(from);
        this.state.dateTo = this._fmtDate(today);
        await this._loadData();
    }

    async onDateChange(field, ev) {
        this.state[field] = ev.target.value;
        this.state.preset = "custom";
        await this._loadData();
    }

    async onRefresh() {
        await this._loadData();
        this.notification.add(_t("Dashboard refreshed"), { type: "success" });
    }

    onToggleSpotlight() {
        this.state.showSpotlight = !this.state.showSpotlight;
    }

    onToggleApprovals() {
        this.state.showApprovals = !this.state.showApprovals;
    }

    async onApprovalDone() {
        // refresh the main KPIs when something is approved/refused
        await this._loadData();
    }

    // ---------- Drill-down actions ----------
    // Odoo 19: pass `views` as array of [view_id, view_type] tuples — DO NOT also pass `view_mode`
    // because the two conflict and Odoo silently ignores the action. We pass `view_mode` only,
    // and add context: {create:false, delete:false, duplicate:false} to remove those buttons.
    _noCreateCtx() {
        return { create: false, delete: false, duplicate: false };
    }

    openEmployees() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Employees"),
            res_model: "hr.employee",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            view_mode: "kanban,list,form",
            domain: [["active", "=", true]],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openNewHires() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("New Hires"),
            res_model: "hr.employee",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            view_mode: "kanban,list,form",
            domain: [
                ["create_date", ">=", this.state.dateFrom],
                ["create_date", "<=", this.state.dateTo + " 23:59:59"],
                ["active", "=", true],
            ],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openAttendance() {
        const today = this._fmtDate(new Date());
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Today's Attendance"),
            res_model: "hr.attendance",
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            domain: [
                ["check_in", ">=", today + " 00:00:00"],
                ["check_in", "<=", today + " 23:59:59"],
            ],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openPendingLeaves() {
        // Odoo 19 hr.leave states awaiting approval: 'confirm' (first) and 'validate1' (second)
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Pending Leave Requests"),
            res_model: "hr.leave",
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            domain: [["state", "in", ["confirm", "validate1"]]],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openApprovedLeaves() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Approved Leaves"),
            res_model: "hr.leave",
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            domain: [
                ["state", "=", "validate"],
                ["date_from", ">=", this.state.dateFrom],
                ["date_to", "<=", this.state.dateTo],
            ],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openExpenses() {
        // KPI shows expenses still needing review (draft + submitted)
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Expenses Needing Review"),
            res_model: "hr.expense",
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            domain: [["state", "in", ["draft", "submitted"]]],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openContracts() {
        // Odoo 19: hr.contract renamed to hr.version
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Employee Versions"),
            res_model: "hr.version",
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            domain: [["employee_id.active", "=", true]],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openAppraisals() {
        // Odoo 19 hr.appraisal states: '1_new' (Draft), '2_pending' (Ongoing), '3_done' (Done)
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Pending Appraisals"),
            res_model: "hr.appraisal",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            view_mode: "kanban,list,form",
            domain: [["state", "in", ["1_new", "2_pending"]]],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openDoneAppraisals() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Completed Appraisals"),
            res_model: "hr.appraisal",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            view_mode: "kanban,list,form",
            domain: [["state", "=", "3_done"]],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openPayslips() {
        // Overlap detection: payslip whose period intersects the dashboard date range
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Payslips"),
            res_model: "hr.payslip",
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            domain: [
                ["date_from", "<=", this.state.dateTo],
                ["date_to", ">=", this.state.dateFrom],
            ],
            context: this._noCreateCtx(),
            target: "current",
        });
    }

    openDepartmentEmployees(deptName) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: deptName,
            res_model: "hr.employee",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            view_mode: "kanban,list,form",
            domain: [["department_id.name", "=", deptName], ["active", "=", true]],
            context: this._noCreateCtx(),
            target: "current",
        });
    }
}

registry.category("actions").add("msn_hr_dashboard.dashboard", HRDashboard);
