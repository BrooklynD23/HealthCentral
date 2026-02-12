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

