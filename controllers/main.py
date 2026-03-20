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

class PestDocsController(http.Controller):

    @http.route('/pest_control/docs/<string:filename>', type='http', auth='user', website=True)
    def render_doc(self, filename, **kw):
        # Security: only allow rendering from the explicit doc directory
        if '..' in filename or filename.startswith('/'):
            return request.not_found()
            
        file_path = os.path.join(os.path.dirname(__file__), '../doc', filename)
        
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
