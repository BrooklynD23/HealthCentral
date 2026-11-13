"""HC-TZW: IANA time zones must resolve on Windows, which has no system tz database (WIN-TZDATA)."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
from packaging.markers import Marker
from packaging.requirements import Requirement

BACKEND = Path(__file__).resolve().parents[1]
REQUIREMENTS = BACKEND / "requirements.txt"

# Keys the app resolves: "UTC" (default + fallback in core/time.py), plus
# user-chosen profile zones that go through core.time / streak_engine / badge_evaluator.
APP_KEYS = ["UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Asia/Tokyo"]

_HIDE_TZDATA = """
import importlib.abc, sys, zoneinfo
class _Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name == "tzdata" or name.startswith("tzdata."):
            raise ModuleNotFoundError(name)
sys.meta_path.insert(0, _Block())
zoneinfo.reset_tzpath([])
"""

_USE_TZDATA = """
import zoneinfo
zoneinfo.reset_tzpath([])
"""


def _tzdata_requirement() -> Requirement:
    for raw in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line and Requirement(line).name.lower() == "tzdata":
            return Requirement(line)
    pytest.fail("tzdata is not listed in requirements.txt")


def _run(prelude: str, body: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", prelude + body],
        capture_output=True,
        text=True,
        cwd=BACKEND,
        timeout=60,
    )


def test_hc_tzw_001_tzdata_required_on_windows_only():
    req = _tzdata_requirement()
    assert req.marker is not None, "tzdata must be platform-marked (Linux needs nothing new)"
    assert req.marker.evaluate({"sys_platform": "win32"}) is True
    assert req.marker.evaluate({"sys_platform": "linux"}) is False
    assert req.marker.evaluate({"sys_platform": "darwin"}) is False
    assert Marker('sys_platform == "win32"')  # sanity: marker syntax parses


def test_hc_tzw_002a_utc_fails_without_system_db_or_tzdata():
    """Proves the Windows failure mode: no tz database anywhere -> UTC is not found."""
    result = _run(_HIDE_TZDATA, "from zoneinfo import ZoneInfo\nZoneInfo('UTC')\n")
    assert result.returncode != 0
    assert "No time zone found with key UTC" in result.stderr


@pytest.mark.skipif(
    importlib.util.find_spec("tzdata") is None,
    reason="tzdata not installed in this venv; install requirements.txt on win32 or pip install tzdata",
)
def test_hc_tzw_002b_app_keys_resolve_with_tzdata_only():
    body = (
        "from zoneinfo import ZoneInfo\n"
        "from core.time import safe_zone_name\n"
        f"keys = {APP_KEYS!r}\n"
        "for k in keys:\n"
        "    ZoneInfo(k)\n"
        "    assert safe_zone_name(k) == k, k\n"
        "print('OK')\n"
    )
    result = _run(_USE_TZDATA, body)
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
