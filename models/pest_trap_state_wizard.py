from odoo import models, fields, api


class PestTrapStateWizard(models.TransientModel):
    _name = 'pest.trap.state.wizard'
    _description = 'Wizard para registro masivo de estados de trampas'

    blueprint_id = fields.Many2one('pest.blueprint', string='Plano', required=True)
    line_ids = fields.One2many('pest.trap.state.wizard.line', 'wizard_id', string='Líneas')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        blueprint_id = self.env.context.get('default_blueprint_id')
        if blueprint_id:
            blueprint = self.env['pest.blueprint'].browse(blueprint_id)
            lines = []
            for trap in blueprint.trap_ids.filtered('active'):
                lines.append((0, 0, {
                    'trap_id': trap.id,
                    'new_state': False,
                }))
            res['line_ids'] = lines
            res['blueprint_id'] = blueprint_id
        return res

    def action_save_all(self):
        self.ensure_one()
        TrapState = self.env['pest.trap.state']
        vals_list = []
        for line in self.line_ids:
            if line.new_state:
                vals_list.append({
                    'trap_id': line.trap_id.id,
                    'blueprint_id': self.blueprint_id.id,
                    'sede_id': self.blueprint_id.sede_id.id,
                    'state': line.new_state,
                    'observations': line.observations or '',
                    'date': fields.Datetime.now(),
                    'user_id': self.env.uid,
                })
        if vals_list:
            TrapState.create(vals_list)
        return {'type': 'ir.actions.act_window_close'}


class PestTrapStateWizardLine(models.TransientModel):
    _name = 'pest.trap.state.wizard.line'
    _description = 'Línea del wizard de estados de trampas'

    wizard_id = fields.Many2one('pest.trap.state.wizard', string='Wizard', ondelete='cascade')
    trap_id = fields.Many2one('pest.trap', string='Trampa', readonly=True)
    trap_name = fields.Char(related='trap_id.name', string='Nombre', readonly=True)
    current_state_display = fields.Selection(related='trap_id.current_state', string='Estado Actual', readonly=True)
    new_state = fields.Selection([
        ('funciona', 'Funciona'),
        ('en_reparacion', 'En Reparación'),
        ('no_funciona', 'No Funciona'),
        ('sin_registro', 'Sin Registro'),
    ], string='Nuevo Estado')
    observations = fields.Text(string='Observaciones')
