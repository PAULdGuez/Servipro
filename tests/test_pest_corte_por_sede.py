"""El corte por sede DENTRO de una empresa — decisión D9, fail-closed.

Las reglas de empresa cortan «que Bimbo no vea a Totis». Éstas cortan «que el jefe de planta de
Azcapotzalco no vea Villahermosa», que con 16 sedes en Grupo Bimbo es el corte que de verdad se
pide.

🔴 **Estas pruebas existen porque el corte falló CUATRO veces pareciendo instalado**, y las cuatro
sin dar un solo error: la regla se veía correcta en la pantalla de reglas y no recortaba a nadie.
Un permiso que no se comprueba contando registros con el usuario real es una hipótesis.
"""

from odoo.tests.common import TransactionCase


class TestCortePorSede(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.empresa = cls.env['res.company'].create({'name': 'Panadería del corte'})
        cls.norte = cls.env['pest.sede'].create({'name': 'Planta Norte', 'company_id': cls.empresa.id})
        cls.sur = cls.env['pest.sede'].create({'name': 'Planta Sur', 'company_id': cls.empresa.id})
        cls.tipo = cls.env['pest.trap.type'].create({'name': 'Tipo corte', 'code': 'corte'})
        for sede, cuantas in ((cls.norte, 3), (cls.sur, 5)):
            plano = cls.env['pest.blueprint'].create({'name': 'Plano ' + sede.name, 'sede_id': sede.id})
            for i in range(cuantas):
                cls.env['pest.trap'].create({
                    'name': '%s-%d' % (sede.name[:4], i), 'sede_id': sede.id,
                    'blueprint_id': plano.id, 'trap_type_id': cls.tipo.id,
                })

    def _usuario(self, login, sedes=None, personal=False):
        grupos = [(4, self.env.ref('pest_control.group_pest_client').id)]
        if personal:
            grupos.append((4, self.env.ref('pest_control.group_pest_staff').id))
        return self.env['res.users'].create({
            'name': login, 'login': login,
            'company_id': self.empresa.id, 'company_ids': [(6, 0, [self.empresa.id])],
            'group_ids': grupos,
            'pest_sede_ids': [(6, 0, (sedes or self.env['pest.sede']).ids)],
        })

    def _ve(self, usuario, modelo='pest.trap'):
        self.env.invalidate_all()          # sin esto se lee del caché del admin y la prueba miente
        return self.env[modelo].with_user(usuario).search_count([])

    def test_s01_solo_ve_las_trampas_de_SU_planta(self):
        """El caso central: dos plantas de la misma empresa, y solo se ve una."""
        solo_norte = self._usuario('corte.norte', self.norte)
        self.assertEqual(self._ve(solo_norte), 3)
        self.assertEqual(self._ve(solo_norte, 'pest.sede'), 1)

    def test_s02_con_las_DOS_plantas_ve_todo(self):
        """La prueba del caso contrario: un corte que recorta de más no se nota si solo
        pruebas que recorta."""
        ambas = self._usuario('corte.ambas', self.norte | self.sur)
        self.assertEqual(self._ve(ambas), 8)
        self.assertEqual(self._ve(ambas, 'pest.sede'), 2)

    def test_s03_SIN_sedes_no_ve_nada_ni_de_su_empresa(self):
        """Fail-closed. Al revés, un alta a medias sería una fuga que nadie descubre."""
        sin_nada = self._usuario('corte.sinnada')
        self.assertEqual(self._ve(sin_nada), 0)
        self.assertEqual(self._ve(sin_nada, 'pest.sede'), 0)
        self.assertEqual(self._ve(sin_nada, 'pest.incident'), 0)

    def test_s04_el_personal_de_servipro_ve_todo_sin_asignarle_nada(self):
        """Y sin ninguna sede marcada: es lo que distingue al personal del cliente.

        Falló una vez: al hacer globales las reglas, el personal fue el único que dejó de ver
        todo, porque una regla global se evalúa siempre.
        """
        staff = self._usuario('corte.staff', personal=True)
        self.assertTrue(staff.pest_es_personal)
        self.assertFalse(staff.pest_sede_ids)
        self.assertEqual(self._ve(staff), 8)

    def test_s05_no_se_puede_entrar_por_la_puerta_de_atras(self):
        """Pedir el registro por su id directo tiene que rebotar igual.

        Que la lista no lo muestre no es impedir: por URL, por RPC o por importación se entra
        por debajo de la pantalla.
        """
        from odoo.exceptions import AccessError
        solo_norte = self._usuario('corte.puerta', self.norte)
        ajena = self.env['pest.trap'].search([('sede_id', '=', self.sur.id)], limit=1)
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            ajena.with_user(solo_norte).name

    def test_s06_una_sede_ARCHIVADA_asignada_sigue_contando(self):
        """Costó tres intentos: lo archivado desaparece al buscar, al guardar Y al leer.

        Una sede archivada conserva sus trampas e incidencias; si el corte la pierde, activar
        esta función le quita al usuario histórico que ayer veía.
        """
        usuario = self._usuario('corte.archivada', self.norte | self.sur)
        self.sur.active = False
        self.env.invalidate_all()
        self.assertEqual(self._ve(usuario), 8,
                         'archivar una sede no puede esconder sus trampas a quien la tiene asignada')

    def test_s07_no_se_puede_asignar_una_planta_de_OTRA_empresa(self):
        """La vista filtra el desplegable, pero un dominio de vista no es una garantía."""
        from odoo.exceptions import ValidationError
        otra = self.env['res.company'].create({'name': 'Empresa ajena del corte'})
        suya = self.env['pest.sede'].create({'name': 'Planta ajena', 'company_id': otra.id})
        usuario = self._usuario('corte.ajena', self.norte)
        with self.assertRaises(ValidationError):
            usuario.pest_sede_ids = [(4, suya.id)]

    def test_s08_quitar_todas_las_sedes_quita_TAMBIEN_las_archivadas(self):
        """Que lo archivado no se pueda quitar desde la pantalla es un agujero, no un detalle.

        Un Many2many escribe sobre lo que ve, y por defecto no ve los archivados: un `(6, 0, ...)`
        que pretende reemplazar toda la lista **deja dentro las sedes archivadas**. Quien quita
        todas las sedes de un usuario en la ficha cree habérselo quitado todo, y el usuario
        conserva acceso al histórico de las archivadas.

        Medido en la base real: al dejar a un usuario con una sola planta, conservó 3 sedes
        archivadas y 139 trampas de más.
        """
        usuario = self._usuario('corte.quitar', self.norte | self.sur)
        self.sur.active = False
        self.env.invalidate_all()

        # el gesto de la pantalla: reemplazar la lista por una sola sede
        usuario.pest_sede_ids = [(6, 0, self.norte.ids)]
        self.env.invalidate_all()

        con_archivadas = usuario.with_context(active_test=False).pest_sede_ids
        self.assertEqual(
            len(con_archivadas), 1,
            'la sede archivada sobrevivió al reemplazo: el usuario conserva acceso invisible',
        )
        self.assertEqual(self._ve(usuario), 3, 'solo debería ver las trampas de Planta Norte')
