from odoo import api, fields, models


class PestTrap(models.Model):
    _name = 'pest.trap'
    _description = 'Trampa'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(
        string='ID Trampa',
        required=True,
        tracking=True,
        help='Código visible de la trampa, e.g. EDC-001',
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

    _sql_constraints = [
        (
            'name_blueprint_unique',
            'UNIQUE(name, blueprint_id)',
            'El nombre de la trampa debe ser único por plano.',
        ),
    ]

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
