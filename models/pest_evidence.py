from odoo import api, fields, models


class PestEvidence(models.Model):
    _name = 'pest.evidence'
    _description = 'Evidencia Fotográfica'
    _inherit = ['mail.thread']
    _order = 'date desc'

    blueprint_id = fields.Many2one(
        'pest.blueprint',
        string='Plano',
        required=True,
        ondelete='cascade',
    )
    location = fields.Char(
        string='Ubicación',
        required=True,
    )
    description = fields.Text(string='Descripción')
    date = fields.Datetime(
        string='Fecha',
        default=fields.Datetime.now,
    )
    image_evidence = fields.Binary(
        string='Foto de Evidencia',
        attachment=True,
    )
    image_resolved = fields.Binary(
        string='Foto de Resolución',
        attachment=True,
    )
    coord_x = fields.Integer(string='Coordenada X')
    coord_y = fields.Integer(string='Coordenada Y')
    state = fields.Selection(
        selection=[
            ('pendiente', 'Pendiente'),
            ('resuelta', 'Resuelta'),
        ],
        string='Estado',
        default='pendiente',
        required=True,
        tracking=True,
    )
    resolution_date = fields.Datetime(string='Fecha de Resolución')
    supervisor_approval = fields.Boolean(
        string='Visto Bueno Supervisor',
        default=False,
    )

    # ── Actions ─────────────────────────────────────────────────────
    def action_resolve(self):
        for rec in self:
            rec.write({
                'state': 'resuelta',
                'resolution_date': fields.Datetime.now(),
            })

    def action_approve(self):
        for rec in self:
            rec.supervisor_approval = True
