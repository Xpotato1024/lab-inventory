# Procedural 3D locator

## Purpose

The 3D view is a locator aid derived from the operational datastore. It helps a user understand approximately where a rack, shelf, desk, wall-storage region, container, tool, or piece of equipment is located.

It is not CAD, a digital twin, or a competing source of truth.

## Coordinate convention

Stored spatial coordinates use millimetres:

- `x`: room width / right;
- `y`: room depth / back;
- `z`: height / up.

`Fixture.x_mm`, `y_mm`, and `z_mm` identify the fixture origin within its room. Placement-zone coordinates are offsets from that fixture origin. Fixture `rotation_z_deg` rotates the fixture and its zones/placed units together around the vertical axis.

The browser renderer maps the domain coordinate system to Three.js as:

- domain `x` -> Three.js `x`;
- domain `z` -> Three.js `y` (up);
- domain `y` -> Three.js `z` (depth).

## Geometry fidelity

Exact dimensions are optional in the operational model. Missing dimensions must never block inventory registration or normal placement operations.

The viewer therefore uses deterministic placeholder geometry when required. The UI must visibly warn when room/fixture positions or physical-unit dimensions are being inferred.

Placeholder geometry is display-only and must never be written back into the operational datastore automatically.

## Fixture rendering

Initial fixture kinds are rendered with simple primitives:

- rack/cabinet/other: approximate bounds plus placement zones;
- desk/workbench: tabletop and simple supports;
- wall: thin vertical volume;
- placement zones: translucent volumes/surfaces/regions.

The viewer does not require a Blender or GLB model.

## Rack shelves

A rack shelf is a `PlacementZone`, not a fixed number of box slots.

If explicit zone height/position data is absent, `level_order` is used to derive a deterministic display height. This derivation affects only the 3D view.

The number of boxes that fit on a shelf is not stored as capacity. Direct children are ordered by current placement order and laid out using their known or placeholder footprints.

## Stacking

A physical unit placed on another physical unit is positioned on the supporting unit's top surface. Supported children are laid out using the same relative ordering model, and recursive stacks are rendered recursively.

The existing placement invariant prohibiting support cycles remains authoritative. The viewer must not introduce a separate stacking model.

## Wall-mounted objects

`WALL` and `ANCHOR` placement zones are rendered as vertical placement regions/points. Physical units placed there use approximate front-facing boxes. Precise tool silhouettes are intentionally outside V1 scope.

## Focus and navigation

Stable query links support direct focus:

```text
/3d/?unit=C-0042
/3d/?zone=Z-0127
/3d/?fixture=R-003
/3d/?room=ROOM-A
```

Unit focus resolves the effective root placement zone through the same recursive placement relationship used by the normal UI.

## Failure boundary

Three.js is a derived-view dependency. If WebGL, the CDN, or the viewer JavaScript is unavailable:

- search remains available;
- item/unit/zone detail pages remain available;
- stock and placement changes remain available;
- import/export and audit history remain available.

Users must never be required to use the 3D view to mutate authoritative state.
