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

Actualización E7, 2026-10-19: consultar [controles implementados, operación y
pendientes](E7_PRODUCTION_HARDENING.md). El perfil Docker es local: Compose valida,
pero build/runtime no se probaron porque el daemon no está disponible. No aporta
aislamiento Linux equivalente al backend Windows.

Para el perfil Windows, usar `.env.production.example` como referencia sin claves
inline, una clave binaria externa de 32 bytes con ACL privada y una identidad
dedicada sin Administradores. `scripts/production_audit.py` rechaza configuración
insegura; `scripts/start-api-production.ps1` audita antes de iniciar. Esto no
provisiona TLS, identidad ni servicio. La cuenta actual no cumple la política.

El respaldo cifrado y su restauración a staging se operan mediante
`scripts/recovery_bundle.py` según la guía E7. Requiere escritores detenidos y
DPAPI del usuario: no sustituye copia independiente, escrow y ensayo de desastre.
`scripts/sqlite_backup.py` continúa siendo una utilidad SQLite en claro, no un
respaldo completo cifrado del expediente.

Continuación E7: [OperiaSvc y ACL de solo lectura](E7_SERVICE_ACCOUNT.md) ya se
prepararon y probaron sobre copia nueva con datos sintéticos. La cuenta queda
deshabilitada; no representa una instalación del servicio ni un runtime listo.

Tramo posterior: [runtime independiente y arranque bajo OperiaSvc](E7_SERVICE_RUNTIME.md)
validados en ProgramData con datos sintéticos y árboles RX. La cuenta termina
deshabilitada; la aplicación habitual conserva su configuración y datos.
Faltan ciclo de servicio, credencial/configuración/claves efectivas, TLS y
recuperación independiente antes de aceptar producción.

Lista histórica de requisitos; permisos por expediente y procedimientos locales
ya tienen implementaciones documentadas, pendientes de aceptación productiva.
Antes de cualquier despliegue real del SaaS:

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



## Aislamiento Windows y pentest local

Ejecutar `python scripts/prepare_worker_sandbox.py` desde la raiz antes de
trabajos nuevos y despues de actualizar el runtime. AppContainer/Job son
obligatorios, sin fallback a ejecucion normal. La IA directa a localhost queda
bloqueada hasta disponer de pasarela separada; no agregar excepciones de loopback.
Ver [operacion, resultados y limites](LOCAL_PENTEST.md).

El Docker API Linux existente no proporciona este backend Windows. Los trabajos
y conectores que requieran contencion se rechazan en esa plataforma; se necesita
un backend de aislamiento Linux validado antes de habilitarlos alli.


Actualizacion 2026-10-17: la [pasarela de IA local](LOCAL_AI_GATEWAY.md) ya esta
implementada, deshabilitada por defecto. Requiere preparacion del runtime, dos
flags globales, modelo concedido por organizacion y caso autorizado. Los workers
siguen sin loopback. La guia describe el servicio Ollama confiable y sus limites.
