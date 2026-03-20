from odoo import api, fields, models


class PestIncident(models.Model):
    _name = 'pest.incident'
    _description = 'Incidencia de Plaga'
    _order = 'date desc'

    trap_id = fields.Many2one(
        'pest.trap',
        string='Trampa',
        ondelete='set null',
        help='Dejar vacío para hallazgos sin trampa asociada.',
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
    plague_type_id = fields.Many2one(
        'pest.plague.type',
        string='Tipo de Plaga',
    )
    plague_type_custom = fields.Char(
        string='Tipo de Plaga Personalizado',
        help='Usar cuando el tipo de plaga no está en el catálogo.',
    )
    incident_type = fields.Selection(
        selection=[
            ('captura', 'Captura'),
            ('hallazgo', 'Hallazgo'),
        ],
        string='Tipo de Incidencia',
        required=True,
    )
    insect_type = fields.Selection(
        selection=[
            ('volador', 'Volador'),
            ('rastrero', 'Rastrero'),
        ],
        string='Tipo de Insecto',
    )
    organism_count = fields.Integer(
        string='Cantidad de Organismos',
        default=0,
    )
    date = fields.Datetime(
        string='Fecha',
        required=True,
        default=fields.Datetime.now,
    )
    inspector = fields.Char(string='Inspector')
    notes = fields.Text(string='Notas')
    inspection_id = fields.Many2one(
        'pest.inspection',
        string='Inspección',
        ondelete='set null',
    )

    # ── Computed ────────────────────────────────────────────────────
    plague_display_name = fields.Char(
        string='Plaga',
        compute='_compute_plague_display_name',
    )

    @api.depends('plague_type_id', 'plague_type_custom')
    def _compute_plague_display_name(self):
        for rec in self:
            if rec.plague_type_id:
                rec.plague_display_name = rec.plague_type_id.name
            elif rec.plague_type_custom:
                rec.plague_display_name = rec.plague_type_custom
            else:
                rec.plague_display_name = 'Sin especificar'
