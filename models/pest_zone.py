from odoo import models, fields


class PestZone(models.Model):
    _name = 'pest.zone'
    _description = 'Zona / Ubicación'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'El nombre de zona debe ser único.'),
    ]
