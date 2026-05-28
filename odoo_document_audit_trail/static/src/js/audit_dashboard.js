/** @odoo-module **/

import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef }
    from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

export class AuditTrailDashboard extends Component {
    static template = "odoo_document_audit_trail.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.barRef = useRef("barChart");
        this.opRef = useRef("opChart");
        this.rootRef = useRef("root");
        this._charts = [];

        this.state = useState({
            loading: true,
            error: false,
            days: 30,
            data: null,
        });

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
        });

        onMounted(async () => {
            await this.load();
        });

        onWillUnmount(() => this._destroyCharts());
    }

    async load() {
        this.state.loading = true;
        this.state.error = false;
        try {
            const data = await this.orm.call(
                "audit.trail.entry", "get_dashboard_data", [this.state.days]
            );
            this.state.data = data;
            this.state.loading = false;
            // Wait a tick so refs are in the DOM, then draw + animate.
            setTimeout(() => {
                this._renderCharts();
                this._animateCounters();
            }, 60);
        } catch (e) {
            console.error("[AuditDashboard] load failed", e);
            this.state.error = true;
            this.state.loading = false;
        }
    }

    async setRange(days) {
        if (this.state.days === days) {
            return;
        }
        this.state.days = days;
        this._destroyCharts();
        await this.load();
    }

    // --- KPI count-up animation -----------------------------------------
    _animateCounters() {
        const root = this.rootRef.el;
        const els = root ? root.querySelectorAll("[data-count]") : [];
        els.forEach((el) => {
            const target = parseInt(el.dataset.count || "0", 10);
            const dur = 900;
            const start = performance.now();
            const step = (now) => {
                const p = Math.min((now - start) / dur, 1);
                // easeOutCubic
                const eased = 1 - Math.pow(1 - p, 3);
                el.textContent = Math.round(target * eased).toLocaleString();
                if (p < 1) {
                    requestAnimationFrame(step);
                }
            };
            requestAnimationFrame(step);
        });
    }

    _destroyCharts() {
        this._charts.forEach((c) => {
            try { c.destroy(); } catch (e) { /* ignore */ }
        });
        this._charts = [];
    }

    _renderCharts() {
        const Chart = window.Chart;
        if (!Chart || !this.state.data) {
            return;
        }
        this._destroyCharts();
        const d = this.state.data;

        // Activity-over-time bar chart
        if (this.barRef.el) {
            const grad = this.barRef.el.getContext("2d")
                .createLinearGradient(0, 0, 0, 220);
            grad.addColorStop(0, "rgba(56,189,248,0.95)");
            grad.addColorStop(1, "rgba(37,99,235,0.55)");
            this._charts.push(new Chart(this.barRef.el, {
                type: "bar",
                data: {
                    labels: d.by_day.map((x) => x.label),
                    datasets: [{
                        label: _t("Actions"),
                        data: d.by_day.map((x) => x.count),
                        backgroundColor: grad,
                        borderRadius: 6,
                        maxBarThickness: 26,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    animation: { duration: 900, easing: "easeOutQuart" },
                    scales: {
                        x: { grid: { display: false } },
                        y: { beginAtZero: true, ticks: { precision: 0 } },
                    },
                },
            }));
        }

        // By-operation doughnut
        if (this.opRef.el) {
            const palette = [
                "#2563eb", "#38bdf8", "#22c55e", "#f59e0b", "#ef4444",
                "#a855f7", "#14b8a6", "#eab308", "#fb7185", "#64748b",
            ];
            this._charts.push(new Chart(this.opRef.el, {
                type: "doughnut",
                data: {
                    labels: d.by_operation.map((x) => x.label),
                    datasets: [{
                        data: d.by_operation.map((x) => x.count),
                        backgroundColor: d.by_operation.map(
                            (_x, i) => palette[i % palette.length]),
                        borderWidth: 0,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "62%",
                    plugins: {
                        legend: { position: "right", labels: { boxWidth: 12 } },
                    },
                    animation: {
                        animateRotate: true,
                        duration: 1000,
                        easing: "easeOutQuart",
                    },
                },
            }));
        }
    }

    maxUser() {
        const u = this.state.data && this.state.data.top_users;
        return u && u.length ? Math.max(...u.map((x) => x.count)) : 1;
    }

    maxDoc() {
        const t = this.state.data && this.state.data.top_documents;
        return t && t.length ? Math.max(...t.map((x) => x.count)) : 1;
    }

    pct(count, max) {
        return Math.max(4, Math.round((count / (max || 1)) * 100));
    }

    iconFor(op) {
        const map = {
            create: "fa-plus-circle", write: "fa-pencil",
            unlink: "fa-trash", archive: "fa-archive",
            unarchive: "fa-rotate-left", lock: "fa-lock",
            unlock: "fa-unlock", download: "fa-download",
            preview_open: "fa-eye", preview_close: "fa-eye-slash",
            share: "fa-share-alt", split_source: "fa-scissors",
            split_result: "fa-file", replace: "fa-retweet",
            restore_version: "fa-history", sign_request: "fa-pen-nib",
            sign_completed: "fa-check-double", sign_item_added: "fa-plus",
            sign_item_removed: "fa-minus", sign_item_signed: "fa-signature",
        };
        return map[op] || "fa-circle";
    }

    openOperation(op) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Audit Trail"),
            res_model: "audit.trail.entry",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: op ? [["operation_type", "=", op]] : [],
            context: { create: false },
        });
    }

    openFollowups() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Follow-ups"),
            res_model: "audit.trail.entry",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["followup_state", "in", ["open", "in_progress"]]],
            context: { create: false },
        });
    }

    openEntry(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "audit.trail.entry",
            res_id: id,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openTrail(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "audit.trail.entry",
            name: _t("Document Timeline"),
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["trail_id", "=", id]],
            context: { create: false },
        });
    }
}

registry.category("actions").add(
    "audit_trail_dashboard", AuditTrailDashboard);
