"""Allow uploaded documents to exist before identity resolution."""

from alembic import op
import sqlalchemy as sa

revision = "0003_nullable_document_candidate"
down_revision = "0002_document_extraction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "candidate_documents",
        "candidate_id",
        existing_type=sa.String(length=40),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "candidate_documents",
        "candidate_id",
        existing_type=sa.String(length=40),
        existing_nullable=True,
        nullable=False,
    )