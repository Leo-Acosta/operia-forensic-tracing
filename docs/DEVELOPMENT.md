# Development Guide

## Backend

Run the API:

```powershell
cd new_unified_app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8020
```

Health check:

```text
GET /api/health
```

API docs:

```text
http://127.0.0.1:8020/docs
```

## Frontend

Run the web app:

```powershell
cd new_unified_app\apps\web
npm install
npm run dev
```

Default API base:

```text
http://127.0.0.1:8020/api
```

## Current Smoke Test Targets

Useful endpoints:

```text
GET  /api/dashboard
GET  /api/legal-report
GET  /api/cybercrime
GET  /api/geo-trace
GET  /api/geo-proximity
POST /api/geo-trace/analyze
GET  /api/geo-proximity/nearest
```

## Local Storage

Generated local artifacts are stored in:

```text
storage/evidence
storage/uploads
storage/exports
storage/maps
storage/temp
```

These are development artifacts and should not be treated as production evidence storage.

