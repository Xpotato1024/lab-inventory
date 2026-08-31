# Operations documentation

This directory contains procedures for routine users and maintainers.

## Start here

- [Daily operations](daily-operations.md) — search, low-stock status, stock changes, inventory counts, placement changes, and stacking.
- [Master-data management](master-data.md) — Maintainer workflow for CatalogItems and PhysicalUnits.
- [Layout management](layout-management.md) — Maintainer workflow for rooms, fixtures, rack shelves, desks, and wall zones.
- [Users and roles](users-and-roles.md) — Viewer, Editor, Maintainer, staff, and superuser responsibilities.
- [Workstation deployment](workstation-deployment.md) — production `.env`, persistent storage, preflight, Compose startup, and ingress boundary.
- [Backup and restore](backup-restore.md) — database-aware online backup and guarded offline restore.

## Routine-user principle

Routine users should need only a browser and the physical labels/QR codes attached to laboratory storage and tracked units.

Routine operations include:

- search for an item or physical unit;
- inspect aggregate low-stock warnings;
- view normal storage location and derived 3D locator;
- move a physical unit to another placement zone or onto another physical unit;
- add/remove stock;
- perform inventory-count reconciliation;
- print/read stable ID and QR labels;
- review recent changes.

## Administrative operations

Documented administrator/maintainer workflows include or will include:

- create/deactivate CatalogItems and PhysicalUnits through the Master UI;
- create/deactivate rooms, fixtures, and placement zones through the Layout UI;
- bulk import with validation/preview;
- user/access administration;
- workstation deployment and controlled upgrades;
- backup and restore;
- label/QR regeneration;
- troubleshooting.

Routine maintenance must not require manually written SQL or interactive database administration.

## Location-update policy

The recorded placement represents the normal storage location. Temporary movement during active use does not normally require an update. A change should be recorded when the normal storage position changes, for example after a cleanup, reorganization, or long-term relocation.

Detailed GUI procedures should evolve alongside implementation so terminology and examples stay aligned with the actual application.
