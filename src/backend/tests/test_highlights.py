"""HC-M16 smart-highlight tests (HC-HLT-NNN).

Highlights are small organizational tags derived on read from existing
verified data structures (observations and document entities) — no new
tables, no LLM, no interpretation. Every highlight resolves to a source
row (source_kind + source_id) and rejected entities never produce any
highlight.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth import Session
from core.profile_database import ProfileDatabaseBase
from core.time import utcnow
from models import Document, Observation
from models.document_category import DocumentEntity
from modules.highlights import (
    LOW_CONFIDENCE_THRESHOLD,
    derive_entity_highlights,
    derive_highlights,
    derive_observation_highlights,
)


# ---------------------------------------------------------------------------
# Shared helpers (style matches tests/test_care_tasks.py)
# ---------------------------------------------------------------------------


def _make_session(profile_id: str = "test-profile") -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="Test Profile",
        expires_at=utcnow() + timedelta(hours=1),
    )


def _make_entity(doc_id: str, **overrides) -> DocumentEntity:
    fields = dict(
        id=str(uuid.uuid4()),
        doc_id=doc_id,
        category="visit_notes",
        entity_type="follow_up_instruction",
        entity_value="follow-up in 4 weeks",
        confidence=0.75,
        source_page=None,
        char_start=0,
        char_end=20,
        quote="follow-up in 4 weeks",
        verified_by_user=None,
        extraction_version="rule-v2",
    )
    fields.update(overrides)
    return DocumentEntity(**fields)


def _make_observation(doc_id: str, **overrides) -> Observation:
    fields = dict(
        id=str(uuid.uuid4()),
        profile_id="test-profile",
        doc_id=doc_id,
        analyte_canonical="hemoglobin",
        analyte_raw="Hemoglobin",
        value=10.2,
        unit="g/dL",
        ref_low=12.0,
        ref_high=16.0,
        flag="L",
        is_abnormal=True,
        extraction_confidence=0.9,
        user_verified=False,
    )
    fields.update(overrides)
    return Observation(**fields)


def _types(highlights) -> set[str]:
    return {h.highlight_type for h in highlights}


# ---------------------------------------------------------------------------
# Derivation matrix — observations
# ---------------------------------------------------------------------------


class TestObservationDerivation:
    def test_hc_hlt_001_abnormal_observation_yields_abnormal_value(self):
        doc_id = str(uuid.uuid4())
        obs = _make_observation(doc_id, is_abnormal=True, user_verified=True)
        highlights = derive_observation_highlights([obs])
        assert len(highlights) == 1
        h = highlights[0]
        assert h.highlight_type == "abnormal_value"
        assert h.doc_id == doc_id
        assert h.source_kind == "observation"
        assert h.source_id == obs.id
        assert h.quote is None
        assert h.confidence == obs.extraction_confidence
        assert h.verification_state == "verified"

    def test_hc_hlt_002_in_range_observations_yield_nothing(self):
        doc_id = str(uuid.uuid4())
        in_range = _make_observation(
            doc_id, value=13.5, flag=None, is_abnormal=False
        )
        unknown = _make_observation(
            doc_id, value=13.5, flag=None, is_abnormal=None
        )
        assert derive_observation_highlights([in_range, unknown]) == []

    def test_hc_hlt_003_unverified_observation_state(self):
        doc_id = str(uuid.uuid4())
        obs = _make_observation(doc_id, is_abnormal=True, user_verified=False)
        (h,) = derive_observation_highlights([obs])
        assert h.verification_state == "unverified"


# ---------------------------------------------------------------------------
# Derivation matrix — entities
# ---------------------------------------------------------------------------


class TestEntityDerivation:
    def _single_type_highlight(self, entity):
        """Derive for a verified entity so only the type-based rule fires."""
        highlights = derive_entity_highlights([entity])
        assert len(highlights) == 1
        return highlights[0]

    def test_hc_hlt_004_medication_start_verb_yields_medication_started(self):
        doc_id = str(uuid.uuid4())
        ent = _make_entity(
            doc_id,
            entity_type="medication_change",
            entity_value="start lisinopril 10 mg daily",
            quote="Start Lisinopril 10 mg daily",
            verified_by_user=True,
        )
        h = self._single_type_highlight(ent)
        assert h.highlight_type == "medication_started"
        assert h.source_kind == "entity"
        assert h.source_id == ent.id
        assert h.quote == "Start Lisinopril 10 mg daily"
        assert h.confidence == ent.confidence
        assert h.verification_state == "verified"

    def test_hc_hlt_005_medication_stop_verb_yields_medication_stopped(self):
        doc_id = str(uuid.uuid4())
        ent = _make_entity(
            doc_id,
            entity_type="medication_change",
            entity_value="stop metformin",
            quote="Discontinued metformin",
            verified_by_user=True,
        )
        assert self._single_type_highlight(ent).highlight_type == "medication_stopped"

    @pytest.mark.parametrize(
        "value",
        [
            "increase atorvastatin to 40 mg",
            "decrease levothyroxine",
            "change to losartan 50 mg",
            "continue aspirin 81 mg",
        ],
    )
    def test_hc_hlt_006_other_medication_verbs_yield_medication_changed(self, value):
        doc_id = str(uuid.uuid4())
        ent = _make_entity(
            doc_id,
            entity_type="medication_change",
            entity_value=value,
            quote=value,
            verified_by_user=True,
        )
        assert self._single_type_highlight(ent).highlight_type == "medication_changed"

    @pytest.mark.parametrize(
        "entity_type,expected",
        [
            ("follow_up_instruction", "follow_up_needed"),
            ("test_ordered", "test_ordered"),
            ("referral", "referral_created"),
            ("diagnoses", "new_diagnosis_mentioned"),
        ],
    )
    def test_hc_hlt_007_type_mapped_highlights(self, entity_type, expected):
        doc_id = str(uuid.uuid4())
        ent = _make_entity(
            doc_id,
            entity_type=entity_type,
            entity_value="some extracted value",
            quote="some extracted value",
            verified_by_user=True,
        )
        assert self._single_type_highlight(ent).highlight_type == expected

    def test_hc_hlt_008_low_confidence_below_threshold_only(self):
        doc_id = str(uuid.uuid4())
        low = _make_entity(
            doc_id, entity_type="finding", confidence=0.59, verified_by_user=True
        )
        at_threshold = _make_entity(
            doc_id,
            entity_type="finding",
            confidence=LOW_CONFIDENCE_THRESHOLD,
            verified_by_user=True,
        )
        assert _types(derive_entity_highlights([low])) == {"low_confidence_extraction"}
        assert derive_entity_highlights([at_threshold]) == []

    def test_hc_hlt_009_unreviewed_entity_yields_needs_verification(self):
        doc_id = str(uuid.uuid4())
        unreviewed = _make_entity(
            doc_id, entity_type="finding", confidence=0.9, verified_by_user=None
        )
        highlights = derive_entity_highlights([unreviewed])
        assert _types(highlights) == {"needs_verification"}
        assert highlights[0].verification_state == "unreviewed"

    def test_hc_hlt_010_verified_entity_has_no_needs_verification(self):
        doc_id = str(uuid.uuid4())
        verified = _make_entity(
            doc_id,
            entity_type="test_ordered",
            confidence=0.9,
            verified_by_user=True,
        )
        assert _types(derive_entity_highlights([verified])) == {"test_ordered"}

    def test_hc_hlt_011_rejected_entity_produces_no_highlights_at_all(self):
        doc_id = str(uuid.uuid4())
        rejected = _make_entity(
            doc_id,
            entity_type="medication_change",
            entity_value="start lisinopril",
            confidence=0.3,  # would otherwise be low-confidence too
            verified_by_user=False,
        )
        assert derive_entity_highlights([rejected]) == []

    def test_hc_hlt_012_one_entity_can_produce_multiple_highlights(self):
        doc_id = str(uuid.uuid4())
        ent = _make_entity(
            doc_id,
            entity_type="medication_change",
            entity_value="start lisinopril 10 mg",
            confidence=0.5,
            verified_by_user=None,
        )
        highlights = derive_entity_highlights([ent])
        assert _types(highlights) == {
            "medication_started",
            "low_confidence_extraction",
            "needs_verification",
        }
        # Every highlight resolves to the same source entity.
        assert {h.source_id for h in highlights} == {ent.id}
        assert {h.source_kind for h in highlights} == {"entity"}

    def test_hc_hlt_013_unmapped_entity_types_get_no_type_highlight(self):
        doc_id = str(uuid.uuid4())
        for entity_type in ("visit_date", "finding", "warning_sign", "diagnosis"):
            ent = _make_entity(
                doc_id, entity_type=entity_type, confidence=0.9, verified_by_user=True
            )
            assert derive_entity_highlights([ent]) == [], entity_type

    def test_hc_hlt_014_combined_derivation_covers_both_sources(self):
        doc_id = str(uuid.uuid4())
        obs = _make_observation(doc_id, is_abnormal=True)
        ent = _make_entity(doc_id, entity_type="referral", verified_by_user=True)
        highlights = derive_highlights([ent], [obs])
        assert _types(highlights) == {"abnormal_value", "referral_created"}


# ---------------------------------------------------------------------------
# API endpoints (real in-memory profile DB; audit mocked on the master DB)
# ---------------------------------------------------------------------------

from api.documents import (  # noqa: E402
    DocumentHighlightSummary,
    HighlightResponse,
    get_document_highlights,
    get_highlights_summary,
)


@pytest_asyncio.fixture
async def real_profile_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _make_document(
    doc_id: str,
    profile_id: str = "test-profile",
    imported_at: datetime | None = None,
) -> Document:
    return Document(
        id=doc_id,
        profile_id=profile_id,
        path_hash="x" * 64,
        content_hash=str(uuid.uuid4()),
        doc_type="lab_pdf",
        source="report.pdf",
        status="parsed",
        imported_at=imported_at or datetime(2026, 6, 1, 12, 0, 0),
    )


class TestDocumentHighlightsEndpoint:
    @pytest.mark.asyncio
    async def test_hc_hlt_015_returns_highlights_and_audits(
        self, real_profile_db, monkeypatch
    ):
        db = real_profile_db
        doc_id = str(uuid.uuid4())
        db.add(_make_document(doc_id))
        ent = _make_entity(
            doc_id,
            entity_type="medication_change",
            entity_value="start lisinopril 10 mg",
            verified_by_user=None,
        )
        db.add(ent)
        obs = _make_observation(doc_id, is_abnormal=True)
        db.add(obs)
        await db.commit()

        master_db = AsyncMock()
        audit_mock = AsyncMock()
        monkeypatch.setattr("api.documents.log_document_event", audit_mock)

        result = await get_document_highlights(doc_id, _make_session(), db, master_db)

        assert all(isinstance(h, HighlightResponse) for h in result)
        assert {h.highlight_type for h in result} == {
            "abnormal_value",
            "medication_started",
            "needs_verification",
        }
        by_type = {h.highlight_type: h for h in result}
        assert by_type["abnormal_value"].source_kind == "observation"
        assert by_type["abnormal_value"].source_id == obs.id
        assert by_type["medication_started"].source_id == ent.id
        assert by_type["medication_started"].doc_id == doc_id

        # Audit row written on the master DB and committed (fail-closed view).
        audit_mock.assert_awaited_once()
        kwargs = audit_mock.await_args.kwargs
        assert kwargs["event"] == "view"
        assert kwargs["profile_id"] == "test-profile"
        assert kwargs["document_id"] == doc_id
        assert kwargs["details"]["action"] == "highlights"
        master_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_hc_hlt_016_rejected_entities_excluded_via_endpoint(
        self, real_profile_db, monkeypatch
    ):
        db = real_profile_db
        doc_id = str(uuid.uuid4())
        db.add(_make_document(doc_id))
        db.add(
            _make_entity(
                doc_id,
                entity_type="referral",
                entity_value="cardiology",
                verified_by_user=False,
            )
        )
        await db.commit()

        monkeypatch.setattr("api.documents.log_document_event", AsyncMock())
        result = await get_document_highlights(
            doc_id, _make_session(), db, AsyncMock()
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_hc_hlt_017_404_when_document_missing(self, real_profile_db):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_document_highlights(
                str(uuid.uuid4()), _make_session(), real_profile_db, AsyncMock()
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_hc_hlt_018_403_when_wrong_profile(self, real_profile_db):
        from fastapi import HTTPException

        db = real_profile_db
        doc_id = str(uuid.uuid4())
        db.add(_make_document(doc_id, profile_id="other-profile"))
        await db.commit()

        with pytest.raises(HTTPException) as exc_info:
            await get_document_highlights(
                doc_id, _make_session("test-profile"), db, AsyncMock()
            )
        assert exc_info.value.status_code == 403


class TestHighlightsSummaryEndpoint:
    @pytest.mark.asyncio
    async def test_hc_hlt_019_summary_counts_per_recent_document(
        self, real_profile_db, monkeypatch
    ):
        db = real_profile_db
        doc_a = str(uuid.uuid4())  # newest
        doc_b = str(uuid.uuid4())
        db.add(_make_document(doc_a, imported_at=datetime(2026, 6, 2)))
        db.add(_make_document(doc_b, imported_at=datetime(2026, 6, 1)))
        # doc_a: two abnormal observations + one unreviewed referral entity
        db.add(_make_observation(doc_a, is_abnormal=True))
        db.add(_make_observation(doc_a, is_abnormal=True, analyte_canonical="tsh"))
        db.add(_make_entity(doc_a, entity_type="referral", verified_by_user=None))
        # doc_b: one rejected entity only -> no highlights, omitted entirely
        db.add(_make_entity(doc_b, entity_type="test_ordered", verified_by_user=False))
        await db.commit()

        master_db = AsyncMock()
        audit_mock = AsyncMock()
        monkeypatch.setattr("api.documents.log_document_event", audit_mock)

        result = await get_highlights_summary(_make_session(), 20, db, master_db)

        assert all(isinstance(s, DocumentHighlightSummary) for s in result)
        assert [s.doc_id for s in result] == [doc_a]
        assert result[0].counts == {
            "abnormal_value": 2,
            "referral_created": 1,
            "needs_verification": 1,
        }

        audit_mock.assert_awaited_once()
        kwargs = audit_mock.await_args.kwargs
        assert kwargs["event"] == "view"
        assert kwargs["profile_id"] == "test-profile"
        assert kwargs["details"]["action"] == "highlights_summary"
        master_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_hc_hlt_020_summary_is_bounded_by_limit(
        self, real_profile_db, monkeypatch
    ):
        db = real_profile_db
        doc_ids = []
        for day in (1, 2, 3):
            doc_id = str(uuid.uuid4())
            doc_ids.append(doc_id)
            db.add(_make_document(doc_id, imported_at=datetime(2026, 6, day)))
            db.add(_make_observation(doc_id, is_abnormal=True))
        await db.commit()

        monkeypatch.setattr("api.documents.log_document_event", AsyncMock())
        result = await get_highlights_summary(_make_session(), 2, db, AsyncMock())

        # Only the 2 most recently imported documents are summarized.
        assert [s.doc_id for s in result] == [doc_ids[2], doc_ids[1]]

    @pytest.mark.asyncio
    async def test_hc_hlt_021_summary_scoped_to_session_profile(
        self, real_profile_db, monkeypatch
    ):
        db = real_profile_db
        mine = str(uuid.uuid4())
        other = str(uuid.uuid4())
        db.add(_make_document(mine, profile_id="test-profile"))
        db.add(_make_document(other, profile_id="other-profile"))
        db.add(_make_observation(mine, is_abnormal=True))
        db.add(
            _make_observation(other, profile_id="other-profile", is_abnormal=True)
        )
        await db.commit()

        monkeypatch.setattr("api.documents.log_document_event", AsyncMock())
        result = await get_highlights_summary(_make_session(), 20, db, AsyncMock())

        assert [s.doc_id for s in result] == [mine]

    def test_hc_hlt_022_summary_limit_is_declared_bounded(self):
        """The limit query parameter must carry server-side bounds so the
        summary query stays bounded regardless of client input."""
        import inspect

        from annotated_types import Ge, Le

        sig = inspect.signature(get_highlights_summary)
        limit_default = sig.parameters["limit"].default

        ge = getattr(limit_default, "ge", None)
        le = getattr(limit_default, "le", None)
        for constraint in getattr(limit_default, "metadata", []):
            if isinstance(constraint, Ge):
                ge = constraint.ge
            if isinstance(constraint, Le):
                le = constraint.le

        assert le is not None and le <= 100
        assert ge == 1
