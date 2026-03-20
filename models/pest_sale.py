from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sede_id = fields.Many2one(
        'pest.sede',
        string='Sede / Planta',
    )
