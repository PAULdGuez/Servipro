# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module Overview

**ServiPro - Control de Plagas** is an Odoo 19 module for integrated pest control management. It depends on `base`, `mail`, and `sale`.

Module technical name: `pest_control`
Version: `19.0.1.0.0`

## Installation & Development Commands

```bash
# Install the module
python odoo-bin -i pest_control -d <database>

# Update the module after changes
python odoo-bin -u pest_control -d <database>

# Run Odoo with dev mode (auto-reload assets)
python odoo-bin -u pest_control -d <database> --dev=all
```

There are no standalone test, lint, or build commands — testing is done through Odoo's test runner:

```bash
python odoo-bin -i pest_control -d <database> --test-enable --stop-after-init
```

## Architecture

### Domain Models (in `models/`)

The module follows a clear site-centric hierarchy:

- **`pest_sede`** — Customer site/branch. The central entity. Has `one2many` relations to blueprints, traps, incidents, and complaints. Contains computed counters displayed as stat buttons.
- **`pest_blueprint`** — Floor plan linked to a sede. Uses `image_web` and the OWL `blueprint_canvas` widget for interactive trap positioning.
- **`pest_trap`** — Physical trap with percentage coordinates (`coord_x_pct`, `coord_y_pct`) on a blueprint. Unique name per blueprint. Has state history and incident relations.
- **`pest_incident`** — A capture or finding event. Links to a trap, a plague type (standard or custom), and an inspector.
- **`pest_evidence`** — Photographic evidence with a 2-step workflow (`pendiente` → `resuelta`) and supervisor approval. Stores before/after images.
- **`pest_inspection`** — Technical inspection visit. Auto-sequenced (`INS-XXXX`). Has a 3-state workflow: `borrador` → `en_progreso` → `completada`.
- **`pest_complaint`** — Customer complaint. Auto-sequenced (`QJ-XXXX`). Classified by priority (`critico/alto/medio/bajo`).

**History/audit models:** `pest_trap_state`, `pest_trap_movement` — record state changes and physical relocations of traps.

**Catalog models:** `pest_plague_type`, `pest_trap_type` — reference data, pre-populated via `data/` XML files.

**Extension:** `pest_sale` — adds a `sede_id` field to `sale.order`.

### Security Groups (in `security/pest_security.xml`)

Three-tier hierarchy (each implies the one below):
1. **Supervisor** — full access, approvals
2. **Tecnico** — register incidents, evidence, inspections
3. **Cliente** — read-only access

Row-level permissions are defined in `security/ir.model.access.csv`.

### Auto-sequencing

- Complaints: `QJ-` prefix (defined in `data/pest_sequence_data.xml`)
- Inspections: `INS-` prefix (defined in `data/pest_sequence_data.xml`)

Sequences are applied in `_default_name` or `create()` overrides in the respective models.

## Key Conventions

- All UI labels are in **Spanish** — keep new fields and views consistent.
- State fields use `selection` type with string keys (e.g., `'pendiente'`, `'resuelta'`).
- Traps store responsive percentage coordinates (`coord_x_pct`, `coord_y_pct`) on `pest_trap` from 0.0 to 100.0. The `pest_blueprint` widget uses OWL to intercept Save events transactionally.
- Custom plague name logic: `pest_incident` has both a `plague_type_id` (FK) and a `custom_plague_name` field; a computed `plague_display_name` resolves which to show.


---

# Reglas de este repositorio

> Añadido el 2026-09-03 al integrar el proyecto al stack. Lo de arriba describe la arquitectura del
> módulo; esto es cómo se trabaja aquí.

## Antes de tocar nada

**El plan maestro está en el vault**, y hay que leerlo antes de construir:
`~/Documents/OBSIDIAN/01 - Proyectos/pest_control/PLAN-MAESTRO.md`

Trae el estado verificado, las decisiones tomadas con su porqué, lo que falta decidir y el orden de
trabajo. **No re-litigar una decisión que ya está ahí sin leer primero por qué se tomó.**

## Las tres ubicaciones

| | |
|---|---|
| **Este repo** | Solo código. **Ojo: el repo ES el addon** — la raíz tiene el `__manifest__.py` |
| **Workspace** | `~/Documents/Workspaces/servipro` — runbook, guiones, datos, entregables |
| **Vault** | `OBSIDIAN/01 - Proyectos/pest_control` — plan maestro, decisiones, hallazgos |

**Nada que no sea código va en este repo.** Los volcados de base y los respaldos del sistema PHP
están bloqueados en `.gitignore` a propósito: llevan datos reales de clientes.

## Entorno

Odoo 19 Enterprise local, contenedor `odoo19-enterprise-dev`, **puerto 8079**, base `servipro`.
El repo se monta como `/mnt/servipro-addons/pest_control`. Comandos exactos en el runbook del
workspace — y **el contenedor ya ocupa el 8069**, así que todo comando extra necesita
`--http-port=8123 --gevent-port=8124` o falla.

🔑 **Antes de medir cualquier cosa contra una base, córrele `-u pest_control`.** Si la base quedó en
una versión anterior, mides código viejo y concluyes sobre el nuevo. Ya pasó dos veces aquí.

## Commits

Convencionales, atómicos, y **el `__manifest__.py` se bumpea en el mismo commit** — sin bump,
odoo.sh no carga los cambios. En `fix` y `feat`, el cuerpo explica **el porqué**, no el qué.

## Cómo se verifica aquí

Cuatro reglas que costaron caro y no se negocian:

1. **Ejercer permisos con el usuario del rol**, nunca con el administrador — no ejerce permisos, y
   ya escondió tres fallos reales de acceso.
2. **`env.invalidate_all()` antes de leer** en cualquier prueba de permisos, o el valor sale del
   caché de quien lo cargó y **la prueba dice lo contrario de la verdad**.
3. **Probar toda guarda por los dos lados**: que impida lo que debe **y permita lo legítimo**.
4. **Mirar la captura**, no solo los asertos. El tablero en blanco no da error, solo se ve.

## Si construyes algo distinto a lo planeado

Se anota en `Workspaces/servipro/planes/BITACORA-DESVIACIONES.md` **antes de commitear**: qué decía
el plan, qué se hizo y por qué. Una desviación anotada es una decisión; sin anotar es un misterio.

## Tracking

El repo trae una carpeta `.beads/` con cuatro pendientes del desarrollo anterior. **Ese sistema no
se usa en este setup** — está ahí como registro histórico. Antes de retomar esos pendientes,
confirmar con Paul cuál es el sistema de tracking vigente.
