from odoo import api, fields, models


class PestComplaint(models.Model):
    _name = 'pest.complaint'
    _description = 'Queja / Reclamo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(
        string='Referencia',
        readonly=True,
        default='Nuevo',
        copy=False,
    )
    sede_id = fields.Many2one(
        'pest.sede',
        string='Sede',
        required=True,
    )
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.today,
    )
    insect = fields.Char(
        string='Insecto Reportado',
        required=True,
    )
    location = fields.Char(
        string='Ubicación',
        required=True,
    )
    production_lines = fields.Char(
        string='Líneas Afectadas',
    )
    attachment = fields.Binary(
        string='Archivo Adjunto',
        attachment=True,
    )
    attachment_filename = fields.Char(
        string='Nombre del Archivo',
    )
    classification = fields.Selection(
        [
            ('critico', 'Crítico'),
            ('alto', 'Alto'),
            ('medio', 'Medio'),
            ('bajo', 'Bajo'),
        ],
        string='Clasificación',
        required=True,
    )
    insect_state = fields.Selection(
        [
            ('vivo', 'Vivo'),
            ('muerto', 'Muerto'),
        ],
        string='Estado del Insecto',
    )
    state = fields.Selection(
        [
            ('pendiente', 'Pendiente'),
            ('en_proceso', 'En Proceso'),
            ('resuelta', 'Resuelta'),
            ('cerrada', 'Cerrada'),
        ],
        string='Estado',
        default='pendiente',
        required=True,
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('pest.complaint') or 'Nuevo'
        return super().create(vals_list)

    # ── Actions ─────────────────────────────────────────────────────
    def action_resolve(self):
        for rec in self:
            rec.state = 'resuelta'

    def action_close(self):
        for rec in self:
            rec.state = 'cerrada'
