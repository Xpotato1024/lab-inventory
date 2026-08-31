# ADR-0009: Select the operational database engine

- Status: Proposed
- Date: 2026-08-31

## Context

ADR-0008 selects laboratory-workstation hosting. The remaining database decision should optimize long-term handover and recovery, not merely theoretical production scale.

Expected workload is small and read-heavy. Writes are primarily inventory adjustments, placement changes, imports, and inventory counts. However, the database is the operational source of truth and must preserve transactional integrity and audit history.

A future maintainer should not need to know SQL for routine operation.

## Required operational property

Regardless of engine selection:

> Direct SQL must not be required for normal operation, deployment, backup, restore, or routine upgrades.

Routine workflows must use the application GUI, validated imports, migrations, and documented wrapper scripts.

SQL/database expertise may still be useful for exceptional corruption analysis or major application development, but it is an emergency/developer skill rather than a routine administrator requirement.

## Option A: SQLite

Use a single SQLite database file managed by the application.

### Advantages

- no separate database service;
- no database credentials or network configuration;
- simple deployment topology;
- straightforward file-level portability;
- well suited to a low-write-concurrency laboratory application;
- significantly reduces the number of components a future maintainer must understand.

### Risks and requirements

- concurrent writes are more constrained than PostgreSQL;
- backups must use a safe application/database-aware procedure rather than blindly copying a live file;
- long-running writes or poorly designed transactions can cause lock contention;
- some future features may eventually justify migration to a server database.

## Option B: PostgreSQL

Run PostgreSQL as a separate service, likely alongside the application through the workstation deployment stack.

### Advantages

- stronger behavior under concurrent writes;
- conventional production database for Django-class server applications;
- mature dump/restore and operational tooling;
- more headroom for future features and data volume.

### Costs

- additional service lifecycle and version upgrades;
- database credentials and persistent-volume configuration;
- backup/restore tooling is more involved internally;
- more operational concepts must be handed over even if scripts hide most routine commands.

## Selection criteria

Before accepting this ADR, validate:

1. expected number of simultaneous editors;
2. expected bulk-import and inventory-count write patterns;
3. whether application transactions can be kept short;
4. backup and restore simplicity for each engine;
5. migration portability through the selected application ORM;
6. recovery procedure after total workstation loss;
7. whether any planned V1 feature genuinely requires server-database concurrency.

## Current assessment

SQLite is the current simplicity-oriented candidate for V1 because the expected workload is low-concurrency and the project explicitly minimizes handover burden.

PostgreSQL remains the conservative production alternative if workload testing or feature requirements show that SQLite's write-concurrency model is unsuitable.

No application code should depend on SQLite-specific behavior unless this ADR is accepted and the dependency is documented.

## Decision gate

Before implementation foundation is considered stable:

- define a representative concurrent-write test;
- define backup/restore procedures for the candidate engine;
- select SQLite or PostgreSQL;
- record the migration path if future scale requires changing engines.
