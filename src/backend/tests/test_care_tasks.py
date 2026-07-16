"""HC-M15 care-plan task tests (HC-TASK-NNN).

Follow-up instructions, ordered tests, and referrals extracted from visit
notes become checklist-task *candidates*. Nothing is persisted without
explicit user acceptance, and a candidate NEVER carries an invented due date:
a due date exists only when the source text contains an absolute date, or a
relative expression that can be resolved against an anchored document date.
"""

from __future__ import annotations

import itertools
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth import Session
from core.time import utcnow
from models.care_plan_task import CarePlanTask
from models.document_category import DocumentEntity
from modules.care_tasks import derive_task_candidates


# ---------------------------------------------------------------------------
# Shared helpers (mock-session style matches tests/test_source_spans.py)
# ---------------------------------------------------------------------------


def _make_session(profile_id: str = "test-profile") -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="Test Profile",
        expires_at=utcnow() + timedelta(hours=1),
    )


def _make_document(
    doc_id: str,
    profile_id: str = "test-profile",
    collection_date: datetime | None = None,
) -> MagicMock:
    doc = MagicMock()
    doc.id = doc_id
    doc.profile_id = profile_id
    doc.source = "visit-note.pdf"
    doc.collection_date = collection_date
    return doc


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


def _visit_date_entity(doc_id: str, value: str = "04/02/2026") -> DocumentEntity:
    return _make_entity(
        doc_id,
        entity_type="visit_date",
        entity_value=value,
        quote=value,
    )


# ---------------------------------------------------------------------------
# Candidate derivation per entity type
# ---------------------------------------------------------------------------


class TestCandidateDerivation:
    def test_hc_task_001_follow_up_instruction_becomes_candidate(self):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _make_entity(
            doc_id,
            entity_type="follow_up_instruction",
            entity_value="Follow-up in 3 months",
            quote="Follow-up in 3 months",
        )
        candidates = derive_task_candidates([ent], doc)
        assert len(candidates) == 1
        cand = candidates[0]
        assert cand["source_entity_id"] == ent.id
        assert cand["source_document_id"] == doc_id
        assert cand["source_quote"] == "Follow-up in 3 months"
        # No anchor date on the document -> relative timing cannot resolve.
        assert cand["due_date"] is None
        assert cand["due_date_confidence"] is None
        assert cand["suggested_status"] == "needs_review"

    def test_hc_task_002_test_ordered_title_is_concise_imperative(self):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _make_entity(
            doc_id,
            entity_type="test_ordered",
            entity_value="Repeat CBC in 4 weeks",
            quote="Repeat CBC in 4 weeks",
        )
        candidates = derive_task_candidates([ent], doc)
        assert len(candidates) == 1
        assert candidates[0]["title"] == "Repeat CBC"

    def test_hc_task_003_referral_title_mentions_target(self):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _make_entity(
            doc_id,
            entity_type="referral",
            entity_value="cardiology",
            quote="Referred to cardiology",
        )
        candidates = derive_task_candidates([ent], doc)
        assert len(candidates) == 1
        assert "cardiology" in candidates[0]["title"].lower()
        assert candidates[0]["title"][0].isupper()

    def test_hc_task_004_non_task_entity_types_are_ignored(self):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        entities = [
            _make_entity(doc_id, entity_type="warning_sign", entity_value="call if fever"),
            _make_entity(doc_id, entity_type="medication_change", entity_value="start lisinopril"),
            _visit_date_entity(doc_id),
        ]
        assert derive_task_candidates(entities, doc) == []


# ---------------------------------------------------------------------------
# Due-date rules: never invent a due date
# ---------------------------------------------------------------------------


