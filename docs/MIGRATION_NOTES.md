# Migration Notes

## Phase 1-4 Refactor

Completed architectural changes:

- created canonical modules for identity, cases, evidence, reports, audit, legal knowledge, AI assistant, and AI security;
- moved shared SQLAlchemy model ownership out of `operia/legal_report`;
- kept `operia/legal_report/models` as a compatibility export path;
- mounted canonical API routes;
- added a lightweight SQLite additive migration for SaaS columns;
- routed Cybercrime, Geo Trace, Geo Proximity, Dashboard, and Reports toward canonical shared models;
- added initial Mistral/Ollama assistant integration with graceful offline behavior;
- added AI model security evaluation records, controlled test catalog, scoring, and report output.

Important compatibility note:

`/api/legal-report`, `/api/geo-trace`, and `/api/geo-proximity` still exist as temporary aliases. They should be removed only after the frontend and tests are fully migrated to canonical routes.

## Phase 5 Refactor

Completed:

- split `/api/legal` into a clean legal router;
- kept `/api/legal-report` as a legacy compatibility router;
- strengthened canonical exports with JSON, CSV, Markdown, and simple PDF payload exports;
- seeded `legal_knowledge` with an initial Argentine cybercrime/legal article library;
- added article search for legal RAG-style assistance;
- hardened `ai_assistant` with guardrails, legal context, case context, and JSON-oriented prompts;
- upgraded `ai_security` to optionally run controlled tests against local Ollama/Mistral and score each response.

Remaining:

- migrate frontend screens to canonical routes;
- build full legal update pipeline against official sources;
- replace legacy report PDF internals with fully canonical templates;
- add auth and authorization enforcement over organization/case scopes.

## Phase 7 Legal Knowledge

Completed:

- expanded the Argentine legal seed library for cybercrime, fraud, access, data protection, consumer protection, civil damages, Budapest preservation/cooperation, and procedural evidence workflows;
- added controlled article seeding/update behavior;
- added structured article search;
- added incident-to-article recommendations;
- added source URL verification endpoints;
- connected AI Assistant legal context to the recommendation engine.

Remaining:

- build a full official-source ingestion pipeline;
- preserve source snapshots per update;
- add legal article diffing by version;
- add richer legal schemas for objective/subjetive elements by jurisdiction and procedural route.

## Phase 9 SaaS Security

Completed:

- added local password hashing and bearer token auth;
- added admin bootstrap and login/logout/me endpoints;
- added auth token storage and revocation;
- added role permission catalog;
- added organization-aware identity listings;
- added audit logging service;
- added audit events for case, evidence, custody, report and identity actions;
- propagated authenticated organization context into new cases, evidence and reports.

Remaining:

- enforce authentication on every write route after frontend login is added;
- add per-case ACLs;
- add MFA/password reset;
- add production-grade secret management;
- add database migrations with Alembic instead of lightweight SQLite additive migration.

## Phase 10 Professional Exports

Completed:

- added `ExportManifest` table;
- added SHA-256 and MD5 calculation for canonical exports;
- added sidecar manifest JSON files;
- added manifest listing and download endpoints;
- added forensic metadata including product, user, organization, case, report, timestamp, file path and review warning;
- added audit logs for export generation;
- added response headers carrying manifest id and SHA-256.

Remaining:

- migrate legacy DOCX/PDF internals into fully canonical templates;
- add signed manifests;
- add export bundle ZIP generation;
- add visual PDF templates with cover page, custody footer and evidence appendix;
- add frontend manifest browser.

## Phase 11 Tests

Completed:

- added pytest fixtures with isolated SQLite test databases;
- avoided system temp dependency by using workspace-local `storage/test_runs`;
- added tests for identity/auth;
- added tests for case/evidence/report/audit flow;
- added tests for legal knowledge;
- added tests for AI assistant offline tolerance;
- added tests for AI Security evaluation and report;
- added tests for export manifests and hashes.

Result:

- `7 passed`

Recommended command:

```powershell
python -m pytest -q -p no:cacheprovider
```

## Phase 8 Canonical Ownership Closure

Completed:

- moved Pydantic contracts out of `legal_report.schemas` into canonical module schemas:
  - `operia/cases/schemas.py`;
  - `operia/evidence/schemas.py`;
  - `operia/legal_knowledge/schemas.py`;
  - `operia/reports/schemas.py`;
  - `operia/shared/schemas.py`;
- kept `operia/legal_report/schemas/domain.py` as a compatibility shim only;
- moved report/DOCX/PDF/presentation export implementation into `operia/exports/report_exporters.py`;
- kept `operia/legal_report/services/export_service.py` as a compatibility shim only;
- updated canonical routers to import schemas and exporters from their owning modules;
- replaced the `users_cases` placeholder response with a real legacy-compatible view backed by canonical `identity` and `cases` models;
- documented that legacy namespaces are now compatibility surfaces, not architectural owners.

