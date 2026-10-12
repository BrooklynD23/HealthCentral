"""AUDIT-ORDER AD-DENIALS B: HC-AUD-ORD-040/040b/041/042 + write failure."""

from __future__ import annotations

import logging
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core import denial_audit
from core.database import Base
from models.audit import AuditLog

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


