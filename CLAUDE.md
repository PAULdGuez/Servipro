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
- **`pest_blueprint`** — Floor plan linked to a sede. Stores trap positions as JSON (`state_data` field) for a canvas-based frontend.
- **`pest_trap`** — Physical trap with coordinates on a blueprint. Unique name per blueprint. Has state history and incident relations.
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
- Traps store canvas coordinates (`pos_x`, `pos_y`) as `Float` fields on `pest_trap`; blueprint canvas state is stored as `Text` (JSON) in `pest_blueprint.state_data`.
- Custom plague name logic: `pest_incident` has both a `plague_type_id` (FK) and a `custom_plague_name` field; a computed `plague_display_name` resolves which to show.
