# Backup and restore

This procedure is intentionally designed so routine maintainers do not need SQL or the SQLite command-line shell.

## Storage model

The container sees:

- operational database: `/data/db.sqlite3`
- backup directory: `/backups`

The host paths mounted at those locations are configured by:

- `LAB_INVENTORY_HOST_DATA_DIR`
- `LAB_INVENTORY_HOST_BACKUP_DIR`

For disaster recovery, configure `LAB_INVENTORY_OFFSITE_BACKUP_DIR` as a **mounted path backed by a different physical system**, for example a NAS share or other independently stored filesystem.

A second directory or second disk path on the same workstation is not considered sufficient disaster recovery by itself.

## Create an online local backup

The application may remain online.

```sh
sh scripts/backup.sh
```

The command uses SQLite's Online Backup API through Python and verifies the resulting snapshot before reporting success.

Do **not** use `cp` on the live operational database as the normal backup procedure.

## Create and mirror a verified backup

For routine scheduled protection, prefer:

```sh
sh scripts/backup-mirror.sh
```

Requirements:

1. the application is running;
2. `LAB_INVENTORY_HOST_BACKUP_DIR` points to the local host backup directory;
3. `LAB_INVENTORY_OFFSITE_BACKUP_DIR` points to a mounted, writable path on separate storage.

The wrapper:

1. asks the running application to create a database-aware online backup under `/backups`;
2. relies on the application command to run SQLite integrity and foreign-key checks before success;
3. confirms the corresponding host backup file exists;
4. copies the verified file to a temporary name on separate storage;
5. compares the local and mirrored files byte-for-byte;
6. renames the temporary copy to its final timestamped filename only after comparison succeeds.

If copying or comparison fails, no incomplete file is promoted to the final mirrored-backup filename.

### Suggested daily scheduling

Once a real separate-storage mount is configured and tested manually, a simple host cron entry is sufficient. Example for a checkout under `/opt/lab-inventory`:

```cron
17 3 * * * cd /opt/lab-inventory && sh scripts/backup-mirror.sh >> /var/log/lab-inventory-backup.log 2>&1
```

The exact schedule and log location are workstation policy. Run the command manually first and confirm a valid file appears on the separate storage before enabling unattended scheduling.

Do not add an automatic deletion job until a retention policy has been explicitly agreed and at least one independently stored known-good backup is confirmed.

## Verify a backup manually

Normally local backup verification is automatic. For troubleshooting:

```sh
docker compose exec -T web python manage.py verify_db /backups/<filename>.sqlite3
```

A successful result means SQLite integrity and foreign-key checks passed. It does not replace application-level validation or testing that the separate-storage copy can actually be read during recovery.

## Restore

Restore is deliberately offline because replacing the source-of-truth file while web workers are writing would be unsafe.

List the host backup directory and select the intended snapshot, then run:

```sh
sh scripts/restore.sh <backup-filename>.sqlite3
```

If the required backup exists only on separate storage, copy that verified backup into `LAB_INVENTORY_HOST_BACKUP_DIR` first. Do not restore directly across an unreliable network mount.

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

Create the host data/backup directories, start the stack once if necessary, copy the selected separate-storage backup into the mounted local backup directory, and use the standard restore wrapper.

After recovery, immediately run a new local + mirrored backup and verify the production hostname/QR workflow.

## Backup retention

Exact retention is an operations policy rather than application semantics. A reasonable initial policy is to retain multiple recent daily snapshots plus less frequent older snapshots, with at least one copy outside the workstation.

The application intentionally does not automatically delete backups in V1. This avoids turning a retention configuration mistake into silent loss of the only known-good recovery point.
