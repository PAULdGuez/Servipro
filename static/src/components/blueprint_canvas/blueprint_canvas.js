/** @odoo-module */

import { Component, useState, onWillStart, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";


export class BlueprintCanvas extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.containerRef = useRef("container");

        this.state = useState({
            data: null, // { image_url, traps: [], can_edit }
            loading: true,
            error: null,
            draggedTrapId: null,
            selectedTrapId: null,
            zoomLevel: 1.0,
            hiddenTypes: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        try {
            if (this.props.record.isNew) {
                this.state.loading = false;
                this.state.error = new Error("El plano de sede debe guardarse antes de usar el mapa interactivo.");
                return;
            }
            const data = await this.orm.call(this.props.record.resModel, "get_widget_data", [[this.props.record.resId]]);
            this.state.data = data;
            this.state.error = null;
            this.state.loading = false;
        } catch (error) {
            this.state.error = error;
            this.state.loading = false;
            this.notification.add("Sucedió un error cargando el mapa de trampas. " + (error.message || ""), { type: "danger" });
        }
    }

    onDragStart(ev, trap) {
        if (!this.state.data.can_edit || this.props.readonly) {
            ev.preventDefault();
            return;
        }
        this.state.draggedTrapId = trap.id;

        if (ev.dataTransfer) {
            const dragImage = new Image();
            dragImage.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'; // transparent pixel
            ev.dataTransfer.setDragImage(dragImage, 0, 0);
            ev.dataTransfer.effectAllowed = "move";
        }
    }

    onDragOver(ev) {
        if (!this.state.data.can_edit || this.props.readonly || !this.state.draggedTrapId) return;
        ev.preventDefault();
        if (ev.dataTransfer) {
            ev.dataTransfer.dropEffect = "move";
        }
    }

    async onDrop(ev) {
        if (!this.state.data.can_edit || this.props.readonly || !this.state.draggedTrapId) return;
        ev.preventDefault();

        const container = this.containerRef.el;
        if (!container) return;

        const rect = container.getBoundingClientRect();

        const x = ev.clientX - rect.left;
        const y = ev.clientY - rect.top;

        const pctX = Math.max(0, Math.min(100, (x / rect.width) * 100));
        const pctY = Math.max(0, Math.min(100, (y / rect.height) * 100));

        const trapId = this.state.draggedTrapId;
        this.state.draggedTrapId = null;

        await this.updateTrapPosition(trapId, pctX, pctY);
    }

    onDragEnd() {
        this.state.draggedTrapId = null;
    }

    async updateTrapPosition(trapId, pctX, pctY) {
        const trap = this.state.data.traps.find(t => t.id === trapId);
        if (trap) {
            trap.coord_x_pct = pctX;
            trap.coord_y_pct = pctY;
        }

        try {
            await this.orm.call("pest.trap", "action_move_to_from_widget", [[trapId], pctX, pctY]);
        } catch (error) {
            this.notification.add("Error al guardar la posición en el servidor.", { type: "danger" });
        }
    }

    onContainerClick(ev) {
        // Close popover if clicking outside a marker or popover
        if (ev.target.closest('.o_blueprint_popover')) return;
        if (ev.target.closest('.blueprint-trap-marker')) return;

        // Close any open popover
        if (this.state.selectedTrapId !== null) {
            this.state.selectedTrapId = null;
            return;
        }

        if (!this.state.data.can_edit || this.props.readonly) return;

        const container = this.containerRef.el;
        if (!container) return;

        const rect = container.getBoundingClientRect();
        const pctX = Math.max(0, Math.min(100, ((ev.clientX - rect.left) / rect.width) * 100));
        const pctY = Math.max(0, Math.min(100, ((ev.clientY - rect.top) / rect.height) * 100));

        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'pest.trap',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_blueprint_id: this.props.record.resId,
                default_coord_x_pct: pctX,
                default_coord_y_pct: pctY,
            }
        }, {
            onClose: () => {
                this.state.loading = true;
                this.loadData();
            }
        });
    }

    onTrapMarkerClick(ev, trap) {
        ev.stopPropagation();
        // Toggle popover: click same marker again to close
        if (this.state.selectedTrapId === trap.id) {
            this.state.selectedTrapId = null;
        } else {
            this.state.selectedTrapId = trap.id;
        }
    }

    async onRegisterIncident(trap) {
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'pest.incident',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_trap_id: trap.id,
                default_blueprint_id: this.props.record.resId,
                default_sede_id: trap.sede_id,
            },
        }, {
            onClose: () => this.loadData(),
        });
        this.state.selectedTrapId = null;
    }

    async onViewHistory(trap) {
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'pest.trap',
            res_id: trap.id,
            views: [[false, 'form']],
            target: 'new',
        });
        this.state.selectedTrapId = null;
    }

    onKeyDown(ev) {
        if (!this.state.data.can_edit || this.props.readonly) return;
        // Space or Enter on container to add trap
        if ((ev.key === "Enter" || ev.key === " ") && ev.target.classList.contains('blueprint-container')) {
            ev.preventDefault();
            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'pest.trap',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_blueprint_id: this.props.record.resId,
                    default_coord_x_pct: 50,
                    default_coord_y_pct: 50,
                }
            }, {
                onClose: () => {
                    this.state.loading = true;
                    this.loadData();
                }
            });
        }
    }

    onZoomIn() {
        this.state.zoomLevel = Math.min(3.0, this.state.zoomLevel + 0.25);
    }

    onZoomOut() {
        this.state.zoomLevel = Math.max(0.5, this.state.zoomLevel - 0.25);
    }

    onZoomReset() {
        this.state.zoomLevel = 1.0;
    }

    onWheel(ev) {
        if (ev.ctrlKey) {
            ev.preventDefault();
            if (ev.deltaY < 0) {
                this.onZoomIn();
            } else {
                this.onZoomOut();
            }
        }
    }

    async onDeactivateTrap(trapId) {
        const trap = this.state.data.traps.find(t => t.id === trapId);
        if (!trap) return;

        const confirmed = window.confirm(
            `¿Desactivar trampa "${trap.name}"? La trampa no se eliminará, solo se archivará.`
        );
        if (!confirmed) return;

        // Close popover immediately
        this.state.selectedTrapId = null;

        // Optimistic UI update — remove from array immediately
        const trapIndex = this.state.data.traps.findIndex(t => t.id === trapId);
        const removedTrap = this.state.data.traps.splice(trapIndex, 1)[0];

        try {
            await this.orm.call('pest.trap', 'write', [[trapId], { active: false }]);
            this.notification.add(
                `Trampa "${trap.name}" archivada correctamente.`,
                { type: 'success' }
            );
        } catch (error) {
            // Revert optimistic update on failure
            this.state.data.traps.splice(trapIndex, 0, removedTrap);
            this.notification.add(
                `Error al archivar trampa: ${error.message || 'Error desconocido'}`,
                { type: 'danger' }
            );
        }
    }

    toggleTypeVisibility(typeId) {
        const idx = this.state.hiddenTypes.indexOf(typeId);
        if (idx >= 0) {
            this.state.hiddenTypes.splice(idx, 1);
        } else {
            this.state.hiddenTypes.push(typeId);
        }
    }

    isTrapVisible(trap) {
        return !this.state.hiddenTypes.includes(trap.trap_type_id);
    }
}

BlueprintCanvas.template = "pest_control.BlueprintCanvas";
BlueprintCanvas.components = {};
BlueprintCanvas.props = {
    ...standardFieldProps,
};
BlueprintCanvas.supportedTypes = ["binary"];

registry.category("fields").add("blueprint_canvas", {
    component: BlueprintCanvas,
});
