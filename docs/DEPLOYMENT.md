# Deployment

This document describes local deployment options for OPERIA Forensic Tracing.

## Local Windows Setup

Run once:

```powershell
.\scripts\setup.ps1
```

Start the API:

```powershell
.\scripts\start-api.ps1
```

Start the frontend:

```powershell
.\scripts\start-web.ps1
```

Open:

- `http://127.0.0.1:5173`
- `http://127.0.0.1:8020/docs`

## Environment

Copy `.env.example` to `.env` if you need custom settings.

Important variables:

- `OPERIA_APP_NAME`
- `OPERIA_ENV`
- `OPERIA_API_PREFIX`
- `OPERIA_DATABASE_URL`
- `OPERIA_STORAGE_DIR`
- `OPERIA_CORS_ORIGINS`
- `OPERIA_OLLAMA_BASE_URL`
- `OPERIA_DEFAULT_AI_MODEL`
- `VITE_API_BASE`

## Ollama

Ollama is optional.

Network access is disabled by default. Local AI now requires
`OPERIA_LOCAL_AI_ENABLED=true`, an explicit `local_ai` organization grant and
`ai:use`. Public connectors require both a server host allowlist and an organization
purpose grant. See [security audit and operator settings](SECURITY_AUDIT.md).
Back up the persistent `storage/.auth-signing-key` with storage and protect it
with host ACLs; database-only backups do not include this signing key.

Expected local endpoint:

```text
http://127.0.0.1:11434
```

Default model:

```text
mistral
```

If Ollama is unavailable, OPERIA continues working and AI endpoints return an unavailable status instead of crashing.

## Docker API

Build and run the API:

```powershell
docker compose up --build
```

API:

```text
http://127.0.0.1:8020
```

Notes:

- Docker currently runs the API only.
- SQLite data is stored in the mounted `storage` directory.
- The frontend is still best run locally with Vite during this stage.

## Production Hardening Checklist

Before any real SaaS deployment:

- replace SQLite with PostgreSQL;
- use Alembic migrations;
- configure a real secret key;
- force authentication on all write routes;
- add HTTPS;
- add password policy and reset flow;
- add MFA;
- add per-case ACLs;
- add structured logging;
- add backup and restore procedures;
- add signed export manifests;
- add monitoring.

