# lab-inventory

Laboratory inventory, asset, storage-location, and spatial visualization system.

The project provides a maintainable source of truth for **what the laboratory owns, how much exists, and where it is normally stored**. A simple 3D view is derived from the same data to help users locate shelves, desks, wall storage, containers, tools, and equipment.

## Project priorities

1. Normal operation must not require source-code changes.
2. Future laboratory members must be able to operate and maintain the system from the documentation.
3. Physical location, movable physical units, catalog items, and stock quantities remain separate concepts.
4. The 3D representation is a derived view, never the source of truth.
5. The system must tolerate irregular container sizes, direct placement of equipment, wall-mounted tools, and stacked objects without fixed shelf-slot counts.

## Documentation

Start with [`docs/README.md`](docs/README.md).

Architecture decisions are recorded under [`docs/adr/`](docs/adr/). Deployment technology is intentionally still under evaluation; see ADR-0008.
