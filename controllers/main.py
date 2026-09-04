import os
import logging
from odoo import http
from odoo.tools import html_sanitize
from odoo.http import request
from markupsafe import Markup

_logger = logging.getLogger(__name__)

try:
    import markdown
except ImportError:
    markdown = None
    _logger.warning("Markdown library not found. Falling back to plain text rendering for docs.")

ALLOWED_DOCS = {'CONTRIBUTING.md', 'TECHNICAL_ARCHITECTURE.md', 'USER_MANUAL.md'}

class PestDocsController(http.Controller):

    @http.route('/pest_control/blueprint/<int:blueprint_id>/heatmap_data', type='jsonrpc', auth='user')
    def get_heatmap_data(self, blueprint_id, mode='incidents', plague_type_id=None, **kwargs):
        blueprint = request.env['pest.blueprint'].browse(blueprint_id)
        if not blueprint.exists():
            return {'error': 'Blueprint not found'}

        traps = request.env['pest.trap'].search([
            ('blueprint_id', '=', blueprint_id),
            ('active', '=', True),
        ])

        if not traps:
            return {'points': [], 'max_value': 1}

        # Base domain
        domain = [('trap_id', 'in', traps.ids)]

        # Filter by plague type if specified
        if plague_type_id:
            domain.append(('plague_type_id', '=', int(plague_type_id)))

        # Build trap coordinate map
        trap_coords = {t.id: (t.coord_x_pct, t.coord_y_pct) for t in traps}

        points = []

        if mode == 'incidents':
            incident_data = request.env['pest.incident']._read_group(
                domain=domain,
                groupby=['trap_id'],
                aggregates=['__count'],
            )
            for trap, count in incident_data:
                if count and count > 0:
                    coords = trap_coords.get(trap.id)
                    if coords:
                        points.append({'x': coords[0] or 0, 'y': coords[1] or 0, 'value': count})
        else:
            incident_data = request.env['pest.incident']._read_group(
                domain=domain,
                groupby=['trap_id'],
                aggregates=['organism_count:sum'],
            )
            for trap, total_organisms in incident_data:
                if total_organisms and total_organisms > 0:
                    coords = trap_coords.get(trap.id)
                    if coords:
                        points.append({'x': coords[0] or 0, 'y': coords[1] or 0, 'value': total_organisms})

        max_value = max((p['value'] for p in points), default=1)

        # Get plague-specific threshold if filtering by plague
        threshold_alto = None
        if plague_type_id:
            plague = request.env['pest.plague.type'].browse(int(plague_type_id))
            if plague.exists():
                threshold_alto = plague.heatmap_umbral_alto

        return {
            'points': points,
            'max_value': max_value,
            'mode': mode,
            'plague_type_id': plague_type_id,
            'threshold_alto': threshold_alto,
        }

    @http.route('/pest_control/docs/<string:filename>', type='http', auth='user', website=True)
    def render_doc(self, filename, **kw):
        if filename not in ALLOWED_DOCS:
            return request.not_found()

        doc_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'doc'))
        file_path = os.path.abspath(os.path.join(doc_dir, filename))

        if not file_path.startswith(doc_dir):
            return request.not_found()

        if not os.path.exists(file_path):
            return request.not_found()

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 🔴 Las DOS ramas eran inyectables, y el `Markup(...)` de abajo es lo que las hacía
        # peligrosas: le dice a la plantilla «esto ya viene seguro, píntalo tal cual».
        #
        # - Sin la librería, el contenido del archivo entraba crudo en un f-string dentro de
        #   un `<pre>`: un `.md` con un `<script>` se ejecutaba en el navegador de quien lo
        #   abriera.
        # - Con la librería tampoco bastaba: `markdown.markdown()` **deja pasar el HTML crudo
        #   del documento a propósito** — es una función de Markdown, no un fallo.
        #
        # Hoy los `.md` son del repo y la ruta pide sesión, así que el riesgo es bajo. Pero es
        # una inyección esperando su entrada: el día que alguien permita subir documentación,
        # o que un `.md` llegue de un cliente, ya está armada. Se cierra ahora, que cuesta dos
        # líneas, y no el día que haga falta.
        #
        # `html_sanitize` es el sanitizador del propio Odoo: quita `<script>` y compañía y
        # respeta el formato. Nada que instalar.
        if markdown:
            # Parse extensions like tables and fenced code blocks typical in technical docs
            html_string = html_sanitize(
                markdown.markdown(content, extensions=['fenced_code', 'tables']))
        else:
            html_string = Markup(
                "<pre style='white-space: pre-wrap; word-wrap: break-word;'>{}</pre>"
            ).format(content)      # `.format` de Markup ESCAPA lo que se le mete

        return request.render('pest_control.doc_template', {
            'html_content': Markup(html_string),
            'filename': filename,
        })
