from . import models
from . import controllers

def _post_init_hook_migrate_coordinates(env):
    import logging
    _logger = logging.getLogger(__name__)

    # Only migrate blueprints that actually need it
    # (have traps with absolute coords but no percentage coords)
    env.cr.execute("""
        SELECT DISTINCT bp.id FROM pest_blueprint bp
        JOIN pest_trap t ON t.blueprint_id = bp.id
        WHERE bp.image IS NOT NULL
          AND t.coord_x != 0
          AND (t.coord_x_pct = 0 OR t.coord_x_pct IS NULL)
        LIMIT 1
    """)
    needs_migration = env.cr.fetchone()

    if not needs_migration:
        _logger.info("pest_control: No coordinate migration needed.")
        return

    _logger.info("pest_control: Migrating coordinates for existing blueprints...")
    blueprints = env['pest.blueprint'].search([('image', '!=', False)])
    blueprints.action_migrate_coordinates()
    _logger.info("pest_control: Coordinate migration complete for %d blueprints.", len(blueprints))
