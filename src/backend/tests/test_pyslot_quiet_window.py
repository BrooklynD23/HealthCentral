"""Guards for WF-PYSLOTS-6 and WF-QUIET-WINDOW (HC-QW-001...007).

- HC-QW-001: ``pyslot.sh`` defaults to 6 slots and ``hold_slots.sh`` still claims them all.
- HC-QW-002: 6 parallel ``pyslot.sh`` runs proceed at once under the default; a 7th waits.
- HC-QW-003: a caller waiting past ``PYSLOT_WAIT_WARN_MIN`` gets ONE stderr line naming the
  wait and the holder PID, keeps waiting and then runs (report, do not fail).
- HC-QW-004: ``quiet_run.sh`` outside ``QUIET_WINDOW`` without ``QUIET_FORCE=1`` refuses (76)
  and runs nothing; with no window set it behaves as before.
- HC-QW-005: a forced run outside the window is killed at ``QUIET_MAX_MIN`` and its locks
  are released.
- HC-QW-006: inside the window there is no cap.
- HC-QW-007: a malformed ``QUIET_WINDOW`` exits 64.

Every functional case runs *copies* of the scripts inside ``tmp_path`` with the
``/tmp/claude-1000`` lock dir rewritten there; the box's real slots are never touched.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"

_NEEDS = pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None or shutil.which("flock") is None,
    reason="needs bash+flock",
)


def _scratch(tmp_path: Path, name: str, *, edits: tuple[tuple[str, str], ...] = ()) -> Path:
    text = (SCRIPTS / name).read_text(encoding="utf-8").replace("/tmp/claude-1000", str(tmp_path))
    for old, new in edits:
        edited = text.replace(old, new, 1)
        assert edited != text, f"edit did not apply in {name}: {old!r}"
        text = edited
    copy = tmp_path / name
    copy.write_text(text, encoding="utf-8")
    copy.chmod(0o755)
    return copy


def _probe(lock: Path) -> int:
    return subprocess.run(
        ["flock", "-n", "-E", "75", str(lock), "true"], capture_output=True, timeout=10
    ).returncode


def _wait_for(predicate, seconds: float, what: str) -> None:
    deadline = time.monotonic() + seconds
    while not predicate():
        assert time.monotonic() < deadline, what
        time.sleep(0.05)


def _env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYSLOT", "QUIET", "HOLD"))}
    env.update(extra)
    return env


def _window(start_offset_min: int, end_offset_min: int) -> str:
    now = datetime.now()
    s, e = now + timedelta(minutes=start_offset_min), now + timedelta(minutes=end_offset_min)
    return f"{s:%H:%M}-{e:%H:%M}"


def _quiet_scratch(tmp_path: Path) -> Path:
    """quiet_run + hold_slots copies on a box that is always quiet (stubbed probes)."""
    _scratch(tmp_path, "hold_slots.sh")
    quiet = _scratch(
        tmp_path,
        "quiet_run.sh",
        edits=(('load=$(cut -d" " -f1 /proc/loadavg)', "load=0"), ("sleep 10", "sleep 1")),
    )
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for stub in ("pgrep", "ss"):
        (stubs / stub).write_text("#!/usr/bin/env bash\nexit 0\n")
        (stubs / stub).chmod(0o755)
    return quiet


def _quiet_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    return _env(PATH=f"{tmp_path / 'stubs'}:{os.environ['PATH']}", **extra)


def test_hc_qw_001_default_is_six_and_hold_slots_covers_it():
    pyslot = (SCRIPTS / "pyslot.sh").read_text(encoding="utf-8")
    hold = (SCRIPTS / "hold_slots.sh").read_text(encoding="utf-8")
    assert 'n="${PYSLOTS:-6}"' in pyslot
    assert "n=${PYSLOTS:-6}; [ \"$n\" -lt 8 ] && n=8" in hold  # slots 1..8 >= 1..6
    for name in ("pyslot.sh", "hold_slots.sh", "quiet_run.sh"):
        assert b"\r" not in (SCRIPTS / name).read_bytes(), f"{name} must stay LF-only"


@_NEEDS
def test_hc_qw_002_six_runs_proceed_and_a_seventh_waits(tmp_path):
    pyslot = _scratch(tmp_path, "pyslot.sh", edits=(("sleep 5", "sleep 1"),))
    running = [
        subprocess.Popen([str(pyslot), "sleep", "5"], env=_env(), stderr=subprocess.DEVNULL)
        for _ in range(6)
    ]
    try:
        _wait_for(
            lambda: all(_probe(tmp_path / f"hc-pytest.{i}.lock") == 75 for i in range(1, 7)),
            4,
            "six runs did not hold six distinct slots at once",
        )
        seventh = subprocess.Popen([str(pyslot), "true"], env=_env(), stderr=subprocess.DEVNULL)
        time.sleep(2)
        assert seventh.poll() is None, "the 7th run started while all 6 slots were busy"
        assert all(p.poll() is None for p in running), "a slot holder ended early"
        assert seventh.wait(timeout=30) == 0, "the 7th run never started after slots freed"
    finally:
        for p in running:
            p.wait(timeout=30)


@_NEEDS
@pytest.mark.skipif(shutil.which("fuser") is None, reason="needs fuser")
def test_hc_qw_003_a_long_wait_prints_one_line_and_keeps_waiting(tmp_path):
    pyslot = _scratch(tmp_path, "pyslot.sh", edits=(("sleep 5", "sleep 1"),))
    slot = tmp_path / "hc-pytest.1.lock"
    holder = subprocess.Popen(["flock", str(slot), "sleep", "6"], stderr=subprocess.DEVNULL)
    try:
        _wait_for(lambda: _probe(slot) == 75, 3, "holder never took the slot")
        t0 = time.monotonic()
        run = subprocess.run(
            [str(pyslot), "true"],
            env=_env(PYSLOTS="1", PYSLOT_WAIT_WARN_MIN="0.03"),  # 1 s
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        holder.wait(timeout=30)
    lines = [ln for ln in run.stderr.splitlines() if ln.startswith("pyslot:")]
    assert run.returncode == 0, (run.returncode, run.stderr)  # it kept waiting, then ran
    assert time.monotonic() - t0 > 3, "did not wait for the slot"
    assert len(lines) == 1, run.stderr
    assert re.search(r"waited \d+ min", lines[0]) and str(holder.pid) in lines[0], lines[0]

    # Default threshold is 20 min: a short wait prints nothing.
    holder = subprocess.Popen(["flock", str(slot), "sleep", "3"], stderr=subprocess.DEVNULL)
    try:
        _wait_for(lambda: _probe(slot) == 75, 3, "holder never took the slot")
        quiet = subprocess.run(
            [str(pyslot), "true"], env=_env(PYSLOTS="1"), capture_output=True, text=True, timeout=60
        )
    finally:
        holder.wait(timeout=30)
    assert quiet.returncode == 0 and quiet.stderr == "", quiet.stderr


@_NEEDS
def test_hc_qw_004_outside_the_window_refuses_without_force(tmp_path):
    quiet = _quiet_scratch(tmp_path)
    marker = tmp_path / "ran"
    run = subprocess.run(
        [str(quiet), "touch", str(marker)],
        env=_quiet_env(tmp_path, QUIET_WINDOW=_window(120, 180)),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run.returncode == 76, (run.returncode, run.stdout, run.stderr)
    assert "outside QUIET_WINDOW" in run.stderr and "QUIET_FORCE=1" in run.stderr
    assert not marker.exists(), "the command ran outside the window"
    assert _probe(tmp_path / "hc-pytest.hold.lock") == 0, "refusal must not take locks"
    # No window set: unchanged behaviour, the command runs.
    ok = subprocess.run(
        [str(quiet), "touch", str(marker)], env=_quiet_env(tmp_path), capture_output=True, timeout=60
    )
    assert ok.returncode == 0 and marker.exists(), ok


@_NEEDS
def test_hc_qw_005_the_forced_daytime_cap_kills_the_child_and_frees_the_locks(tmp_path):
    quiet = _quiet_scratch(tmp_path)
    pid_file = tmp_path / "child.pid"
    t0 = time.monotonic()
    run = subprocess.run(
        [str(quiet), "bash", "-c", f"echo $$ > {pid_file}; exec sleep 60"],
        env=_quiet_env(
            tmp_path, QUIET_WINDOW=_window(120, 180), QUIET_FORCE="1", QUIET_MAX_MIN="0.03"
        ),
        capture_output=True,
        text=True,
        timeout=60,
    )
    elapsed = time.monotonic() - t0
    assert run.returncode == 124, (run.returncode, run.stdout, run.stderr)  # timeout's cap code
    assert "capped at" in run.stdout and elapsed < 30, (elapsed, run.stdout)
    child = int(pid_file.read_text())
    with pytest.raises(OSError):
        os.kill(child, 0)  # the child is dead
    assert _probe(tmp_path / "hc-pytest.hold.lock") == 0
    assert all(_probe(tmp_path / f"hc-pytest.{i}.lock") == 0 for i in range(1, 9))


@_NEEDS
def test_hc_qw_006_inside_the_window_there_is_no_cap(tmp_path):
    quiet = _quiet_scratch(tmp_path)
    run = subprocess.run(
        [str(quiet), "bash", "-c", "sleep 3; echo done"],
        env=_quiet_env(tmp_path, QUIET_WINDOW=_window(-60, 60), QUIET_MAX_MIN="0.03"),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run.returncode == 0 and "done" in run.stdout, (run.returncode, run.stdout, run.stderr)
    assert "capped" not in run.stdout


@_NEEDS
def test_hc_qw_007_a_malformed_window_is_refused(tmp_path):
    quiet = _quiet_scratch(tmp_path)
    run = subprocess.run(
        [str(quiet), "true"],
        env=_quiet_env(tmp_path, QUIET_WINDOW="night"),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run.returncode == 64 and "bad QUIET_WINDOW" in run.stderr, run
