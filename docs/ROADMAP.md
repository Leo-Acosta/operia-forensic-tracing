# Roadmap

Estado actualizado al 2026-10-17: consultar la [matriz E0/E1](E0_E1_SECURITY_BASELINE.md).
Las listas siguientes conservan la planificación inicial y no acreditan pendientes
actuales. Las próximas prioridades son E2 (custodia append-only) y E3 (ACL por expediente).

## Near Term

- Refactor shared models into canonical modules.
- Normalize API paths.
- Add Alembic migrations.
- Build smoke tests for core workflows.
- Replace placeholder frontend screens with real module UIs.

## Mid Term

- Add authentication.
- Add organization/team support.
- Add role-based access control.
- Add audit logging.
- Improve PDF/DOCX export layout.
- Add evidence upload workflow to the frontend.

## Long Term

- Multi-tenant SaaS mode.
- PostgreSQL production support.
- Background jobs for heavy exports and analysis.
- Advanced dashboards.
- External tool connector registry.
- Deployment profiles for local, lab, and cloud environments.

## Core Workflow Target

```text
Create case
  -> Add technical data
  -> Upload evidence
  -> Hash and custody logging
  -> Run cybercrime/geo analysis
  -> Create findings
  -> Build hypotheses
  -> Legal mapping
  -> Generate report
  -> Review
  -> Export PDF/DOCX
  -> Dashboard/audit visibility
```

