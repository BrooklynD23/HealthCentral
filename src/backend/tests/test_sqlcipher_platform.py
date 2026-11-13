"""HC-SQLC-011, 014, 015, 016: platform pins and the SQLCipher file probe (SQLCIPHER-WHEEL).

Nothing here imports the `core` package: it must run on a bare Windows runner.
HC-SQLC-011 reads requirements.txt and requirements-sqlcipher-win.txt, so the pin
in one cannot drift from the other or from dev.ps1.
"""

from __future__ import annotations

import importlib.metadata
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from packaging.markers import Marker
from packaging.requirements import Requirement

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parents[1]
WHEEL_SHA = "698d58f9ea5d5208bb06ee542678f3aa7921078b3bee8783f7c3fb861910eca6"


def _requirement_lines(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split(" #")[0].strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def test_hc_sqlc_011_exactly_one_sqlcipher_requirement_per_platform():
    reqs = [
        Requirement(line.split(" --hash")[0])
        for line in _requirement_lines(BACKEND / "requirements.txt")
        if "sqlcipher" in line
    ]
    for platform, expected in (
        ("win32", "sqlcipher3"),
        ("linux", "sqlcipher3-binary"),
        ("darwin", "sqlcipher3-binary"),
    ):
        env = {"sys_platform": platform}
        selected = [r.name for r in reqs if r.marker is None or r.marker.evaluate(env)]
        assert selected == [expected], (platform, selected)
    win = next(r for r in reqs if r.name == "sqlcipher3")
    assert str(win.specifier) == "==0.6.5"
    assert isinstance(win.marker, Marker)


def test_hc_sqlc_011b_windows_pin_matches_the_hashed_file_and_dev_ps1():
    win_file = BACKEND / "requirements-sqlcipher-win.txt"
    lines = _requirement_lines(win_file)
    assert len(lines) == 1, lines
    assert lines[0] == f"sqlcipher3==0.6.5 --hash=sha256:{WHEEL_SHA}"
    main = _requirement_lines(BACKEND / "requirements.txt")
    assert 'sqlcipher3==0.6.5; sys_platform == "win32"' in main
    assert "sqlcipher3-binary>=0.5.0; sys_platform != \"win32\"" in main
    dev = (REPO / "dev.ps1").read_text(encoding="utf-8")
    assert "requirements-sqlcipher-win.txt" in dev


def test_hc_sqlc_011c_hashed_install_is_binary_only_with_no_deps():
    dev = (REPO / "dev.ps1").read_text(encoding="utf-8")
    line = next(l for l in dev.splitlines() if "$venvPip install" in l and "$sqlcipherReqs" in l)
    for flag in ("--only-binary=:all:", "--no-deps", "--require-hashes"):
        assert flag in line, (flag, line)


def test_hc_sqlc_010_launcher_never_disables_encryption_silently():
    dev = (REPO / "dev.ps1").read_text(encoding="utf-8")
    # the whole-log fallback that flipped .env to false is gone
    assert not re.search(r'-match\s+"sqlcipher"', dev)
    assert not re.search(r'-notmatch\s+"sqlcipher"', dev)
    assert "dev.bat stopped so your health data is never stored unencrypted; .env was not changed" in dev
    assert "--file-probe" in dev
    assert "will NOT be encrypted" in dev
    # the default .env written without a template requires encryption
    assert '"DATABASE_ENCRYPTION_REQUIRED=true"' in dev
    assert '"DATABASE_ENCRYPTION_REQUIRED=false"' not in dev
    # false -> true flip once the probe passed
    assert 'Key "DATABASE_ENCRYPTION_REQUIRED" -Value "true"' in dev
    # the only write of false comes after HC_ALLOW_UNENCRYPTED is read
    writes = [m.start() for m in re.finditer(r'Key "DATABASE_ENCRYPTION_REQUIRED" -Value "false"', dev)]
    assert len(writes) == 1
    assert dev.index("HC_ALLOW_UNENCRYPTED") < writes[0]


def test_hc_sqlc_010b_launcher_stops_on_an_asclexis_already_running_from_this_folder():
    dev = (REPO / "dev.ps1").read_text(encoding="utf-8")
    assert "Win32_Process" in dev
    assert "Asclexis is already running from this folder (PID" in dev
    assert "taskkill /PID" in dev
    # the check runs before the launcher picks or frees ports
    assert dev.index("Asclexis is already running from this folder") < dev.index("Port $BACKEND_PORT is in use")


@pytest.mark.skipif(sys.platform != "win32", reason="the Windows wheel is installed only on win32")
def test_hc_sqlc_014_windows_installs_the_pinned_wheel():
    assert importlib.metadata.version("sqlcipher3") == "0.6.5"
    import sqlcipher3

    conn = sqlcipher3.connect(":memory:")
    try:
        assert conn.execute("PRAGMA cipher_version").fetchone()[0]
    finally:
        conn.close()


def _probe(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(REPO / "scripts" / "check_sqlcipher.py"), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_hc_sqlc_015_file_probe_proves_ciphertext_on_disk():
    pytest.importorskip("sqlcipher3")
    result = _probe("--file-probe")
    assert result.returncode == 0, result.stderr
    assert "file probe" in result.stdout


_FAKE_SQLCIPHER = """
import sqlite3 as _s
DatabaseError = _s.DatabaseError
class _Conn:
    def __init__(self, *a, **k):
        self._c = _s.connect(*a, **k)
    def execute(self, sql, *a):
        low = sql.strip().lower()
        if low.startswith("pragma cipher_version"):
            return self._c.execute("select '4.99 fake'")
        if low.startswith("pragma key"):
            return self._c.execute("select 1")
        return self._c.execute(sql, *a)
    def __getattr__(self, name):
        return getattr(self._c, name)
def connect(*a, **k):
    return _Conn(*a, **k)
"""


def test_hc_sqlc_016_file_probe_fails_when_the_file_is_plaintext(tmp_path):
    """Negative control: a module that reports a cipher version but ignores PRAGMA key
    writes a plaintext file; the probe must catch it and exit 1."""
    fake = tmp_path / "fake"
    fake.mkdir()
    (fake / "sqlcipher3.py").write_text(_FAKE_SQLCIPHER, encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(fake)}
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "check_sqlcipher.py"), "--file-probe"],
        capture_output=True, text=True, timeout=60, env=env,
    )
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "FAIL" in result.stderr
    assert "plaintext" in result.stderr


