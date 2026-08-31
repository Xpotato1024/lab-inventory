# ADR-0010: Use a conventional Django server-rendered application stack

- Status: Accepted
- Date: 2026-08-31

## Context

The project must remain maintainable after the original author leaves the laboratory. Routine users should need only a browser, while maintainers should be able to understand deployment with ordinary Python and Docker knowledge.

The application needs authentication, forms, transactional mutations, validation, an administrative interface, migrations, audit data, search pages, structured import/export, and a procedural 3D view. It does not require an independent SPA frontend or high-throughput asynchronous API platform.

## Decision

Use the following V1 application stack:

- **Python 3.13** as the application runtime;
- **Django 5.2 LTS** as the web framework;
- **server-rendered Django templates** for normal pages;
- **minimal vanilla JavaScript** for interactive behavior;
- **Three.js** only for the procedural 3D view;
- **Gunicorn** as the production WSGI application server;
- **WhiteNoise** for collected static assets;
- **SQLite** as selected by ADR-0009;
- **Docker Compose** as the workstation deployment interface.

No Node.js runtime or frontend build pipeline is required for V1 operation or deployment.

## Version policy

Django 5.2 is selected because it remains under extended security/data-loss support until April 2028. The project should track the latest 5.2 patch release while on this series.

Django 6.2 LTS is scheduled for April 2027 and is the planned next major framework upgrade target. That upgrade is maintenance work, not a prerequisite for V1.

Python 3.13 is selected as a current stable Python series supported by Django 5.2 and suitable for a conservative container runtime.

## Why Django

Django keeps several operational concerns inside one well-documented framework:

- authentication and sessions;
- authorization/groups;
- forms and validation;
- ORM and migrations;
- database transactions;
- CSRF protection;
- administrative data interface;
- server-rendered templates;
- test framework.

Using these built-in facilities reduces the amount of project-specific infrastructure that future maintainers must learn.

## Why not a separate SPA/API architecture

A React/Next/Vue frontend plus a separate API would introduce:

- a second dependency ecosystem and build toolchain;
- duplicated routing/data-contract concerns;
- additional authentication and CSRF/CORS design;
- more deployment artifacts;
- more handover surface without a demonstrated requirement.

The procedural 3D viewer does not require the rest of the application to become an SPA.

## Static assets

Django's development static-file server is not appropriate for production. WhiteNoise is used to serve collected static files from the same application deployment boundary, avoiding a separate nginx/static-file service solely for this application.

User-uploaded files, if introduced later, must be reconsidered separately; WhiteNoise is for versioned/static application assets, not arbitrary uploaded media.

## WSGI rather than ASGI for V1

V1 does not require WebSockets, long-lived async requests, or async background orchestration. A conventional synchronous WSGI deployment is therefore simpler.

ASGI may be introduced later if a concrete feature requires it; it is not prohibited by the domain architecture.

## Dependency discipline

- Prefer the Python standard library and Django built-ins where practical.
- Add third-party packages only for a concrete requirement.
- Pin production dependencies to reviewed versions.
- Routine deployment must not require npm, pnpm, yarn, or another JavaScript package manager.
- Three.js should be version-pinned and served as a project static dependency rather than depending on a mutable CDN URL at runtime.

## Consequences

### Positive

- one primary language/runtime for backend and operations;
- no frontend compilation requirement;
- standard Django knowledge is sufficient for most future modifications;
- built-in authentication/admin/migrations reduce custom code;
- one application container can serve both dynamic pages and static application assets.

### Negative

- highly interactive screens require deliberate vanilla-JS implementation;
- future SPA-scale requirements would require revisiting this decision;
- Gunicorn/WhiteNoise are additional Python dependencies, though they replace separate infrastructure components.

## References

- Django supported versions: https://www.djangoproject.com/download/
- Django deployment: https://docs.djangoproject.com/en/5.2/howto/deployment/
- Django static file deployment: https://docs.djangoproject.com/en/5.2/howto/static-files/deployment/
- Gunicorn: https://gunicorn.org/
- WhiteNoise Django integration: https://whitenoise.readthedocs.io/en/stable/django.html
