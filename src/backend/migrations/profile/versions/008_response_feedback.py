"""Add response_feedback table for RL preference dataset pipeline.

Revision ID: 008_response_feedback
Revises: 007_chat_sessions
Create Date: 2026-06-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008_response_feedback"
down_revision: Union[str, None] = "007_chat_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "response_feedback",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("turn_id", sa.String(length=36), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("correction_text", sa.Text(), nullable=True),
        sa.Column("feedback_tags", sa.JSON(), nullable=True),
        sa.Column("prompt_snapshot", sa.Text(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_response_feedback_profile_id", "response_feedback", ["profile_id"])
    op.create_index("ix_response_feedback_session_id", "response_feedback", ["session_id"])
    op.create_index("ix_response_feedback_turn_id", "response_feedback", ["turn_id"])
    # Unique constraint: one feedback row per (profile_id, turn_id)
    op.create_index(
        "uq_response_feedback_profile_turn",
        "response_feedback",
        ["profile_id", "turn_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_response_feedback_profile_turn", table_name="response_feedback")
    op.drop_index("ix_response_feedback_turn_id", table_name="response_feedback")
    op.drop_index("ix_response_feedback_session_id", table_name="response_feedback")
    op.drop_index("ix_response_feedback_profile_id", table_name="response_feedback")
    op.drop_table("response_feedback")
