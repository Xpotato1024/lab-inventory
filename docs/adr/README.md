# Architecture Decision Records

ADRs record significant architectural decisions and their rationale.

## Status values

- `Proposed` — under evaluation; implementation must not assume the decision is final.
- `Accepted` — current architectural decision.
- `Superseded` — replaced by a later ADR.
- `Deprecated` — retained for history but no longer recommended.
- `Rejected` — considered and intentionally not adopted.

Accepted ADRs should not be silently rewritten to change their decision. Add a new ADR that supersedes the old decision when architecture changes materially.

## Index

- [ADR-0001: Keep one operational application](0001-single-operational-application.md) — Accepted
- [ADR-0002: Use one operational datastore as the source of truth](0002-operational-datastore-as-source-of-truth.md) — Accepted
- [ADR-0003: Model storage using placement zones](0003-placement-zones.md) — Accepted
- [ADR-0004: Support recursive physical-unit placement](0004-recursive-placement.md) — Accepted
- [ADR-0005: Generate the 3D view procedurally](0005-procedural-3d-view.md) — Accepted
- [ADR-0006: Make normal operations GUI-first](0006-gui-first-operations.md) — Accepted
- [ADR-0007: Separate immutable identity from physical position](0007-stable-identifiers.md) — Accepted
- [ADR-0008: Use laboratory workstation hosting](0008-deployment-runtime.md) — Accepted
- [ADR-0009: Select the operational database engine](0009-database-engine.md) — Proposed
