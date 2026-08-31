# Backup and restore

This procedure is intentionally designed so routine maintainers do not need SQL or the SQLite command-line shell.

## Storage model

The container sees:

- operational database: `/data/db.sqlite3`
- backup directory: `/backups`

The host paths mounted at those locations are configured by:

- `LAB_INVENTORY_HOST_DATA_DIR`
- `LAB_INVENTORY_HOST_BACKUP_DIR`

The backup directory must also be replicated away from the workstation. A second directory on the same workstation is not sufficient disaster recovery.

## Create an online backup

The application may remain online.

```sh
sh scripts/backup.sh
```

The command uses SQLite's Online Backup API through Python and verifies the resulting snapshot before reporting success.

Do **not** use `cp` on the live operational database as the normal backup procedure.

## Verify a backup manually

Normally backup verification is automatic. For troubleshooting:

```sh
docker compose exec -T web python manage.py verify_db /backups/<filename>.sqlite3
```

A successful result means SQLite integrity and foreign-key checks passed. It does not replace application-level validation or an off-workstation backup policy.

## Restore

Restore is deliberately offline because replacing the source-of-truth file while web workers are writing would be unsafe.

List the host backup directory and select the intended snapshot, then run:

```sh
sh scripts/restore.sh <backup-filename>.sqlite3
```

The wrapper:

1. stops the web service;
2. starts a one-off maintenance container with restore mode enabled;
3. verifies the selected backup;
4. creates a database-aware pre-restore recovery snapshot of the current database;
5. replaces the operational database;
6. verifies the restored database;
7. starts the normal web service again.

If the restore command fails, the wrapper intentionally leaves the web service stopped. Investigate before restarting it.

Pre-restore recovery snapshots are stored under `/backups/recovery/`.

## After restore

Check:

```sh
docker compose ps
docker compose logs --tail=100 web
```

Then open the application and verify at least:

- login works;
- expected recent inventory/location data exists;
- search/detail pages load;
- no migration/startup error appears in logs.

## Workstation-loss recovery

A replacement workstation needs only:

1. this repository at the intended release/commit;
2. Docker Compose;
3. a valid `.env`;
4. an off-workstation SQLite backup;
5. the documented ingress configuration.

Create the host data/backup directories, start the stack once if necessary, place the selected backup in the mounted backup directory, and use the standard restore wrapper.

## Backup retention

Exact retention is an operations policy rather than application semantics. A reasonable initial policy is to retain multiple recent daily snapshots plus less frequent older snapshots, with at least one copy outside the workstation. Do not automatically delete the only known-good backup.
