"""Add chat_sessions, chat_turns tables and assistant_memory_enabled column.

Revision ID: 007_chat_sessions
Revises: 006_ocr_preference
Create Date: 2026-06-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007_chat_sessions"
down_revision: Union[str, None] = "006_ocr_preference"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- chat_sessions table ---
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_chat_sessions_profile_id", "chat_sessions", ["profile_id"])

    # --- chat_turns table ---
    op.create_table(
        "chat_turns",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=36),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_chat_turns_session_id", "chat_turns", ["session_id"])
    op.create_index("ix_chat_turns_profile_id", "chat_turns", ["profile_id"])

    # --- assistant_memory_enabled column on user_model_settings ---
    # Use batch_alter_table for SQLite ALTER TABLE compatibility
    with op.batch_alter_table("user_model_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "assistant_memory_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("user_model_settings") as batch_op:
        batch_op.drop_column("assistant_memory_enabled")

    op.drop_index("ix_chat_turns_profile_id", table_name="chat_turns")
    op.drop_index("ix_chat_turns_session_id", table_name="chat_turns")
    op.drop_table("chat_turns")

    op.drop_index("ix_chat_sessions_profile_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