class TestDueDateRules:
    def test_hc_task_005_relative_with_visit_date_anchor_resolves(self):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _make_entity(
            doc_id,
            entity_type="follow_up_instruction",
            entity_value="follow-up in 4 weeks",
            quote="follow-up in 4 weeks",
        )
        candidates = derive_task_candidates([ent, _visit_date_entity(doc_id, "04/02/2026")], doc)
        assert len(candidates) == 1
        cand = candidates[0]
        assert cand["due_date"] == date(2026, 4, 30)
        assert cand["due_date_confidence"] is not None
        assert cand["due_date_confidence"] <= 0.8
        assert cand["suggested_status"] == "open"

    def test_hc_task_006_relative_months_with_collection_date_anchor(self):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id, collection_date=datetime(2026, 1, 31))
        ent = _make_entity(
            doc_id,
            entity_type="follow_up_instruction",
            entity_value="return in 3 months",
            quote="return in 3 months",
        )
        candidates = derive_task_candidates([ent], doc)
        cand = candidates[0]
        # Calendar-month addition with day clamped to the month's end.
        assert cand["due_date"] == date(2026, 4, 30)
        assert cand["due_date_confidence"] <= 0.8
        assert cand["suggested_status"] == "open"

    def test_hc_task_007_relative_without_anchor_yields_no_due_date(self):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _make_entity(
            doc_id,
            entity_type="test_ordered",
            entity_value="repeat CBC in 2 weeks",
            quote="repeat CBC in 2 weeks",
        )
        cand = derive_task_candidates([ent], doc)[0]
        assert cand["due_date"] is None
        assert cand["due_date_confidence"] is None
        assert cand["suggested_status"] == "needs_review"

    def test_hc_task_008_vague_timing_yields_needs_review(self):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        for phrase in ("follow-up soon", "repeat labs as needed", "schedule appointment"):
            ent = _make_entity(
                doc_id,
                entity_type="follow_up_instruction",
                entity_value=phrase,
                quote=phrase,
            )
            cand = derive_task_candidates([ent, _visit_date_entity(doc_id)], doc)[0]
            assert cand["due_date"] is None, phrase
            assert cand["due_date_confidence"] is None, phrase
            assert cand["suggested_status"] == "needs_review", phrase

    def test_hc_task_009_absolute_date_in_source_text_parses_directly(self):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _make_entity(
            doc_id,
            entity_type="follow_up_instruction",
            entity_value="Follow-up appointment: May 1, 2026 with Dr. Jones",
            quote="Follow-up appointment: May 1, 2026 with Dr. Jones",
        )
        # No anchor anywhere — absolute dates need none.
        cand = derive_task_candidates([ent], doc)[0]
        assert cand["due_date"] == date(2026, 5, 1)
        assert cand["due_date_confidence"] is not None
        assert cand["suggested_status"] == "open"

    def test_hc_task_026_stray_past_absolute_date_prefers_anchored_relative(self):
        """A stray absolute date in the quote (a past reference, e.g. a
        prior MRI) must not override the real relative expression."""
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        quote = "Will review the MRI performed 01/04/2019, return in 6 weeks"
        ent = _make_entity(
            doc_id,
            entity_type="follow_up_instruction",
            entity_value=quote,
            quote=quote,
        )
        cand = derive_task_candidates(
            [ent, _visit_date_entity(doc_id, "06/10/2026")], doc
        )[0]
        # Anchored relative resolution wins: 2026-06-10 + 6 weeks.
        assert cand["due_date"] == date(2026, 7, 22)
        assert cand["due_date_confidence"] is not None
        assert cand["due_date_confidence"] <= 0.8
        assert cand["suggested_status"] == "open"

    def test_hc_task_027_past_absolute_date_alone_never_becomes_due_date(self):
        """An absolute date earlier than the anchor (document) date is a
        reference to the past, not a follow-up due date."""
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        quote = "Follow up regarding the MRI performed 01/04/2019"
        ent = _make_entity(
            doc_id,
            entity_type="follow_up_instruction",
            entity_value=quote,
            quote=quote,
        )
        cand = derive_task_candidates(
            [ent, _visit_date_entity(doc_id, "06/10/2026")], doc
        )[0]
        assert cand["due_date"] is None
        assert cand["due_date_confidence"] is None
        assert cand["suggested_status"] == "needs_review"

    def test_hc_task_010_property_no_due_date_without_textual_basis(self):
        """Property: a candidate has a due date only when its source text has
        an absolute date, or a relative expression AND the document has an
        anchor date. All other combinations must yield due_date=None."""
        doc_id = str(uuid.uuid4())

        base_phrases = [
            "follow-up with Dr. Jones",
            "repeat CBC",
            "schedule appointment with dermatology",
            "return to clinic",
            "follow-up as needed",
            "recheck labs soon",
        ]
        relative_suffixes = ["", " in 6 weeks", " within 2 months", " in 10 days"]
        absolute_suffixes = ["", " on 05/01/2026", " on May 1, 2026", " 2026-05-01"]
        anchors = [None, "04/02/2026"]

        for phrase, rel, absolute, anchor in itertools.product(
            base_phrases, relative_suffixes, absolute_suffixes, anchors
        ):
            text = f"{phrase}{rel}{absolute}"
            ent = _make_entity(
                doc_id,
                entity_type="follow_up_instruction",
                entity_value=text,
                quote=text,
            )
            entities = [ent]
            if anchor:
                entities.append(_visit_date_entity(doc_id, anchor))
            cand = derive_task_candidates(entities, _make_document(doc_id))[0]

            has_textual_basis = bool(absolute) or (bool(rel) and anchor is not None)
            if not has_textual_basis:
                assert cand["due_date"] is None, f"invented due date for: {text!r}"
                assert cand["due_date_confidence"] is None
                assert cand["suggested_status"] == "needs_review"
            else:
                assert cand["due_date"] is not None, f"expected due date for: {text!r}"
                assert cand["due_date_confidence"] is not None
                assert cand["suggested_status"] == "open"
                if not absolute:
                    # Computed (relative) dates must never look certain.
                    assert cand["due_date_confidence"] <= 0.8


