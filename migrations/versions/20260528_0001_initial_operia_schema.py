"""initial operia schema baseline

Revision ID: 20260528_0001
Revises:
Create Date: 2026-05-28
"""
from alembic import op

revision = "20260528_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The current development database is created by SQLAlchemy bootstrap.
    # This baseline lets Alembic own the schema history from this point forward.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY,
            version VARCHAR(160) NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            applied_at VARCHAR(80) NOT NULL
        )
        """
    )


def downgrade() -> None:
    # Keep the application tables intact; this baseline is non-destructive.
    pass
