# ADR-0005: Generate the 3D view procedurally

- Status: Accepted
- Date: 2026-08-31

## Context

The 3D view only needs to communicate the approximate spatial arrangement of shelves, desks, wall storage, containers, and equipment. Requiring a maintained CAD/Blender model would add a second editing workflow and increase handover cost.

## Decision

Generate the 3D view from application data using simple primitives and procedural layout.

Fixture/zone dimensions and optional physical-unit dimensions inform rendering. Missing dimensions use sensible placeholder geometry.

The 3D scene is a derived locator view, never authoritative placement state.

## Consequences

### Positive

- layout changes can be made through application data or validated configuration;
- no Blender/GLB editing skill is required for normal maintenance;
- moved containers are reflected automatically from placement data;
- the 3D view remains intentionally simple.

### Negative

- visual fidelity is lower than a hand-authored model;
- procedural placement requires heuristics for unknown dimensions and stacks.

## Alternatives considered

- hand-authored Blender model exported to GLB;
- CAD/digital-twin model as the source of truth;
- no spatial visualization.
