# lab-inventory

Laboratory inventory, asset, storage-location, and spatial visualization system.

The project provides a maintainable source of truth for **what the laboratory owns, how much exists, and where it is normally stored**. A simple 3D view is derived from the same data to help users locate shelves, desks, wall storage, containers, tools, and equipment.

## Project priorities

1. Normal operation must not require source-code changes.
2. Future laboratory members must be able to operate and maintain the system from the documentation.
3. Physical location, movable physical units, catalog items, and stock quantities remain separate concepts.
4. The 3D representation is a derived view, never the source of truth.
5. The system must tolerate irregular container sizes, direct placement of equipment, wall-mounted tools, and stacked objects without fixed shelf-slot counts.

## Accepted V1 stack

- Python 3.13
- Django 5.2 LTS
- SQLite operational datastore
- Gunicorn
- WhiteNoise
- Docker Compose
- server-rendered HTML + minimal vanilla JavaScript
- Three.js for the derived procedural 3D locator

The authoritative deployment runs on the laboratory always-on workstation. GitHub Pages may be used for documentation or static demonstrations, but not for the writable operational source of truth.

## First local/workstation start

```sh
cp .env.example .env
# Edit .env: set a strong DJANGO_SECRET_KEY and the real host/domain values.
docker compose up -d --build
```

Check status:

```sh
docker compose ps
docker compose logs -f web
```

Create the first administrator account:

```sh
docker compose exec web python manage.py createsuperuser
```

Open `http://127.0.0.1:8000/` locally. Production ingress/custom-domain configuration is documented separately and must remain replaceable.

## Routine maintenance commands

Create a database-aware online backup:

```sh
sh scripts/backup.sh
```

Restore a selected backup (the wrapper stops the web service first):

```sh
sh scripts/restore.sh lab-inventory-YYYYMMDDTHHMMSSZ.sqlite3
```

Routine operation, backup, restore, and ordinary upgrades must not require interactive SQL or direct SQLite administration.

## Documentation

Start with [`docs/README.md`](docs/README.md).

Architecture decisions are recorded under [`docs/adr/`](docs/adr/). In particular:

- ADR-0008 — workstation hosting;
- ADR-0009 — SQLite for V1;
- ADR-0010 — Django application stack.
