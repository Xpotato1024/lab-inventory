# lab-inventory

Laboratory inventory, asset, storage-location, and spatial visualization system.

The project provides a maintainable source of truth for **what the laboratory owns, how much exists, and where it is normally stored**. A simple procedural 3D view is derived from the same data to help users locate shelves, desks, wall storage, containers, tools, and equipment.

## Project priorities

1. Normal operation must not require source-code changes.
2. Future laboratory members must be able to operate and maintain the system from the documentation.
3. Physical location, movable physical units, catalog items, and stock quantities remain separate concepts.
4. The 3D representation is a derived view, never the source of truth.
5. The system must tolerate irregular container sizes, direct placement of equipment, wall-mounted tools, and stacked objects without fixed shelf-slot counts.
6. Routine operation, deployment, backup, restore, and ordinary upgrades must not require direct SQL.

## V1 capabilities

- search by item, part number, physical-unit ID, or placement-zone ID;
- audited stock increase/decrease and inventory-count reconciliation;
- aggregate low-stock warnings based on optional per-item thresholds;
- placement on rack shelves, desk surfaces, wall zones, anchors, or recursively on another physical unit;
- relative left/right ordering without fixed shelf slots;
- procedural 3D locator with direct unit/zone focus;
- durable ID + QR label generation and browser-printable label sheets;
- validated CSV/JSON bulk operations with preview and stale-preview protection;
- read-only JSON state snapshot export;
- browser-based Layout and Master-data maintenance for the Maintainer role;
- user-visible stock and placement audit history;
- database-aware online SQLite backup, guarded restore, and verified off-workstation backup mirroring.

## Accepted V1 stack

- Python 3.13
- Django 5.2 LTS
- SQLite operational datastore
- Gunicorn
- WhiteNoise
- Docker Compose
- server-rendered HTML + minimal vanilla JavaScript
- Three.js 0.185.1 as pinned browser ES modules for the derived 3D locator

The authoritative deployment runs on the laboratory always-on workstation. GitHub Pages may be used for documentation or static demonstrations, but not for the writable operational source of truth.

## Local development / smoke start

```sh
cp .env.example .env
# Edit .env and set a non-placeholder DJANGO_SECRET_KEY.
docker compose up -d --build --wait
```

Check status:

```sh
docker compose ps
docker compose logs -f web
```

Open `http://127.0.0.1:8000/` locally.

## Production workstation start

Use the production template and keep SQLite data/backups outside the Git checkout:

```sh
cp .env.production.example .env
# Edit the production hostname, secret, and persistent host paths.
sh scripts/preflight.sh
docker compose up -d --build --wait
```

The application remains bound to workstation localhost. Connect the long-lived HTTPS laboratory hostname through the controlled ingress described in [`docs/operations/workstation-deployment.md`](docs/operations/workstation-deployment.md).

Create the first technical administrator account:

```sh
docker compose exec web python manage.py createsuperuser
```

## Routine maintenance commands

Create a database-aware online local backup:

```sh
sh scripts/backup.sh
```

Create a verified local backup and mirror it to configured separate storage:

```sh
sh scripts/backup-mirror.sh
```

Restore a selected local backup (the wrapper stops the web service first):

```sh
sh scripts/restore.sh lab-inventory-YYYYMMDDTHHMMSSZ.sqlite3
```

## Documentation

Start with [`docs/README.md`](docs/README.md), then use [`docs/operations/`](docs/operations/) for operator and maintainer procedures.

Architecture decisions are recorded under [`docs/adr/`](docs/adr/). In particular:

- ADR-0008 — workstation hosting;
- ADR-0009 — SQLite for V1;
- ADR-0010 — Django application stack;
- ADR-0011 — Three.js without a JavaScript build pipeline.
