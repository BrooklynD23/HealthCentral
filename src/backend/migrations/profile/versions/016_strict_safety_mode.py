"""Add strict_safety_mode column to user_model_settings (default off).

SAFETY-MODE-SETTING: per-profile opt-in to the stricter safety mode. The
server default keeps every existing profile off.

Revision ID: 016_strict_safety_mode
Revises: 015_data_donation
Create Date: 2026-10-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "016_strict_safety_mode"
down_revision: Union[str, None] = "015_data_donation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_model_settings",
        sa.Column(
            "strict_safety_mode",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_model_settings", "strict_safety_mode")
