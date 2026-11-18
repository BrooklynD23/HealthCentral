"""PROFILE-MEMORY-PURGE (owner answer MEM-PURGE, 2026-11-11): lock, logout, profile delete
and restore clear THAT profile's decrypted page images and cached assistant answers, through
`purge_profile_exports`, before its no-open-vault early return. Another profile's entries stay.

MEM-PURGE-RACE (HC-MEMP-010..013): an answer is not cached when a purge lands after the request's
cache miss and before its put (a lock landing mid-answer). A purge that lands before the miss
(during the DB awaits ahead of `get_cached`) is not caught; the window is milliseconds.

Would not notice: the page-image cache re-filling after a purge (MEM-PURGE-RACE-PAGES); a get in
one task and the put in another; several worker processes (the cache is per process); in-memory
stores not named here; the synthetic reset route (calls no purge).
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

import api.documents as docs_api
import api.export as export_api
import modules.agent.cache as answer_cache
from api.export import purge_profile_exports
from tests.test_export_store_purge import _db_with_profile, _profiles_client

A, B = "profile-a", "profile-b"


@pytest.fixture(autouse=True)
def _clean():
    docs_api._page_image_cache.clear()
    answer_cache.clear_cache()
    yield
    docs_api._page_image_cache.clear()
    answer_cache.clear_cache()


def _key(pid: str) -> answer_cache.CacheKey:
    return answer_cache.CacheKey(normalized_question="is my ldl high", profile_version="v1",
                                 profile_id=pid, tz_name="UTC")


def _seed() -> None:
    docs_api._page_image_cache_set((A, "doc-1", 1, 150), b"PNG-A")
    docs_api._page_image_cache_set((A, "doc-1", 2, 150), b"PNG-A2")
    docs_api._page_image_cache_set((B, "doc-2", 1, 150), b"PNG-B")
    answer_cache._cache[_key(A)] = "ANSWER-A"
    answer_cache._cache[_key(B)] = "ANSWER-B"


def _left() -> tuple[set[str], set[str]]:
    return ({k[0] for k in docs_api._page_image_cache},
            {k.profile_id for k in answer_cache._cache})


@pytest.mark.asyncio
async def test_hc_memp_001_purge_drops_only_that_profiles_images_and_answers():
    _seed()
    await purge_profile_exports(A)  # no open vault: the early-return path
    images, answers = _left()
    assert images == {B} and answers == {B}
    assert docs_api._page_image_cache_get((B, "doc-2", 1, 150)) == b"PNG-B"
    assert answer_cache.get_cached(_key(B)) == "ANSWER-B"


def test_hc_memp_002_lock_over_http_clears_both_caches_for_that_profile_only():
    _seed()
    profile = SimpleNamespace(id=A, display_name="T", is_locked=False, password_hash="x",
                              created_at=datetime(2026, 11, 7, 12, 0, 0), last_accessed_at=None)
    with _profiles_client(A, _db_with_profile(profile)) as prof:
        assert prof.post(f"/profiles/{A}/lock").status_code == 200
    assert _left() == ({B}, {B})


def test_hc_memp_002b_logout_over_http_clears_both_caches_for_that_profile_only():
    _seed()
    with _profiles_client(A, _db_with_profile(None)) as prof:
        assert prof.post("/profiles/logout").status_code == 200
    assert _left() == ({B}, {B})


@pytest.mark.asyncio
async def test_hc_memp_003_return_value_is_still_the_export_count_only(monkeypatch):
    monkeypatch.setattr(export_api, "_summary_store", {"s1": {"profile_id": A}})
    _seed()
    assert await purge_profile_exports(A) == 1
    assert _left() == ({B}, {B})


# --- MEM-PURGE-RACE: an answer that finishes after a purge is not cached --------------------

def test_hc_memp_010_put_after_purge_is_dropped():
    k = _key(A)
    assert answer_cache.get_cached(k) is None  # request starts: miss
    answer_cache.purge_profile(A)  # the lock lands while the agent thinks
    answer_cache.put_cached(k, "LATE-ANSWER")
    assert answer_cache.get_cached(k) is None
    assert A not in {x.profile_id for x in answer_cache._cache}


def test_hc_memp_011_fresh_put_after_purge_is_kept():
    k = _key(A)
    answer_cache.purge_profile(A)  # purge first, request starts after it
    assert answer_cache.get_cached(k) is None
    answer_cache.put_cached(k, "FRESH")
    assert answer_cache.get_cached(k) == "FRESH"
    # a put with no prior get (several callers do this) still stores
    k2 = answer_cache.CacheKey(normalized_question="other", profile_version="v1",
                               profile_id=A, tz_name="UTC")
    answer_cache.put_cached(k2, "NO-GET")
    assert answer_cache.get_cached(k2) == "NO-GET"


def test_hc_memp_012_purge_of_another_profile_does_not_drop_the_put():
    k = _key(A)
    assert answer_cache.get_cached(k) is None
    answer_cache.purge_profile(B)
    answer_cache.put_cached(k, "A-ANSWER")
    assert answer_cache.get_cached(k) == "A-ANSWER"


def test_hc_memp_012b_a_dropped_put_does_not_poison_the_next_request():
    k = _key(A)
    assert answer_cache.get_cached(k) is None
    answer_cache.purge_profile(A)
    answer_cache.put_cached(k, "LATE")  # dropped
    assert answer_cache.get_cached(k) is None  # new request starts after the purge
    answer_cache.put_cached(k, "NEXT")
    assert answer_cache.get_cached(k) == "NEXT"


def test_hc_memp_012c_clear_cache_resets_this_contexts_mark():
    k = _key(A)
    answer_cache.get_cached(k)
    answer_cache.purge_profile(A)
    answer_cache.clear_cache()
    answer_cache.put_cached(k, "AFTER-CLEAR")  # mark was reset, so this is a plain put
    assert answer_cache.get_cached(k) == "AFTER-CLEAR"


def test_hc_memp_012d_clear_cache_elsewhere_does_not_revive_a_purged_put():
    import contextvars

    k = _key(A)
    assert answer_cache.get_cached(k) is None
    answer_cache.purge_profile(A)
    contextvars.copy_context().run(answer_cache.clear_cache)  # another context: our mark stays
    answer_cache.put_cached(k, "LATE")
    assert answer_cache.get_cached(k) is None


def test_hc_memp_012e_clear_cache_mid_request_drops_the_put():
    import contextvars

    k = _key(A)
    assert answer_cache.get_cached(k) is None
    contextvars.copy_context().run(answer_cache.clear_cache)
    answer_cache.put_cached(k, "LATE")
    assert answer_cache.get_cached(k) is None


def test_hc_memp_012f_a_hit_clears_a_stale_mark():
    k, k2 = _key(A), answer_cache.CacheKey(normalized_question="x", profile_version="v1",
                                           profile_id=A, tz_name="UTC")
    answer_cache.get_cached(k)  # miss, request fails, no put
    answer_cache.purge_profile(A)
    answer_cache._cache[k2] = "HIT"
    assert answer_cache.get_cached(k2) == "HIT"  # overwrites the mark with None
    answer_cache.put_cached(k, "PLAIN")
    assert answer_cache.get_cached(k) == "PLAIN"


def _chat_with_agent(monkeypatch, agent):
    import asyncio
    from unittest.mock import patch

    import api.assistant as assistant_api
    from core.auth import get_profile_db_session
    from tests.support.routes import route_client
    from tests.test_assist_agent_dates_http import _make_db

    db, engine = asyncio.run(_make_db())
    monkeypatch.setattr(assistant_api, "run_agent", agent)
    try:
        with patch.object(assistant_api, "is_agent_enabled", return_value=True):
            with route_client(assistant_api.router, "/assistant", profile_id="profile-a") as client:
                async def _override():
                    return db

                client.app.dependency_overrides[get_profile_db_session] = _override
                resp = client.post("/assistant/chat", json={"question": "what is my glucose?"})
        assert resp.status_code == 200, resp.text
        return resp.json()
    finally:
        asyncio.run(db.close())
        asyncio.run(engine.dispose())


def _late_terminal():
    from modules.agent.schemas import AgentTerminal

    return AgentTerminal(terminal="answer", text="LATE-ANSWER", citations=[], run_id="r")


def test_hc_memp_013_lock_landing_mid_answer_leaves_no_cache_entry_over_http(monkeypatch):
    async def _agent_then_lock(question, ctx):
        await purge_profile_exports(ctx.profile_id)  # the lock lands during the LLM call
        return _late_terminal()

    body = _chat_with_agent(monkeypatch, _agent_then_lock)
    assert "LATE-ANSWER" in body["full_response"]  # the agent path served it (no legacy fallback)
    assert "profile-a" not in {k.profile_id for k in answer_cache._cache}


def test_hc_memp_013b_control_same_request_without_a_lock_is_cached(monkeypatch):
    async def _agent(question, ctx):
        return _late_terminal()

    body = _chat_with_agent(monkeypatch, _agent)
    assert "LATE-ANSWER" in body["full_response"]
    assert "profile-a" in {k.profile_id for k in answer_cache._cache}
