from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from operia.core.config import settings
from operia.core.database import Base

# Import all model modules so Alembic sees the whole schema.
from operia.ai_assistant import models as ai_assistant_models  # noqa: F401
from operia.ai_security import models as ai_security_models  # noqa: F401
from operia.audit import models as audit_models  # noqa: F401
from operia.cases import models as case_models  # noqa: F401
from operia.cybercrime import models as cybercrime_models  # noqa: F401
from operia.evidence import models as evidence_models  # noqa: F401
from operia.exports import models as export_models  # noqa: F401
from operia.geo_proximity import models as geo_proximity_models  # noqa: F401
from operia.geo_trace import models as geo_trace_models  # noqa: F401
from operia.identity import models as identity_models  # noqa: F401
from operia.legal_knowledge import models as legal_knowledge_models  # noqa: F401
from operia.reports import models as report_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.database_url
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
