"""
Feedback API — RL-FEED-001/002.

Endpoints:
  POST   /feedback/turns/{turn_id}      — upsert rating + correction for a turn
  GET    /feedback/stats                — aggregate stats for the profile
  POST   /feedback/export               — write JSONL dataset files locally

Privacy:
  - All data stored in per-profile SQLCipher DB (ProfileDbSession).
  - Export applies redaction.RedactionEngine before writing.
  - Export requires explicit confirmation flag in request body.

Audit:
  - Feedback submission and export are logged to the master audit log.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import RequireAuth, ProfileDbSession
from core.audit import create_audit_log
from core.database import get_db
from core.time import utcnow
from models.response_feedback import ResponseFeedback


async def _emit_audit(event_type: str, action: str, profile_id: str,
                      entity_type: str, entity_id: str, details: dict) -> None:
    """Best-effort audit log — swallows all errors so feedback never fails."""
    try:
        async for master_db in get_db():
            await create_audit_log(
                db=master_db,
                event_type=event_type,
                action=action,
                profile_id=profile_id,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
            )
            await master_db.commit()
            break
    except Exception:
        pass

logger = logging.getLogger(__name__)

router = APIRouter()

# Valid feedback tags
VALID_TAGS = frozenset({
    "inaccurate",
    "too_technical",
    "missing_context",
    "unsafe",
    "too_long",
    "too_short",
    "off_topic",
    "helpful",
})

# Default export directory (relative to the backend working dir)
_DEFAULT_EXPORT_DIR = Path(os.environ.get(
    "RL_EXPORT_DIR",
    str(Path(__file__).resolve().parents[1] / "rl_exports"),
))


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    """Upsert feedback for a single assistant turn."""

    session_id: str = Field(..., min_length=1)
    rating: int = Field(..., description="+1 (helpful) or -1 (unhelpful)")
    correction_text: Optional[str] = Field(
        default=None,
        max_length=8000,
        description="User's improved answer (for DPO 'chosen').",
    )
    feedback_tags: Optional[list[str]] = Field(
        default=None,
        description="Free-set of quality tags.",
    )
    prompt_snapshot: Optional[str] = Field(
        default=None,
        description="Fully-composed prompt including retrieved context.",
    )
    response_text: Optional[str] = Field(
        default=None,
        description="The assistant response that was rated.",
    )
    model_name: Optional[str] = Field(default=None, max_length=200)
    provider: Optional[str] = Field(default=None, max_length=100)

    @field_validator("rating")
    @classmethod
    def rating_must_be_pm1(cls, v: int) -> int:
        if v not in (1, -1):
            raise ValueError("rating must be +1 or -1")
        return v

    @field_validator("feedback_tags")
    @classmethod
    def validate_tags(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        invalid = [t for t in v if t not in VALID_TAGS]
        if invalid:
            raise ValueError(f"Invalid tags: {invalid}. Valid: {sorted(VALID_TAGS)}")
        return v


class FeedbackResponse(BaseModel):
    turn_id: str
    rating: int
    correction_text: Optional[str]
    feedback_tags: Optional[list[str]]
    created_at: str
    updated_at: str


class FeedbackStatsResponse(BaseModel):
    total_feedback: int
    positive_count: int
    negative_count: int
    correction_count: int
    tag_distribution: dict[str, int]
    model_distribution: dict[str, int]
    provider_distribution: dict[str, int]


class ExportRequest(BaseModel):
    """Explicit confirmation is required before writing dataset files."""

    confirmed: bool = Field(
        ...,
        description="Must be true to proceed with export.",
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="Optional override for the export directory.",
    )


class ExportResponse(BaseModel):
    dpo_pairs_count: int
    sft_positives_count: int
    grpo_rewards_count: int
    dpo_path: str
    sft_path: str
    grpo_path: str
    metadata_path: str
    redacted_fields: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_feedback_for_turn(
    turn_id: str,
    profile_id: str,
    profile_db: AsyncSession,
) -> Optional[ResponseFeedback]:
    result = await profile_db.execute(
        select(ResponseFeedback).where(
            ResponseFeedback.turn_id == turn_id,
            ResponseFeedback.profile_id == profile_id,
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/turns/{turn_id}",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Upsert feedback for an assistant turn",
)
async def upsert_feedback(
    turn_id: str,
    body: FeedbackRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """
    Submit or update feedback for a specific assistant turn.

    Upsert semantics: if feedback for this turn already exists in this
    profile, it is overwritten (user may change their rating).
    """
    profile_id = session.profile_id
    now = utcnow()

    existing = await _get_feedback_for_turn(turn_id, profile_id, profile_db)

    if existing:
        existing.rating = body.rating
        existing.correction_text = body.correction_text
        existing.feedback_tags = body.feedback_tags
        if body.prompt_snapshot is not None:
            existing.prompt_snapshot = body.prompt_snapshot
        if body.response_text is not None:
            existing.response_text = body.response_text
        if body.model_name is not None:
            existing.model_name = body.model_name
        if body.provider is not None:
            existing.provider = body.provider
        existing.updated_at = now
        feedback = existing
    else:
        feedback = ResponseFeedback(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            session_id=body.session_id,
            turn_id=turn_id,
            rating=body.rating,
            correction_text=body.correction_text,
            feedback_tags=body.feedback_tags,
            prompt_snapshot=body.prompt_snapshot,
            response_text=body.response_text,
            model_name=body.model_name,
            provider=body.provider,
            created_at=now,
            updated_at=now,
        )
        profile_db.add(feedback)

    await profile_db.commit()
    await profile_db.refresh(feedback)

    # Audit log (master DB) — best-effort, mockable via _emit_audit
    await _emit_audit(
        event_type="feedback.submit",
        action=f"Feedback {'updated' if existing else 'submitted'} for turn {turn_id}",
        profile_id=profile_id,
        entity_type="response_feedback",
        entity_id=feedback.id,
        details={"rating": body.rating, "has_correction": bool(body.correction_text)},
    )

    return FeedbackResponse(
        turn_id=feedback.turn_id,
        rating=feedback.rating,
        correction_text=feedback.correction_text,
        feedback_tags=feedback.feedback_tags,
        created_at=feedback.created_at.isoformat(),
        updated_at=feedback.updated_at.isoformat(),
    )


@router.get(
    "/stats",
    response_model=FeedbackStatsResponse,
    summary="Aggregate feedback stats for the authenticated profile",
)
async def get_feedback_stats(
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Return counts and distributions for this profile's feedback."""
    profile_id = session.profile_id

    result = await profile_db.execute(
        select(ResponseFeedback).where(
            ResponseFeedback.profile_id == profile_id,
        )
    )
    rows = result.scalars().all()

    positive_count = sum(1 for r in rows if r.rating == 1)
    negative_count = sum(1 for r in rows if r.rating == -1)
    correction_count = sum(1 for r in rows if r.correction_text)

    tag_dist: dict[str, int] = {}
    model_dist: dict[str, int] = {}
    provider_dist: dict[str, int] = {}

    for r in rows:
        for tag in (r.feedback_tags or []):
            tag_dist[tag] = tag_dist.get(tag, 0) + 1
        m = r.model_name or "unknown"
        p = r.provider or "unknown"
        model_dist[m] = model_dist.get(m, 0) + 1
        provider_dist[p] = provider_dist.get(p, 0) + 1

    return FeedbackStatsResponse(
        total_feedback=len(rows),
        positive_count=positive_count,
        negative_count=negative_count,
        correction_count=correction_count,
        tag_distribution=tag_dist,
        model_distribution=model_dist,
        provider_distribution=provider_dist,
    )


