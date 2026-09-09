"""HC-MEM-AUDIT-001..005 — the memory routes must write audit rows.

CLAUDE.md hard invariant: "Audit logging on every route that touches
documents, observations, or profile data." `api/memory.py` writes MemoryItem
rows through `ProfileDbSession` — profile data by definition — and was the
only router under `api/` that imported nothing from `core.audit`
(14 of the other 15 do).

These go through HTTP via `tests/support/routes.py::route_client`, per
recurring-failures.md #1: a test that calls the handler directly cannot see a
broken `Depends(...)`.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from api.memory import router as memory_router
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models.memory_item import MemoryItem
from tests.support.routes import route_client

PROFILE = "profile-a"


class _RecordingMasterDb:
    """Captures rows handed to the master DB so a test can assert an
    AuditLog was written, without needing a real master database."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:  # pragma: no cover - not exercised
        pass

    def audit_rows(self) -> list[object]:
        return [o for o in self.added if type(o).__name__ == "AuditLog"]


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _seed_item(db: AsyncSession, *, key: str = "diet", value: str = "vegetarian") -> str:
    item = MemoryItem(
        id=str(uuid.uuid4()), profile_id=PROFILE, key=key, value=value, category=None
    )
    db.add(item)
    await db.commit()
    return item.id


def _client(master_db, profile_db):
    ctx = route_client(memory_router, "/memory", profile_id=PROFILE, master_db=master_db)
    client = ctx.__enter__()

    async def _override_profile_db():
        return profile_db

    client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
    return ctx, client


@pytest.mark.asyncio
async def test_hc_mem_audit_001_create_writes_audit_row(profile_db):
    master = _RecordingMasterDb()
    ctx, client = _client(master, profile_db)
    try:
        resp = client.post("/memory/", json={"key": "diet", "value": "vegetarian"})
        assert resp.status_code == 201, resp.text
        assert master.audit_rows(), "POST /memory/ wrote no AuditLog row"
    finally:
        ctx.__exit__(None, None, None)


@pytest.mark.asyncio
async def test_hc_mem_audit_002_list_writes_audit_row(profile_db):
    await _seed_item(profile_db)
    master = _RecordingMasterDb()
    ctx, client = _client(master, profile_db)
    try:
        resp = client.get("/memory/")
        assert resp.status_code == 200, resp.text
        assert master.audit_rows(), "GET /memory/ wrote no AuditLog row"
    finally:
        ctx.__exit__(None, None, None)


@pytest.mark.asyncio
async def test_hc_mem_audit_003_get_one_writes_audit_row(profile_db):
    item_id = await _seed_item(profile_db)
    master = _RecordingMasterDb()
    ctx, client = _client(master, profile_db)
    try:
        resp = client.get(f"/memory/{item_id}")
        assert resp.status_code == 200, resp.text
        assert master.audit_rows(), "GET /memory/{id} wrote no AuditLog row"
    finally:
        ctx.__exit__(None, None, None)


@pytest.mark.asyncio
async def test_hc_mem_audit_004_update_writes_audit_row(profile_db):
    item_id = await _seed_item(profile_db)
    master = _RecordingMasterDb()
    ctx, client = _client(master, profile_db)
    try:
        resp = client.put(f"/memory/{item_id}", json={"value": "pescatarian"})
        assert resp.status_code == 200, resp.text
        assert master.audit_rows(), "PUT /memory/{id} wrote no AuditLog row"
    finally:
        ctx.__exit__(None, None, None)


@pytest.mark.asyncio
async def test_hc_mem_audit_005_delete_writes_audit_row(profile_db):
    item_id = await _seed_item(profile_db)
    master = _RecordingMasterDb()
    ctx, client = _client(master, profile_db)
    try:
        resp = client.delete(f"/memory/{item_id}")
        assert resp.status_code == 204, resp.text
        assert master.audit_rows(), "DELETE /memory/{id} wrote no AuditLog row"
    finally:
        ctx.__exit__(None, None, None)


@pytest.mark.asyncio
async def test_hc_mem_audit_006_audit_row_carries_no_memory_value(profile_db):
    """The audit trail lives in the UNENCRYPTED master DB (core/audit.py
    AUDIT-PHI-001). A memory item's `value` is user-authored PHI and must
    never appear in an audit row's details."""
    master = _RecordingMasterDb()
    ctx, client = _client(master, profile_db)
    try:
        secret = "my nephrologist is Dr. Chen at 555-0142"
        resp = client.post("/memory/", json={"key": "care team", "value": secret})
        assert resp.status_code == 201, resp.text
        rows = master.audit_rows()
        assert rows, "POST /memory/ wrote no AuditLog row"
        blob = " ".join(str(getattr(r, "details_json", "") or "") for r in rows)
        assert "Dr. Chen" not in blob and "555-0142" not in blob, (
            f"memory value leaked into the unencrypted audit trail: {blob}"
        )
    finally:
        ctx.__exit__(None, None, None)
