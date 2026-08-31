# Users and roles

The application uses Django users and groups. Normal authorization is intentionally small so future maintainers can understand it without reconstructing a custom RBAC system.

## Standard roles

The `bootstrap_roles` management command creates and synchronizes these groups idempotently on normal container startup.

### Viewer

For members who only need to find equipment and inspect inventory/location information.

Viewer can:

- sign in;
- search items, physical units, and placement zones;
- inspect normal storage locations and inventory;
- view the derived 3D locator when implemented.

Viewer cannot change operational data.

### Editor

For ordinary members trusted to keep the SoT current.

Editor includes Viewer behavior and can:

- add a quantity-tracked item to a holder/container;
- increase/decrease stock through the audited GUI;
- record an inventory-count correction;
- change the normal placement of a physical unit;
- place a unit onto another physical unit.

Every operational mutation goes through application service logic and creates its audit record in the same transaction.

### Maintainer

For members responsible for laboratory layout/master data and system administration.

Maintainer can manage inventory master data such as:

- rooms;
- fixtures;
- placement zones;
- catalog items;
- physical units.

Operational `Stock` and `Placement` records remain read-only in Django Admin. A Maintainer should use the normal audited workflows for stock and placement changes rather than editing those rows directly.

## Superuser and Django Admin

A Django superuser is a technical administrator and bypasses normal permission checks. Keep the number of superusers small.

Django Admin also requires the user's `is_staff` flag. Membership in the Maintainer group does not automatically set `is_staff` because that account-level decision should remain explicit.

A typical setup is:

- ordinary laboratory member: Viewer or Editor, not staff;
- master-data maintainer: Maintainer + `is_staff`;
- system owner/emergency administrator: superuser.

## Create the first administrator

On the workstation:

```sh
docker compose exec web python manage.py createsuperuser
```

Then sign in to `/admin/` and create users or assign groups.

## Rebuild standard group permissions

Normally this runs automatically at startup. It can be invoked manually after troubleshooting:

```sh
docker compose exec web python manage.py bootstrap_roles
```

Do not manually invent parallel role names/permissions unless there is a documented requirement. If the authorization model materially changes, update this document and the relevant architecture decision/documentation.

## Account retirement

When a member leaves the laboratory, deactivate the account rather than deleting audit history. Historical `StockChange` and `PlacementChange` records should remain understandable even after the user can no longer sign in.
