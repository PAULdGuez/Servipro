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
