# Documentation map

This directory is the documentation entry point for `lab-inventory`.

## Architecture

`architecture/` explains the conceptual structure of the system and the boundaries between major domain concepts.

- `architecture/overview.md` — system boundaries and source-of-truth flow.
- `architecture/domain-model.md` — domain entities and relationships.
- `architecture/deployment.md` — selected workstation-hosted deployment boundary and maintainer responsibilities.

## Specifications

`specifications/` contains normative behavior and data semantics.

- `specifications/placement-model.md` — placement zones, ordering, stacking, and recursive placement rules.
- `specifications/identifiers.md` — internal identifiers, human-facing codes, and label/QR rules.
- `specifications/import-export.md` — validated structured import/export behavior.

## Operations

`operations/` contains procedures for routine users and maintainers. These documents will grow as implementation begins.

Routine operation must be GUI-first. Structured files are secondary interfaces for bulk operations, migration, and administration.

Routine deployment, backup, restore, and ordinary upgrades must not require direct SQL.

## Architecture Decision Records

`adr/` records why significant architectural choices were made. See `adr/README.md` for status conventions and the current decision index.

The operational application is hosted on the laboratory always-on workstation under ADR-0008. Database engine selection remains open under ADR-0009.

## Source-of-truth rule

Operational state belongs to the application's operational datastore. 3D geometry, generated views, CSV/XLSX/YAML/JSON imports, exports, and documentation do not become competing operational sources of truth.
