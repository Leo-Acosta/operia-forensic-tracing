from sqlalchemy import inspect, text

from operia.core.database import Base, engine
from operia.core.migrations import record_schema_version

# Import model modules so SQLAlchemy registers their tables before create_all.
from operia import ai_assistant, ai_security, audit, cases, cybercrime, evidence, exports, identity, legal_knowledge, reports, rubrics  # noqa: F401
from operia.ai_assistant import models as ai_assistant_models  # noqa: F401
from operia.ai_security import models as ai_security_models  # noqa: F401
from operia.audit import models as audit_models  # noqa: F401
from operia.cases import models as case_models  # noqa: F401
from operia.cybercrime import models as cybercrime_models  # noqa: F401
from operia.evidence import models as evidence_models  # noqa: F401
from operia.exports import models as export_models  # noqa: F401
from operia.identity import models as identity_models  # noqa: F401
from operia.legal_knowledge import models as legal_knowledge_models  # noqa: F401
from operia.reports import models as report_models  # noqa: F401
from operia.rubrics import models as rubric_models  # noqa: F401


SQLITE_PLATFORM_COLUMNS: dict[str, dict[str, str]] = {
    "users": {
        "organization_id": "INTEGER",
        "status": "VARCHAR(60) DEFAULT 'active'",
        "title": "VARCHAR(160) DEFAULT ''",
        "agency": "VARCHAR(180) DEFAULT ''",
        "registration_id": "VARCHAR(120) DEFAULT ''",
        "phone": "VARCHAR(80) DEFAULT ''",
        "signature": "TEXT DEFAULT ''",
        "profile_notes": "TEXT DEFAULT ''",
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
        "decision_status": "VARCHAR(80) DEFAULT 'sugerido'",
        "analyst_name": "VARCHAR(160) DEFAULT ''",
        "analyst_rationale": "TEXT DEFAULT ''",
        "legal_role": "VARCHAR(80) DEFAULT ''",
        "applicability_to_case": "TEXT DEFAULT ''",
        "probatory_limits": "TEXT DEFAULT ''",
        "decided_at": "VARCHAR(80) DEFAULT ''",
    },
    "legal_mapping_evidence": {
        "organization_id": "INTEGER",
        "element_status": "VARCHAR(80) DEFAULT 'pendiente'",
        "missing_evidence": "TEXT DEFAULT ''",
        "contradiction_risk": "VARCHAR(80) DEFAULT 'bajo'",
        "recommended_measure": "TEXT DEFAULT ''",
    },
    "rubric_evaluations": {"organization_id": "INTEGER"},
    "cybercrime_deepfake_analyses": {
        "finding_id": "INTEGER",
        "source_origin": "TEXT DEFAULT ''",
        "evidence_hash": "VARCHAR(128) DEFAULT ''",
        "tool_used": "VARCHAR(255) DEFAULT ''",
        "findings": "TEXT DEFAULT ''",
        "limitations": "TEXT DEFAULT ''",
        "legal_relevance": "TEXT DEFAULT ''",
        "legal_mapping_ids": "VARCHAR(255) DEFAULT ''",
        "analyst_name": "VARCHAR(160) DEFAULT ''",
    },
    "cybercrime_blockchain_transactions": {
        "evidence_id": "INTEGER",
        "finding_id": "INTEGER",
        "wallet_classification": "VARCHAR(120) DEFAULT 'desconocido'",
        "evidence_hash": "VARCHAR(128) DEFAULT ''",
        "tool_used": "VARCHAR(255) DEFAULT ''",
        "limitations": "TEXT DEFAULT ''",
        "recommended_measures": "TEXT DEFAULT ''",
        "legal_mapping_ids": "VARCHAR(255) DEFAULT ''",
        "analyst_name": "VARCHAR(160) DEFAULT ''",
        "route_order": "INTEGER DEFAULT 0",
        "include_in_report": "BOOLEAN DEFAULT 1",
        "preservation_checklist": "TEXT DEFAULT ''",
        "warning": "TEXT DEFAULT 'Una wallet no identifica por si sola a una persona sin evidencia externa corroborante.'",
    },
    "cybercrime_iot_devices": {
        "evidence_id": "INTEGER",
        "finding_id": "INTEGER",
        "logs_available": "TEXT DEFAULT ''",
        "evidence_hash": "VARCHAR(128) DEFAULT ''",
        "tool_used": "VARCHAR(255) DEFAULT ''",
        "limitations": "TEXT DEFAULT ''",
        "recommended_measures": "TEXT DEFAULT ''",
        "legal_mapping_ids": "VARCHAR(255) DEFAULT ''",
        "analyst_name": "VARCHAR(160) DEFAULT ''",
        "warning": "TEXT DEFAULT 'No ejecutar escaneos ni modificar el dispositivo sin autorizacion, resguardo de estado y metodologia documentada.'",
    },
}


def init_platform_schema() -> None:
    """Create tables and add additive SQLite columns needed by the modular platform."""
    Base.metadata.create_all(bind=engine)
    record_schema_version(description="Esquema modular OPERIA con controles operativos base.")
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
