"""AUDIT-ORDER D (A2): intent rows around irreversible deletes.

HC-AUD-ORD-004 (helper), 001a/001b/002/003 (4 delete routes), 020 (C branch).
Route tests go through HTTP with a real in-memory master and vault.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch
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
from models import Document, DocumentEntity, LabInterpretation, Medication, Observation
from models.pinboard import PinboardItem
import api.assistant as assistant_api
import api.backup as backup_api
import api.documents as documents_api
import api.profiles as profiles_api
import api.interpretations as interp_api
from api.interpretations import router as interp_router
from modules.rag import ModelUnavailableError
from models import Profile
from models.chat_session import ChatTurn
from api.assistant import ResponseSegment, VerificationInfo
from api.assistant import router as assistant_router
from core.audit import create_audit_log
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from scripts.backup import RestoreResult
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


# --- T3: reprocess, interpretation regenerate, pin prune ---------------------


def _fail_vault_commit(vault, monkeypatch):
    async def _boom():
        await vault.rollback()
        raise OperationalError("COMMIT", {}, Exception("disk I/O error"))

    monkeypatch.setattr(vault, "commit", _boom)


def _call(router, prefix, master, vault, method, url, **kw):
    with route_client(
        router, prefix, profile_id=PROFILE, master_db=master,
        raise_server_exceptions=False,
    ) as client:
        async def _v():
            return vault

        client.app.dependency_overrides[get_profile_db_session] = _v
        return client.request(method, url, **kw)


def _details(row: AuditLog) -> dict:
    return json.loads(row.details_json) if row.details_json else {}


# row 2: reprocess ------------------------------------------------------------


def _entity(doc_id: str) -> DocumentEntity:
    return DocumentEntity(
        id=str(uuid.uuid4()), doc_id=doc_id, category="visit_note", entity_type="dx",
        entity_value="v", confidence=0.9, quote="q", verified_by_user=None,
    )


@dataclass
class Reprocess:
    doc_id: str
    old_entity_id: str


@pytest_asyncio.fixture
async def reprocess(vault, monkeypatch):
    doc_id = str(uuid.uuid4())
    vault.add(Document(
        id=doc_id, profile_id=PROFILE, path_hash="p" * 64, content_hash="c" * 64,
        doc_type="visit_note_pdf", source="n.pdf", status="parsed",
        imported_at=datetime.now(timezone.utc).replace(tzinfo=None),
    ))
    ent = _entity(doc_id)
    vault.add(ent)
    await vault.commit()

    async def _pipeline(**kw):
        return {"observations_extracted": 3, "needs_verification": True, "extracted_text": "t"}

    async def _classify(profile_db, doc_id, **kw):
        profile_db.add(_entity(doc_id))
        await profile_db.commit()

    monkeypatch.setattr(documents_api, "_run_extraction_pipeline", _pipeline)
    monkeypatch.setattr(documents_api, "_classify_and_extract_entities", _classify)
    return Reprocess(doc_id, ent.id)


async def _entity_ids(vault, doc_id) -> set[str]:
    vault.expire_all()
    res = await vault.execute(select(DocumentEntity.id).where(DocumentEntity.doc_id == doc_id))
    return set(res.scalars())


def _reprocess(master, vault, r):
    return _call(documents_router, "/documents", master, vault, "POST",
                 f"/documents/{r.doc_id}/reprocess")


@pytest.mark.asyncio
async def test_hc_aud_ord_001a_reprocess_intent_fails(master, vault, reprocess):
    master.fail_on = 1
    assert _reprocess(master, vault, reprocess).status_code == 500
    assert await _entity_ids(vault, reprocess.doc_id) == {reprocess.old_entity_id}
    assert await _rows(master) == []


@pytest.mark.asyncio
async def test_hc_aud_ord_001b_reprocess_completion_fails(master, vault, reprocess):
    master.fail_on = 2
    assert _reprocess(master, vault, reprocess).status_code == 500
    assert reprocess.old_entity_id not in await _entity_ids(vault, reprocess.doc_id)
    assert [_status(r) for r in await _rows(master)] == ["started"]


@pytest.mark.asyncio
async def test_hc_aud_ord_002_reprocess_vault_commit_fails(master, vault, reprocess, monkeypatch):
    _fail_vault_commit(vault, monkeypatch)
    assert _reprocess(master, vault, reprocess).status_code == 500
    monkeypatch.undo()
    assert await _entity_ids(vault, reprocess.doc_id) == {reprocess.old_entity_id}
    assert [_status(r) for r in await _rows(master)] == ["started"]


@pytest.mark.asyncio
async def test_hc_aud_ord_003_reprocess_happy(master, vault, reprocess):
    assert _reprocess(master, vault, reprocess).status_code == 200
    rows = await _rows(master)
    assert [_status(r) for r in rows] == ["started", "completed"]
    assert _details(rows[1])["observations_extracted"] == 3
    assert rows[0].entity_id == rows[1].entity_id == reprocess.doc_id


# rows 19/20/23: interpretation regenerate ---------------------------------------


@dataclass
class Interp:
    obs_id: str
    old_id: str | None


class StubInterpret:
    """Mirrors modules/interpret.py:272-279: delete old, add new, commit vault."""

    async def interpret_observation(self, observation_id, profile_db, master_db, force_regenerate):
        old = (await profile_db.execute(
            select(LabInterpretation).where(LabInterpretation.observation_id == observation_id)
        )).scalar_one_or_none()
        if old is not None:
            await profile_db.delete(old)
            await profile_db.flush()
        new = _lab_interp(observation_id)
        profile_db.add(new)
        await profile_db.commit()
        return type("R", (), {"success": True, "interpretation": new, "error_message": None})()


def _lab_interp(obs_id: str) -> LabInterpretation:
    return LabInterpretation(
        id=str(uuid.uuid4()), profile_id=PROFILE, observation_id=obs_id,
        interpretation_text="t", severity_level="normal", citations_json="[]",
        model_id="m", model_tier="template", confidence_score=0.5,
    )


async def _seed_obs(vault, with_interp: bool) -> Interp:
    obs = Observation(
        id=str(uuid.uuid4()), profile_id=PROFILE, doc_id=str(uuid.uuid4()),
        analyte_canonical="ldl", analyte_raw="LDL Cholesterol", value=120.0,
        unit="mg/dL", ref_low=0.0, ref_high=130.0, collected_at=datetime(2026, 3, 1),
    )
    vault.add(obs)
    old = None
    if with_interp:
        old = _lab_interp(obs.id)
        vault.add(old)
    await vault.commit()
    return Interp(obs.id, old.id if old else None)


async def _interp_ids(vault, obs_id) -> set[str]:
    vault.expire_all()
    res = await vault.execute(
        select(LabInterpretation.id).where(LabInterpretation.observation_id == obs_id)
    )
    return set(res.scalars())


class _Rag:
    async def query(self, **kw):
        raise ModelUnavailableError("stub")


INTERP_ROUTES = {
    "plain": ("generate", lambda i: f"/interpretations/observations/{i.obs_id}/interpret?force_regenerate=true", 201),
    "grounded": ("grounded", lambda i: f"/interpretations/observations/{i.obs_id}/interpret-grounded?force_regenerate=true", 501),
}


def _interp_call(master, vault, kind, i):
    event, url, _ = INTERP_ROUTES[kind]
    with patch.object(interp_api, "get_interpret_module", return_value=StubInterpret()), \
            patch.object(interp_api, "get_rag_module", return_value=_Rag()):
        return _call(interp_router, "/interpretations", master, vault, "POST", url(i))


@pytest.mark.parametrize("kind", list(INTERP_ROUTES))
@pytest.mark.asyncio
async def test_hc_aud_ord_001a_interp_intent_fails(kind, master, vault):
    i = await _seed_obs(vault, True)
    master.fail_on = 1
    assert _interp_call(master, vault, kind, i).status_code == 500
    assert await _interp_ids(vault, i.obs_id) == {i.old_id}
    assert await _rows(master) == []


@pytest.mark.parametrize("kind", list(INTERP_ROUTES))
@pytest.mark.asyncio
async def test_hc_aud_ord_001b_interp_completion_fails(kind, master, vault):
    i = await _seed_obs(vault, True)
    master.fail_on = 2
    assert _interp_call(master, vault, kind, i).status_code == 500
    ids = await _interp_ids(vault, i.obs_id)
    assert len(ids) == 1 and i.old_id not in ids
    assert [_status(r) for r in await _rows(master)] == ["started"]


@pytest.mark.parametrize("kind", list(INTERP_ROUTES))
@pytest.mark.asyncio
async def test_hc_aud_ord_002_interp_vault_commit_fails(kind, master, vault, monkeypatch):
    i = await _seed_obs(vault, True)
    _fail_vault_commit(vault, monkeypatch)
    assert _interp_call(master, vault, kind, i).status_code == 500
    monkeypatch.undo()
    assert await _interp_ids(vault, i.obs_id) == {i.old_id}
    assert [_status(r) for r in await _rows(master)] == ["started"]


@pytest.mark.parametrize("kind", list(INTERP_ROUTES))
@pytest.mark.asyncio
async def test_hc_aud_ord_003_interp_happy(kind, master, vault):
    i = await _seed_obs(vault, True)
    assert _interp_call(master, vault, kind, i).status_code == INTERP_ROUTES[kind][2]
    rows = await _rows(master)
    assert [_status(r) for r in rows] == ["started", "completed"]
    assert rows[0].entity_id == rows[1].entity_id == i.obs_id


@pytest.mark.asyncio
async def test_hc_aud_ord_020_interp_first_generation_single_row_and_error_log(
    master, vault, caplog
):
    i = await _seed_obs(vault, False)
    assert _interp_call(master, vault, "plain", i).status_code == 201
    rows = await _rows(master)
    assert len(rows) == 1 and _status(rows[0]) is None

    j = await _seed_obs(vault, False)
    master.commits = 0
    master.fail_on = 1
    with caplog.at_level(logging.ERROR):
        assert _interp_call(master, vault, "plain", j).status_code == 500
    errs = [r for r in caplog.records if "AUDIT-ORDER" in r.getMessage()]
    assert len(errs) == 1 and j.obs_id in errs[0].getMessage()
    assert "LDL" not in caplog.text


@pytest.mark.asyncio
async def test_hc_aud_ord_batch_intent_pair_and_no_non_uuid_in_details(master, vault):
    i = await _seed_obs(vault, True)
    junk = "Jane Doe 1985-02-03"
    with patch.object(interp_api, "get_interpret_module", return_value=StubInterpret()):
        resp = _call(
            interp_router, "/interpretations", master, vault, "POST", "/interpretations/batch",
            json={"observation_ids": [i.obs_id, junk], "force_regenerate": True},
        )
    assert resp.status_code == 200, resp.text
    rows = await _rows(master)
    assert [_status(r) for r in rows] == ["started", "completed"]
    assert all(junk not in (r.details_json or "") and "Jane" not in (r.details_json or "")
               for r in rows)
    assert i.obs_id in rows[0].details_json


@pytest.mark.asyncio
async def test_hc_aud_ord_001a_batch_intent_fails(master, vault):
    i = await _seed_obs(vault, True)
    master.fail_on = 1
    with patch.object(interp_api, "get_interpret_module", return_value=StubInterpret()):
        resp = _call(
            interp_router, "/interpretations", master, vault, "POST", "/interpretations/batch",
            json={"observation_ids": [i.obs_id], "force_regenerate": True},
        )
    assert resp.status_code == 500
    assert await _interp_ids(vault, i.obs_id) == {i.old_id}
    assert await _rows(master) == []


# rows 29/30: pin prune ---------------------------------------------------------


@dataclass
class Pins:
    board_id: str
    stale_id: str


@pytest_asyncio.fixture
async def pins(vault):
    board = Pinboard(id=str(uuid.uuid4()), name="b")
    stale = PinboardItem(
        id=str(uuid.uuid4()), pinboard_id=board.id, item_type="observation",
        item_id=str(uuid.uuid4()),
    )
    vault.add_all([board, stale])
    await vault.commit()
    return Pins(board.id, stale.id)


async def _stale_present(vault, p: Pins) -> bool:
    vault.expire_all()
    return (await vault.execute(
        select(PinboardItem.id).where(PinboardItem.id == p.stale_id))).first() is not None


PIN_ROUTES = {
    "list": lambda p: ("GET", f"/pinboards/{p.board_id}/items", {}),
    "export": lambda p: ("POST", f"/pinboards/{p.board_id}/export", {"json": {"confirm": True}}),
}


def _pin_call(master, vault, kind, p):
    method, url, kw = PIN_ROUTES[kind](p)
    return _call(pinboards_router, "/pinboards", master, vault, method, url, **kw)


@pytest.mark.parametrize("kind", list(PIN_ROUTES))
@pytest.mark.asyncio
async def test_hc_aud_ord_001a_prune_intent_fails(kind, master, vault, pins):
    master.fail_on = 1
    assert _pin_call(master, vault, kind, pins).status_code == 500
    assert await _stale_present(vault, pins)
    assert await _rows(master) == []


@pytest.mark.parametrize("kind", list(PIN_ROUTES))
@pytest.mark.asyncio
async def test_hc_aud_ord_001b_prune_completion_fails(kind, master, vault, pins):
    master.fail_on = 2
    assert _pin_call(master, vault, kind, pins).status_code == 500
    assert not await _stale_present(vault, pins)
    assert [_status(r) for r in await _rows(master)] == ["started"]


@pytest.mark.parametrize("kind", list(PIN_ROUTES))
@pytest.mark.asyncio
async def test_hc_aud_ord_002_prune_vault_commit_fails(kind, master, vault, pins, monkeypatch):
    _fail_vault_commit(vault, monkeypatch)
    assert _pin_call(master, vault, kind, pins).status_code == 500
    monkeypatch.undo()
    assert await _stale_present(vault, pins)
    assert [_status(r) for r in await _rows(master)] == ["started"]


@pytest.mark.parametrize("kind", list(PIN_ROUTES))
@pytest.mark.asyncio
async def test_hc_aud_ord_003_prune_happy(kind, master, vault, pins):
    assert _pin_call(master, vault, kind, pins).status_code == 200
    assert not await _stale_present(vault, pins)
    rows = await _rows(master)
    assert [_status(r) for r in rows][:2] == ["started", "completed"]
    assert {r.event_type for r in rows[:2]} == {"pinboard.item_remove"}
    assert _details(rows[0])["count"] == 1


# --- T4: row 26 backup restore, row 27 profile delete ------------------------


async def _seed_profile(master) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    master.add(Profile(
        id=PROFILE, display_name="Jane Doe", encryption_key_id="k", is_locked=False,
        created_at=now, updated_at=now,
    ))
    await master.commit()
    master.commits = 0


@dataclass
class Restore:
    restore: MagicMock
    close: AsyncMock


@pytest_asyncio.fixture
async def restore_env(master, tmp_path, monkeypatch):
    await _seed_profile(master)
    restore = MagicMock(return_value=RestoreResult(
        success=True, partial=False, files_restored=3, safety_copies=[],
    ))
    close = AsyncMock()
    monkeypatch.setattr(backup_api, "authenticate_profile",
                        AsyncMock(return_value=SimpleNamespace(id=PROFILE)))
    monkeypatch.setattr(backup_api, "close_profile_database_on_logout", close)
    monkeypatch.setattr(backup_api, "_resolve_backup_dir", lambda pid, bid: tmp_path)
    monkeypatch.setattr(backup_api.backup_script, "verify", lambda p: SimpleNamespace(valid=True))
    monkeypatch.setattr(backup_api.backup_script, "restore", restore)
    return Restore(restore, close)


def _restore(master):
    with route_client(
        backup_api.router, "/backup", profile_id=PROFILE, master_db=master,
        raise_server_exceptions=False,
    ) as client:
        return client.post("/backup/backup_20261009_123456/restore", json={
            "password": "CorrectHorse1",
            "confirmation_phrase": backup_api.BACKUP_RESTORE_CONFIRMATION,
        })


@pytest.mark.asyncio
async def test_hc_aud_ord_001a_restore_intent_fails(master, restore_env):
    master.fail_on = 1
    assert _restore(master).status_code == 500
    restore_env.restore.assert_not_called()
    restore_env.close.assert_not_called()
    assert await _rows(master) == []


@pytest.mark.asyncio
async def test_hc_aud_ord_001b_restore_completion_fails(master, restore_env):
    master.fail_on = 2
    assert _restore(master).status_code == 500
    restore_env.restore.assert_called_once()
    assert [_status(r) for r in await _rows(master)] == ["started"]


@pytest.mark.asyncio
async def test_hc_aud_ord_002_restore_file_operation_fails(master, restore_env):
    restore_env.restore.side_effect = RuntimeError("disk gone")
    assert _restore(master).status_code == 500
    assert [_status(r) for r in await _rows(master)] == ["started"]


@pytest.mark.asyncio
async def test_hc_aud_ord_003_restore_happy(master, restore_env):
    assert _restore(master).status_code == 200
    rows = await _rows(master)
    assert [_status(r) for r in rows] == ["started", "completed"]
    assert rows[0].entity_id == rows[1].entity_id == "backup_20261009_123456"
    assert _details(rows[1])["count"] == 3


@dataclass
class Erase:
    vault: Path
    keys: list[Path]


@pytest_asyncio.fixture
async def erase_env(master, tmp_path, monkeypatch):
    await _seed_profile(master)
    monkeypatch.setattr(type(profiles_api.settings), "app_data_path",
                        property(lambda self: tmp_path))
    vault = tmp_path / "vaults" / PROFILE
    (vault / "docs").mkdir(parents=True)
    keys = [vault / "key.bin", vault / "key.method"]
    for k in keys:
        k.write_bytes(b"sealed")
    (vault / "vault.db").write_bytes(b"enc")
    monkeypatch.setattr(profiles_api, "authenticate_profile",
                        AsyncMock(return_value=SimpleNamespace(id=PROFILE)))
    monkeypatch.setattr(profiles_api, "close_profile_database_on_logout", AsyncMock())
    monkeypatch.setattr(profiles_api, "revoke_jwt_token", MagicMock())
    return Erase(vault, keys)


def _delete_profile(master):
    with route_client(
        profiles_api.router, "/profiles", profile_id=PROFILE, master_db=master,
        raise_server_exceptions=False,
    ) as client:
        return client.request("DELETE", f"/profiles/{PROFILE}", json={
            "password": "CorrectHorse1",
            "confirmation_phrase": profiles_api.PROFILE_DELETE_CONFIRMATION,
            "export_acknowledged": True,
        })


async def _profile_present(master) -> bool:
    master.expire_all()
    return (await master.execute(select(Profile.id))).first() is not None


@pytest.mark.asyncio
async def test_hc_aud_ord_001a_profile_delete_intent_fails(master, erase_env):
    master.fail_on = 1
    assert _delete_profile(master).status_code == 500
    assert all(k.exists() for k in erase_env.keys) and erase_env.vault.exists()
    assert await _profile_present(master)
    assert await _rows(master) == []


@pytest.mark.asyncio
async def test_hc_aud_ord_002_profile_delete_vault_sweep_fails(
    master, erase_env, monkeypatch
):
    def _boom(path, *a, **k):
        raise RuntimeError("rmtree exploded")  # not OSError: swallowed by design

    monkeypatch.setattr(profiles_api.shutil, "rmtree", _boom)
    assert _delete_profile(master).status_code == 500
    rows = await _rows(master)
    assert [(_status(r), r.profile_id) for r in rows] == [("started", PROFILE)]
    assert not any(r.event_type == "profile.delete" and r.profile_id is None for r in rows)


@pytest.mark.asyncio
async def test_hc_aud_ord_007_profile_delete_leaves_no_trace_of_id(master, erase_env):
    assert _delete_profile(master).status_code == 204
    rows = await _rows(master)
    assert len(rows) == 1 and rows[0].event_type == "profile.delete"
    assert rows[0].profile_id is None
    blob = " ".join(str(getattr(rows[0], c.name)) for c in rows[0].__table__.columns)
    assert PROFILE not in blob
    assert not erase_env.vault.exists()


# --- T5: row 28 agent chat ----------------------------------------------------


async def _agent_stub(question, profile_id, profile_db, db):
    await create_audit_log(
        db=db, event_type="agent.run", action="agent.run", profile_id=profile_id,
        entity_type="agent_run", entity_id=str(uuid.uuid4()),
    )
    return [ResponseSegment(segment_type="facts", content="ok")], "ok", VerificationInfo()


def _chat(master, vault):
    with patch.object(assistant_api, "get_rag_module", return_value=MagicMock()), \
            patch.object(assistant_api, "is_agent_enabled", return_value=True), \
            patch.object(assistant_api, "_serve_via_agent", _agent_stub):
        return _call(assistant_router, "/assistant", master, vault, "POST",
                     "/assistant/chat", json={"question": "what is my ldl?", "use_memory": False})


async def _turn_count(vault) -> int:
    vault.expire_all()
    return len((await vault.execute(select(ChatTurn.id))).all())


@pytest.mark.asyncio
async def test_hc_aud_ord_060_agent_audit_commit_fails_fails_request(master, vault):
    master.fail_on = 1
    resp = _chat(master, vault)
    assert resp.status_code >= 500, resp.text
    assert await _turn_count(vault) == 0


@pytest.mark.asyncio
async def test_hc_aud_ord_060_agent_audit_rows_committed_explicitly(master, vault):
    resp = _chat(master, vault)
    assert resp.status_code == 200, resp.text
    assert master.commits == 1, "agent audit rows were left to the after-response commit"
    assert [r.event_type for r in await _rows(master)] == ["agent.run"]
