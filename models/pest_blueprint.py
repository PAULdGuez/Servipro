from odoo import api, fields, models


class PestBlueprint(models.Model):
    _name = 'pest.blueprint'
    _description = 'Plano de Planta'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(
        string='Nombre del Plano',
        required=True,
    )
    sede_id = fields.Many2one(
        'pest.sede',
        string='Sede',
        required=True,
        ondelete='cascade',
    )
    description = fields.Text(string='Descripción')
    image = fields.Binary(
        string='Imagen del Plano',
        attachment=True,
    )
    image_filename = fields.Char(string='Nombre del Archivo')
    active = fields.Boolean(default=True)

    # ── Relations ───────────────────────────────────────────────────
    trap_ids = fields.One2many(
        'pest.trap',
        'blueprint_id',
        string='Trampas',
    )
    evidence_ids = fields.One2many(
        'pest.evidence',
        'blueprint_id',
        string='Evidencias',
    )

    # ── Computed ────────────────────────────────────────────────────
    incident_ids = fields.One2many(
        'pest.incident',
        'blueprint_id',
        string='Incidencias',
    )
    trap_count = fields.Integer(
        string='Nº Trampas',
        compute='_compute_trap_count',
        store=True,
    )

    # JSON payload for frontend rendering (zones, renderedWidth, etc.)
    state_data = fields.Text(string='Datos del Estado JSON')

    @api.depends('trap_ids')
    def _compute_trap_count(self):
        for rec in self:
            rec.trap_count = len(rec.trap_ids)
