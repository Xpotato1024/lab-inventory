# ADR-0003: Model storage using placement zones

- Status: Accepted
- Date: 2026-08-31

## Context

Laboratory storage is heterogeneous. Objects may be placed on rack shelves, desks, wall panels, hooks, cabinets, or similar structures. Modeling each storage furniture type with its own placement mechanism would create special cases and make the system harder to maintain.

## Decision

Represent meaningful places where physical units can be stored as `PlacementZone` entities associated with fixtures.

Initial zone semantics are:

- `VOLUME`;
- `SURFACE`;
- `WALL`;
- `ANCHOR`.

A rack shelf is one placement zone. A placement zone does not declare a fixed number of container slots.

## Consequences

### Positive

- shelves, desks, wall storage, and hooks share one placement mechanism;
- storage capacity is not incorrectly reduced to a fixed slot count;
- new fixture types can normally reuse existing placement semantics.

### Negative

- visualization and validation must interpret zone geometry and type;
- some highly specialized storage may eventually require additional zone semantics.

## Alternatives considered

- separate tables and workflows for shelves, desks, hooks, and wall storage;
- fixed bins/slots per shelf;
- arbitrary 3D coordinates as the primary location model.

These alternatives were rejected because they either create special cases or make ordinary location data unnecessarily precise.