# ---------------------------------------------------------------------------
# API endpoints (mock-session style matches tests/test_document_category_api.py)
# ---------------------------------------------------------------------------

from api.care_tasks import (  # noqa: E402
    AcceptTaskRequest,
    CarePlanTaskResponse,
    CareTaskUpdateRequest,
    TaskCandidateResponse,
    accept_care_task,
    get_care_task_candidates,
    list_care_tasks,
    update_care_task,
)


class _ScalarResult:
    def __init__(self, one: object = None, all_items: list | None = None):
        self._one = one
        self._all_items = all_items or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return self

    def all(self):
        return self._all_items


def _make_task(**overrides) -> CarePlanTask:
    fields = dict(
        id=str(uuid.uuid4()),
        title="Repeat CBC",
        due_date=None,
        due_date_confidence=None,
        status="open",
        source_document_id=str(uuid.uuid4()),
        source_entity_id=str(uuid.uuid4()),
        source_quote="Repeat CBC in 4 weeks",
        user_note=None,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    fields.update(overrides)
    return CarePlanTask(**fields)


def _sequential_db(results: list[_ScalarResult]) -> AsyncMock:
    """Profile DB mock returning canned results in order."""
    it = iter(results)

    async def mock_execute(stmt):
        return next(it)

    db = AsyncMock()
    db.execute = mock_execute
    return db


class TestListCareTasks:
    @pytest.mark.asyncio
    async def test_hc_task_011_list_returns_tasks_and_audits(self, monkeypatch):
        task = _make_task()
        profile_db = _sequential_db([_ScalarResult(all_items=[task])])
        master_db = AsyncMock()
        audit_mock = AsyncMock()
        monkeypatch.setattr("api.care_tasks.log_care_task_event", audit_mock)

        result = await list_care_tasks(_make_session(), None, profile_db, master_db)

        assert len(result) == 1
        assert isinstance(result[0], CarePlanTaskResponse)
        assert result[0].title == "Repeat CBC"
        assert result[0].status == "open"
        audit_mock.assert_awaited_once()
        assert audit_mock.await_args.kwargs["profile_id"] == "test-profile"
        master_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_hc_task_012_list_rejects_invalid_status_filter(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await list_care_tasks(_make_session(), "bogus", AsyncMock(), AsyncMock())
        assert exc_info.value.status_code == 400


class TestCandidatesEndpoint:
    @pytest.mark.asyncio
    async def test_hc_task_013_excludes_linked_and_rejected_entities(self, monkeypatch):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        fresh = _make_entity(doc_id, entity_value="follow-up in 4 weeks")
        linked = _make_entity(doc_id, entity_value="repeat CBC", entity_type="test_ordered")
        rejected = _make_entity(
            doc_id,
            entity_value="cardiology",
            entity_type="referral",
            verified_by_user=False,
        )
        linked_task = _make_task(source_document_id=doc_id, source_entity_id=linked.id)

        profile_db = _sequential_db([
            _ScalarResult(one=doc),
            _ScalarResult(all_items=[fresh, linked, rejected]),
            _ScalarResult(all_items=[linked_task]),
        ])
        master_db = AsyncMock()
        monkeypatch.setattr("api.care_tasks.log_care_task_event", AsyncMock())

        result = await get_care_task_candidates(
            _make_session(), doc_id, profile_db, master_db
        )

        assert len(result) == 1
        assert isinstance(result[0], TaskCandidateResponse)
        assert result[0].source_entity_id == fresh.id

    @pytest.mark.asyncio
    async def test_hc_task_014_candidates_403_when_wrong_profile(self):
        from fastapi import HTTPException

        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id, profile_id="other-profile")
        profile_db = _sequential_db([_ScalarResult(one=doc)])

        with pytest.raises(HTTPException) as exc_info:
            await get_care_task_candidates(
                _make_session("test-profile"), doc_id, profile_db, AsyncMock()
            )
        assert exc_info.value.status_code == 403


class TestAcceptEndpoint:
    def _accept_db(self, doc, entity, existing_task=None, entities=None):
        return _sequential_db([
            _ScalarResult(one=doc),
            _ScalarResult(one=entity),
            _ScalarResult(one=existing_task),
            _ScalarResult(all_items=entities if entities is not None else [entity]),
        ])

    @pytest.mark.asyncio
    async def test_hc_task_015_accept_persists_task_with_audit(self, monkeypatch):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _make_entity(
            doc_id,
            entity_type="test_ordered",
            entity_value="Repeat CBC in 4 weeks",
            quote="Repeat CBC in 4 weeks",
        )
        anchor = _visit_date_entity(doc_id, "04/02/2026")
        profile_db = self._accept_db(doc, ent, entities=[ent, anchor])
        master_db = AsyncMock()
        audit_mock = AsyncMock()
        monkeypatch.setattr("api.care_tasks.log_care_task_event", audit_mock)

        payload = AcceptTaskRequest(
            source_entity_id=ent.id,
            source_document_id=doc_id,
            source_quote="Repeat CBC in 4 weeks",
            user_note="before next visit",
        )
        result = await accept_care_task(payload, _make_session(), profile_db, master_db)

        assert isinstance(result, CarePlanTaskResponse)
        assert result.title == "Repeat CBC"
        assert result.source_entity_id == ent.id
        assert result.source_quote == "Repeat CBC in 4 weeks"
        assert result.due_date == "2026-04-30"
        assert result.status == "open"
        assert result.user_note == "before next visit"

        # Task persisted in the per-profile DB.
        profile_db.add.assert_called_once()
        added = profile_db.add.call_args.args[0]
        assert isinstance(added, CarePlanTask)
        profile_db.commit.assert_awaited()

        # Audit entry written and committed on the master DB.
        audit_mock.assert_awaited_once()
        kwargs = audit_mock.await_args.kwargs
        assert kwargs["event"] == "create"
        assert kwargs["profile_id"] == "test-profile"
        assert kwargs["details"]["source_entity_id"] == ent.id
        master_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_hc_task_016_accept_409_on_quote_mismatch(self):
        from fastapi import HTTPException

        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _make_entity(doc_id, quote="follow-up in 4 weeks")
        profile_db = self._accept_db(doc, ent)

        payload = AcceptTaskRequest(
            source_entity_id=ent.id,
            source_document_id=doc_id,
            source_quote="a different quote entirely",
        )
        with pytest.raises(HTTPException) as exc_info:
            await accept_care_task(payload, _make_session(), profile_db, AsyncMock())
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_hc_task_017_accept_409_when_entity_rejected(self):
        from fastapi import HTTPException

        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _make_entity(doc_id, verified_by_user=False)
        profile_db = self._accept_db(doc, ent)

        payload = AcceptTaskRequest(
            source_entity_id=ent.id,
            source_document_id=doc_id,
            source_quote=ent.quote,
        )
        with pytest.raises(HTTPException) as exc_info:
            await accept_care_task(payload, _make_session(), profile_db, AsyncMock())
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_hc_task_018_accept_409_when_already_linked(self):
        from fastapi import HTTPException

        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _make_entity(doc_id)
        existing = _make_task(source_document_id=doc_id, source_entity_id=ent.id)
        profile_db = self._accept_db(doc, ent, existing_task=existing)

        payload = AcceptTaskRequest(
            source_entity_id=ent.id,
            source_document_id=doc_id,
            source_quote=ent.quote,
        )
        with pytest.raises(HTTPException) as exc_info:
            await accept_care_task(payload, _make_session(), profile_db, AsyncMock())
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_hc_task_019_accept_400_for_non_task_entity_type(self):
        from fastapi import HTTPException

        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _make_entity(doc_id, entity_type="warning_sign")
        profile_db = self._accept_db(doc, ent)

        payload = AcceptTaskRequest(
            source_entity_id=ent.id,
            source_document_id=doc_id,
            source_quote=ent.quote,
        )
        with pytest.raises(HTTPException) as exc_info:
            await accept_care_task(payload, _make_session(), profile_db, AsyncMock())
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_hc_task_020_accept_403_when_wrong_profile(self):
        from fastapi import HTTPException

        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id, profile_id="other-profile")
        profile_db = _sequential_db([_ScalarResult(one=doc)])

        payload = AcceptTaskRequest(
            source_entity_id=str(uuid.uuid4()),
            source_document_id=doc_id,
            source_quote=None,
        )
        with pytest.raises(HTTPException) as exc_info:
            await accept_care_task(payload, _make_session(), profile_db, AsyncMock())
        assert exc_info.value.status_code == 403


