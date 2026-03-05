"""Add timezone, voice settings, and gamification tables.

Revision ID: 003_gamification_voice
Revises: 002_external_api
Create Date: 2026-03-04

Adds:
- timezone, voice_logging_enabled, voice_modal_seen to user_model_settings
- badge_definition table (seed data for 8 badges)
- earned_badge table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003_gamification_voice"
down_revision: Union[str, None] = "002_external_api"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BADGE_SEEDS = [
    ("first-log", "First Log", "Log your first dose", "spark", "count", '{"count": 1}', 0),
    ("3-day-streak", "3-Day Streak", "3 consecutive days of adherence", "flame", "streak", '{"streak_days": 3}', 1),
    ("week-warrior", "Week Warrior", "7 consecutive days of adherence", "flame", "streak", '{"streak_days": 7}', 2),
    ("two-week-titan", "Two-Week Titan", "14 consecutive days of adherence", "trophy", "streak", '{"streak_days": 14}', 3),
    ("month-master", "Month Master", "30 consecutive days of adherence", "trophy", "streak", '{"streak_days": 30}', 4),
    ("perfect-week", "Perfect Week", "All scheduled doses on time for 7 days", "star", "pattern", '{"perfect_days": 7, "max_variance_minutes": 60}', 5),
    ("multi-med-master", "Multi-Med Master", "7-day streak on 2+ medications", "shield", "streak", '{"streak_days": 7, "min_medications": 2}', 6),
    ("comeback-kid", "Comeback Kid", "Resume logging after a 3+ day gap", "heart", "gap", '{"gap_days": 3}', 7),
]


def upgrade() -> None:
    # user_model_settings additions
    op.add_column(
        "user_model_settings",
        sa.Column("timezone", sa.Text(), nullable=False, server_default="UTC"),
    )
    op.add_column(
        "user_model_settings",
        sa.Column("voice_logging_enabled", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_model_settings",
        sa.Column("voice_modal_seen", sa.Boolean(), nullable=False, server_default="0"),
    )

    # badge_definition
    op.create_table(
        "badge_definition",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon", sa.Text(), nullable=False),
        sa.Column("criteria_type", sa.Text(), nullable=False),
        sa.Column("criteria_json", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    # earned_badge
    op.create_table(
        "earned_badge",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("profile_id", sa.Text(), nullable=False),
        sa.Column("badge_id", sa.Text(), sa.ForeignKey("badge_definition.id"), nullable=False),
        sa.Column("medication_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("earned_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("profile_id", "badge_id", "medication_id", name="uq_earned_badge"),
    )

    # Seed badge definitions
    badge_table = sa.table(
        "badge_definition",
        sa.column("id", sa.Text()),
        sa.column("name", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("icon", sa.Text()),
        sa.column("criteria_type", sa.Text()),
        sa.column("criteria_json", sa.Text()),
        sa.column("sort_order", sa.Integer()),
    )
    op.bulk_insert(badge_table, [
        {
            "id": b[0], "name": b[1], "description": b[2], "icon": b[3],
            "criteria_type": b[4], "criteria_json": b[5], "sort_order": b[6],
        }
        for b in BADGE_SEEDS
    ])


def downgrade() -> None:
    op.drop_table("earned_badge")
    op.drop_table("badge_definition")
    op.drop_column("user_model_settings", "voice_modal_seen")
    op.drop_column("user_model_settings", "voice_logging_enabled")
    op.drop_column("user_model_settings", "timezone")
