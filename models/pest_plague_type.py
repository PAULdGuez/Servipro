from odoo import fields, models


class PestPlagueType(models.Model):
    _name = 'pest.plague.type'
    _description = 'Tipo de Plaga'
    _order = 'name'

    name = fields.Char(
        string='Nombre',
        required=True,
    )
    code = fields.Char(
        string='Código',
        required=True,
    )
    category = fields.Selection(
        selection=[
            ('volador', 'Volador'),
            ('rastrero', 'Rastrero'),
            ('otro', 'Otro'),
        ],
        string='Categoría',
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            'code_unique',
            'UNIQUE(code)',
            'El código del tipo de plaga debe ser único.',
        ),
    ]
