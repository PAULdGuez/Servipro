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

    heatmap_umbral_bajo = fields.Integer(string='Umbral Bajo (Heatmap)', default=5,
        help='Cantidad de organismos considerada nivel bajo')
    heatmap_umbral_medio = fields.Integer(string='Umbral Medio (Heatmap)', default=20,
        help='Cantidad de organismos considerada nivel medio')
    heatmap_umbral_alto = fields.Integer(string='Umbral Alto (Heatmap)', default=50,
        help='Cantidad de organismos considerada nivel alto/critico')

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
    incident_count = fields.Integer(
        compute='_compute_incident_count',
        string='Nº Incidencias',
    )

    def _compute_incident_count(self):
        for rec in self:
            rec.incident_count = sum(rec.trap_ids.mapped('incident_count'))

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
                try:
                    rec._process_image_background()
                    rec.image_processing_state = 'done'
                except Exception:
                    rec.image_processing_state = 'pending'
        return records

    def get_widget_data(self, limit=200, offset=0):
        self.ensure_one()

        # Total count before pagination
        total_trap_count = len(self.trap_ids)

        # Apply limit/offset to trap recordset
        if limit:
            trap_ids_to_read = self.trap_ids[offset:offset + limit]
        else:
            trap_ids_to_read = self.trap_ids

        # Batch incident counts (already using _read_group from previous fix)
        incident_counts = {}
        try:
            data = self.env['pest.incident']._read_group(
                [('trap_id', 'in', self.trap_ids.ids)],
                ['trap_id'], ['__count'])
            incident_counts = {trap.id: count for trap, count in data}
        except Exception:
            pass

        # Batch read all trap data in one query (paginated)
        traps_data = trap_ids_to_read.read([
            'name', 'coord_x_pct', 'coord_y_pct', 'current_state',
            'trap_type_id', 'sede_id', 'zone_id',
        ])

        # Batch read trap types
        type_ids = list(set(
            t['trap_type_id'][0] for t in traps_data if t.get('trap_type_id')
        ))
        types_map = {}
        if type_ids:
            types_data = self.env['pest.trap.type'].search_read(
                [('id', 'in', type_ids)], ['name', 'icon'])
            types_map = {t['id']: t for t in types_data}

        trap_list = []
        for t in traps_data:
            tt = types_map.get(t['trap_type_id'][0]) if t.get('trap_type_id') else {}
            trap_list.append({
                'id': t['id'],
                'name': t.get('name') or '',
                'coord_x_pct': t.get('coord_x_pct') or 0.0,
                'coord_y_pct': t.get('coord_y_pct') or 0.0,
                'current_state': t.get('current_state') or 'sin_registro',
                'trap_type_id': t['trap_type_id'][0] if t.get('trap_type_id') else False,
                'trap_type_name': tt.get('name', ''),
                'trap_type_icon': tt.get('icon', 'fa-crosshairs') or 'fa-crosshairs',
                'sede_id': t['sede_id'][0] if t.get('sede_id') else False,
                'zone_id': t['zone_id'][0] if t.get('zone_id') else False,
                'incident_count': incident_counts.get(t['id'], 0),
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
            'sede_id': self.sede_id.id if self.sede_id else False,
            'heatmap_config': {
                'umbral_bajo': self.heatmap_umbral_bajo or 5,
                'umbral_medio': self.heatmap_umbral_medio or 20,
                'umbral_alto': self.heatmap_umbral_alto or 50,
            },
            'total_trap_count': total_trap_count,
            'trap_offset': offset,
            'trap_limit': limit,
            'has_more_traps': bool(limit) and (offset + limit) < total_trap_count,
        }


    def action_view_traps(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Trampas',
            'res_model': 'pest.trap',
            'view_mode': 'list,form',
            'domain': [('blueprint_id', '=', self.id)],
            'context': {'default_blueprint_id': self.id, 'default_sede_id': self.sede_id.id},
        }

    def action_view_incidents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Incidencias',
            'res_model': 'pest.incident',
            'view_mode': 'list,form,graph,pivot',
            'domain': [('trap_id', 'in', self.trap_ids.ids)],
            'context': {'default_blueprint_id': self.id, 'default_sede_id': self.sede_id.id},
        }

    def action_view_dashboard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'pest_control.dashboard',
            'name': 'Gráficas - ' + self.name,
            'context': {
                'default_sede_id': self.sede_id.id,
                'default_blueprint_id': self.id,
            },
        }

    def can_user_edit_traps(self):
        self.ensure_one()
        return self.env.user.has_group('pest_control.group_pest_technician')

    def write(self, vals):
        res = super().write(vals)
        if 'image' in vals and 'image_web' not in vals:
            for rec in self:
                if rec.image:
                    try:
                        rec._process_image_background()
                        rec.image_processing_state = 'done'
                    except Exception:
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
