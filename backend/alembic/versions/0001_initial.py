"""Initial candidate schema."""

from alembic import op
from sqlalchemy import MetaData

from app.db import Base
from app import models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(op.get_bind())


def downgrade() -> None:
    metadata = MetaData()
    metadata.reflect(bind=op.get_bind())
    for table in reversed(metadata.sorted_tables):
        table.drop(op.get_bind())