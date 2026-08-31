# ADR-0008: Use laboratory workstation hosting

- Status: Accepted
- Date: 2026-08-31

## Context

The laboratory has an always-on workstation capable of hosting background services and has access to a laboratory domain. The project prioritizes long-term maintainability, low handover burden, and conventional tooling that future laboratory members can understand without learning a provider-specific application platform.

The operational application is stateful: users must be able to change inventory, placement, layout metadata, and audit state from the GUI. Deployment must therefore support authenticated transactional writes to one operational datastore.

GitHub Pages and managed full-stack platforms were evaluated before selecting the hosting model.

## Decision

Run the authoritative operational application on an always-on laboratory workstation.

The deployment boundary is:

```text
Browser
  -> HTTPS / laboratory custom domain
  -> controlled ingress
  -> one workstation-hosted application
  -> one operational datastore
```

The workstation is the application host, but it is not itself the source of truth. The operational datastore remains the authoritative state store as defined by ADR-0002.

Normal users must never need shell access, source-code changes, or direct database access. Routine administration must be exposed through the GUI, validated structured import/export, and documented wrapper commands or scripts.

The exact application framework and database engine are separate implementation decisions. In particular, SQLite versus PostgreSQL is not decided by this ADR.

## Ingress

Prefer an ingress design that minimizes workstation network administration.

If the laboratory domain and account ownership make it practical, an outbound secure tunnel such as Cloudflare Tunnel is preferred because it avoids exposing an inbound application port and delegates public TLS termination.

A conventional reverse proxy with HTTPS remains an acceptable fallback.

The ingress mechanism is not part of the domain model and may be replaced without changing application semantics.

## Operational requirements

The workstation-hosted deployment must satisfy the following:

1. routine users need only a web browser;
2. ordinary inventory and placement operations require no source-code changes;
3. direct SQL must not be required for routine operation, deployment, backup, restore, or ordinary upgrades;
4. application and datastore startup/shutdown must be documented and scriptable;
5. backup and restore procedures must be documented and testable without ad-hoc database commands;
6. secrets and credentials must not be committed to the repository;
7. a workstation failure must be recoverable from repository state, configuration, and backups;
8. the custom-domain and ingress ownership must be transferable to future maintainers.

## Alternatives considered

### GitHub Pages as the operational application

Rejected.

GitHub Pages is static hosting and does not provide the authenticated transactional server-side write path required by the authoritative inventory application.

It remains suitable for:

- project documentation;
- a read-only demonstration;
- static exported snapshots.

### GitHub Pages plus a separate API/backend

Rejected.

This preserves static hosting only by introducing a second deployment boundary, separate authentication/API concerns, and additional operational complexity. It is not simpler than serving the UI and backend from one application runtime.

### Cloudflare Workers + D1

Not selected for the initial architecture.

This approach would reduce server-administration burden, but would move the project toward Cloudflare-specific runtime, database, and deployment tooling. Because an always-on laboratory workstation already exists, the operational savings do not currently justify the additional platform coupling and handover requirements.

This alternative may be reconsidered if maintaining the workstation becomes materially burdensome.

## Consequences

### Positive

- uses infrastructure already available in the laboratory;
- keeps the application architecture conventional and portable;
- avoids splitting the frontend and backend solely for hosting reasons;
- supports the full GUI, procedural 3D view, imports, audit history, and transactional updates without platform-specific restrictions;
- leaves database and application framework choices independently replaceable;
- allows secure publication under the laboratory domain.

### Negative

- workstation OS/runtime lifecycle remains a laboratory responsibility;
- workstation or laboratory network outages can make the application unavailable;
- backup and recovery must be actively maintained and tested;
- security updates and ingress configuration remain operational responsibilities.

## Related decisions

- ADR-0001: single operational application
- ADR-0002: operational datastore as source of truth
- ADR-0006: GUI-first normal operations
- ADR-0009: database engine selection (Proposed)

## External references

- GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- Cloudflare Tunnel: https://developers.cloudflare.com/tunnel/
- Cloudflare Workers: https://developers.cloudflare.com/workers/
- Cloudflare D1: https://developers.cloudflare.com/d1/
