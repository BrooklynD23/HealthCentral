"""Guards for ``scripts/pyslot.sh``'s flock contract (HC-PSG-001…005).

#490 (``431fbf52``) added ``-o`` (util-linux ``--close``) to the flock call at
``scripts/pyslot.sh:9``: without it, a command that leaves a background child
behind leaks the slot lock through the inherited fd (a leftover vite server
held slot 2 for ~4 h). That fix's acceptance was a pasted two-line test, so
nothing committed guarded it — a later edit that drops ``-o`` fails nothing.

- HC-PSG-001 (static): the script's one slot ``flock`` invocation (lock
  ``hc-pytest.$i.lock``) carries standalone ``-o``, ``-n`` and ``-E 75``.
- HC-PSG-002 (self-proving pair): a verbatim scratch copy frees the slot after
  a command that leaves an orphaned child (probe 0); a copy the test itself
  de-``-o``s leaks it (probe 75 — the built-in RED proof).
- HC-PSG-003 (anti-vacuous): the slot lock is genuinely held while the command
  runs and released after.
- HC-PSG-004: non-75 command exits pass through; a busy slot retries on 75.
- HC-PSG-005: the script bytes stay LF-only.

Every functional case runs a *copy* of the real script inside ``tmp_path`` with
its ``/tmp/claude-1000`` lock dir rewritten to the scratch dir, so the box's
real pytest slots and the real script are never touched.
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
PYSLOT_SH = REPO_ROOT / "scripts" / "pyslot.sh"

_NEEDS_BASH_FLOCK = pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None or shutil.which("flock") is None,
    reason="needs bash+flock",
)


def _flock_invocations(text: str) -> list[list[str]]:
    """Tokenized ``flock`` invocations in the script (first token ``flock``)."""
    return [
        tokens
        for line in text.splitlines()
        for tokens in [line.split()]
        if tokens and tokens[0] == "flock"
    ]


def _scratch(tmp_path: Path, name: str, *, edits: tuple[tuple[str, str], ...] = ()) -> Path:
    """Copy ``scripts/pyslot.sh`` into ``tmp_path`` with the lock dir moved there."""
    text = PYSLOT_SH.read_text(encoding="utf-8")
    assert "/tmp/claude-1000" in text, "script no longer locks under /tmp/claude-1000"
    text = text.replace("/tmp/claude-1000", str(tmp_path))
    for old, new in edits:
        edited = text.replace(old, new, 1)
        assert edited != text, f"edit did not apply: {old!r}"
        text = edited
    copy = tmp_path / name
    copy.write_text(text, encoding="utf-8")
    copy.chmod(0o755)
    return copy


def _env() -> dict[str, str]:
    """The script's own environment: single slot so the lock name is deterministic."""
    return {**os.environ, "PYSLOTS": "1"}


def _probe(lock: Path) -> int:
    """``flock -n -E 75 <lock> true``: 0 when free, 75 when held."""
    return subprocess.run(
        ["flock", "-n", "-E", "75", str(lock), "true"],
        capture_output=True,
        timeout=10,
    ).returncode


def test_hc_psg_001_flock_invocation_pins_close_nonblocking_and_exit75_flags():
    """Static pin: tokenized flags, not a substring — flag order may change."""
    invocations = _flock_invocations(PYSLOT_SH.read_text(encoding="utf-8"))
    # Exactly one *slot* flock (HOLD-SLOTS-IN-REPO added a separate hold-lock probe).
    slot = [t for t in invocations if any("hc-pytest.$i.lock" in tok for tok in t)]
    assert len(slot) == 1, invocations
    tokens = slot[0]
    assert "-o" in tokens, tokens  # --close: spawned children must not inherit the slot fd
    assert "-n" in tokens, tokens  # --nonblock: busy slot -> 75, the outer loop retries
    assert "-E" in tokens and tokens[tokens.index("-E") + 1] == "75", tokens


