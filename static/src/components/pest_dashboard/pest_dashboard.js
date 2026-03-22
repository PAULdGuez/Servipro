/** @odoo-module **/
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { DashboardChart } from "../dashboard_chart/dashboard_chart";

export class PestDashboard extends Component {
    static template = "pest_control.PestDashboard";
    static components = { DashboardChart };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            error: null,
            sedeId: null,
            dateFrom: null,
            dateTo: null,
            activeTab: "sede",
            sedes: [],
            chartsData: {},
        });
        onMounted(async () => await this.loadSedes());
    }

    async loadSedes() {
        try {
            const sedes = await this.orm.searchRead("pest.sede", [["active", "=", true]], ["name"]);
            this.state.sedes = sedes;
            if (sedes.length > 0) {
                this.state.sedeId = sedes[0].id;
                await this.loadChartsData();
            }
            this.state.loading = false;
        } catch (e) {
            this.state.error = "Error al cargar sedes: " + (e.message || "");
            this.state.loading = false;
        }
    }

    async loadChartsData() {
        if (!this.state.sedeId) return;
        this.state.loading = true;
        this.state.error = null;
        try {
            const params = {
                date_from: this.state.dateFrom || false,
                date_to: this.state.dateTo || false,
            };
            if (this.state.activeTab === "sede") {
                const data = await this.orm.call("pest.sede", "get_dashboard_data", [[this.state.sedeId], params]);
                this.state.chartsData = data || {};
            } else if (this.state.activeTab === "quejas") {
                const data = await this.orm.call("pest.sede", "get_quejas_dashboard_data", [[this.state.sedeId], params]);
                this.state.chartsData = data || {};
            } else if (this.state.activeTab === "ventas") {
                const data = await this.orm.call("pest.sede", "get_ventas_dashboard_data", [[this.state.sedeId], params]);
                this.state.chartsData = data || {};
            }
        } catch (e) {
            this.state.error = "Error al cargar datos: " + (e.message || "");
            this.state.chartsData = {};
        }
        this.state.loading = false;
    }

    async onSedeChange(ev) {
        this.state.sedeId = parseInt(ev.target.value) || null;
        await this.loadChartsData();
    }
    async onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value || null;
        await this.loadChartsData();
    }
    async onDateToChange(ev) {
        this.state.dateTo = ev.target.value || null;
        await this.loadChartsData();
    }
    async onTabChange(tab) {
        this.state.activeTab = tab;
        this.state.chartsData = {};
        await this.loadChartsData();
    }

    exportPowerPoint() {
        this.notification.add("Exportar a PowerPoint: en desarrollo", { type: "warning" });
    }
}

registry.category("actions").add("pest_control.dashboard", PestDashboard);
