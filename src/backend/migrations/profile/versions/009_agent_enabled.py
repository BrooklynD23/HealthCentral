"""Add agent_enabled column to user_model_settings (default on).

Agent Overhaul S5-1: persists the agent_enabled flag so /assistant/chat can
read a real settings value instead of always falling through to the
in-code default (resolves RECONCILIATION R-8). Default True matches the
S5 cutover's AGENT_ENABLED_DEFAULT.

Revision ID: 009_agent_enabled
Revises: 008_response_feedback
Create Date: 2026-06-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009_agent_enabled"
down_revision: Union[str, None] = "008_response_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_model_settings",
        sa.Column(
            "agent_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_model_settings", "agent_enabled")
