"""HTTP-level tests for notification routes (STREAK-TZ)."""

import logging
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

import api.notifications as notif_api
import modules.adherence_patterns as ap_module
from api.notifications import router as notif_router
from core.auth import get_profile_db_session
from models import Medication, ReminderLog
from tests.support.routes import route_client
from tests.test_medications_routes_http import PROFILE, _seed_la_doses, profile_db  # noqa: F401


@pytest.mark.asyncio
async def test_hc_streak_tz_003_test_notification_streak_uses_profile_zone(profile_db, monkeypatch):  # noqa: F811  # pytest fixture parameter
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
        seen["hour"] = context.hour_of_day
        seen["weekend"] = context.is_weekend
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
    # Local 17:00 Thursday; UTC would give hour 1.
    assert seen["hour"] == 17
    assert seen["weekend"] is False


def _audmed_setup(monkeypatch, order):
    message = SimpleNamespace(title="t", body="b", action_text=None)
    monkeypatch.setattr(
        notif_api, "get_message_generator",
        lambda: SimpleNamespace(generate_reminder=lambda ctx: message),
    )

    async def _send(payload):
        order.append("send")
        return SimpleNamespace(success=True, platform=None, error_message=None)

    service = SimpleNamespace(initialize=AsyncMock(), send=AsyncMock(side_effect=_send))
    monkeypatch.setattr(notif_api, "get_notification_service", lambda: service)
    return service


@pytest.mark.asyncio
async def test_hc_audmed_003_test_notification_audited_before_send(profile_db, monkeypatch):  # noqa: F811
    med_id = await _seed_la_doses(profile_db, [datetime(2026, 1, 15, 17, 0)])
    order = []
    calls = []

    async def _spy(**kwargs):
        order.append("audit")
        calls.append(kwargs)

    monkeypatch.setattr(notif_api, "log_document_event", _spy, raising=False)
    service = _audmed_setup(monkeypatch, order)

    async def _override_profile_db():
        return profile_db

    master_db = AsyncMock()
    with route_client(notif_router, "/notifications", profile_id=PROFILE, master_db=master_db) as client:
        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        resp = client.post(f"/notifications/test/{med_id}")
    assert resp.status_code == 200, resp.text
    assert len(calls) == 1
    assert calls[0]["event"] == "view"
    assert calls[0]["profile_id"] == PROFILE
    assert calls[0]["document_id"] == med_id
    assert calls[0]["details"]["entity_type"] == "medication_test_notification"
    assert calls[0]["db"] is master_db
    master_db.commit.assert_awaited()
    service.send.assert_awaited_once()
    assert order == ["audit", "send"]


@pytest.mark.asyncio
async def test_hc_audmed_004_test_notification_audit_failure_blocks_send(profile_db, monkeypatch):  # noqa: F811
    med_id = await _seed_la_doses(profile_db, [datetime(2026, 1, 15, 17, 0)])
    order = []

    async def _boom(**kwargs):
        raise RuntimeError("audit down")

    monkeypatch.setattr(notif_api, "log_document_event", _boom, raising=False)
    service = _audmed_setup(monkeypatch, order)

    async def _override_profile_db():
        return profile_db

    with route_client(
        notif_router, "/notifications", profile_id=PROFILE, raise_server_exceptions=False
    ) as client:
        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        resp = client.post(f"/notifications/test/{med_id}")
    assert resp.status_code != 200
    service.send.assert_not_awaited()
    service.initialize.assert_not_awaited()
    assert order == []


@pytest.mark.asyncio
async def test_hc_msg_004_test_notification_streak_holds_through_missed_morning(profile_db, monkeypatch):  # noqa: F811
    # Doses Jan 13-15 at 09:00 PST; now = Jan 16 10:00 PST, no dose yet today.
    med_id = await _seed_la_doses(
        profile_db, [datetime(2026, 1, d, 17, 0) for d in (13, 14, 15)]
    )
    frozen = datetime(2026, 1, 16, 18, 0)
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


# --- AUDIT-NOTIF-ALL: audit rows on settings, history, interaction ---------


