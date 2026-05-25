/** @odoo-module **/

import { Component, useState, onMounted, useRef } from "@odoo/owl";

export class KpiCard extends Component {
    static template = "msn_hr_dashboard.KpiCard";
    static props = {
        label: String,
        value: { type: [Number, String], optional: true },
        icon: { type: String, optional: true },
        colorVar: { type: String, optional: true },
        sparkline: { type: Array, optional: true },
        trend: { type: String, optional: true },
        onClick: { type: Function, optional: true },
    };

    setup() {
        this.state = useState({ displayValue: 0 });
        this.sparkRef = useRef("spark");
        this.cardRef = useRef("card");

        onMounted(() => {
            this._animateCounter();
            this._drawSparkline();
            this._setupHoverTilt();
        });
    }

    _animateCounter() {
        const target = parseFloat(this.props.value) || 0;
        const duration = 1200;
        const start = performance.now();
        const tick = (now) => {
            const t = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - t, 3);
            this.state.displayValue = (target * eased);
            if (t < 1) requestAnimationFrame(tick);
            else this.state.displayValue = target;
        };
        requestAnimationFrame(tick);
    }

    formattedValue() {
        const v = this.state.displayValue;
        if (Number.isInteger(parseFloat(this.props.value))) return Math.round(v).toLocaleString();
        return v.toFixed(1);
    }

    _drawSparkline() {
        const svg = this.sparkRef.el;
        if (!svg || !this.props.sparkline || !this.props.sparkline.length) return;
        const data = this.props.sparkline;
        const w = 120, h = 36, pad = 2;
        const max = Math.max(...data, 1);
        const min = Math.min(...data, 0);
        const range = (max - min) || 1;
        const stepX = (w - 2 * pad) / Math.max(data.length - 1, 1);
        const points = data.map((v, i) => {
            const x = pad + i * stepX;
            const y = h - pad - ((v - min) / range) * (h - 2 * pad);
            return [x, y];
        });
        const pathD = points.map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
        const areaD = pathD + ` L ${points[points.length - 1][0]},${h} L ${points[0][0]},${h} Z`;
        svg.innerHTML = `
            <defs>
                <linearGradient id="sparkGrad-${this.props.label.replace(/\s/g,'')}" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stop-color="currentColor" stop-opacity="0.5"/>
                    <stop offset="100%" stop-color="currentColor" stop-opacity="0"/>
                </linearGradient>
            </defs>
            <path d="${areaD}" fill="url(#sparkGrad-${this.props.label.replace(/\s/g,'')})"/>
            <path d="${pathD}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="${points[points.length-1][0]}" cy="${points[points.length-1][1]}" r="2.5" fill="currentColor"/>
        `;
    }

    _setupHoverTilt() {
        const card = this.cardRef.el;
        if (!card) return;
        card.addEventListener("mousemove", (e) => {
            const rect = card.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
            const y = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
            card.style.setProperty("--mx", `${e.clientX - rect.left}px`);
            card.style.setProperty("--my", `${e.clientY - rect.top}px`);
            card.style.transform = `perspective(900px) rotateX(${-y * 3}deg) rotateY(${x * 3}deg) translateZ(0)`;
        });
        card.addEventListener("mouseleave", () => {
            card.style.transform = "";
        });
    }

    iconPath() {
        const icons = {
            users: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M23 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75",
            check: "M22 11.08V12a10 10 0 1 1-5.93-9.14 M22 4L12 14.01l-3-3",
            calendar: "M19 4H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zM16 2v4M8 2v4M3 10h18",
            "user-plus": "M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 M8.5 7a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M20 8v6M23 11h-6",
            wallet: "M21 12V7H5a2 2 0 0 1 0-4h14v4 M3 5v14a2 2 0 0 0 2 2h16v-5 M18 12a2 2 0 0 0 0 4h4v-4Z",
            file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8",
            star: "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z",
        };
        return icons[this.props.icon] || icons.users;
    }
}
