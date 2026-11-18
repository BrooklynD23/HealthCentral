"""
Export API endpoints.

Generates clinician-ready summaries and data exports.
All endpoints require authentication.

Sprint 4: Wired to ExportModule for CSV/JSON/summary/questions generation.
"""

import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import time as core_time
from core.audit import audit_and_commit, log_export_event
from core.auth import ProfileDbSession, RequireAuth
from core.database import get_db
from core.denial_audit import audit_denial
from core.profile_database import get_profile_db_manager
from core.security import is_jwt_token_revoked
from core.time import NaiveUtcDatetime, profile_timezone_name, to_local, utcnow
from models import AuditLog, CarePlanTask, Document, Medication, Observation, Profile
from models.document_category import DocumentCategory, DocumentEntity
from models.export_artifact import EXPORT_ARTIFACT_KINDS, ExportArtifact
from modules.export import ExportModule
from modules.fhir_export import build_fhir_bundle
from modules.normalize import canonical_unit_for, convert_to_canonical, normalize_unit

logger = logging.getLogger(__name__)

router = APIRouter()

# UUID validation pattern
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE
)

# In-process layer of the export artifacts (G-C1, owner decision
# EXPORT-ARTIFACT-RETENTION): every artifact is written here AND as an
# `export_artifact` row in the profile vault. A download reads here first and
# falls back to the vault row on a miss (the backend-restart case). TTL and
# purge apply to both layers.
_summary_store: dict[str, dict] = {}

# Visit-prep and pinboard packets (HC-M18)
_packet_store: dict[str, dict] = {}

# FHIR R4 exports (HC-M22)
_fhir_store: dict[str, dict] = {}

# Stored exports expire after this long (EXPORT-STORE-PURGE). The TTL clock is
# read via the core.time module so tests that freeze `api.export.utcnow` (the
# generation-day footer tests) do not also age the stored entries.
_EXPORT_TTL = timedelta(minutes=30)

# Title of the trends section ExportModule.generate_doctor_summary adds (modules/export.py).
TRENDS_SECTION_TITLE = "Notable Trends"


def _expired(entry: dict) -> bool:
    # L0 ruling (iii): an entry with no `created_at` counts as FRESH, so
    # legacy fixtures that write bare entries keep being served.
    created = entry.get("created_at")
    return created is not None and core_time.utcnow() - created > _EXPORT_TTL


def _prune_expired() -> None:
    for store in (_summary_store, _packet_store, _fhir_store):
        for key in [k for k, v in store.items() if _expired(v)]:
            del store[key]


async def purge_profile_exports(profile_id: str) -> int:
    """Drop every export for `profile_id` from memory and from its open vault.

    Returns how many entries and rows went. The vault delete runs through the
    profile's open connection, so callers must await this BEFORE closing it.
    If no connection is open there is no vault session to delete through (the
    vault cannot serve a download either); that is logged, never silent. A
    delete that raises is not caught: the lock, logout or delete fails loudly.

    Also drops that profile's cached page pictures and assistant answers from memory
    (MEM-PURGE). That runs first, so it holds when no vault is open. The return value
    still counts exports only.
    """
    from api.documents import purge_page_images
    from modules.agent.cache import purge_profile

    images, answers = purge_page_images(profile_id), purge_profile(profile_id)
    logger.debug("Memory purge: %d page images, %d cached answers dropped", images, answers)
    removed = 0
    for store in (_summary_store, _packet_store, _fhir_store):
        for key in [k for k, v in store.items() if v.get("profile_id") == profile_id]:
            del store[key]
            removed += 1
    connection = get_profile_db_manager().get_connection(profile_id)
    if connection is None:
        logger.warning(
            "Export purge: no open vault for profile %s; persisted artifacts not reachable",
            profile_id,
        )
        return removed
    async with connection.get_session() as vault:
        # The vault is per-profile, so EVERY row goes, including one carrying another
        # profile's id (left by a cross-profile restore). Serving such a row stays a 403.
        result = await vault.execute(delete(ExportArtifact))
    return removed + (result.rowcount or 0)


def _session_exp(session) -> datetime:
    """The session's expiry as naive UTC, the form the column and `core_time.utcnow()` use.

    `Session.expires_at` is tz-aware UTC; comparing it with a naive value raises, so every
    stored or compared expiry goes through here.
    """
    return session.expires_at.astimezone(timezone.utc).replace(tzinfo=None)


async def _prune_dead_rows(profile_db: AsyncSession, profile_id: str) -> None:
    """Delete `profile_id`'s rows that can never be served again (EXPORT-LIVE-LOGIN).

    Dead means expired, a NULL or empty `session_jti`, a revoked one, or a NULL
    `session_exp` or one that has passed. Runs in the caller's transaction (no commit), so
    the route's stage, audit commit, vault commit order is unchanged and another profile's
    rows are never touched.
    """
    rows = (
        await profile_db.execute(
            select(
                ExportArtifact.id,
                ExportArtifact.created_at,
                ExportArtifact.session_jti,
                ExportArtifact.session_exp,
            ).where(ExportArtifact.profile_id == profile_id)
        )
    ).all()
    now = core_time.utcnow()
    dead = [
        row.id
        for row in rows
        if now - row.created_at > _EXPORT_TTL
        or not row.session_jti
        or row.session_exp is None
        or now >= row.session_exp
        or is_jwt_token_revoked(row.session_jti)
    ]
    if dead:
        await profile_db.execute(
            delete(ExportArtifact).where(
                ExportArtifact.profile_id == profile_id, ExportArtifact.id.in_(dead)
            )
        )


