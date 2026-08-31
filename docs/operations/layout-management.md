# Layout management

This procedure is for members in the `Maintainer` group. Normal layout changes do not require Django Admin, shell access, Python, or SQL.

## Open the layout view

Use `Layout` in the application header.

The hierarchy is displayed as:

```text
Room
  Fixture (rack / desk / wall / cabinet / workbench)
    Placement Zone (shelf / surface / wall region / anchor)
```

The number of boxes on a shelf is not part of this hierarchy. Boxes are separate `PhysicalUnit` placements.

## Add a room

1. Select `部屋を追加`.
2. Assign a durable Room ID and name.
3. Enter approximate room dimensions in millimetres.
4. Save.

Dimensions may be refined later. Missing dimensions do not block the SoT, but the 3D view will use a placeholder and show a warning.

## Add a fixture

From the target room, select `設備を追加`.

Record:

- durable Fixture ID;
- kind;
- approximate width/depth/height;
- X/Y/Z position in the room;
- optional horizontal rotation.

If X/Y is missing, the 3D view uses a deterministic temporary display position. This temporary position is not written back to the database.

## Add rack shelves / Placement Zones

From the target fixture, select `Zone追加`.

For a rack, the form defaults to:

- `VOLUME` zone;
- next `level_order` value;
- a provisional shelf name.

`level_order` is counted from bottom to top. It describes shelf order; it does not define a fixed number of box slots.

Enter an actual Z height when known. If it is absent, the 3D view estimates a display height from `level_order`.

## Stable IDs

Once a Room/Fixture/Zone exists, its public code is disabled in the normal edit form. This prevents accidental divergence from printed physical labels.

If a durable ID truly must change, treat that as exceptional maintenance and review identifier/audit consequences rather than bypassing the UI casually.

## Retirement instead of deletion

Do not delete old rooms, fixtures, or placement zones during normal cleanup.

Clear `使用中` to retire them. Retaining the row preserves:

- QR/label identity history;
- audit references;
- old placement history;
- the ability to understand earlier exports/backups.

## Verify in 3D

Each room, fixture, and zone has a direct 3D link from the Layout page. After changing dimensions or positions, open the 3D view and verify that the approximate spatial relationship is understandable.

The 3D view is a derived check only; if it differs from the recorded textual placement, correct the relevant layout metadata rather than treating the rendered model as authoritative.
