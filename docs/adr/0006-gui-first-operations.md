# ADR-0006: Make normal operations GUI-first

- Status: Accepted
- Date: 2026-08-31

## Context

Future laboratory users should not need to understand the backend implementation. Normal inventory and placement changes must remain possible after the original author leaves.

## Decision

Make the web GUI the primary interface for routine operations, including:

- searching items and locations;
- moving physical units;
- changing stock quantities;
- inventory counts/reconciliation;
- adding ordinary catalog/container records;
- viewing audit history.

Provide structured import/export as secondary interfaces:

- CSV/XLSX for human-edited bulk tabular data;
- YAML for hierarchical layout/configuration where appropriate;
- JSON for machine-oriented interchange and operation batches.

Imports must follow: upload -> validate -> preview -> explicit confirmation -> transactional commit.

## Consequences

### Positive

- routine operation does not require Git, shell, SQL, or source-code access;
- bulk workflows remain available without making files the source of truth;
- validation and audit behavior can be consistent across GUI and imports.

### Negative

- the application must implement administrative workflows that could otherwise be done directly in the database;
- import validation and previews require additional implementation effort.

## Alternatives considered

- YAML/JSON files as the primary operational interface;
- database-admin UI as the only management interface;
- source-code/config edits for layout changes.
