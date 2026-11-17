"""EXPORT-QUESTIONS-PARITY (HC-EQP-NNN): the downloaded questions are the previewed questions.

Before this row the download's stored questions came from a thinner call than the preview's
(`POST /export/questions`): no care-plan tasks, no visit-note entities, and trend questions even
with Trends off. Now both go through one helper, and every stored question still passes strict
redaction before it is stored (owner decision D3, unchanged: `modules/redaction.py` is not touched).

Every test drives FastAPI's dependency graph through tests/support/routes.py::route_client
(recurring-failures #1). The fake vault of test_export_redaction.py answers every query with
observation rows, so the two care-plan/entity fetchers are stubbed with the dicts the real ones return.
CSV/JSON byte-identity is HC-EXPR-002 (test_export_redaction.py), in the acceptance command.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import api.export as export_api
from modules.redaction import RedactionEngine
from tests.test_export_redaction import (
    PHI_ROWS,
    _export_client,
    _install_capturing_weasyprint,
)

# PHI canaries: strict redaction removes an email address. Each sits in a field that feeds a question.
TASK_MARK = "EQPTASKMARK"
ENTITY_MARK = "EQPENTITYMARK"
TASK_EMAIL = "taskcanary@example.com"
ENTITY_EMAIL = "entitycanary@example.org"
CANARIES = (TASK_EMAIL, ENTITY_EMAIL)

CARE_TASKS = [
    {
        "id": "task-eqp-1",
        "title": f"Call {TASK_MARK} clinic",
        "status": "needs_review",
        "due_date": None,
        "source_quote": f"Call {TASK_MARK} clinic at {TASK_EMAIL} about the scan",
        "source_entity_id": None,
    }
]
ENTITIES = [
    {
        "id": "ent-eqp-1",
        "entity_type": "referral",
        "entity_value": f"{ENTITY_MARK} cardiology ({ENTITY_EMAIL})",
        "quote": f"Refer to {ENTITY_MARK} cardiology",
        "verified_by_user": True,
    }
]

# Two clean glucose rows (no PHI), so any redaction counted comes from the seeded questions.
CLEAN_ROWS = PHI_ROWS[:2]


@contextmanager
def _client(rows: tuple = PHI_ROWS) -> Iterator[TestClient]:
    with _export_client(rows=rows) as client:
        with patch.object(export_api, "_fetch_care_task_dicts", AsyncMock(return_value=CARE_TASKS)), patch.object(
            export_api, "_fetch_question_entity_dicts", AsyncMock(return_value=ENTITIES)
        ):
            yield client


def _preview(client: TestClient) -> list[dict]:
    response = client.post("/export/questions")
    assert response.status_code == 200, response.text
    return response.json()


def _generate(client: TestClient, *, trends: bool = True, questions: bool = True) -> str:
    created = client.post(
        "/export/doctor-summary",
        json={"format": "text", "include_trends": trends, "include_questions": questions},
    )
    assert created.status_code == 200, created.text
    return created.json()["summary_id"]


def _download(client: TestClient, summary_id: str, fmt: str = "text") -> str:
    response = client.get(
        f"/export/doctor-summary/{summary_id}/download", params={"format": fmt}
    )
    assert response.status_code == 200, response.text
    return response.content.decode("utf-8")


def _text_questions(text: str) -> set[str]:
    """The question lines of the text download's QUESTIONS FOR YOUR PROVIDER block."""
    lines = text.splitlines()
    assert "QUESTIONS FOR YOUR PROVIDER" in lines, text
    start = lines.index("QUESTIONS FOR YOUR PROVIDER") + 2  # skip the dashed rule
    found: set[str] = set()
    for line in lines[start:]:
        if not line.startswith("  - "):
            break
        found.add(line[4:])
    return found


def _strict(text: str) -> str:
    return RedactionEngine(policy_level="strict").redact(text).text


def test_hc_eqp_001_download_questions_equal_preview_after_strict_redaction() -> None:
    """HC-EQP-001: Questions + Trends on: the download carries exactly the previewed questions, redacted."""
    with _client() as client:
        preview = _preview(client)
        text = _download(client, _generate(client))
    # Not vacuous: the preview has the sources the old download call lacked.
    assert {q["source_kind"] for q in preview} >= {"observation", "trend", "care_task", "entity"}
    expected = {_strict(q["question"]) for q in preview}
    assert _text_questions(text) == expected
    assert TASK_MARK in text and ENTITY_MARK in text


@pytest.mark.parametrize("fmt", ["text", "html", "pdf"])
def test_hc_eqp_002_canary_emails_absent_from_every_download_format(
    fmt: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HC-EQP-002: the new question sources still go through strict redaction before the store."""
    if fmt == "pdf":
        _install_capturing_weasyprint(monkeypatch)
    with _client(CLEAN_ROWS) as client:
        summary_id = _generate(client)
        body = _download(client, summary_id, fmt)
        stored = export_api._summary_store[summary_id]
    assert TASK_MARK in body and ENTITY_MARK in body  # the questions are there, the canaries are not
    for canary in CANARIES:
        assert canary not in body
        assert canary not in repr(stored["questions"])
    assert stored["redaction_count"] >= len(CANARIES)


def test_hc_eqp_003_trends_off_drops_trend_questions_and_keeps_the_rest() -> None:
    """HC-EQP-003: Trends off: no stored trend question; the rest equals the preview minus its trend questions."""
    with _client() as client:
        preview = _preview(client)
        summary_id = _generate(client, trends=False)
        text = _download(client, summary_id)
        stored = export_api._summary_store[summary_id]["questions"]
    assert any(q["source_kind"] == "trend" for q in preview)  # not vacuous
    assert stored and all(q["source_kind"] != "trend" for q in stored)
    expected = {_strict(q["question"]) for q in preview if q["source_kind"] != "trend"}
    assert _text_questions(text) == expected
    assert {q["source_kind"] for q in stored} >= {"care_task", "entity"}


def test_hc_eqp_004_post_questions_is_unchanged() -> None:
    """HC-EQP-004: the preview route returns what it did before the refactor, and audits the same count."""
    with _client() as client:
        preview = _preview(client)
        audit_calls = [
            c.kwargs for c in export_api.log_export_event.call_args_list
            if c.kwargs.get("export_type") == "questions"
        ]
    assert [(q["category"], q["source_kind"]) for q in preview] == [
        ("abnormal", "observation"),
        ("abnormal", "observation"),
        ("abnormal", "observation"),
        ("trend", "trend"),
        ("clarification", "care_task"),
        ("referral", "entity"),
    ]
    assert audit_calls and audit_calls[-1]["details"] == {"question_count": len(preview)}
