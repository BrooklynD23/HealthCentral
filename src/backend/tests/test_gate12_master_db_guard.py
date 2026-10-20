"""GATE-12: the conftest guard that stops any test opening the real master DB."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from core import database, denial_audit
from core.database import Base
from models.audit import AuditLog

gate = importlib.import_module("tests.conftest")


def _hits() -> list:
    return getattr(gate, "_GATE12_HITS", [])


@pytest_asyncio.fixture
async def master_maker():
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_hc_gate12_001_real_master_engine_is_blocked_and_recorded():
    # SQLAlchemy's sqlite dialect resolves the relative URL to an absolute path when the
    # engine is built at import, so chdir cannot redirect it: use the engine's real path.
    real = Path(database.engine.url.database)
    existed, dir_existed = real.exists(), real.parent.exists()
    real.parent.mkdir(parents=True, exist_ok=True)  # as on a developer machine
    denial_audit._state.clear()
    before = len(_hits())
    try:
        await denial_audit.audit_denial("caller-x", "document")  # swallows the guard's error
        created = real.exists() and not existed
        hits = _hits()
        # "file absent" alone could pass vacuously (e.g. no data/ dir); the hit list must grow.
        assert len(hits) == before + 1
        assert "test_hc_gate12_001" in hits[-1]
        hits.pop()  # our own hit, so this test's teardown check passes
        assert not created
    finally:
        if not existed:
            real.unlink(missing_ok=True)
        if not dir_existed:
            real.parent.rmdir()


def test_hc_gate12_002_check_fails_on_new_hit_and_passes_without():
    start = len(_hits())
    gate._gate12_check(start, "x")  # no new hit: returns
    _hits().append("x")
    try:
        with pytest.raises(pytest.fail.Exception) as exc:
            gate._gate12_check(start, "x")
    finally:
        _hits().pop()
    assert "GATE-12" in str(exc.value)
    assert "I-12" in str(exc.value)


@pytest.mark.asyncio
async def test_hc_gate12_003_patched_master_maker_is_not_blocked(master_maker, monkeypatch):
    denial_audit._state.clear()
    monkeypatch.setattr(denial_audit.database, "async_session_maker", master_maker)
    before = len(_hits())

    await denial_audit.audit_denial("caller-x", "document")

    async with master_maker() as s:
        rows = list((await s.execute(select(AuditLog))).scalars())
    assert [r.event_type for r in rows] == ["denial.cross_profile"]
    assert len(_hits()) == before
