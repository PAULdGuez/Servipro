"""Las ubicaciones pasan a colgar de una sede, y hasta ahora eran globales.

POR QUÉ ESTE SCRIPT EXISTE
--------------------------
`pest.zone.sede_id` nace `required`. Odoo crea la columna vacía y **no puede poner el NOT NULL**
sobre una tabla que ya tiene filas: lo registra como aviso y sigue, dejando la restricción sin
aplicar y la base a medio migrar. Poblar la columna **antes** de que el ORM la cree es lo que
hace que la restricción llegue de verdad.

QUÉ HACE, Y POR QUÉ DESDOBLA
----------------------------
Una ubicación global puede estar usada por trampas de **varias sedes** a la vez — es justo el
motivo del cambio. No se puede elegir una sede «ganadora» sin dejar trampas apuntando a la
ubicación de otra planta, así que **se desdobla**: una copia por cada sede que la usaba, y cada
trampa se reapunta a la de la suya. El nombre se conserva, que es lo que la gente reconoce.

Las ubicaciones que no usa ninguna trampa se borran: no hay forma de adivinarles una sede, y
conservarlas sin ella bloquearía el NOT NULL.

Es idempotente: si la columna ya existe y está poblada, no hace nada.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # La unicidad vieja era `UNIQUE(name)` a secas y **hay que soltarla antes de desdoblar**:
    # las copias por sede comparten nombre a propósito, y Odoo no retira la restricción obsoleta
    # hasta después de este script. Sin esto, la migración muere en la primera copia.
    cr.execute("ALTER TABLE pest_zone DROP CONSTRAINT IF EXISTS pest_zone_name_unique")
    cr.execute("ALTER TABLE pest_zone ADD COLUMN IF NOT EXISTS sede_id integer")

    # (zona, sede) que de verdad se usan, con la sede tomada de las trampas
    cr.execute("""
        SELECT z.id, t.sede_id, z.name
          FROM pest_zone z
          JOIN pest_trap t ON t.zone_id = z.id
         WHERE t.sede_id IS NOT NULL
      GROUP BY z.id, t.sede_id, z.name
      ORDER BY z.id, t.sede_id
    """)
    usos = cr.fetchall()

    vistas = set()
    desdobladas = 0
    for zona_id, sede_id, nombre in usos:
        if zona_id not in vistas:
            # la primera sede se queda con la ubicación original
            vistas.add(zona_id)
            cr.execute("UPDATE pest_zone SET sede_id = %s WHERE id = %s", (sede_id, zona_id))
            continue
        # las demás sedes reciben su propia copia
        cr.execute("""
            INSERT INTO pest_zone (name, code, sede_id, active, create_uid, create_date,
                                   write_uid, write_date)
                 SELECT name, code, %s, active, create_uid, now(), write_uid, now()
                   FROM pest_zone WHERE id = %s
              RETURNING id
        """, (sede_id, zona_id))
        copia_id = cr.fetchone()[0]
        cr.execute("UPDATE pest_trap SET zone_id = %s WHERE zone_id = %s AND sede_id = %s",
                   (copia_id, zona_id, sede_id))
        desdobladas += 1
        _logger.info('ubicacion "%s": copia para la sede %s', nombre, sede_id)

    cr.execute("DELETE FROM pest_zone WHERE sede_id IS NULL")
    huerfanas = cr.rowcount

    _logger.info('ubicaciones: %d con sede asignada, %d desdobladas por usarse en varias sedes, '
                 '%d borradas por no usarlas ninguna trampa',
                 len(vistas), desdobladas, huerfanas)
