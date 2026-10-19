# Roadmap

Estado actualizado al 2026-10-18: consultar la [matriz de continuidad](DELIVERY_STATUS.md).
Las listas siguientes conservan la planificación inicial y no acreditan pendientes
actuales. E2 se implementa en [custodia append-only](CUSTODY_APPEND_ONLY.md).
E3 incorpora [permisos por expediente](CASE_ACCESS_CONTROL.md). E4 ya incorpora la
[base visual con shadcn/ui y Tailwind](FRONTEND_VISUAL_BASE.md): navegación, listado
de casos y expediente, validados con datos sintéticos y regresión completa.
E4 también incorpora [evidencias, formularios e informes](E4_EVIDENCE_REPORTS.md),
con accesibilidad de los recorridos intervenidos, descargas autenticadas y pruebas.
La migración de [módulos heredados y revisión técnica de accesibilidad](E4_LEGACY_MODULES.md)
se completó el 2026-10-18. Continúa pendiente la validación con lectores de pantalla
y dispositivos físicos; no hay certificación global WCAG. Las pantallas de estado
Geo Trace, Geo Proximity y exportaciones conservan su alcance funcional previo.

E5 incorpora la [importación pasiva de resultados estáticos](STATIC_LAB.md), con
custodia, hashes y aislamiento por expediente. La continuidad de esta entrega agrega
la [interfaz premium y la incorporación revisada a hallazgos e informes](STATIC_LAB_INTERFACE.md).
La continuidad incorpora [CPython AST real, trabajos persistentes y revisiones](STATIC_PROVIDER_JOBS.md),
validados con fuente Python benigna; no acredita análisis APK o de ejecutables.
El registro pendiente de dispositivos reales está en [accesibilidad asistida](ASSISTIVE_ACCESSIBILITY.md).

E6 incorpora el [motor 0.2.0 y dos lectores de metadatos de backups iOS](forensic_engine/E6_BACKUP_METADATA.md).
La validación del proveedor real usa procesos aislados y fixtures sintéticos;
la cobertura amplia de SQLite/WAL/SHM, archivos lógicos y adquisiciones reales sigue pendiente.

Continuidad: [motor 0.3.0](forensic_engine/E6_MANIFEST_SQLITE.md) incorpora Files de
Manifest.db y catálogo SQLite ordinario sobre copias privadas, sin extender esa
validación sintética a registros lógicos, sidecars o dispositivos reales.

Continuidad 0.4.0: [WAL/SHM acotados](forensic_engine/E6_WAL_SHM.md),
instantánea derivada del último commit y cabeceras SHM contrastadas sobre conjuntos
preservados. Continúan pendientes formatos fuera del perfil, registros lógicos,
capturas consistentes autorizadas por versión y validación en dispositivos reales.

Continuidad actual: [cierre técnico acotado de E6, motor 0.7.0](forensic_engine/E6_CLOSURE_0_7_0.md),
13 lectores / 11 formatos, regresión completa y demostración de perfil público
externo. Adquisiciones de dispositivos y corpus por OS pendientes por falta de
muestras. La siguiente etapa del prompt maestro es E7, operación productiva.
Las listas de scaffold siguientes se conservan como roadmap histórico; el estado
vigente por etapa está en [DELIVERY_STATUS](DELIVERY_STATUS.md).

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

