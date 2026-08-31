# AGENTS.md

## Purpose

`lab-inventory` is a laboratory inventory and spatial-location source-of-truth system. It must remain understandable and operable after the original author leaves the laboratory.

## Primary goals

1. Maintain an understandable source of truth for laboratory items, stock quantities, movable physical units, and normal storage locations.
2. Make normal operation possible entirely through documented GUI workflows or validated structured import/export.
3. Keep deployment, backup, restore, and maintenance simple enough for future laboratory members.
4. Prefer explicit domain semantics, auditability, and maintainability over feature richness.
5. Treat the 3D view as a locator aid derived from operational data, not as a CAD model or digital-twin source of truth.

## Non-goals

Do not turn the project into:

- a warehouse-management system with fixed bin capacities;
- a CAD editor;
- a real-time tracking system;
- a microservice platform;
- an application that requires source-code edits for ordinary inventory or layout changes.

## Domain constraints

- Do not make the 3D representation the source of truth.
- Do not introduce fixed shelf slot counts.
- Do not encode mutable physical positions into immutable database identifiers.
- Do not require exact physical dimensions before an object can be registered.
- A physical unit may be placed directly on a placement zone or supported by another physical unit.
- Recursive placement must reject cycles and self-support relationships.
- "On top of" and "contained in" are distinct relationships. Do not overload one to represent the other.
- Human-facing phrases such as "leftmost", "third from the left", or "second level" are normally derived from current placement/order data rather than stored as immutable identity.
- A location records a normal storage position. Temporary movement during active use should not require a location update unless an operational policy explicitly says otherwise.

## Operational constraints

- Routine users must not need shell access, Git, Python, JavaScript, SQL, or database administration.
- GUI operations are the default path for normal changes.
- Structured imports must validate before mutation and provide a preview before confirmation.
- Bulk human-edited tabular data should prefer CSV/XLSX; hierarchical layout/configuration may use YAML; machine-oriented interchange may use JSON.
- Import/export files are interfaces, not competing sources of truth.
- Mutating stock or placement must create an audit record in the same logical transaction.

## Architecture discipline

- Keep the application as a single operational system unless a concrete requirement justifies decomposition.
- Avoid introducing infrastructure components without a demonstrated operational need.
- Prefer boring, well-supported technology over novelty.
- Deployment/runtime technology remains undecided until ADR-0008 is accepted or superseded.

## Documentation discipline

Any change that alters domain semantics, persistence semantics, source-of-truth boundaries, identifiers, placement rules, deployment architecture, authentication boundaries, backup/restore behavior, or normal operator workflows must update the relevant documentation.

A material architectural decision must add a new ADR or supersede an existing ADR. Do not silently rewrite the rationale of an accepted ADR.

## Expected document roles

- `docs/architecture/`: how the system is conceptually structured.
- `docs/specifications/`: normative behavior and data semantics.
- `docs/operations/`: procedures for users and maintainers.
- `docs/adr/`: why architectural decisions were made.

## Change quality

Before considering a change complete:

1. Verify domain invariants and validation behavior.
2. Add or update tests for behavior changes.
3. Update affected documentation.
4. Confirm that routine workflows remain possible without source-code changes.
5. Check that any new dependency or service is justified against simpler alternatives.
