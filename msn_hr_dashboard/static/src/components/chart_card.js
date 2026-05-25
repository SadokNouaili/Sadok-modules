/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useRef, useEffect } from "@odoo/owl";

/* global Chart */

export class ChartCard extends Component {
    static template = "msn_hr_dashboard.ChartCard";
    static props = {
        title: String,
        subtitle: { type: String, optional: true },
        type: String, // 'bar' | 'line' | 'pie' | 'doughnut'
        data: Array,
        labelKey: String,
        valueKey: String,
        colorVar: { type: String, optional: true },
        size: { type: String, optional: true }, // 'md' | 'lg'
        fill: { type: Boolean, optional: true },
        horizontal: { type: Boolean, optional: true },
        onBarClick: { type: Function, optional: true },
    };

    setup() {
        this.canvasRef = useRef("canvas");
        this.chart = null;

        onMounted(() => this._renderChart());
        onWillUnmount(() => { if (this.chart) this.chart.destroy(); });

        useEffect(
            () => { this._renderChart(); },
            () => [this.props.data, this.props.type]
        );
    }

    _getCssColor(varName) {
        const root = this.canvasRef.el ? this.canvasRef.el.closest(".msn_hr_dashboard") : null;
        if (!root) return "#6366F1";
        const v = getComputedStyle(root).getPropertyValue(varName).trim();
        return v || "#6366F1";
    }

    _palette() {
        return [
            this._getCssColor("--hr-card-1"),
            this._getCssColor("--hr-card-2"),
            this._getCssColor("--hr-card-3"),
            this._getCssColor("--hr-card-4"),
            this._getCssColor("--hr-card-5"),
            this._getCssColor("--hr-card-6"),
            this._getCssColor("--hr-primary"),
            this._getCssColor("--hr-secondary"),
        ];
    }

    _renderChart() {
        if (!this.canvasRef.el || typeof Chart === "undefined") return;
        if (this.chart) { this.chart.destroy(); this.chart = null; }

        const labels = this.props.data.map(d => d[this.props.labelKey]);
        const values = this.props.data.map(d => d[this.props.valueKey]);
        const baseColor = this.props.colorVar ? this._getCssColor(this.props.colorVar) : this._getCssColor("--hr-primary");
        const palette = this._palette();
        const textColor = this._getCssColor("--hr-text") || "#F1F5F9";
        const mutedColor = this._getCssColor("--hr-text-muted") || "#94A3B8";

        const ctx = this.canvasRef.el.getContext("2d");
        let cfg;

        if (this.props.type === "line") {
            const grad = ctx.createLinearGradient(0, 0, 0, 260);
            grad.addColorStop(0, this._hexToRgba(baseColor, 0.45));
            grad.addColorStop(1, this._hexToRgba(baseColor, 0));
            cfg = {
                type: "line",
                data: {
                    labels,
                    datasets: [{
                        data: values,
                        borderColor: baseColor,
                        backgroundColor: grad,
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointBackgroundColor: baseColor,
                        pointBorderColor: "#fff",
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 7,
                    }],
                },
                options: this._lineBarOptions(textColor, mutedColor),
            };
        } else if (this.props.type === "bar") {
            cfg = {
                type: "bar",
                data: {
                    labels,
                    datasets: [{
                        data: values,
                        backgroundColor: values.map((_, i) => this._hexToRgba(palette[i % palette.length], 0.85)),
                        borderColor: values.map((_, i) => palette[i % palette.length]),
                        borderWidth: 0,
                        borderRadius: 10,
                        borderSkipped: false,
                    }],
                },
                options: {
                    ...this._lineBarOptions(textColor, mutedColor),
                    indexAxis: this.props.horizontal ? "y" : "x",
                    onClick: (evt, els) => {
                        if (els.length && this.props.onBarClick) {
                            const idx = els[0].index;
                            this.props.onBarClick(labels[idx]);
                        }
                    },
                },
            };
        } else { // pie or doughnut
            cfg = {
                type: this.props.type,
                data: {
                    labels,
                    datasets: [{
                        data: values,
                        backgroundColor: values.map((_, i) => palette[i % palette.length]),
                        borderColor: "rgba(254, 250, 224, 0.9)",
                        borderWidth: 2,
                        hoverOffset: 12,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: this.props.type === "doughnut" ? "65%" : 0,
                    animation: { animateRotate: true, duration: 1100, easing: "easeOutQuart" },
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: {
                                color: textColor,
                                usePointStyle: true,
                                pointStyle: "circle",
                                padding: 14,
                                font: { size: 12, family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" },
                            },
                        },
                        tooltip: this._tooltipStyle(),
                    },
                },
            };
        }

        this.chart = new Chart(this.canvasRef.el, cfg);
    }

    _lineBarOptions(textColor, mutedColor) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 900, easing: "easeOutQuart" },
            plugins: {
                legend: { display: false },
                tooltip: this._tooltipStyle(textColor, mutedColor),
            },
            scales: {
                x: {
                    ticks: { color: mutedColor, font: { size: 11, family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" } },
                    grid: { display: false },
                    border: { color: "rgba(40, 54, 24, 0.12)" },
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: mutedColor, font: { size: 11, family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" } },
                    grid: { color: "rgba(40, 54, 24, 0.08)" },
                    border: { display: false },
                },
            },
        };
    }

    _tooltipStyle(textColor, mutedColor) {
        // Tooltip: dark olive bg with cornsilk text — works on either theme
        return {
            backgroundColor: "rgba(40, 54, 24, 0.94)",
            titleColor: "#FEFAE0",
            bodyColor: "#F5EFC9",
            borderColor: "rgba(254, 250, 224, 0.2)",
            borderWidth: 1,
            padding: 12,
            cornerRadius: 12,
            titleFont: { family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", weight: "600", size: 13 },
            bodyFont: { family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", size: 12 },
            displayColors: true,
            boxPadding: 6,
        };
    }

    _hexToRgba(hex, alpha) {
        const h = hex.replace("#", "");
        const r = parseInt(h.substring(0, 2), 16);
        const g = parseInt(h.substring(2, 4), 16);
        const b = parseInt(h.substring(4, 6), 16);
        return `rgba(${r},${g},${b},${alpha})`;
    }
}
