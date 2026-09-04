"""Restricciones de datos y errores que no deben disfrazarse de ceros.

Criterios C03, C04 y C05 de `criterios-bloque-1.md`.

Cada guarda se prueba POR LOS DOS LADOS: que impida lo que debe, y que permita
lo legitimo. Sin la segunda mitad, una restriccion demasiado ancha bloquea casos
validos y nadie lo nota hasta que un usuario se queja.
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError
from odoo.tools import mute_logger


class TestPestIntegridad(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sede = cls.env['pest.sede'].create({'name': 'Sede integridad'})
        cls.plano_1 = cls.env['pest.blueprint'].create({'name': 'Plano uno', 'sede_id': cls.sede.id})
        cls.plano_2 = cls.env['pest.blueprint'].create({'name': 'Plano dos', 'sede_id': cls.sede.id})
        cls.tipo = cls.env['pest.trap.type'].create({'name': 'Tipo integridad', 'code': 'tipo_int'})

    def _trampa(self, nombre, plano):
        return self.env['pest.trap'].create({
            'name': nombre, 'sede_id': self.sede.id, 'blueprint_id': plano.id,
            'trap_type_id': self.tipo.id})

    # ------------------------------------------------------------------ C04

    @mute_logger('odoo.sql_db')
    def test_c04_nombre_de_trampa_unico_por_plano(self):
        """Lo que la restriccion DEBE impedir."""
        self._trampa('TR-01', self.plano_1)
        with self.assertRaises(IntegrityError, msg='se pudo repetir el nombre en el mismo plano'):
            with self.cr.savepoint():
                self._trampa('TR-01', self.plano_1)

    def test_c04_mismo_nombre_en_otro_plano_si_se_permite(self):
        """Lo que la restriccion NO debe impedir: es legitimo y frecuente."""
        self._trampa('TR-01', self.plano_1)
        otra = self._trampa('TR-01', self.plano_2)
        self.assertTrue(otra.id, 'la restriccion bloquea de mas: TR-01 en dos planos es valido')

    # ------------------------------------------------------------------ C05

    @mute_logger('odoo.sql_db')
    def test_c05_catalogo_de_plagas_sin_codigos_repetidos(self):
        self.env['pest.plague.type'].create({'name': 'Plaga uno', 'code': 'codigo_repetido'})
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.env['pest.plague.type'].create({'name': 'Plaga dos', 'code': 'codigo_repetido'})

    @mute_logger('odoo.sql_db')
    def test_c05_catalogo_de_trampas_sin_codigos_repetidos(self):
        self.env['pest.trap.type'].create({'name': 'Tipo uno', 'code': 'otro_repetido'})
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.env['pest.trap.type'].create({'name': 'Tipo dos', 'code': 'otro_repetido'})

    @mute_logger('odoo.sql_db')
    def test_c05_ubicaciones_sin_nombres_repetidos(self):
        self.env['pest.zone'].create({'name': 'Zona repetida'})
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.env['pest.zone'].create({'name': 'Zona repetida'})

    # ------------------------------------------------------------------ nombres

    def test_trampas_sin_plano_no_comparten_nombre(self):
        """Sin plano no hay serie por (plano, tipo): caen a la secuencia generica.
        Cuando esa secuencia no existia, TODAS se llamaban igual."""
        nombres = [self.env['pest.trap'].create({
            'sede_id': self.sede.id, 'trap_type_id': self.tipo.id}).name for _ in range(3)]
        self.assertEqual(len(set(nombres)), 3, 'tres trampas sin plano recibieron nombres repetidos')
        self.assertNotIn('TRP-NEW', nombres, 'volvio el nombre literal de respaldo')

    # ------------------------------------------------------------------ C03

    def test_c03_un_fallo_al_contar_organismos_no_devuelve_cero(self):
        """Antes, cualquier excepcion aqui se tragaba y salia 0, que el usuario lee
        como 'esta trampa no ha capturado nada'. Se comprueba el COMPORTAMIENTO:
        con datos reales el total tiene que ser el real, no un cero de consuelo."""
        trampa = self._trampa('TR-CONTEO', self.plano_1)
        for cantidad in (3, 7):
            self.env['pest.incident'].create({
                'trap_id': trampa.id, 'sede_id': self.sede.id,
                'incident_type': 'captura', 'organism_count': cantidad})
        datos = trampa.get_detail_data()
        self.assertEqual(datos.get('total_organisms'), 10,
                         'el total de organismos no cuadra con las incidencias reales')

    def test_c03_sin_incidencias_el_total_es_cero_de_verdad(self):
        """El caso contrario: un cero legitimo debe seguir siendo cero."""
        trampa = self._trampa('TR-VACIA', self.plano_1)
        self.assertEqual(trampa.get_detail_data().get('total_organisms'), 0)
