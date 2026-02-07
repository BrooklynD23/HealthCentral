"""Add external API settings to user_model_settings.

Revision ID: 002_external_api
Revises: 001_initial
Create Date: 2026-02-07

Phase 2E: External API Backend (opt-in)
Adds columns for external API provider configuration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_external_api"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_model_settings",
        sa.Column("use_external_api", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_model_settings",
        sa.Column("external_api_provider", sa.String(50), nullable=False, server_default=""),
    )
    op.add_column(
        "user_model_settings",
        sa.Column("external_api_key_encrypted", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("user_model_settings", "external_api_key_encrypted")
    op.drop_column("user_model_settings", "external_api_provider")
    op.drop_column("user_model_settings", "use_external_api")
