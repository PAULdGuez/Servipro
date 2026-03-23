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
    heatmap_umbral_bajo = fields.Integer(string='Umbral Bajo', default=5,
        help='Cantidad de organismos considerada nivel bajo para esta plaga')
    heatmap_umbral_medio = fields.Integer(string='Umbral Medio', default=20,
        help='Cantidad de organismos considerada nivel medio para esta plaga')
    heatmap_umbral_alto = fields.Integer(string='Umbral Alto', default=50,
        help='Cantidad de organismos considerada nivel alto/critico para esta plaga')

    _sql_constraints = [
        (
            'code_unique',
            'UNIQUE(code)',
            'El código del tipo de plaga debe ser único.',
        ),
    ]
