"""Initial schema for per-profile encrypted database.

Revision ID: 001_initial
Revises:
Create Date: 2026-02-04

Profile database tables:
- documents: Imported medical documents
- observations: Lab values and measurements
- chunks: RAG text segments
- embeddings: Vector storage for similarity search
- lab_interpretations: AI-generated lab result interpretations
- panel_interpretations: Holistic panel interpretations
- medications: User's medication records
- medication_schedules: When medications should be taken
- doses_taken: Records of doses taken/skipped
- adherence_patterns: Learned behavioral patterns
- reminder_logs: Log of reminders sent
- user_model_settings: User's model tier preferences
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
    # === documents table ===
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("path_hash", sa.String(64), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("source", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), default="pending", nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("collection_date", sa.DateTime(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.Column("parsed_at", sa.DateTime(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("encryption_iv", sa.String(32), nullable=True),
    )
    op.create_index("ix_documents_profile_id", "documents", ["profile_id"])
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])

    # === observations table ===
    op.create_table(
        "observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column(
            "doc_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("analyte_canonical", sa.String(100), nullable=False),
        sa.Column("analyte_raw", sa.String(255), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("value_text", sa.String(255), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("ref_low", sa.Float(), nullable=True),
        sa.Column("ref_high", sa.Float(), nullable=True),
        sa.Column("ref_range_text", sa.String(100), nullable=True),
        sa.Column("flag", sa.String(10), nullable=True),
        sa.Column("is_abnormal", sa.Boolean(), nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=True),
        sa.Column("user_verified", sa.Boolean(), default=False, nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("extraction_confidence", sa.Float(), nullable=True),
        sa.Column("version", sa.Integer(), default=1, nullable=False),
        sa.Column("original_value_json", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_bbox_json", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_observations_profile_id", "observations", ["profile_id"])
    op.create_index("ix_observations_doc_id", "observations", ["doc_id"])
    op.create_index(
        "ix_observations_analyte_canonical", "observations", ["analyte_canonical"]
    )
    op.create_index("ix_observations_collected_at", "observations", ["collected_at"])

    # === chunks table ===
    op.create_table(
        "chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "doc_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("start_char", sa.Integer(), nullable=True),
        sa.Column("end_char", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("chunk_type", sa.String(50), default="text", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_chunks_doc_id", "chunks", ["doc_id"])

    # === embeddings table ===
    op.create_table(
        "embeddings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "chunk_id",
            sa.String(36),
            sa.ForeignKey("chunks.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("vector_blob", sa.LargeBinary(), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("vector_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_embeddings_chunk_id", "embeddings", ["chunk_id"])

    # === lab_interpretations table ===
    op.create_table(
        "lab_interpretations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column(
            "observation_id",
            sa.String(36),
            sa.ForeignKey("observations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("interpretation_text", sa.Text(), nullable=False),
        sa.Column("severity_level", sa.String(20), nullable=False),
        sa.Column("advice_text", sa.Text(), nullable=True),
        sa.Column("citations_json", sa.Text(), nullable=False),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("model_tier", sa.String(20), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("requires_physician_review", sa.Boolean(), default=False, nullable=False),
        sa.Column("physician_review_reason", sa.Text(), nullable=True),
        sa.Column("safety_validation_json", sa.Text(), nullable=True),
        sa.Column("viewed_at", sa.DateTime(), nullable=True),
        sa.Column("regeneration_count", sa.Integer(), default=0, nullable=False),
        sa.Column("previous_interpretation_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_lab_interpretations_profile_id", "lab_interpretations", ["profile_id"]
    )
    op.create_index(
        "ix_lab_interpretations_observation_id",
        "lab_interpretations",
        ["observation_id"],
    )
    op.create_index(
        "ix_lab_interpretations_severity_level",
        "lab_interpretations",
        ["severity_level"],
    )

    # === panel_interpretations table ===
    op.create_table(
        "panel_interpretations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("panel_name", sa.String(50), nullable=False),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.Column("observation_ids_json", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("overall_status", sa.String(20), nullable=False),
        sa.Column("relationship_insights_json", sa.Text(), nullable=True),
        sa.Column("advice_text", sa.Text(), nullable=True),
        sa.Column("citations_json", sa.Text(), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("requires_physician_review", sa.Boolean(), default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_panel_interpretations_profile_id", "panel_interpretations", ["profile_id"]
    )
    op.create_index(
        "ix_panel_interpretations_panel_name", "panel_interpretations", ["panel_name"]
    )
    op.create_index(
        "ix_panel_interpretations_collected_at",
        "panel_interpretations",
        ["collected_at"],
    )

    # === medications table ===
    op.create_table(
        "medications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("generic_name", sa.String(255), nullable=True),
        sa.Column("dosage_amount", sa.Float(), nullable=True),
        sa.Column("dosage_unit", sa.String(50), nullable=True),
        sa.Column("dosage_form", sa.String(50), nullable=True),
        sa.Column("frequency", sa.String(30), default="once_daily", nullable=False),
        sa.Column("frequency_details_json", sa.Text(), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("reminder_enabled", sa.Boolean(), default=False, nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_medications_profile_id", "medications", ["profile_id"])
    op.create_index("ix_medications_name", "medications", ["name"])

    # === medication_schedules table ===
    op.create_table(
        "medication_schedules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "medication_id",
            sa.String(36),
            sa.ForeignKey("medications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("schedule_label", sa.String(30), nullable=False),
        sa.Column("target_time", sa.Time(), nullable=False),
        sa.Column("adaptive_window_start", sa.Time(), nullable=True),
        sa.Column("adaptive_window_end", sa.Time(), nullable=True),
        sa.Column("reminder_offset_minutes", sa.Integer(), default=15, nullable=False),
        sa.Column("days_of_week_json", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_medication_schedules_medication_id",
        "medication_schedules",
        ["medication_id"],
    )

    # === doses_taken table ===
    op.create_table(
        "doses_taken",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "medication_id",
            sa.String(36),
            sa.ForeignKey("medications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "schedule_id",
            sa.String(36),
            sa.ForeignKey("medication_schedules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("taken_at", sa.DateTime(), nullable=False),
        sa.Column("log_method", sa.String(30), nullable=False),
        sa.Column("dosage_amount", sa.Float(), nullable=True),
        sa.Column("dosage_unit", sa.String(50), nullable=True),
        sa.Column("variance_minutes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("was_skipped", sa.Boolean(), default=False, nullable=False),
        sa.Column("skip_reason", sa.String(100), nullable=True),
        sa.Column("logged_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_doses_taken_medication_id", "doses_taken", ["medication_id"])
    op.create_index("ix_doses_taken_schedule_id", "doses_taken", ["schedule_id"])
    op.create_index("ix_doses_taken_taken_at", "doses_taken", ["taken_at"])

    # === adherence_patterns table ===
    op.create_table(
        "adherence_patterns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "medication_id",
            sa.String(36),
            sa.ForeignKey("medications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "schedule_id",
            sa.String(36),
            sa.ForeignKey("medication_schedules.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("pattern_type", sa.String(30), nullable=False),
        sa.Column("pattern_data_json", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("learned_at", sa.DateTime(), nullable=False),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_adherence_patterns_medication_id", "adherence_patterns", ["medication_id"]
    )
    op.create_index(
        "ix_adherence_patterns_schedule_id", "adherence_patterns", ["schedule_id"]
    )
    op.create_index(
        "ix_adherence_patterns_pattern_type", "adherence_patterns", ["pattern_type"]
    )

    # === reminder_logs table ===
    op.create_table(
        "reminder_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column(
            "medication_id",
            sa.String(36),
            sa.ForeignKey("medications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "schedule_id",
            sa.String(36),
            sa.ForeignKey("medication_schedules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reminder_type", sa.String(20), nullable=False),
        sa.Column("message_tone", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.Column("delivery_method", sa.String(20), nullable=False),
        sa.Column("was_interacted", sa.Boolean(), default=False, nullable=False),
        sa.Column("interaction_type", sa.String(20), nullable=True),
        sa.Column("interacted_at", sa.DateTime(), nullable=True),
        sa.Column("snooze_minutes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_reminder_logs_profile_id", "reminder_logs", ["profile_id"])
    op.create_index(
        "ix_reminder_logs_medication_id", "reminder_logs", ["medication_id"]
    )
    op.create_index("ix_reminder_logs_sent_at", "reminder_logs", ["sent_at"])

    # === user_model_settings table ===
    op.create_table(
        "user_model_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("preferred_tier", sa.String(20), default="low", nullable=False),
        sa.Column("auto_detect_enabled", sa.Boolean(), default=True, nullable=False),
        sa.Column("last_hardware_json", sa.Text(), nullable=True),
        sa.Column("last_detection_at", sa.DateTime(), nullable=True),
        sa.Column("download_state_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_user_model_settings_profile_id", "user_model_settings", ["profile_id"]
    )


def downgrade() -> None:
    op.drop_table("user_model_settings")
    op.drop_table("reminder_logs")
    op.drop_table("adherence_patterns")
    op.drop_table("doses_taken")
    op.drop_table("medication_schedules")
    op.drop_table("medications")
    op.drop_table("panel_interpretations")
    op.drop_table("lab_interpretations")
    op.drop_table("embeddings")
    op.drop_table("chunks")
    op.drop_table("observations")
    op.drop_table("documents")
