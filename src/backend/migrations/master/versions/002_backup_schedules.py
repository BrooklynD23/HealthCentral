"""Per-profile backup schedules (BKUP-UX-001).

Revision ID: 002_backup_schedules
Revises: 001_initial
Create Date: 2026-07-28

Lives in the MASTER chain, not the profile chain, on purpose: the background
scheduler must be able to see that a backup is due while the profile vault is
still locked, and anything inside the vault is unreadable until unlock.

The master DB is unencrypted, so every column here is an id, an enum, a count
or a timestamp — no health data, no display names, no free text.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_backup_schedules"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backup_schedules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "profile_id",
            sa.String(36),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("frequency", sa.String(16), nullable=False, server_default="off"),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_result", sa.String(24), nullable=False, server_default="never_run"),
        sa.Column("last_file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )
    op.create_index(
        "ix_backup_schedules_profile_id", "backup_schedules", ["profile_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_backup_schedules_profile_id", table_name="backup_schedules")
    op.drop_table("backup_schedules")
