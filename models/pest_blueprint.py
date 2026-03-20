import json
import logging
from odoo import api, fields, models
from odoo.tools.image import image_process

_logger = logging.getLogger(__name__)


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
    image_processing_state = fields.Selection([
        ('done', 'Completado'),
        ('pending', 'Pendiente'),
        ('failed', 'Fallido'),
    ], string='Estado Procesamiento', default='done')

    # ── Relations ───────────────────────────────────────────────────
    trap_ids = fields.One2many(
        'pest.trap',
        'blueprint_id',
        string='Trampas',
    )
    zone_ids = fields.One2many('pest.blueprint.zone', 'blueprint_id', string='Zonas')
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
            if rec.image and not rec.image_web:
                rec.image_processing_state = 'pending'
        return records

    def get_widget_data(self):
        self.ensure_one()

        # Get incident counts per trap using Odoo 19 _read_group API
        incident_counts = {}
        try:
            trap_incident_data = self.env['pest.incident']._read_group(
                domain=[('trap_id', 'in', self.trap_ids.ids)],
                groupby=['trap_id'],
                aggregates=['__count'],
            )
            incident_counts = {trap.id: count for trap, count in trap_incident_data}
        except Exception:
            pass

        trap_list = []
        for trap in self.trap_ids:
            trap_list.append({
                'id': trap.id,
                'name': trap.name or '',
                'coord_x_pct': trap.coord_x_pct or 0.0,
                'coord_y_pct': trap.coord_y_pct or 0.0,
                'current_state': trap.current_state or 'sin_registro',
                'trap_type_id': trap.trap_type_id.id if trap.trap_type_id else False,
                'trap_type_name': trap.trap_type_id.name if trap.trap_type_id else '',
                'trap_type_icon': (trap.trap_type_id.icon or 'fa-crosshairs') if trap.trap_type_id else 'fa-crosshairs',
                'sede_id': trap.sede_id.id if trap.sede_id else False,
                'incident_count': incident_counts.get(trap.id, 0),
            })

        # Build trap type summary for the legend
        type_counts = {}
        for t in trap_list:
            tid = t['trap_type_id']
            if not tid:
                continue
            if tid not in type_counts:
                type_counts[tid] = {
                    'id': tid,
                    'name': t['trap_type_name'],
                    'icon': t['trap_type_icon'],
                    'count': 0,
                }
            type_counts[tid]['count'] += 1

        # Build zone list
        zones = []
        for zone in self.zone_ids:
            try:
                import json as _json
                points = _json.loads(zone.points_data)
            except Exception:
                points = []
            zones.append({
                'id': zone.id,
                'name': zone.name or '',
                'points': points,
                'color': zone.color or '#3498db55',
            })

        return {
            'image_url': f'/web/image/pest.blueprint/{self.id}/image_web',
            'traps': trap_list,
            'trap_types': list(type_counts.values()),
            'can_edit': self.can_user_edit_traps(),
            '__last_update': self.write_date.isoformat() if self.write_date else '',
            'zones': zones,
        }


    def can_user_edit_traps(self):
        self.ensure_one()
        return self.env.user.has_group('pest_control.group_pest_technician')

    def write(self, vals):
        res = super().write(vals)
        if 'image' in vals and 'image_web' not in vals:
            for rec in self:
                if rec.image:
                    rec.image_processing_state = 'pending'
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

    @api.model
    def _process_pending_images(self):
        """Cron job: process pending blueprint images in batch."""
        records = self.search([('image_processing_state', '=', 'pending')], limit=50)
        for rec in records:
            try:
                rec._process_image_background()
                rec.image_processing_state = 'done'
            except Exception:
                _logger.exception('Error processing image for blueprint %s', rec.id)
                rec.image_processing_state = 'failed'

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
