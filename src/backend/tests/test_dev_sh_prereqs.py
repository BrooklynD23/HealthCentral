"""dev.sh launcher: compiler / LLM_PROVIDER prerequisites (DEV-SH-CC).

Each test runs a copy of dev.sh in a sandbox whose PATH is only tmp_path/bin
(symlinks to the tools dev.sh needs plus stubs), so the host's cc/gcc never
leak in. HC_DEV_STOP_AFTER_DEPS=1 stops the script after the pip step.
"""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="dev.sh is a bash launcher")

REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_TOOLS = [
    "bash", "grep", "mktemp", "tail", "rm", "cp", "cat", "dirname", "awk",
    "touch", "mkdir", "chmod", "sed", "sha256sum", "cut", "tr", "head", "uname",
]

PYTHON_STUB = """#!/bin/bash
# Stub python3 / venv python. Records `-m pip` calls to $HC_TEST_RECORD.
case "$1" in
  --version) echo "Python 3.11.0"; exit 0 ;;
  -c) exit 0 ;;
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


def _run_dev_sh(tmp_path: Path, *, compiler: bool, provider_env=None, env_file=None):
    root = tmp_path / "repo"
    (root / "src" / "backend").mkdir(parents=True)
    (root / "config").mkdir()
    shutil.copy(REPO_ROOT / "dev.sh", root / "dev.sh")
    (root / "src" / "backend" / "requirements.txt").write_text(
        "fastapi\nllama-cpp-python==0.3.35\n"
    )
    (root / "config" / ".env.example").write_text("LLM_PROVIDER=llama_cpp\n")
    if env_file is not None:
        (root / "src" / "backend" / ".env").write_text(env_file)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in REAL_TOOLS:
        real = shutil.which(tool)
        if real:
            (bin_dir / tool).symlink_to(real)
    _stub(bin_dir / "python3", PYTHON_STUB)
    _stub(bin_dir / "node", '#!/bin/bash\necho "v22.12.0"\n')
    _stub(bin_dir / "npm", '#!/bin/bash\necho "10.0.0"\n')
    if compiler:
        _stub(bin_dir / "cc", "#!/bin/bash\nexit 0\n")

    record = tmp_path / "pip-record.txt"
    env = {
        "PATH": str(bin_dir),
        "HOME": str(tmp_path),
        "HC_ALLOW_WINDOWS_MOUNT": "1",
        "HC_DEV_STOP_AFTER_DEPS": "1",
        "HC_TEST_RECORD": str(record),
    }
    if provider_env is not None:
        env["LLM_PROVIDER"] = provider_env
    proc = subprocess.run(
        [str(bin_dir / "bash"), str(root / "dev.sh")],
        cwd=root, env=env, capture_output=True, text=True, timeout=60,
    )
    return proc, (record.read_text() if record.exists() else "")


def _requirements_installed(record: str) -> list[str]:
    blocks = record.split("REQ-BEGIN\n")[1:]
    return [b.split("REQ-END")[0] for b in blocks]


def test_hc_devsh_001_no_compiler_ollama_skips_llama_cpp(tmp_path):
    proc, record = _run_dev_sh(tmp_path, compiler=False, provider_env="ollama")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    reqs = _requirements_installed(record)
    assert reqs, record
    assert all("llama-cpp-python" not in r for r in reqs)
    assert "fastapi" in reqs[0]
    assert "llama-cpp-python skipped: no C compiler" in proc.stderr


def test_hc_devsh_002_no_compiler_llama_cpp_dies_before_pip(tmp_path):
    proc, record = _run_dev_sh(tmp_path, compiler=False, provider_env="llama_cpp")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert record == ""
    assert "build-essential" in proc.stderr
    assert "LLM_PROVIDER=ollama" in proc.stderr


def test_hc_devsh_003_compiler_present_installs_full_requirements(tmp_path):
    proc, record = _run_dev_sh(tmp_path, compiler=True, provider_env="ollama")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    reqs = _requirements_installed(record)
    assert reqs and "llama-cpp-python==0.3.35" in reqs[0]
    assert "fastapi" in reqs[0]


def test_hc_devsh_004_provider_read_from_backend_env_file(tmp_path):
    proc, record = _run_dev_sh(
        tmp_path, compiler=False, provider_env=None, env_file="LLM_PROVIDER=ollama\n"
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    reqs = _requirements_installed(record)
    assert reqs and all("llama-cpp-python" not in r for r in reqs)
    assert "llama-cpp-python skipped: no C compiler" in proc.stderr
