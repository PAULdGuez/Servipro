from odoo import api, fields, models


class PestInspection(models.Model):
    _name = 'pest.inspection'
    _description = 'Inspección Técnica / Registro Técnico'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(
        string='Referencia',
        compute='_compute_name',
        store=True,
        readonly=False,
    )
    sede_id = fields.Many2one(
        'pest.sede',
        string='Sede',
        required=True,
    )
    inspector_id = fields.Many2one(
        'res.users',
        string='Inspector',
        default=lambda self: self.env.user,
    )
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.today,
    )
    incident_ids = fields.One2many(
        'pest.incident',
        'inspection_id',
        string='Incidencias',
    )
    notes = fields.Html(string='Observaciones')
    state = fields.Selection(
        selection=[
            ('borrador', 'Borrador'),
            ('en_progreso', 'En Progreso'),
            ('completada', 'Completada'),
        ],
        string='Estado',
        default='borrador',
        required=True,
        tracking=True,
    )

    @api.depends('sede_id', 'date')
    def _compute_name(self):
        for rec in self:
            sede_name = rec.sede_id.name or ''
            date_str = fields.Date.to_string(rec.date) if rec.date else ''
            rec.name = f'INSP - {sede_name} - {date_str}'

    # ── Actions ─────────────────────────────────────────────────────
    def action_start(self):
        for rec in self:
            rec.state = 'en_progreso'

    def action_complete(self):
        for rec in self:
            rec.state = 'completada'
