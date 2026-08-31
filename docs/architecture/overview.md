# Architecture overview

## Design objective

The system is an operational source of truth for laboratory inventory and normal storage locations, with a derived procedural 3D view that helps people find physical objects.

The architecture is intentionally divided into conceptual layers so implementation details can evolve without redefining laboratory semantics.

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

Direct SQL must not be part of routine operation, deployment, backup, restore, or ordinary upgrades.

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

The authoritative operational application runs on an always-on laboratory workstation as defined by ADR-0008.

```text
Browser
  -> HTTPS / laboratory domain
  -> controlled ingress
  -> workstation-hosted application
  -> operational datastore
```

A secure outbound tunnel is preferred when it reduces network/TLS administration, with a conventional reverse proxy as a fallback.

The database engine is intentionally a separate decision; see ADR-0009.
