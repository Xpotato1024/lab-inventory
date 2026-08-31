# Identifiers

## Principle

Immutable identity and human-readable physical labels are separate concerns.

Do not make a mutable physical position the database identity of an entity.

## Internal identifiers

Persisted entities should use stable internal identifiers that do not change when the object moves, is renamed, or is reordered.

The exact database representation is an implementation decision, but UUID-style identifiers are preferred for externally durable entity references.

## Human-facing codes

Human-facing codes are short, readable, and suitable for printed labels.

Candidate prefixes:

- `R-` — fixture/rack where a rack-specific code is useful;
- `Z-` — placement zone;
- `C-` — reusable container;
- `U-` — generic physical unit when a more specific prefix is not appropriate;
- `A-` — individually tracked asset/equipment, if retained as a distinct public code category;
- `I-` — catalog item.

Examples:

```text
R-003
Z-0127
C-0042
A-0017
I-0001
```

Codes must not contain information that becomes false when the entity moves. For example, a container code must not encode its current rack or shelf.

## Rack shelf display names

A shelf zone may display a contextual path such as:

```text
Room A > Rack 03 > second level from bottom
```

The displayed ordinal is mutable metadata derived from the current rack configuration. It is not the shelf zone's immutable identity.

## Physical labels

Tracked placement zones and movable physical units should support durable labels containing:

1. a human-facing code;
2. a QR code;
3. optional short descriptive text that is explicitly non-authoritative.

Labels on reusable containers identify the physical container, not its current contents.

## QR links

QR codes should resolve to stable application routes for the labeled entity, for example:

```text
https://inventory.example/.../C-0042
```

The final URL scheme depends on deployment and routing decisions.

A QR link must not embed mutable inventory state.

## Renaming and retirement

Human-facing codes should normally remain stable after printing. If a code must be retired or replaced, historical audit records must continue to resolve the original entity identity.
