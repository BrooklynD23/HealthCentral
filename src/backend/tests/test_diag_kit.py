"""HC-DIAGKIT-001: the diagnosis kit scripts compile and run on an empty directory."""
import py_compile
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[3] / "scripts" / "diag-kit"


def test_hc_diagkit_001_scripts_compile_and_run_empty(tmp_path):
    for name in ("gap_attrib.py", "tick_delay.py"):
        py_compile.compile(str(KIT / name), cfile=str(tmp_path / (name + "c")), doraise=True)
    tick = subprocess.run([sys.executable, str(KIT / "tick_delay.py"), str(tmp_path)], capture_output=True, text=True, timeout=60)
    assert tick.returncode == 0, tick.stderr
    assert tick.stdout.startswith("run cpu gap_ms")
    gap = subprocess.run([sys.executable, str(KIT / "gap_attrib.py"), str(tmp_path)], capture_output=True, text=True, timeout=60)
    assert gap.returncode == 0, gap.stderr
    assert "SUMMARY" in gap.stdout
