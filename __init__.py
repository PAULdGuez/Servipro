from . import models
from . import controllers

def _post_init_hook_migrate_coordinates(env):
    # Odoo 16+ post_init_hooks take env directly
    blueprints = env['pest.blueprint'].search([('image', '!=', False)])
    if blueprints:
        blueprints.action_migrate_coordinates()
