# ADR-0008: Select deployment and runtime architecture

- Status: Proposed
- Date: 2026-08-31

## Context

The laboratory has an always-on workstation capable of hosting background services and has access to a laboratory domain. However, the project explicitly prioritizes long-term maintainability and low operational burden, so managed/static deployment options must be considered rather than assuming self-hosting.

The operational application is stateful: users must be able to change inventory, placement, layout metadata, and audit state from the GUI. Therefore deployment must support authenticated writes to one operational datastore.

## Evaluation criteria

The selected model should minimize the total handover burden, not merely the number of initial deployment commands.

Important criteria are:

1. routine users need only a browser;
2. no source-code changes for ordinary operations;
3. one clear operational source of truth;
4. straightforward authentication and access restriction;
5. straightforward backup and disaster recovery;
6. custom-domain support;
7. low server/runtime maintenance burden;
8. understandable local development and migration path;
9. minimal provider-specific lock-in;
10. ability to serve the procedural 3D UI and structured import/export workflows.

## Option A: GitHub Pages as the operational application

GitHub Pages is static hosting and does not execute Python or other conventional server-side application code. A Pages-only deployment therefore cannot directly provide the authenticated transactional write backend required by this system.

It could host:

- project documentation;
- a read-only demonstration;
- a static snapshot/viewer generated from exported data.

It should not host the authoritative operational application.

### Split Pages + external API variant

A static Pages frontend could call a separately hosted API/database. This technically supports writes, but it introduces two deployment boundaries, cross-origin/authentication concerns, and a second operational component solely to preserve Pages hosting.

This is not considered simpler than serving the frontend and backend from the same application runtime.

## Option B: Laboratory workstation hosting

Run one application on the laboratory workstation and publish it through a controlled ingress path.

Candidate shape:

```text
Browser
  -> HTTPS/custom domain
  -> secure tunnel or reverse proxy
  -> one application
  -> operational database
```

If the laboratory domain is managed in Cloudflare, Cloudflare Tunnel is a strong ingress option because the workstation establishes outbound connections and no inbound application port must be opened. If the domain/network is not suitable for Cloudflare Tunnel, a conventional reverse proxy/TLS arrangement remains possible.

The application framework/database choice remains a sub-decision. Current candidates include Django with PostgreSQL and a deliberately evaluated Django/SQLite variant for very low concurrency. PostgreSQL is the safer production default; SQLite would reduce service count but introduces concurrency limits and requires carefully documented safe backup behavior.

### Advantages

- preserves the single-application architecture;
- can use broadly understood server frameworks and databases;
- full control over data and migration;
- makes use of existing always-on laboratory infrastructure;
- procedural 3D and GUI workflows have no special platform constraints.

### Costs

- workstation/OS/container lifecycle must be maintained;
- database backups and restore procedures are laboratory responsibilities;
- workstation/network outage affects the service;
- secure ingress and application patching must be documented.

## Option C: Cloudflare Workers + D1

Serve static assets and application API logic from one Cloudflare Worker and use D1 as the operational SQL datastore.

Cloudflare Workers can serve a full-stack application and custom domains. D1 provides managed SQLite-semantics SQL storage and point-in-time recovery. Cloudflare Access can restrict access before requests reach the Worker.

### Advantages

- removes workstation, reverse-proxy, and database-server maintenance from the operational path;
- frontend and backend can still deploy as one application;
- custom-domain and TLS management are handled by the platform;
- managed database recovery reduces routine backup burden;
- Git-based CI/CD can make deployment repeatable.

### Costs

- application/runtime becomes Cloudflare-specific;
- implementation would move away from the previously considered conventional Django stack;
- local development and administration require Cloudflare tooling such as Wrangler;
- account/domain ownership and access must be handed over correctly;
- migration away from D1/Workers is possible but is a deliberate project rather than a simple server move.

## Preliminary assessment

- GitHub Pages alone: unsuitable for the operational application.
- GitHub Pages + separate backend: technically possible but adds complexity without a clear benefit; not recommended.
- Workstation-hosted single application: strong candidate because suitable hardware already exists and it preserves a conventional, portable architecture.
- Workers + D1: strong alternative if minimizing server administration is valued more highly than provider neutrality and conventional backend tooling.

The current preference is **Option B, workstation-hosted single application with simplified secure ingress**, but this ADR remains Proposed until the team explicitly accepts the operational trade-off against Option C.

## External references

- GitHub Pages server-side language limitation: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- Cloudflare Tunnel: https://developers.cloudflare.com/tunnel/
- Cloudflare Workers full-stack applications: https://developers.cloudflare.com/workers/static-assets/routing/full-stack-application/
- Cloudflare D1: https://developers.cloudflare.com/d1/
- Cloudflare D1 Time Travel: https://developers.cloudflare.com/d1/reference/time-travel/
- Cloudflare Access for Workers: https://developers.cloudflare.com/workers/configuration/cloudflare-access/

## Decision required before implementation foundation

Before application scaffolding is committed, choose either:

1. workstation-hosted conventional application; or
2. Workers + D1 managed application.

The domain model and placement specifications are intentionally independent of this choice.
