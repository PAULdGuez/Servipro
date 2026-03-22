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
            blueprintId: null,
            blueprints: [],
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
                await this.loadBlueprints();
                await this.loadChartsData();
            }
            this.state.loading = false;
        } catch (e) {
            this.state.error = "Error al cargar sedes: " + (e.message || "");
            this.state.loading = false;
        }
    }

    async loadBlueprints() {
        if (!this.state.sedeId) {
            this.state.blueprints = [];
            this.state.blueprintId = null;
            return;
        }
        try {
            const blueprints = await this.orm.searchRead(
                "pest.blueprint",
                [["sede_id", "=", this.state.sedeId], ["active", "=", true]],
                ["name"]
            );
            this.state.blueprints = blueprints;
            this.state.blueprintId = null;
        } catch (e) {
            this.state.blueprints = [];
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
                blueprint_id: this.state.blueprintId || false,
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
        await this.loadBlueprints();
        await this.loadChartsData();
    }
    async onBlueprintChange(ev) {
        this.state.blueprintId = parseInt(ev.target.value) || null;
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

    async exportPowerPoint() {
        if (!window.PptxGenJS) {
            this.notification.add('PptxGenJS no está cargado. Reemplace el stub con la librería real.', { type: 'danger' });
            return;
        }

        this.notification.add('Generando presentación...', { type: 'info' });

        try {
            const pptx = new window.PptxGenJS();

            // Get all chart canvases in the dashboard
            const chartCards = document.querySelectorAll('.dashboard-chart-card');

            for (const card of chartCards) {
                const canvas = card.querySelector('canvas');
                const titleEl = card.querySelector('.chart-title');
                if (!canvas) continue;

                const slide = pptx.addSlide();
                const title = titleEl ? titleEl.textContent : 'Gráfica';

                // Add title
                slide.addText(title, {
                    x: 0.5, y: 0.3, w: 9, h: 0.5,
                    fontSize: 18, bold: true, color: '333333',
                });

                // Add chart image
                const imgData = canvas.toDataURL('image/png');
                slide.addImage({
                    data: imgData,
                    x: 0.5, y: 1.0, w: 9, h: 5.5,
                });
            }

            // Add metadata slide
            const metaSlide = pptx.addSlide();
            const sede = this.state.sedes.find(s => s.id === this.state.sedeId);
            metaSlide.addText('Dashboard de Control de Plagas', {
                x: 1, y: 1, w: 8, h: 1, fontSize: 28, bold: true, color: '333333', align: 'center',
            });
            metaSlide.addText('Sede: ' + (sede ? sede.name : ''), {
                x: 1, y: 2.5, w: 8, h: 0.5, fontSize: 16, color: '666666', align: 'center',
            });
            metaSlide.addText('Generado: ' + new Date().toLocaleDateString(), {
                x: 1, y: 3.2, w: 8, h: 0.5, fontSize: 14, color: '999999', align: 'center',
            });

            const fileName = 'Dashboard_' + (sede ? sede.name.replace(/\s+/g, '_') : 'Sede') + '.pptx';
            await pptx.writeFile({ fileName: fileName });

            this.notification.add('Presentación exportada: ' + fileName, { type: 'success' });
        } catch (error) {
            this.notification.add('Error al exportar: ' + (error.message || ''), { type: 'danger' });
        }
    }
}

registry.category("actions").add("pest_control.dashboard", PestDashboard);
