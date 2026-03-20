import os
import logging
from odoo import http
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
    def get_heatmap_data(self, blueprint_id, **kwargs):
        """Return heatmap data points for a blueprint's incidents."""
        blueprint = request.env['pest.blueprint'].browse(blueprint_id)
        if not blueprint.exists():
            return {'error': 'Blueprint not found'}

        traps = request.env['pest.trap'].search([
            ('blueprint_id', '=', blueprint_id),
            ('active', '=', True),
        ])

        # Build heatmap points: each trap's position weighted by organism count
        points = []
        for trap in traps:
            incidents = request.env['pest.incident'].search([
                ('trap_id', '=', trap.id),
            ])
            total_organisms = sum(incidents.mapped('organism_count'))
            if total_organisms > 0:
                points.append({
                    'x': trap.coord_x_pct,
                    'y': trap.coord_y_pct,
                    'value': total_organisms,
                })

        max_value = max((p['value'] for p in points), default=1)

        return {
            'points': points,
            'max_value': max_value,
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
            
        if markdown:
            # Parse extensions like tables and fenced code blocks typical in technical docs
            html_string = markdown.markdown(content, extensions=['fenced_code', 'tables'])
        else:
            html_string = f"<pre style='white-space: pre-wrap; word-wrap: break-word;'>{content}</pre>"
            
        return request.render('pest_control.doc_template', {
            'html_content': Markup(html_string),
            'filename': filename,
        })
