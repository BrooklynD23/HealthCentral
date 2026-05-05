"""Add assistant memory items table.

Revision ID: 005_memory_items
Revises: 004_document_categories
Create Date: 2026-05-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_memory_items"
down_revision: Union[str, None] = "004_document_categories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memory_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_memory_items_profile_id", "memory_items", ["profile_id"])
    op.create_index("ix_memory_items_key", "memory_items", ["key"])
    op.create_index("ix_memory_items_category", "memory_items", ["category"])


def downgrade() -> None:
    op.drop_index("ix_memory_items_category", table_name="memory_items")
    op.drop_index("ix_memory_items_key", table_name="memory_items")
    op.drop_index("ix_memory_items_profile_id", table_name="memory_items")
    op.drop_table("memory_items")
