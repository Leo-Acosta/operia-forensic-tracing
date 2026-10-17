import logging

from fastapi import APIRouter, Depends, HTTPException

from operia.core.config import settings
from operia.core.migrations import migration_status
from operia.identity.dependencies import require_permission

router = APIRouter(dependencies=[Depends(require_permission("settings:read"))])


@router.get("/")
def read_settings() -> dict[str, object]:
    return {
        "app_name": settings.app_name,
        "env": settings.env,
        "api_prefix": settings.api_prefix,
    }


@router.get("/readiness")
def readiness() -> dict[str, object]:
    try:
        migrations = migration_status()
    except Exception:
        # Driver messages can contain credentials, SQL and host paths.
        logging.getLogger("operia.security").warning("settings_readiness_unavailable")
        raise HTTPException(503, "settings_readiness_unavailable") from None
    return {
        "database": {
            "dialect": migrations["dialect"],
            "schema_version": migrations["current_schema_version"],
            "alembic_heads": migrations["alembic_heads"],
            "alembic_available": migrations["alembic_available"],
            "registered_migration_count": len(migrations["registered"]),
            "postgres_ready": migrations["postgres_ready"],
        },
        "storage": {
            "mode": "managed_local_storage",
        },
        "saas_readiness": {
            "organizations": True,
            "users": True,
            "roles": True,
            "audit_logs": True,
            "case_permissions": "base",
            "database_migrations": True,
        },
        "recommendations": [
            "Configurar PostgreSQL para produccion.",
            "Activar backups programados de base de datos y storage.",
            "Usar usuarios nominales antes de emitir informes finales.",
        ],
    }
