"""Que el mismo hecho dé el mismo número, se mire desde donde se mire.

El módulo llegó a tener TRES cálculos distintos para «cuántas incidencias tiene esto», y sobre
los datos de producción daban tres respuestas: Bimbo Azcapotzalco decía 2,289 en la ficha de la
sede y 2,278 sumando sus planos.

Ninguno estaba mal leído por separado — por eso pasó la revisión. Estas pruebas existen para que
la próxima divergencia **no espere a que alguien se dé cuenta mirando dos pantallas**.
"""

from odoo.tests.common import TransactionCase


class TestPestCoherencia(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sede = cls.env['pest.sede'].create({'name': 'Sede de coherencia'})
        cls.plano = cls.env['pest.blueprint'].create({
            'name': 'Plano de coherencia', 'sede_id': cls.sede.id,
        })
        cls.tipo = cls.env['pest.trap.type'].create({'name': 'Tipo coherencia', 'code': 'coh'})
        cls.trampa = cls.env['pest.trap'].create({
            'name': 'TRAP-COH', 'sede_id': cls.sede.id,
            'blueprint_id': cls.plano.id, 'trap_type_id': cls.tipo.id,
        })

    def _incidencia(self, **extra):
        vals = {
            'sede_id': self.sede.id,
            'incident_type': 'captura',
            'organism_count': 1,
            'date': '2026-05-05 10:00:00',
        }
        vals.update(extra)
        return self.env['pest.incident'].create(vals)

    def test_el_total_de_la_sede_cuadra_con_sus_planos(self):
        """La cuenta de la sede = la de sus planos + las que no cuelgan de ningún plano.

        Es la comprobación que faltaba. El plano SUMABA el contador de sus trampas, así que las
        incidencias sin trampa se le escapaban y los dos números no cuadraban nunca.
        """
        self._incidencia(trap_id=self.trampa.id, blueprint_id=self.plano.id)
        self._incidencia(blueprint_id=self.plano.id)          # hallazgo: plano sí, trampa no
        self._incidencia()                                    # ni plano ni trampa
        self.env.invalidate_all()

        por_planos = sum(
            b.incident_count
            for b in self.env['pest.blueprint'].search([('sede_id', '=', self.sede.id)])
        )
        sueltas = self.env['pest.incident'].search_count([
            ('sede_id', '=', self.sede.id), ('blueprint_id', '=', False),
        ])
        self.assertEqual(
            self.sede.incident_count, por_planos + sueltas,
            'el total de la sede no cuadra con la suma de sus planos más las sueltas',
        )

    def test_el_plano_cuenta_las_incidencias_SIN_trampa(self):
        """El caso exacto que producía la diferencia de 11 en Azcapotzalco."""
        self._incidencia(blueprint_id=self.plano.id)          # sin trampa, con plano
        self.env.invalidate_all()
        self.assertEqual(
            self.plano.incident_count, 1,
            'un hallazgo sin trampa pertenece al plano igual: sumando trampas se perdía',
        )

    def test_el_contador_y_la_lista_del_boton_salen_del_MISMO_dominio(self):
        """Si el botón dice 8 y al pulsarlo salen 7, nadie vuelve a creerle a la pantalla."""
        from odoo.addons.pest_control.models import helpers
        self._incidencia(trap_id=self.trampa.id, blueprint_id=self.plano.id)
        self._incidencia(blueprint_id=self.plano.id)
        self.env.invalidate_all()

        cuantas_dice = self.plano.incident_count
        cuantas_hay = self.env['pest.incident'].search_count(
            helpers.dominio_incidencias(self.plano))
        self.assertEqual(cuantas_dice, cuantas_hay)

    def test_contar_lo_de_un_modelo_que_no_sabe_contar_AVISA(self):
        """Que falle ruidosamente es el punto: obliga a añadirlo al helper.

        Si devolviera cero en silencio, el siguiente escribiría su propio cálculo — que es
        exactamente como nacieron los tres que había.
        """
        from odoo.addons.pest_control.models import helpers
        with self.assertRaises(ValueError):
            helpers.dominio_incidencias(self.env['pest.trap.type'].search([], limit=1))


class TestPestCoherenciaArchivados(TransactionCase):
    """Vector c05 del banco de ataque: los archivados, ¿entran o no en los totales?

    Lo cazó el banco, no la revisión. La primera versión del arreglo de coherencia hacía cuadrar
    los números **preguntando a la base**, y en PANTALLA el usuario seguía viendo el desajuste:
    abría la sede, leía 2,289, sumaba los planos que tenía delante y le daban 2,278. Los 16
    planos archivados no se listan.

    El test anterior pasaba porque en su escenario no había ni un plano archivado. **Un caso que
    no está en la prueba es un caso que la prueba no protege.**
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sede = cls.env['pest.sede'].create({'name': 'Sede con archivados'})
        cls.vivo = cls.env['pest.blueprint'].create({
            'name': 'Plano vivo', 'sede_id': cls.sede.id})
        cls.archivado = cls.env['pest.blueprint'].create({
            'name': 'Plano archivado', 'sede_id': cls.sede.id})

    def _incidencia(self, plano):
        return self.env['pest.incident'].create({
            'sede_id': self.sede.id, 'blueprint_id': plano.id,
            'incident_type': 'captura', 'organism_count': 1,
            'date': '2026-05-05 10:00:00',
        })

    def test_b01_el_total_de_la_sede_NO_pierde_lo_archivado(self):
        """Archivar un plano no puede hacer desaparecer histórico del total.

        Si se descontara, archivar por error borraría datos de los informes sin avisar.
        """
        self._incidencia(self.vivo)
        self._incidencia(self.archivado)
        self.archivado.active = False
        self.env.invalidate_all()
        self.assertEqual(self.sede.incident_count, 2,
                         'archivar un plano no puede restar del histórico de la sede')

    def test_b02_la_diferencia_con_los_planos_visibles_queda_EXPLICADA(self):
        """Lo que el usuario no puede alcanzar, se dice; no se esconde ni se resta.

        total de la sede = suma de los planos que SÍ ve + los que están en archivados.
        """
        self._incidencia(self.vivo)
        self._incidencia(self.archivado)
        self._incidencia(self.archivado)
        self.archivado.active = False
        self.env.invalidate_all()

        visibles = sum(
            b.incident_count
            for b in self.env['pest.blueprint'].search([('sede_id', '=', self.sede.id)])
        )
        self.assertEqual(visibles, 1, 'el plano archivado no debe listarse')
        self.assertEqual(self.sede.incident_count_archivado, 2)
        self.assertEqual(
            self.sede.incident_count, visibles + self.sede.incident_count_archivado,
            'la diferencia entre el total y lo visible tiene que quedar explicada',
        )

    def test_b03_sin_planos_archivados_el_aviso_NO_aparece(self):
        """La prueba del caso contrario: un aviso que sale siempre deja de avisar."""
        self._incidencia(self.vivo)
        self.env.invalidate_all()
        self.assertEqual(self.sede.incident_count_archivado, 0)

    def test_b04_desarchivar_devuelve_el_conteo_a_su_sitio(self):
        """Ida y vuelta: deshacer tiene que dejar el sistema exactamente como estaba.

        Un dato derivado que sabe avanzar y no sabe retroceder miente en cuanto alguien se
        arrepiente — y la gente se arrepiente todo el tiempo.
        """
        self._incidencia(self.vivo)
        self._incidencia(self.archivado)
        self.env.invalidate_all()
        antes = (self.sede.incident_count, self.sede.incident_count_archivado)

        self.archivado.active = False
        self.env.invalidate_all()
        self.assertEqual(self.sede.incident_count_archivado, 1)

        self.archivado.active = True
        self.env.invalidate_all()
        self.assertEqual((self.sede.incident_count, self.sede.incident_count_archivado), antes,
                         'desarchivar debe dejar los contadores como estaban')

    def test_b05_las_TRAMPAS_archivadas_tambien_quedan_explicadas(self):
        """El gemelo del b02, y existe porque se arregló uno y se dejó el otro.

        Cerrado el descuadre de incidencias, la ficha de Bimbo Azcapotzalco decía 582 trampas y
        sus planos visibles sumaban 243: **339 de diferencia sin nada que la explicara**, en la
        misma pantalla donde las incidencias ya cuadraban.

        ⇒ Cuando arregles un hecho, busca su hermano ANTES de dar el arreglo por cerrado.
        """
        tipo = self.env['pest.trap.type'].create({'name': 'Tipo b05', 'code': 'b05'})
        for plano, cuantas in ((self.vivo, 2), (self.archivado, 3)):
            for i in range(cuantas):
                self.env['pest.trap'].create({
                    'name': '%s-%d' % (plano.name[:6], i), 'sede_id': self.sede.id,
                    'blueprint_id': plano.id, 'trap_type_id': tipo.id,
                })
        self.archivado.active = False
        self.env.invalidate_all()

        visibles = sum(
            b.trap_count
            for b in self.env['pest.blueprint'].search([('sede_id', '=', self.sede.id)])
        )
        self.assertEqual(visibles, 2)
        self.assertEqual(self.sede.trap_count_archivado, 3)
        self.assertEqual(
            self.sede.trap_count, visibles + self.sede.trap_count_archivado,
            'el total de trampas no cuadra con lo visible más lo archivado',
        )
