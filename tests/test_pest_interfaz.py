"""Pruebas de interfaz: que la pantalla CARGUE, no solo que el modelo responda.

Un test de modelo no ve si el widget monta ni si la vista revienta al dibujarse.
Estos tours entran por donde entra el usuario —el menú— y con el rol que le toca.

Se ejecutan dentro de la suite normal: `--test-enable --test-tags=/pest_control`.
Odoo levanta el navegador; no hace falta infraestructura aparte.
"""

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestPestInterfaz(HttpCase):

    def test_cliente_abre_su_plano(self):
        """El flujo que estuvo roto: al Cliente le faltaba permiso sobre los catálogos
        y el plano tronaba con AccessError. Aquí se prueba ENTRANDO como cliente."""
        empresa = self.env.company
        sede = self.env['pest.sede'].create({'name': 'Sede del tour', 'company_id': empresa.id})
        plano = self.env['pest.blueprint'].create({'name': 'Plano del tour', 'sede_id': sede.id})
        tipo = self.env['pest.trap.type'].search([], limit=1) or \
            self.env['pest.trap.type'].create({'name': 'Tipo tour', 'code': 'tipo_tour'})
        self.env['pest.trap'].create({
            'name': 'TR-TOUR', 'sede_id': sede.id, 'blueprint_id': plano.id,
            'trap_type_id': tipo.id, 'coord_x_pct': 50, 'coord_y_pct': 50})

        usuario = self.env['res.users'].create({
            'name': 'Cliente del tour', 'login': 'cliente.tour',
            'password': 'cliente.tour',
            'company_id': empresa.id, 'company_ids': [(6, 0, [empresa.id])],
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('pest_control.group_pest_client').id])],
        })
        self.env.flush_all()

        self.start_tour('/odoo', 'pest_cliente_abre_su_plano', login=usuario.login)
