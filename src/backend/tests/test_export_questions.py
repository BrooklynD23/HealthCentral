"""HC-M17 doctor-question generator tests (HC-QGN-NNN).

The "questions for the doctor" list draws on everything the app knows:
abnormal labs and trends (existing behavior, unchanged), plus verified
visit-note entities (medication_change, test_ordered, referral) and
open/needs_review care-plan tasks. Every generated question:

- is a QUESTION (interrogative, ends with "?"), never advice;
- carries provenance: category, source_kind, source_id, source_quote.

Template generation only — no LLM involved.
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth import Session
from core.time import utcnow
from modules.export import ExportModule, QuestionPrompt

TODAY = date(2026, 7, 12)

# Phrases that would turn a question into advice. Every generated question
# must be free of these (no-medical-advice invariant).
ADVICE_PHRASES = ("you should", "make sure to", "be sure to")


def _assert_interrogative_no_advice(questions: list[QuestionPrompt]) -> None:
    assert questions, "expected at least one question"
    for q in questions:
        assert q.question.strip().endswith("?"), q.question
        lowered = q.question.lower()
        for phrase in ADVICE_PHRASES:
            assert phrase not in lowered, q.question


def _task(**overrides) -> dict:
    fields = dict(
        id=str(uuid.uuid4()),
        title="Repeat CBC",
        status="open",
        due_date=None,
        source_quote="Repeat CBC in 4 weeks",
        source_entity_id=None,
    )
    fields.update(overrides)
    return fields


def _entity(**overrides) -> dict:
    fields = dict(
        id=str(uuid.uuid4()),
        entity_type="medication_change",
        entity_value="start lisinopril 10mg daily",
        quote="Start lisinopril 10mg daily",
        verified_by_user=True,
    )
    fields.update(overrides)
    return fields


@pytest.fixture
def export_module():
    return ExportModule()


class TestQuestionSources:
    def test_hc_qgn_001_needs_review_task_yields_clarification_question(self, export_module):
        task = _task(status="needs_review", source_quote="Follow up with cardiology soon")
        questions = export_module.generate_questions(
            observations=[], trends=[], care_tasks=[task], today=TODAY
        )

        assert len(questions) == 1
        q = questions[0]
        assert q.category == "clarification"
        assert "Follow up with cardiology soon" in q.question
        assert q.question.strip().endswith("?")
        assert q.source_kind == "care_task"
        assert q.source_id == task["id"]
        assert q.source_quote == "Follow up with cardiology soon"

    def test_hc_qgn_002_verified_medication_change_yields_question(self, export_module):
        ent = _entity(entity_type="medication_change", entity_value="start lisinopril 10mg daily")
        questions = export_module.generate_questions(
            observations=[], trends=[], entities=[ent], today=TODAY
        )

        assert len(questions) == 1
        q = questions[0]
        assert q.category == "medication_change"
        assert "start lisinopril 10mg daily" in q.question
        assert q.source_kind == "entity"
        assert q.source_id == ent["id"]
        assert q.source_quote == ent["quote"]

    def test_hc_qgn_003_unverified_entities_are_excluded(self, export_module):
        """Unverified data policy: only verified entities generate questions."""
        entities = [
            _entity(verified_by_user=None),
            _entity(verified_by_user=False),
            _entity(entity_type="test_ordered", entity_value="CBC", verified_by_user=None),
        ]
        questions = export_module.generate_questions(
            observations=[], trends=[], entities=entities, today=TODAY
        )
        assert questions == []

    def test_hc_qgn_004_test_ordered_entity_references_quote(self, export_module):
        ent = _entity(
            entity_type="test_ordered",
            entity_value="repeat CBC",
            quote="Repeat CBC at next visit",
        )
        questions = export_module.generate_questions(
            observations=[], trends=[], entities=[ent], today=TODAY
        )

        assert len(questions) == 1
        q = questions[0]
        assert q.category == "test_ordered"
        assert "Repeat CBC at next visit" in q.question
        assert q.source_kind == "entity"
        assert q.source_quote == "Repeat CBC at next visit"

    def test_hc_qgn_005_referral_entity_asks_who_and_when(self, export_module):
        ent = _entity(entity_type="referral", entity_value="cardiology", quote="Referred to cardiology")
        questions = export_module.generate_questions(
            observations=[], trends=[], entities=[ent], today=TODAY
        )

        assert len(questions) == 1
        q = questions[0]
        assert q.category == "referral"
        assert "cardiology" in q.question
        assert q.source_kind == "entity"

    def test_hc_qgn_006_open_task_past_due_yields_follow_up_question(self, export_module):
        overdue = _task(title="Schedule cardiology follow-up", due_date=TODAY - timedelta(days=3))
        near_due = _task(title="Repeat CBC", due_date=TODAY + timedelta(days=7))
        far_future = _task(title="Annual physical", due_date=TODAY + timedelta(days=120))
        no_due = _task(title="Ask about statin", due_date=None)

        questions = export_module.generate_questions(
            observations=[],
            trends=[],
            care_tasks=[overdue, near_due, far_future, no_due],
            today=TODAY,
        )

        follow_up = [q for q in questions if q.category == "follow_up"]
        titles = " | ".join(q.question for q in follow_up)
        assert len(follow_up) == 2
        assert "Schedule cardiology follow-up" in titles
        assert "Repeat CBC" in titles
        assert "Annual physical" not in titles

    def test_hc_qgn_007_done_and_ignored_tasks_are_skipped(self, export_module):
        tasks = [
            _task(status="done", due_date=TODAY - timedelta(days=1)),
            _task(status="ignored", due_date=TODAY - timedelta(days=1)),
        ]
        questions = export_module.generate_questions(
            observations=[], trends=[], care_tasks=tasks, today=TODAY
        )
        assert questions == []

    def test_hc_qgn_008_entity_linked_to_task_not_duplicated(self, export_module):
        """An entity already covered by an accepted care task must not
        produce a second, duplicate question."""
        ent = _entity(entity_type="test_ordered", entity_value="CBC", quote="Repeat CBC in 4 weeks")
        task = _task(
            status="needs_review",
            source_quote="Repeat CBC in 4 weeks",
            source_entity_id=ent["id"],
        )
        questions = export_module.generate_questions(
            observations=[], trends=[], care_tasks=[task], entities=[ent], today=TODAY
        )
        assert len(questions) == 1
        assert questions[0].source_kind == "care_task"

    def test_hc_qgn_014_task_quote_dedupes_entity_recreated_with_new_id(self, export_module):
        """A reprocess deletes and recreates entities under new UUIDs, so a
        task's source_entity_id can go stale. The shared verbatim quote must
        still prevent a duplicate question for the same instruction."""
        ent = _entity(
            entity_type="test_ordered",
            entity_value="CBC",
            quote="Repeat CBC in 4 weeks",
        )
        task = _task(
            status="needs_review",
            source_quote="Repeat CBC in 4 weeks",
            source_entity_id=str(uuid.uuid4()),  # stale pre-reprocess entity id
        )
        questions = export_module.generate_questions(
            observations=[], trends=[], care_tasks=[task], entities=[ent], today=TODAY
        )
        assert len(questions) == 1
        assert questions[0].source_kind == "care_task"


class TestInterrogativeInvariant:
    def test_hc_qgn_009_all_questions_interrogative_and_advice_free(self, export_module):
        """Every question from every source ends with '?' and contains no
        imperative advice phrasing."""
        observations = [
            {
                "id": str(uuid.uuid4()),
                "analyte_canonical": "hemoglobin_a1c",
                "value": 7.2,
                "unit": "%",
                "flag": "H",
                "is_abnormal": True,
                "user_verified": True,
            }
        ]
        trends = [{"analyte": "hemoglobin_a1c", "trend_direction": "up", "delta_percent": 15.2}]
        care_tasks = [
            _task(status="needs_review", source_quote="Follow up as needed"),
            _task(status="open", due_date=TODAY - timedelta(days=1)),
        ]
        entities = [
            _entity(entity_type="medication_change"),
            _entity(entity_type="test_ordered", entity_value="CBC", quote="Repeat CBC"),
            _entity(entity_type="referral", entity_value="cardiology", quote="Referred to cardiology"),
        ]

        questions = export_module.generate_questions(
            observations=observations,
            trends=trends,
            care_tasks=care_tasks,
            entities=entities,
            today=TODAY,
        )

        assert len(questions) >= 6
        _assert_interrogative_no_advice(questions)

    def test_hc_qgn_010_every_question_carries_provenance(self, export_module):
        questions = ExportModule().generate_questions(
            observations=[
                {
                    "id": "obs-1",
                    "analyte_canonical": "glucose",
                    "value": 130.0,
                    "unit": "mg/dL",
                    "flag": "H",
                    "is_abnormal": True,
                }
            ],
            trends=[{"analyte": "glucose", "trend_direction": "up", "delta_percent": 12.0}],
            care_tasks=[_task(status="needs_review")],
            entities=[_entity()],
            today=TODAY,
        )
        for q in questions:
            assert q.category
            assert q.source_kind in {"observation", "trend", "care_task", "entity"}
            assert q.source_id


class TestBackwardCompatibility:
    def test_hc_qgn_011_two_argument_call_still_works(self, export_module):
        """Existing callers pass only observations and trends."""
        questions = export_module.generate_questions(
            observations=[
                {
                    "analyte_canonical": "cholesterol_total",
                    "value": 245.0,
                    "unit": "mg/dL",
                    "flag": "H",
                    "is_abnormal": True,
                }
            ],
            trends=[],
        )
        assert len(questions) == 1
        assert questions[0].category == "abnormal"
        # New provenance fields exist with usable defaults.
        assert questions[0].source_kind == "observation"
        assert questions[0].source_quote is None

    def test_hc_qgn_012_question_prompt_dataclass_defaults(self):
        """QuestionPrompt can still be constructed with the original four
        fields (backward-compatible dataclass extension)."""
        q = QuestionPrompt(
            category="abnormal",
            question="What might that indicate?",
            context="ctx",
            related_analytes=["glucose"],
        )
        assert q.source_id is None
        assert q.source_quote is None


# ---------------------------------------------------------------------------
# Route-level: POST /export/questions includes the new sources
# ---------------------------------------------------------------------------

from api.export import generate_questions as questions_route  # noqa: E402


def _make_session(profile_id: str = "test-profile") -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="Test Profile",
        expires_at=utcnow() + timedelta(hours=1),
    )


class TestQuestionsRoute:
    @pytest.mark.asyncio
    async def test_hc_qgn_013_route_includes_new_sources_and_audits(self, monkeypatch):
        obs = [
            {
                "id": str(uuid.uuid4()),
                "analyte_canonical": "glucose",
                "analyte_raw": "Glucose",
                "value": 130.0,
                "value_text": None,
                "unit": "mg/dL",
                "ref_low": 70.0,
                "ref_high": 100.0,
                "flag": "H",
                "is_abnormal": True,
                "user_verified": True,
                "collected_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
            }
        ]
        task = _task(status="needs_review", source_quote="Follow up with endocrinology")
        ent = _entity(entity_type="medication_change")

        monkeypatch.setattr("api.export._fetch_observations", AsyncMock(return_value=obs))
        monkeypatch.setattr("api.export._fetch_care_task_dicts", AsyncMock(return_value=[task]))
        monkeypatch.setattr("api.export._fetch_question_entity_dicts", AsyncMock(return_value=[ent]))
        audit_mock = AsyncMock()
        monkeypatch.setattr("api.export.log_export_event", audit_mock)

        master_db = AsyncMock()
        result = await questions_route(
            session=_make_session(),
            from_date=None,
            to_date=None,
            profile_db=AsyncMock(),
            master_db=master_db,
        )

        categories = {item.category for item in result}
        assert "abnormal" in categories  # existing source keeps working
        assert "clarification" in categories
        assert "medication_change" in categories

        # Backward-compatible response shape: original fields still present.
        for item in result:
            assert item.question
            assert item.context is not None
            assert isinstance(item.related_analytes, list)

        # New provenance fields exposed on the response model.
        clarification = next(item for item in result if item.category == "clarification")
        assert clarification.source_kind == "care_task"
        assert clarification.source_id == task["id"]
        assert clarification.source_quote == "Follow up with endocrinology"

        audit_mock.assert_awaited_once()
        assert audit_mock.await_args.kwargs["export_type"] == "questions"
