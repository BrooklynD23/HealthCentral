"""AUDIT-ORDER AD-DENIALS B: HC-AUD-ORD-040/040b/041/042 + write failure."""

from __future__ import annotations

import logging
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import api.export as export_api
import api.profiles as profiles_api
from core import denial_audit
from core.database import Base, get_db
from models.audit import AuditLog
from tests.support.routes import route_client

CALLER, OTHER = "profile-a", "profile-b"


@pytest_asyncio.fixture
async def maker():
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False},
                                 poolclass=__import__("sqlalchemy.pool", fromlist=["StaticPool"]).StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch):
    denial_audit._state.clear()
    clock = {"t": 1000.0}
    monkeypatch.setattr(denial_audit, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(denial_audit.database, "async_session_maker", None, raising=False)
    return clock


async def _rows(maker) -> list[AuditLog]:
    async with maker() as s:
        return list((await s.execute(select(AuditLog).order_by(AuditLog.timestamp, AuditLog.id))).scalars())


def _client(router, prefix, maker):
    ctx = route_client(router, prefix, profile_id=CALLER, raise_server_exceptions=False)
    client = ctx.__enter__()

    async def _real_get_db():  # mirrors core/database.py get_db
        async with maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    client.app.dependency_overrides[get_db] = _real_get_db
    return ctx, client


EXPORT_CASES = [
    ("summary", export_api._summary_store, "/export/doctor-summary/{}/download", "summary"),
    ("packet", export_api._packet_store, "/export/visit-prep/{}/download", "packet"),
    ("export", export_api._fhir_store, "/export/fhir/{}/download", "export"),
]


@pytest.mark.parametrize("store_kind", EXPORT_CASES, ids=[c[0] for c in EXPORT_CASES])
@pytest.mark.asyncio
async def test_hc_aud_ord_040_and_042_export_denial_committed_without_target(
    store_kind, maker, monkeypatch
):
    _, store, url, entity_type = store_kind
    art_id = str(uuid.uuid4())
    monkeypatch.setitem(store, art_id, {"profile_id": OTHER})
    ctx, client = _client(export_api.router, "/export", maker)
    try:
        resp = client.get(url.format(art_id))
    finally:
        ctx.__exit__(None, None, None)
    assert resp.status_code == 403
    (row,) = await _rows(maker)
    assert row.event_type == "denial.cross_profile"
    assert row.profile_id == CALLER and row.entity_type == entity_type
    assert row.entity_id is None
    blob = " ".join(str(getattr(row, c.name)) for c in row.__table__.columns)
    assert OTHER not in blob and art_id not in blob


@pytest.mark.asyncio
async def test_hc_aud_ord_041_cap_and_suppressed_summary(maker, _fresh_state):
    async with maker() as s:
        for _ in range(21):
            await denial_audit.audit_denial(CALLER, "profile", s)
    rows = await _rows(maker)
    assert [r.event_type for r in rows] == ["denial.cross_profile"] * 20
    _fresh_state["t"] += denial_audit.DENIAL_WINDOW_SECONDS + 1
    async with maker() as s:
        await denial_audit.audit_denial(CALLER, "profile", s)
    rows = await _rows(maker)
    sup = [r for r in rows if r.event_type == "denial.suppressed"]
    assert len(sup) == 1 and '"count": 1' in sup[0].details_json
    assert len([r for r in rows if r.event_type == "denial.cross_profile"]) == 21


@pytest.mark.asyncio
async def test_hc_aud_ord_040_write_failure_keeps_403_and_logs_ids_only(maker, monkeypatch, caplog):
    art_id = str(uuid.uuid4())
    monkeypatch.setitem(export_api._summary_store, art_id, {"profile_id": OTHER})

    async def _boom(*a, **k):
        raise RuntimeError("disk full")

    monkeypatch.setattr(denial_audit, "create_audit_log", _boom)
    ctx, client = _client(export_api.router, "/export", maker)
    try:
        with caplog.at_level(logging.ERROR):
            resp = client.get(f"/export/doctor-summary/{art_id}/download")
    finally:
        ctx.__exit__(None, None, None)
    assert resp.status_code == 403
    errs = [r for r in caplog.records if "Denial audit write failed" in r.getMessage()]
    assert len(errs) == 1 and CALLER in errs[0].getMessage()
    assert OTHER not in caplog.text and art_id not in caplog.text


@pytest.mark.asyncio
async def test_hc_aud_ord_040b_profile_route_denial(maker, monkeypatch, caplog):
    monkeypatch.setattr(denial_audit.database, "async_session_maker", maker)
    ctx, client = _client(profiles_api.router, "/profiles", maker)
    try:
        with caplog.at_level(logging.WARNING):
            resp = client.get(f"/profiles/{OTHER}")
    finally:
        ctx.__exit__(None, None, None)
    assert resp.status_code == 403
    (row,) = await _rows(maker)
    assert row.event_type == "denial.cross_profile" and row.profile_id == CALLER
    assert row.entity_type == "profile" and row.entity_id is None
    assert OTHER not in caplog.text