Verification:

- `python -m compileall operia apps\api tests` passed;
- FastAPI app import passed with 215 registered routes;
- `python -m pytest -q -p no:cacheprovider` passed with `7 passed`.

Remaining:

- migrate remaining `/api/legal-report` endpoint internals into smaller canonical services before removing the legacy route;
- replace FastAPI `on_event` startup hook with lifespan handlers;
- add Alembic migrations before production database use.

## Fase Operativa 1

Completed:

- added a browser-facing operational workflow for case handling;
- added case participants for physical persons, legal entities, witnesses, victims, harmed parties, suspects, platforms, financial entities and other relevant actors;
- added participant CRUD under canonical case routes;
- added participant audit events;
- added participants to generated forensic reports;
- added file evidence upload with SHA-256/MD5 hash calculation from the frontend flow;
- added chain-of-custody registration from the frontend flow;
- added cybercrime indicator analysis for IP, domain and URL inputs;
- connected legal knowledge search/recommendation into the workflow;
- connected local AI assistance with Mistral/Ollama graceful offline behavior;
- connected report generation, review and canonical PDF export;
- added case closure readiness checks;
- added controlled case closure with audit and custody record;
- changed the workflow to 12 visible steps.

Validated end-to-end:

- created case `OP-FLOW-20260528082936`;
- registered participant;
- uploaded evidence and calculated SHA-256;
- registered custody action;
- analyzed suspicious URL as high risk;
- received legal recommendations;
- called AI assistant, with expected `ollama_unavailable` tolerance when Ollama was not active;
- generated report;
- reviewed report with score `85`;
- exported PDF with HTTP 200;
- closed case successfully.

Final verification:

- `python -m pytest -q -p no:cacheprovider` passed with `7 passed`;
- `npm run build` passed.

## Fase Operativa 2

Completed:

- added `Detalle del Caso` frontend module;
- added case overview metrics for selected case;
- added editable participant records;
- added editable evidence records;
- added editable chain-of-custody records;
- added delete actions for participants, evidence and custody records;
- added visible reports and PDF export links;
- added visible export manifests for the selected case;
- added visible audit log for the selected case;
- added custody update/delete canonical endpoints;
- added audit events for custody updates/deletions;
- added automated test coverage for advanced case management.

Verification:

- `python -m pytest -q -p no:cacheprovider` passed with `8 passed`;
- `npm run build` passed.

Remaining:

- implement a formal case reopening workflow for closed cases;
- enforce closed-case write restrictions server-side;
- add richer evidence detail screens with attachment preview and participant/evidence linking;
- add signed export manifests and immutable audit policies.

## Fase Operativa 3

Completed:

- replaced canonical report PDF generation with a professional forensic report template;
- fixed Spanish text normalization for common mojibake/encoding artifacts in exports;
- added cover metadata, human-review warning, case metrics, participants, evidence, chain of custody, findings, hypotheses, legal mappings, conclusions and export annex sections;
- connected `GET /api/exports/reports/{report_id}/pdf` to the professional report exporter instead of the generic text PDF exporter;
- marked report PDF manifests with `template=forensic_professional`;
- extended automated coverage so the case/evidence/report flow verifies report PDF generation, manifest hash and audit event.

Verification:

- `python -m compileall operia apps\api tests` passed;
- `python -m pytest -q -p no:cacheprovider` passed with `8 passed`.

Remaining:

- add signed manifests;
- add richer legal citation annexes with source snapshots;
- add visual evidence annex previews;
- add report template selection and editable section ordering from the frontend.

## Fase Operativa 5

Completed:

- converted the final PDF into a non-revealing professional forensic-legal report;
- removed visible references to internal assistant providers and fallback behavior from report output;
- added analyst/operator authorship support in the frontend report flow;
- normalized professional case/report state labels for visible exports;
- replaced unresolved responsible values with a formal non-attribution statement;
- unified Argentine legal framing and removed duplicate legal sections;
- prioritized phishing/fraud mappings to registered Argentine legal articles, including CP art. 172;
- added future-ready registered jurisprudence and doctrine models and API routes;
- added an attribution engine with sufficient/insufficient attribution branches;
- added robust attribution and non-attribution conclusion templates;
- added export metadata annex content based on real case/report values;
- extended automated coverage to reject internal terms in enriched report content and generated PDF text.

Verification:

- `python -m compileall operia apps\api tests` passed;
- `python -m pytest -q -p no:cacheprovider` passed with `8 passed`;
- `npm run build` passed.
