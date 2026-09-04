"""Los vectores del banco de ataque que tocaron esta sesión, fijados en pruebas.

**Una fila del banco no se cierra con prosa, se cierra con el nombre de una prueba que existe.**
«Ya lo valida el framework» es una hipótesis; si de verdad lo valida, la prueba que lo demuestra
tarda cinco minutos y además avisa el día que el framework cambie.

Los cuatro de aquí se comprobaron a mano contra los datos reales y los cuatro pasaban. Se escriben
igual: **verde hoy no es garantía de mañana**, y el vector que ya está cubierto es barato de fijar.
"""

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase


class TestBancoDeAtaque(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sede = cls.env['pest.sede'].create({'name': 'Sede del banco'})

    # ── superficie: consulta / reporte ───────────────────────────────

    def test_c08_una_sede_SIN_datos_devuelve_cero_no_truena(self):
        """Un reporte sobre nada tiene que dar cero, no una excepción ni media pantalla rota.

        Es el caso que nadie prueba porque «obviamente funciona», y donde vive la división entre
        cero. Con datos de demostración siempre hay algo; el día del alta de un cliente nuevo, no.
        """
        datos = self.sede.get_dashboard_data()
        self.assertTrue(datos, 'el tablero de una sede vacía no puede venir vacío del todo')
        con_datos = [k for k, v in datos.items() if isinstance(v, dict) and v.get('labels')]
        self.assertEqual(con_datos, [], 'sin registros, ninguna gráfica debería traer etiquetas')

    def test_c08_el_tablero_de_una_sede_vacia_trae_TODAS_las_claves(self):
        """Y las trae completas: si al front le falta una clave, la gráfica revienta en el cliente.

        Devolver menos claves cuando no hay datos es el error clásico: se prueba con datos, se ve
        bien, y el primer cliente sin histórico abre el tablero y se le cae.
        """
        vacia = self.sede.get_dashboard_data()
        con_datos = self.env['pest.sede'].search([('incident_count', '>', 0)], limit=1)
        if not con_datos:
            self.skipTest('no hay ninguna sede con datos contra la que comparar')
        self.assertEqual(
            set(vacia), set(con_datos.get_dashboard_data()),
            'la sede sin datos devuelve un juego de claves distinto al de una con datos',
        )

    def test_c07_los_permisos_recortan_el_reporte(self):
        """Dos usuarios de empresas distintas ven números distintos, y **deben**.

        Correrlo como administrador no prueba nada: el superusuario no ejerce permisos.
        """
        otra = self.env['res.company'].create({'name': 'Empresa del banco'})
        suya = self.env['pest.sede'].create({'name': 'Sede ajena', 'company_id': otra.id})
        usuario = self.env['res.users'].create({
            'name': 'Cliente del banco', 'login': 'cliente.banco',
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
            'group_ids': [(4, self.env.ref('pest_control.group_pest_client').id)],
        })
        self.env.invalidate_all()
        with self.assertRaises(AccessError,
                               msg='un usuario leyó una sede de otra empresa'):
            suya.with_user(usuario).name

    # ── superficie: modelo con estado ────────────────────────────────

    def test_m03_la_guarda_de_fecha_aguanta_la_escritura_DIRECTA(self):
        """No basta con validar en el formulario: por RPC o por importación se entra por debajo.

        Un `required` de vista se lo salta cualquiera que escriba por el ORM — que es justo como
        entraron las 19 fechas imposibles del sistema anterior.
        """
        inc = self.env['pest.incident'].create({
            'sede_id': self.sede.id, 'incident_type': 'captura',
            'organism_count': 1, 'date': '2026-05-05 10:00:00',
        })
        with self.assertRaises(ValidationError):
            inc.write({'date': '1015-05-08 10:00:00'})

    def test_m06_un_registro_VIEJO_sin_zona_no_rompe_el_plano(self):
        """Las 2,219 trampas migradas nacieron antes de que la zona existiera.

        El código que asume que un campo nuevo está lleno funciona perfecto con los registros que
        crea él, y truena con todo lo que ya estaba.
        """
        plano = self.env['pest.blueprint'].create({
            'name': 'Plano del banco', 'sede_id': self.sede.id})
        tipo = self.env['pest.trap.type'].create({'name': 'Tipo banco', 'code': 'banco'})
        self.env['pest.trap'].create({
            'name': 'TRAP-BANCO', 'sede_id': self.sede.id, 'blueprint_id': plano.id,
            'trap_type_id': tipo.id, 'coord_x_pct': 40.0, 'coord_y_pct': 60.0,
        })
        datos = plano.get_widget_data()          # sin zone_id a propósito
        self.assertEqual(len(datos['traps']), 1)
        self.assertEqual(datos['traps'][0]['name'], 'TRAP-BANCO')