@router.post(
    "/export",
    response_model=ExportResponse,
    summary="Export DPO/GRPO preference dataset files",
)
async def export_dataset(
    body: ExportRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """
    Write JSONL preference dataset files to local storage.

    Requires confirmed=true.  Redaction is applied to all prompt/response/
    correction fields before writing.  Returns file paths and row counts.
    """
    if not body.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export requires confirmed=true in the request body.",
        )

    profile_id = session.profile_id

    # Load all feedback for this profile
    result = await profile_db.execute(
        select(ResponseFeedback).where(
            ResponseFeedback.profile_id == profile_id,
        ).order_by(ResponseFeedback.created_at)
    )
    rows = result.scalars().all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No feedback records found for this profile.",
        )

    # Determine output directory
    out_dir = Path(body.output_dir) if body.output_dir else _DEFAULT_EXPORT_DIR
    profile_out_dir = out_dir / f"profile_{profile_id[:8]}"

    # Convert ORM rows → FeedbackRecord dataclasses for the module
    from modules.rl_dataset import FeedbackRecord, export_rl_datasets

    records = [
        FeedbackRecord(
            id=r.id,
            profile_id=r.profile_id,
            session_id=r.session_id,
            turn_id=r.turn_id,
            rating=r.rating,
            correction_text=r.correction_text,
            feedback_tags=r.feedback_tags,
            prompt_snapshot=r.prompt_snapshot,
            response_text=r.response_text,
            model_name=r.model_name,
            provider=r.provider,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]

    export_result = export_rl_datasets(
        records=records,
        output_dir=profile_out_dir,
        profile_id=profile_id,
    )

    # Audit log — best-effort, mockable via _emit_audit
    await _emit_audit(
        event_type="feedback.export",
        action=f"RL dataset exported: {export_result.dpo_pairs_count} DPO, "
               f"{export_result.sft_positives_count} SFT, "
               f"{export_result.grpo_rewards_count} GRPO",
        profile_id=profile_id,
        entity_type="rl_export",
        entity_id=str(profile_out_dir),
        details={
            "output_dir": str(profile_out_dir),
            "dpo_pairs": export_result.dpo_pairs_count,
            "sft": export_result.sft_positives_count,
            "grpo": export_result.grpo_rewards_count,
        },
    )

    return ExportResponse(
        dpo_pairs_count=export_result.dpo_pairs_count,
        sft_positives_count=export_result.sft_positives_count,
        grpo_rewards_count=export_result.grpo_rewards_count,
        dpo_path=export_result.dpo_path,
        sft_path=export_result.sft_path,
        grpo_path=export_result.grpo_path,
        metadata_path=export_result.metadata_path,
        redacted_fields=export_result.redacted_fields,
    )
