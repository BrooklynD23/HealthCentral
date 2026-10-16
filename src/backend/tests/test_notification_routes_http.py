"""HTTP-level tests for notification routes (STREAK-TZ)."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import api.notifications as notif_api
import modules.adherence_patterns as ap_module
from api.notifications import router as notif_router
from core.auth import get_profile_db_session
from tests.support.routes import route_client
from tests.test_medications_routes_http import PROFILE, _seed_la_doses, profile_db  # noqa: F401


@pytest.mark.asyncio
async def test_hc_streak_tz_003_test_notification_streak_uses_profile_zone(profile_db, monkeypatch):
    # Same seed as tz_001: three PST days, now = Jan 15 17:00 PST (Jan 16 01:00Z).
    med_id = await _seed_la_doses(
        profile_db, [datetime(2026, 1, d, 17, 0) for d in (13, 14, 15)]
    )
    frozen = datetime(2026, 1, 16, 1, 0)
    monkeypatch.setattr(notif_api, "utcnow", lambda: frozen)
    monkeypatch.setattr(ap_module, "utcnow", lambda: frozen)

    seen = {}
    message = SimpleNamespace(title="t", body="b", action_text=None)

    def _generate(context):
        seen["streak"] = context.current_streak
        return message

    monkeypatch.setattr(
        notif_api, "get_message_generator", lambda: SimpleNamespace(generate_reminder=_generate)
    )
    service = SimpleNamespace(
        initialize=AsyncMock(),
        send=AsyncMock(return_value=SimpleNamespace(success=True, platform=None, error_message=None)),
    )
    monkeypatch.setattr(notif_api, "get_notification_service", lambda: service)

    async def _override_profile_db():
        return profile_db

    with route_client(notif_router, "/notifications", profile_id=PROFILE) as client:
        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        resp = client.post(f"/notifications/test/{med_id}")
    assert resp.status_code == 200, resp.text
    assert seen["streak"] == 3
