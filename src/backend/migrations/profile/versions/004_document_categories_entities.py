"""Add document_category and document_entity tables.

Revision ID: 004_document_categories
Revises: 003_gamification_voice
Create Date: 2026-03-04

INGEST-EPIC-001 Phase A: Schema for document classification and entity extraction.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_document_categories"
down_revision: Union[str, None] = "003_gamification_voice"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_category",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("doc_id", sa.Text(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("classified_by", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("idx_doc_category_doc_id", "document_category", ["doc_id"])

    op.create_table(
        "document_entity",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("doc_id", sa.Text(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_bbox_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("idx_doc_entity_doc_id", "document_entity", ["doc_id"])
    op.create_index("idx_doc_entity_type", "document_entity", ["entity_type"])


def downgrade() -> None:
    op.drop_index("idx_doc_entity_type")
    op.drop_index("idx_doc_entity_doc_id")
    op.drop_table("document_entity")
    op.drop_index("idx_doc_category_doc_id")
    op.drop_table("document_category")
