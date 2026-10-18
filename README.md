# OPERIA Forensic Tracing

OPERIA Forensic Tracing is a modular forensic investigation platform for cybercrime intelligence, legal-forensic reporting, geolocation tracing, evidence workflows, AI-assisted analysis, model safety evaluation, dashboards, and professional export pipelines.

The platform is built as a single FastAPI + React application, with a shared local database and modular backend packages.

## Current Capabilities

- Shared cases and technical data.
- Evidence and chain-of-custody workflows.
- Cybercrime Intelligence module.
- Geo Trace module.
- Geo Proximity module.
- Legal Report module.
- Argentine Legal Knowledge library.
- Local AI Assistant prepared for Ollama/Mistral.
- AI Security model risk evaluation.
- SaaS-ready identity foundation.
- Audit logs.
- Canonical exports with SHA-256, MD5 and manifest files.
- React frontend with operational screens.
- Automated test suite.
- Explicit case permissions, audited append-only grants/revocations and worker revalidation: [E3 policy](docs/CASE_ACCESS_CONTROL.md).
- Native mobile forensic engine for selected iOS plist and Android text artifacts (synthetic validation).

## Quick Start On Windows

From the repository root:

```powershell
.\scripts\setup.ps1
```

Start API:

```powershell
.\scripts\start-api.ps1
```

Start frontend in another terminal:

```powershell
.\scripts\start-web.ps1
```

Open:

- App: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8020/docs`
- Health: `http://127.0.0.1:8020/api/health`

## Manual Start

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\prepare_worker_sandbox.py
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8020
```

Frontend:

```powershell
cd apps\web
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

## Tests

```powershell
.\scripts\test.ps1
```

Equivalent:

```powershell
python -m pytest -q -p no:cacheprovider
```

## Optional Docker API

```powershell
docker compose up --build
```

The Docker setup currently runs the API only. The frontend remains local through Vite.

## Repository Layout

```text
apps/
  api/                  FastAPI entry point
  web/                  React frontend

operia/
  core/                 Configuration, database, bootstrap, API router
  shared/               Reusable utilities
  identity/             Organizations, users, roles, auth
  cases/                Cases, technical data, findings, hypotheses
  evidence/             Evidence and chain of custody
  reports/              Reports, sections, versions, presentations
  exports/              Export manifests, hashes, PDF/JSON/CSV/Markdown
  legal_knowledge/      Argentine legal library
  legal_report/         Legal review and legacy compatibility workflows
  ai_assistant/         Ollama/Mistral assistant
  ai_security/          Model evaluation and risk scoring
  cybercrime/           Cybercrime intelligence workflows
  geo_trace/            IP/URL tracing and risk
  geo_proximity/        Location proximity workflows
  dashboard/            Global metrics
  settings/             Runtime settings
  audit/                Audit logs

docs/
  Architecture, modules, AI, security, testing and deployment notes

storage/
  Local runtime data, ignored by git except placeholders
```

## Important Notes

- Ollama is optional. If Ollama/Mistral is unavailable, the app continues working and records `ollama_unavailable`.
- Legal and AI outputs are assistive. They require human professional review.
- Legacy aliases are kept while the frontend and workflows complete migration to canonical APIs.
- The included SaaS security is a local foundation, not final production identity.

## Documentation

- [Matriz vigente de etapas y pendientes](docs/DELIVERY_STATUS.md)

- [E2: custodia append-only y rectificaciones versionadas](docs/CUSTODY_APPEND_ONLY.md)

- [Estado E0/E1: diagnóstico, respaldo y configuración segura](docs/E0_E1_SECURITY_BASELINE.md)
- [E4: base visual premium, permisos y validación](docs/FRONTEND_VISUAL_BASE.md)
- [E4: evidencias, formularios, informes y accesibilidad](docs/E4_EVIDENCE_REPORTS.md)
- [E4: módulos heredados y revisión de accesibilidad](docs/E4_LEGACY_MODULES.md)
- [Validación pendiente con tecnologías de asistencia reales](docs/ASSISTIVE_ACCESSIBILITY.md)
- [E5: laboratorio estático — importación pasiva, entrega parcial](docs/STATIC_LAB.md)
- [E5: CPython AST real, trabajos y revisión versionada](docs/STATIC_PROVIDER_JOBS.md)
- [E5: interfaz premium e incorporación a hallazgos e informes](docs/STATIC_LAB_INTERFACE.md)

- [Architecture](docs/ARCHITECTURE.md)
- [API Routes](docs/API_ROUTES.md)
- [Modules](docs/MODULES.md)
- [Legal Knowledge](docs/LEGAL_KNOWLEDGE.md)
- [AI Assistant](docs/AI_ASSISTANT.md)
- [AI Security](docs/AI_SECURITY.md)
- [Exports](docs/EXPORTS.md)
- [SaaS Readiness](docs/SAAS_READINESS.md)
- [Capas de seguridad y contrato de conectores](docs/SECURITY_LAYERS.md)
- [Auditoría de seguridad y dependencias](docs/SECURITY_AUDIT.md)
- [Pentest local y aislamiento Windows de workers/conectores](docs/LOCAL_PENTEST.md)
- [Pasarela segura para IA local](docs/LOCAL_AI_GATEWAY.md)
- [Testing](docs/TESTING.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Migration Notes](docs/MIGRATION_NOTES.md)
- [Forense móvil: piloto, diagnóstico y límites](docs/MOBILE_FORENSICS.md)
- [Motor móvil propio: arquitectura](docs/forensic_engine/ARCHITECTURE.md)
- [Motor móvil propio: operación y límites](docs/forensic_engine/OPERATOR_GUIDE.md)
- [E6: metadatos de backups iOS, motor 0.2.0](docs/forensic_engine/E6_BACKUP_METADATA.md)
- [E6: Manifest.db y catálogo SQLite acotados, motor 0.3.0](docs/forensic_engine/E6_MANIFEST_SQLITE.md)
- [E6: WAL/SHM sobre conjuntos preservados, motor 0.4.0](docs/forensic_engine/E6_WAL_SHM.md)
- [E6 actual: selección de archivos lógicos iOS, motor 0.5.0](docs/forensic_engine/E6_IOS_LOGICAL_FILES.md)

## Disclaimer

OPERIA Forensic Tracing is an assistive forensic and legal-technical platform. It does not replace expert human review, professional legal judgment, forensic validation, or proper chain-of-custody procedures.

