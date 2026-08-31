# ADR-0009: Use SQLite as the V1 operational database

- Status: Accepted
- Date: 2026-08-31

## Context

ADR-0008 selects laboratory-workstation hosting. The database decision should optimize long-term handover and recovery, not theoretical scale.

The expected workload is small and read-heavy. Writes are primarily short inventory adjustments, placement changes, validated imports, and inventory-count corrections. The database remains the operational source of truth and must preserve transactional integrity and audit history.

A future maintainer must not need SQL knowledge for routine operation.

## Decision

Use **SQLite** as the V1 operational database through the Django ORM.

The application must follow these constraints:

1. direct SQL is not part of normal operation, deployment, backup, restore, or routine upgrades;
2. write transactions must remain short and must not include user interaction, file parsing, network access, sleeps, or other avoidable blocking work;
3. stock and placement mutations must write their audit record in the same logical transaction;
4. bulk-import validation and preview happen before the write transaction begins;
5. the application must not depend on `SELECT ... FOR UPDATE`, which SQLite does not support;
6. concurrency-sensitive quantity changes should use atomic database updates and constraints rather than read-modify-write logic in application memory;
7. live backups must use SQLite's database-aware backup mechanism, not a blind copy of an open database file;
8. restore must be exposed through a documented wrapper command and performed with the application write path stopped;
9. SQLite-specific behavior must be isolated so migration to PostgreSQL remains practical.

## Runtime configuration

The initial target configuration is:

- SQLite database stored on a local filesystem on the workstation, never on a network filesystem;
- WAL journal mode for concurrent readers and a writer;
- a finite busy timeout so short write contention waits rather than failing immediately;
- short explicit `transaction.atomic()` scopes around compound mutations;
- `ATOMIC_REQUESTS` remains disabled.

Exact timeout/checkpoint values are implementation configuration rather than domain semantics and may be tuned from observed operation.

## Why SQLite is appropriate here

SQLite removes an entire separately managed database service, including database credentials, service lifecycle, network configuration, and independent server-version upgrades.

The application's expected write pattern is substantially below the point where a server database is normally required. SQLite serializes writers, but readers and a writer can proceed concurrently in WAL mode. This is compatible with a laboratory application in which searches and 3D views dominate and writes are brief administrative actions.

A synthetic validation performed during the architecture phase used Python 3.13.5 with SQLite 3.46.1. A transaction consisted of a quantity update plus an audit insert. Results were:

- 20 concurrent writer threads performing 1,000 short transactions: 0 lock errors;
- 20 editors plus a 10,000-row bulk write transaction: 0 lock errors;
- deliberately holding each write transaction open for 50 ms caused lock timeouts under 10–20 concurrent writers.

This is not a production benchmark and does not establish a capacity guarantee. It validates the architectural rule that **transaction duration, not data volume alone, is the critical SQLite risk for this workload**.

See `../architecture/sqlite-validation.md` for the validation method and acceptance criteria.

## Backup and recovery

The project must provide application-level commands/scripts that hide database-specific details.

Normal maintainer operations should reduce to concepts such as:

```text
backup
restore <backup>
verify
```

For SQLite, backup must use the Online Backup API (available through Python's `sqlite3` library) or another SQLite-aware snapshot mechanism. A live `cp db.sqlite3 ...` is not an accepted backup procedure.

The restore procedure must:

1. stop the application write path;
2. preserve the current database as a recovery copy;
3. restore the selected snapshot;
4. run an integrity check;
5. run Django migrations/checks as applicable;
6. restart and verify the application.

Backups must ultimately leave the workstation so workstation loss is not also backup loss.

## PostgreSQL migration triggers

SQLite is not an indefinite commitment. Reconsider this ADR if any of the following occurs:

- observed `database is locked` failures despite short transactions and reasonable timeout configuration;
- sustained or routine concurrent write workloads become normal;
- the application must run from multiple hosts against one database;
- a required feature depends on row-level locking or other PostgreSQL-specific concurrency behavior;
- bulk operations require write transactions long enough to materially disrupt routine use;
- operational evidence shows that PostgreSQL would reduce, rather than increase, total maintenance risk.

Migration should be performed through Django migrations/data export-import tooling, not by introducing backend-specific SQL throughout the application.

## Consequences

### Positive

- one fewer service for future maintainers;
- no database credentials or network database configuration;
- backup/restore can be wrapped entirely in Python management commands;
- easy local development and workstation replacement;
- sufficient concurrency for the expected V1 workload when transactions are correctly designed.

### Negative

- only one writer proceeds at a time;
- long transactions are operationally dangerous;
- `select_for_update()` is unavailable;
- some future features may require migration to PostgreSQL;
- WAL requires the database to reside on a local filesystem shared by all application processes on the same host.

## References

- Django SQLite database notes: https://docs.djangoproject.com/en/5.2/ref/databases/
- SQLite isolation: https://www.sqlite.org/isolation.html
- SQLite WAL: https://www.sqlite.org/wal.html
- SQLite Online Backup API: https://www.sqlite.org/backup.html
