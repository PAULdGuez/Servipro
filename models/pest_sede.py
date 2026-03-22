from odoo import api, fields, models


class PestSede(models.Model):
    _name = 'pest.sede'
    _description = 'Sede / Planta'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Nombre',
        required=True,
        tracking=True,
    )
    street = fields.Char(string='Dirección')
    city = fields.Char(string='Ciudad')
    country_id = fields.Many2one(
        'res.country',
        string='País',
    )
    active = fields.Boolean(default=True)
    state = fields.Selection(
        selection=[
            ('active', 'Activa'),
            ('inactive', 'Inactiva'),
        ],
        string='Estado',
        default='active',
        required=True,
        tracking=True,
    )

    # ── One2many relations ──────────────────────────────────────────
    blueprint_ids = fields.One2many(
        'pest.blueprint',
        'sede_id',
        string='Planos',
    )
    trap_ids = fields.One2many(
        'pest.trap',
        'sede_id',
        string='Trampas',
    )
    incident_ids = fields.One2many(
        'pest.incident',
        'sede_id',
        string='Incidencias',
    )
    complaint_ids = fields.One2many(
        'pest.complaint',
        'sede_id',
        string='Quejas',
    )

    # ── Computed counts ─────────────────────────────────────────────
    trap_count = fields.Integer(
        string='Nº Trampas',
        compute='_compute_counts',
        store=True,
    )
    blueprint_count = fields.Integer(
        string='Nº Planos',
        compute='_compute_counts',
        store=True,
    )
    incident_count = fields.Integer(
        string='Nº Incidencias',
        compute='_compute_counts',
        store=True,
    )

    @api.depends('blueprint_ids', 'trap_ids', 'incident_ids')
    def _compute_counts(self):
        for rec in self:
            rec.trap_count = 0
            rec.blueprint_count = 0
            rec.incident_count = 0

        if not self.ids:
            return

        trap_data = self.env['pest.trap']._read_group(
            [('sede_id', 'in', self.ids)], ['sede_id'], ['__count'])
        bp_data = self.env['pest.blueprint']._read_group(
            [('sede_id', 'in', self.ids)], ['sede_id'], ['__count'])
        inc_data = self.env['pest.incident']._read_group(
            [('sede_id', 'in', self.ids)], ['sede_id'], ['__count'])

        trap_counts = {sede.id: count for sede, count in trap_data}
        bp_counts = {sede.id: count for sede, count in bp_data}
        inc_counts = {sede.id: count for sede, count in inc_data}

        for rec in self:
            rec.trap_count = trap_counts.get(rec.id, 0)
            rec.blueprint_count = bp_counts.get(rec.id, 0)
            rec.incident_count = inc_counts.get(rec.id, 0)

    # ── Actions ─────────────────────────────────────────────────────
    def action_view_traps(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Trampas',
            'res_model': 'pest.trap',
            'view_mode': 'list,form',
            'domain': [('sede_id', '=', self.id)],
            'context': {'default_sede_id': self.id},
        }

    def action_view_blueprints(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Planos',
            'res_model': 'pest.blueprint',
            'view_mode': 'list,form',
            'domain': [('sede_id', '=', self.id)],
            'context': {'default_sede_id': self.id},
        }

    def action_view_incidents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Incidencias',
            'res_model': 'pest.incident',
            'view_mode': 'list,form',
            'domain': [('sede_id', '=', self.id)],
            'context': {'default_sede_id': self.id},
        }

    # ── Dashboard ────────────────────────────────────────────────────
    def get_dashboard_data(self, params=None):
        """Return aggregated data for 14 sede charts in Chart.js format."""
        self.ensure_one()
        params = params or {}
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        blueprint_id = params.get('blueprint_id')

        # Base domain for incidents in this sede
        domain = [('sede_id', '=', self.id)]
        if blueprint_id:
            domain.append(('blueprint_id', '=', blueprint_id))
        import logging
        _logger = logging.getLogger(__name__)

        if date_from:
            domain.append(('date', '>=', date_from + ' 00:00:00' if isinstance(date_from, str) and len(date_from) == 10 else date_from))
        if date_to:
            domain.append(('date', '<=', date_to + ' 23:59:59' if isinstance(date_to, str) and len(date_to) == 10 else date_to))

        _logger.info('Dashboard params: date_from=%s, date_to=%s, blueprint_id=%s, domain=%s', date_from, date_to, blueprint_id, domain)

        Incident = self.env['pest.incident']
        Trap = self.env['pest.trap']
        PlagueType = self.env['pest.plague.type']

        # Helper: generate consistent colors
        colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#E7E9ED', '#8BC34A', '#FF5722', '#607D8B',
            '#E91E63', '#00BCD4', '#FFC107', '#795548', '#9C27B0',
            '#3F51B5', '#009688', '#CDDC39',
        ]

        def get_color(idx):
            return colors[idx % len(colors)]

        result = {}

        # ── Chart 1: Plagas por Mes (grouped bar) ──
        try:
            data = Incident._read_group(
                domain,
                ['plague_type_id', 'date:month'],
                ['organism_count:sum'],
            )
            months = sorted(set(str(d[1]) for d in data if d[1]))
            plague_types = {}
            for plague, month, total in data:
                if not plague or not month:
                    continue
                pname = plague.name if plague else 'Otro'
                if pname not in plague_types:
                    plague_types[pname] = {}
                plague_types[pname][str(month)] = total or 0

            datasets = []
            for idx, (pname, month_data) in enumerate(plague_types.items()):
                datasets.append({
                    'label': pname,
                    'data': [month_data.get(m, 0) for m in months],
                    'backgroundColor': get_color(idx),
                })
            result['plagas_por_mes'] = {'labels': months, 'datasets': datasets}
        except Exception:
            result['plagas_por_mes'] = {'labels': [], 'datasets': []}

        # ── Chart 2: Tipo Incidencia Pie ──
        try:
            data = Incident._read_group(domain, ['incident_type'], ['__count'])
            labels = [str(d[0] or 'Sin tipo') for d in data]
            counts = [d[1] for d in data]
            result['tipo_incidencia_pie'] = {
                'labels': labels,
                'datasets': [{'data': counts, 'backgroundColor': [get_color(i) for i in range(len(labels))]}],
            }
        except Exception:
            result['tipo_incidencia_pie'] = {'labels': [], 'datasets': []}

        # ── Chart 4: Areas Mayor Incidencia (doughnut) ──
        try:
            # Group incidents by trap's zone
            data = Incident._read_group(domain, ['trap_id'], ['organism_count:sum'])
            zone_totals = {}
            for trap, total in data:
                if trap and trap.zone_id:
                    zname = trap.zone_id.name
                elif trap and trap.location:
                    zname = trap.location
                else:
                    zname = 'Sin ubicación'
                zone_totals[zname] = zone_totals.get(zname, 0) + (total or 0)

            sorted_zones = sorted(zone_totals.items(), key=lambda x: x[1], reverse=True)[:10]
            labels = [z[0] for z in sorted_zones]
            values = [z[1] for z in sorted_zones]
            result['areas_mayor_incidencia'] = {
                'labels': labels,
                'datasets': [{'data': values, 'backgroundColor': [get_color(i) for i in range(len(labels))]}],
            }
        except Exception:
            result['areas_mayor_incidencia'] = {'labels': [], 'datasets': []}

        # ── Chart 5: Trampas Mayor Captura (bar, top 10) ──
        try:
            data = Incident._read_group(domain, ['trap_id'], ['organism_count:sum'])
            trap_totals = [(trap.name if trap else '?', total or 0) for trap, total in data if trap]
            trap_totals.sort(key=lambda x: x[1], reverse=True)
            top10 = trap_totals[:10]
            result['trampas_mayor_captura'] = {
                'labels': [t[0] for t in top10],
                'datasets': [{'label': 'Capturas', 'data': [t[1] for t in top10], 'backgroundColor': '#36A2EB'}],
            }
        except Exception:
            result['trampas_mayor_captura'] = {'labels': [], 'datasets': []}

        # ── Chart 6: Areas Capturas por Plaga (stacked bar) ──
        try:
            data = Incident._read_group(domain, ['trap_id', 'plague_type_id'], ['organism_count:sum'])
            zones = {}
            plagues_set = set()
            for trap, plague, total in data:
                if not trap:
                    continue
                zname = trap.zone_id.name if trap.zone_id else (trap.location or 'Sin ubicación')
                pname = plague.name if plague else 'Otro'
                plagues_set.add(pname)
                if zname not in zones:
                    zones[zname] = {}
                zones[zname][pname] = zones[zname].get(pname, 0) + (total or 0)

            zone_labels = list(zones.keys())
            plague_list = sorted(plagues_set)
            datasets = []
            for idx, pname in enumerate(plague_list):
                datasets.append({
                    'label': pname,
                    'data': [zones.get(z, {}).get(pname, 0) for z in zone_labels],
                    'backgroundColor': get_color(idx),
                })
            result['areas_capturas_por_plaga'] = {
                'labels': zone_labels,
                'datasets': datasets,
            }
        except Exception:
            result['areas_capturas_por_plaga'] = {'labels': [], 'datasets': []}

        # ── Chart 7: Incidencias por Tipo y Mes (grouped bar) ──
        try:
            data = Incident._read_group(domain, ['incident_type', 'date:month'], ['__count'])
            months = sorted(set(str(d[1]) for d in data if d[1]))
            types = {}
            for itype, month, count in data:
                if not month:
                    continue
                tname = str(itype or 'Sin tipo')
                if tname not in types:
                    types[tname] = {}
                types[tname][str(month)] = count

            datasets = []
            type_colors = {'captura': '#36A2EB', 'hallazgo': '#FF6384'}
            for idx, (tname, month_data) in enumerate(types.items()):
                datasets.append({
                    'label': tname,
                    'data': [month_data.get(m, 0) for m in months],
                    'backgroundColor': type_colors.get(tname, get_color(idx)),
                })
            result['incidencias_tipo_mes'] = {'labels': months, 'datasets': datasets}
        except Exception:
            result['incidencias_tipo_mes'] = {'labels': [], 'datasets': []}

        # ── Chart 8: Trampas por Ubicacion (bar) ──
        try:
            trap_domain = [('sede_id', '=', self.id), ('active', '=', True)]
            if blueprint_id:
                trap_domain.append(('blueprint_id', '=', blueprint_id))
            traps = Trap.search(trap_domain)
            zone_counts = {}
            for t in traps:
                zname = t.zone_id.name if t.zone_id else (t.location or 'Sin ubicación')
                zone_counts[zname] = zone_counts.get(zname, 0) + 1
            sorted_zones = sorted(zone_counts.items(), key=lambda x: x[1], reverse=True)
            result['trampas_por_ubicacion'] = {
                'labels': [z[0] for z in sorted_zones],
                'datasets': [{'label': 'Trampas', 'data': [z[1] for z in sorted_zones], 'backgroundColor': '#4BC0C0'}],
            }
        except Exception:
            result['trampas_por_ubicacion'] = {'labels': [], 'datasets': []}

        # ── Helper for voladores/rastreros ──
        def get_category_charts(category):
            cat_domain = domain + [('plague_type_id.category', '=', category)]
            charts = {}

            # Pie: distribution by plague type
            try:
                data = Incident._read_group(cat_domain, ['plague_type_id'], ['organism_count:sum'])
                labels = [d[0].name if d[0] else 'Otro' for d in data]
                values = [d[1] or 0 for d in data]
                charts['plagas'] = {
                    'labels': labels,
                    'datasets': [{'data': values, 'backgroundColor': [get_color(i) for i in range(len(labels))]}],
                }
            except Exception:
                charts['plagas'] = {'labels': [], 'datasets': []}

            # Bar: top 10 traps
            try:
                data = Incident._read_group(cat_domain, ['trap_id'], ['organism_count:sum'])
                trap_totals = [(t.name if t else '?', v or 0) for t, v in data if t]
                trap_totals.sort(key=lambda x: x[1], reverse=True)
                top10 = trap_totals[:10]
                charts['trampas_captura'] = {
                    'labels': [t[0] for t in top10],
                    'datasets': [{'label': 'Capturas', 'data': [t[1] for t in top10], 'backgroundColor': '#FF9F40'}],
                }
            except Exception:
                charts['trampas_captura'] = {'labels': [], 'datasets': []}

            # Stacked bar: areas by plague
            try:
                data = Incident._read_group(cat_domain, ['trap_id', 'plague_type_id'], ['organism_count:sum'])
                zones = {}
                plagues_set = set()
                for trap, plague, total in data:
                    if not trap:
                        continue
                    zname = trap.zone_id.name if trap.zone_id else (trap.location or 'Sin ubicación')
                    pname = plague.name if plague else 'Otro'
                    plagues_set.add(pname)
                    if zname not in zones:
                        zones[zname] = {}
                    zones[zname][pname] = zones[zname].get(pname, 0) + (total or 0)

                zone_labels = list(zones.keys())
                plague_list = sorted(plagues_set)
                datasets = []
                for idx, pname in enumerate(plague_list):
                    datasets.append({
                        'label': pname,
                        'data': [zones.get(z, {}).get(pname, 0) for z in zone_labels],
                        'backgroundColor': get_color(idx),
                    })
                charts['areas_captura'] = {'labels': zone_labels, 'datasets': datasets}
            except Exception:
                charts['areas_captura'] = {'labels': [], 'datasets': []}

            return charts

        # ── Charts 9-11: Voladores ──
        vol = get_category_charts('volador')
        result['plagas_voladores'] = vol.get('plagas', {'labels': [], 'datasets': []})
        result['trampas_captura_voladores'] = vol.get('trampas_captura', {'labels': [], 'datasets': []})
        result['areas_captura_voladores'] = vol.get('areas_captura', {'labels': [], 'datasets': []})

        # ── Charts 12-14: Rastreros ──
        ras = get_category_charts('rastrero')
        result['plagas_rastreros'] = ras.get('plagas', {'labels': [], 'datasets': []})
        result['trampas_captura_rastreros'] = ras.get('trampas_captura', {'labels': [], 'datasets': []})
        result['areas_captura_rastreros'] = ras.get('areas_captura', {'labels': [], 'datasets': []})

        # Ensure all chart keys exist (even if empty)
        all_keys = [
            'plagas_por_mes', 'tipo_incidencia_pie', 'areas_mayor_incidencia',
            'trampas_mayor_captura', 'areas_capturas_por_plaga', 'incidencias_tipo_mes',
            'trampas_por_ubicacion', 'plagas_voladores', 'trampas_captura_voladores',
            'areas_captura_voladores', 'plagas_rastreros', 'trampas_captura_rastreros',
            'areas_captura_rastreros',
        ]
        for key in all_keys:
            if key not in result:
                result[key] = {'labels': [], 'datasets': []}

        return result

    def get_quejas_dashboard_data(self, params=None):
        self.ensure_one()
        params = params or {}
        date_from = params.get('date_from')
        date_to = params.get('date_to')

        domain = [('sede_id', '=', self.id)]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        Complaint = self.env['pest.complaint']
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#E7E9ED', '#8BC34A']
        result = {}

        # Chart 15: Quejas por Semana (line — current year vs previous)
        try:
            from datetime import datetime, timedelta
            import calendar
            now = datetime.now()
            current_year = now.year
            prev_year = current_year - 1

            # Current year by week
            curr_domain = domain + [('date', '>=', f'{current_year}-01-01'), ('date', '<=', f'{current_year}-12-31')]
            curr_complaints = Complaint.search(curr_domain)
            curr_weeks = {}
            for c in curr_complaints:
                if c.date:
                    week = c.date.isocalendar()[1]
                    curr_weeks[week] = curr_weeks.get(week, 0) + 1

            # Previous year
            prev_domain = domain + [('date', '>=', f'{prev_year}-01-01'), ('date', '<=', f'{prev_year}-12-31')]
            prev_complaints = Complaint.search(prev_domain)
            prev_weeks = {}
            for c in prev_complaints:
                if c.date:
                    week = c.date.isocalendar()[1]
                    prev_weeks[week] = prev_weeks.get(week, 0) + 1

            weeks = list(range(1, 53))
            result['quejas_por_semana'] = {
                'labels': [f'S{w}' for w in weeks],
                'datasets': [
                    {'label': str(current_year), 'data': [curr_weeks.get(w, 0) for w in weeks], 'borderColor': '#36A2EB', 'fill': False},
                    {'label': str(prev_year), 'data': [prev_weeks.get(w, 0) for w in weeks], 'borderColor': '#FF6384', 'fill': False},
                ],
            }
        except Exception:
            result['quejas_por_semana'] = {'labels': [], 'datasets': []}

        # Chart 16: Lineas Afectadas (pie)
        try:
            complaints = Complaint.search(domain)
            lines = {}
            for c in complaints:
                line = c.production_lines or 'Sin línea'
                lines[line] = lines.get(line, 0) + 1
            labels = list(lines.keys())
            result['lineas_afectadas'] = {
                'labels': labels,
                'datasets': [{'data': list(lines.values()), 'backgroundColor': [colors[i % len(colors)] for i in range(len(labels))]}],
            }
        except Exception:
            result['lineas_afectadas'] = {'labels': [], 'datasets': []}

        # Chart 17: Quejas por Ano (bar)
        try:
            complaints = Complaint.search([('sede_id', '=', self.id)])
            years = {}
            for c in complaints:
                if c.date:
                    y = c.date.year
                    years[y] = years.get(y, 0) + 1
            sorted_years = sorted(years.items())
            result['quejas_por_ano'] = {
                'labels': [str(y[0]) for y in sorted_years],
                'datasets': [{'label': 'Quejas', 'data': [y[1] for y in sorted_years], 'backgroundColor': '#36A2EB'}],
            }
        except Exception:
            result['quejas_por_ano'] = {'labels': [], 'datasets': []}

        # Chart 18: Tipo de Insecto (pie)
        try:
            complaints = Complaint.search(domain)
            insects = {}
            for c in complaints:
                ins = c.insect or 'Sin especificar'
                insects[ins] = insects.get(ins, 0) + 1
            labels = list(insects.keys())
            result['tipo_insecto'] = {
                'labels': labels,
                'datasets': [{'data': list(insects.values()), 'backgroundColor': [colors[i % len(colors)] for i in range(len(labels))]}],
            }
        except Exception:
            result['tipo_insecto'] = {'labels': [], 'datasets': []}

        # Chart 19: Clasificacion (bar)
        try:
            class_colors = {'critico': '#dc3545', 'alto': '#fd7e14', 'medio': '#ffc107', 'bajo': '#28a745'}
            data = Complaint._read_group(domain, ['classification'], ['__count'])
            labels = [str(d[0] or 'Sin clasificar') for d in data]
            counts = [d[1] for d in data]
            bg_colors = [class_colors.get(str(d[0]), '#6c757d') for d in data]
            result['quejas_clasificacion'] = {
                'labels': labels,
                'datasets': [{'label': 'Quejas', 'data': counts, 'backgroundColor': bg_colors}],
            }
        except Exception:
            result['quejas_clasificacion'] = {'labels': [], 'datasets': []}

        # Chart 20: Estado organismo (doughnut)
        try:
            complaints = Complaint.search(domain)
            states = {}
            for c in complaints:
                st = c.insect_state or 'Sin especificar'
                states[st] = states.get(st, 0) + 1
            labels = list(states.keys())
            result['estado_organismo'] = {
                'labels': labels,
                'datasets': [{'data': list(states.values()), 'backgroundColor': ['#28a745', '#dc3545', '#6c757d'][:len(labels)]}],
            }
        except Exception:
            result['estado_organismo'] = {'labels': [], 'datasets': []}

        # Chart 21: Estado quejas (doughnut)
        try:
            data = Complaint._read_group(domain, ['state'], ['__count'])
            labels = [str(d[0] or 'Sin estado') for d in data]
            counts = [d[1] for d in data]
            state_colors = {'pendiente': '#ffc107', 'en_proceso': '#17a2b8', 'resuelta': '#28a745', 'cerrada': '#6c757d'}
            bg = [state_colors.get(str(d[0]), '#6c757d') for d in data]
            result['estado_quejas'] = {
                'labels': labels,
                'datasets': [{'data': counts, 'backgroundColor': bg}],
            }
        except Exception:
            result['estado_quejas'] = {'labels': [], 'datasets': []}

        all_keys = [
            'quejas_por_semana', 'lineas_afectadas', 'quejas_por_ano',
            'tipo_insecto', 'quejas_clasificacion', 'estado_organismo', 'estado_quejas',
        ]
        for key in all_keys:
            if key not in result:
                result[key] = {'labels': [], 'datasets': []}

        return result

    def get_ventas_dashboard_data(self, params=None):
        self.ensure_one()
        params = params or {}
        result = {}

        try:
            SaleOrder = self.env['sale.order']
        except Exception:
            # sale module not installed
            return {
                'ventas_por_sede': {'labels': [], 'datasets': []},
                'ventas_por_usuario': {'labels': [], 'datasets': []},
            }

        # Check if sede_id field exists on sale.order
        if 'sede_id' not in SaleOrder._fields:
            return {
                'ventas_por_sede': {'labels': [], 'datasets': []},
                'ventas_por_usuario': {'labels': [], 'datasets': []},
            }

        domain = []
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        if date_from:
            domain.append(('date_order', '>=', date_from))
        if date_to:
            domain.append(('date_order', '<=', date_to))

        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']

        # Chart 22: Ventas por Sede
        try:
            data = SaleOrder._read_group(domain + [('sede_id', '!=', False)], ['sede_id'], ['__count'])
            labels = [d[0].name if d[0] else 'Sin sede' for d in data]
            counts = [d[1] for d in data]
            result['ventas_por_sede'] = {
                'labels': labels,
                'datasets': [{'label': 'Ventas', 'data': counts, 'backgroundColor': [colors[i % len(colors)] for i in range(len(labels))]}],
            }
        except Exception:
            result['ventas_por_sede'] = {'labels': [], 'datasets': []}

        # Chart 23: Ventas por Usuario
        try:
            data = SaleOrder._read_group(domain, ['user_id'], ['__count'])
            labels = [d[0].name if d[0] else 'Sin usuario' for d in data]
            counts = [d[1] for d in data]
            result['ventas_por_usuario'] = {
                'labels': labels,
                'datasets': [{'label': 'Ventas', 'data': counts, 'backgroundColor': [colors[i % len(colors)] for i in range(len(labels))]}],
            }
        except Exception:
            result['ventas_por_usuario'] = {'labels': [], 'datasets': []}

        all_keys = ['ventas_por_sede', 'ventas_por_usuario']
        for key in all_keys:
            if key not in result:
                result[key] = {'labels': [], 'datasets': []}

        return result
