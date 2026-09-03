from . import models
from . import controllers

def _post_init_hook_migrate_coordinates(env):
    import logging
    _logger = logging.getLogger(__name__)

    # Only migrate blueprints that actually need it
    # (have traps with absolute coords but no percentage coords).
    # Via ORM, no SQL: 'image' is a Binary(attachment=True), so it has no column
    # in pest_blueprint -- it lives in ir_attachment.
    needs_migration = env['pest.trap'].search_count([
        ('blueprint_id.image', '!=', False),
        ('coord_x', '!=', 0),
        '|', ('coord_x_pct', '=', 0), ('coord_x_pct', '=', False),
    ], limit=1)

    if not needs_migration:
        _logger.info("pest_control: No coordinate migration needed.")
        return

    _logger.info("pest_control: Migrating coordinates for existing blueprints...")
    blueprints = env['pest.blueprint'].search([('image', '!=', False)])
    blueprints.action_migrate_coordinates()
    _logger.info("pest_control: Coordinate migration complete for %d blueprints.", len(blueprints))


def post_init_hook(env):
    """Hook principal post-instalacion: migra coordenadas y asigna company_id."""
    _post_init_hook_migrate_coordinates(env)
    _post_init_hook_assign_company(env)


def _post_init_hook_assign_company(env):
    """Asigna company_id a sedes existentes que no tengan empresa asignada."""
    import logging
    _logger = logging.getLogger(__name__)
    sedes_sin_empresa = env['pest.sede'].search([('company_id', '=', False)])
    if sedes_sin_empresa:
        empresas = env['res.company'].search([])
        if len(empresas) == 1:
            sedes_sin_empresa.write({'company_id': empresas.id})
            _logger.info('post_init_hook: %d sedes asignadas a empresa %s',
                        len(sedes_sin_empresa), empresas.name)
        else:
            _logger.critical(
                'post_init_hook: %d sedes sin empresa y hay multiples empresas. '
                'Asignacion manual requerida.', len(sedes_sin_empresa))
