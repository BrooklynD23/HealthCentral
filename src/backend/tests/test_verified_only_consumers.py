"""W-3 / owner decision D4 (2026-09-27): verified-only legacy RAG, labelled trends.

HC-VER-001..004. Retrieval tests use a REAL in-memory SQLite session: every
pre-existing legacy-retrieval test uses a fake session that ignores WHERE
clauses, so it cannot see a verification filter (recurring-failures #1).
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

import api.observations as observations_api  # noqa: E402
from api.observations import router as observations_router  # noqa: E402
from core.auth import get_profile_db_session  # noqa: E402
from core.profile_database import ProfileDatabaseBase  # noqa: E402
from models import Chunk, Document, Embedding, Observation  # noqa: E402
from modules.rag import RAGModule  # noqa: E402
from tests.support.routes import route_client  # noqa: E402

PROFILE = "profile-w03"


# ── HC-VER-002: trends over HTTP ─────────────────────────────────────────────

class _Scalars:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def all(self) -> list:
        return self._rows


class _Result:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def scalars(self) -> _Scalars:
        return _Scalars(self._rows)


class _FakeProfileDb:
    """Returns the seeded rows whatever the statement: fine here, because the
    trends route must NOT filter by verification (D4: trends may show them)."""

    def __init__(self, rows: list) -> None:
        self._rows = rows

    async def execute(self, _stmt) -> _Result:
        return _Result(self._rows)


def _trend_row(*, value: float, collected_at: datetime, user_verified: bool) -> SimpleNamespace:
    return SimpleNamespace(
        id=str(uuid.uuid4()), profile_id=PROFILE, doc_id="doc-a",
        analyte_canonical="glucose", analyte_raw="Glucose",
        value=value, value_text=None, unit="mg/dL",
        ref_low=70.0, ref_high=99.0, ref_range_text=None,
        flag=None, is_abnormal=False, collected_at=collected_at,
        user_verified=user_verified, extraction_confidence=0.9,
        source_page=None, source_bbox_json=None,
    )


def test_hc_ver_002_trend_points_carry_user_verified_over_http(monkeypatch) -> None:
    rows = [
        _trend_row(value=90.0, collected_at=datetime(2025, 1, 10), user_verified=True),
        _trend_row(value=130.0, collected_at=datetime(2025, 6, 10), user_verified=False),
    ]
    monkeypatch.setattr(
        observations_api, "log_observation_event", AsyncMock(return_value=object())
    )

    async def _override_profile_db():
        return _FakeProfileDb(rows)

    with route_client(observations_router, "/observations", profile_id=PROFILE) as client:
        # route_client overrides auth + master DB only; add the profile DB here
        # rather than editing tests/support/routes.py (owned by P7 / G-B1).
        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        response = client.get("/observations/trends/glucose")

    assert response.status_code == 200, response.text
    points = response.json()["data_points"]
    # Both points are still shown (D4: trends MAY show unverified) and each
    # carries its own row's flag — a constant True or False fails this.
    assert [(p["value"], p["user_verified"]) for p in points] == [
        (90.0, True),
        (130.0, False),
    ]