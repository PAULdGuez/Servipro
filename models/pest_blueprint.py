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
            rec.trap_count = 0
            
        if not self.ids:
            return
            
        try:
            trap_data = self.env['pest.trap']._read_group([('blueprint_id', 'in', self.ids)], ['blueprint_id'], ['__count'])
            trap_counts = {bp.id: count for bp, count in trap_data}
        except Exception:
            trap_counts = {g['blueprint_id'][0]: g['blueprint_id_count'] for g in self.env['pest.trap'].read_group([('blueprint_id', 'in', self.ids)], ['blueprint_id'], ['blueprint_id'])}
            
        for rec in self:
            rec.trap_count = trap_counts.get(rec.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.image:
                rec._process_image_background()
        return records

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
        res = super().write(vals)
        if 'image' in vals and 'image_web' not in vals:
            for rec in self:
                rec._process_image_background()
        return res

    def _process_image_background(self):
        self.ensure_one()
        if self.image:
            try:
                processed = image_process(self.image, size=(1920, 1920), quality=85)
                super(PestBlueprint, self).write({'image_web': processed})
            except Exception:
                # If processing fails, use the original image as-is
                super(PestBlueprint, self).write({'image_web': self.image})

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
