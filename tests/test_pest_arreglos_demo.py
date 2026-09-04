# -*- coding: utf-8 -*-
"""Las seis cosas que la demostración habría enseñado rotas, cada una con su prueba.

Ninguna de las seis se veía leyendo el código: salieron de navegar la aplicación y pulsar los
controles. Estas pruebas existen para que, si alguien deshace uno de los arreglos, la suite lo
diga **con el nombre del caso** en vez de esperar a que se note en una demostración.

Se cubre lo que es Python. La desambiguación del desplegable de planos vive en JavaScript y su
prueba es el recorrido con navegador, anotado en el guion.
"""

from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from ..models import helpers


class TestEstadoDerivadoDeArchivado(TransactionCase):
    """`state` y `active` decían el mismo hecho y se desincronizaban.

    Había 3 sedes reales diciendo «Activa» estando archivadas, porque al archivar solo cambiaba
    `active`. Ahora uno se deriva del otro, así que la contradicción no puede existir.
    """

    def setUp(self):
        super().setUp()
        self.sede = self.env['pest.sede'].create({'name': 'Sede del estado'})

    def test_archivar_arrastra_el_estado(self):
        self.assertEqual(self.sede.state, 'active')
        self.sede.active = False
        self.assertEqual(
            self.sede.state, 'inactive',
            'al archivar una sede su estado debe seguirla; si no, la ficha dice «Activa» '
            'en una planta archivada — que es el fallo original',
        )

    def test_mover_el_estado_archiva_de_verdad(self):
        """El caso contrario, que es donde suelen esconderse los fallos.

        Sin esto, el usuario movería la barra de estado, se guardaría sin protestar, y la sede
        seguiría activa: la misma mentira vista desde el otro lado.
        """
        self.sede.state = 'inactive'
        self.assertFalse(
            self.sede.active,
            'mover el estado a Inactiva tiene que archivar el registro de verdad',
        )
        self.sede.state = 'active'
        self.assertTrue(self.sede.active, 'y volver a Activa tiene que desarchivarlo')

    def test_ninguna_sede_puede_contradecirse(self):
        """La comprobación de conjunto: lo que se midió sobre los datos reales."""
        sedes = self.env['pest.sede'].with_context(active_test=False).search([])
        malas = sedes.filtered(lambda s: (s.state == 'active') != bool(s.active))
        self.assertFalse(
            malas, 'estas sedes dicen un estado y tienen otro: %s' % malas.mapped('name'))


class TestEtiquetaEnVezDeValorCrudo(TransactionCase):
    """El globo del plano pintaba `en_reparacion`, con guion bajo y sin acento.

    Lo que lo convierte en lección: el helper que lo traduce YA existía, pero vivía en el modelo
    de sedes, donde nadie lo buscó. Ahora está en `helpers.py` y estas pruebas fijan que la
    etiqueta viaje ya resuelta desde el backend, para que el front no tenga que saber la tabla.
    """

    def test_traduce_el_valor_a_lo_que_se_lee(self):
        self.assertEqual(
            helpers.etiqueta_de(self.env, 'pest.trap', 'current_state', 'en_reparacion'),
            'En Reparación',
        )

    def test_un_valor_vacio_no_deja_hueco_en_la_pantalla(self):
        self.assertEqual(
            helpers.etiqueta_de(self.env, 'pest.trap', 'current_state', False),
            'Sin especificar',
        )

    def test_un_valor_desconocido_no_revienta(self):
        """Si mañana alguien mete un valor que no está en la lista, se muestra tal cual.

        Vale más una etiqueta fea que una pantalla caída delante del cliente.
        """
        self.assertEqual(
            helpers.etiqueta_de(self.env, 'pest.trap', 'current_state', 'inventado'),
            'inventado',
        )

    def test_la_trampa_manda_su_etiqueta_al_visor(self):
        sede = self.env['pest.sede'].create({'name': 'Sede del visor'})
        tipo = self.env['pest.trap.type'].create({'name': 'Tipo visor', 'code': 'vis'})
        trampa = self.env['pest.trap'].create({
            'name': 'TRAP-VIS', 'sede_id': sede.id, 'trap_type_id': tipo.id,
        })
        datos = trampa.get_detail_data()
        self.assertIn(
            'current_state_label', datos,
            'el visor necesita la etiqueta ya resuelta; sin ella vuelve a pintar el valor crudo',
        )
        self.assertNotIn(
            '_', datos['current_state_label'],
            'la etiqueta no puede llevar guiones bajos: eso es el valor interno, no un texto',
        )


class TestFechaRazonableRelativa(TransactionCase):
    """El corte estaba en el año 2000 fijo, y dejaba pasar los dedazos de 2005.

    El problema no era que fuese generoso: estaba calibrado contra lo **imposible** en vez de
    contra lo **plausible**. Un año fijo además envejece solo.
    """

    def setUp(self):
        super().setUp()
        self.Incidencia = self.env['pest.incident']

    def test_el_corte_se_mueve_con_el_calendario(self):
        desde, _ = self.Incidencia._limites_de_fecha_razonable()
        esperado = fields.Datetime.now().year - helpers_anios()
        self.assertEqual(
            desde.year, esperado,
            'el corte tiene que ser relativo al presente; si es un año fijo, dentro de diez '
            'años seguirá aceptando fechas que ya no tienen sentido',
        )

    def test_un_dedazo_de_un_digito_ya_no_pasa(self):
        """2005 por 2025: el caso real que estiraba el eje veinte años."""
        desde, _ = self.Incidencia._limites_de_fecha_razonable()
        self.assertGreater(
            desde.year, 2005,
            'una fecha de 2005 debe quedar fuera del rango que se grafica',
        )

    def test_lo_de_ayer_y_lo_de_mañana_siguen_valiendo(self):
        """El caso contrario: que el corte no se coma datos buenos."""
        desde, hasta = self.Incidencia._limites_de_fecha_razonable()
        ahora = fields.Datetime.now()
        self.assertLess(desde, ahora - timedelta(days=365 * 2),
                        'dos años de histórico tienen que caber')
        self.assertGreater(hasta, ahora + timedelta(days=30),
                           'una fecha del mes que viene tiene que poder capturarse')

    def test_la_guarda_rechaza_una_fecha_imposible(self):
        sede = self.env['pest.sede'].create({'name': 'Sede de fechas'})
        with self.assertRaises(ValidationError):
            self.env['pest.incident'].create({
                'sede_id': sede.id,
                'incident_type': 'captura',
                'date': '1969-12-31 18:00:00',
            })


class TestTextosQueLeeElCliente(TransactionCase):
    """Siete textos nuestros salían sin acento en la leyenda de las gráficas.

    «Mosca Domestica» es la plaga número uno del sistema: la primera barra del tablero.
    """

    def test_los_nombres_del_catalogo_llevan_sus_acentos(self):
        malos = []
        for modelo in ('pest.plague.type', 'pest.trap.type'):
            for rec in self.env[modelo].with_context(active_test=False).search([]):
                for palabra in ('Domestica', 'Metalica', 'Forida', 'Quimicas',
                                'Sonico', 'Aranas', 'de Almacen'):
                    if palabra in (rec.name or ''):
                        malos.append('%s: %s' % (modelo, rec.name))
        self.assertFalse(
            malos,
            'estos textos los lee el cliente en la leyenda de las gráficas: %s' % malos)


def helpers_anios():
    """El número de años que se consideran histórico razonable, leído de donde se define."""
    from ..models.pest_incident import ANIOS_DE_HISTORIA_RAZONABLE
    return ANIOS_DE_HISTORIA_RAZONABLE