class TestUpdateEndpoint:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("new_status", ["open", "done", "ignored", "needs_review"])
    async def test_hc_task_021_patch_sets_status_and_audits(self, new_status, monkeypatch):
        task = _make_task(status="open" if new_status != "open" else "done")
        profile_db = _sequential_db([_ScalarResult(one=task)])
        master_db = AsyncMock()
        audit_mock = AsyncMock()
        monkeypatch.setattr("api.care_tasks.log_care_task_event", audit_mock)

        result = await update_care_task(
            task.id,
            CareTaskUpdateRequest(status=new_status),
            _make_session(),
            profile_db,
            master_db,
        )

        assert task.status == new_status
        assert result.status == new_status
        profile_db.commit.assert_awaited()
        audit_mock.assert_awaited_once()
        assert audit_mock.await_args.kwargs["event"] == "update"
        master_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_hc_task_022_patch_rejects_invalid_status(self):
        with pytest.raises(Exception):  # pydantic ValidationError
            CareTaskUpdateRequest(status="finished")

    @pytest.mark.asyncio
    async def test_hc_task_023_patch_updates_user_note(self, monkeypatch):
        task = _make_task(user_note=None)
        profile_db = _sequential_db([_ScalarResult(one=task)])
        monkeypatch.setattr("api.care_tasks.log_care_task_event", AsyncMock())

        result = await update_care_task(
            task.id,
            CareTaskUpdateRequest(user_note="ask about dose"),
            _make_session(),
            profile_db,
            AsyncMock(),
        )

        assert task.user_note == "ask about dose"
        assert result.user_note == "ask about dose"
        assert task.status == "open"  # unchanged when not provided

    @pytest.mark.asyncio
    async def test_hc_task_024_patch_404_when_task_missing(self):
        from fastapi import HTTPException

        profile_db = _sequential_db([_ScalarResult(one=None)])
        with pytest.raises(HTTPException) as exc_info:
            await update_care_task(
                str(uuid.uuid4()),
                CareTaskUpdateRequest(status="done"),
                _make_session(),
                profile_db,
                AsyncMock(),
            )
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Reprocess resilience: duplicate detection must be content-keyed
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