async def _save_artifact(
    profile_db: AsyncSession,
    *,
    artifact_id: str,
    kind: str,
    profile_id: str,
    payload: dict,
    session_jti: Optional[str],
    session_exp: datetime,
    created_at: datetime,
) -> None:
    """Stage a downloadable artifact in the caller's profile vault (G-C1).

    Flush only: the route commits the vault after its audit row commits, so a
    failed audit never leaves an unaudited artifact behind. `json.dumps` is
    strict (no `default=`): a value that is not JSON fails here, loudly, and is
    never silently stringified. Expired rows are deleted on read, and every row
    goes at logout, lock and profile delete (`purge_profile_exports`).
    `session_jti` records the generating login (EXPORT-LIVE-LOGIN): any live login of the
    profile may be served the row, and each save prunes this profile's dead rows.
    `session_exp` is that login's expiry as naive UTC (`_session_exp`): the revocation list
    forgets the jti at that moment, so the row is not served from then on.
    `created_at` is the artifact's one creation time, taken by the route before this call
    and reused for the in-process entry, so a logout committed between save and publish
    cannot make the two layers disagree about which side of the cutoff the export is on.
    """
    if kind not in EXPORT_ARTIFACT_KINDS:
        raise ValueError(f"unknown export artifact kind: {kind}")
    await _prune_dead_rows(profile_db, profile_id)
    profile_db.add(
        ExportArtifact(
            id=artifact_id,
            kind=kind,
            profile_id=profile_id,
            payload_json=json.dumps(payload),
            created_at=created_at,
            session_jti=session_jti,
            session_exp=session_exp,
        )
    )
    await profile_db.flush()


