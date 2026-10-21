"""GATE-12: the conftest guard that stops any test opening the real master DB."""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
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
    return gate._GATE12_HITS


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


def test_hc_gate12_002_check_fails_on_new_hit_and_passes_without(tmp_path):
    start = len(_hits())
    gate._gate12_check(start, "x")  # no new hit: returns
    _hits().append("x")
    with pytest.raises(pytest.fail.Exception) as exc:
        gate._gate12_check(start, "x")  # also drops the hit it reported
    assert len(_hits()) == start
    assert "GATE-12" in str(exc.value)
    assert "I-12" in str(exc.value)

    # Wiring: the real conftest must fail a test whose body leaves a hit behind (e.g. a
    # swallowed error). Calling _gate12_check directly cannot see a dropped autouse fixture.
    shutil.copy(Path(gate.__file__), tmp_path / "conftest.py")
    (tmp_path / "test_inner.py").write_text(
        "import conftest\n\n"
        "def test_inner():\n"
        "    conftest._GATE12_HITS.append('swallowed')\n"
    )
    backend = Path(gate.__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(backend), "HF_HUB_OFFLINE": "1"}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_inner.py"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120,
    )
    out = proc.stdout + proc.stderr
    assert "1 passed, 1 error" in out, out
    # the per-test check names the test node; the session-end backstop would name the hit
    assert "GATE-12" in out and "[test_inner.py::test_inner]" in out, out


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


@pytest.mark.asyncio
async def test_hc_gate12_004_guard_raises_with_master_db_present():
    # Pins that the guard RAISES (not merely records) even when the master DB file exists,
    # as on a developer machine: a record-only listener would let the connect succeed.
    real = Path(database.engine.url.database)
    existed, dir_existed = real.exists(), real.parent.exists()
    real.parent.mkdir(parents=True, exist_ok=True)
    if not real.exists():
        real.touch()
    before = len(_hits())
    try:
        with pytest.raises(RuntimeError, match="GATE-12"):
            async with database.engine.connect():
                pass
        hits = _hits()
        assert len(hits) == before + 1
        assert "test_hc_gate12_004" in hits[-1]
        hits.pop()  # our own hit, so this test's teardown check passes
    finally:
        await database.engine.dispose()
        if not existed:
            real.unlink(missing_ok=True)
        if not dir_existed:
            real.parent.rmdir()


def test_hc_gate12_005_session_end_backstop_fails_on_late_hit(tmp_path):
    # A hit appended in session-fixture teardown falls outside every per-test window;
    # only the session-end backstop in conftest can report it.
    shutil.copy(Path(gate.__file__), tmp_path / "conftest.py")
    (tmp_path / "test_inner.py").write_text(
        "import conftest\n"
        "import pytest\n\n"
        "@pytest.fixture(scope='session')\n"
        "def late():\n"
        "    yield\n"
        "    conftest._GATE12_HITS.append('late-session-teardown')\n\n"
        "def test_inner(late):\n"
        "    pass\n"
    )
    backend = Path(gate.__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(backend), "HF_HUB_OFFLINE": "1"}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_inner.py"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120,
    )
    out = proc.stdout + proc.stderr
    assert "1 passed, 1 error" in out, out
    assert "[late-session-teardown]" in out, out
