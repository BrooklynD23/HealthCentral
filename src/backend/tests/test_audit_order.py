"""AUDIT-ORDER D (A2): intent rows around irreversible deletes.

HC-AUD-ORD-004 (helper), 001a/001b/002/003 (4 delete routes), 020 (C branch).
Route tests go through HTTP with a real in-memory master and vault.
"""

from __future__ import annotations

import json
import logging
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from api.documents import router as documents_router
from api.medications import router as medications_router
from api.memory import router as memory_router
from api.pinboards import router as pinboards_router
from core.config import settings
from core.audit import audit_intent, log_memory_event
from core.auth import get_profile_db_session
from core.database import Base
from core.profile_database import ProfileDatabaseBase
from models import Document, Medication
from models.audit import AuditLog
from models.memory_item import MemoryItem
from models.pinboard import Pinboard
from tests.support.routes import route_client

PROFILE = "profile-a"


# --- harness ---------------------------------------------------------------


class FailingCommitSession(AsyncSession):
    """Master session whose Nth commit (1-based) raises a disk error."""

    fail_on: int | None = None
    commits = 0

    async def commit(self) -> None:
        self.commits += 1
        if self.fail_on == self.commits:
            await self.rollback()
            raise OperationalError("COMMIT", {}, Exception("disk I/O error"))
        await super().commit()


@pytest_asyncio.fixture
async def master():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = FailingCommitSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def vault():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _rows(master: AsyncSession) -> list[AuditLog]:
    master.expire_all()
    res = await master.execute(select(AuditLog).order_by(AuditLog.timestamp, AuditLog.id))
    return list(res.scalars())


def _status(row: AuditLog) -> str | None:
    return (json.loads(row.details_json) if row.details_json else {}).get("status")


# --- helper (T1) -------------------------------------------------------------


@pytest.mark.parametrize("bad", ["done", "", "started "])
@pytest.mark.asyncio
async def test_hc_aud_ord_004_bad_status_raises(master, bad):
    with pytest.raises(ValueError):
        await audit_intent(
            master, bad, log_memory_event, event="delete", profile_id=PROFILE, item_id="i"
        )
    assert not master.new and await _rows(master) == []


@pytest.mark.parametrize("status", ["started", "completed"])
@pytest.mark.asyncio
async def test_hc_aud_ord_004_good_status_only_allowlisted(master, status):
    await audit_intent(
        master, status, log_memory_event, event="delete", profile_id=PROFILE,
        item_id=str(uuid.uuid4()), details={"status": "evil", "junk_key": "Jane Doe"},
    )
    (row,) = await _rows(master)
    d = json.loads(row.details_json)
    assert d["status"] == status and "junk_key" not in d and "Jane" not in row.details_json
