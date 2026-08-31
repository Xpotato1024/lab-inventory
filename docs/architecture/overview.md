# Architecture overview

## Design objective

The system is an operational source of truth for laboratory inventory and normal storage locations, with a derived procedural 3D view that helps people find physical objects.

The architecture is intentionally divided into conceptual layers so deployment technology can change without redefining laboratory semantics.

## Conceptual layers

```text
Users
  |
  | browser / structured import
  v
Application UI and validation
  |
  | transactional commands
  v
Operational datastore  <---- authoritative current state
  |
  +----> search and tabular views
  +----> procedural 3D view
  +----> exports / labels / reports
```

## Operational boundary

Normal users interact with the application through the web UI. Administrative bulk changes may use validated CSV/XLSX/YAML/JSON import workflows.

Source code, shell access, and direct database changes are maintenance-only activities.

## Domain boundary

The system separates:

- fixed/semi-fixed spatial fixtures;
- placement zones provided by those fixtures;
- movable physical units;
- catalog item definitions;
- quantity-tracked stock;
- audit/history records.

See `domain-model.md` and `../specifications/placement-model.md`.

## 3D boundary

The 3D scene is generated from dimensions, fixture structure, placement zones, and current placement relationships.

It is not a separately edited authoritative model.

## Deployment boundary

The operational deployment model is not yet accepted. See ADR-0008. The domain and UI contracts should not depend on whether the application ultimately runs on a laboratory workstation or a managed full-stack platform.
