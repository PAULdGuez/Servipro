/** @odoo-module */

import { Component, useState, onWillStart, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";


export class BlueprintCanvas extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.containerRef = useRef("container");

        this.state = useState({
            data: null, // { image_url, traps: [], can_edit }
            loading: true,
            error: null,
            draggedTrapId: null,
            selectedTrapId: null,
            trapDetail: null,
            zoomLevel: 1.0,
            sidePanelOpen: false,
            filterTrapType: null,
            filterTrapState: null,
            searchTerm: '',
            highlightedTrapId: null,
            hiddenTypes: [],
            showIncidentBadges: true,
            heatmapActive: false,
            heatmapLoading: false,
            heatmapMode: 'organisms', // 'organisms' or 'incidents'
            drawingMode: false,
            drawingPoints: [],
            selectedZoneId: null,
            isEditMode: false,
            trapOffset: 0,
            trapLimit: 200,
        });

        onWillStart(async () => {
            await this.loadData();
        });

        this._lastHeatmapData = null;
        this._resizeTimer = null;
        this._onResize = () => {
            if (this.state.heatmapActive) {
                this._removeHeatmapCanvas();
                clearTimeout(this._resizeTimer);
                this._resizeTimer = setTimeout(() => {
                    if (this.state.heatmapActive && this._lastHeatmapData) {
                        this._renderHeatmap(this._lastHeatmapData);
                    }
                }, 300);
            }
        };
        window.addEventListener('resize', this._onResize);

        onWillUnmount(() => {
            window.removeEventListener('resize', this._onResize);
            clearTimeout(this._resizeTimer);
        });
    }

    async loadData() {
        try {
            if (this.props.record.isNew) {
                this.state.loading = false;
                this.state.error = new Error("El plano de sede debe guardarse antes de usar el mapa interactivo.");
                return;
            }
            const recordId = this.props.record.resId;
            const data = await this.orm.call(
                this.props.record.resModel,
                "get_widget_data",
                [[recordId]],
                
            );

            if (this.state.trapOffset > 0 && this.state.data) {
                // Append traps to existing list (Load More scenario)
                data.traps = [...this.state.data.traps, ...data.traps];
            }

            this.state.data = data;
            this.state.error = null;
            this.state.loading = false;
        } catch (error) {
            this.state.error = error;
            this.state.loading = false;
            this.notification.add("Sucedió un error cargando el mapa de trampas. " + (error.message || ""), { type: "danger" });
        }
    }

    async loadMoreTraps() {
        this.state.trapOffset += this.state.trapLimit;
        await this.loadData();
    }

    onDragStart(ev, trap) {
        if (!this.state.data.can_edit || this.props.readonly || !this.state.isEditMode) {
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
        if (!this.state.data.can_edit || this.props.readonly || !this.state.isEditMode || !this.state.draggedTrapId) return;
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

    toggleEditMode() {
        this.state.isEditMode = !this.state.isEditMode;
    }

    async updateTrapPosition(trapId, pctX, pctY) {
        // Get current trap data for zone_from
        const trap = this.state.data.traps.find(t => t.id === trapId);
        
        // Open the movement wizard instead of window.prompt
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'pest.trap.movement.wizard',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_trap_id: trapId,
                default_blueprint_id: this.props.record.resId,
                default_new_x_pct: pctX,
                default_new_y_pct: pctY,
                default_zone_from_id: trap && trap.zone_id ? trap.zone_id : false,
            },
        }, {
            onClose: async () => {
                await this.loadData();
                // Force chatter refresh by reloading the form
                if (this.props.record && this.props.record.load) {
                    await this.props.record.load();
                }
            },
        });
    }

    onContainerClick(ev) {
        if (this.state.drawingMode) {
            this.onCanvasClickForZone(ev);
            return;
        }

        // Close popover if clicking outside a marker or popover
        // (these checks must happen before isEditMode guard so drag events don't get blocked)
        if (ev.target.closest('.o_blueprint_popover')) return;
        if (ev.target.closest('.blueprint-trap-marker')) return;

        // Close any open popover
        if (this.state.selectedTrapId !== null) {
            this.state.selectedTrapId = null;
            this.state.trapDetail = null;
            return;
        }

        // Only allow creating new traps in edit mode
        if (!this.state.isEditMode) return;

        if (!this.state.data.can_edit || this.props.readonly) return;

        const container = this.containerRef.el;
        if (!container) return;

        const rect = container.getBoundingClientRect();
        const pctX = Math.max(0, Math.min(100, ((ev.clientX - rect.left) / rect.width) * 100));
        const pctY = Math.max(0, Math.min(100, ((ev.clientY - rect.top) / rect.height) * 100));

        // Auto-detect zone name for the clicked position
        let defaultLocation = '';
        if (this.state.data.zones) {
            for (const zone of this.state.data.zones) {
                if (this._pointInPolygon(pctX, pctY, zone.points)) {
                    defaultLocation = zone.name;
                    break;
                }
            }
        }

        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'pest.trap',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_blueprint_id: this.props.record.resId,
                default_coord_x_pct: pctX,
                default_coord_y_pct: pctY,
                default_sede_id: this.state.data && this.state.data.sede_id ? this.state.data.sede_id : false,
                default_location: defaultLocation,
            }
        }, {
            onClose: async () => {
                const oldCount = this.state.data ? this.state.data.traps.length : 0;
                await this.loadData();
                // Force chatter refresh by reloading the form
                if (this.props.record && this.props.record.load) {
                    await this.props.record.load();
                }
                const newCount = this.state.data ? this.state.data.traps.length : 0;

                // Only ask about incident if a new trap was actually created
                if (newCount > oldCount) {
                    this.dialog.add(ConfirmationDialog, {
                        title: "Trampa Creada",
                        body: "¿Desea registrar una incidencia para esta trampa?",
                        confirm: async () => {
                            if (this.state.data && this.state.data.traps && this.state.data.traps.length > 0) {
                                const newestTrap = this.state.data.traps[this.state.data.traps.length - 1];
                                await this.onRegisterIncident(newestTrap);
                            }
                        },
                        cancel: () => {},
                    });
                }
            },
        });
    }

    async onTrapMarkerClick(ev, trap) {
        ev.stopPropagation();
        if (this.state.selectedTrapId === trap.id) {
            this.state.selectedTrapId = null;
            this.state.trapDetail = null;
            return;
        }
        this.state.selectedTrapId = trap.id;
        try {
            const detail = await this.orm.call('pest.trap', 'get_detail_data', [[trap.id]]);
            this.state.trapDetail = detail;
        } catch (e) {
            this.state.trapDetail = null;
        }
    }

    closeDetailPanel() {
        this.state.trapDetail = null;
        this.state.selectedTrapId = null;
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
                default_sede_id: trap.sede_id || (this.state.data && this.state.data.sede_id) || false,
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

    async onEditTrap(trap) {
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'pest.trap',
            res_id: trap.id,
            views: [[false, 'form']],
            target: 'new',
            context: {
                form_view_initial_mode: 'edit',
            },
        }, {
            onClose: () => this.loadData(),
        });
        this.state.selectedTrapId = null;
    }

    onKeyDown(ev) {
        if (!this.state.data) return;

        const traps = this.state.data.traps;
        if (!traps || traps.length === 0) return;

        switch (ev.key) {
            case 'Tab': {
                // Navigate between traps
                ev.preventDefault();
                const currentIdx = traps.findIndex(t => t.id === this.state.selectedTrapId);
                let nextIdx;
                if (ev.shiftKey) {
                    nextIdx = currentIdx <= 0 ? traps.length - 1 : currentIdx - 1;
                } else {
                    nextIdx = currentIdx >= traps.length - 1 ? 0 : currentIdx + 1;
                }
                const nextTrap = traps[nextIdx];
                this.state.selectedTrapId = nextTrap.id;
                this.onTrapMarkerClick({ stopPropagation: () => {} }, nextTrap);
                break;
            }
            case 'Enter':
            case ' ': {
                // Open popover for selected trap (same as click)
                ev.preventDefault();
                if (this.state.selectedTrapId) {
                    const trap = traps.find(t => t.id === this.state.selectedTrapId);
                    if (trap) {
                        this.onTrapMarkerClick({ stopPropagation: () => {} }, trap);
                    }
                }
                break;
            }
            case 'Escape': {
                // Close popover
                this.state.selectedTrapId = null;
                this.state.trapDetail = null;
                break;
            }
            case 'ArrowUp':
            case 'ArrowDown':
            case 'ArrowLeft':
            case 'ArrowRight': {
                // Move selected trap (only in edit mode)
                if (!this.state.isEditMode || !this.state.selectedTrapId) break;
                ev.preventDefault();
                const trap = traps.find(t => t.id === this.state.selectedTrapId);
                if (!trap) break;

                const step = ev.shiftKey ? 5 : 1; // Shift = bigger steps
                let newX = trap.coord_x_pct;
                let newY = trap.coord_y_pct;

                switch (ev.key) {
                    case 'ArrowUp': newY = Math.max(0, newY - step); break;
                    case 'ArrowDown': newY = Math.min(100, newY + step); break;
                    case 'ArrowLeft': newX = Math.max(0, newX - step); break;
                    case 'ArrowRight': newX = Math.min(100, newX + step); break;
                }

                // Update position locally (visual feedback)
                trap.coord_x_pct = newX;
                trap.coord_y_pct = newY;
                break;
            }
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

    toggleSidePanel() {
        this.state.sidePanelOpen = !this.state.sidePanelOpen;
    }

    onFilterTrapType(ev) {
        this.state.filterTrapType = ev.target.value || null;
        this.state.trapOffset = 0;
    }

    onFilterTrapState(ev) {
        this.state.filterTrapState = ev.target.value || null;
        this.state.trapOffset = 0;
    }

    isTrapHighlighted(trap) {
        // Individual trap highlight from side panel click
        if (this.state.highlightedTrapId === trap.id) return true;
        
        const hasTypeFilter = !!this.state.filterTrapType;
        const hasStateFilter = !!this.state.filterTrapState;
        
        // No filters active — no highlight
        if (!hasTypeFilter && !hasStateFilter) return false;
        
        const matchesType = !hasTypeFilter || ('' + trap.trap_type_id === this.state.filterTrapType);
        const matchesState = !hasStateFilter || (trap.current_state === this.state.filterTrapState);
        
        // Highlight only if ALL active filters match
        return matchesType && matchesState;
    }

    onSearchTrap(ev) {
        this.state.searchTerm = ev.target.value || '';
        this.state.trapOffset = 0;
    }

    get filteredTraps() {
        if (!this.state.data || !this.state.data.traps) return [];
        let traps = this.state.data.traps;
        if (this.state.filterTrapType) {
            traps = traps.filter(t => String(t.trap_type_id) === this.state.filterTrapType);
        }
        if (this.state.searchTerm) {
            const term = this.state.searchTerm.toLowerCase();
            traps = traps.filter(t => t.name.toLowerCase().includes(term));
        }
        if (this.state.filterTrapState) {
            traps = traps.filter(t => t.current_state === this.state.filterTrapState);
        }
        return traps;
    }

    get uniqueTrapTypes() {
        if (!this.state.data || !this.state.data.traps) return [];
        const typeMap = new Map();
        for (const trap of this.state.data.traps) {
            if (trap.trap_type_id && !typeMap.has(trap.trap_type_id)) {
                typeMap.set(trap.trap_type_id, trap.trap_type_name);
            }
        }
        return Array.from(typeMap, ([id, name]) => ({ id, name }));
    }

    onSidePanelTrapClick(trapId) {
        this.state.highlightedTrapId = trapId;
        // Auto-clear highlight after 2 seconds
        setTimeout(() => {
            if (this.state.highlightedTrapId === trapId) {
                this.state.highlightedTrapId = null;
            }
        }, 2000);
    }

    toggleIncidentBadges() {
        this.state.showIncidentBadges = !this.state.showIncidentBadges;
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

    async toggleHeatmap() {
        if (this.state.heatmapActive) {
            this.state.heatmapActive = false;
            this._removeHeatmapCanvas();
            return;
        }

        this.state.heatmapLoading = true;
        try {
            const response = await fetch(`/pest_control/blueprint/${this.props.record.resId}/heatmap_data`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: { mode: this.state.heatmapMode } }),
            });
            const data = await response.json();
            const heatmapData = data.result || data;

            if (heatmapData.points && heatmapData.points.length > 0) {
                this._renderHeatmap(heatmapData);
                this.state.heatmapActive = true;
            } else {
                this.notification.add('No hay datos de incidencias para el mapa de calor.', { type: 'info' });
            }
        } catch (error) {
            this.notification.add('Error al cargar datos del mapa de calor.', { type: 'danger' });
        }
        this.state.heatmapLoading = false;
    }

    async switchHeatmapMode() {
        this.state.heatmapMode = this.state.heatmapMode === 'organisms' ? 'incidents' : 'organisms';
        if (this.state.heatmapActive) {
            // Reload heatmap with new mode
            this._removeHeatmapCanvas();
            this.state.heatmapLoading = true;
            try {
                const response = await fetch(`/pest_control/blueprint/${this.props.record.resId}/heatmap_data`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: { mode: this.state.heatmapMode } }),
                });
                const data = await response.json();
                const heatmapData = data.result || data;
                if (heatmapData.points && heatmapData.points.length > 0) {
                    this._renderHeatmap(heatmapData);
                } else {
                    this.notification.add('No hay datos para este modo de mapa de calor.', { type: 'info' });
                    this.state.heatmapActive = false;
                }
            } catch (error) {
                this.notification.add('Error al cambiar modo del mapa de calor.', { type: 'danger' });
            }
            this.state.heatmapLoading = false;
        }
    }

    _renderHeatmap(data) {
        this._lastHeatmapData = data;
        this._removeHeatmapCanvas();

        const container = this.containerRef.el;
        if (!container) return;

        const img = container.querySelector('.blueprint-image');
        if (!img) return;

        const canvas = document.createElement('canvas');
        canvas.className = 'o_heatmap_canvas';
        canvas.width = img.offsetWidth;
        canvas.height = img.offsetHeight;
        container.appendChild(canvas);

        const heat = window.simpleheat(canvas);

        // Different gradient for each mode
        if (this.state.heatmapMode === 'incidents') {
            // Blue-purple gradient for frequency
            heat.gradient({
                0.0: 'rgba(0, 0, 255, 0)',
                0.2: 'blue',
                0.4: 'cyan',
                0.6: 'magenta',
                0.8: 'purple',
                1.0: 'red'
            });
        } else {
            // Default green-yellow-red gradient for volume
            heat.gradient({
                0.0: 'rgba(0, 255, 0, 0)',
                0.2: 'lime',
                0.4: 'yellow',
                0.6: 'orange',
                0.8: 'orangered',
                1.0: 'red'
            });
        }

        // Convert percentage coordinates to pixel coordinates
        const points = data.points.map(p => [
            (p.x / 100) * canvas.width,
            (p.y / 100) * canvas.height,
            p.value,
        ]);

        // Filter by visible trap types
        const visibleTraps = this.state.data.traps.filter(t => this.isTrapVisible(t));
        const visibleCoords = new Set(visibleTraps.map(t => `${t.coord_x_pct.toFixed(1)},${t.coord_y_pct.toFixed(1)}`));
        const filteredPoints = points.filter(p => {
            const key = `${(p[0] / canvas.width * 100).toFixed(1)},${(p[1] / canvas.height * 100).toFixed(1)}`;
            return visibleCoords.has(key);
        });

        heat.data(filteredPoints);
        const config = this.state.data && this.state.data.heatmap_config || {};
        const maxVal = this.state.heatmapMode === 'incidents'
            ? (config.inc_umbral_alto || data.max_value || 30)
            : (config.umbral_alto || data.max_value || 50);
        heat.max(maxVal);
        heat.radius(45, 35);
        heat.draw(0.05);
    }

    _removeHeatmapCanvas() {
        const container = this.containerRef.el;
        if (!container) return;
        const existing = container.querySelector('.o_heatmap_canvas');
        if (existing) existing.remove();
    }

    toggleDrawingMode() {
        if (this.state.drawingMode) {
            // Cancel drawing
            this.state.drawingMode = false;
            this.state.drawingPoints = [];
        } else {
            this.state.drawingMode = true;
            this.state.drawingPoints = [];
            this.state.selectedTrapId = null; // close any popover
        }
    }

    onCanvasClickForZone(ev) {
        if (!this.state.drawingMode) return;

        const container = this.containerRef.el;
        if (!container) return;
        const img = container.querySelector('.blueprint-image');
        if (!img) return;

        const rect = img.getBoundingClientRect();
        const x = ((ev.clientX - rect.left) / rect.width) * 100;
        const y = ((ev.clientY - rect.top) / rect.height) * 100;

        const pctX = Math.max(0, Math.min(100, x));
        const pctY = Math.max(0, Math.min(100, y));

        this.state.drawingPoints = [...this.state.drawingPoints, { x: pctX, y: pctY }];
    }

    async finishDrawingZone() {
        if (this.state.drawingPoints.length < 3) {
            this.notification.add('Un polígono necesita al menos 3 puntos.', { type: 'warning' });
            return;
        }

        const name = window.prompt('Nombre de la zona:');
        if (!name) return;

        const color = '#' + Math.floor(Math.random() * 0xFFFFFF).toString(16).padStart(6, '0') + '55';

        try {
            await this.orm.create('pest.blueprint.zone', [{
                blueprint_id: this.props.record.resId,
                name: name,
                points_data: JSON.stringify(this.state.drawingPoints),
                color: color,
            }]);
            this.notification.add('Zona "' + name + '" creada.', { type: 'success' });
            this.state.drawingMode = false;
            this.state.drawingPoints = [];
            await this.loadData();
        } catch (error) {
            this.notification.add('Error al crear zona: ' + (error.message || String(error)), { type: 'danger' });
            console.error('Zone creation error:', error);
        }
    }

    cancelDrawing() {
        this.state.drawingMode = false;
        this.state.drawingPoints = [];
    }

    onZoneClick(ev, zone) {
        ev.stopPropagation();
        this.state.selectedZoneId = this.state.selectedZoneId === zone.id ? null : zone.id;
    }

    async deleteSelectedZone() {
        if (!this.state.selectedZoneId) return;
        const zone = this.state.data.zones.find(z => z.id === this.state.selectedZoneId);
        if (!zone) return;

        const confirmed = window.confirm(`¿Eliminar zona "${zone.name}"?`);
        if (!confirmed) return;

        try {
            await this.orm.unlink('pest.blueprint.zone', [this.state.selectedZoneId]);
            this.state.selectedZoneId = null;
            await this.loadData();
            this.notification.add('Zona eliminada.', { type: 'success' });
        } catch (error) {
            this.notification.add('Error al eliminar zona.', { type: 'danger' });
        }
    }

    getZonePolygonPoints(zone) {
        // Convert [{x,y}...] to SVG polygon points string "x1,y1 x2,y2 ..."
        return zone.points.map(p => `${p.x},${p.y}`).join(' ');
    }

    getZoneCentroid(zone) {
        const pts = zone.points;
        const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length;
        const cy = pts.reduce((s, p) => s + p.y, 0) / pts.length;
        return { x: cx, y: cy };
    }

    _pointInPolygon(x, y, polygon) {
        let inside = false;
        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i].x, yi = polygon[i].y;
            const xj = polygon[j].x, yj = polygon[j].y;
            if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) {
                inside = !inside;
            }
        }
        return inside;
    }

    getPopoverPosition(trap) {
        const x = trap.coord_x_pct;
        const y = trap.coord_y_pct;
        // More aggressive thresholds
        if (y < 35) return 'bottom';
        if (y > 75) return 'top';
        if (x < 30) return 'right';
        if (x > 70) return 'left';
        return 'top';
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
