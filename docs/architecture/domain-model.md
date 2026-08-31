# Domain model

## Scope

The system answers three operational questions:

1. What physical things and catalog items exist?
2. Where is each tracked physical thing normally stored?
3. How much stock of each quantity-tracked item is available?

## Core concepts

### Room

A physical laboratory room or other top-level spatial area.

### Fixture

A relatively fixed physical structure that provides places where objects can be stored or used.

Examples:

- rack;
- desk;
- wall or wall-storage panel;
- cabinet;
- workbench.

A fixture is not itself a stock container.

### PlacementZone

A meaningful area or point associated with a fixture where a physical unit may be placed.

Initial zone semantics:

- `VOLUME` — shelf/cabinet volume or similar storage space;
- `SURFACE` — desk/workbench/top surface;
- `WALL` — a wall or panel region where objects may be mounted;
- `ANCHOR` — a specific hook, bracket, or attachment point.

A rack shelf is represented as a placement zone. The number of physical units that fit on a shelf is not fixed in the model.

### PhysicalUnit

A physical object that is individually tracked and can be placed somewhere.

Examples:

- reusable container or parts case;
- cardboard carton;
- DC power supply;
- soldering iron;
- individually tracked motor;
- tool.

Physical units may optionally have dimensions. Missing dimensions do not prevent registration.

### Placement

The current normal-storage relationship for a physical unit.

A physical unit is placed either:

1. directly on/in a `PlacementZone`; or
2. on top of another `PhysicalUnit`.

This supports irregular shelf occupancy and recursive stacking without fixed shelf slots.

### CatalogItem

A type of item independent of any particular physical instance or container.

Examples:

- M3x10 socket-head screw;
- M3 nut;
- black PLA filament;
- a model of DC motor;
- a model of soldering iron.

### Stock

The quantity of a quantity-tracked `CatalogItem` associated with a container/physical unit or other supported stock holder.

Current quantity is operational state. Quantity changes must also create an audit record.

### Asset

A concept for individually tracked equipment or tools when individual identity matters. Implementation may model this as a specialized role of `PhysicalUnit` rather than a separate placement system.

## Relationship overview

```text
Room
 └─ Fixture
     └─ PlacementZone
          ▲
          │ direct placement
      Placement
          │
          ▼
     PhysicalUnit
          ▲
          │ supported-by placement
      Placement

PhysicalUnit ── holds ── Stock ── references ── CatalogItem
```

## Source-of-truth boundary

The operational datastore is authoritative for current inventory and placement state.

Derived representations include:

- 3D visualization;
- phrases such as "third from the left";
- total stock summaries;
- exported CSV/XLSX/YAML/JSON;
- generated labels and QR links.

These derived representations must not become independent authoritative state.
