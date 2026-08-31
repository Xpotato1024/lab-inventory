# ADR-0011: Use pinned Three.js ES modules without a JavaScript build step

- Status: Accepted
- Date: 2026-08-31

## Context

ADR-0005 requires a procedural 3D locator view. The project also prioritizes handover simplicity and deliberately avoids making Node.js, npm, or a frontend build pipeline part of routine maintenance unless they provide a clear operational benefit.

Three.js officially supports browser ES modules through an import map and a CDN in addition to npm/build-tool workflows. The 3D view is a derived convenience view rather than the operational source of truth.

## Decision

Use Three.js `0.185.1` as pinned ES modules loaded from jsDelivr through an import map.

The application-owned viewer code remains a normal Django static ES module. No Node.js, npm, Vite, webpack, or separate frontend application is introduced for V1.

The core search, inventory, placement, audit, import/export, and administration workflows must not depend on Three.js loading successfully.

## Consequences

### Positive

- no JavaScript package manager or build pipeline is added to the handover surface;
- version selection is explicit and reproducible at the application-document level;
- Three.js and OrbitControls can be used directly as ES modules;
- the operational source of truth remains fully usable if 3D rendering is unavailable.

### Negative

- the 3D view requires network access to the pinned CDN URL at browser load time;
- a CDN outage or blocked external access can temporarily disable only the 3D viewer;
- upgrades require deliberately updating the pinned Three.js version and validating the viewer.

## Migration trigger

Replace CDN delivery with locally vendored/build-time assets if any of the following become true:

- the laboratory requires offline-only operation;
- external CDN access is blocked or unreliable;
- the viewer gains enough frontend dependencies that an explicit build pipeline becomes simpler than import-map management.

## References

- Three.js installation guide: https://threejs.org/manual/en/installation.html
- Three.js npm package/version history: https://www.npmjs.com/package/three
