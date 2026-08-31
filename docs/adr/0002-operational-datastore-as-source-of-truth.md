# ADR-0002: Use one operational datastore as the source of truth

- Status: Accepted
- Date: 2026-08-31

## Context

The application will expose inventory and placement data through a GUI, 3D visualization, exports, and structured imports. Without a clear source-of-truth boundary, these representations can diverge.

## Decision

Use one operational datastore as the authoritative source for current inventory, physical-unit placement, and audit state.

The following are derived or interchange representations and are not authoritative operational state:

- 3D scenes;
- CSV/XLSX/YAML/JSON files;
- generated reports;
- QR labels;
- cached search/index data.

Structured imports must be validated and committed into the operational datastore before they become current state.

## Consequences

### Positive

- clear conflict-resolution semantics;
- simpler backup and restore expectations;
- 3D and tabular views cannot independently drift by design;
- one place to enforce transactions and audit rules.

### Negative

- offline file edits are not current until imported;
- disaster recovery must protect the operational datastore carefully.

## Alternatives considered

- YAML files in Git as the primary database;
- 3D model metadata as authoritative location state;
- spreadsheet-first operation with periodic synchronization.

These alternatives were rejected because they create competing state and weak transactional behavior.
