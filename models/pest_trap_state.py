from odoo import fields, models


class PestTrapState(models.Model):
    _name = 'pest.trap.state'
    _description = 'Historial de Estado de Trampa'
    _order = 'date desc'

    trap_id = fields.Many2one(
        'pest.trap',
        string='Trampa',
        required=True,
        ondelete='cascade',
    )
    blueprint_id = fields.Many2one(
        'pest.blueprint',
        string='Plano',
    )
    sede_id = fields.Many2one(
        'pest.sede',
        string='Sede',
    )
    state = fields.Selection(
        selection=[
            ('funciona', 'Funciona'),
            ('en_reparacion', 'En Reparación'),
            ('no_funciona', 'No Funciona'),
            ('sin_registro', 'Sin Registro'),
        ],
        string='Estado',
        required=True,
    )
    observations = fields.Text(string='Observaciones')
    date = fields.Datetime(
        string='Fecha',
        default=fields.Datetime.now,
        index=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Registrado por',
        default=lambda self: self.env.user,
    )
