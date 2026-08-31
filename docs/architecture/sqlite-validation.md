# SQLite V1 validation

This document records the architecture-phase evidence supporting ADR-0009. It is not a production capacity claim.

## Workload model

The expected application workload is read-heavy:

- item/location search;
- procedural 3D viewing;
- container/location detail pages;
- occasional stock adjustments;
- occasional container movement;
- inventory counts and bulk imports during maintenance events.

Mutations are expected to be short. Validation, parsing, preview generation, and user confirmation must occur outside the write transaction.

## Synthetic concurrency check

Date: 2026-08-31

Environment used for the architecture check:

- Python 3.13.5
- SQLite 3.46.1
- WAL journal mode
- 5 second connection timeout
- one SQLite connection per worker

The representative mutation transaction was:

1. begin write transaction;
2. update one stock quantity;
3. insert one audit record;
4. commit.

### Results

| Scenario | Result |
| --- | --- |
| 2 writers, 100 total short mutations | 0 lock errors |
| 5 writers, 250 total short mutations | 0 lock errors |
| 10 writers, 500 total short mutations | 0 lock errors |
| 20 writers, 1,000 total short mutations | 0 lock errors |
| 40 writers, 2,000 total short mutations | 0 lock errors |
| 20 editors plus one 10,000-row bulk transaction | 0 lock errors |

A deliberately bad scenario held each write transaction open for 50 ms. Under that artificial condition, lock timeout errors appeared with 10–20 concurrent writers.

## Interpretation

The result supports SQLite for V1 only under the architectural constraint that write transactions remain short.

The application must therefore avoid:

- waiting for user input inside a transaction;
- parsing uploaded files inside a transaction;
- performing network calls inside a transaction;
- sleeping/retrying inside a transaction while holding the write lock;
- wrapping every request in a transaction;
- long read-modify-write workflows that can be replaced by atomic database updates.

## Production acceptance checks

Before first production deployment, repeat a representative test using the actual Docker image and workstation storage.

Minimum acceptance criteria:

1. 10 concurrent short mutation workers complete without lock errors;
2. representative inventory import completes without corrupting or losing audit history;
3. routine reads remain responsive during a representative import;
4. database-aware backup succeeds while the application is online;
5. a clean restore into a fresh data directory passes integrity and Django checks.

Failure of these criteria is a reason to revisit ADR-0009 before production.

## Migration trigger

Operational lock failures are evidence, not something to hide indefinitely by increasing timeout values. If short transactions routinely exhaust the configured timeout, evaluate PostgreSQL rather than normalizing repeated retries.
