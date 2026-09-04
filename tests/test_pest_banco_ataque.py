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


class TestMetodosLlamablesPorRPC(TransactionCase):
    """Invocar un método sobre un registro ajeno tiene que REBOTAR, no devolver vacío.

    Odoo protege leer campos y escribir, pero **no impide llamar a un método** sobre un registro
    que no puedes ver. Antes de esto, un cliente podía llamar por RPC a
    `pest.sede(<id de otro cliente>).get_dashboard_data()`: el método se ejecutaba y devolvía las
    13 gráficas vacías, sin error.

    No filtraba datos —las reglas hacen su trabajo dentro— pero permitía **averiguar qué
    identificadores existen**, que es enumeración. Lo encontró una auditoría independiente.

    🔑 **Y la prueba se escribe con el caché invalidado JUSTO antes de cada llamada.** Sin eso
    lee lo que el superusuario dejó cargado y **miente en las dos direcciones**: puede dar por
    buena una fuga que no existe, o dar por protegido algo que no lo está. Pasó dos veces en este
    proyecto.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mia = cls.env['res.company'].create({'name': 'Mi empresa RPC'})
        cls.suya = cls.env['res.company'].create({'name': 'Empresa ajena RPC'})
        cls.sede_ajena = cls.env['pest.sede'].create({'name': 'Planta ajena', 'company_id': cls.suya.id})
        cls.plano_ajeno = cls.env['pest.blueprint'].create({
            'name': 'Plano ajeno', 'sede_id': cls.sede_ajena.id})
        cls.trampa_ajena = cls.env['pest.trap'].create({
            'name': 'TRAP-AJENA', 'sede_id': cls.sede_ajena.id,
            'blueprint_id': cls.plano_ajeno.id,
            'trap_type_id': cls.env['pest.trap.type'].create({'name': 'T RPC', 'code': 'trpc'}).id,
        })
        cls.mia_sede = cls.env['pest.sede'].create({'name': 'Mi planta', 'company_id': cls.mia.id})
        cls.usuario = cls.env['res.users'].create({
            'name': 'cliente RPC', 'login': 'cliente.rpc',
            'company_id': cls.mia.id, 'company_ids': [(6, 0, [cls.mia.id])],
            'group_ids': [(4, cls.env.ref('pest_control.group_pest_client').id)],
            'pest_sede_ids': [(6, 0, cls.mia_sede.ids)],
        })

    # ⚠️ **MEDIDO: de los cuatro, solo `get_dashboard_data` era un agujero real.**
    #
    # Anulando el guard, de estas cuatro pruebas cae UNA (`r01`). Las otras tres siguen verdes:
    # `get_detail_data`, `get_widget_data` y `action_move_to_from_widget` ya rebotaban solos,
    # porque leen campos del registro y ahí Odoo sí comprueba el permiso. `get_dashboard_data`
    # no leía ninguno —solo agrupaba con el id— y por eso se colaba.
    #
    # Se dejan las cuatro y el guard en los cuatro **a propósito**: r02-r04 no prueban el guard,
    # prueban que el comportamiento correcto se mantiene si alguien toca esos métodos y deja de
    # leer campos. Pero conviene saber cuál muerde y cuál no: **una prueba verde por una razón
    # distinta de la que dice su nombre es una prueba que no protege lo que crees.**

    def _como_el(self, registro):
        self.env.invalidate_all()          # sin esto la prueba lee del caché del admin y miente
        return registro.with_user(self.usuario)

    def test_r01_el_tablero_de_una_sede_ajena_REBOTA(self):
        with self.assertRaises(AccessError):
            self._como_el(self.sede_ajena).get_dashboard_data()

    def test_r02_la_ficha_de_una_trampa_ajena_REBOTA(self):
        with self.assertRaises(AccessError):
            self._como_el(self.trampa_ajena).get_detail_data()

    def test_r03_el_plano_ajeno_REBOTA(self):
        with self.assertRaises(AccessError):
            self._como_el(self.plano_ajeno).get_widget_data()

    def test_r04_mover_una_trampa_ajena_REBOTA(self):
        with self.assertRaises(AccessError):
            self._como_el(self.trampa_ajena).action_move_to_from_widget(10.0, 20.0)

    def test_r05_y_SOBRE_LO_SUYO_sigue_funcionando(self):
        """La prueba del caso contrario: un guard que bloquea todo también «protege».

        Sin esto, poner el candado en el sitio equivocado dejaría los cuatro tests de arriba en
        verde y el sistema inservible para el usuario legítimo.
        """
        datos = self._como_el(self.mia_sede).get_dashboard_data()
        self.assertTrue(isinstance(datos, dict) and datos,
                        'el usuario no puede ver el tablero de su propia sede')
