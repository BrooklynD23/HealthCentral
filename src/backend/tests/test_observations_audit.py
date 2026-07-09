from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.observations as observations_api
from api.observations import get_analyte_trend, router as observations_router
from core.auth import Session, get_profile_db_session, require_auth
from core.database import get_db


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _Scalars(self._rows)


class _FakeProfileDb:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, _stmt):
        return _Result(self._rows)


def _session(profile_id: str) -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="T",
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )


def _observation(*, analyte: str, value: float, unit: str, collected_at: datetime, profile_id: str = "profile-a"):
    return SimpleNamespace(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        doc_id="doc-a",
        analyte_canonical=analyte,
        analyte_raw=analyte,
        value=value,
        value_text=None,
        unit=unit,
        ref_low=None,
        ref_high=None,
        ref_range_text=None,
        flag=None,
        is_abnormal=False,
        collected_at=collected_at,
        user_verified=False,
        extraction_confidence=0.9,
        source_page=None,
        source_bbox_json=None,
    )


@pytest.mark.asyncio
async def test_HC_OBS_AUDIT_001_trend_view_fails_closed(monkeypatch):
    profile_id = str(uuid.uuid4())
    rows = [
        _observation(
            analyte="glucose",
            value=94.0,
            unit="mg/dL",
            collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
    ]
    profile_db = _FakeProfileDb(rows)
    master_db = AsyncMock()
    master_db.commit.side_effect = RuntimeError("audit commit failed")

    monkeypatch.setattr(
        observations_api,
        "log_observation_event",
        AsyncMock(return_value=object()),
    )

    with pytest.raises(RuntimeError, match="audit commit failed"):
        await get_analyte_trend(
            analyte="glucose",
            session=_session(profile_id),
            profile_db=profile_db,
            master_db=master_db,
        )

    master_db.commit.assert_awaited_once()


def test_HC_OBS_AUDIT_002_list_writes_view_row(monkeypatch):
    profile_id = str(uuid.uuid4())
    rows = [
        _observation(
            analyte="glucose",
            value=94.0,
            unit="mg/dL",
            collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
    ]
    profile_db = _FakeProfileDb(rows)
    master_db = AsyncMock()
    log_mock = AsyncMock(return_value=object())
    monkeypatch.setattr(observations_api, "log_observation_event", log_mock)

    app = FastAPI()
    app.include_router(observations_router, prefix="/observations")

    async def _override_auth():
        return _session(profile_id)

    async def _override_profile_db():
        return profile_db

    async def _override_master_db():
        return master_db

    app.dependency_overrides[require_auth] = _override_auth
    app.dependency_overrides[get_profile_db_session] = _override_profile_db
    app.dependency_overrides[get_db] = _override_master_db

    with TestClient(app) as client:
        response = client.get("/observations/")

    assert response.status_code == 200
    log_mock.assert_awaited_once()
    assert log_mock.await_args.kwargs["event"] == "view"
    master_db.commit.assert_awaited_once()