@_NEEDS_BASH_FLOCK
def test_hc_psg_002_orphaned_child_releases_the_slot_only_with_close_flag(tmp_path):
    """Verbatim copy -> probe 0; the test's own de-``-o`` copy -> probe 75 (RED proof)."""
    good = _scratch(tmp_path, "pyslot-good.sh")
    bad = _scratch(tmp_path, "pyslot-bad.sh", edits=(("flock -o -n", "flock -n"),))
    bad_tokens = _flock_invocations(bad.read_text(encoding="utf-8"))[0]
    assert "-o" not in bad_tokens, bad_tokens  # the test produced the regressed script

    lock = tmp_path / "hc-pytest.1.lock"
    pid_file = tmp_path / "child.pid"
    pids: list[int] = []
    probes: dict[str, int] = {}
    try:
        for name, copy in (("good", good), ("bad", bad)):
            # The orphan's std fds are /dev/null'd (as in the batch's recorded
            # acceptance): with pipes it would hold them open for 30 s and
            # subprocess.run would hang on EOF long after the script exits.
            run = subprocess.run(
                [str(copy), "bash", "-c", "sleep 30 >/dev/null 2>&1 & echo $! > child.pid; exit 0"],
                env=_env(),
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert run.returncode == 0, (name, run.returncode, run.stdout, run.stderr)
            pids.append(int(pid_file.read_text().strip()))
            pid_file.unlink()
            probes[name] = _probe(lock)
    finally:
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    print(
        f"HC-PSG-002 probes: good={probes.get('good')} bad={probes.get('bad')} "
        "(the bad-copy 75 is this guard's RED proof)"
    )
    assert probes["good"] == 0, probes
    assert probes["bad"] == 75, probes


@_NEEDS_BASH_FLOCK
def test_hc_psg_003_the_lock_is_held_while_the_command_runs(tmp_path):
    """Anti-vacuous: a script that stopped locking would pass HC-PSG-002 trivially."""
    copy = _scratch(tmp_path, "pyslot.sh")
    lock = tmp_path / "hc-pytest.1.lock"
    proc = subprocess.Popen(
        [str(copy), "sleep", "4"],
        env=_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        held = None
        deadline = time.monotonic() + 3.5
        while proc.poll() is None and time.monotonic() < deadline:
            if _probe(lock) == 75:
                held = 75
                break
            time.sleep(0.05)
        assert held == 75, "the slot lock must be held while the command runs"
        assert proc.poll() is None, "command ended before the held-lock probe"
    finally:
        proc.wait(timeout=15)
    assert proc.returncode == 0, proc.returncode
    assert _probe(lock) == 0, "the slot lock must be released once the command exits"


@_NEEDS_BASH_FLOCK
def test_hc_psg_004_non75_exit_passes_through_and_a_busy_slot_retries(tmp_path):
    """The scratch copy shortens ``sleep 5`` -> ``sleep 1`` to keep the retry fast;
    the retry *interval* is not the pinned property — the 75-loop mechanism is."""
    copy = _scratch(tmp_path, "pyslot.sh", edits=(("sleep 5", "sleep 1"),))
    lock = tmp_path / "hc-pytest.1.lock"
    env = _env()

    ok = subprocess.run([str(copy), "true"], env=env, capture_output=True, timeout=30)
    assert ok.returncode == 0, (ok.returncode, ok.stdout, ok.stderr)
    fails = subprocess.run([str(copy), "false"], env=env, capture_output=True, timeout=30)
    assert fails.returncode == 1, (fails.returncode, fails.stdout, fails.stderr)

    holder = subprocess.Popen(
        ["flock", str(lock), "sleep", "2"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 2
        while _probe(lock) != 75:
            assert time.monotonic() < deadline, "the holder never took the scratch lock"
            time.sleep(0.05)
        started = time.monotonic()
        run = subprocess.run(
            [str(copy), "bash", "-c", "exit 3"],
            env=env,
            capture_output=True,
            timeout=30,
        )
        elapsed = time.monotonic() - started
    finally:
        holder.wait(timeout=15)
    # First pass probes 75 (slot held), the loop retries, then the command's own
    # exit code passes through — 3, not 75 and not 0.
    assert run.returncode == 3, (run.returncode, run.stdout, run.stderr)
    assert elapsed >= 0.5, f"a busy slot must cost at least one 75-pass + retry ({elapsed:.3f}s)"


def test_hc_psg_005_the_script_stays_lf_only():
    """A CRLF conversion breaks the shebang/flags on Linux — fails anywhere."""
    data = PYSLOT_SH.read_bytes()
    assert b"\r" not in data, "scripts/pyslot.sh must keep LF endings"
