# API Routes

Canonical routes:

- `/api/identity`
- `/api/audit`
- `/api/cases`
- `/api/evidence`
- `/api/reports`
- `/api/exports`
- `/api/legal`
- `/api/legal-knowledge`
- `/api/ai`
- `/api/ai-security`
- `/api/cybercrime`
- `/api/geo/trace`
- `/api/geo/proximity`
- `/api/dashboard`
- `/api/settings`

Temporary legacy aliases:

- `/api/legal-report`
- `/api/geo-trace`
- `/api/geo-proximity`
- `/api/users-cases`

Legacy aliases are kept to avoid breaking existing migrated workflows while the frontend and documentation move to canonical routes.

## Phase 5 Notes

`/api/legal` is now a clean legal route focused on legal analysis, legal mappings, consistency enrichment, and report evaluation.

`/api/legal-report` remains as a broad legacy route for migrated workflows that still combine cases, evidence, reports, exports, presentations, and legal operations.

`/api/exports` now supports canonical JSON, CSV, Markdown, and simple PDF payload exports, plus report export helpers.

`/api/legal-knowledge/articles` supports `q` search over the initial Argentine legal article library.

`/api/ai-security/evaluations` supports `run_tests=true` for controlled local tests against the configured Ollama model.

## Phase 10 Export Routes

Canonical export routes now create forensic manifests:

- `POST /api/exports/json`
- `POST /api/exports/csv`
- `POST /api/exports/markdown`
- `POST /api/exports/pdf`
- `GET /api/exports/reports/{report_id}/{json|csv|markdown|pdf}`
- `GET /api/exports/manifests`
- `GET /api/exports/manifests/{manifest_id}`
- `GET /api/exports/manifests/{manifest_id}/download`

Every canonical export returns headers:

- `X-OPERIA-Export-Manifest-Id`
- `X-OPERIA-SHA256`
- `X-OPERIA-Manifest-Path`

## Phase Operativa 1 Routes

Case participants:

- `GET /api/cases/{case_id}/participants`
- `POST /api/cases/{case_id}/participants`
- `PUT /api/cases/participants/{participant_id}`
- `DELETE /api/cases/participants/{participant_id}`

Case closure:

- `GET /api/cases/{case_id}/closure-status`
- `POST /api/cases/{case_id}/close`

Cybercrime indicator analysis:

- `POST /api/cybercrime/analyze-indicator`

Operational PDF export:

- `GET /api/exports/reports/{report_id}/pdf`
