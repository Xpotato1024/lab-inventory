# Documentation map

This directory is the documentation entry point for `lab-inventory`.

## Architecture

`architecture/` explains the conceptual structure of the system and the boundaries between major domain concepts.

- `architecture/domain-model.md` — domain entities and relationships.

## Specifications

`specifications/` contains normative behavior and data semantics.

- `specifications/placement-model.md` — placement zones, ordering, stacking, and recursive placement rules.
- `specifications/identifiers.md` — internal identifiers, human-facing codes, and label/QR rules.

## Operations

`operations/` contains procedures for routine users and maintainers. These documents will grow as implementation begins.

Routine operation must be GUI-first. Structured files are secondary interfaces for bulk operations, migration, and administration.

## Architecture Decision Records

`adr/` records why significant architectural choices were made. See `adr/README.md` for status conventions and the current decision index.

Deployment/runtime technology is deliberately not frozen yet. ADR-0008 compares the candidate deployment models, including GitHub Pages, self-hosting through a secure tunnel, and a managed serverless deployment.

## Source-of-truth rule

Operational state belongs to the application's operational datastore. 3D geometry, generated views, CSV/XLSX/YAML/JSON imports, exports, and documentation do not become competing operational sources of truth.
