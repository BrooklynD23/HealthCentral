"""Add user-curated pinboards.

Revision ID: 012_pinboards
Revises: 011_care_plan_tasks
Create Date: 2026-07-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012_pinboards"
down_revision: Union[str, None] = "011_care_plan_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pinboard",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_table(
        "pinboard_item",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "pinboard_id", sa.Text(),
            sa.ForeignKey("pinboard.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("item_type", sa.Text(), nullable=False),
        sa.Column("item_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("pinboard_id", "item_type", "item_id", name="uq_pinboard_item_target"),
    )
    op.create_index("idx_pinboard_item_pinboard", "pinboard_item", ["pinboard_id"])
    op.create_index("idx_pinboard_item_target", "pinboard_item", ["item_type", "item_id"])


def downgrade() -> None:
    op.drop_index("idx_pinboard_item_target")
    op.drop_index("idx_pinboard_item_pinboard")
    op.drop_table("pinboard_item")
    op.drop_table("pinboard")
