"""CHAT-TREND-DEF (owner CTD-DEF (a)): compute_trend direction is first-vs-last
with a 5% band, the same rule as the Trends page (api/observations.py)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import delete

from api.observations import router as observations_router
from core.auth import get_profile_db_session
from models.observation import Observation
from modules.agent.tools.compute_trend import ComputeTrendInput, ComputeTrendTool
from tests.agent.conftest import seed_document, seed_observation
from tests.support.routes import route_client

PROFILE = "profile-a"
T0 = datetime(2026, 1, 1, 12, 0, 0)


async def _seed(session_maker, values):
    doc_id = await seed_document(session_maker, profile_id=PROFILE, doc_id="doc-ctd")
    for i, v in enumerate(values):
        await seed_observation(
            session_maker, profile_id=PROFILE, doc_id=doc_id, analyte="glucose",
            value=v, verified=True, collected_at=T0 + timedelta(days=30 * i),
        )


async def _direction(session_maker, make_run_context) -> str:
    ctx = make_run_context(session_maker, profile_id=PROFILE)
    out = await ComputeTrendTool().run(ComputeTrendInput(analyte="glucose"), ctx)
    return out.direction


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "values,expected",
    [([100.0, 103.0], "flat"), ([100.0, 110.0], "up"), ([100.0, 90.0], "down")],
    ids=["within_band_flat", "up", "down"],
)
async def test_hc_ctd_001_five_percent_band(agent_profile_db, make_run_context, values, expected):
    await _seed(agent_profile_db, values)
    assert await _direction(agent_profile_db, make_run_context) == expected


@pytest.mark.asyncio
async def test_hc_ctd_002_first_vs_last_not_last_step(agent_profile_db, make_run_context):
    # 100 -> 150 -> 104: last step is down, overall first-vs-last is +4% => flat.
    await _seed(agent_profile_db, [100.0, 150.0, 104.0])
    assert await _direction(agent_profile_db, make_run_context) == "flat"


@pytest.mark.asyncio
async def test_hc_ctd_003_agrees_with_trends_page(agent_profile_db, make_run_context):
    await seed_document(agent_profile_db, profile_id=PROFILE, doc_id="doc-ctd")
    cases = [
        ([100.0, 103.0], "stable", "flat"),
        ([100.0, 106.0], "increased", "up"),
        ([100.0, 94.0], "decreased", "down"),
        ([0.0, 5.0], "stable", "flat"),  # zero base: no division, flat on both sides
        # Band edge: exactly 5% is outside the band (strict < 5), on both sides.
        ([100.0, 105.0], "increased", "up"),
        ([100.0, 95.0], "decreased", "down"),
        ([100.0, 104.9], "stable", "flat"),
        # Negative base: sign comes from delta, not from change_pct.
        ([-10.0, -5.0], "increased", "up"),
    ]
    for values, word, expected in cases:
        async with agent_profile_db() as s:
            await s.execute(delete(Observation))
            await s.commit()
        await _seed_obs_only(agent_profile_db, values)
        agent_direction = await _direction(agent_profile_db, make_run_context)

        with route_client(observations_router, "/observations", profile_id=PROFILE) as client:
            async def _override():
                async with agent_profile_db() as session:
                    yield session

            client.app.dependency_overrides[get_profile_db_session] = _override
            resp = client.get("/observations/trends/glucose")
        assert resp.status_code == 200, resp.text
        summary = resp.json()["summary"]
        assert f"has {word}" in summary, (values, summary)
        assert agent_direction == expected, (values, agent_direction)


async def _seed_obs_only(session_maker, values):
    for i, v in enumerate(values):
        await seed_observation(
            session_maker, profile_id=PROFILE, doc_id="doc-ctd", analyte="glucose",
            value=v, verified=True, collected_at=T0 + timedelta(days=30 * i),
        )
