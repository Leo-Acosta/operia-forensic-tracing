# Roadmap

Estado actualizado al 2026-10-17: consultar la [matriz E0/E1](E0_E1_SECURITY_BASELINE.md).
Las listas siguientes conservan la planificación inicial y no acreditan pendientes
actuales. E2 se implementa en [custodia append-only](CUSTODY_APPEND_ONLY.md).
E3 incorpora [permisos por expediente](CASE_ACCESS_CONTROL.md). E4 ya incorpora la
[base visual con shadcn/ui y Tailwind](FRONTEND_VISUAL_BASE.md): navegación, listado
de casos y expediente, validados con datos sintéticos y regresión completa.
E4 también incorpora [evidencias, formularios e informes](E4_EVIDENCE_REPORTS.md),
con accesibilidad de los recorridos intervenidos, descargas autenticadas y pruebas.
La próxima prioridad visual es migrar los módulos heredados restantes y validar
con lectores de pantalla y dispositivos físicos; no hay certificación global WCAG.

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

