# Placement model

## Purpose

The placement model must represent real laboratory storage without assuming uniform containers or fixed shelf slot counts.

It must support, without special-case storage systems:

- multiple narrow parts cases on one shelf;
- large containers occupying most of a shelf;
- cardboard cartons placed directly on a shelf;
- equipment such as a DC power supply placed directly on a shelf or desk;
- tools placed on a desk surface;
- tools mounted on a wall panel or hook;
- physical units stacked on top of other physical units.

## Placement targets

A `PhysicalUnit` has exactly one current normal-storage placement unless it is explicitly unplaced.

A placement targets exactly one of:

1. a `PlacementZone`; or
2. a supporting `PhysicalUnit`.

The two targets are mutually exclusive.

## Direct placement

A direct placement associates a physical unit with a placement zone.

Example:

```text
C-0042 -> Rack 03 / shelf zone Z-0127
```

The shelf does not define a fixed number of slots.

## Relative ordering

Physical units sharing the same support surface have a relative order used for human-readable positioning and procedural rendering.

Example persisted order:

```text
C-0042 order=10
C-0072 order=15
C-0051 order=20
PSU-03 order=30
```

A UI may derive:

```text
1. C-0042
2. C-0072
3. C-0051
4. PSU-03
```

Therefore phrases such as "third from the left" are derived values, not immutable identifiers.

The persistence representation of ordering may change during implementation, but it must support insertion/reordering without introducing fixed shelf slots.

## Recursive stacking

A physical unit may be supported by another physical unit.

Example:

```text
Shelf Z-0127
├─ C-0042
│  ├─ C-0072
│  │  └─ C-0090
│  └─ C-0073
└─ C-0051
```

Semantically:

```text
C-0042 -> zone Z-0127
C-0051 -> zone Z-0127
C-0072 -> on C-0042
C-0073 -> on C-0042
C-0090 -> on C-0072
```

Ordering is also allowed among objects sharing the same supporting physical unit.

## Invariants

Implementations must enforce:

- a physical unit cannot support itself;
- placement relationships must not contain cycles;
- a placement cannot simultaneously target a zone and a supporting unit;
- a physical unit cannot have multiple current placements;
- deleting/deactivating a support target must not silently orphan descendants;
- placement changes must be auditable.

## Stacked movement

When moving a physical unit that supports descendants, the UI must make the consequence explicit.

The system should support at least:

- moving the whole stack/subtree while preserving support relationships;
- moving only the selected physical unit, after explicitly resolving/re-homing any supported descendants.

The implementation must never silently discard descendant placement information.

## Dimensions

Placement zones and physical units may have width, depth, and height.

Dimensions are optional for physical units. Unknown dimensions must not block registration or placement.

When sufficient dimensions are available, the application may warn about apparent geometric conflicts or overflow. Such warnings are advisory because real-world arrangements may include overhang, inaccurate measurements, cable clearance, rotation, or other exceptions.

## Optional precision

Normal operation should require only:

- target placement zone/supporting unit;
- relative order.

Optional fields may support more precise visualization, for example:

- local X/Y offset;
- rotation;
- measured dimensions.

These fields must not be required for ordinary location tracking.

## Shelf levels

A rack shelf/level is a placement zone with a mutable display order such as "second level from the bottom".

The internal identity of the shelf zone must remain stable if shelf heights or displayed level numbers change.

## Meaning of location

Placement records the normal storage location, not every temporary movement during active use.

Routine procedures should update placement when the normal storage location changes, such as after a laboratory cleanup or long-term relocation.