async def _audntf_seed(db, with_reminder=False):
    med_id = str(uuid.uuid4())
    db.add(Medication(
        id=med_id, profile_id=PROFILE, name="Metformin",
        frequency="once_daily", is_active=True, reminder_enabled=True,
    ))
    reminder_id = None
    if with_reminder:
        reminder_id = str(uuid.uuid4())
        db.add(ReminderLog(
            id=reminder_id, profile_id=PROFILE, medication_id=med_id,
            reminder_type="initial", message_tone="friendly", message="Time for Metformin",
            sent_at=datetime(2026, 3, 1, 19, 45), delivery_method="in_app",
        ))
    await db.commit()
    return med_id, reminder_id


def _audntf_spy(monkeypatch, order, calls, fail=False):
    async def _spy(**kwargs):
        if fail:
            raise RuntimeError("audit down")
        order.append("audit")
        calls.append(kwargs)

    monkeypatch.setattr(notif_api, "log_document_event", _spy)


def _audntf_track_vault(db, monkeypatch, order):
    real_commit = db.commit

    async def _commit():
        order.append("vault")
        await real_commit()

    monkeypatch.setattr(db, "commit", _commit)


def _audntf_override(client, db):
    async def _override_profile_db():
        return db

    client.app.dependency_overrides[get_profile_db_session] = _override_profile_db


_SETTINGS_BODY = {"enabled": False, "quiet_hours_start": "22:00"}


@pytest.mark.asyncio
async def test_hc_audntf_001_settings_update_audited_after_vault(profile_db, monkeypatch):  # noqa: F811
    med_id, _ = await _audntf_seed(profile_db)
    order, calls = [], []
    _audntf_track_vault(profile_db, monkeypatch, order)
    _audntf_spy(monkeypatch, order, calls)
    master = AsyncMock()
    with route_client(notif_router, "/notifications", profile_id=PROFILE, master_db=master) as client:
        _audntf_override(client, profile_db)
        resp = client.patch(f"/notifications/settings/{med_id}", json=_SETTINGS_BODY)
    assert resp.status_code == 200, resp.text
    assert len(calls) == 1
    assert calls[0]["event"] == "notification_settings_update"
    assert calls[0]["profile_id"] == PROFILE
    assert calls[0]["document_id"] == med_id
    assert calls[0]["details"] == {"changed_fields": ["enabled", "quiet_hours_start"]}
    assert calls[0]["db"] is master
    assert order == ["vault", "audit"]
    master.commit.assert_awaited()


@pytest.mark.asyncio
async def test_hc_audntf_002_settings_update_audit_commit_failure_logged(profile_db, monkeypatch, caplog):  # noqa: F811
    med_id, _ = await _audntf_seed(profile_db)
    _audntf_spy(monkeypatch, [], [])
    master = AsyncMock()
    master.commit.side_effect = RuntimeError("master down")
    with caplog.at_level(logging.DEBUG):
        with route_client(
            notif_router, "/notifications", profile_id=PROFILE, master_db=master,
            raise_server_exceptions=False,
        ) as client:
            _audntf_override(client, profile_db)
            resp = client.patch(f"/notifications/settings/{med_id}", json=_SETTINGS_BODY)
    assert resp.status_code == 500
    await profile_db.rollback()
    med = (await profile_db.execute(select(Medication).where(Medication.id == med_id))).scalar_one()
    assert med.reminder_enabled is False
    errors = [r for r in caplog.records if r.levelno == logging.ERROR and "AUDIT-ORDER" in r.getMessage()]
    assert len(errors) == 1
    assert med_id in errors[0].getMessage()
    assert "Metformin" not in caplog.text


@pytest.mark.asyncio
async def test_hc_audntf_003_reminder_interaction_audited_after_vault(profile_db, monkeypatch):  # noqa: F811
    _, reminder_id = await _audntf_seed(profile_db, with_reminder=True)
    order, calls = [], []
    _audntf_track_vault(profile_db, monkeypatch, order)
    _audntf_spy(monkeypatch, order, calls)
    master = AsyncMock()
    with route_client(notif_router, "/notifications", profile_id=PROFILE, master_db=master) as client:
        _audntf_override(client, profile_db)
        resp = client.post(
            f"/notifications/{reminder_id}/interaction",
            params={"interaction_type": "snoozed", "snooze_minutes": 10},
        )
    assert resp.status_code == 204, resp.text
    assert len(calls) == 1
    assert calls[0]["event"] == "reminder_interaction"
    assert calls[0]["profile_id"] == PROFILE
    assert calls[0]["document_id"] == reminder_id
    assert calls[0]["details"] == {"entity_type": "reminder_interaction"}
    assert calls[0]["db"] is master
    assert order == ["vault", "audit"]
    master.commit.assert_awaited()


