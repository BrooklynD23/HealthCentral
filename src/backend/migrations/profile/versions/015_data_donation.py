"""Add donation_consents and donated_records (opt-in data donation, PR-1).

RSI1-DONATE: consent record plus the redacted-only donated set. There is no
raw-text column and no foreign key (source_id is an opaque reference).

Revision ID: 015_data_donation
Revises: 014_streaks_hidden
Create Date: 2026-10-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "015_data_donation"
down_revision: Union[str, None] = "014_streaks_hidden"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "donation_consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("consent_text_version", sa.String(64), nullable=False),
    )
    op.create_index("ix_donation_consents_profile_id", "donation_consents", ["profile_id"])
    op.create_index("ix_donation_consents_purpose", "donation_consents", ["purpose"])

    op.create_table(
        "donated_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.Column("source_kind", sa.String(32), nullable=False),
        sa.Column("source_id", sa.String(64), nullable=True),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("prompt_redacted", sa.Text(), nullable=False),
        sa.Column("response_redacted", sa.Text(), nullable=False),
        sa.Column("strict_redaction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_donated_records_profile_id", "donated_records", ["profile_id"])
    op.create_index("ix_donated_records_purpose", "donated_records", ["purpose"])
    op.create_index("ix_donated_records_parent_id", "donated_records", ["parent_id"])


def downgrade() -> None:
    op.drop_table("donated_records")
    op.drop_table("donation_consents")
