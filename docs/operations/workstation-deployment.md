# Workstation deployment

This document prepares the application for the selected always-on laboratory-workstation deployment. The public ingress technology is intentionally outside the application container and can be a secure outbound tunnel or a conventional reverse proxy.

## Deployment boundary

The application listens only on the workstation loopback interface:

```text
Browser
  -> HTTPS / long-lived laboratory hostname
  -> controlled ingress on/for the workstation
  -> http://127.0.0.1:8000
  -> Docker Compose `web`
  -> SQLite SoT under /srv/lab-inventory/data
```

Do not expose Gunicorn directly to the Internet.

## 1. Prepare persistent directories

Keep operational data outside the Git checkout so a re-clone, branch switch, or source rollback cannot accidentally delete the SoT.

Example Linux workstation setup:

```sh
sudo install -d -o "$USER" -g "$(id -gn)" /srv/lab-inventory/data
sudo install -d -o "$USER" -g "$(id -gn)" /srv/lab-inventory/backups
```

The database and backup paths should live on reliable local storage. A local backup directory on the same workstation is **not** sufficient disaster recovery; copy verified backups to separate storage as well.

## 2. Prepare `.env`

From the repository checkout:

```sh
cp .env.production.example .env
```

Generate a secret without an external password service:

```sh
python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Edit `.env` and set at least:

```text
DJANGO_SECRET_KEY=<generated secret>
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=inventory.<laboratory-domain>
DJANGO_CSRF_TRUSTED_ORIGINS=https://inventory.<laboratory-domain>
LAB_INVENTORY_HOST_DATA_DIR=/srv/lab-inventory/data
LAB_INVENTORY_HOST_BACKUP_DIR=/srv/lab-inventory/backups
```

The production hostname should be chosen before durable QR labels are printed.

## 3. Run preflight

```sh
sh scripts/preflight.sh
```

Preflight verifies:

- Docker and Docker Compose v2 are available;
- `.env` is present and production mode is selected;
- the secret is not the repository placeholder;
- persistent directories exist and are writable;
- Compose configuration parses;
- the image builds;
- Django deployment checks pass.

It does not start the long-running application service.

## 4. Start the application

```sh
docker compose up -d --build --wait
```

Verify:

```sh
curl --fail http://127.0.0.1:8000/healthz/
docker compose ps
docker compose logs --tail=100 web
```

Normal startup applies Django migrations, configures SQLite WAL mode, synchronizes standard authorization groups, collects static files, runs deployment checks, and then starts Gunicorn.

## 5. Create the first technical administrator

```sh
docker compose exec web python manage.py createsuperuser
```

Use the administrator account to create initial user accounts and assign Viewer / Editor / Maintainer groups. Routine layout and master-data work should subsequently use the normal `Layout` and `Master` pages rather than Django Admin where possible.

## 6. Connect ingress

Configure the chosen ingress to proxy/tunnel to:

```text
http://127.0.0.1:8000
```

Requirements:

- the browser-visible URL is HTTPS;
- the original production Host header reaches Django;
- `X-Forwarded-Proto: https` is supplied when TLS terminates before Gunicorn;
- direct external access to workstation port 8000 is not opened;
- the production hostname exactly matches `.env` host/CSRF settings.

The application already trusts `X-Forwarded-Proto` through Django's `SECURE_PROXY_SSL_HEADER` configuration. Do not send that header from an untrusted publicly reachable proxy path.

## 7. Verify through the production hostname

After ingress is live:

1. sign in through the production HTTPS URL;
2. search an item/location;
3. open `/3d/` and verify the derived viewer loads;
4. generate one temporary QR label and scan it from another device;
5. verify the QR resolves to the production hostname, not localhost or a temporary tunnel name;
6. create an online database backup and verify it.

Do not bulk-print durable QR labels until this check is complete.

## Backup immediately after initial configuration

Once initial users/master/layout data exist:

```sh
sh scripts/backup.sh
```

Then copy the newly verified backup to separate storage. See [Backup and restore](backup-restore.md).

## Update procedure

Before updating application code:

1. create and verify a backup;
2. update the Git checkout to the reviewed target commit/release;
3. run `sh scripts/preflight.sh`;
4. rebuild/restart with `docker compose up -d --build --wait`;
5. verify `/healthz/`, sign-in, search, and one read/write workflow.

Do not edit SQLite manually as part of a routine upgrade. Schema changes are Django migrations and run automatically during controlled startup.

## Rollback principle

Code rollback and data rollback are different operations.

- If only application code is faulty and the schema/data remain compatible, roll source code back and rebuild.
- If a migration/data operation must also be reversed, use an explicitly reviewed restore/migration procedure rather than copying an arbitrary older SQLite file over the live database.

Every destructive recovery should begin with a fresh recovery snapshot of the current database when possible.