async def _load_artifact(
    profile_db: Optional[AsyncSession], *, artifact_id: str, kind: str
) -> Optional[tuple[str, dict, Optional[str], Optional[datetime], datetime]]:
    """Return `(owner profile_id, payload, session_jti, session_exp, created_at)` for a live persisted artifact, else None.

    None covers: no vault session, no such row, a row of another kind, and a row
    older than `_EXPORT_TTL` (deleted here, on read). The caller keeps the
    ownership check and its denial audit.
    """
    if profile_db is None:
        return None
    result = await profile_db.execute(
        select(ExportArtifact).where(
            ExportArtifact.id == artifact_id, ExportArtifact.kind == kind
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    if core_time.utcnow() - row.created_at > _EXPORT_TTL:
        await profile_db.execute(delete(ExportArtifact).where(ExportArtifact.id == artifact_id))
        await profile_db.commit()
        return None
    return row.profile_id, json.loads(row.payload_json), row.session_jti, row.session_exp, row.created_at


async def _logout_cutoff(master_db: AsyncSession, profile_id: str) -> Optional[datetime]:
    """Timestamp of the profile's latest `profile.logout` / `profile.lock` audit row, else None.

    Logout and lock commit that row before the export purge runs, so it is a durable cutoff
    even when the purge could not reach a closed vault (EXPORT-LIVE-LOGIN fail-closed).
    """
    result = await master_db.execute(
        select(func.max(AuditLog.timestamp)).where(
            AuditLog.profile_id == profile_id,
            AuditLog.event_type.in_(("profile.logout", "profile.lock")),
        )
    )
    return result.scalar()


async def _bound_to_session(
    profile_db: Optional[AsyncSession], entry: dict, session, *, artifact_id: str, store: dict,
    master_db: AsyncSession,
) -> bool:
    """EXPORT-LIVE-LOGIN: serve to any live login of the owning profile.

    Runs after the ownership check and the 30-minute TTL check. True when the entry's
    `session_exp` is set and still ahead (the revocation list forgets a jti at its token's
    exp, so a logout is only remembered until then) and its `session_jti` is non-empty and
    not revoked (a revoked jti means that login ended). The caller's jti is not compared
    to the stored one, because every login mints a new jti, so equality could never serve
    a row after a restart. A caller with no jti stays refused. A NULL jti or `session_exp`
    fails closed. The entry must also be newer than the profile's latest logout or lock audit
    row (`_logout_cutoff`): a later logout by another login ends every earlier export, even
    when its purge could not reach a closed vault. An entry with no `created_at` cannot be
    shown newer, so it fails closed whenever such a row exists. Otherwise the in-process entry and the vault row are deleted and the
    caller answers the same 404 as for an expired export.
    """
    jti = entry.get("session_jti")
    exp = entry.get("session_exp")
    if (
        jti
        and exp is not None
        and core_time.utcnow() < exp
        and session.token_jti
        and not is_jwt_token_revoked(jti)
    ):
        cutoff = await _logout_cutoff(master_db, session.profile_id)
        created = entry.get("created_at")
        if cutoff is None or (created is not None and created > cutoff):
            return True
    store.pop(artifact_id, None)
    if profile_db is not None:
        await profile_db.execute(delete(ExportArtifact).where(ExportArtifact.id == artifact_id))
        await profile_db.commit()
    return False

# Verified entity types that feed the FHIR export (Condition, Encounter,
# DiagnosticReport). Only verified_by_user is True rows are ever fetched.
FHIR_ENTITY_TYPES = ("diagnosis", "visit_type", "impression", "finding")

# Visit-note entity types that generate doctor questions (HC-M17).
QUESTION_ENTITY_TYPES = ("medication_change", "test_ordered", "referral")

# Verified entity types shown as visit/diagnosis mentions in the packet.
VISIT_MENTION_ENTITY_TYPES = ("diagnoses", "visit_type", "chief_complaint")


def validate_uuid(value: str, field_name: str = "ID") -> str:
    """Validate that a string is a valid UUID format."""
    if not UUID_PATTERN.match(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format"
        )
    return value


class SummaryRequest(BaseModel):
    """Request model for generating doctor summary."""

    # Time range
    from_date: Optional[NaiveUtcDatetime] = None
    to_date: Optional[NaiveUtcDatetime] = None

    # Content options
    include_all_values: bool = False  # vs only abnormal/changed
    include_trends: bool = True
    include_questions: bool = False  # "Questions to ask" section

    # Format
    format: str = "text"  # "pdf", "text", "html"


class SummaryResponse(BaseModel):
    """Response model for summary generation."""
    summary_id: str
    profile_id: str
    generated_at: str
    format: str

    # Content preview
    key_findings: list[str]
    abnormal_count: int
    date_range: str


class QuestionItem(BaseModel):
    """A discussion prompt for clinician visits.

    Categories: "trend", "abnormal", "clarification", "follow_up",
    "medication_change", "test_ordered", "referral" (HC-M17).
    """
    category: str
    question: str
    context: str  # Why this question is suggested
    related_analytes: list[str]
    # Provenance (HC-M17). Optional so existing consumers keep working.
    source_kind: Optional[str] = None  # observation | trend | care_task | entity
    source_id: Optional[str] = None

    @classmethod
    def from_prompt(cls, q) -> "QuestionItem":
        return cls(
            category=q.category,
            question=q.question,
            context=q.context,
            related_analytes=q.related_analytes,
            source_kind=q.source_kind,
            source_id=q.source_id,
        )


async def _fetch_observations(
    profile_db: AsyncSession,
    profile_id: str,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    analyte_filter: Optional[list[str]] = None,
) -> list[dict]:
    """
    Fetch observations from the profile database.

    Returns observations as dictionaries for use with ExportModule.
    """
    query = select(Observation).where(Observation.profile_id == profile_id)

    if from_date:
        query = query.where(Observation.collected_at >= from_date)
    if to_date:
        query = query.where(Observation.collected_at <= to_date)
    if analyte_filter:
        query = query.where(Observation.analyte_canonical.in_(analyte_filter))

    query = query.order_by(Observation.collected_at.desc(), Observation.analyte_canonical)

    result = await profile_db.execute(query)
    observations = result.scalars().all()

    # Convert to dictionaries for ExportModule
    return [
        {
            "id": obs.id,
            "analyte_canonical": obs.analyte_canonical,
            "analyte_raw": obs.analyte_raw,
            "value": obs.value,
            "value_text": obs.value_text,
            "unit": obs.unit,
            "ref_low": obs.ref_low,
            "ref_high": obs.ref_high,
            "ref_range_text": obs.ref_range_text,
            "flag": obs.flag,
            "is_abnormal": obs.is_abnormal,
            "user_verified": obs.user_verified,
            "collected_at": obs.collected_at,
        }
        for obs in observations
    ]


async def _fetch_care_task_dicts(profile_db: AsyncSession) -> list[dict]:
    """Open and needs_review care-plan tasks as dicts for ExportModule.

    Tasks are user-accepted by construction (HC-M15), so no verification
    filter is needed. Profile isolation comes from the per-profile DB.
    """
    result = await profile_db.execute(
        select(CarePlanTask).where(CarePlanTask.status.in_(["open", "needs_review"]))
    )
    return [
        {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "due_date": task.due_date,
            "source_quote": task.source_quote,
            "source_entity_id": task.source_entity_id,
        }
        for task in result.scalars().all()
    ]


async def _fetch_question_entity_dicts(profile_db: AsyncSession) -> list[dict]:
    """Verified visit-note entities that can generate doctor questions.

    Joins Document so entities orphaned by an old document delete (before
    entity cleanup existed) never feed exported questions.
    """
    result = await profile_db.execute(
        select(DocumentEntity)
        .join(Document, Document.id == DocumentEntity.doc_id)
        .where(
            DocumentEntity.entity_type.in_(QUESTION_ENTITY_TYPES),
            DocumentEntity.verified_by_user.is_(True),
        )
    )
    return [
        {
            "id": ent.id,
            "entity_type": ent.entity_type,
            "entity_value": ent.entity_value,
            "quote": ent.quote,
            "verified_by_user": ent.verified_by_user,
        }
        for ent in result.scalars().all()
    ]


async def _fetch_active_medication_dicts(
    profile_db: AsyncSession, profile_id: str
) -> list[dict]:
    """Active medications from the tracker for the packet."""
    result = await profile_db.execute(
        select(Medication).where(
            Medication.profile_id == profile_id,
            Medication.is_active.is_(True),
        )
    )
    return [
        {
            "id": med.id,
            "name": med.name,
            "dosage_amount": med.dosage_amount,
            "dosage_unit": med.dosage_unit,
            "frequency": med.frequency,
            "instructions": med.instructions,
        }
        for med in result.scalars().all()
    ]


async def _fetch_visit_mention_dicts(
    profile_db: AsyncSession,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> list[dict]:
    """Verified visit/diagnosis mention entities, with their document date."""
    query = (
        select(DocumentEntity, Document)
        .join(Document, Document.id == DocumentEntity.doc_id)
        .where(
            DocumentEntity.entity_type.in_(VISIT_MENTION_ENTITY_TYPES),
            DocumentEntity.verified_by_user.is_(True),
        )
    )
    if from_date:
        query = query.where(Document.collection_date >= from_date)
    if to_date:
        query = query.where(Document.collection_date <= to_date)

    result = await profile_db.execute(query)
    return [
        {
            "id": ent.id,
            "entity_type": ent.entity_type,
            "entity_value": ent.entity_value,
            "doc_date": (
                doc.collection_date.date().isoformat() if doc.collection_date else None
            ),
            "verified_by_user": ent.verified_by_user,
        }
        for ent, doc in result.all()
    ]


async def _fetch_selected_document_dicts(
    profile_db: AsyncSession, profile_id: str, doc_ids: list[str]
) -> list[dict]:
    """Filename/date metadata for the user-selected source documents."""
    if not doc_ids:
        return []
    result = await profile_db.execute(
        select(Document).where(
            Document.id.in_(doc_ids),
            Document.profile_id == profile_id,
        )
    )
    return [
        {
            "id": doc.id,
            "source": doc.source,
            "collection_date": doc.collection_date,
        }
        for doc in result.scalars().all()
    ]


def _compute_trends(observations: list[dict]) -> list[dict]:
    """
    Compute trend data from observations.

    Groups by analyte and calculates direction/change. Values are
    converted to a canonical unit (modules.normalize) before comparing
    across dates so cross-lab unit differences (e.g. mg/dL vs mmol/L)
    don't produce a spurious delta (NORM-UNIT-001). Observations whose
    unit can't be converted are excluded from the comparison; if the
    analyte isn't in the conversion table and its units are mixed, no
    trend is reported rather than comparing incompatible numbers.
    """
    # Group observations by analyte
    analyte_groups: dict[str, list[dict]] = {}
    for obs in observations:
        analyte = obs["analyte_canonical"]
        if analyte not in analyte_groups:
            analyte_groups[analyte] = []
        analyte_groups[analyte].append(obs)

    trends = []
    for analyte, obs_list in analyte_groups.items():
        # Sort by date
        sorted_obs = sorted(
            [o for o in obs_list if o.get("collected_at") and o.get("value") is not None],
            key=lambda x: x["collected_at"]
        )

        if len(sorted_obs) < 2:
            continue

        canonical_unit = canonical_unit_for(analyte)
        distinct_units = {
            normalize_unit(o["unit"]) for o in sorted_obs if o.get("unit")
        }

        if len(distinct_units) > 1:
            if canonical_unit is None:
                # Untabled analyte with mixed units: no safe basis for
                # comparison, don't report a trend.
                continue
            comparable_values = []
            for o in sorted_obs:
                conv = convert_to_canonical(analyte, o["value"], o.get("unit"))
                if conv is not None:
                    comparable_values.append(conv.canonical_value)
            if len(comparable_values) < 2:
                continue
        else:
            comparable_values = [o["value"] for o in sorted_obs]

        first_val = comparable_values[0]
        last_val = comparable_values[-1]

        if first_val == 0:
            continue

        delta_percent = ((last_val - first_val) / first_val) * 100

        if abs(delta_percent) < 5:
            direction = "stable"
        elif delta_percent > 0:
            direction = "up"
        else:
            direction = "down"

        trends.append({
            "analyte": analyte,
            "trend_direction": direction,
            "delta_percent": abs(delta_percent),
        })

    return trends


@router.post("/doctor-summary", response_model=SummaryResponse)
async def generate_doctor_summary(
    request: SummaryRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Generate a clinician-ready summary.

    Creates a 1-2 page summary with:
    - Key values and dates
    - Trend highlights
    - Abnormal values with context
    - Exact values and collection dates
    - Citations to source documents

    Creates audit log entry.
    Only includes data from the authenticated profile.
    """
    profile_id = session.profile_id
    local_today = to_local(
        utcnow(), await profile_timezone_name(profile_db, profile_id)
    ).date()

    # Fetch observations from profile database
    observations = await _fetch_observations(
        profile_db,
        profile_id,
        from_date=request.from_date,
        to_date=request.to_date,
    )

    # Compute trends
    trends = _compute_trends(observations) if request.include_trends else []

    questions: list[QuestionItem] = []
    if request.include_questions:
        export_module = ExportModule()
        generated_questions = export_module.generate_questions(
            observations=observations,
            trends=trends,
            today=local_today,
        )
        questions = [QuestionItem.from_prompt(q) for q in generated_questions]

    # Generate summary using ExportModule
    export_module = ExportModule()
    summary = await export_module.generate_doctor_summary(
        profile_id=profile_id,
        observations=observations,
        trends=trends,
        from_date=request.from_date,
        to_date=request.to_date,
        include_all_values=request.include_all_values,
        include_trends=request.include_trends,
    )

    # Store summary for later download
    summary_data = {
        "summary_id": summary.summary_id,
        "profile_id": profile_id,
        "generated_at": summary.generated_at.isoformat(),
        "format": request.format,
        "key_findings": summary.key_findings,
        "sections": [{"title": s.title, "content": s.content} for s in summary.sections],
        "total_observations": summary.total_observations,
        "abnormal_count": summary.abnormal_count,
        "critical_count": summary.critical_count,
        "questions": [q.model_dump() for q in questions],
    }
    # D3 (2026-09-27): the doctor summary goes to a third party. Strict
    # redaction runs BEFORE it is stored, so the preview below and every
    # download format (text/html/pdf render from the store) are redacted.
    summary_data = export_module.redact_summary_data(summary_data)
    # Profile-local generation day, added after redaction (a bare ISO date).
    summary_data["generated_on"] = local_today.isoformat()
    _prune_expired()
    created_at = core_time.utcnow()
    await _save_artifact(
        profile_db,
        artifact_id=summary.summary_id,
        kind="doctor_summary",
        profile_id=profile_id,
        payload=summary_data,  # the redacted copy; created_at below is not persisted
        session_jti=session.token_jti,
        session_exp=_session_exp(session),
        created_at=created_at,
    )

    # Create audit log
    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=profile_id,
        export_type="doctor_summary",
        details={
            "summary_id": summary.summary_id,
            "format": request.format,
            "observation_count": summary.total_observations,
            "question_count": len(questions),
            "redaction_count": summary_data["redaction_count"],
        },
    )
    await profile_db.commit()
    # Published to memory only after the audit row AND the vault row are committed.
    summary_data["created_at"] = created_at
    summary_data["session_jti"] = session.token_jti
    summary_data["session_exp"] = _session_exp(session)
    _summary_store[summary.summary_id] = summary_data

    # Build date range string
    date_range = "All time"
    if request.from_date and request.to_date:
        date_range = f"{request.from_date.strftime('%Y-%m-%d')} to {request.to_date.strftime('%Y-%m-%d')}"
    elif request.from_date:
        date_range = f"Since {request.from_date.strftime('%Y-%m-%d')}"
    elif request.to_date:
        date_range = f"Until {request.to_date.strftime('%Y-%m-%d')}"

    return SummaryResponse(
        summary_id=summary.summary_id,
        profile_id=profile_id,
        generated_at=summary.generated_at.isoformat(),
        format=request.format,
        key_findings=summary_data["key_findings"],
        abnormal_count=summary.abnormal_count,
        date_range=date_range,
    )


@router.get("/doctor-summary/{summary_id}/download")
async def download_summary(
    summary_id: str,
    session: RequireAuth,
    format: str = Query("text", description="Download format: text, html, or pdf"),
    omit_questions: bool = Query(
        False, description="Leave the questions out (patient unticked them after generating)"
    ),
    omit_trends: bool = Query(
        False, description="Leave the trends out (patient unticked them after generating)"
    ),
    master_db: AsyncSession = Depends(get_db),
    profile_db: ProfileDbSession = None,
):
    """
    Download a previously generated summary.

    Supports formats: text (default), html, pdf.
    Verifies the summary belongs to the authenticated profile.
    """
    validate_uuid(summary_id, "summary_id")

    # Retrieve from store
    summary_data = _summary_store.get(summary_id)
    if summary_data and _expired(summary_data):
        summary_data = None
    if not summary_data:  # backend restarted, or never in this process: read the vault
        loaded = await _load_artifact(profile_db, artifact_id=summary_id, kind="doctor_summary")
        if loaded:
            summary_data = {
                **loaded[1], "profile_id": loaded[0],
                "session_jti": loaded[2], "session_exp": loaded[3], "created_at": loaded[4],
            }

    if not summary_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found"
        )

    # Verify ownership
    if summary_data["profile_id"] != session.profile_id:
        await audit_denial(session.profile_id, "summary", master_db)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this summary"
        )
    if not await _bound_to_session(
        profile_db, summary_data, session, artifact_id=summary_id, store=_summary_store,
        master_db=master_db,
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found")

    # Log download
    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=session.profile_id,
        export_type="summary_download",
        details={"summary_id": summary_id, "format": format},
    )

    export_module = ExportModule()
    short_id = summary_id[:8]

    if omit_questions:
        # Render-time only: the stored summary keeps its questions. Nothing else is dropped.
        summary_data = {**summary_data, "questions": []}
    if omit_trends:
        # Render-time only, like omit_questions: match a fresh Generate with Trends off, which has
        # no trends section and no trend-sourced questions (owner answer EXPORT-TRENDS-QS).
        summary_data = {
            **summary_data,
            "sections": [
                s for s in summary_data["sections"] if s.get("title") != TRENDS_SECTION_TITLE
            ],
            "questions": [
                q for q in summary_data.get("questions", [])
                if not (isinstance(q, dict) and q.get("source_kind") == "trend")
            ],
        }

    if format == "html":
        html_content = export_module.render_html_summary(summary_data)
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="health_summary_{short_id}.html"'
            }
        )

    elif format == "pdf":
        try:
            pdf_bytes = export_module.render_pdf_summary(summary_data)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="health_summary_{short_id}.pdf"'
                }
            )
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=str(e),
            )

    else:
        # Default: text format
        lines = [
            "=" * 60,
            "HEALTH SUMMARY REPORT",
            "=" * 60,
            "",
            f"Generated: {summary_data['generated_at']}",
            f"Total Observations: {summary_data['total_observations']}",
            f"Abnormal Values: {summary_data['abnormal_count']}",
            f"Critical Values: {summary_data['critical_count']}",
            "",
        ]

        if summary_data["key_findings"]:
            lines.append("-" * 40)
            lines.append("KEY FINDINGS")
            lines.append("-" * 40)
            for finding in summary_data["key_findings"]:
                lines.append(f"  - {finding}")
            lines.append("")

        for section in summary_data["sections"]:
            lines.append("-" * 40)
            lines.append(section["title"].upper())
            lines.append("-" * 40)
            lines.append(section["content"])
            lines.append("")

        if summary_data.get("questions"):
            lines.append("-" * 40)
            lines.append("QUESTIONS FOR YOUR PROVIDER")
            lines.append("-" * 40)
            for q in summary_data["questions"]:
                q_text = q.get("question", "") if isinstance(q, dict) else str(q)
                if q_text:
                    lines.append(f"  - {q_text}")
            lines.append("")

        lines.append("=" * 60)
        lines.append("This summary was generated by Asclexis based on")
        lines.append("uploaded laboratory reports. This is not medical advice.")
        lines.append("Discuss all results with your healthcare provider.")
        lines.append("=" * 60)

        content = "\n".join(lines)

        return Response(
            content=content,
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="health_summary_{short_id}.txt"'
            }
        )


@router.post("/questions", response_model=list[QuestionItem])
async def generate_questions(
    session: RequireAuth,
    from_date: Optional[NaiveUtcDatetime] = Query(None, description="Start date"),
    to_date: Optional[NaiveUtcDatetime] = Query(None, description="End date"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Generate discussion prompts for clinician visits.

    User-initiated only. Framed as discussion prompts,
    not medical advice.
    Only includes data from the authenticated profile.

    HC-M17: besides abnormal values and trends, questions are derived from
    open/needs_review care-plan tasks and verified visit-note entities
    (medication changes, ordered tests, referrals), each tied to its source.
    """
    profile_id = session.profile_id
    local_today = to_local(
        utcnow(), await profile_timezone_name(profile_db, profile_id)
    ).date()

    # Fetch observations from profile database
    observations = await _fetch_observations(
        profile_db,
        profile_id,
        from_date=from_date,
        to_date=to_date,
    )

    # Compute trends
    trends = _compute_trends(observations)

    # HC-M17 sources: accepted care tasks + verified visit-note entities.
    care_tasks = await _fetch_care_task_dicts(profile_db)
    entities = await _fetch_question_entity_dicts(profile_db)

    # Generate questions using ExportModule
    export_module = ExportModule()
    questions = export_module.generate_questions(
        observations=observations,
        trends=trends,
        care_tasks=care_tasks,
        entities=entities,
        today=local_today,
    )

    # Log generation
    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=profile_id,
        export_type="questions",
        details={"question_count": len(questions)},
    )

    return [QuestionItem.from_prompt(q) for q in questions]


class VisitPrepRequest(BaseModel):
    """Request model for the visit-prep packet (HC-M18).

    confirm MUST be true — packet generation assembles personal health data
    into an exportable artifact, so it requires the same explicit user
    confirmation as the RL dataset export.
    """

    reason_for_visit: Optional[str] = None
    from_date: Optional[NaiveUtcDatetime] = None
    to_date: Optional[NaiveUtcDatetime] = None

    # Section include flags
    include_medications: bool = True
    include_labs: bool = True
    include_visits: bool = True
    include_tasks: bool = True
    include_questions: bool = True

    selected_doc_ids: Optional[list[str]] = None
    confirm: bool = False


class VisitPrepResponse(BaseModel):
    """Response model for visit-prep packet generation."""

    packet_id: str
    profile_id: str
    generated_at: str
    section_titles: list[str]
    markdown: str
    redaction_count: int


@router.post("/visit-prep", response_model=VisitPrepResponse)
async def generate_visit_prep(
    request: VisitPrepRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Generate a visit-prep packet (HC-M18).

    One exportable packet before an appointment: reason for visit, current
    medications, recent abnormal verified labs, verified visit/diagnosis
    mentions, open follow-up tasks, generated questions (HC-M17), and the
    selected source documents. Unverified data is excluded everywhere.

    Requires confirm=true. All content is redacted (strict policy) by the
    ExportModule before it is stored or downloadable. Creates an audit entry.
    """
    if request.confirm is not True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visit-prep export requires confirm=true in the request body.",
        )

    profile_id = session.profile_id
    for doc_id in request.selected_doc_ids or []:
        validate_uuid(doc_id, "selected_doc_ids entry")
    local_today = to_local(
        utcnow(), await profile_timezone_name(profile_db, profile_id)
    ).date()

    observations = None
    questions = None
    if request.include_labs or request.include_questions:
        fetched_observations = await _fetch_observations(
            profile_db,
            profile_id,
            from_date=request.from_date,
            to_date=request.to_date,
        )
        observations = fetched_observations if request.include_labs else None

    medications = (
        await _fetch_active_medication_dicts(profile_db, profile_id)
        if request.include_medications
        else None
    )
    visit_mentions = (
        await _fetch_visit_mention_dicts(
            profile_db, from_date=request.from_date, to_date=request.to_date
        )
        if request.include_visits
        else None
    )
    care_tasks = (
        await _fetch_care_task_dicts(profile_db)
        if request.include_tasks or request.include_questions
        else None
    )

    export_module = ExportModule()
    if request.include_questions:
        # Packet policy: unverified data is excluded — questions inside the
        # packet only draw on verified observations (and verified entities,
        # which generate_questions enforces itself). Content the user has
        # excluded from the packet (include_labs=False / include_tasks=False /
        # include_visits=False)
        # must not resurface as question inputs either.
        verified_observations = (
            [o for o in fetched_observations if o.get("user_verified")]
            if request.include_labs
            else []
        )
        questions_care_tasks = care_tasks if request.include_tasks else []
        question_entities = (
            await _fetch_question_entity_dicts(profile_db)
            if request.include_visits
            else []
        )
        questions = export_module.generate_questions(
            observations=verified_observations,
            trends=_compute_trends(verified_observations),
            care_tasks=questions_care_tasks,
            entities=question_entities,
            today=local_today,
        )

    selected_documents = (
        await _fetch_selected_document_dicts(
            profile_db, profile_id, request.selected_doc_ids
        )
        if request.selected_doc_ids
        else None
    )

    packet = export_module.compose_visit_prep_packet(
        profile_id=profile_id,
        reason_for_visit=request.reason_for_visit,
        medications=medications,
        observations=observations,
        visit_mentions=visit_mentions,
        care_tasks=care_tasks if request.include_tasks else None,
        questions=questions,
        selected_documents=selected_documents,
        today=local_today,
    )
    _prune_expired()
    created_at = core_time.utcnow()
    await _save_artifact(
        profile_db,
        artifact_id=packet["packet_id"],
        kind="visit_prep",
        profile_id=profile_id,
        payload=packet,
        session_jti=session.token_jti,
        session_exp=_session_exp(session),
        created_at=created_at,
    )

    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=profile_id,
        export_type="visit_prep",
        details={
            "packet_id": packet["packet_id"],
            # AUDIT-PHI-001: section titles are content-derived free text.
            "count": len(packet["sections"]),
            "redaction_count": packet["redaction_count"],
        },
    )
    await profile_db.commit()
    packet["created_at"] = created_at  # published only after both commits
    packet["session_jti"] = session.token_jti
    packet["session_exp"] = _session_exp(session)
    _packet_store[packet["packet_id"]] = packet

    return VisitPrepResponse(
        packet_id=packet["packet_id"],
        profile_id=profile_id,
        generated_at=packet["generated_at"],
        section_titles=[s["title"] for s in packet["sections"]],
        markdown=packet["markdown"],
        redaction_count=packet["redaction_count"],
    )


@router.get("/visit-prep/{packet_id}/download")
async def download_visit_prep(
    packet_id: str,
    session: RequireAuth,
    format: str = Query("markdown", description="Download format: markdown, html, or pdf"),
    master_db: AsyncSession = Depends(get_db),
    profile_db: ProfileDbSession = None,
):
    """
    Download a previously generated visit-prep packet.

    markdown is always available; html/pdf reuse the doctor-summary
    renderer (pdf requires WeasyPrint, 501 if not installed). Content was
    redacted at composition time, so every format is redacted.
    """
    validate_uuid(packet_id, "packet_id")

    packet = _packet_store.get(packet_id)
    if packet and _expired(packet):
        packet = None
    if not packet:
        loaded = await _load_artifact(profile_db, artifact_id=packet_id, kind="visit_prep")
        if loaded:
            packet = {
                **loaded[1], "profile_id": loaded[0],
                "session_jti": loaded[2], "session_exp": loaded[3], "created_at": loaded[4],
            }
    if not packet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit-prep packet not found",
        )

    if packet["profile_id"] != session.profile_id:
        await audit_denial(session.profile_id, "packet", master_db)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this packet",
        )
    if not await _bound_to_session(
        profile_db, packet, session, artifact_id=packet_id, store=_packet_store,
        master_db=master_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit-prep packet not found",
        )

    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=session.profile_id,
        export_type="visit_prep_download",
        details={"packet_id": packet_id, "format": format},
    )

    short_id = packet_id[:8]
    if format in ("html", "pdf"):
        export_module = ExportModule()
        # Reuse the existing doctor-summary renderer (no new dependency).
        summary_data = {
            "date_range": (
                "Visit Prep Packet — "
                f"{packet.get('generated_on') or packet['generated_at'][:10]}"
            ),
            "generated_on": packet.get("generated_on"),
            "key_findings": [],
            "sections": packet["sections"],
            "questions": [],  # already rendered as a packet section
        }
        if format == "html":
            return Response(
                content=export_module.render_html_summary(summary_data),
                media_type="text/html",
                headers={
                    "Content-Disposition": f'attachment; filename="visit_prep_{short_id}.html"'
                },
            )
        try:
            pdf_bytes = export_module.render_pdf_summary(summary_data)
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=str(e),
            )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="visit_prep_{short_id}.pdf"'
            },
        )

    # Default: markdown (always available)
    return Response(
        content=packet["markdown"],
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="visit_prep_{short_id}.md"'
        },
    )


@router.get("/csv")
async def export_csv(
    session: RequireAuth,
    analytes: Optional[str] = Query(None, description="Comma-separated analyte filter"),
    from_date: Optional[NaiveUtcDatetime] = Query(None, description="Start date"),
    to_date: Optional[NaiveUtcDatetime] = Query(None, description="End date"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Export observations as CSV.

    Only includes data from the authenticated profile.
    Creates audit log entry.
    """
    profile_id = session.profile_id

    # Parse analyte filter
    analyte_filter = None
    if analytes:
        analyte_filter = [a.strip().lower() for a in analytes.split(",")]

    # Fetch observations from profile database
    observations = await _fetch_observations(
        profile_db,
        profile_id,
        from_date=from_date,
        to_date=to_date,
        analyte_filter=analyte_filter,
    )

    # Generate CSV using ExportModule
    export_module = ExportModule()
    csv_content = export_module.export_csv(observations)

    # Log export
    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=profile_id,
        export_type="csv",
        details={"observation_count": len(observations)},
    )

    # Generate filename with date
    filename = f"health_data_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/json")
async def export_json(
    session: RequireAuth,
    analytes: Optional[str] = Query(None, description="Comma-separated analyte filter"),
    from_date: Optional[NaiveUtcDatetime] = Query(None, description="Start date"),
    to_date: Optional[NaiveUtcDatetime] = Query(None, description="End date"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Export observations as JSON.

    Only includes data from the authenticated profile.
    Creates audit log entry.
    """
    profile_id = session.profile_id

    # Parse analyte filter
    analyte_filter = None
    if analytes:
        analyte_filter = [a.strip().lower() for a in analytes.split(",")]

    # Fetch observations from profile database
    observations = await _fetch_observations(
        profile_db,
        profile_id,
        from_date=from_date,
        to_date=to_date,
        analyte_filter=analyte_filter,
    )

    # Generate JSON using ExportModule
    export_module = ExportModule()
    json_content = export_module.export_json(observations)

    # Log export
    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=profile_id,
        export_type="json",
        details={"observation_count": len(observations)},
    )

    # Generate filename with date
    filename = f"health_data_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"

    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# ---------------------------------------------------------------------------
# FHIR R4 export (HC-M22)
# ---------------------------------------------------------------------------


async def _fetch_all_medication_dicts(
    profile_db: AsyncSession, profile_id: str
) -> list[dict]:
    """All medications (active and inactive) for the FHIR export."""
    result = await profile_db.execute(
        select(Medication).where(Medication.profile_id == profile_id)
    )
    return [
        {
            "id": med.id,
            "name": med.name,
            "generic_name": med.generic_name,
            "dosage_amount": med.dosage_amount,
            "dosage_unit": med.dosage_unit,
            "dosage_form": med.dosage_form,
            "frequency": med.frequency,
            "instructions": med.instructions,
            "is_active": med.is_active,
            "started_at": med.started_at,
            "ended_at": med.ended_at,
        }
        for med in result.scalars().all()
    ]


async def _fetch_document_dicts_for_fhir(
    profile_db: AsyncSession, profile_id: str
) -> list[dict]:
    """Document metadata + category for the FHIR export (no binary content)."""
    result = await profile_db.execute(
        select(Document).where(Document.profile_id == profile_id)
    )
    documents = result.scalars().all()
    doc_ids = [doc.id for doc in documents]

    categories: dict[str, str] = {}
    if doc_ids:
        cat_result = await profile_db.execute(
            select(DocumentCategory).where(DocumentCategory.doc_id.in_(doc_ids))
        )
        categories = {cat.doc_id: cat.category for cat in cat_result.scalars().all()}

    return [
        {
            "id": doc.id,
            "category": categories.get(doc.id),
            "collection_date": doc.collection_date,
            "imported_at": doc.imported_at,
            "metadata_json": doc.metadata_json,
        }
        for doc in documents
    ]


async def _fetch_fhir_entity_dicts(profile_db: AsyncSession) -> list[dict]:
    """Verified entities that can feed Condition/Encounter/DiagnosticReport.

    Unreviewed (null) and rejected (False) entities are never fetched —
    the unverified-data policy is enforced here, not just in fhir_export.py.
    """
    result = await profile_db.execute(
        select(DocumentEntity).where(
            DocumentEntity.entity_type.in_(FHIR_ENTITY_TYPES),
            DocumentEntity.verified_by_user.is_(True),
        )
    )
    return [
        {
            "id": ent.id,
            "doc_id": ent.doc_id,
            "entity_type": ent.entity_type,
            "entity_value": ent.entity_value,
            "quote": ent.quote,
            "verified_by_user": ent.verified_by_user,
        }
        for ent in result.scalars().all()
    ]


async def _fetch_care_task_dicts_for_fhir(profile_db: AsyncSession) -> list[dict]:
    """All care-plan tasks (every status) for the CarePlan resource.

    Care-plan tasks are user-accepted by construction (HC-M15); "ignored"
    tasks are included here and excluded inside modules/fhir_export.py so
    the exclusion rule lives in one place.
    """
    result = await profile_db.execute(select(CarePlanTask))
    return [
        {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "due_date": task.due_date,
            "source_quote": task.source_quote,
        }
        for task in result.scalars().all()
    ]


class FhirExportRequest(BaseModel):
    """Request model for the FHIR R4 export (HC-M22).

    confirm MUST be true — the export assembles personal health data into
    an exportable artifact, so it requires the same explicit user
    confirmation as the visit-prep packet and RL dataset export.
    """

    confirm: bool = False
    include_documents: bool = True
    include_medications: bool = True
    include_observations: bool = True
    include_conditions: bool = True
    include_care_plan: bool = True
    include_encounters: bool = True
    include_reports: bool = True


class FhirExportResponse(BaseModel):
    """Response model for FHIR R4 export generation."""

    export_id: str
    profile_id: str
    generated_at: str
    resource_counts: dict[str, int]
    redaction_count: int


@router.post("/fhir", response_model=FhirExportResponse)
async def generate_fhir_export(
    request: FhirExportRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Generate a FHIR R4 export Bundle (HC-M22).

    Export-only (no import), file-based, local-first — no network calls.
    Requires confirm=true. Only user-verified observations and verified
    document entities are included (matching the HC-M18 unverified-data
    exclusion policy); medications and accepted care-plan tasks are
    user-entered/accepted, so they are included as metadata. All free-text
    content is redacted (strict policy) before the bundle is stored, and
    the generation is audit-logged.
    """
    if request.confirm is not True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FHIR export requires confirm=true in the request body.",
        )

    profile_id = session.profile_id

    profile_result = await master_db.execute(
        select(Profile).where(Profile.id == profile_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    observations = (
        await _fetch_observations(profile_db, profile_id)
        if request.include_observations
        else []
    )
    medications = (
        await _fetch_all_medication_dicts(profile_db, profile_id)
        if request.include_medications
        else []
    )
    documents = (
        await _fetch_document_dicts_for_fhir(profile_db, profile_id)
        if (request.include_documents or request.include_encounters or request.include_reports)
        else []
    )
    entities = (
        await _fetch_fhir_entity_dicts(profile_db)
        if (request.include_conditions or request.include_encounters or request.include_reports)
        else []
    )
    care_tasks = (
        await _fetch_care_task_dicts_for_fhir(profile_db)
        if request.include_care_plan
        else []
    )

    result = build_fhir_bundle(
        profile.display_name,
        observations,
        medications,
        documents,
        entities,
        care_tasks,
        include_observations=request.include_observations,
        include_medications=request.include_medications,
        include_conditions=request.include_conditions,
        include_documents=request.include_documents,
        include_encounters=request.include_encounters,
        include_care_plan=request.include_care_plan,
        include_reports=request.include_reports,
    )

    export_id = str(uuid.uuid4())
    _prune_expired()
    created_at = core_time.utcnow()
    await _save_artifact(
        profile_db,
        artifact_id=export_id,
        kind="fhir_r4",
        profile_id=profile_id,
        payload=result["bundle"],
        session_jti=session.token_jti,
        session_exp=_session_exp(session),
        created_at=created_at,
    )

    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=profile_id,
        export_type="fhir_r4",
        details={
            "export_id": export_id,
            "resource_counts": result["resource_counts"],
            "redaction_count": result["redaction_count"],
        },
    )
    await profile_db.commit()
    _fhir_store[export_id] = {  # published only after both commits
        "profile_id": profile_id,
        "bundle": result["bundle"],
        "created_at": created_at,
        "session_jti": session.token_jti,
        "session_exp": _session_exp(session),
    }

    return FhirExportResponse(
        export_id=export_id,
        profile_id=profile_id,
        generated_at=result["bundle"]["timestamp"],
        resource_counts=result["resource_counts"],
        redaction_count=result["redaction_count"],
    )


@router.get("/fhir/{export_id}/download")
async def download_fhir_export(
    export_id: str,
    session: RequireAuth,
    master_db: AsyncSession = Depends(get_db),
    profile_db: ProfileDbSession = None,
):
    """
    Download a previously generated FHIR R4 export as a Bundle JSON file.

    Content was redacted at generation time, so the download is already
    safe to hand to another system. Creates an audit entry.
    """
    validate_uuid(export_id, "export_id")

    stored = _fhir_store.get(export_id)
    if stored and _expired(stored):
        stored = None
    if not stored:
        loaded = await _load_artifact(profile_db, artifact_id=export_id, kind="fhir_r4")
        if loaded:
            stored = {
                "profile_id": loaded[0], "bundle": loaded[1],
                "session_jti": loaded[2], "session_exp": loaded[3], "created_at": loaded[4],
            }
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FHIR export not found",
        )

    if stored["profile_id"] != session.profile_id:
        await audit_denial(session.profile_id, "export", master_db)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this export",
        )
    if not await _bound_to_session(
        profile_db, stored, session, artifact_id=export_id, store=_fhir_store,
        master_db=master_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FHIR export not found",
        )

    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=session.profile_id,
        export_type="fhir_r4_download",
        details={"export_id": export_id},
    )

    short_id = export_id[:8]
    return Response(
        content=json.dumps(stored["bundle"], indent=2),
        media_type="application/fhir+json",
        headers={
            "Content-Disposition": f'attachment; filename="fhir_export_{short_id}.json"'
        },
    )
