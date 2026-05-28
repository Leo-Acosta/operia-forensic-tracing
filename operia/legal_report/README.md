# Forensic Legal Report Module

This module migrates the backend functionality from `Old_Operia Forensic Legal Report` into the new OPERIA Forensic Tracing architecture.

## Mounted API Prefix

The module is mounted under:

```text
/api/legal-report
```

Examples:

```text
GET  /api/legal-report/dashboard
POST /api/legal-report/cases
POST /api/legal-report/cases/{case_id}/reports/generate
GET  /api/legal-report/reports/{report_id}/export/{markdown|html|docx|pdf}
POST /api/legal-report/reports/{report_id}/review
POST /api/legal-report/reports/{report_id}/polish
POST /api/legal-report/reports/{report_id}/presentations/generate
GET  /api/legal-report/presentations/{presentation_id}/export/pdf
```

## Adaptation Notes

- Legacy imports from `app.*` were moved to `operia.legal_report.*`.
- Database access now uses the common `operia.core.database` engine/session.
- Uploads and exports now use shared storage paths from `operia.core.config`.
- Hashing delegates to `operia.shared.hashing` through a small compatibility wrapper.
- Startup seeding moved to `operia.legal_report.bootstrap`.

## Not Migrated Yet

- The legacy Forensic Legal Report frontend screen has not been merged into the new web app.
- Alembic migrations are not defined yet.
- The canonical cross-module data model is still pending.

