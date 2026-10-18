"""Add streaks_hidden column to user_model_settings (default off).

C-GAM2B: per-profile opt-out of streak displays. Badges are unaffected.

Revision ID: 014_streaks_hidden
Revises: 013_adaptive_windows_local
Create Date: 2026-10-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "014_streaks_hidden"
down_revision: Union[str, None] = "013_adaptive_windows_local"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_model_settings",
        sa.Column(
            "streaks_hidden",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_model_settings", "streaks_hidden")
