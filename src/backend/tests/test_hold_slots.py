"""Guards for ``scripts/hold_slots.sh`` and ``scripts/quiet_run.sh`` (HC-HSL-001…004).

HOLD-SLOTS-IN-REPO: the quiet-run wrappers used to live only in
``/tmp/claude-1000`` (a reboot wiped them) and ``hold_slots.sh`` held a fixed
list of slots ``1..8`` while ``pyslot.sh`` hands out ``1..${PYSLOTS:-3}``, so a
``PYSLOTS=9`` run started beside a quiet run (recurring-failures §20). The
wrapper now also takes an exclusive hold lock, ``hc-pytest.hold.lock``, which
``pyslot.sh`` checks before every slot attempt.

- HC-HSL-001: both scripts exist, are executable and LF-only.
- HC-HSL-002: with ``hold_slots.sh`` holding, ``PYSLOTS=9 pyslot.sh true`` does
  not run; after the hold ends (even with an orphaned child left behind) it runs.
- HC-HSL-003: a slot held elsewhere makes ``hold_slots.sh`` exit 75 naming the holder.
- HC-HSL-004: ``quiet_run.sh --max-wait 1`` on a box that is never quiet exits 75.

Every functional case runs *copies* inside ``tmp_path`` with the
``/tmp/claude-1000`` lock dir rewritten there, so the box's real pytest slots
are never touched.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parents[1]
SCRIPTS = REPO_ROOT / "scripts"

_NEEDS_BASH_FLOCK = pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None or shutil.which("flock") is None,
    reason="needs bash+flock",
)


def _scratch(tmp_path: Path, name: str, *, edits: tuple[tuple[str, str], ...] = ()) -> Path:
    """Copy ``scripts/<name>`` into ``tmp_path`` with the lock dir moved there."""
    text = (SCRIPTS / name).read_text(encoding="utf-8")
    text = text.replace("/tmp/claude-1000", str(tmp_path))
    for old, new in edits:
        edited = text.replace(old, new, 1)
        assert edited != text, f"edit did not apply in {name}: {old!r}"
        text = edited
    copy = tmp_path / name
    copy.write_text(text, encoding="utf-8")
    copy.chmod(0o755)
    return copy


def _probe(lock: Path) -> int:
    """``flock -n -E 75 <lock> true``: 0 when free, 75 when held exclusively."""
    return subprocess.run(
        ["flock", "-n", "-E", "75", str(lock), "true"], capture_output=True, timeout=10
    ).returncode


def _wait_for(predicate, seconds: float, what: str) -> None:
    deadline = time.monotonic() + seconds
    while not predicate():
        assert time.monotonic() < deadline, what
        time.sleep(0.05)


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except OSError:
        pass
    proc.wait(timeout=15)


@pytest.mark.parametrize("name", ["hold_slots.sh", "quiet_run.sh"])
def test_hc_hsl_001_wrappers_exist_executable_and_lf_only(name):
    path = SCRIPTS / name
    assert path.is_file(), f"{path} missing: the wrapper must live in the repo"
    data = path.read_bytes()
    assert data.startswith(b"#!/usr/bin/env bash\n"), data[:40]
    assert b"\r" not in data, f"scripts/{name} must keep LF endings"
    if sys.platform != "win32":
        assert os.access(path, os.X_OK), f"scripts/{name} must be executable"


@_NEEDS_BASH_FLOCK
def test_hc_hsl_002_a_pyslots9_run_blocks_while_the_hold_lock_is_held(tmp_path):
    """The measured §20 escape: slots 1-8 held, ``PYSLOTS=9`` took slot 9 at once."""
    hold = _scratch(tmp_path, "hold_slots.sh")
    pyslot = _scratch(tmp_path, "pyslot.sh", edits=(("sleep 5", "sleep 1"),))
    hold_lock = tmp_path / "hc-pytest.hold.lock"
    env = {**os.environ, "PYSLOTS": "9"}

    # Case 1: the hold command runs; a PYSLOTS=9 run must not start meanwhile.
    holder = subprocess.Popen(
        [str(hold), "sleep", "6"],
        env={**os.environ, "HOLD_WAIT": "5"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        assert "holding" in holder.stdout.readline(), "hold_slots never reported holding"
        blocked = subprocess.Popen(
            [str(pyslot), "true"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        try:
            time.sleep(3)
            assert blocked.poll() is None, (
                f"PYSLOTS=9 ran while hold_slots held (rc={blocked.returncode}): "
                "slot 9 is outside the held list and the hold lock is not checked"
            )
        finally:
            blocked.wait(timeout=30)  # runs once the 6 s hold ends
        assert blocked.returncode == 0, blocked.returncode
    finally:
        _kill_group(holder)
    assert _probe(hold_lock) == 0, "the hold lock must be released when the hold ends"

    # Case 2: the held command leaves an orphan behind; it must not keep the
    # hold lock (the #490 class), so the next run starts at once.
    pid_file = tmp_path / "orphan.pid"
    run = subprocess.run(
        [str(hold), "bash", "-c", f"sleep 30 >/dev/null 2>&1 & echo $! > {pid_file}; exit 0"],
        env={**os.environ, "HOLD_WAIT": "5"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    orphan = int(pid_file.read_text().strip())
    try:
        assert run.returncode == 0, (run.returncode, run.stdout, run.stderr)
        assert _probe(hold_lock) == 0, "an orphaned child leaked the hold lock"
        after = subprocess.run([str(pyslot), "true"], env=env, capture_output=True, timeout=30)
        assert after.returncode == 0, after
    finally:
        try:
            os.kill(orphan, signal.SIGTERM)
        except OSError:
            pass


@_NEEDS_BASH_FLOCK
@pytest.mark.skipif(shutil.which("fuser") is None, reason="needs fuser")
def test_hc_hsl_003_a_busy_slot_exits_75_and_names_the_holder(tmp_path):
    hold = _scratch(tmp_path, "hold_slots.sh")
    slot2 = tmp_path / "hc-pytest.2.lock"
    holder = subprocess.Popen(
        ["flock", str(slot2), "sleep", "8"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        _wait_for(lambda: _probe(slot2) == 75, 3, "the holder never took the scratch slot")
        run = subprocess.run(
            [str(hold), "true"],
            env={**os.environ, "HOLD_WAIT": "1"},
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        _kill_group(holder)
    assert run.returncode == 75, (run.returncode, run.stdout, run.stderr)
    assert "slot 2 not free" in run.stdout, run.stdout
    assert str(holder.pid) in run.stdout, f"holder pid {holder.pid} not named: {run.stdout!r}"
    assert _probe(tmp_path / "hc-pytest.hold.lock") == 0, "a failed hold must release the hold lock"


@_NEEDS_BASH_FLOCK
def test_hc_hsl_004_quiet_run_exits_75_when_the_box_is_never_quiet(tmp_path):
    _scratch(tmp_path, "hold_slots.sh")
    quiet = _scratch(tmp_path, "quiet_run.sh", edits=(("sleep 10", "sleep 1"),))
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    ss = stubs / "ss"
    ss.write_text("#!/usr/bin/env bash\necho 'LISTEN 0 128 0.0.0.0:3000 0.0.0.0:*'\n")
    ss.chmod(0o755)
    run = subprocess.run(
        [str(quiet), "--max-wait", "1", "true"],
        env={**os.environ, "PATH": f"{stubs}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run.returncode == 75, (run.returncode, run.stdout, run.stderr)
    assert "never quiet in 1s" in run.stdout, run.stdout
    assert "ports=1" in run.stdout, run.stdout
