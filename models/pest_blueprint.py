from odoo import api, fields, models
from odoo.tools.image import image_process


class PestBlueprint(models.Model):
    _name = 'pest.blueprint'
    _description = 'Plano de Planta'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(
        string='Nombre del Plano',
        required=True,
    )
    sede_id = fields.Many2one(
        'pest.sede',
        string='Sede',
        required=True,
        ondelete='cascade',
    )
    description = fields.Text(string='Descripción')
    image = fields.Binary(
        string='Imagen del Plano',
        attachment=True,
    )
    image_filename = fields.Char(string='Nombre del Archivo')
    image_web = fields.Binary(
        string='Imagen Optimizada (Web)',
        attachment=True,
    )
    active = fields.Boolean(default=True)

    # ── Relations ───────────────────────────────────────────────────
    trap_ids = fields.One2many(
        'pest.trap',
        'blueprint_id',
        string='Trampas',
    )
    evidence_ids = fields.One2many(
        'pest.evidence',
        'blueprint_id',
        string='Evidencias',
    )

    # ── Computed ────────────────────────────────────────────────────
    incident_ids = fields.One2many(
        'pest.incident',
        'blueprint_id',
        string='Incidencias',
    )
    trap_count = fields.Integer(
        string='Nº Trampas',
        compute='_compute_trap_count',
        store=True,
    )

    # JSON payload for frontend rendering (zones, renderedWidth, etc.)
    state_data = fields.Text(string='Datos del Estado JSON')

    @api.depends('trap_ids')
    def _compute_trap_count(self):
        for rec in self:
            rec.trap_count = len(rec.trap_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('image'):
                vals['image_web'] = image_process(vals['image'], size=(1920, 1920), quality=85)
        return super().create(vals_list)

    def get_widget_data(self):
        self.ensure_one()
        traps = []
        for trap in self.trap_ids:
            traps.append({
                'id': trap.id,
                'name': trap.name,
                'coord_x_pct': trap.coord_x_pct,
                'coord_y_pct': trap.coord_y_pct,
                'current_state': trap.current_state,
                'trap_type_name': trap.trap_type_id.name,
            })
        return {
            'image_url': f'/web/image/pest.blueprint/{self.id}/image_web',
            'traps': traps,
            'can_edit': self.can_user_edit_traps(),
        }

    def can_user_edit_traps(self):
        self.ensure_one()
        return self.env.user.has_group('pest_control.group_pest_technician')

    def write(self, vals):
        if vals.get('image'):
            vals['image_web'] = image_process(vals['image'], size=(1920, 1920), quality=85)
            
        if 'trap_ids' in vals:
            trap_commands = vals['trap_ids']
            new_commands = []
            for cmd in trap_commands:
                if cmd[0] == 1:
                    trap_id = cmd[1]
                    trap_vals = cmd[2]
                    if 'coord_x_pct' in trap_vals or 'coord_y_pct' in trap_vals:
                        trap = self.env['pest.trap'].browse(trap_id)
                        new_x = trap_vals.pop('coord_x_pct', trap.coord_x_pct)
                        new_y = trap_vals.pop('coord_y_pct', trap.coord_y_pct)
                        if new_x != trap.coord_x_pct or new_y != trap.coord_y_pct:
                            trap.action_move_to_from_widget(new_x, new_y)
                    if trap_vals:
                        new_commands.append((1, trap_id, trap_vals))
                else:
                    new_commands.append(cmd)
            vals['trap_ids'] = new_commands

        return super().write(vals)

    def action_migrate_coordinates(self):
        import base64
        import io
        import json
        from PIL import Image
        for blueprint in self:
            if not blueprint.image or not blueprint.trap_ids:
                continue
            try:
                image_data = base64.b64decode(blueprint.image)
                image = Image.open(io.BytesIO(image_data))
                width, height = image.size
                
                rendered_width = width
                rendered_height = height
                if blueprint.state_data:
                    try:
                        state = json.loads(blueprint.state_data)
                        if 'renderedWidth' in state and 'renderedHeight' in state:
                            rendered_width = state.get('renderedWidth', width)
                            rendered_height = state.get('renderedHeight', height)
                    except Exception:
                        pass
                
                for trap in blueprint.trap_ids:
                    if not trap.coord_x_pct and trap.coord_x and rendered_width:
                        trap.coord_x_pct = (trap.coord_x / rendered_width) * 100.0
                    if not trap.coord_y_pct and trap.coord_y and rendered_height:
                        trap.coord_y_pct = (trap.coord_y / rendered_height) * 100.0
            except Exception:
                pass
