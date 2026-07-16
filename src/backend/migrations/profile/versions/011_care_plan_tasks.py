"""Add care_plan_task table.

Revision ID: 011_care_plan_tasks
Revises: 010_entity_source_spans
Create Date: 2026-07-10

HC-M15: Follow-up instructions, ordered tests, and referrals extracted from
visit notes become checklist tasks after explicit user acceptance. Each task
carries source provenance (document, entity, verbatim quote) and a due date
only when the source text supported one.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "011_care_plan_tasks"
down_revision: Union[str, None] = "010_entity_source_spans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "care_plan_task",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("due_date_confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("source_document_id", sa.Text(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("source_entity_id", sa.Text(), sa.ForeignKey("document_entity.id"), nullable=True),
        sa.Column("source_quote", sa.Text(), nullable=True),
        sa.Column("user_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("idx_care_plan_task_status", "care_plan_task", ["status"])
    op.create_index("idx_care_plan_task_source_doc", "care_plan_task", ["source_document_id"])
    op.create_index("idx_care_plan_task_source_entity", "care_plan_task", ["source_entity_id"])


def downgrade() -> None:
    op.drop_index("idx_care_plan_task_source_entity")
    op.drop_index("idx_care_plan_task_source_doc")
    op.drop_index("idx_care_plan_task_status")
    op.drop_table("care_plan_task")
