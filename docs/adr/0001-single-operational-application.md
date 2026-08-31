# ADR-0001: Keep one operational application

- Status: Accepted
- Date: 2026-08-31

## Context

The project must remain maintainable by future laboratory members. The workload is small, the operational team is limited, and the system does not require independent scaling of subsystems.

Splitting the product into independently deployed front-end, API, authentication, inventory, and 3D services would increase deployment and troubleshooting burden without a demonstrated operational benefit.

## Decision

Build and operate the system as one application boundary by default.

Internal modules may be separated in code, but normal deployment should not require coordinating multiple independently versioned application services unless a future requirement justifies that complexity.

## Consequences

### Positive

- simpler deployment and backup procedures;
- fewer failure modes for future maintainers;
- easier local development and end-to-end testing;
- clearer ownership of transactions and audit records.

### Negative

- less independent scaling and deployment flexibility;
- future integrations may require carefully designed interfaces within the monolith.

## Alternatives considered

- separate SPA and REST API deployments;
- microservices by domain area;
- independent 3D service.

These remain possible future changes but are not justified for the initial system.
