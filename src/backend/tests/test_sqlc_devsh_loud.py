"""dev.sh stops like dev.bat when SQLCipher is missing or fails its file probe (SQLC-DEVSH-LOUD).

Each launcher test runs a copy of dev.sh in a sandbox whose PATH is only tmp_path/bin
(symlinks to the tools dev.sh needs plus a python stub), with HC_DEV_STOP_AFTER_DEPS=1.
The stub fails ``pip install -r`` on a sqlcipher requirement (HC_TEST_PIP_SQLCIPHER_FAIL=1),
fails ``check_sqlcipher.py --file-probe`` (HC_TEST_PROBE_FAIL=1) and records every call.
The child's output goes to files, never pipes (recurring-failures section 21).
"""

import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None, reason="dev.sh is a bash launcher"
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_SH = REPO_ROOT / "dev.sh"
REAL_TOOLS = [
    "bash", "grep", "mktemp", "tail", "rm", "cp", "cat", "dirname", "awk",
    "touch", "mkdir", "chmod", "sed", "sha256sum", "cut", "tr", "head", "uname",
]

BANNER = "Your health data will NOT be encrypted on this computer"
NEVER_UNENCRYPTED = "never stored unencrypted"
OVERRIDE = "HC_ALLOW_UNENCRYPTED=1"

PYTHON_STUB = """#!/bin/bash
# Stub python3 / venv python. Records calls to $HC_TEST_RECORD.
case "$1" in
  --version) echo "Python 3.11.0"; exit 0 ;;
  -c) exit 0 ;;
  */check_sqlcipher.py)
    echo "probe $*" >> "$HC_TEST_RECORD"
    if [ "${HC_TEST_PROBE_FAIL:-}" = "1" ]; then
      echo "FAIL: stub probe says the file is not ciphertext" >&2
      exit 1
    fi
    exit 0 ;;
esac
if [ "$1" = "-m" ] && [ "$2" = "venv" ]; then
  mkdir -p "$3/bin"
  cat "$0" > "$3/bin/python"
  chmod +x "$3/bin/python"
  exit 0
fi
if [ "$1" = "-m" ] && [ "$2" = "pip" ]; then
  shift 2
  echo "pip $*" >> "$HC_TEST_RECORD"
  while [ $# -gt 0 ]; do
    if [ "$1" = "-r" ]; then
      echo "REQ-BEGIN" >> "$HC_TEST_RECORD"
      cat "$2" >> "$HC_TEST_RECORD"
      echo "REQ-END" >> "$HC_TEST_RECORD"
      if [ "${HC_TEST_PIP_SQLCIPHER_FAIL:-}" = "1" ] && grep -qi sqlcipher "$2"; then
        echo "ERROR: Failed building wheel for sqlcipher3-binary"
        exit 1
      fi
    fi
    shift
  done
  exit 0
fi
exit 0
"""


