"""Add custody ledger and immutable SQLite events without rewriting history."""
from alembic import op
from operia.identity import models as identity_models  # noqa: F401 - resolve FK types in a clean process.
from operia.cases import models as case_models  # noqa: F401
from operia.evidence.models import CustodyLedgerEntry
from operia.evidence.custody import install_sqlite_protection

revision = "20261017_0006"
down_revision = "20261016_0005"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    CustodyLedgerEntry.__table__.create(connection, checkfirst=True)
    install_sqlite_protection(connection)


def downgrade():
    pass  # Keep ledger, protections and historical records; no destructive rollback.
