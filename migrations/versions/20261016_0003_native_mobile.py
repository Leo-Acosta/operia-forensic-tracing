"""Add independent native engine records; historical results remain untouched."""
from alembic import op
from operia.forensic_jobs.models import Acquisition, IndicatorSet, ExaminationJob, JobEvent, ReviewRevision, ExportRecord

revision = "20261016_0003"
down_revision = "20261016_0002"
branch_labels = None
depends_on = None


def upgrade():
    for model in (Acquisition, IndicatorSet, ExaminationJob, JobEvent, ReviewRevision, ExportRecord):
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    # Reverting code must not destroy preserved originals, outputs or reviews.
    pass
