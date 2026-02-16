"""Tests for search API pagination bounds."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.search import router as search_router
from api import search as search_api
from core.auth import Session, require_auth, get_profile_db_session
from core.database import get_db
from modules.search import SearchResult, SearchResponse


class _FakeMasterDb:
    def add(self, _obj):
        return None

    async def commit(self):
        return None


def _build_search_app(profile_id: str):
    app = FastAPI()
    app.include_router(search_router, prefix="/search")

    async def _override_auth():
        return Session(
            profile_id=profile_id,
            profile_name="Search Test",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    async def _override_profile_db():
        return object()

    async def _override_master_db():
        return _FakeMasterDb()

    app.dependency_overrides[require_auth] = _override_auth
    app.dependency_overrides[get_profile_db_session] = _override_profile_db
    app.dependency_overrides[get_db] = _override_master_db
    return app


class _FakeSearchModule:
    def __init__(self):
        self.fulltext_limit = None

    async def search_fulltext(self, _q, _profile_db, _profile_id, _filters, limit):
        self.fulltext_limit = limit
        return [
            SearchResult(
                id=f"result-{i}",
                type="chunk",
                title=f"Result {i}",
                score=1.0,
                snippet=f"Snippet {i}",
            )
            for i in range(limit)
        ]

    async def search_semantic(self, _q, _profile_db, _profile_id, top_k):
        return [
            SearchResult(
                id=f"semantic-{i}",
                type="chunk",
                title=f"Semantic {i}",
                score=1.0,
                snippet=f"Snippet {i}",
            )
            for i in range(top_k)
        ]

    async def search_hybrid(self, _q, _profile_db, _profile_id, _filters, limit):
        results = [
            SearchResult(
                id=f"hybrid-{i}",
                type="chunk",
                title=f"Hybrid {i}",
                score=1.0,
                snippet=f"Snippet {i}",
            )
            for i in range(limit)
        ]
        return SearchResponse(results=results, total_count=len(results), query="q", mode="hybrid")


def test_search_caps_limit_plus_offset_window(monkeypatch):
    profile_id = str(uuid.uuid4())
    app = _build_search_app(profile_id)
    fake_search_module = _FakeSearchModule()

    monkeypatch.setattr(search_api, "SearchModule", lambda: fake_search_module)
    monkeypatch.setattr(search_api, "log_search_event", AsyncMock())

    with TestClient(app) as client:
        response = client.get(
            "/search",
            params={"q": "glucose", "mode": "text", "limit": 100, "offset": 980},
        )

    assert response.status_code == 200
    assert fake_search_module.fulltext_limit == search_api.MAX_SEARCH_WINDOW
    assert len(response.json()["results"]) == 20


def test_search_rejects_offset_above_max():
    profile_id = str(uuid.uuid4())
    app = _build_search_app(profile_id)

    with TestClient(app) as client:
        response = client.get(
            "/search",
            params={"q": "glucose", "offset": search_api.MAX_SEARCH_OFFSET + 1},
        )

    assert response.status_code == 422
