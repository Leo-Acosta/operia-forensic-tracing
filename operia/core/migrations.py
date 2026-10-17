from pathlib import Path

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
    inspector = inspect(engine)
    rows = []
    if inspector.has_table("schema_migrations"):
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT version, description, applied_at FROM schema_migrations ORDER BY id DESC")
            ).mappings().all()
    heads = _migration_heads_from_files()
    alembic_available = _alembic_is_available()
    return {
        "dialect": engine.dialect.name,
        "current_schema_version": CURRENT_SCHEMA_VERSION,
        "alembic_heads": heads,
        "alembic_available": alembic_available,
        "registered": [dict(row) for row in rows],
        "tables": sorted(inspector.get_table_names()),
        "postgres_ready": not settings.database_url.startswith("sqlite"),
        "backup_recommendation": "Programar copia de storage/ y dump de base antes de uso productivo.",
    }


def _migration_heads_from_files() -> list[str]:
    versions_dir = Path("migrations") / "versions"
    if not versions_dir.exists():
        return []
    heads: list[str] = []
    for path in versions_dir.glob("*.py"):
        text_content = path.read_text(encoding="utf-8")
        for line in text_content.splitlines():
            if line.startswith("revision = "):
                heads.append(line.split("=", 1)[1].strip().strip('"').strip("'"))
                break
    return sorted(heads)


def _alembic_is_available() -> bool:
    try:
        import alembic  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True
