from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

# El sistema anterior no validaba NADA al capturar, y se colaron 19 incidencias con años
# imposibles: 25, 205, 1010, 1015, 1025, 1969 y 2925. Son erratas de tecleo («25» por «2025»,
# «1015» por «2015») y el 1969-12-31 del cero de los relojes, o sea una fecha vacía.
#
# 🔑 **El daño no es proporcional al número.** Son 19 de 6,983 —un 0.3%— y bastan para estirar
# el eje de la gráfica de tendencia 1,800 años, dejando los datos reales aplastados en un
# centímetro. La gráfica más útil que tienen queda ilegible por culpa de tres milésimas.
# El umbral es RELATIVO al presente, no un año fijo. Estuvo en 2000 y el problema no fue que
# fuese generoso: es que estaba calibrado contra lo IMPOSIBLE en vez de contra lo PLAUSIBLE. El
# año 2005 no es imposible para un sistema, pero sí para unos datos que empiezan en 2025 — así
# que tres registros con un dedazo de un dígito (2005 por 2025) pasaban el filtro y estiraban el
# eje de la gráfica veinte años. Un umbral fijo además envejece: en 2035 seguiría diciendo 2000.
ANIOS_DE_HISTORIA_RAZONABLE = 10
MARGEN_AL_FUTURO = timedelta(days=365)


class PestIncident(models.Model):
    _name = 'pest.incident'
    _description = 'Incidencia de Plaga'
    _order = 'date desc'

    trap_id = fields.Many2one(
        'pest.trap',
        string='Trampa',
        ondelete='set null',
        help='Dejar vacío para hallazgos sin trampa asociada.',
    )
    sede_id = fields.Many2one(
        'pest.sede',
        string='Sede',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        'res.company', string='Empresa',
        related='sede_id.company_id', store=True, index=True,
    )
    blueprint_id = fields.Many2one(
        'pest.blueprint',
        string='Plano',
        ondelete='set null',
    )
    plague_type_id = fields.Many2one(
        'pest.plague.type',
        string='Tipo de Plaga',
    )
    plague_type_custom = fields.Char(
        string='Tipo de Plaga Personalizado',
        help='Usar cuando el tipo de plaga no está en el catálogo.',
    )
    incident_type = fields.Selection(
        selection=[
            ('captura', 'Captura'),
            ('hallazgo', 'Hallazgo'),
        ],
        string='Tipo de Incidencia',
        required=True,
    )
    insect_type = fields.Selection(
        selection=[
            ('volador', 'Volador'),
            ('rastrero', 'Rastrero'),
        ],
        string='Tipo de Insecto',
    )
    organism_count = fields.Integer(
        string='Cantidad de Organismos',
        default=0,
    )
    date = fields.Datetime(
        string='Fecha',
        required=True,
        default=fields.Datetime.now,
    )
    inspector = fields.Char(string='Inspector')
    notes = fields.Text(string='Notas')
    inspection_id = fields.Many2one(
        'pest.inspection',
        string='Inspección',
        ondelete='set null',
    )

    # ── Computed ────────────────────────────────────────────────────
    plague_display_name = fields.Char(
        string='Plaga',
        compute='_compute_plague_display_name',
    )

    @api.depends('plague_type_id', 'plague_type_custom')
    def _compute_plague_display_name(self):
        for rec in self:
            if rec.plague_type_id:
                rec.plague_display_name = rec.plague_type_id.name
            elif rec.plague_type_custom:
                rec.plague_display_name = rec.plague_type_custom
            else:
                rec.plague_display_name = 'Sin especificar'

    # ── Fechas defendibles ──────────────────────────────────────────
    #
    # UN SOLO SITIO define qué fecha es válida, y lo usan los tres: la validación al capturar,
    # el filtro del tablero y la lista para corregirlas. Si el criterio vive en tres lados, el
    # día que alguien lo ajuste va a dejar dos sin ajustar y nada va a avisar.

    @api.model
    def _limites_de_fecha_razonable(self):
        """(desde, hasta) — el rango fuera del cual una fecha es, con seguridad, una errata."""
        ahora = fields.Datetime.now()
        desde = fields.Datetime.to_datetime(
            '%d-01-01 00:00:00' % (ahora.year - ANIOS_DE_HISTORIA_RAZONABLE))
        hasta = ahora + MARGEN_AL_FUTURO
        return desde, hasta

    @api.model
    def _dominio_fecha_razonable(self):
        """Para EXCLUIR las erratas de una consulta, sin borrarlas de la base."""
        desde, hasta = self._limites_de_fecha_razonable()
        return [('date', '>=', desde), ('date', '<=', hasta)]

    @api.constrains('date')
    def _check_date_razonable(self):
        """Impide que entren MÁS. No toca las 19 que ya están.

        Deliberadamente no se corrigen solas: no hay forma de saber si «1015-05-08» era 2015 o
        2025, y adivinarlo sería inventar un dato de campo. Al editar una de ellas, esta guarda
        obliga a poner la buena — que es quien sabe, no el sistema.
        """
        desde, hasta = self._limites_de_fecha_razonable()
        for rec in self:
            if rec.date and not (desde <= rec.date <= hasta):
                raise ValidationError(
                    'La fecha %s no puede ser: está fuera del rango razonable '
                    '(del %s al %s). Revise el año, suele ser una errata al teclear.'
                    % (rec.date.strftime('%d/%m/%Y'), desde.strftime('%d/%m/%Y'),
                       hasta.strftime('%d/%m/%Y'))
                )
