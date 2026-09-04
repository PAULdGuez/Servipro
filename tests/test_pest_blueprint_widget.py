from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

class TestPestBlueprintWidget(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sede = cls.env['pest.sede'].create({'name': 'Test Sede'})
        cls.trap_type = cls.env['pest.trap.type'].create({'name': 'Test Type', 'code': 'test'})
        cls.blueprint = cls.env['pest.blueprint'].create({
            'name': 'Test Blueprint',
            'sede_id': cls.sede.id,
            # 1x1 pixel PNG base64 representation
            'image': b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=', 
        })
        cls.trap1 = cls.env['pest.trap'].create({
            'name': 'TRAP-001',
            'sede_id': cls.sede.id,
            'blueprint_id': cls.blueprint.id,
            'trap_type_id': cls.trap_type.id,
            'coord_x': 100,
            'coord_y': 100,
        })
        
    def test_01_action_migrate_coordinates(self):
        """Test the migration script from absolute to percentage coordinates."""
        self.blueprint.action_migrate_coordinates()
        
        # 1x1 image -> width=1, height=1. Trap at 100,100 -> coordx = 100/1 * 100 = 10000 %
        self.assertEqual(self.trap1.coord_x_pct, 10000.0)
        self.assertEqual(self.trap1.coord_y_pct, 10000.0)
        
    def test_02_action_move_to_from_widget(self):
        """Test server-side validation and logging of trap movement."""
        with self.assertRaises(UserError):
            self.trap1.action_move_to_from_widget(-10.0, 50.0)
            
        with self.assertRaises(UserError):
            self.trap1.action_move_to_from_widget(110.0, 50.0)
            
        self.trap1.action_move_to_from_widget(25.5, 75.0)
        self.assertEqual(self.trap1.coord_x_pct, 25.5)
        self.assertEqual(self.trap1.coord_y_pct, 75.0)
        
        movement = self.env['pest.trap.movement'].search([('trap_id', '=', self.trap1.id)], limit=1)
        self.assertTrue(bool(movement))
        self.assertEqual(movement.x_to_pct, 25.5)
        self.assertEqual(movement.y_to_pct, 75.0)
        
    def test_03_action_move_to_creates_movement_record(self):
        """Test that action_move_to_from_widget moves trap and creates a movement record."""
        self.trap1.write({'coord_x_pct': 10.0, 'coord_y_pct': 10.0})

        self.trap1.action_move_to_from_widget(30.0, 40.0)

        self.assertEqual(self.trap1.coord_x_pct, 30.0)
        self.assertEqual(self.trap1.coord_y_pct, 40.0)

        movement = self.env['pest.trap.movement'].search([
            ('trap_id', '=', self.trap1.id),
            ('x_to_pct', '=', 30.0),
            ('y_to_pct', '=', 40.0),
        ], limit=1)
        self.assertTrue(bool(movement))
        self.assertEqual(movement.x_from_pct, 10.0)
        self.assertEqual(movement.y_from_pct, 10.0)
        
    def test_04_get_widget_data(self):
        """Una trampa SIN posicion no se dibuja: se separa aparte.

        Antes se dibujaban en la esquina superior izquierda, todas encima de todas — con los
        datos reales fueron 2,139 trampas amontonadas en un punto, y el plano no servia para
        nada. Ahora las que no tienen posicion salen en `traps_sin_ubicar`, que la interfaz
        muestra como un contador «N por ubicar».

        Se comprueban LOS DOS LADOS: que la sin posicion no se cuele en el dibujo, y que la
        que SI la tiene se siga dibujando. Probar solo el primero dejaria pasar un arreglo que
        se lleva por delante tambien a las buenas.
        """
        data = self.blueprint.get_widget_data()
        self.assertIn('image_url', data)
        self.assertIn('traps', data)
        self.assertIn('can_edit', data)

        # la del setUp tiene coord_x/coord_y pero NO porcentaje: no se puede dibujar
        self.assertEqual(self.trap1.coord_x_pct, 0.0)
        self.assertEqual(len(data['traps']), 0)
        self.assertEqual(len(data['traps_sin_ubicar']), 1)
        self.assertEqual(data['traps_sin_ubicar'][0]['name'], 'TRAP-001')

        # y con posicion de verdad, se dibuja
        self.trap1.write({'coord_x_pct': 25.5, 'coord_y_pct': 75.0})
        data = self.blueprint.get_widget_data()
        self.assertEqual(len(data['traps']), 1)
        self.assertEqual(data['traps'][0]['name'], 'TRAP-001')
        self.assertEqual(len(data['traps_sin_ubicar']), 0)
