"""Immutable static observations incorporated into findings and report snapshots."""
from alembic import op
from operia.static_lab.models import StaticProjection,install_projection_protection
revision='20261018_0010'
down_revision='20261018_0009'
branch_labels=None
depends_on=None

def upgrade():
    connection=op.get_bind()
    StaticProjection.__table__.create(connection,checkfirst=True)
    install_projection_protection(connection)

def downgrade():
    pass  # Retain derived findings/reports and their provenance.
