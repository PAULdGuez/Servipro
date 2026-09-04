"""El visor de documentación no puede ejecutar lo que trae el archivo.

Las dos ramas del visor eran inyectables —con y sin la librería de Markdown—, y el `Markup(...)`
final era lo que las hacía peligrosas: le dice a la plantilla «esto ya viene seguro».

Hoy los `.md` son del repo y la ruta pide sesión, así que el riesgo es bajo. **Es una inyección
esperando su entrada**: el día que se permita subir documentación, o que un `.md` llegue de un
cliente, ya está armada.
"""

from odoo.tests.common import TransactionCase
from odoo.tools import html_sanitize


class TestVisorDeDocumentacion(TransactionCase):

    def test_d01_el_sanitizador_quita_el_script(self):
        """La pieza que usa el visor, probada por los dos lados."""
        peligroso = '<p>Documentación normal</p><script>alert("robado")</script>'
        limpio = html_sanitize(peligroso)
        self.assertNotIn('<script', limpio, 'el script sobrevivió al sanitizador')
        self.assertIn('Documentación normal', limpio,
                      'el sanitizador se llevó por delante el contenido legítimo')

    def test_d02_el_formato_util_SOBREVIVE(self):
        """La prueba del caso contrario: un sanitizador que borra todo también «protege».

        Sin esto, cambiar el sanitizador por uno que devuelva cadena vacía dejaría el test
        anterior en verde y el visor inservible.
        """
        conservados = html_sanitize(
            '<h2>Título</h2><table><tr><td>celda</td></tr></table>'
            '<pre><code>codigo()</code></pre><strong>negrita</strong>'
        )
        for etiqueta in ('Título', 'celda', 'codigo()', 'negrita'):
            self.assertIn(etiqueta, conservados,
                          'el sanitizador se comió %s, que es formato legítimo de un manual' % etiqueta)

    def test_d03_el_texto_plano_se_ESCAPA_al_meterlo_en_el_pre(self):
        """La rama sin librería: `Markup(...).format()` escapa lo que se le inyecta.

        Un f-string ahí dentro NO escapa nada — era exactamente el fallo.
        """
        from markupsafe import Markup
        resultado = Markup("<pre>{}</pre>").format('<script>alert(1)</script>')
        self.assertNotIn('<script>', str(resultado))
        self.assertIn('&lt;script&gt;', str(resultado))
