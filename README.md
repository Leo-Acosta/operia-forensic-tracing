# OPERIA Forensic Tracing

OPERIA Forensic Tracing is a modular forensic investigation platform that unifies cybercrime intelligence, legal-forensic reporting, geolocation tracing, evidence workflows, dashboards, and export pipelines into one professional application.

The project is currently in migration/refactor phase. Legacy backend logic from the original OPERIA prototypes has started to move into a single FastAPI + React architecture.

## Current Status

Migrated backend modules:

- Forensic Legal Report
- Cybercrime Intelligence Analyst
- Geo Trace
- Geo Proximity

Platform foundation:

- FastAPI backend
- React + TypeScript frontend shell
- Shared SQLite database for local development
- Shared configuration system
- Shared storage layout
- Shared PDF export pipeline
- Shared dashboard metrics

Still pending:

- Canonical domain refactor for cases, evidence, reports, exports, identity, and audit
- Full frontend migration for each module
- Authentication and authorization
- Alembic migrations
- SaaS/multi-tenant model
- Production hardening

## Quick Start

Backend:

```powershell
cd new_unified_app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8020
```

Frontend:

```powershell
cd new_unified_app\apps\web
npm install
npm run dev
```

API docs:

- `http://127.0.0.1:8020/docs`
- `http://127.0.0.1:8020/api/health`

## Repository Layout

```text
apps/
  api/                  FastAPI entry point
  web/                  React frontend shell

operia/
  core/                 Configuration, database, API router
  shared/               Reusable services
  legal_report/         Forensic Legal Report module
  cybercrime/           Cybercrime Intelligence module
  geo_trace/            IP/URL geolocation and risk tracing
  geo_proximity/        Nearest-location/proximity module
  dashboard/            Global metrics
  settings/             Runtime settings API
  evidence/             Placeholder for canonical evidence module
  reports/              Placeholder for canonical reports module
  exports/              Placeholder for canonical exports module
  users_cases/          Placeholder for canonical users/cases module

storage/
  evidence/
  uploads/
  exports/
  maps/
  temp/
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Migration Plan](docs/MIGRATION_PLAN.md)
- [Modules](docs/MODULES.md)
- [Roadmap](docs/ROADMAP.md)
- [Development Guide](docs/DEVELOPMENT.md)

## Professional Disclaimer

OPERIA Forensic Tracing is an assistive forensic and legal-technical platform. It does not replace expert human review, professional legal judgment, forensic validation, or proper chain-of-custody procedures.