def _stub(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _run_dev_sh(tmp_path: Path, *, pip_fail=False, probe_fail=False, override=False, env_file=None):
    root = tmp_path / "repo"
    (root / "src" / "backend").mkdir(parents=True)
    (root / "config").mkdir()
    # The sandbox copy (never the real file) also records the flag STEP 4 branches on, just before
    # the HC_DEV_STOP_AFTER_DEPS exit, so a test can see it without running the rest of dev.sh.
    text = DEV_SH.read_text(encoding="utf-8")
    anchor = '[ "${HC_DEV_STOP_AFTER_DEPS:-}" != "1" ]'
    assert text.count(anchor) == 1, "dev.sh stop-after-deps line moved"
    text = text.replace(anchor, 'echo "flag SQLCIPHER_AVAILABLE=$SQLCIPHER_AVAILABLE" >> "$HC_TEST_RECORD"\n' + anchor)
    (root / "dev.sh").write_text(text, encoding="utf-8")
    (root / "src" / "backend" / "requirements.txt").write_text("fastapi\nsqlcipher3-binary\n")
    (root / "config" / ".env.example").write_text("LLM_PROVIDER=ollama\n")
    env_path = root / "src" / "backend" / ".env"
    if env_file is not None:
        env_path.write_text(env_file)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in REAL_TOOLS:
        real = shutil.which(tool)
        if real:
            (bin_dir / tool).symlink_to(real)
    _stub(bin_dir / "python3", PYTHON_STUB)
    _stub(bin_dir / "node", '#!/bin/bash\necho "v22.12.0"\n')
    _stub(bin_dir / "npm", '#!/bin/bash\necho "10.0.0"\n')
    _stub(bin_dir / "cc", "#!/bin/bash\nexit 0\n")

    record = tmp_path / "record.txt"
    env = {
        "PATH": str(bin_dir),
        "HOME": str(tmp_path),
        "HC_ALLOW_WINDOWS_MOUNT": "1",
        "HC_DEV_STOP_AFTER_DEPS": "1",
        "HC_TEST_RECORD": str(record),
        "LLM_PROVIDER": "ollama",
    }
    if pip_fail:
        env["HC_TEST_PIP_SQLCIPHER_FAIL"] = "1"
    if probe_fail:
        env["HC_TEST_PROBE_FAIL"] = "1"
    if override:
        env["HC_ALLOW_UNENCRYPTED"] = "1"
    out_file, err_file = tmp_path / "out.txt", tmp_path / "err.txt"
    with out_file.open("w") as out, err_file.open("w") as err:
        proc = subprocess.run(
            [str(bin_dir / "bash"), str(root / "dev.sh")],
            cwd=root, env=env, stdout=out, stderr=err, stdin=subprocess.DEVNULL, timeout=60,
        )
    output = out_file.read_text() + err_file.read_text()
    rec = record.read_text() if record.exists() else ""
    return proc.returncode, output, rec, env_path


def _requirements_installed(record: str) -> list[str]:
    return [b.split("REQ-END")[0] for b in record.split("REQ-BEGIN\n")[1:]]


def _flag(record: str) -> str:
    """The SQLCIPHER_AVAILABLE value dev.sh held when it left the dependency step."""
    flags = [line for line in record.splitlines() if line.startswith("flag SQLCIPHER_AVAILABLE=")]
    assert len(flags) == 1, record
    return flags[0].split("=", 1)[1]


def _probe_calls(record: str) -> list[str]:
    return [line for line in record.splitlines() if line.startswith("probe ")]


def test_hc_sdl_001_pip_sqlcipher_failure_stops_without_override(tmp_path):
    seeded = "DATABASE_ENCRYPTION_REQUIRED=true\nOTHER=1\n"
    rc, output, record, env_path = _run_dev_sh(tmp_path, pip_fail=True, env_file=seeded)
    assert rc != 0, output
    assert OVERRIDE in output, output
    assert NEVER_UNENCRYPTED in output, output
    assert len(_requirements_installed(record)) == 1, "no retry without SQLCipher: " + record
    assert env_path.read_text() == seeded
    assert _probe_calls(record) == [], "no SQLCipher installed, nothing to probe"


def test_hc_sdl_002_pip_sqlcipher_failure_with_override_continues_without_sqlcipher(tmp_path):
    rc, output, record, _ = _run_dev_sh(tmp_path, pip_fail=True, override=True)
    assert rc == 0, output
    reqs = _requirements_installed(record)
    assert len(reqs) == 2, record
    assert "sqlcipher" in reqs[0].lower()
    assert "sqlcipher" not in reqs[1].lower()
    assert "fastapi" in reqs[1]
    assert BANNER in output, output
    assert _probe_calls(record) == []
    assert _flag(record) == "0", "STEP 4 must see SQLCipher as unavailable"


def test_hc_sdl_003_probe_failure_stops_without_override(tmp_path):
    seeded = "DATABASE_ENCRYPTION_REQUIRED=true\n"
    rc, output, record, env_path = _run_dev_sh(tmp_path, probe_fail=True, env_file=seeded)
    assert rc != 0, output
    assert len(_probe_calls(record)) == 1, record
    assert "dev-sqlcipher-probe.log" in output, output
    assert OVERRIDE in output, output
    assert NEVER_UNENCRYPTED in output, output
    assert BANNER not in output
    assert env_path.read_text() == seeded


def test_hc_sdl_004_probe_failure_with_override_continues_with_banner(tmp_path):
    rc, output, record, _ = _run_dev_sh(tmp_path, probe_fail=True, override=True)
    assert rc == 0, output
    assert len(_probe_calls(record)) == 1, record
    assert BANNER in output, output
    assert _flag(record) == "0", "a failed probe must leave SQLCIPHER_AVAILABLE=0 so STEP 4 writes REQUIRED=false"


def test_hc_sdl_005_probe_runs_and_passes_quietly(tmp_path):
    rc, output, record, _ = _run_dev_sh(tmp_path)
    assert rc == 0, output
    probes = _probe_calls(record)
    assert len(probes) == 1 and probes[0].endswith("scripts/check_sqlcipher.py --file-probe"), record
    assert BANNER not in output
    assert NEVER_UNENCRYPTED not in output
    assert len(_requirements_installed(record)) == 1
    assert _flag(record) == "1"


# --- STEP 4: the real .env block ------------------------------------------------


def _block(path: Path, opener: str, closer: str, after: str = "") -> str:
    """Text from the first line starting with ``opener`` (searched after the line starting with ``after``)
    to the first later line that is exactly ``closer``."""
    lines = path.read_text(encoding="utf-8").splitlines()
    first = next((i for i, line in enumerate(lines) if line.startswith(after)), None)
    assert first is not None, f"{path.name} has no line starting with {after!r}"
    start = next((i for i in range(first, len(lines)) if lines[i].startswith(opener)), None)
    assert start is not None, f"{path.name} has no line starting with {opener!r}"
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == closer)
    return "\n".join(lines[start : end + 1])


