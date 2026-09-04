"""Aislamiento entre clientes y permisos por rol.

Cada prueba corresponde a un criterio de aceptación de
`Workspaces/servipro/planes/criterios-bloque-1.md`, y lleva su número en el nombre
para que un rojo diga CUÁL criterio se rompió.

Dos reglas de la casa que se aplican aquí y no son opcionales:
  1. Los permisos se ejercen con el usuario del rol, nunca con el administrador,
     que no los ejerce.
  2. `invalidate_cache()` antes de leer. Sin eso el valor sale del caché de quien
     lo cargó y la prueba dice lo contrario de la verdad — ya pasó en este proyecto.
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError

POLIGONO = '[{"x":10,"y":10},{"x":90,"y":10},{"x":50,"y":90}]'


class TestPestSeguridad(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Comp = cls.env['res.company']
        cls.emp_a = Comp.create({'name': 'Cliente A de prueba'})
        cls.emp_b = Comp.create({'name': 'Cliente B de prueba'})

        cls.g_cliente = cls.env.ref('pest_control.group_pest_client')
        cls.g_tecnico = cls.env.ref('pest_control.group_pest_technician')
        cls.g_interno = cls.env.ref('base.group_user')
        cls.tipo = cls.env['pest.trap.type'].create({'name': 'Tipo prueba', 'code': 'tipo_prueba'})
        cls.plaga = cls.env['pest.plague.type'].create({'name': 'Plaga prueba', 'code': 'plaga_prueba'})

        cls.usr_a = cls._usuario('cliente.a.prueba', cls.emp_a, cls.g_cliente)
        cls.usr_b = cls._usuario('cliente.b.prueba', cls.emp_b, cls.g_cliente)
        cls.tec_a = cls._usuario('tecnico.a.prueba', cls.emp_a, cls.g_tecnico)

        cls.sede_a, cls.plano_a, cls.trampa_a, cls.zona_a = cls._escenario(cls.emp_a, 'A')
        cls.sede_b, cls.plano_b, cls.trampa_b, cls.zona_b = cls._escenario(cls.emp_b, 'B')

        # 🔑 Desde el corte por sede (D9), un usuario de cliente necesita sus sedes asignadas: el
        # corte es **fail-closed** y sin ellas no ve nada, ni de su propia empresa. Los usuarios
        # se crean arriba, antes que las sedes, así que la asignación va aquí.
        #
        # No es adaptar la prueba para que pase: es que un cliente sin sedes asignadas **no es un
        # escenario real**, es un alta a medias. Lo que estas pruebas comprueban —que A no vea lo
        # de B— sigue intacto, y ahora sobre un usuario bien configurado.
        cls.usr_a.pest_sede_ids = [(6, 0, cls.sede_a.ids)]
        cls.tec_a.pest_sede_ids = [(6, 0, cls.sede_a.ids)]
        cls.usr_b.pest_sede_ids = [(6, 0, cls.sede_b.ids)]

    @classmethod
    def _usuario(cls, login, empresa, grupo):
        return cls.env['res.users'].create({
            'name': login, 'login': login,
            'company_id': empresa.id, 'company_ids': [(6, 0, [empresa.id])],
            'group_ids': [(6, 0, [cls.g_interno.id, grupo.id])],
        })

    @classmethod
    def _escenario(cls, empresa, etiqueta):
        sede = cls.env['pest.sede'].create({'name': 'Sede %s' % etiqueta, 'company_id': empresa.id})
        plano = cls.env['pest.blueprint'].create({'name': 'Plano %s' % etiqueta, 'sede_id': sede.id})
        trampa = cls.env['pest.trap'].create({
            'name': 'TR-01', 'sede_id': sede.id, 'blueprint_id': plano.id,
            'trap_type_id': cls.tipo.id, 'coord_x_pct': 50, 'coord_y_pct': 50})
        zona = cls.env['pest.blueprint.zone'].create({
            'name': 'Zona %s' % etiqueta, 'blueprint_id': plano.id, 'points_data': POLIGONO})
        return sede, plano, trampa, zona

    # ------------------------------------------------------------------ C01

    def test_c01_cliente_abre_plano_y_ve_trampas(self):
        """Un cliente puede abrir el plano de su planta y ver sus trampas."""
        self.env.invalidate_all()
        datos = self.plano_a.with_user(self.usr_a).get_widget_data()
        self.assertIn('traps', datos, 'el widget del plano no devolvio las trampas')
        self.assertTrue(datos['traps'], 'el plano salio sin trampas y si las tiene')

    def test_c01_cliente_lee_los_catalogos_que_el_plano_necesita(self):
        """Sin estos dos catalogos el plano no puede dibujarse: fue el bug original."""
        self.env.invalidate_all()
        self.assertTrue(self.env['pest.trap.type'].with_user(self.usr_a).search_count([]) >= 0)
        self.assertTrue(self.env['pest.plague.type'].with_user(self.usr_a).search_count([]) >= 0)

    def test_c01_cliente_no_puede_modificar(self):
        """El caso contrario: ver no es editar."""
        with self.assertRaises(AccessError, msg='un Cliente pudo modificar una sede'):
            self.sede_a.with_user(self.usr_a).write({'name': 'renombrada'})

    # ------------------------------------------------------------------ C06

    def test_c06_un_cliente_no_ve_las_sedes_de_otro(self):
        self.env.invalidate_all()
        visibles = self.env['pest.sede'].with_user(self.usr_a).search([])
        self.assertIn(self.sede_a, visibles, 'no ve ni su propia sede')
        self.assertNotIn(self.sede_b, visibles, 'FUGA: ve la sede de otro cliente')

    def test_c06_tampoco_leyendo_por_id_directo(self):
        """Que no salga en la lista no basta: hay que probar la puerta de atras."""
        self.env.invalidate_all()
        with self.assertRaises(AccessError, msg='FUGA: leyo por ID la sede de otro cliente'):
            self.env['pest.sede'].with_user(self.usr_a).browse(self.sede_b.id).read(['name'])

    def test_c06_las_zonas_del_plano_tambien_se_aislan(self):
        """Se coló durante meses: la zona no tiene company_id propio, lo hereda del plano."""
        self.env.invalidate_all()
        visibles = self.env['pest.blueprint.zone'].with_user(self.usr_a).search([])
        self.assertIn(self.zona_a, visibles, 'no ve ni su propia zona')
        self.assertNotIn(self.zona_b, visibles, 'FUGA: ve las zonas del plano de otro cliente')

    def test_c06_el_tecnico_puede_editar_pero_no_borrar(self):
        self.env.invalidate_all()
        self.sede_a.with_user(self.tec_a).write({'name': 'Sede A renombrada por el tecnico'})
        with self.assertRaises(AccessError, msg='un Tecnico pudo borrar'):
            self.sede_a.with_user(self.tec_a).unlink()
