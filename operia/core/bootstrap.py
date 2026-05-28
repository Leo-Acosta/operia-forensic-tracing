from sqlalchemy import inspect, text

from operia.core.database import Base, engine

# Import model modules so SQLAlchemy registers their tables before create_all.
from operia import ai_assistant, ai_security, audit, cases, evidence, exports, identity, legal_knowledge, reports  # noqa: F401
from operia.ai_assistant import models as ai_assistant_models  # noqa: F401
from operia.ai_security import models as ai_security_models  # noqa: F401
from operia.audit import models as audit_models  # noqa: F401
from operia.cases import models as case_models  # noqa: F401
from operia.evidence import models as evidence_models  # noqa: F401
from operia.exports import models as export_models  # noqa: F401
from operia.identity import models as identity_models  # noqa: F401
from operia.legal_knowledge import models as legal_knowledge_models  # noqa: F401
from operia.reports import models as report_models  # noqa: F401


SQLITE_PLATFORM_COLUMNS: dict[str, dict[str, str]] = {
    "users": {
        "organization_id": "INTEGER",
        "status": "VARCHAR(60) DEFAULT 'active'",
        "password_hash": "VARCHAR(255) DEFAULT ''",
        "failed_login_attempts": "INTEGER DEFAULT 0",
        "last_login_at": "VARCHAR(80) DEFAULT ''",
    },
    "cases": {"organization_id": "INTEGER"},
    "case_participants": {"organization_id": "INTEGER"},
    "technical_data": {"organization_id": "INTEGER"},
    "evidence": {"organization_id": "INTEGER"},
    "chain_of_custody_actions": {"organization_id": "INTEGER"},
    "findings": {"organization_id": "INTEGER"},
    "hypotheses": {"organization_id": "INTEGER"},
    "damage_items": {"organization_id": "INTEGER"},
    "damage_calculations": {"organization_id": "INTEGER"},
    "reports": {"organization_id": "INTEGER"},
    "report_sections": {"organization_id": "INTEGER"},
    "report_versions": {"organization_id": "INTEGER"},
    "report_reviews": {"organization_id": "INTEGER"},
    "templates": {"organization_id": "INTEGER"},
    "attachments": {"organization_id": "INTEGER"},
    "presentations": {"organization_id": "INTEGER"},
    "presentation_slides": {"organization_id": "INTEGER"},
    "presentation_versions": {"organization_id": "INTEGER"},
    "presentation_reviews": {"organization_id": "INTEGER"},
    "presentation_fragments": {"organization_id": "INTEGER"},
    "legal_sources": {"organization_id": "INTEGER"},
    "legal_mappings": {
        "organization_id": "INTEGER",
        "article_id": "INTEGER",
        "confidence_level": "VARCHAR(40) DEFAULT 'medio'",
        "requires_human_review": "BOOLEAN DEFAULT 1",
    },
}


def init_platform_schema() -> None:
    """Create tables and add additive SQLite columns needed by the modular platform."""
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table_name, columns in SQLITE_PLATFORM_COLUMNS.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl in columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))
