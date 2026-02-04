"""Initial schema for master database.

Revision ID: 001_initial
Revises:
Create Date: 2026-02-04

Master database tables:
- profiles: User accounts
- audit_logs: HIPAA-compliant audit trail
- biomarker_knowledge: Medical reference data
- intervention_mappings: Evidence-based lifestyle interventions
- biomarker_relationships: Panel-level biomarker relationships
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # profiles table
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("encryption_key_id", sa.String(36), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("password_salt", sa.String(64), nullable=True),
        sa.Column("is_locked", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(), nullable=True),
    )

    # audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "profile_id",
            sa.String(36),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("action", sa.String(500), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.String(36), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("client_info", sa.String(255), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_logs_profile_id", "audit_logs", ["profile_id"])
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])

    # biomarker_knowledge table
    op.create_table(
        "biomarker_knowledge",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analyte_canonical", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("loinc_codes_json", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("clinical_significance", sa.Text(), nullable=False),
        sa.Column("normal_interpretation", sa.Text(), nullable=False),
        sa.Column("high_interpretation", sa.Text(), nullable=False),
        sa.Column("low_interpretation", sa.Text(), nullable=False),
        sa.Column("ref_range_adult_json", sa.Text(), nullable=False),
        sa.Column("common_causes_high_json", sa.Text(), nullable=True),
        sa.Column("common_causes_low_json", sa.Text(), nullable=True),
        sa.Column("critical_low", sa.Float(), nullable=True),
        sa.Column("critical_high", sa.Float(), nullable=True),
        sa.Column("standard_unit", sa.String(50), nullable=False),
        sa.Column("unit_conversions_json", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("panels_json", sa.Text(), nullable=True),
        sa.Column("sources_json", sa.Text(), nullable=False),
        sa.Column("last_reviewed", sa.DateTime(), nullable=False),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("version", sa.Integer(), default=1, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_biomarker_knowledge_analyte_canonical",
        "biomarker_knowledge",
        ["analyte_canonical"],
    )
    op.create_index(
        "ix_biomarker_knowledge_category", "biomarker_knowledge", ["category"]
    )

    # intervention_mappings table
    op.create_table(
        "intervention_mappings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analyte_canonical", sa.String(100), nullable=False),
        sa.Column("condition_type", sa.String(30), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("intervention_text", sa.Text(), nullable=False),
        sa.Column("intervention_title", sa.String(100), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("strength_of_evidence", sa.String(20), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("contraindications_json", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), default=10, nullable=False),
        sa.Column("sources_json", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Integer(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_intervention_mappings_analyte_canonical",
        "intervention_mappings",
        ["analyte_canonical"],
    )
    op.create_index(
        "ix_intervention_mappings_condition_type",
        "intervention_mappings",
        ["condition_type"],
    )
    op.create_index(
        "ix_intervention_mappings_category", "intervention_mappings", ["category"]
    )

    # biomarker_relationships table
    op.create_table(
        "biomarker_relationships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("primary_analyte", sa.String(100), nullable=False),
        sa.Column("related_analyte", sa.String(100), nullable=False),
        sa.Column("relationship_type", sa.String(30), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("clinical_significance", sa.Text(), nullable=False),
        sa.Column("ratio_calculation", sa.String(100), nullable=True),
        sa.Column("ratio_target_range_json", sa.Text(), nullable=True),
        sa.Column("abnormal_interpretation", sa.Text(), nullable=True),
        sa.Column("panel_name", sa.String(50), nullable=True),
        sa.Column("sources_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_biomarker_relationships_primary_analyte",
        "biomarker_relationships",
        ["primary_analyte"],
    )
    op.create_index(
        "ix_biomarker_relationships_related_analyte",
        "biomarker_relationships",
        ["related_analyte"],
    )
    op.create_index(
        "ix_biomarker_relationships_relationship_type",
        "biomarker_relationships",
        ["relationship_type"],
    )
    op.create_index(
        "ix_biomarker_relationships_panel_name",
        "biomarker_relationships",
        ["panel_name"],
    )


def downgrade() -> None:
    op.drop_table("biomarker_relationships")
    op.drop_table("intervention_mappings")
    op.drop_table("biomarker_knowledge")
    op.drop_table("audit_logs")
    op.drop_table("profiles")
