"""MEM-PURGE-RACE-PAGES (HC-MPRP-001..006): a page picture rendered across a profile purge is
not cached. `get_page_image` misses, renders (slow), audits, then puts; a lock or logout that runs
`purge_page_images` in between must not be undone by the put (mirror of MEM-PURGE-RACE, #629, for
the answer cache). The racing request still gets its picture: it was authorized and audited
before the purge finished. Only the cache entry goes.

Route tests go through HTTP (`route_client`). The render is stubbed: `pdfplumber.open` yields a
fake one-page PDF whose `to_image().save()` writes `b"PNG"` and can run a hook (the purge).

Would not notice: a purge that lands before the cache miss (during the DB awaits above it; the
window is milliseconds); a get in one task and the put in another; several worker processes (the
cache is per process); the answer cache (covered by test_profile_memory_purge.py).
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import api.documents as docs_api
from api.documents import router as documents_router
from tests.support.routes import route_client

A, B = "profile-a", "profile-b"
DOC = "11111111-1111-4111-8111-111111111111"
URL = f"/documents/{DOC}/pages/1/image"
KEY = (A, DOC, 1, 150)


def _reset_page_cache() -> None:
    docs_api._page_image_cache.clear()
    # absent on the unchanged code, so the RED run fails on behaviour, not on this fixture
    getattr(docs_api, "_page_image_purged_at", {}).clear()


@pytest.fixture(autouse=True)
def _clean():
    _reset_page_cache()
    yield
    _reset_page_cache()


@pytest_asyncio.fixture
async def sessions(tmp_path):
    from core.profile_database import ProfileDatabaseBase
    from models import Document

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'vault.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        session.add(
            Document(
                id=DOC, profile_id=A, path_hash="p" * 64, content_hash="c" * 64,
                doc_type="lab_pdf", status="parsed", imported_at=datetime(2026, 1, 1),
            )
        )
        await session.commit()
    try:
        yield maker
    finally:
        await engine.dispose()


class _Renders:
    """Counts renders; `on_render` runs inside `save()`, i.e. mid-render."""

    def __init__(self) -> None:
        self.count = 0
        self.on_render = None


@pytest.fixture
def renders(monkeypatch):
    import pdfplumber

    state = _Renders()

    class _Img:
        def save(self, buf, format="PNG"):
            state.count += 1
            if state.on_render is not None:
                state.on_render()
            buf.write(b"PNG")

    class _Page:
        def to_image(self, resolution=150):
            return _Img()

    class _Pdf:
        pages = [_Page()]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(docs_api, "get_decrypted_document", lambda _pid, _did: object())
    monkeypatch.setattr(pdfplumber, "open", lambda _doc: _Pdf())
    return state


@contextmanager
def _client(sessions):
    with route_client(documents_router, "/documents", profile_id=A, profile_db=sessions) as client:
        yield client


def _get(client):
    resp = client.get(URL)
    assert resp.status_code == 200
    assert resp.content == b"PNG"
    return resp


def test_hc_mprp_001_purge_during_render_drops_the_put_but_still_serves(sessions, renders):
    renders.on_render = lambda: docs_api.purge_page_images(A)
    with _client(sessions) as client:
        _get(client)
        assert not [k for k in docs_api._page_image_cache if k[0] == A]
        renders.on_render = None
        _get(client)  # nothing cached: renders again
    assert renders.count == 2


def test_hc_mprp_002_control_without_purge_is_cached(sessions, renders):
    with _client(sessions) as client:
        _get(client)
        _get(client)
    assert renders.count == 1
    assert KEY in docs_api._page_image_cache


def test_hc_mprp_003_purge_of_another_profile_keeps_the_put(sessions, renders):
    renders.on_render = lambda: docs_api.purge_page_images(B)
    with _client(sessions) as client:
        _get(client)
        _get(client)
    assert renders.count == 1
    assert KEY in docs_api._page_image_cache


def test_hc_mprp_004_purge_with_nothing_cached_still_drops_the_in_flight_put(sessions, renders):
    assert not docs_api._page_image_cache
    purged: list[int] = []
    renders.on_render = lambda: purged.append(docs_api.purge_page_images(A))
    with _client(sessions) as client:
        _get(client)
    assert purged == [0]
    assert not docs_api._page_image_cache


def test_hc_mprp_005_dropped_put_does_not_poison_the_next_request(sessions, renders):
    renders.on_render = lambda: docs_api.purge_page_images(A)
    with _client(sessions) as client:
        _get(client)  # raced: not cached
        renders.on_render = None
        _get(client)  # fresh render, no purge: cached
        _get(client)  # served from cache
    assert renders.count == 2
    assert KEY in docs_api._page_image_cache


def test_hc_mprp_006_set_without_a_mark_stores_even_after_a_purge():
    docs_api.purge_page_images(A)
    docs_api._page_image_cache_set(KEY, b"PNG")  # fail-open: existing callers pass no mark
    assert docs_api._page_image_cache_get(KEY) == b"PNG"
