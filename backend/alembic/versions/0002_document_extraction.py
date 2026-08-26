"""Add document extraction metadata and nullable candidate identity."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0002_document_extraction"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    document_columns = {column["name"] for column in inspect(connection).get_columns("candidate_documents")}
    for name, column_type in (("uploaded_at", sa.DateTime()), ("extraction_method", sa.String(40)), ("extraction_quality", sa.Float()), ("extracted_character_count", sa.Integer()), ("extracted_word_count", sa.Integer()), ("extraction_error", sa.Text()), ("extracted_text", sa.Text())):
        if name not in document_columns:
            op.add_column("candidate_documents", sa.Column(name, column_type, nullable=True))
    if not inspect(connection).has_table("candidate_update_proposals"):
        op.create_table("candidate_update_proposals", sa.Column("id", sa.String(40), primary_key=True), sa.Column("document_id", sa.String(40), sa.ForeignKey("candidate_documents.id"), nullable=False), sa.Column("candidate_id", sa.String(40), sa.ForeignKey("candidates.id"), nullable=True), sa.Column("status", sa.String(40), nullable=False, server_default="pending"), sa.Column("confidence", sa.Float(), nullable=False, server_default="0"), sa.Column("changes", sa.Text(), nullable=False, server_default="[]"), sa.Column("created_at", sa.DateTime(), nullable=True))
        op.create_index("ix_candidate_update_proposals_document_id", "candidate_update_proposals", ["document_id"])
        op.create_index("ix_candidate_update_proposals_candidate_id", "candidate_update_proposals", ["candidate_id"])


def downgrade() -> None:
    connection = op.get_bind()
    if inspect(connection).has_table("candidate_update_proposals"):
        op.drop_index("ix_candidate_update_proposals_candidate_id", table_name="candidate_update_proposals")
        op.drop_index("ix_candidate_update_proposals_document_id", table_name="candidate_update_proposals")
        op.drop_table("candidate_update_proposals")
    for name in ("extracted_text", "extraction_error", "extracted_word_count", "extracted_character_count", "extraction_quality", "extraction_method", "uploaded_at"):
        if name in {column["name"] for column in inspect(connection).get_columns("candidate_documents")}: op.drop_column("candidate_documents", name)