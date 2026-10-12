"""AUDIT-ORDER D (A2): intent rows around irreversible deletes.

HC-AUD-ORD-004 (helper), 001a/001b/002/003 (4 delete routes), 020 (C branch).
Route tests go through HTTP with a real in-memory master and vault.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

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


# --- per-route cases ---------------------------------------------------------


class Case:
    def __init__(self, name, router, prefix, model):
        self.name, self.router, self.prefix, self.model = name, router, prefix, model

    async def seed(self, vault: AsyncSession, tmp_path) -> str:
        id_ = str(uuid.uuid4())
        if self.name == "document":
            vault.add(Document(
                id=id_, profile_id=PROFILE, path_hash="p" * 64, content_hash="c" * 64,
                doc_type="lab_report", source="secret_Jane.pdf", status="completed",
                imported_at=datetime.now(timezone.utc).replace(tzinfo=None),
            ))
            d = tmp_path / "vaults" / PROFILE / "docs"
            d.mkdir(parents=True)
            (d / f"{id_}.bin").write_bytes(b"x")
        elif self.name == "medication":
            vault.add(Medication(
                id=id_, profile_id=PROFILE, name="Metformin",
                frequency="once_daily", is_active=True, reminder_enabled=False,
            ))
        elif self.name == "memory":
            vault.add(MemoryItem(id=id_, profile_id=PROFILE, key="k", value="v"))
        else:
            vault.add(Pinboard(id=id_, name="board"))
        await vault.commit()
        return id_

    def url(self, id_: str) -> str:
        suffix = "?hard_delete=true" if self.name == "medication" else ""
        return f"{self.prefix}/{id_}{suffix}"

    async def present(self, vault: AsyncSession, id_: str, tmp_path) -> bool:
        vault.expire_all()
        found = (await vault.execute(select(self.model).where(self.model.id == id_))).first()
        if self.name == "document":
            on_disk = (tmp_path / "vaults" / PROFILE / "docs" / f"{id_}.bin").exists()
            assert on_disk == bool(found), "document row and .bin disagree"
        return bool(found)


CASES = [
    Case("document", documents_router, "/documents", Document),
    Case("medication", medications_router, "/medications", Medication),
    Case("memory", memory_router, "/memory", MemoryItem),
    Case("pinboard", pinboards_router, "/pinboards", Pinboard),
]
IDS = [c.name for c in CASES]


def _client(case: Case, master, vault):
    ctx = route_client(
        case.router, case.prefix, profile_id=PROFILE, master_db=master,
        raise_server_exceptions=False,
    )
    client = ctx.__enter__()

    async def _vault():
        return vault

    client.app.dependency_overrides[get_profile_db_session] = _vault
    return ctx, client


@pytest.fixture(autouse=True)
def _app_data(tmp_path, monkeypatch):
    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))


@pytest.mark.parametrize("case", CASES, ids=IDS)
@pytest.mark.asyncio
async def test_hc_aud_ord_001a_intent_commit_fails(case, master, vault, tmp_path):
    id_ = await case.seed(vault, tmp_path)
    master.fail_on = 1
    ctx, client = _client(case, master, vault)
    try:
        resp = client.delete(case.url(id_))
    finally:
        ctx.__exit__(None, None, None)
    assert resp.status_code == 500
    assert await case.present(vault, id_, tmp_path), "vault changed although intent failed"
    assert await _rows(master) == []


@pytest.mark.parametrize("case", CASES, ids=IDS)
@pytest.mark.asyncio
async def test_hc_aud_ord_001b_completion_commit_fails(case, master, vault, tmp_path):
    id_ = await case.seed(vault, tmp_path)
    master.fail_on = 2
    ctx, client = _client(case, master, vault)
    try:
        resp = client.delete(case.url(id_))
    finally:
        ctx.__exit__(None, None, None)
    assert resp.status_code == 500
    assert not await case.present(vault, id_, tmp_path), "vault change must be durable"
    rows = await _rows(master)
    assert [_status(r) for r in rows] == ["started"]


@pytest.mark.parametrize("case", CASES, ids=IDS)
@pytest.mark.asyncio
async def test_hc_aud_ord_002_vault_commit_fails(case, master, vault, tmp_path, monkeypatch):
    id_ = await case.seed(vault, tmp_path)

    async def _boom():
        await vault.rollback()
        raise OperationalError("COMMIT", {}, Exception("disk I/O error"))

    monkeypatch.setattr(vault, "commit", _boom)
    ctx, client = _client(case, master, vault)
    try:
        resp = client.delete(case.url(id_))
    finally:
        ctx.__exit__(None, None, None)
    assert resp.status_code == 500
    monkeypatch.undo()
    assert await case.present(vault, id_, tmp_path)
    assert [_status(r) for r in await _rows(master)] == ["started"]


@pytest.mark.parametrize("case", CASES, ids=IDS)
@pytest.mark.asyncio
async def test_hc_aud_ord_003_happy_path(case, master, vault, tmp_path):
    id_ = await case.seed(vault, tmp_path)
    ctx, client = _client(case, master, vault)
    try:
        resp = client.delete(case.url(id_))
    finally:
        ctx.__exit__(None, None, None)
    assert resp.status_code == 204, resp.text
    assert not await case.present(vault, id_, tmp_path)
    rows = await _rows(master)
    assert [_status(r) for r in rows] == ["started", "completed"]
    assert rows[0].entity_id == rows[1].entity_id == id_
    assert rows[0].timestamp <= rows[1].timestamp


@pytest.mark.asyncio
async def test_hc_aud_ord_020_soft_delete_commit_fail_logs_ids_only(
    master, vault, tmp_path, caplog
):
    case = CASES[1]
    id_ = await case.seed(vault, tmp_path)
    master.fail_on = 1
    ctx, client = _client(case, master, vault)
    try:
        with caplog.at_level(logging.ERROR):
            resp = client.delete(f"/medications/{id_}")
    finally:
        ctx.__exit__(None, None, None)
    assert resp.status_code == 500
    errs = [r for r in caplog.records if "AUDIT-ORDER" in r.getMessage()]
    assert len(errs) == 1 and errs[0].levelno == logging.ERROR
    assert id_ in errs[0].getMessage()
    assert "Metformin" not in caplog.text


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
