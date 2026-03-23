from odoo import models, fields, api


class PestTrapMovementWizard(models.TransientModel):
    _name = 'pest.trap.movement.wizard'
    _description = 'Wizard para mover trampa'

    trap_id = fields.Many2one('pest.trap', string='Trampa', required=True, readonly=True)
    trap_name = fields.Char(related='trap_id.name', string='ID Trampa', readonly=True)
    trap_type_name = fields.Char(related='trap_id.trap_type_id.name', string='Tipo de Trampa', readonly=True)
    blueprint_id = fields.Many2one('pest.blueprint', string='Plano', required=True, readonly=True)
    zone_from_id = fields.Many2one('pest.zone', string='Zona Anterior', readonly=True)
    zone_to_id = fields.Many2one('pest.zone', string='Zona Nueva')
    new_x_pct = fields.Float(string='Nueva X (%)', readonly=True)
    new_y_pct = fields.Float(string='Nueva Y (%)', readonly=True)
    comment = fields.Text(string='Motivo del Movimiento')
    user_id = fields.Many2one('res.users', string='Movido por', default=lambda self: self.env.user, readonly=True)

    def action_confirm_move(self):
        self.ensure_one()
        trap = self.trap_id
        # Execute the move
        old_x = trap.coord_x_pct
        old_y = trap.coord_y_pct
        
        trap.write({
            'coord_x_pct': self.new_x_pct,
            'coord_y_pct': self.new_y_pct,
        })
        
        # Update zone if selected
        if self.zone_to_id:
            trap.zone_id = self.zone_to_id
        
        # Create movement record
        self.env['pest.trap.movement'].create({
            'trap_id': trap.id,
            'blueprint_id': self.blueprint_id.id,
            'movement_type': 'widget_drag',
            'zone_from': self.zone_from_id.name if self.zone_from_id else '',
            'zone_to': self.zone_to_id.name if self.zone_to_id else '',
            'x_from_pct': old_x,
            'y_from_pct': trap.coord_y_pct if old_y == 0 else old_y,
            'x_to_pct': self.new_x_pct,
            'y_to_pct': self.new_y_pct,
            'comment': self.comment or '',
        })
        
        # Auto-detect zone if not manually selected
        if not self.zone_to_id and trap.blueprint_id:
            zone_name = self.env['pest.blueprint.zone'].find_zone_for_coords(
                trap.blueprint_id.id, self.new_x_pct, self.new_y_pct
            )
            if zone_name:
                trap.location = zone_name

        # Log movement to blueprint chatter
        if self.blueprint_id:
            self.blueprint_id.message_post(
                body='Trampa %s movida. Motivo: %s' % (
                    trap.name,
                    self.comment or 'Sin motivo',
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

        return {'type': 'ir.actions.act_window_close'}