@pytest.mark.asyncio
async def test_hc_audntf_004_reminder_interaction_audit_commit_failure_logged(profile_db, monkeypatch, caplog):  # noqa: F811
    _, reminder_id = await _audntf_seed(profile_db, with_reminder=True)
    _audntf_spy(monkeypatch, [], [])
    master = AsyncMock()
    master.commit.side_effect = RuntimeError("master down")
    with caplog.at_level(logging.DEBUG):
        with route_client(
            notif_router, "/notifications", profile_id=PROFILE, master_db=master,
            raise_server_exceptions=False,
        ) as client:
            _audntf_override(client, profile_db)
            resp = client.post(
                f"/notifications/{reminder_id}/interaction",
                params={"interaction_type": "snoozed", "snooze_minutes": 10},
            )
    assert resp.status_code == 500
    await profile_db.rollback()
    row = (await profile_db.execute(select(ReminderLog).where(ReminderLog.id == reminder_id))).scalar_one()
    assert row.was_interacted is True
    errors = [r for r in caplog.records if r.levelno == logging.ERROR and "AUDIT-ORDER" in r.getMessage()]
    assert len(errors) == 1
    assert reminder_id in errors[0].getMessage()
    assert "snoozed" not in errors[0].getMessage()


@pytest.mark.asyncio
async def test_hc_audntf_005_settings_read_audited(profile_db, monkeypatch):  # noqa: F811
    med_id, _ = await _audntf_seed(profile_db)
    order, calls = [], []
    _audntf_spy(monkeypatch, order, calls)
    master = AsyncMock()
    with route_client(notif_router, "/notifications", profile_id=PROFILE, master_db=master) as client:
        _audntf_override(client, profile_db)
        resp = client.get(f"/notifications/settings/{med_id}")
    assert resp.status_code == 200, resp.text
    assert len(calls) == 1
    assert calls[0]["event"] == "view"
    assert calls[0]["profile_id"] == PROFILE
    assert calls[0]["document_id"] == med_id
    assert calls[0]["details"] == {"entity_type": "notification_settings"}
    assert calls[0]["db"] is master
    master.commit.assert_awaited()


@pytest.mark.asyncio
async def test_hc_audntf_006_settings_read_fails_closed(profile_db, monkeypatch):  # noqa: F811
    med_id, _ = await _audntf_seed(profile_db)
    _audntf_spy(monkeypatch, [], [], fail=True)
    master = AsyncMock()
    with route_client(
        notif_router, "/notifications", profile_id=PROFILE, master_db=master,
        raise_server_exceptions=False,
    ) as client:
        _audntf_override(client, profile_db)
        resp = client.get(f"/notifications/settings/{med_id}")
    assert resp.status_code == 500
    assert "quiet_hours_start" not in resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("filtered", [False, True])
async def test_hc_audntf_007_history_read_audited(profile_db, monkeypatch, filtered):  # noqa: F811
    med_id, _ = await _audntf_seed(profile_db, with_reminder=True)
    order, calls = [], []
    _audntf_spy(monkeypatch, order, calls)
    master = AsyncMock()
    params = {"medication_id": med_id} if filtered else {}
    with route_client(notif_router, "/notifications", profile_id=PROFILE, master_db=master) as client:
        _audntf_override(client, profile_db)
        resp = client.get("/notifications/history", params=params)
    assert resp.status_code == 200, resp.text
    assert len(calls) == 1
    assert calls[0]["event"] == "view"
    assert calls[0]["profile_id"] == PROFILE
    assert calls[0]["document_id"] == (med_id if filtered else "all")
    assert calls[0]["details"] == {"entity_type": "notification_history", "count": 1}
    assert calls[0]["db"] is master
    master.commit.assert_awaited()


@pytest.mark.asyncio
async def test_hc_audntf_008_history_read_fails_closed(profile_db, monkeypatch):  # noqa: F811
    await _audntf_seed(profile_db, with_reminder=True)
    _audntf_spy(monkeypatch, [], [], fail=True)
    master = AsyncMock()
    with route_client(
        notif_router, "/notifications", profile_id=PROFILE, master_db=master,
        raise_server_exceptions=False,
    ) as client:
        _audntf_override(client, profile_db)
        resp = client.get("/notifications/history")
    assert resp.status_code == 500
    assert "Time for Metformin" not in resp.text
