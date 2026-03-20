import json
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PestBlueprintZone(models.Model):
    _name = 'pest.blueprint.zone'
    _description = 'Zona del Plano'
    _order = 'name'

    name = fields.Char(string='Nombre de Zona', required=True)
    blueprint_id = fields.Many2one('pest.blueprint', string='Plano', required=True, ondelete='cascade')
    points_data = fields.Text(string='Puntos del Polígono', required=True,
                              help='JSON array de objetos {x, y} en porcentaje (0.0 a 100.0)')
    color = fields.Char(string='Color', default='#3498db55')
    active = fields.Boolean(default=True)

    @api.constrains('points_data')
    def _check_points_data(self):
        for record in self:
            try:
                points = json.loads(record.points_data)
            except (json.JSONDecodeError, TypeError):
                raise ValidationError('points_data debe ser un JSON válido.')
            if not isinstance(points, list):
                raise ValidationError('points_data debe ser una lista de puntos.')
            if len(points) < 3:
                raise ValidationError('Un polígono necesita al menos 3 puntos.')
            for i, point in enumerate(points):
                if not isinstance(point, dict):
                    raise ValidationError(f'El punto {i} debe ser un objeto con claves x e y.')
                if 'x' not in point or 'y' not in point:
                    raise ValidationError(f'El punto {i} debe tener claves "x" e "y".')
                if not (0 <= float(point['x']) <= 100 and 0 <= float(point['y']) <= 100):
                    raise ValidationError(f'El punto {i} tiene coordenadas fuera del rango 0-100.')
