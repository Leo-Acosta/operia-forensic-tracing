"""Add isolated static jobs and immutable review versions."""
from alembic import op
from operia.static_lab.models import StaticJob, StaticReview, StaticJobEvent, install_job_protection
revision = '20261018_0009'
down_revision = '20261018_0008'
branch_labels = None
depends_on = None

def upgrade():
    connection = op.get_bind()
    for model in (StaticJob,StaticReview,StaticJobEvent):
        model.__table__.create(connection,checkfirst=True)
    install_job_protection(connection)

def downgrade():
    pass  # Preserve all forensic results and review history.
