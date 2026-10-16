"""Preserved references from reviewed engine artifacts to case analysis."""
from alembic import op
from operia.forensic_jobs.models import AnalysisProjection
revision = "20261016_0005"
down_revision = "20261016_0004"
branch_labels = None
depends_on = None

def upgrade():
    AnalysisProjection.__table__.create(op.get_bind(), checkfirst=True)

def downgrade():
    pass  # Preserve projections and all historical records.
