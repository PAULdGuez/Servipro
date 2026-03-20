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
        for rec in self:
            rec.incident_count = len(rec.incident_ids)

    @api.depends('state_ids', 'state_ids.date', 'state_ids.state')
    def _compute_current_state(self):
        for rec in self:
            latest = rec.state_ids.sorted('date', reverse=True)[:1]
            rec.current_state = latest.state if latest else 'sin_registro'

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
