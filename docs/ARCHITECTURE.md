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

operia/identity
  Organizations, users, roles, memberships

operia/cases
  Canonical cases, technical data, findings, hypotheses, damages

operia/evidence
  Canonical evidence and chain of custody

operia/reports
  Canonical reports, sections, versions, reviews, presentations

operia/exports
  Canonical export interface

operia/legal_knowledge
  Argentine legal sources, articles, citations, mappings, evaluations

operia/ai_assistant
  Local Ollama/Mistral assistance with human-review guardrails

operia/ai_security
  Controlled model tests, logs, reports, and risk scoring

operia/audit
  Audit logs

operia/legal_report
  Legal-forensic responsibilities and compatibility routes

operia/cybercrime
  Migrated cybercrime intelligence backend

operia/geo_trace
  Migrated IP/URL geolocation and risk scoring backend

operia/geo_proximity
  Migrated nearest-location backend
```

## Target Architecture

Shared domain ownership has started moving out of individual migrated modules. The remaining target is to migrate the frontend and remove legacy aliases after compatibility tests pass.

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
  legal_knowledge/
  ai_assistant/
  ai_security/
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

`legal_report.models` and `legal_report.schemas` are no longer the source of shared platform contracts. They remain as compatibility export paths only; canonical ownership lives in `identity`, `cases`, `evidence`, `reports`, `legal_knowledge`, `exports`, and `audit`.

Canonical ownership now lives in:

- `operia/cases`
- `operia/evidence`
- `operia/reports`
- `operia/exports`
- `operia/identity`
- `operia/audit`
- `operia/legal_knowledge`
- `operia/ai_assistant`
- `operia/ai_security`

Remaining debt:

- `legal_report.router` still exposes several legacy combined workflows.
- export implementation delegates to the migrated legal report exporter while templates are stabilized.
- frontend routes still need to move from module placeholders to the canonical API.
