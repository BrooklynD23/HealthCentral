"""Add source-span and verification columns to document_entity.

Revision ID: 010_entity_source_spans
Revises: 009_agent_enabled
Create Date: 2026-07-10

HC-M12: Every extracted entity carries a verbatim source span
(char_start/char_end/quote), a user verification state
(null = unreviewed, true = verified, false = rejected), and the
extraction ruleset version that produced it. Additive columns only.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "010_entity_source_spans"
down_revision: Union[str, None] = "009_agent_enabled"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document_entity", sa.Column("char_start", sa.Integer(), nullable=True))
    op.add_column("document_entity", sa.Column("char_end", sa.Integer(), nullable=True))
    op.add_column("document_entity", sa.Column("quote", sa.Text(), nullable=True))
    op.add_column("document_entity", sa.Column("verified_by_user", sa.Boolean(), nullable=True))
    op.add_column("document_entity", sa.Column("extraction_version", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_entity", "extraction_version")
    op.drop_column("document_entity", "verified_by_user")
    op.drop_column("document_entity", "quote")
    op.drop_column("document_entity", "char_end")
    op.drop_column("document_entity", "char_start")
