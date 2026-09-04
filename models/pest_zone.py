from odoo import models, fields


class PestZone(models.Model):
    _name = 'pest.zone'
    _description = 'Ubicación'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código')
    active = fields.Boolean(default=True)

    _name_unique = models.Constraint(
        'UNIQUE(name)',
        'El nombre de zona debe ser único.',
    )