def _run_step4(tmp_path: Path, *, available: int, env_text: str) -> tuple[str, list[str]]:
    block = _block(DEV_SH, 'if [ "$SQLCIPHER_AVAILABLE" = "1" ]; then', "fi", after="# --- STEP 4")
    helper = _block(DEV_SH, "set_env_key() {", "}")
    env_file = tmp_path / ".env"
    env_file.write_text(env_text)
    calls = tmp_path / "calls.log"
    calls.unlink(missing_ok=True)
    script = (
        "set -euo pipefail\n"
        'ok() { echo "ok:$*" >> "$CALLS"; }\n'
        'warn() { echo "warn:$*" >> "$CALLS"; }\n'
        + helper + "\n"
        + f"SQLCIPHER_AVAILABLE={available}\n"
        + block
        + '\necho DONE >> "$CALLS"\n'
    )
    env = {"PATH": "/usr/bin:/bin", "ENV_FILE": str(env_file), "CALLS": str(calls)}
    done = subprocess.run(
        ["bash", "-c", script], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL, timeout=30,
    )
    assert done.returncode == 0
    lines = calls.read_text().splitlines()
    assert lines and lines[-1] == "DONE", lines
    return env_file.read_text(), lines[:-1]


def test_hc_sdl_006_step4_sets_required_from_the_probe_result(tmp_path):
    # Probe passed: a REQUIRED=false left by an older dev.sh is repaired to true.
    text, calls = _run_step4(tmp_path, available=1, env_text="A=1\nDATABASE_ENCRYPTION_REQUIRED=false\n")
    assert "DATABASE_ENCRYPTION_REQUIRED=true" in text.splitlines(), text
    assert "DATABASE_ENCRYPTION_REQUIRED=false" not in text
    assert any(c.startswith("ok:") and "DATABASE_ENCRYPTION_REQUIRED=true" in c for c in calls), calls

    # Probe passed, already true: stays true, no "Set ..." line.
    text, calls = _run_step4(tmp_path, available=1, env_text="DATABASE_ENCRYPTION_REQUIRED=true\n")
    assert text.splitlines() == ["DATABASE_ENCRYPTION_REQUIRED=true"], text
    assert calls == [], calls

    # Override path only: flips to false and the warning names the override.
    text, calls = _run_step4(tmp_path, available=0, env_text="DATABASE_ENCRYPTION_REQUIRED=true\n")
    assert "DATABASE_ENCRYPTION_REQUIRED=false" in text.splitlines(), text
    assert any(c.startswith("warn:") and OVERRIDE in c for c in calls), calls
