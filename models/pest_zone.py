from odoo import models, fields


class PestZone(models.Model):
    """Una zona operativa dentro de una planta: «Almacén de MP», «Andén de carga», «Comedor».

    🔑 **La zona cuelga de la SEDE, no de la empresa.** Es un lugar físico de una planta concreta:
    Bimbo tiene 19 plantas y cada una su propio «Almacén de MP». Colgándola de la empresa, un
    técnico de Azcapotzalco elegiría entre las zonas de Villahermosa; colgándola de la sede, el
    desplegable de la trampa se filtra solo. La empresa se deriva de la sede y es la que engancha
    la regla de aislamiento entre clientes.

    ⚠️ Antes esta unicidad era `UNIQUE(name)` a secas, y eso **es un fallo de multi-cliente**: el
    primer cliente que registrara «Despacho» dejaba a todos los demás sin poder tener el suyo.
    """
    _name = 'pest.zone'
    _description = 'Ubicación'
    _order = 'sede_id, name'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código')
    sede_id = fields.Many2one(
        'pest.sede', string='Sede', required=True, ondelete='cascade', index=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Empresa', related='sede_id.company_id',
        store=True, readonly=True, index=True,
    )
    active = fields.Boolean(default=True)

    _name_sede_unique = models.Constraint(
        'UNIQUE(name, sede_id)',
        'Ya existe una ubicación con ese nombre en esta sede.',
    )
