"""PROFILE-MEMORY-PURGE (owner answer MEM-PURGE, 2026-11-11): lock, logout, profile delete
and restore clear THAT profile's decrypted page images and cached assistant answers, through
`purge_profile_exports`, before its no-open-vault early return. Another profile's entries stay.

Would not notice: a request already in flight when the purge runs can re-fill a cache after it
(not tested); in-memory stores not named here; the synthetic reset route (calls no purge).
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
