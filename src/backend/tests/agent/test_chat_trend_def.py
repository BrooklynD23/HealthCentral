"""CHAT-TREND-DEF (owner CTD-DEF (a)): compute_trend direction is first-vs-last
with a 5% band, the same rule as the Trends page (api/observations.py)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from api.observations import router as observations_router
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models.document import Document
from models.observation import Observation
from modules.agent.graph import RunContext
from modules.agent.state import ChatFilters
from modules.agent.tools.compute_trend import ComputeTrendInput, ComputeTrendTool
from tests.support.routes import route_client

PROFILE = "profile-a"
T0 = datetime(2026, 1, 1, 12, 0, 0)


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    db = AsyncSession(engine, expire_on_commit=False)
    db.add(Document(
        id="doc-ctd", profile_id=PROFILE, path_hash="h", content_hash="h",
        doc_type="pdf", status="verified", collection_date=T0, imported_at=T0,
    ))
    await db.commit()
    try:
        yield db
    finally:
        await db.close()
        await engine.dispose()


async def _seed(db, values, *, verified=True, prefix="o"):
    for i, v in enumerate(values):
        when = T0 + timedelta(days=30 * i)
        db.add(Observation(
            id=f"{prefix}-{i}", profile_id=PROFILE, doc_id="doc-ctd",
            analyte_canonical="glucose", analyte_raw="Glucose", value=v, unit="mg/dL",
            collected_at=when, user_verified=verified, verified_at=when if verified else None,
        ))
    await db.commit()


def _ctx(db) -> RunContext:
    @asynccontextmanager
    async def _factory():
        yield db

    return RunContext(profile_id=PROFILE, run_id="run-ctd", db_session_factory=_factory, filters=ChatFilters())


async def _direction(db) -> str:
    out = await ComputeTrendTool().run(ComputeTrendInput(analyte="glucose"), _ctx(db))
    return out.direction


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "values,expected",
    [([100.0, 103.0], "flat"), ([100.0, 110.0], "up"), ([100.0, 90.0], "down")],
    ids=["within_band_flat", "up", "down"],
)
async def test_hc_ctd_001_five_percent_band(profile_db, values, expected):
    await _seed(profile_db, values)
    assert await _direction(profile_db) == expected


@pytest.mark.asyncio
async def test_hc_ctd_002_first_vs_last_not_last_step(profile_db):
    # 100 -> 150 -> 104: last step is down, overall first-vs-last is +4% => flat.
    await _seed(profile_db, [100.0, 150.0, 104.0])
    assert await _direction(profile_db) == "flat"


@pytest.mark.asyncio
async def test_hc_ctd_003_agrees_with_trends_page(profile_db):
    cases = [
        ([100.0, 103.0], "stable", "flat"),
        ([100.0, 106.0], "increased", "up"),
        ([100.0, 94.0], "decreased", "down"),
        ([0.0, 5.0], "stable", "flat"),  # zero base: no division, flat on both sides
    ]
    for values, word, expected in cases:
        await profile_db.execute(delete(Observation))
        await profile_db.commit()
        await _seed(profile_db, values)
        agent_direction = await _direction(profile_db)

        with route_client(observations_router, "/observations", profile_id=PROFILE) as client:
            async def _override():
                return profile_db

            client.app.dependency_overrides[get_profile_db_session] = _override
            resp = client.get("/observations/trends/glucose")
        assert resp.status_code == 200, resp.text
        summary = resp.json()["summary"]
        assert f"has {word}" in summary, (values, summary)
        assert agent_direction == expected, (values, agent_direction)
