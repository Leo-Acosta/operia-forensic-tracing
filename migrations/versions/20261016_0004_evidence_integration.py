"""Add links without rewriting historical records."""
from alembic import op
from operia.forensic_jobs.models import EvidenceIntegration
revision = "20261016_0004"
down_revision = "20261016_0003"
branch_labels = None
depends_on = None

def upgrade():
    EvidenceIntegration.__table__.create(op.get_bind(), checkfirst=True)

def downgrade():
    pass  # Preservation is intentional.
