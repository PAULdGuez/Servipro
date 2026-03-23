/** @odoo-module **/
import { Component, useState, useRef, onMounted, onWillUnmount, onPatched } from "@odoo/owl";

export class DashboardChart extends Component {
    static template = "pest_control.DashboardChart";
    static props = {
        title: { type: String },
        chartType: { type: String },
        chartData: { type: Object, optional: true },
        chartOptions: { type: Object, optional: true },
        height: { type: Number, optional: true },
    };

    get hasData() {
        return !!(this.props.chartData && this.props.chartData.labels && this.props.chartData.labels.length > 0);
    }

    setup() {
        this.canvasRef = useRef("chartCanvas");
        this.chartInstance = null;
        this.state = useState({ isFullscreen: false });

        onMounted(() => {
            setTimeout(() => this._tryRender(), 50);
        });
        onPatched(() => this._tryRender());
        onWillUnmount(() => this._destroyChart());
    }

    _tryRender() {
        if (this.props.chartData && this.props.chartData.labels) {
            this._renderChart();
        }
    }

    _renderChart() {
        this._destroyChart();
        const canvas = this.canvasRef.el;
        if (!canvas || !window.Chart) return;

        // Read theme colors from CSS variables
        const style = getComputedStyle(document.documentElement);
        const textColor = style.getPropertyValue('--pest-chart-text').trim() || '#666';
        const gridColor = style.getPropertyValue('--pest-chart-grid').trim() || '#e0e0e0';

        this.chartInstance = new window.Chart(canvas.getContext("2d"), {
            type: this.props.chartType || "bar",
            data: this.props.chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { boxWidth: 12, font: { size: 11 }, color: textColor }
                    },
                    title: { display: false },
                },
                scales: {
                    x: {
                        ticks: { color: textColor },
                        grid: { color: gridColor },
                    },
                    y: {
                        ticks: { color: textColor },
                        grid: { color: gridColor },
                    },
                },
                ...(this.props.chartOptions || {}),
            },
        });
    }

    _destroyChart() {
        if (this.chartInstance) {
            this.chartInstance.destroy();
            this.chartInstance = null;
        }
    }

    downloadPNG() {
        if (!this.chartInstance) return;
        const link = document.createElement("a");
        link.download = (this.props.title || "chart").replace(/\s+/g, "_") + ".png";
        link.href = this.chartInstance.toBase64Image();
        link.click();
    }

    toggleFullscreen() {
        this.state.isFullscreen = !this.state.isFullscreen;
        setTimeout(() => { if (this.chartInstance) this.chartInstance.resize(); }, 150);
    }
}
