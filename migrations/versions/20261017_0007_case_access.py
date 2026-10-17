"""Add explicit, append-only case permissions without granting legacy access."""
from alembic import op
from operia.identity import models as identity_models  # noqa: F401
from operia.cases import models as case_models  # noqa: F401
from operia.identity.case_access import CaseAccessEvent, install_protection

revision = "20261017_0007"
down_revision = "20261017_0006"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    CaseAccessEvent.__table__.create(connection, checkfirst=True)
    install_protection(connection)


def downgrade():
    pass  # Preserve authorization history and protections.
