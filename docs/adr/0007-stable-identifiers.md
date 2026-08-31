# ADR-0007: Separate immutable identity from physical position

- Status: Accepted
- Date: 2026-08-31

## Context

Racks, shelf levels, containers, and equipment may move or be reordered during cleanups and layout changes. If mutable position is encoded into identity, labels and historical references become false or require relabeling.

## Decision

Use stable internal entity identifiers and separate human-facing codes from mutable placement metadata.

Printed labels identify the entity, not its current contents or current parent location.

Displayed paths and ordinals such as "Rack 03 / second level from bottom / third from left" are derived from current relationships and ordering.

## Consequences

### Positive

- physical labels remain usable after relocation;
- audit records can retain durable references;
- shelf reordering does not require identity migration.

### Negative

- users sometimes need both a stable code and a descriptive current path;
- routing and lookup logic must resolve codes to stable internal identities.

## Alternatives considered

- codes that embed room/rack/shelf position;
- shelf ordinal as database primary key;
- QR codes containing current placement state.
