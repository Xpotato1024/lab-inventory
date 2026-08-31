# Operations documentation

This directory contains procedures for routine users and maintainers.

## Routine-user principle

Routine users should need only a browser and the physical labels/QR codes attached to laboratory storage and tracked units.

Routine operations will include:

- search for an item or physical unit;
- view its normal storage location and 3D locator;
- move a physical unit to another placement zone or onto another physical unit;
- add/remove stock;
- perform inventory-count reconciliation;
- review recent changes.

## Administrative operations

Documented administrator workflows include or will include:

- create/deactivate fixtures and placement zones;
- bulk import with validation/preview;
- user/access administration;
- [backup and restore](backup-restore.md);
- application upgrade and rollback;
- label/QR regeneration;
- troubleshooting.

Routine maintenance must not require manually written SQL or interactive database administration.

## Location-update policy

The recorded placement represents the normal storage location. Temporary movement during active use does not normally require an update. A change should be recorded when the normal storage position changes, for example after a cleanup, reorganization, or long-term relocation.

Detailed GUI procedures should be added alongside implementation so screenshots and command examples stay aligned with the actual application.
