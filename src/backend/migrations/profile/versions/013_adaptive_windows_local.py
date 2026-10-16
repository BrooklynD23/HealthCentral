"""Adaptive windows move to the profile-local frame (D-2 SCHED-TZ).

Adds the per-schedule marker ``adaptive_window_tz`` (zone the stored window
was learned in; NULL = not yet re-learned in local time) and clears stored
windows, which were UTC-frame. The scheduler then falls back to
``target_time +/- tolerance`` until the automatic re-learn runs.

Downgrade clears the windows again (local-frame values must not be read as
UTC by the pre-D-2 scheduler) and drops the column. The original UTC-frame
values are not restored: they cannot be rebuilt.

Revision ID: 013_adaptive_windows_local
Revises: 012_pinboards
Create Date: 2026-10-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "013_adaptive_windows_local"
down_revision: Union[str, None] = "012_pinboards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CLEAR = (
    "UPDATE medication_schedules "
    "SET adaptive_window_start = NULL, adaptive_window_end = NULL"
)


def upgrade() -> None:
    op.add_column(
        "medication_schedules",
        sa.Column("adaptive_window_tz", sa.String(64), nullable=True),
    )
    op.execute(_CLEAR)


def downgrade() -> None:
    op.execute(_CLEAR)
    with op.batch_alter_table("medication_schedules") as batch:
        batch.drop_column("adaptive_window_tz")
