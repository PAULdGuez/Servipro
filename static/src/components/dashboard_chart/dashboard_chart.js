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

    /**
     * 🔑 **Actualizar la gráfica que ya existe, NUNCA tirarla y rehacerla.**
     *
     * Rehacerla en cada repintado costó una gráfica en blanco durante meses: la
     * «Distribución por Tipo de Incidencia» tiene una gemela que consume los mismos datos, y
     * entre las dos se disparaban repintados en cadena. Medido con un contador puesto en el
     * constructor de la librería: **se creaba 122 veces**, contra 1 de las otras trece. Cada
     * creación arrancaba la animación en cero grados y la destruían antes del primer fotograma,
     * así que el arco existía, con los datos correctos, y no llegaba a dibujarse nunca.
     *
     * El fallo es **mudo**: sin error en consola, sin aviso, un cuadro vacío que se lee como
     * «esta planta no tiene datos».
     */
    _tryRender() {
        if (!this.props.chartData || !this.props.chartData.labels) {
            return;
        }
        if (this.chartInstance) {
            this.chartInstance.data = this._copiaDeDatos();
            // Sin animación: un repintado puede llegar mientras la anterior corre, y la gráfica
            // se queda congelada en un fotograma intermedio — un arco a medio dibujar, que se ve
            // peor que vacío porque parece un dato.
            this.chartInstance.update("none");
            return;
        }
        this._renderChart();
    }

    _renderChart() {
        this._destroyChart();
        const canvas = this.canvasRef.el;
        if (!canvas || !window.Chart) return;
        this.chartInstance = new window.Chart(canvas.getContext("2d"), {
            type: this.props.chartType || "bar",
            // 🔑 Una COPIA, nunca el objeto del estado. Chart.js se adueña del objeto de datos
            // que recibe y escribe dentro de cada dataset; si dos gráficas comparten el mismo
            // (pasa en cuanto se pintan los mismos datos como dona y como barras), la segunda
            // se lo arrebata a la primera y **la primera se queda en blanco, sin dar ningún
            // error**. Copiar también evita que Chart.js escriba dentro del estado reactivo de
            // OWL, que dispara repintados en cadena.
            data: this._copiaDeDatos(),
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
                    title: { display: false },
                },
                ...(this.props.chartOptions || {}),
            },
        });
    }

    /** Copia superficial, con su propio arreglo de datasets: es donde Chart.js escribe. */
    _copiaDeDatos() {
        const datos = this.props.chartData || {};
        return {
            ...datos,
            labels: Array.isArray(datos.labels) ? [...datos.labels] : datos.labels,
            // Un dataset sin `label` sale en la leyenda como **«undefined»** en cuanto la gráfica
            // es de barras (en las de dona no se nota, porque la leyenda usa `labels`). Siete de
            // los catorce conjuntos que manda el backend vienen sin nombre. Se rellena aquí, con
            // el título que el usuario ya está viendo arriba, en vez de en los siete sitios:
            // así el octavo que alguien añada nace bien.
            datasets: Array.isArray(datos.datasets)
                ? datos.datasets.map((d) => ({ label: this.props.title, ...d }))
                : [],
        };
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
