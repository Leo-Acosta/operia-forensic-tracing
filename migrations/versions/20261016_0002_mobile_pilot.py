"""Add mobile preservation tables without modifying existing case/evidence data."""
from alembic import op
from operia.mobile_forensics.models import MobileDevice, MobileExam, MobileReview, MobileExport

revision = "20261016_0002"
down_revision = "20260528_0001"
branch_labels = None
depends_on = None


def upgrade():
    # Existing installations may already have tables from development bootstrap.
    for model in (MobileDevice, MobileExam, MobileReview, MobileExport):
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    # Deliberately non-destructive: code rollback retains preserved originals and
    # reviews. Restore a verified pre-upgrade backup for a full schema rollback.
    pass
