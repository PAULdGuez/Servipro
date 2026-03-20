from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

class TestPestBlueprintWidget(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sede = cls.env['pest.sede'].create({'name': 'Test Sede'})
        cls.trap_type = cls.env['pest.trap.type'].create({'name': 'Test Type'})
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
        self.assertEqual(movement.to_x_pct, 25.5)
        self.assertEqual(movement.to_y_pct, 75.0)
        
    def test_03_override_blueprint_write(self):
        """Test that writing to trap_ids via blueprint triggers widget action."""
        self.trap1.coord_x_pct = 10.0
        self.trap1.coord_y_pct = 10.0
        
        self.blueprint.write({
            'trap_ids': [(1, self.trap1.id, {'coord_x_pct': 30.0, 'coord_y_pct': 40.0})]
        })
        
        self.assertEqual(self.trap1.coord_x_pct, 30.0)
        self.assertEqual(self.trap1.coord_y_pct, 40.0)
        
        movement = self.env['pest.trap.movement'].search([
            ('trap_id', '=', self.trap1.id),
            ('to_x_pct', '=', 30.0),
            ('to_y_pct', '=', 40.0)
        ], limit=1)
        self.assertTrue(bool(movement))
        
    def test_04_get_widget_data(self):
        """Test API method returns correct structure."""
        data = self.blueprint.get_widget_data()
        self.assertIn('image_url', data)
        self.assertIn('traps', data)
        self.assertIn('can_edit', data)
        self.assertEqual(len(data['traps']), 1)
        self.assertEqual(data['traps'][0]['name'], 'TRAP-001')
