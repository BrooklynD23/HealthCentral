"""
Pytest configuration for HealthCentral backend tests.

Some execution environments sandbox writes outside the workspace (including the
system temp directory). Pytest's `tmp_path` fixture uses the OS temp dir by
default, so we ensure a writable temp directory inside the repo when needed.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _is_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".hc_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _ensure_writable_temp_dir() -> None:
    current = (
        os.environ.get("TMPDIR")
        or os.environ.get("TEMP")
        or os.environ.get("TMP")
        or tempfile.gettempdir()
    )

    if current and _is_writable_dir(Path(current)):
        return

    repo_temp = Path(__file__).resolve().parents[1] / ".tmp_pytest"
    repo_temp.mkdir(parents=True, exist_ok=True)

    os.environ["TMPDIR"] = str(repo_temp)
    os.environ["TEMP"] = str(repo_temp)
    os.environ["TMP"] = str(repo_temp)

    # Reset tempdir cache to ensure tempfile/pytest picks up the new env vars.
    tempfile.tempdir = None


_ensure_writable_temp_dir()

# TEST-ONLY: Mark this as a test environment. Never set these in production.
# See TEST-001 in docs/features/TASK_LIST.md.
os.environ["TEST_MODE"] = "1"

# TEST-ONLY: Disable SQLCipher requirement for test environments that lack
# the native library. Never set this in production. See TEST-001.
os.environ["DATABASE_ENCRYPTION_REQUIRED"] = "false"



# GATE-12: no test may open the real master DB (contracts I-12). Tests that need a
# master DB must patch core.database.async_session_maker to their own maker.
import pytest  # noqa: E402

_GATE12_HITS: list[str] = []
_GATE12_MSG = (
    "GATE-12: a test opened the real master DB (data/asclexis.db). "
    "Patch core.database.async_session_maker to a test maker (contracts I-12)."
)


@pytest.fixture(scope="session", autouse=True)
def _gate12_guard():
    from sqlalchemy import event

    from core import database

    def _on_connect(dialect, conn_rec, cargs, cparams):
        current = os.environ.get("PYTEST_CURRENT_TEST", "<outside a test>")
        _GATE12_HITS.append(current.rsplit(" (", 1)[0])
        raise RuntimeError(_GATE12_MSG)  # before the DBAPI connects: no file is created

    event.listen(database.engine.sync_engine, "do_connect", _on_connect)
    yield
    event.remove(database.engine.sync_engine, "do_connect", _on_connect)


def _gate12_check(start: int, nodeid: str) -> None:
    if len(_GATE12_HITS) > start:
        pytest.fail(f"{_GATE12_MSG} [{nodeid}]", pytrace=False)


@pytest.fixture(autouse=True)
def _gate12_per_test(request, _gate12_guard):
    start = len(_GATE12_HITS)
    yield
    _gate12_check(start, request.node.nodeid)
