"""HC-M19 medication reconciliation tests (HC-MREC-NNN).

A document's medication_change entities are compared against the profile's
medication list, computed on read. The feature ONLY reports differences in
record-keeping language ("the note says X / your list has Y"); it never
writes to the medication list, never invents drug names, and never produces
advice wording. Applying a change happens exclusively through the existing
medications endpoints, initiated by the user.
"""

from __future__ import annotations

import re
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth import Session
from core.time import utcnow
from models.document_category import DocumentEntity
from models.medication import Medication
from modules.med_reconcile import (
    MAX_SUGGESTIONS,
    SUGGESTION_TYPES,
    derive_reconciliation_suggestions,
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


def _make_document(doc_id: str, profile_id: str = "test-profile") -> MagicMock:
    doc = MagicMock()
    doc.id = doc_id
    doc.profile_id = profile_id
    doc.source = "visit-note.pdf"
    return doc


def _med_entity(doc_id: str, value: str, **overrides) -> DocumentEntity:
    fields = dict(
        id=str(uuid.uuid4()),
        doc_id=doc_id,
        category="visit_notes",
        entity_type="medication_change",
        entity_value=value,
        confidence=0.8,
        source_page=None,
        char_start=0,
        char_end=len(value),
        quote=value,
        verified_by_user=None,
        extraction_version="rule-v2",
    )
    fields.update(overrides)
    return DocumentEntity(**fields)


def _medication(name: str, **overrides) -> Medication:
    fields = dict(
        id=str(uuid.uuid4()),
        profile_id="test-profile",
        name=name,
        generic_name=None,
        dosage_amount=10.0,
        dosage_unit="mg",
        dosage_form="tablet",
        frequency="once_daily",
        is_active=True,
        reminder_enabled=False,
        started_at=datetime(2026, 1, 1),
    )
    fields.update(overrides)
    return Medication(**fields)


DOC_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Suggestion types from seeded fixtures
# ---------------------------------------------------------------------------


class TestSuggestionTypes:
    def test_hc_mrec_001_start_of_unlisted_drug_is_new_medication(self):
        entities = [_med_entity(DOC_ID, "start metformin 500 mg twice daily")]
        meds = [_medication("atorvastatin")]
        suggestions = derive_reconciliation_suggestions(entities, meds)
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["suggestion_type"] == "new_medication"
        assert s["matched_medication_id"] is None
        assert s["current_list_summary"] == "not on your list"
        assert s["drug_name"] == "metformin"
        assert s["source_entity_id"] == entities[0].id
        assert s["source_quote"] == entities[0].quote
        assert s["entity_value"] == entities[0].entity_value

    def test_hc_mrec_002_stop_of_active_listed_drug_is_stopped_medication(self):
        med = _medication("Lisinopril", dosage_amount=20.0)
        entities = [_med_entity(DOC_ID, "stop lisinopril")]
        suggestions = derive_reconciliation_suggestions(entities, [med])
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["suggestion_type"] == "stopped_medication"
        assert s["matched_medication_id"] == med.id
        assert "lisinopril" in s["current_list_summary"].lower()
        assert "20" in s["current_list_summary"]
        assert "mg" in s["current_list_summary"]
        assert "once daily" in s["current_list_summary"]

    @pytest.mark.parametrize(
        "value",
        [
            "increase atorvastatin to 40 mg",
            "decrease atorvastatin to 5 mg",
            "change to atorvastatin 20 mg nightly",
        ],
    )
    def test_hc_mrec_003_dose_or_frequency_change_for_listed_drug(self, value):
        med = _medication("atorvastatin")
        suggestions = derive_reconciliation_suggestions(
            [_med_entity(DOC_ID, value)], [med]
        )
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["suggestion_type"] == "dose_or_frequency_change"
        assert s["matched_medication_id"] == med.id
        assert "atorvastatin" in s["current_list_summary"]

    def test_hc_mrec_004_start_of_active_listed_drug_is_possible_duplicate(self):
        med = _medication("Metformin", dosage_amount=500.0, frequency="twice_daily")
        suggestions = derive_reconciliation_suggestions(
            [_med_entity(DOC_ID, "start metformin 500 mg twice daily")], [med]
        )
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["suggestion_type"] == "possible_duplicate"
        assert s["matched_medication_id"] == med.id
        assert "twice daily" in s["current_list_summary"]

    def test_hc_mrec_005_start_matching_inactive_med_is_new_medication(self):
        med = _medication("metformin", is_active=False)
        suggestions = derive_reconciliation_suggestions(
            [_med_entity(DOC_ID, "start metformin 500 mg")], [med]
        )
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["suggestion_type"] == "new_medication"
        assert s["matched_medication_id"] == med.id
        assert "inactive" in s["current_list_summary"]

    def test_hc_mrec_006_continue_of_active_listed_drug_is_agreement_no_suggestion(self):
        med = _medication("levothyroxine")
        suggestions = derive_reconciliation_suggestions(
            [_med_entity(DOC_ID, "continue levothyroxine 50 mcg daily")], [med]
        )
        assert suggestions == []

    def test_hc_mrec_007_continue_of_unlisted_drug_is_new_medication(self):
        suggestions = derive_reconciliation_suggestions(
            [_med_entity(DOC_ID, "continue levothyroxine 50 mcg daily")], []
        )
        assert len(suggestions) == 1
        assert suggestions[0]["suggestion_type"] == "new_medication"
        assert suggestions[0]["current_list_summary"] == "not on your list"

    def test_hc_mrec_008_stop_of_already_inactive_med_yields_nothing(self):
        med = _medication("lisinopril", is_active=False)
        suggestions = derive_reconciliation_suggestions(
            [_med_entity(DOC_ID, "stop lisinopril")], [med]
        )
        assert suggestions == []

    def test_hc_mrec_009_generic_name_matches_brand_entry(self):
        med = _medication("Lipitor", generic_name="atorvastatin")
        suggestions = derive_reconciliation_suggestions(
            [_med_entity(DOC_ID, "start atorvastatin 10 mg")], [med]
        )
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["suggestion_type"] == "possible_duplicate"
        assert s["matched_medication_id"] == med.id


# ---------------------------------------------------------------------------
# Unclear: never guess
# ---------------------------------------------------------------------------


class TestUnclear:
    def test_hc_mrec_010_ambiguous_match_is_unclear_with_reason(self):
        meds = [
            _medication("metoprolol tartrate"),
            _medication("metoprolol succinate"),
        ]
        suggestions = derive_reconciliation_suggestions(
            [_med_entity(DOC_ID, "increase metoprolol to 100 mg")], meds
        )
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["suggestion_type"] == "unclear"
        assert s["matched_medication_id"] is None
        assert s["reason"]
        assert "metoprolol tartrate" in s["reason"]
        assert "metoprolol succinate" in s["reason"]

    def test_hc_mrec_011_multi_token_entity_disambiguates_similar_names(self):
        tartrate = _medication("metoprolol tartrate")
        succinate = _medication("metoprolol succinate")
        suggestions = derive_reconciliation_suggestions(
            [_med_entity(DOC_ID, "increase metoprolol succinate to 100 mg")],
            [tartrate, succinate],
        )
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["suggestion_type"] == "dose_or_frequency_change"
        assert s["matched_medication_id"] == succinate.id

    @pytest.mark.parametrize(
        "value",
        ["stop hydrochlorothiazide", "increase amlodipine to 10 mg"],
    )
    def test_hc_mrec_012_stop_or_change_of_unlisted_drug_is_unclear(self, value):
        suggestions = derive_reconciliation_suggestions(
            [_med_entity(DOC_ID, value)], [_medication("atorvastatin")]
        )
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["suggestion_type"] == "unclear"
        assert s["matched_medication_id"] is None
        assert s["reason"]

    def test_hc_mrec_013_no_readable_drug_name_is_unclear(self):
        # Only dose/frequency words after the action verb.
        suggestions = derive_reconciliation_suggestions(
            [_med_entity(DOC_ID, "increase to 500 mg twice daily")], []
        )
        assert len(suggestions) == 1
        assert suggestions[0]["suggestion_type"] == "unclear"
        assert suggestions[0]["drug_name"] is None

    def test_hc_mrec_014_unrecognized_action_verb_is_unclear(self):
        suggestions = derive_reconciliation_suggestions(
            [_med_entity(DOC_ID, "consider metformin 500 mg")], []
        )
        assert len(suggestions) == 1
        assert suggestions[0]["suggestion_type"] == "unclear"


# ---------------------------------------------------------------------------
# Entity filtering
# ---------------------------------------------------------------------------


class TestEntityFiltering:
    def test_hc_mrec_015_rejected_entities_are_excluded(self):
        entities = [
            _med_entity(DOC_ID, "start metformin 500 mg"),
            _med_entity(DOC_ID, "stop lisinopril", verified_by_user=False),
        ]
        suggestions = derive_reconciliation_suggestions(
            entities, [_medication("lisinopril")]
        )
        assert len(suggestions) == 1
        assert suggestions[0]["source_entity_id"] == entities[0].id

    def test_hc_mrec_016_verified_and_unreviewed_entities_are_included(self):
        entities = [
            _med_entity(DOC_ID, "start metformin 500 mg", verified_by_user=True),
            _med_entity(DOC_ID, "start amlodipine 5 mg", verified_by_user=None),
        ]
        suggestions = derive_reconciliation_suggestions(entities, [])
        assert len(suggestions) == 2

    def test_hc_mrec_017_non_medication_change_entities_are_ignored(self):
        entities = [
            _med_entity(DOC_ID, "repeat CBC in 4 weeks", entity_type="test_ordered"),
            _med_entity(DOC_ID, "call if fever", entity_type="warning_sign"),
            _med_entity(DOC_ID, "04/02/2026", entity_type="visit_date"),
        ]
        assert derive_reconciliation_suggestions(entities, []) == []


# ---------------------------------------------------------------------------
# Safety properties: no fabrication, no advice wording
# ---------------------------------------------------------------------------

# Wording the app must never generate anywhere in this feature.
FORBIDDEN_WORDING = re.compile(
    r"you\s+should|recommend|advice|advis|please\s+(?:take|stop|start)"
    r"|(?:take|stop|start|increase|decrease)\s+your\b",
    re.IGNORECASE,
)

_TOKEN = re.compile(r"[a-z0-9]+")

RICH_ENTITY_VALUES = [
    "start metformin 500 mg twice daily",
    "stop lisinopril",
    "increase atorvastatin to 40 mg",
    "decrease levothyroxine to 25 mcg",
    "change to losartan 50 mg daily",
    "continue aspirin 81 mg daily",
    "start metoprolol",
    "increase to 500 mg",
    "consider warfarin",
]

RICH_MEDS = [
    _medication("Lisinopril", dosage_amount=20.0),
    _medication("atorvastatin"),
    _medication("levothyroxine", dosage_amount=50.0, dosage_unit="mcg"),
    _medication("metoprolol tartrate"),
    _medication("metoprolol succinate"),
    _medication("aspirin", dosage_amount=325.0, is_active=False),
]


class TestSafetyProperties:
    def _rich_suggestions(self):
        entities = [_med_entity(DOC_ID, v) for v in RICH_ENTITY_VALUES]
        return derive_reconciliation_suggestions(entities, RICH_MEDS), entities

    def test_hc_mrec_018_no_fabricated_drug_names(self):
        """Every drug token in a suggestion appears verbatim in the source
        entity's own value/quote — suggestion generation never invents a
        drug name that is not in the note's words."""
        suggestions, entities = self._rich_suggestions()
        by_id = {e.id: e for e in entities}
        assert suggestions, "fixture should produce suggestions"
        for s in suggestions:
            source = by_id[s["source_entity_id"]]
            source_tokens = set(_TOKEN.findall(source.entity_value.lower()))
            source_tokens |= set(_TOKEN.findall((source.quote or "").lower()))
            if s["drug_name"]:
                for token in _TOKEN.findall(s["drug_name"].lower()):
                    assert token in source_tokens, (
                        f"fabricated drug token {token!r} not in source "
                        f"{source.entity_value!r}"
                    )
            # entity_value and quote must be passed through verbatim.
            assert s["entity_value"] == source.entity_value
            assert s["source_quote"] == source.quote

    def test_hc_mrec_019_payload_wording_is_record_keeping_only(self):
        """App-generated strings (current_list_summary, reason) are neutral
        record-keeping labels: no imperative instructions, no
        recommendation/advice wording anywhere in the payload's own words."""
        suggestions, _ = self._rich_suggestions()
        for s in suggestions:
            for field in ("current_list_summary", "reason", "drug_name"):
                value = s.get(field)
                if value:
                    assert not FORBIDDEN_WORDING.search(value), (
                        f"forbidden wording in {field}: {value!r}"
                    )

    def test_hc_mrec_020_payload_has_exactly_the_documented_fields(self):
        suggestions, _ = self._rich_suggestions()
        expected = {
            "suggestion_type",
            "source_entity_id",
            "source_quote",
            "entity_value",
            "drug_name",
            "matched_medication_id",
            "current_list_summary",
            "confidence",
            "reason",
        }
        for s in suggestions:
            assert set(s.keys()) == expected
            assert s["suggestion_type"] in SUGGESTION_TYPES
            assert 0.0 <= s["confidence"] <= 1.0

    def test_hc_mrec_021_current_list_summary_only_from_user_list_or_neutral(self):
        """The 'your list has' line is built from the matched medication's own
        fields (or the fixed neutral phrases) — never from model/free text."""
        suggestions, _ = self._rich_suggestions()
        med_by_id = {m.id: m for m in RICH_MEDS}
        for s in suggestions:
            summary = s["current_list_summary"]
            if s["matched_medication_id"] is None:
                assert summary == "not on your list"
            else:
                med = med_by_id[s["matched_medication_id"]]
                assert med.name.lower() in summary.lower()


# ---------------------------------------------------------------------------
# Bounded behavior
# ---------------------------------------------------------------------------


class TestBoundedBehavior:
    def test_hc_mrec_022_output_capped_with_many_meds_and_entities(self):
        entities = [
            _med_entity(DOC_ID, f"start drug{i}alpha 10 mg") for i in range(300)
        ]
        meds = [_medication(f"listeddrug{i}") for i in range(150)]
        suggestions = derive_reconciliation_suggestions(entities, meds)
        assert len(suggestions) <= MAX_SUGGESTIONS
        # Deterministic: first entities win the cap.
        assert suggestions[0]["source_entity_id"] == entities[0].id


# ---------------------------------------------------------------------------
# API endpoint (mock-session style matches tests/test_care_tasks.py)
# ---------------------------------------------------------------------------

from api.med_reconcile import (  # noqa: E402
    MedReconcileSuggestionResponse,
    get_med_reconciliation,
)


class _ScalarResult:
    def __init__(self, one: object = None, all_items: list | None = None):
        self._one = one
        self._all_items = all_items or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return self

    def unique(self):
        return self

    def all(self):
        return self._all_items


def _sequential_db(results: list[_ScalarResult]) -> AsyncMock:
    it = iter(results)

    async def mock_execute(stmt):
        return next(it)

    db = AsyncMock()
    db.execute = mock_execute
    return db


class TestReconciliationEndpoint:
    @pytest.mark.asyncio
    async def test_hc_mrec_023_endpoint_returns_suggestions_and_audits(
        self, monkeypatch
    ):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _med_entity(doc_id, "start metformin 500 mg twice daily")
        profile_db = _sequential_db([
            _ScalarResult(one=doc),
            _ScalarResult(all_items=[ent]),
            _ScalarResult(all_items=[_medication("atorvastatin")]),
        ])
        master_db = AsyncMock()
        audit_mock = AsyncMock()
        monkeypatch.setattr("api.med_reconcile.log_document_event", audit_mock)

        result = await get_med_reconciliation(
            _make_session(), doc_id, profile_db, master_db
        )

        assert len(result) == 1
        assert isinstance(result[0], MedReconcileSuggestionResponse)
        assert result[0].suggestion_type == "new_medication"
        assert result[0].source_quote == ent.quote

        audit_mock.assert_awaited_once()
        kwargs = audit_mock.await_args.kwargs
        assert kwargs["profile_id"] == "test-profile"
        assert kwargs["document_id"] == doc_id
        assert kwargs["event"] == "med_reconcile"
        master_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_hc_mrec_024_endpoint_403_when_wrong_profile(self):
        from fastapi import HTTPException

        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id, profile_id="other-profile")
        profile_db = _sequential_db([_ScalarResult(one=doc)])

        with pytest.raises(HTTPException) as exc_info:
            await get_med_reconciliation(
                _make_session("test-profile"), doc_id, profile_db, AsyncMock()
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_hc_mrec_025_endpoint_404_when_document_missing(self):
        from fastapi import HTTPException

        profile_db = _sequential_db([_ScalarResult(one=None)])
        with pytest.raises(HTTPException) as exc_info:
            await get_med_reconciliation(
                _make_session(), str(uuid.uuid4()), profile_db, AsyncMock()
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_hc_mrec_026_endpoint_400_on_invalid_doc_id(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_med_reconciliation(
                _make_session(), "../etc/passwd", AsyncMock(), AsyncMock()
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_hc_mrec_027_rejected_entities_excluded_at_api_level(
        self, monkeypatch
    ):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        rejected = _med_entity(
            doc_id, "stop lisinopril", verified_by_user=False
        )
        profile_db = _sequential_db([
            _ScalarResult(one=doc),
            _ScalarResult(all_items=[rejected]),
            _ScalarResult(all_items=[_medication("lisinopril")]),
        ])
        monkeypatch.setattr("api.med_reconcile.log_document_event", AsyncMock())

        result = await get_med_reconciliation(
            _make_session(), doc_id, profile_db, AsyncMock()
        )
        assert result == []


# ---------------------------------------------------------------------------
# Profile isolation with a real per-profile DB
# ---------------------------------------------------------------------------

import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from core.profile_database import ProfileDatabaseBase  # noqa: E402
from models import Document  # noqa: E402


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


class TestProfileIsolation:
    def _document(self, doc_id: str, profile_id: str) -> Document:
        return Document(
            id=doc_id,
            profile_id=profile_id,
            path_hash="x" * 64,
            content_hash="y" * 64,
            doc_type="lab_pdf",
            source="visit-note.pdf",
            status="parsed",
            imported_at=datetime(2026, 4, 2, 12, 0, 0),
        )

    @pytest.mark.asyncio
    async def test_hc_mrec_028_other_profiles_medications_never_match(
        self, real_profile_db, monkeypatch
    ):
        """A medication belonging to another profile must not be compared
        against — the note's drug reads as 'not on your list'."""
        monkeypatch.setattr("api.med_reconcile.log_document_event", AsyncMock())
        db = real_profile_db

        doc_id = str(uuid.uuid4())
        db.add(self._document(doc_id, "test-profile"))
        db.add(_med_entity(doc_id, "start metformin 500 mg"))
        db.add(_medication("metformin", profile_id="other-profile"))
        await db.commit()

        result = await get_med_reconciliation(
            _make_session("test-profile"), doc_id, db, AsyncMock()
        )
        assert len(result) == 1
        assert result[0].suggestion_type == "new_medication"
        assert result[0].matched_medication_id is None
        assert result[0].current_list_summary == "not on your list"

    @pytest.mark.asyncio
    async def test_hc_mrec_029_own_profile_medication_matches(
        self, real_profile_db, monkeypatch
    ):
        monkeypatch.setattr("api.med_reconcile.log_document_event", AsyncMock())
        db = real_profile_db

        doc_id = str(uuid.uuid4())
        db.add(self._document(doc_id, "test-profile"))
        db.add(_med_entity(doc_id, "stop metformin"))
        own = _medication("metformin", profile_id="test-profile")
        db.add(own)
        await db.commit()

        result = await get_med_reconciliation(
            _make_session("test-profile"), doc_id, db, AsyncMock()
        )
        assert len(result) == 1
        assert result[0].suggestion_type == "stopped_medication"
        assert result[0].matched_medication_id == own.id