FIXTURE_KEY = "A5" * 32  # synthetic, test-only


def test_hc_sqlc_017_vault_written_by_sqlcipher3_binary_opens_with_this_platforms_package():
    """tests/fixtures/sqlcipher/vault_binary_060.db was written on Linux with sqlcipher3-binary
    0.6.0 (SQLCipher 4.12.0), raw hex key, one synthetic row:

        c = sqlcipher3.connect(path); c.execute("PRAGMA key = \\"x'A5...A5'\\"")
        CREATE TABLE observations (id INTEGER PRIMARY KEY, name TEXT NOT NULL, value REAL NOT NULL)
        INSERT INTO observations VALUES (1, 'synthetic-analyte', 4.2)

    A vault moved between machines (backup/restore) must open with whatever package
    the platform installs; on Windows that is the sqlcipher3 0.6.5 wheel."""
    sqlcipher3 = pytest.importorskip("sqlcipher3")
    fixture = BACKEND / "tests" / "fixtures" / "sqlcipher" / "vault_binary_060.db"
    assert fixture.read_bytes()[:16] != b"SQLite format 3\x00"
    conn = sqlcipher3.connect(str(fixture))
    try:
        conn.execute(f"PRAGMA key = \"x'{FIXTURE_KEY}'\"")
        assert conn.execute("SELECT id, name, value FROM observations").fetchall() == [
            (1, "synthetic-analyte", 4.2)
        ]
    finally:
        conn.close()
