from odoo import fields, models


class PestTrapMovement(models.Model):
    _name = 'pest.trap.movement'
    _description = 'Historial de Movimiento de Trampa'
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
    movement_type = fields.Char(string='Tipo')
    zone_from = fields.Char(string='Zona Anterior')
    zone_to = fields.Char(string='Zona Nueva')
    x_from = fields.Float(
        string='X Anterior',
        digits=(10, 2),
    )
    y_from = fields.Float(
        string='Y Anterior',
        digits=(10, 2),
    )
    x_to = fields.Float(
        string='X Nueva',
        digits=(10, 2),
    )
    y_to = fields.Float(
        string='Y Nueva',
        digits=(10, 2),
    )
    x_from_pct = fields.Float(string='X Anterior (%)')
    y_from_pct = fields.Float(string='Y Anterior (%)')
    x_to_pct = fields.Float(string='X Nueva (%)')
    y_to_pct = fields.Float(string='Y Nueva (%)')
    date = fields.Datetime(
        string='Fecha',
        default=fields.Datetime.now,
    )
    comment = fields.Text(string='Comentario')
