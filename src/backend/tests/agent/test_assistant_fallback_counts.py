"""FALLBACK-COUNT-50: the no-LLM fallbacks report the true count, not the 50-row cap.

HTTP-level (route_client) so the real Depends graph runs. Fixture shape copies
test_aet_fallback_label.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import api.assistant as A
from api.assistant import router as assistant_router
from core.auth import get_profile_db_session
from models import chat_session, model_settings  # noqa: F401  register tables
from modules.rag import ModelUnavailableError
from tests.agent.conftest import (
    seed_care_task,
    seed_document,
    seed_medication_change_entity,
)
from tests.support.routes import route_client

TASK_Q = "Which follow-up tasks are open?"
MED_Q = "Show all medication changes"
CLAUSE = "Showing the 50 most recent."


def _post(session_maker, question: str):
    rag = MagicMock()

    async def _boom(*a, **k):
        raise ModelUnavailableError("no model")

    rag.query = _boom
    patches = [
        patch.object(A, "is_agent_enabled", return_value=False),
        patch.object(A, "get_rag_module", return_value=rag),
    ]
    for p in patches:
        p.start()
    try:
        with route_client(assistant_router, "/assistant") as client:

            async def _override():
                async with session_maker() as s:
                    yield s

            client.app.dependency_overrides[get_profile_db_session] = _override
            resp = client.post("/assistant/chat", json={"question": question})
    finally:
        for p in patches:
            p.stop()
    assert resp.status_code == 200, resp.text
    seg = next(s for s in resp.json()["segments"] if s["segment_type"] == "report_facts")
    header, *lines = seg["content"].split("\n")
    return header, lines, seg["citations"]


async def _seed_tasks(maker, n_open: int, n_done: int = 0):
    for i in range(n_open):
        await seed_care_task(maker, title=f"Task {i}")
    for i in range(n_done):
        await seed_care_task(maker, title=f"Done {i}", status="done")


async def _seed_changes(maker, n: int):
    doc_id = await seed_document(maker, profile_id="p1")
    for i in range(n):
        await seed_medication_change_entity(maker, doc_id=doc_id, entity_value=f"Change {i}")


@pytest.mark.asyncio
async def test_hc_afc_001_care_tasks_over_cap_report_true_total(agent_profile_db):
    await _seed_tasks(agent_profile_db, 51)
    header, lines, cites = _post(agent_profile_db, TASK_Q)
    assert header == f"You have 51 open follow-up items. {CLAUSE}"
    assert len(lines) == 50
    assert len(cites) == 50


@pytest.mark.asyncio
async def test_hc_afc_002_care_tasks_at_cap_no_clause(agent_profile_db):
    await _seed_tasks(agent_profile_db, 50)
    header, lines, _ = _post(agent_profile_db, TASK_Q)
    assert header == "You have 50 open follow-up items."
    assert CLAUSE not in header
    assert len(lines) == 50


@pytest.mark.asyncio
async def test_hc_afc_003_med_changes_over_cap_report_true_total(agent_profile_db):
    await _seed_changes(agent_profile_db, 51)
    header, lines, cites = _post(agent_profile_db, MED_Q)
    assert header == f"You have 51 recorded medication changes. {CLAUSE}"
    assert len(lines) == 50
    assert len(cites) == 50


@pytest.mark.asyncio
async def test_hc_afc_004_med_changes_under_cap_exact(agent_profile_db):
    await _seed_changes(agent_profile_db, 49)
    header, lines, _ = _post(agent_profile_db, MED_Q)
    assert header == "You have 49 recorded medication changes."
    assert len(lines) == 49


@pytest.mark.asyncio
async def test_hc_afc_005_total_uses_the_same_filter(agent_profile_db):
    await _seed_tasks(agent_profile_db, 51, n_done=6)
    header, lines, _ = _post(agent_profile_db, TASK_Q)
    assert header.startswith("You have 51 open follow-up items.")
    assert len(lines) == 50


@pytest.mark.asyncio
async def test_hc_afc_006_zero_open_tasks_unchanged(agent_profile_db):
    header, lines, _ = _post(agent_profile_db, TASK_Q)
    assert header == "You have 0 open follow-up items."
    assert lines == []
