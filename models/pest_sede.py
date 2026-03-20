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

    @api.depends('trap_ids', 'blueprint_ids', 'incident_ids')
    def _compute_counts(self):
        for rec in self:
            rec.trap_count = len(rec.trap_ids)
            rec.blueprint_count = len(rec.blueprint_ids)
            rec.incident_count = len(rec.incident_ids)

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
