from odoo import api, fields, models


class PestTrap(models.Model):
    _name = 'pest.trap'
    _description = 'Trampa'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(
        string='ID Trampa',
        tracking=True,
        help='Se genera automáticamente si se deja vacío. Ej: EDC-001',
    )
    sede_id = fields.Many2one(
        'pest.sede',
        string='Sede',
        required=True,
        ondelete='cascade',
    )
    blueprint_id = fields.Many2one(
        'pest.blueprint',
        string='Plano',
        ondelete='set null',
    )
    trap_type_id = fields.Many2one(
        'pest.trap.type',
        string='Tipo de Trampa',
        required=True,
    )
    location = fields.Char(string='Ubicación / Zona')
    zone_id = fields.Many2one('pest.zone', string='Ubicación')
    coord_x = fields.Float(
        string='Coordenada X',
        digits=(10, 2),
    )
    coord_y = fields.Float(
        string='Coordenada Y',
        digits=(10, 2),
    )
    coord_x_pct = fields.Float(
        string='Coordenada X (%)',
        help='Porcentaje de la posición X (0.0 a 100.0)',
    )
    coord_y_pct = fields.Float(
        string='Coordenada Y (%)',
        help='Porcentaje de la posición Y (0.0 a 100.0)',
    )
    installation_date = fields.Date(
        string='Fecha de Instalación',
        default=fields.Date.today,
    )
    active = fields.Boolean(default=True)

    # ── Relations ───────────────────────────────────────────────────
    incident_ids = fields.One2many(
        'pest.incident',
        'trap_id',
        string='Incidencias',
    )
    state_ids = fields.One2many(
        'pest.trap.state',
        'trap_id',
        string='Historial de Estado',
    )
    movement_ids = fields.One2many(
        'pest.trap.movement',
        'trap_id',
        string='Historial de Movimientos',
    )

    # ── Computed ────────────────────────────────────────────────────
    incident_count = fields.Integer(
        string='Nº Incidencias',
        compute='_compute_incident_count',
    )
    current_state = fields.Selection(
        selection=[
            ('funciona', 'Funciona'),
            ('en_reparacion', 'En Reparación'),
            ('no_funciona', 'No Funciona'),
            ('sin_registro', 'Sin Registro'),
        ],
        string='Estado Actual',
        compute='_compute_current_state',
        store=True,
    )
    initial_state = fields.Selection(
        selection=[
            ('funciona', 'Funciona'),
            ('en_reparacion', 'En Reparación'),
            ('no_funciona', 'No Funciona'),
        ],
        string='Estado Inicial',
        store=False,
    )

    _sql_constraints = [
        (
            'name_blueprint_unique',
            'UNIQUE(name, blueprint_id)',
            'El nombre de la trampa debe ser único por plano.',
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        # Extract initial_state before passing to super (it's not stored)
        initial_states = []
        for vals in vals_list:
            initial_states.append(vals.pop('initial_state', None))
            if not vals.get('name') and vals.get('trap_type_id') and vals.get('blueprint_id'):
                trap_type = self.env['pest.trap.type'].browse(vals['trap_type_id'])
                prefix = trap_type.code or 'TRP'
                seq_code = 'pest.trap.%s.%s' % (vals['blueprint_id'], vals['trap_type_id'])
                sequence = self.env['ir.sequence'].sudo().search([('code', '=', seq_code)], limit=1)
                if not sequence:
                    sequence = self.env['ir.sequence'].sudo().create({
                        'name': 'Trampa %s - Plano %s' % (prefix, vals['blueprint_id']),
                        'code': seq_code,
                        'prefix': '%s-' % prefix,
                        'padding': 3,
                        'number_increment': 1,
                    })
                vals['name'] = sequence.next_by_code(seq_code)
            elif not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('pest.trap.generic') or 'TRP-NEW'
        records = super().create(vals_list)
        # Create initial state records if provided and log to blueprint chatter
        for rec, initial in zip(records, initial_states):
            if initial:
                self.env['pest.trap.state'].create({
                    'trap_id': rec.id,
                    'blueprint_id': rec.blueprint_id.id if rec.blueprint_id else False,
                    'sede_id': rec.sede_id.id if rec.sede_id else False,
                    'state': initial,
                    'observations': 'Estado inicial al crear trampa',
                })
            if rec.blueprint_id:
                rec.blueprint_id.message_post(
                    body='Nueva trampa creada: %s (%s)' % (
                        rec.name,
                        rec.trap_type_id.name if rec.trap_type_id else 'Sin tipo',
                    ),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
        return records

    @api.depends('incident_ids')
    def _compute_incident_count(self):
        if not self.ids:
            for rec in self:
                rec.incident_count = 0
            return

        incident_data = self.env['pest.incident']._read_group(
            [('trap_id', 'in', self.ids)],
            ['trap_id'],
            ['__count'],
        )
        count_map = {trap.id: count for trap, count in incident_data}
        for rec in self:
            rec.incident_count = count_map.get(rec.id, 0)

    @api.depends('state_ids.date', 'state_ids.state')
    def _compute_current_state(self):
        if not self.ids:
            for rec in self:
                rec.current_state = 'sin_registro'
            return
            
        self.env.cr.execute("""
            SELECT DISTINCT ON (trap_id) trap_id, state 
            FROM pest_trap_state 
            WHERE trap_id IN %s 
            ORDER BY trap_id, date DESC, id DESC
        """, (tuple(self.ids),))
        
        state_map = {row[0]: row[1] for row in self.env.cr.fetchall()}
        
        for rec in self:
            rec.current_state = state_map.get(rec.id, 'sin_registro')

    def action_move_to_from_widget(self, new_x_pct, new_y_pct, comment=''):
        from odoo.exceptions import UserError
        for trap in self:
            if not isinstance(new_x_pct, (int, float)) or not isinstance(new_y_pct, (int, float)):
                raise UserError('Las coordenadas deben ser números.')
            if not (0.0 <= new_x_pct <= 100.0) or not (0.0 <= new_y_pct <= 100.0):
                raise UserError('Las coordenadas porcentuales deben estar entre 0.0 y 100.0')

            old_x = trap.coord_x_pct
            old_y = trap.coord_y_pct

            trap.write({
                'coord_x_pct': new_x_pct,
                'coord_y_pct': new_y_pct,
            })

            trap.env['pest.trap.movement'].create({
                'trap_id': trap.id,
                'blueprint_id': trap.blueprint_id.id,
                'movement_type': 'widget_drag',
                'x_from_pct': old_x,
                'y_from_pct': old_y,
                'x_to_pct': new_x_pct,
                'y_to_pct': new_y_pct,
                'comment': comment or '',
            })

            # Auto-detect zone for new position
            if trap.blueprint_id:
                zone_name = trap.env['pest.blueprint.zone'].find_zone_for_coords(
                    trap.blueprint_id.id, new_x_pct, new_y_pct
                )
                if zone_name:
                    trap.location = zone_name

    def get_detail_data(self):
        self.ensure_one()
        incidents = self.env['pest.incident'].search_read(
            [('trap_id', '=', self.id)],
            ['date', 'plague_type_id', 'incident_type', 'organism_count', 'notes'],
            limit=10, order='date desc')
        states = self.env['pest.trap.state'].search_read(
            [('trap_id', '=', self.id)],
            ['date', 'state', 'observations', 'user_id'],
            limit=5, order='date desc')

        # Get totals
        total_incidents = self.env['pest.incident'].search_count([('trap_id', '=', self.id)])
        total_organisms = 0
        try:
            org_data = self.env['pest.incident']._read_group(
                [('trap_id', '=', self.id)],
                [],
                ['organism_count:sum'],
            )
            if org_data:
                total_organisms = org_data[0][0] or 0
        except Exception:
            pass

        return {
            'trap_name': self.name or '',
            'trap_type': self.trap_type_id.name if self.trap_type_id else '',
            'location': self.location or '',
            'current_state': self.current_state or 'sin_registro',
            'total_incidents': total_incidents,
            'total_organisms': total_organisms,
            'incidents': [{
                'date': str(i.get('date') or ''),
                'plague': i['plague_type_id'][1] if i.get('plague_type_id') else '',
                'type': i.get('incident_type', ''),
                'count': i.get('organism_count', 0),
                'notes': i.get('notes', ''),
            } for i in incidents],
            'states': [{
                'date': str(s.get('date') or ''),
                'state': s.get('state', ''),
                'observations': s.get('observations', ''),
                'user': s['user_id'][1] if s.get('user_id') else '',
            } for s in states],
        }

    def action_view_incidents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Incidencias',
            'res_model': 'pest.incident',
            'view_mode': 'list,form',
            'domain': [('trap_id', '=', self.id)],
            'context': {'default_trap_id': self.id, 'default_sede_id': self.sede_id.id},
        }
