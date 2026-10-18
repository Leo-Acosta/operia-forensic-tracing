"""Add static imports without rewriting existing tables or histories."""
from alembic import op
from operia.static_lab.models import StaticImport, install_protection
revision = '20261018_0008'
down_revision = '20261017_0007'
branch_labels = None
depends_on = None

def upgrade():
    connection = op.get_bind()
    StaticImport.__table__.create(connection, checkfirst=True)
    install_protection(connection)

def downgrade():
    pass  # Preserve imported forensic records; rollback application code instead.