class TestReprocessDuplicateGuards:
    """Reprocess deletes and recreates DocumentEntity rows with fresh UUIDs
    while SQLite FK enforcement is off, so task.source_entity_id dangles
    silently. Duplicate detection must therefore also key on content
    (source_document_id + source_quote), and nothing may crash on a
    dangling entity id."""

    QUOTE = "Repeat CBC in 4 weeks"

    def _document(self, doc_id: str) -> Document:
        return Document(
            id=doc_id,
            profile_id="test-profile",
            path_hash="x" * 64,
            content_hash="y" * 64,
            doc_type="lab_pdf",
            source="visit-note.pdf",
            status="parsed",
            collection_date=datetime(2026, 4, 2),
            imported_at=datetime(2026, 4, 2, 12, 0, 0),
        )

    def _entity(self, doc_id: str) -> DocumentEntity:
        return _make_entity(
            doc_id,
            entity_type="test_ordered",
            entity_value=self.QUOTE,
            quote=self.QUOTE,
        )

    @pytest.mark.asyncio
    async def test_hc_task_028_reprocess_then_accept_flow(
        self, real_profile_db, monkeypatch
    ):
        from fastapi import HTTPException

        monkeypatch.setattr("api.care_tasks.log_care_task_event", AsyncMock())
        master_db = AsyncMock()
        db = real_profile_db

        doc_id = str(uuid.uuid4())
        db.add(self._document(doc_id))
        original = self._entity(doc_id)
        db.add(original)
        await db.commit()

        # Accept the candidate -> task persisted, linked to the entity.
        task = await accept_care_task(
            AcceptTaskRequest(
                source_entity_id=original.id,
                source_document_id=doc_id,
                source_quote=self.QUOTE,
            ),
            _make_session(),
            db,
            master_db,
        )
        assert task.source_entity_id == original.id

        # Simulate reprocess: delete + recreate the entity with a fresh UUID
        # and identical text (FK enforcement is off, the link dangles).
        await db.delete(original)
        recreated = self._entity(doc_id)
        db.add(recreated)
        await db.commit()
        assert recreated.id != task.source_entity_id

        # The recreated entity's candidate is excluded (same quote).
        candidates = await get_care_task_candidates(
            _make_session(), doc_id, db, master_db
        )
        assert candidates == []

        # A second accept for the equivalent entity 409s.
        with pytest.raises(HTTPException) as exc_info:
            await accept_care_task(
                AcceptTaskRequest(
                    source_entity_id=recreated.id,
                    source_document_id=doc_id,
                    source_quote=self.QUOTE,
                ),
                _make_session(),
                db,
                master_db,
            )
        assert exc_info.value.status_code == 409

        # GET /care-tasks still works with the dangling entity id...
        tasks = await list_care_tasks(_make_session(), None, db, master_db)
        assert len(tasks) == 1
        assert tasks[0].source_entity_id == task.source_entity_id

        # ...and so does PATCH.
        updated = await update_care_task(
            tasks[0].id,
            CareTaskUpdateRequest(status="done"),
            _make_session(),
            db,
            master_db,
        )
        assert updated.status == "done"


# ---------------------------------------------------------------------------
# Migration 011 upgrade/downgrade/upgrade
# ---------------------------------------------------------------------------


def test_hc_task_025_migration_011_upgrade_downgrade_upgrade(tmp_path, monkeypatch):
    from alembic import command

    from core import migrations
    from core.config import settings

    monkeypatch.setattr(settings, "database_encryption_required", False)

    vault_path = tmp_path / "vault.db"
    encryption_key = b"0" * 32

    migrations.run_profile_migration(vault_path, encryption_key)
    assert (
        migrations.get_profile_current_revision(vault_path, encryption_key)
        == "012_pinboards"
    )

    config = migrations._get_alembic_config("profile")
    config.attributes["vault_path"] = vault_path
    config.attributes["encryption_key"] = encryption_key

    command.downgrade(config, "010_entity_source_spans")
    assert (
        migrations.get_profile_current_revision(vault_path, encryption_key)
        == "010_entity_source_spans"
    )

    command.upgrade(config, "head")
    assert (
        migrations.get_profile_current_revision(vault_path, encryption_key)
        == "012_pinboards"
    )
