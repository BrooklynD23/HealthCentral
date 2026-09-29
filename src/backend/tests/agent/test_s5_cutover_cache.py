"""Sprint 5 — Cutover + cache. Stories S5-1..S5-3."""

from __future__ import annotations

import pytest

from modules.agent.cache import CacheKey


# --- live: cache key REQUIRES profile_version (no version-blind caching) -----

def test_s5_2_cache_key_requires_profile_version():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CacheKey(normalized_question="why is my ldl 138?")  # missing profile_version

    # S-CACHE: profile_id is required too, so two profiles can never collide
    # on the same key (HC-CACHE-ISO-001/002).
    with pytest.raises(ValidationError):
        CacheKey(normalized_question="why is my ldl 138?", profile_version="v1")  # missing profile_id


def test_s5_2_cache_key_distinguishes_versions():
    a = CacheKey(normalized_question="q", profile_version="v1", profile_id="p1")
    b = CacheKey(normalized_question="q", profile_version="v2", profile_id="p1")
    assert a != b  # new verified data (version bump) is a different key


@pytest.mark.asyncio
async def test_s5_1_cutover_keeps_legacy_fallback():
    """S5-1: the agent is the default path, but the legacy ``rag.query`` path
    stays reachable on (a) an explicit ``agent_enabled=False`` settings row
    and (b) ANY exception raised while serving via the agent — the one
    release safety net (AC). Both scenarios must still persist the
    user+assistant turn and return the same ``ChatResponse`` shape
    (session_id/turn_id) as the agent path would.
    """
    from dataclasses import dataclass, field
    from unittest.mock import AsyncMock, MagicMock, patch

    import api.assistant as A
    from api.assistant import ChatRequest
    from modules.rag import ResponseSegment, ValidatedResponse, VerificationMetadata
    from tests.test_chat_sessions import _make_session

    @dataclass
    class _FakeUserModelSettings:
        agent_enabled: bool = False

    def _legacy_rag_result():
        return ValidatedResponse(
            segments=[ResponseSegment(segment_type="report_facts", content="Legacy answer")],
            is_valid=True,
            validation_errors=[],
            insufficient_context=False,
            insufficient_reasons=[],
            verification=VerificationMetadata(),
        )

    async def _run_chat_with(*, user_model_settings, serve_via_agent_side_effect):
        chat_session = _make_session(profile_id="prof-1")
        auth = MagicMock()
        auth.profile_id = "prof-1"
        profile_db = AsyncMock()
        master_db = AsyncMock()

        rag = MagicMock()
        rag.query = AsyncMock(return_value=_legacy_rag_result())

        with patch.object(A, "get_rag_module", return_value=rag), \
             patch.object(A, "_get_or_create_session", AsyncMock(return_value=chat_session)), \
             patch.object(A, "_load_session_history", AsyncMock(return_value=[])), \
             patch.object(A, "_effective_use_memory", AsyncMock(return_value=False)), \
             patch.object(A, "_get_user_model_settings", AsyncMock(return_value=user_model_settings)), \
             patch.object(A, "_serve_via_agent", AsyncMock(side_effect=serve_via_agent_side_effect)), \
             patch.object(A, "_append_turns", AsyncMock(return_value="assist-turn-id")) as mock_append:
            result = await A.chat(
                ChatRequest(question="How is my glucose?"),
                auth,
                profile_db=profile_db,
                db=master_db,
            )

        assert result.session_id == chat_session.id
        assert result.turn_id == "assist-turn-id"
        assert result.full_response  # legacy path produced a real answer
        mock_append.assert_awaited_once()
        kwargs = mock_append.await_args.kwargs
        assert kwargs["assistant_content"] == result.full_response
        profile_db.commit.assert_awaited()
        rag.query.assert_awaited_once()
        return result

    # (a) explicit agent_enabled=False -> legacy path used directly; agent
    # is never even called.
    def _agent_should_not_run(*args, **kwargs):
        raise AssertionError("agent path must not run when agent_enabled=False")

    await _run_chat_with(
        user_model_settings=_FakeUserModelSettings(agent_enabled=False),
        serve_via_agent_side_effect=_agent_should_not_run,
    )

    # (b) flag ON, but the agent raises -> falls back to the legacy path
    # (the one-release safety net for ANY agent exception).
    await _run_chat_with(
        user_model_settings=_FakeUserModelSettings(agent_enabled=True),
        serve_via_agent_side_effect=RuntimeError("agent blew up"),
    )


def test_s5_2_cache_hit_and_invalidation():
    """S5-2: put under version 1 -> hit on repeat; after a verified-data
    change (version 2) -> miss (never serve a stale answer for changed
    data — the version bump itself IS the invalidation).
    """
    from modules.agent.cache import (
        CacheKey,
        clear_cache,
        get_cached,
        normalize_question,
        put_cached,
    )
    from modules.agent.schemas import AgentTerminal

    clear_cache()
    try:
        question = "  Why Is My LDL  138?  "
        normalized = normalize_question(question)
        assert normalized == "why is my ldl 138?"

        key_v1 = CacheKey(normalized_question=normalized, profile_version="v1", profile_id="p1")
        terminal = AgentTerminal(
            terminal="answer", text="Your LDL was 138 mg/dL.", citations=[], run_id="run-1"
        )

        # Miss before anything is stored.
        assert get_cached(key_v1) is None

        put_cached(key_v1, terminal)

        # Repeat question, same version -> hit, same terminal content.
        assert get_cached(key_v1) == terminal

        # New verified data lands -> profile_version bumps to 2 -> different
        # key -> miss, even though the question text is identical.
        key_v2 = CacheKey(normalized_question=normalized, profile_version="v2", profile_id="p1")
        assert get_cached(key_v2) is None

        # The old version's entry is untouched (still a hit under v1).
        assert get_cached(key_v1) == terminal
    finally:
        clear_cache()


@pytest.mark.asyncio
async def test_s5_3_per_node_timing_surfaced(agent_profile_db, make_run_context):
    """S5-3: a real agent run records per-node ``agent.<node>`` timing into
    the shared MetricsCollector, which is exactly what backs
    GET /api/v1/monitoring/metrics — asserting against the collector's
    recorded data IS asserting against what that route would report.
    """
    import uuid
    from datetime import datetime

    from monitoring.metrics import metrics_collector
    from modules.agent.graph import run_agent
    from tests.agent.conftest import seed_document, seed_observation

    session_maker = agent_profile_db
    profile_id = str(uuid.uuid4())
    doc_id = await seed_document(session_maker, profile_id=profile_id)
    await seed_observation(
        session_maker, profile_id=profile_id, doc_id=doc_id,
        analyte="LDL", value=138.0, verified=True,
        collected_at=datetime(2025, 12, 1),
    )

    ctx = make_run_context(session_maker, profile_id=profile_id)

    before = {
        ep.route_template: ep.request_count
        for ep in metrics_collector.get_summary().endpoints
    }

    terminal = await run_agent("What is my LDL?", ctx)
    assert terminal.terminal in ("answer", "abstain", "escalate")

    summary = metrics_collector.get_summary()
    after = {ep.route_template: ep.request_count for ep in summary.endpoints}

    # plan/draft/guard always run for a single-step grounded answer; act runs
    # at least once since LDL was found via query_observations.
    for node in ("plan", "act", "draft", "guard"):
        route = f"agent.{node}"
        assert after.get(route, 0) > before.get(route, 0), (
            f"expected agent.{node} timing to be recorded by run_agent"
        )
        stats = metrics_collector.get_endpoint_stats(route)
        assert stats is not None
        assert stats.p95_ms >= 0.0
