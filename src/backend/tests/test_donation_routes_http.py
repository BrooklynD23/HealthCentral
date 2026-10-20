"""RSI1-DONATE PR-1: /donation/consents routes (HC-DON-004..009).

Every test goes through route_client so FastAPI's dependency graph runs
(recurring-failures #1). route_client has no profile_db kwarg (I-9 waits on
C-P7), so get_profile_db_session is overridden the way
test_gamification_settings.py does.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

import api.donation as donation_api
from core.auth import get_profile_db_session, require_auth
from core.profile_database import ProfileDatabaseBase
from models.data_donation import DonatedRecord, DonationConsent
from tests.support.routes import route_client

PREFIX = "/donation"
PATH = f"{PREFIX}/consents"
PROFILE_A = "profile-a"
PROFILE_B = "profile-b"
PURPOSES = ["fine_tune", "synthetic_seed", "agent_traces"]
VERSION = "2026-10-20-draft-1"


def _master_db(commit_error: Exception | None = None) -> MagicMock:
    db = MagicMock()
    db.commit = AsyncMock(side_effect=commit_error)
    return db


async def _new_vault():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    return engine, AsyncSession(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def vault():
    engine, session = await _new_vault()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _call(method, profile_db, path=PATH, profile_id=PROFILE_A, master_db=None, json=None):
    master_db = master_db if master_db is not None else _master_db()
    with route_client(
        donation_api.router, PREFIX,
        profile_id=profile_id, master_db=master_db,
        raise_server_exceptions=False,
    ) as client:
        async def _profile_db():
            return profile_db
        client.app.dependency_overrides[get_profile_db_session] = _profile_db
        resp = client.request(method, path, json=json)
    return resp, master_db


def _put(profile_db, purpose, granted, **kw):
    return _call(
        "PUT", profile_db, f"{PATH}/{purpose}",
        json={"granted": granted, "consent_text_version": VERSION}, **kw,
    )


def _audit_rows(master_db):
    return [c.args[0] for c in master_db.add.call_args_list]


def _state(resp):
    return {c["purpose"]: c for c in resp.json()["consents"]}


async def _seed(session, profile_id, purpose, n_real=2, n_syn_per_real=1):
    real_ids = []
    for i in range(n_real):
        rec = DonatedRecord(
            profile_id=profile_id, purpose=purpose, origin="real",
            source_kind="chat_turn", source_id=f"src-{i}",
            prompt_redacted="p", response_redacted="r", strict_redaction_count=0,
        )
        session.add(rec)
        await session.flush()
        real_ids.append(rec.id)
    for rid in real_ids:
        for _ in range(n_syn_per_real):
            session.add(DonatedRecord(
                profile_id=profile_id, purpose=purpose, origin="synthetic",
                source_kind="chat_turn", parent_id=rid,
                prompt_redacted="p", response_redacted="r",
            ))
    await session.commit()


async def _count(session, purpose=None):
    q = select(func.count()).select_from(DonatedRecord)
    if purpose:
        q = q.where(DonatedRecord.purpose == purpose)
    return (await session.execute(q)).scalar_one()


@pytest.mark.parametrize("method,path,body", [
    ("GET", PATH, None),
    ("PUT", f"{PATH}/fine_tune", {"granted": True, "consent_text_version": VERSION}),
])
def test_hc_don_001_http_requires_auth(method, path, body):
    with route_client(donation_api.router, PREFIX, master_db=_master_db()) as client:
        client.app.dependency_overrides.pop(require_auth)
        resp = client.request(method, path, json=body)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_hc_don_004_fresh_profile_every_purpose_not_granted(vault):
    resp, master = _call("GET", vault)
    assert resp.status_code == 200, resp.text
    state = _state(resp)
    assert sorted(state) == sorted(PURPOSES)
    assert all(c["granted"] is False for c in state.values())
    rows = _audit_rows(master)
    assert [r.event_type for r in rows] == ["donation.consent.view"]


@pytest.mark.asyncio
async def test_hc_don_005_grant_then_get_with_one_audit_row(vault):
    resp, master = _put(vault, "fine_tune", True)
    assert resp.status_code == 200, resp.text
    assert resp.json()["granted"] is True
    rows = _audit_rows(master)
    assert len(rows) == 1
    assert rows[0].event_type == "donation.consent.grant"
    assert rows[0].entity_type == "donation"
    assert rows[0].entity_id == "fine_tune"
    assert rows[0].profile_id == PROFILE_A
    assert VERSION not in (rows[0].details_json or "")

    resp, _ = _call("GET", vault)
    state = _state(resp)
    assert state["fine_tune"]["granted"] is True
    assert state["fine_tune"]["consent_text_version"] == VERSION
    assert state["synthetic_seed"]["granted"] is False
    assert state["agent_traces"]["granted"] is False

    # Re-grant stays one active row per purpose.
    resp, _ = _put(vault, "fine_tune", True)
    assert resp.status_code == 200
    n = (await vault.execute(select(func.count()).select_from(DonationConsent))).scalar_one()
    assert n == 1


@pytest.mark.asyncio
async def test_hc_don_006_revoke_deletes_real_and_synthetic_children(vault):
    await _seed(vault, PROFILE_A, "fine_tune", n_real=2, n_syn_per_real=2)  # 2 + 4
    await _seed(vault, PROFILE_A, "agent_traces", n_real=1, n_syn_per_real=1)
    await _put_ok(vault, "fine_tune", True)
    await _put_ok(vault, "agent_traces", True)

    resp, master = _put(vault, "fine_tune", False)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["granted"] is False
    assert body["deleted_count"] == 6
    assert await _count(vault, "fine_tune") == 0
    assert await _count(vault, "agent_traces") == 2  # untouched

    consent = (await vault.execute(
        select(DonationConsent).where(DonationConsent.purpose == "fine_tune")
    )).scalar_one()
    assert consent.revoked_at is not None  # row kept, never deleted

    rows = _audit_rows(master)
    assert len(rows) == 1
    assert rows[0].event_type == "donation.consent.revoke"
    assert rows[0].entity_id == "fine_tune"
    assert '"count": 6' in rows[0].details_json

    resp, _ = _call("GET", vault)
    assert _state(resp)["fine_tune"]["granted"] is False
    assert _state(resp)["agent_traces"]["granted"] is True


async def _put_ok(vault, purpose, granted):
    resp, _ = _put(vault, purpose, granted)
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_hc_don_006b_revoke_leaves_canary_and_other_profile_rows_alone(vault):
    vault.add(DonatedRecord(
        profile_id=PROFILE_A, purpose="fine_tune", origin="canary",
        source_kind="canary", prompt_redacted="x", response_redacted="y",
    ))
    vault.add(DonatedRecord(
        profile_id=PROFILE_B, purpose="fine_tune", origin="real",
        source_kind="chat_turn", prompt_redacted="x", response_redacted="y",
    ))
    await vault.commit()
    resp, _ = _put(vault, "fine_tune", False)
    assert resp.status_code == 200, resp.text
    assert resp.json()["deleted_count"] == 0
    assert await _count(vault, "fine_tune") == 2


@pytest.mark.asyncio
async def test_hc_don_007_profiles_are_isolated_by_vault():
    """Routes are session-scoped (no {profile_id}), so isolation is the vault.

    Plan text said 403 + denial.cross_profile; there is no path parameter for
    require_profile_access to check. Deviation flagged in the PR body.
    """
    eng_a, vault_a = await _new_vault()
    eng_b, vault_b = await _new_vault()
    try:
        await _seed(vault_b, PROFILE_B, "fine_tune")
        resp, _ = _put(vault_b, "fine_tune", True, profile_id=PROFILE_B)
        assert resp.status_code == 200, resp.text

        resp, _ = _call("GET", vault_a, profile_id=PROFILE_A)
        assert all(c["granted"] is False for c in _state(resp).values())

        resp, _ = _put(vault_a, "agent_traces", True, profile_id=PROFILE_A)
        assert resp.status_code == 200, resp.text
        resp, _ = _put(vault_a, "fine_tune", False, profile_id=PROFILE_A)
        assert resp.json()["deleted_count"] == 0

        resp, _ = _call("GET", vault_b, profile_id=PROFILE_B)
        state_b = _state(resp)
        assert state_b["fine_tune"]["granted"] is True
        assert state_b["agent_traces"]["granted"] is False
        assert await _count(vault_b, "fine_tune") == 4  # 2 real + 2 synthetic children
    finally:
        await vault_a.close()
        await vault_b.close()
        await eng_a.dispose()
        await eng_b.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_purpose", ["marketing", "FINE_TUNE", "fine_tune%20x"])
async def test_hc_don_008_unknown_purpose_is_422(vault, bad_purpose):
    resp, master = _put(vault, bad_purpose, True)
    assert resp.status_code == 422
    assert _audit_rows(master) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [
    {"granted": True},
    {"granted": True, "consent_text_version": ""},
    {"granted": True, "consent_text_version": "x" * 65},
    {"granted": True, "consent_text_version": "has spaces and prose"},
    {"granted": "yes please", "consent_text_version": VERSION},
])
async def test_hc_don_008b_bad_body_is_422(vault, body):
    resp, _ = _call("PUT", vault, f"{PATH}/fine_tune", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,body", [
    ("GET", PATH, None),
    ("PUT", f"{PATH}/fine_tune", {"granted": True, "consent_text_version": VERSION}),
])
async def test_hc_don_010_fails_closed_when_audit_commit_fails(vault, method, path, body):
    resp, _ = _call(method, vault, path, master_db=_master_db(RuntimeError("audit down")), json=body)
    assert resp.status_code == 500
