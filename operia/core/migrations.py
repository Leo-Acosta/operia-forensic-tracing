from sqlalchemy import inspect, text

from operia.core.config import settings
from operia.core.database import engine
from operia.shared.time import utcnow


CURRENT_SCHEMA_VERSION = "2026.05.28-operia-operational-hardening"


def ensure_migration_registry() -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY,
                    version VARCHAR(160) NOT NULL UNIQUE,
                    description TEXT DEFAULT '',
                    applied_at VARCHAR(80) NOT NULL
                )
                """
            )
        )


def record_schema_version(version: str = CURRENT_SCHEMA_VERSION, description: str = "") -> None:
    ensure_migration_registry()
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.execute(
                text(
                    """
                    INSERT OR IGNORE INTO schema_migrations (version, description, applied_at)
                    VALUES (:version, :description, :applied_at)
                    """
                ),
                {"version": version, "description": description, "applied_at": utcnow().isoformat()},
            )


def migration_status() -> dict[str, object]:
    ensure_migration_registry()
    inspector = inspect(engine)
    with engine.begin() as connection:
        rows = connection.execute(
            text("SELECT version, description, applied_at FROM schema_migrations ORDER BY id DESC")
        ).mappings().all()
    return {
        "database_url": settings.database_url,
        "dialect": engine.dialect.name,
        "current_schema_version": CURRENT_SCHEMA_VERSION,
        "registered": [dict(row) for row in rows],
        "tables": sorted(inspector.get_table_names()),
        "postgres_ready": not settings.database_url.startswith("sqlite"),
        "backup_recommendation": "Programar copia de storage/ y dump de base antes de uso productivo.",
    }
