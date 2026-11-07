"""Persist downloadable export artifacts in the profile vault (G-C1, PRIV-08).

Adds ``export_artifact``: one row per generated doctor summary, visit-prep or
pinboard packet, or FHIR bundle, so a download still works after a backend
restart. No foreign key. Rows are served for 30 minutes at most and are purged
at logout, lock and profile delete (EXPORT-ARTIFACT-RETENTION).

``downgrade()`` drops the table and the artifacts in it; they are transient.

Revision ID: 019_export_artifacts
Revises: 018_ocr_opt_in
Create Date: 2026-11-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "019_export_artifacts"
down_revision: Union[str, None] = "018_ocr_opt_in"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "export_artifact",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("profile_id", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )


def downgrade() -> None:
    op.drop_table("export_artifact")
