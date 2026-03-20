from odoo import fields, models


class PestTrapType(models.Model):
    _name = 'pest.trap.type'
    _description = 'Tipo de Trampa'
    _order = 'name'

    name = fields.Char(
        string='Nombre',
        required=True,
    )
    code = fields.Char(
        string='Código',
        required=True,
    )
    icon = fields.Char(
        string='Icono FontAwesome',
        help='Clase CSS de FontAwesome, e.g. "fa-bug"',
    )
    description = fields.Text(string='Descripción')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            'code_unique',
            'UNIQUE(code)',
            'El código del tipo de trampa debe ser único.',
        ),
    ]
