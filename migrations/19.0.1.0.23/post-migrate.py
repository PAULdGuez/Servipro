"""Marca como personal de ServiPro a quien ya lo era, antes de que el corte los deje ciegos.

EL PROBLEMA QUE RESUELVE
------------------------
El corte por sede es **fail-closed**: quien no tenga sedes asignadas no ve nada. Y el personal de
ServiPro no tiene sedes asignadas —no le hacen falta, ve todas—, así que en el momento en que las
reglas entran en vigor **se quedaría sin ver absolutamente nada** hasta que alguien, a mano, les
pusiera el grupo nuevo.

O sea: una función pensada para proteger dejaría fuera primero a quien la instala.

CÓMO SE RECONOCE A QUIEN YA ERA PERSONAL
----------------------------------------
Por **pertenecer a más de una empresa**. Es la señal que existe hoy en la base: quien trabaja para
ServiPro tiene las nueve empresas cliente; la gente de un cliente tiene la suya y nada más.

⚠️ **Es una heurística, no una verdad**, y por eso solo se usa AQUÍ, una vez, para no dejar a nadie
tirado. A partir de este momento la marca es explícita y no se deduce de nada: quien entre nuevo la
lleva o no la lleva.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    grupo = env.ref('pest_control.group_pest_staff', raise_if_not_found=False)
    if not grupo:
        _logger.warning('no existe el grupo de personal: nadie fue marcado')
        return

    candidatos = env['res.users'].search([
        ('share', '=', False),
        # `all_group_ids`, no `group_ids`: quien tiene el rol Supervisor o Técnico **implica**
        # Cliente sin tenerlo explícito, y con `group_ids` el filtro los dejaba fuera — que es
        # justo dejar sin marcar a todo el personal de ServiPro.
        ('all_group_ids', 'in', env.ref('pest_control.group_pest_client').ids),
    ])
    personal = candidatos.filtered(lambda u: len(u.company_ids) > 1)
    if personal:
        personal.write({'group_ids': [(4, grupo.id)]})
    # 🔑 A los usuarios de cliente que YA EXISTÍAN se les asignan todas las sedes de su
    # empresa: es exactamente lo que veían ayer.
    #
    # **Una migración no puede cambiarle a nadie lo que ve.** El corte es una capacidad nueva;
    # activarla no debe estrenarse quitándole el acceso a gente que lleva meses trabajando, que
    # además es como se pierde la confianza en una función de permisos: el primer día que la
    # instalas, medio equipo se queda fuera sin saber por qué.
    #
    # A partir de aquí se recorta a mano, usuario por usuario, que es la decisión de negocio.
    de_cliente = candidatos - personal
    ajustados = 0
    for usuario in de_cliente:
        if usuario.pest_sede_ids:
            continue
        # `active_test=False`: `search([])` filtra las archivadas por defecto, y Grupo Bimbo
        # tiene 3 sedes archivadas con 139 trampas dentro. Sin esto, activar el corte le
        # quitaba a cada usuario de Bimbo 139 trampas que ayer veía — justo lo que esta
        # migración existe para evitar.
        suyas = env['pest.sede'].sudo().with_context(active_test=False).search(
            [('company_id', 'in', usuario.company_ids.ids)])
        if suyas:
            usuario.pest_sede_ids = [(6, 0, suyas.ids)]
            ajustados += 1

    _logger.info(
        'corte por sede: %d marcados como personal de ServiPro (%s); '
        '%d usuarios de cliente conservan las sedes que ya veían. '
        'A partir de ahora se recortan a mano desde la ficha del usuario.',
        len(personal), ', '.join(personal.mapped('login')) or 'ninguno', ajustados,
    )
