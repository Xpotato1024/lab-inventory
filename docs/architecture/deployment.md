# Deployment architecture

## Selected hosting model

The authoritative application is hosted on an always-on laboratory workstation.

```text
Laboratory member
      |
      | HTTPS
      v
Laboratory custom domain
      |
      v
Controlled ingress
      |
      v
Always-on workstation
      |
      +--> application runtime
      |
      +--> operational datastore
```

See ADR-0008 for the decision rationale.

## Design objective

Deployment should be understandable to a future laboratory maintainer who is comfortable with basic Python/container operations but should not be expected to administer the database interactively.

Routine operation and routine maintenance must not require direct SQL.

## Ingress

Preferred shape:

```text
Internet / laboratory network
        |
        v
Secure managed ingress/tunnel
        |
        | outbound-established connection
        v
Workstation application
```

A secure outbound tunnel is preferred when the laboratory domain/account configuration permits it because it avoids exposing an inbound application port and reduces local TLS administration.

A conventional HTTPS reverse proxy is the fallback.

The application must not depend on the specific ingress provider.

## Workstation responsibilities

The workstation is responsible for:

- running the application runtime;
- running or storing the selected operational datastore;
- holding only runtime configuration and secrets that cannot live in Git;
- producing recoverable backups according to the operations documentation;
- exposing the application only through the selected controlled ingress.

The workstation filesystem itself is not the authoritative definition of the application. A replacement workstation must be reconstructable from:

1. the Git repository;
2. documented runtime configuration;
3. secrets/credentials from the designated handover mechanism;
4. a verified datastore backup.

## Routine maintainer interface

Expected routine commands should be wrapped and documented around a small set of operations:

```text
start
stop
status
logs
update
backup
restore
```

Exact commands will be defined after the application runtime and database engine are selected.

Maintainers should not need to manually compose SQL, edit production database files, or modify application source code for these procedures.

## Failure model

The deployment documentation must eventually cover at least:

- application process/container failure;
- workstation reboot;
- workstation disk loss;
- datastore corruption or accidental destructive change;
- loss of ingress/tunnel connectivity;
- loss or transfer of domain/ingress credentials.

## Open implementation decisions

This document does not select:

- the application framework;
- the database engine;
- the container/process supervisor;
- the exact ingress provider;
- the backup destination.

Database engine selection is tracked by ADR-0009.
