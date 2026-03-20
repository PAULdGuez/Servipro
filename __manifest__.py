{
    'name': 'ServiPro - Control de Plagas',
    'version': '19.0.1.0.0',
    'category': 'Services',
    'summary': 'Sistema de gestion integral de control de plagas',
    'description': """
        ServiPro - Sistema de Control de Plagas
        ========================================
        Modulo para gestionar:
        * Sedes y plantas de clientes
        * Planos con posicionamiento de trampas
        * Registro de incidencias (capturas y hallazgos)
        * Evidencias fotograficas con flujo de resolucion
        * Inspecciones tecnicas
        * Quejas de clientes
        * Reportes y estadisticas
    """,
    'author': 'ServiPro / IT Green',
    'website': 'https://servipro.site',
    'depends': ['base', 'mail', 'sale'],
    'data': [
        # 1) Data files: sequences, security, initial data
        'data/pest_sequence_data.xml',
        'security/pest_security.xml',
        'security/ir.model.access.csv',
        'data/pest_trap_type_data.xml',
        'data/pest_plague_type_data.xml',
        # 2) Simple catalog views (no cross-references)
        'views/pest_trap_type_views.xml',
        'views/pest_plague_type_views.xml',
        # 3) Views that define actions but don't reference others
        'views/pest_sede_views.xml',
        'views/pest_incident_views.xml',
        'views/pest_evidence_views.xml',
        'views/pest_inspection_views.xml',
        'views/pest_complaint_views.xml',
        'views/pest_trap_state_views.xml',
        'views/pest_trap_movement_views.xml',
        # wizard action must be loaded before blueprint_views (which references it)
        'views/pest_trap_state_wizard_views.xml',
        'views/pest_blueprint_zone_views.xml',
        'views/pest_blueprint_views.xml',
        # 4) Views that reference other actions
        #    pest_trap_views.xml uses %(pest_control.pest_incident_action)d
        #    so pest_incident_views.xml MUST load before this file
        'views/pest_trap_views.xml',
        # 5) Menus last (references all actions)
        'views/pest_menus.xml',
        # 6) Documentation UI Routes
        'views/pest_doc_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pest_control/static/lib/simpleheat.min.js',
            'pest_control/static/src/components/blueprint_canvas/blueprint_canvas.js',
            'pest_control/static/src/components/blueprint_canvas/blueprint_canvas.xml',
            'pest_control/static/src/components/blueprint_canvas/blueprint_canvas.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'external_dependencies': {'python': ['Pillow', 'openpyxl', 'markdown']},
    'post_init_hook': '_post_init_hook_migrate_coordinates',
}
