# ADR-0004: Support recursive physical-unit placement

- Status: Accepted
- Date: 2026-08-31

## Context

Objects can be stacked. A simple `stack_level` field is insufficient for arrangements such as two small boxes on one large box, with another box stacked on only one of them.

## Decision

A physical unit is placed either directly on a placement zone or on another physical unit. This support relationship may be recursive and therefore forms a forest rooted at placement zones.

Ordering among siblings expresses relative left-to-right or analogous display order. Fixed shelf slots are not introduced.

Implementations must prevent self-support and cycles.

## Consequences

### Positive

- simple single-layer shelves and irregular stacks use the same model;
- moving a supporting unit can naturally move an entire stack/subtree;
- the model remains extensible without enumerating stack levels.

### Negative

- validation requires cycle detection;
- UI operations must make descendant movement explicit;
- 3D rendering requires recursive layout.

## Alternatives considered

- `stack_level` integer;
- fixed grid coordinates;
- special stack/container entities.

The recursive support relationship is more general while keeping the normal case simple.
