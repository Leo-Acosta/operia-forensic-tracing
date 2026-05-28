from fastapi import APIRouter

from operia.core.config import settings
from operia.core.migrations import migration_status

router = APIRouter()


@router.get("/")
def read_settings() -> dict[str, object]:
    return {
        "app_name": settings.app_name,
        "env": settings.env,
        "api_prefix": settings.api_prefix,
        "storage_dir": str(settings.storage_dir),
        "database_url": settings.database_url,
    }


@router.get("/readiness")
def readiness() -> dict[str, object]:
    migrations = migration_status()
    return {
        "database": {
            "dialect": migrations["dialect"],
            "schema_version": migrations["current_schema_version"],
            "migrations": migrations["registered"],
            "postgres_ready": migrations["postgres_ready"],
        },
        "storage": {
            "root": str(settings.storage_dir),
            "evidence": str(settings.evidence_dir),
            "uploads": str(settings.uploads_dir),
            "exports": str(settings.exports_dir),
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
