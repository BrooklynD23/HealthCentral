"""Worker PID file (HC-WOW-*, WIN-ORPHAN-WORKER).

On Windows the venv python.exe is a stub and `uvicorn --reload` spawns the
serving worker as a child. When the launcher chain dies, that worker can live on
with no parent, holding profile vault handles. The backend records its own PID
so dev.ps1 can find and stop it. These tests pin the file's content, atomicity,
location and the one-writer rule; the dev.ps1 side is pinned by the text tests
at the bottom (the real Windows decision is exercised in the PR's probe).
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parents[1]


@pytest.fixture
def pidfile(tmp_path, monkeypatch):
    path = tmp_path / "logs" / "dev-backend.pid"
    monkeypatch.setenv("HC_WORKER_PIDFILE", str(path))
    return path


def test_hc_wow_001_pidfile_has_pid_ppid_and_start_time_and_is_removed_on_shutdown(pidfile):
    import time

    from core import worker_pidfile

    before = time.time()
    written = worker_pidfile.write_worker_pidfile()
    assert written == pidfile
    data = json.loads(pidfile.read_text(encoding="utf-8"))
    assert data["pid"] == os.getpid()
    assert data["ppid"] == os.getppid()
    assert before - 1 <= data["started_unix"] <= time.time() + 1
    assert data["started_at"].endswith("Z")

    worker_pidfile.remove_worker_pidfile()
    assert not pidfile.exists()
    worker_pidfile.remove_worker_pidfile()  # a second call is harmless


def test_hc_wow_001b_lifespan_writes_when_serving_and_removes_on_shutdown(pidfile, monkeypatch):
    from fastapi import FastAPI

    import main as main_module

    monkeypatch.setattr("modules.notification_scheduler.start_notification_scheduler", AsyncMock())
    monkeypatch.setattr("modules.notification_scheduler.stop_notification_scheduler", AsyncMock())
    monkeypatch.setattr("modules.backup_scheduler.start_backup_scheduler", AsyncMock())
    monkeypatch.setattr("modules.backup_scheduler.stop_backup_scheduler", AsyncMock())
    monkeypatch.setattr(main_module, "init_database", AsyncMock())
    monkeypatch.setattr(main_module, "close_database", AsyncMock())
    monkeypatch.setattr(main_module, "run_master_migrations_async", AsyncMock())
    monkeypatch.setattr("core.db_migration.migrate_master_db_filename", MagicMock())
    monkeypatch.setattr("scripts.seed_knowledge_base.seed_all", AsyncMock(return_value={}))
    monkeypatch.setattr(
        main_module, "settings",
        SimpleNamespace(validate_startup=lambda: [], app_data_path="/tmp/hc-wow-test"),
    )

    seen_while_serving = {}

    async def drive():
        async with main_module.lifespan(FastAPI()):
            seen_while_serving["exists"] = pidfile.exists()
            seen_while_serving["pid"] = json.loads(pidfile.read_text(encoding="utf-8"))["pid"]

    asyncio.run(drive())
    assert seen_while_serving == {"exists": True, "pid": os.getpid()}
    assert not pidfile.exists()


def test_hc_wow_001c_nothing_is_written_when_the_launcher_did_not_ask(tmp_path, monkeypatch):
    from core import worker_pidfile

    monkeypatch.delenv("HC_WORKER_PIDFILE", raising=False)
    monkeypatch.chdir(tmp_path)
    assert worker_pidfile.write_worker_pidfile() is None
    assert list(tmp_path.iterdir()) == []


def test_hc_wow_002_write_is_atomic_and_leaves_no_temp_file(pidfile, monkeypatch):
    from core import worker_pidfile

    # An earlier, complete file must survive a write that dies half-way.
    worker_pidfile.write_worker_pidfile()
    before = pidfile.read_text(encoding="utf-8")

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    assert worker_pidfile.write_worker_pidfile() is None  # fail-soft: must not stop the app booting
    monkeypatch.undo()
    assert pidfile.read_text(encoding="utf-8") == before
    assert json.loads(before)["pid"] == os.getpid()
    assert [p.name for p in pidfile.parent.iterdir()] == [pidfile.name]  # no .tmp left behind


def test_hc_wow_002b_a_reader_never_sees_a_partial_file(pidfile):
    """The content reaches the final name only through os.replace of a finished temp file."""
    from core import worker_pidfile

    calls = []
    real_replace = os.replace

    def spy(src, dst):
        calls.append((Path(src).read_text(encoding="utf-8"), Path(dst)))
        real_replace(src, dst)

    os.replace = spy
    try:
        worker_pidfile.write_worker_pidfile()
    finally:
        os.replace = real_replace
    assert len(calls) == 1
    content, dst = calls[0]
    assert dst == pidfile
    assert json.loads(content)["pid"] == os.getpid()  # already complete at the moment of the rename


def test_hc_wow_003_path_is_never_inside_the_data_dir_and_backup_never_collects_it(tmp_path, monkeypatch):
    from core import worker_pidfile
    from scripts import backup as backup_script

    data_dir = tmp_path / "data"
    vault = data_dir / "vaults" / "profile-1"
    vault.mkdir(parents=True)
    (vault / "vault.db").write_bytes(b"x")
    (vault / "key.bin").write_bytes(b"k")
    monkeypatch.setattr(worker_pidfile, "_data_dir", lambda: data_dir)

    # Inside the data dir (any vault dir) is refused, not written.
    for bad in (vault / "dev-backend.pid", data_dir / "dev-backend.pid"):
        monkeypatch.setenv("HC_WORKER_PIDFILE", str(bad))
        assert worker_pidfile.write_worker_pidfile() is None
        assert not bad.exists()

    # The launcher's real location (logs/ next to data/) is accepted ...
    ok = tmp_path / "logs" / "dev-backend.pid"
    monkeypatch.setenv("HC_WORKER_PIDFILE", str(ok))
    assert worker_pidfile.write_worker_pidfile() == ok
    # ... and the backup collectors, which only read data/, cannot see it.
    collected = {
        *map(str, backup_script._discover_databases(data_dir)),
        *map(str, backup_script._discover_key_files(data_dir)),
    }
    assert str(ok) not in collected
    assert not any(c.endswith(".pid") for c in collected)

    # dev.ps1 sets exactly that location for the backend.
    dev = (REPO / "dev.ps1").read_text(encoding="utf-8")
    assert 'Join-Path $ROOT_DIR "logs\\dev-backend.pid"' in dev
    assert "$env:HC_WORKER_PIDFILE = $workerPidFile" in dev


_CHILD = textwrap.dedent(
    """
    import os, sys
    sys.path.insert(0, {backend!r})
    from core import worker_pidfile
    worker_pidfile.write_worker_pidfile()
    print(os.getpid(), os.getppid())
    """
)


def test_hc_wow_004_only_the_serving_process_writes_not_its_reloader_parent(tmp_path, monkeypatch):
    """uvicorn --reload runs the lifespan only in the spawned worker; its supervising parent never
    imports main:app. Reproduce the shape: a parent (this test process, standing in for the
    reloader) spawns a worker. The file must name the worker, with the parent as ppid."""
    path = tmp_path / "logs" / "dev-backend.pid"
    monkeypatch.setenv("HC_WORKER_PIDFILE", str(path))
    out = subprocess.run(
        [sys.executable, "-c", _CHILD.format(backend=str(BACKEND))],
        capture_output=True, text=True, check=True, env={**os.environ, "HC_WORKER_PIDFILE": str(path)},
    ).stdout.split()
    worker_pid, worker_ppid = int(out[0]), int(out[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["pid"] == worker_pid != os.getpid()
    assert data["ppid"] == worker_ppid == os.getpid()


def test_hc_wow_004b_an_old_worker_shutting_down_never_deletes_a_newer_workers_file(pidfile):
    """On reload or restart the old worker can finish shutting down after the new one wrote."""
    from core import worker_pidfile

    newer = {"pid": os.getpid() + 100000, "ppid": 1, "started_unix": 1.0, "started_at": "x"}
    pidfile.parent.mkdir(parents=True, exist_ok=True)
    pidfile.write_text(json.dumps(newer), encoding="utf-8")
    worker_pidfile.remove_worker_pidfile()
    assert json.loads(pidfile.read_text(encoding="utf-8")) == newer


# ---- dev.ps1 text tests (HC-WOW-005+). The real Windows decision is run in the PR probe. ----

DEV = (REPO / "dev.ps1").read_text(encoding="utf-8")


def _func(name: str) -> str:
    start = DEV.index(f"function {name}")
    nxt = DEV.find("\nfunction ", start + 1)
    return DEV[start: nxt if nxt != -1 else len(DEV)]


def test_hc_wow_005_launcher_reads_pidfile_and_verifies_the_command_line_before_acting():
    fn = _func("Test-AsclexisWorkerProcess")
    assert "Win32_Process" in fn
    assert "CommandLine" in fn
    # a Python process, not just any live PID (Windows reuses PIDs)
    assert "python" in fn and "pythonw" in fn
    assert "uvicorn" in fn and "spawn_main" in fn
    # and not one created after the file was written (a reused PID)
    assert "CreationDate" in fn and "started_unix" in DEV


def test_hc_wow_006_launcher_refuses_to_start_over_a_live_recorded_worker():
    assert "Read-WorkerPidFile" in DEV
    assert 'Asclexis is already running from this folder (PID $($worker.pid)). Close it first, or run: taskkill /PID $($worker.pid) /T /F' in DEV
    # the check runs before ports are picked or freed, and before anything is launched
    assert DEV.index("Read-WorkerPidFile -Path $workerPidFile") < DEV.index("Port $BACKEND_PORT is in use")
    refuse = DEV[DEV.index('Asclexis is already running from this folder (PID $($worker.pid))'):]
    assert "exit 1" in refuse.split("Port $BACKEND_PORT is in use")[0]


def test_hc_wow_007_a_stale_file_is_removed_with_one_info_line():
    assert "Removed a stale worker PID file" in DEV
    assert "Remove-Item -LiteralPath $workerPidFile" in DEV


def test_hc_wow_008_shutdown_and_restart_paths_kill_the_recorded_worker_then_remove_the_file():
    stop = _func("Stop-RecordedWorker")
    assert "taskkill.exe" in stop and "/T" in stop and "/F" in stop
    assert "Test-AsclexisWorkerProcess" in stop  # verified before killing
    assert "-NotBefore" in stop or "$NotBefore" in stop  # from this run only
    assert "Remove-Item" in stop
    shutdown = _func("Stop-Servers")
    assert "Stop-RecordedWorker" in shutdown
    # restart path: the dead backend's worker is stopped before the new backend is started
    restart = DEV[DEV.index("$backendRestartCount++"):]
    assert restart.index("Stop-RecordedWorker") < restart.index("Start-BackendDevServer")


def test_hc_wow_009_backend_is_told_where_to_write_the_file():
    fn = _func("Start-BackendDevServer")
    assert "$env:HC_WORKER_PIDFILE = $workerPidFile" in fn
