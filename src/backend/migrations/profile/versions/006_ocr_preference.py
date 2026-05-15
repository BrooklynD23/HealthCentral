"""Add per-profile OCR preference (default on).

Revision ID: 006_ocr_preference
Revises: 005_memory_items
Create Date: 2026-05-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006_ocr_preference"
down_revision: Union[str, None] = "005_memory_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_model_settings",
        sa.Column(
            "ocr_preference_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_model_settings", "ocr_preference_enabled")
