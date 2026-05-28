# Architecture

OPERIA Forensic Tracing is being refactored into a single modular platform, not a mechanical merge of legacy folders.

## Current Architecture

```text
apps/api
  FastAPI entry point

apps/web
  React frontend shell

operia/core
  Shared configuration, database, and router wiring

operia/shared
  Cross-module utilities

operia/legal_report
  Migrated legal-forensic report backend

operia/cybercrime
  Migrated cybercrime intelligence backend

operia/geo_trace
  Migrated IP/URL geolocation and risk scoring backend

operia/geo_proximity
  Migrated nearest-location backend
```

## Target Architecture

The final professional architecture should move shared domain ownership out of individual migrated modules.

```text
operia/
  core/
  shared/
  identity/
  cases/
  evidence/
  intelligence/
  cybercrime/
  geo/
  legal/
  reports/
  exports/
  dashboard/
  settings/
  audit/
```

## Design Principles

- One platform, one API, one database.
- Modules communicate through canonical domain services.
- Shared concepts belong to shared modules, not migrated legacy modules.
- Reports and exports are platform services.
- Evidence and chain of custody are platform services.
- Cybercrime, legal, and geo modules consume shared case/evidence/report services.
- The architecture should be ready for authentication, organizations, roles, and SaaS tenancy.

## Known Architectural Debt

The current migration temporarily uses `legal_report.models` as the source of shared models like `Case`, `Evidence`, and `Report`.

This works for migration, but it is not the final architecture. These models should move into canonical modules:

- `operia/cases`
- `operia/evidence`
- `operia/reports`
- `operia/exports`
- `operia/identity`
- `operia/audit`

