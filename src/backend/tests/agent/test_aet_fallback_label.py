"""AET-FALLBACK-LABEL: care-task text carries the AET-WORDING label on both paths.

HTTP-level (route_client) so the real Depends graph runs. HC-AFL-001/002 hit the
no-LLM fallback (_build_care_task_fallback); HC-AFL-003 the real agent path.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

import api.assistant as A
from api.assistant import router as assistant_router
from core.auth import get_profile_db_session
from models import chat_session, model_settings  # noqa: F401  register tables
from modules.rag import ModelUnavailableError
from tests.agent.conftest import seed_care_task
from tests.support.routes import route_client

LABEL = "Open follow-up you saved (wording taken from your documents, not checked): "
QUESTION = "Which follow-up tasks are open?"


async def _seed(session_maker):
    await seed_care_task(
        session_maker, title="Book retest", due_date=date(2026, 12, 1),
        source_quote="repeat labs in 6 weeks",
    )
    await seed_care_task(session_maker, title="Call clinic")
    await seed_care_task(session_maker, title="Already finished", status="done")


def _post(session_maker, *, agent: bool, serve_raises: bool = False, spy=None):
    rag = MagicMock()

    async def _boom(*a, **k):
        raise ModelUnavailableError("no model")

    rag.query = _boom
    patches = [
        patch.object(A, "is_agent_enabled", return_value=agent),
        patch.object(A, "get_rag_module", return_value=rag),
    ]
    if serve_raises:
        patches.append(patch.object(A, "_serve_via_agent", side_effect=RuntimeError("x")))
    if spy is not None:
        patches.append(patch.object(A, "_append_turns", spy))
    for p in patches:
        p.start()
    try:
        with route_client(assistant_router, "/assistant") as client:

            async def _override():
                async with session_maker() as s:
                    yield s

            client.app.dependency_overrides[get_profile_db_session] = _override
            resp = client.post("/assistant/chat", json={"question": QUESTION})
    finally:
        for p in patches:
            p.stop()
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
@pytest.mark.parametrize("agent,serve_raises", [(False, False), (True, True)])
async def test_hc_afl_001_fallback_lines_carry_label(agent_profile_db, agent, serve_raises):
    await _seed(agent_profile_db)
    body = _post(agent_profile_db, agent=agent, serve_raises=serve_raises)
    seg = next(s for s in body["segments"] if s["segment_type"] == "report_facts")
    header, *lines = seg["content"].split("\n")
    assert header == "You have 2 open follow-up items."
    assert len(lines) == 2
    assert all(line.startswith("- " + LABEL) for line in lines)
    assert len(seg["citations"]) == 2
    assert "Already finished" not in body["full_response"]


@pytest.mark.asyncio
async def test_hc_afl_002_saved_turn_matches_response(agent_profile_db):
    await _seed(agent_profile_db)
    saved: list[str] = []
    real = A._append_turns

    async def spy(*args, **kwargs):
        saved.append(kwargs["assistant_content"])
        return await real(*args, **kwargs)

    body = _post(agent_profile_db, agent=False, spy=spy)
    assert saved == [body["full_response"]]
    assert saved[0].count(LABEL) == 2


@pytest.mark.asyncio
async def test_hc_afl_003_agent_path_label(agent_profile_db):
    await _seed(agent_profile_db)
    with patch.object(A, "is_agent_enabled", return_value=True):
        with route_client(assistant_router, "/assistant") as client:

            async def _override():
                async with agent_profile_db() as s:
                    yield s

            client.app.dependency_overrides[get_profile_db_session] = _override
            resp = client.post("/assistant/chat", json={"question": QUESTION})
    assert resp.status_code == 200, resp.text
    full = resp.json()["full_response"]
    assert full.count(LABEL) == 2
    assert "from your documents, not verified by you" not in full
