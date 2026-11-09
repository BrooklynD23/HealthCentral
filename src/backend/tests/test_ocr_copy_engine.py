"""OCR-COPY-ENGINE: patient-facing copy for the bundled RapidOCR engine.

HC-OCE-005  environment diagnostics: Tesseract is the fallback (label, missing
            detail by engine state, Poppler detail) — plan rows 10-11
HC-OCE-006  PATCH /api/v1/settings/model/ocr OpenAPI description — plan row 9
HC-OCE-007  dev.sh step 3b prints the missing-tools lines through `status` — rows 13-14
HC-OCE-008  config/.env.example OCR comment names the bundled reader — row 12

Every string is asserted verbatim against the owner-approved rows in
docs/plans/2026-11-07-three-rows-plan.md (OCR-COPY-TEXT: "Approved strings +
table fills gaps"; OCR-BLOCKER-CODE keeps the `tesseract_missing` API value;
dev.ps1 is out of scope per OCR-DEVPS1-SCOPE).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app  # noqa: E402
from modules.environment_diagnostics import build_environment_diagnostics  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parents[1]

_DEV_SH = REPO_ROOT / "dev.sh"
_ENV_EXAMPLE = REPO_ROOT / "config" / ".env.example"

# Plan row 10: the approved diagnostics strings.
_TESSERACT_LABEL = "Tesseract OCR (fallback)"
_MISSING_ENGINE_OK = (
    "Not installed. Not needed: the bundled OCR reader handles scans and images; "
    "Tesseract is only a fallback."
)
_MISSING_ENGINE_ERR = (
    "Not on PATH, and the built-in OCR reader did not load. "
    "One of the two is needed to read scans and images."
)
# Plan row 11.
_POPPLER_DETAIL = (
    "Not on PATH. Only the Tesseract fallback needs it; "
    "the bundled OCR reader renders PDF pages itself."
)
# Plan row 9.
_OCR_ROUTE_DESCRIPTION = (
    "Per-profile toggle for scanned PDF and image OCR "
    "(subject to server config and an OCR engine)."
)
# Plan rows 13-14.
_TESSERACT_STATUS_LINE = (
    "Tesseract not found (optional fallback; the bundled OCR reader is used first). "
    "To add it: sudo apt install tesseract-ocr  (macOS: brew install tesseract)"
)
_POPPLER_STATUS_LINE = (
    "pdftoppm not found (optional: only the Tesseract fallback needs it). "
    "Install: sudo apt install poppler-utils  (macOS: brew install poppler)"
)
# Plan row 12.
_ENV_LINES = (
    "# OCR enabled (Phase 1+). The bundled OCR reader is detected automatically; dev.ps1/dev.sh",
    "# set this flag. Tesseract on PATH is an optional fallback (on Windows dev.ps1 can install it",
    "# and Poppler). Set HC_SKIP_OCR_SETUP=1 to skip.",
)

# The Tesseract fix commands today, unchanged in the engine-absent state.
_INSTALL_ACTIONS = [
    {"action_type": "copy_command", "label": "Windows (winget)",
     "command": "winget install --id UB-Mannheim.TesseractOCR", "url": None},
    {"action_type": "copy_command", "label": "macOS (Homebrew)",
     "command": "brew install tesseract", "url": None},
    {"action_type": "copy_command", "label": "Debian/Ubuntu",
     "command": "sudo apt install tesseract-ocr", "url": None},
]


def _diagnostics(which_map: dict[str, str | None], rapidocr_installed: bool) -> dict[str, dict]:
    """The component dicts keyed by id, with PATH and the bundled engine stubbed."""
    with patch(
        "modules.environment_diagnostics.shutil.which",
        side_effect=lambda name: which_map.get(name),
    ), patch(
        "modules.environment_diagnostics._rapidocr_installed",
        return_value=rapidocr_installed,
    ):
        return {c["id"]: c for c in build_environment_diagnostics()}


def test_hc_oce_005_tesseract_is_the_fallback_component():
    # Tesseract missing, bundled engine present: an ok row with no fix actions.
    comps = _diagnostics({"pdftoppm": "/usr/bin/pdftoppm"}, rapidocr_installed=True)
    tess = comps["tesseract"]
    assert tess["id"] == "tesseract"
    assert tess["label"] == _TESSERACT_LABEL
    assert tess["status"] == "ok"
    assert tess["detail"] == _MISSING_ENGINE_OK
    assert tess["fix_actions"] == []

    # Tesseract missing, bundled engine absent: an error row, install hints unchanged.
    comps = _diagnostics({"pdftoppm": "/usr/bin/pdftoppm"}, rapidocr_installed=False)
    tess = comps["tesseract"]
    assert tess["id"] == "tesseract"
    assert tess["label"] == _TESSERACT_LABEL
    assert tess["status"] == "error"
    assert tess["detail"] == _MISSING_ENGINE_ERR
    assert tess["fix_actions"] == _INSTALL_ACTIONS

    # Tesseract found: the state is unchanged apart from the label.
    comps = _diagnostics({"tesseract": "/usr/bin/tesseract"}, rapidocr_installed=True)
    tess = comps["tesseract"]
    assert tess["id"] == "tesseract"
    assert tess["label"] == _TESSERACT_LABEL
    assert tess["status"] == "ok"
    assert tess["detail"] == "Found at /usr/bin/tesseract"
    assert tess["fix_actions"] == []

    # Plan row 11: Poppler's detail, still a warn.
    comps = _diagnostics({"tesseract": "/usr/bin/tesseract"}, rapidocr_installed=True)
    poppler = comps["poppler"]
    assert poppler["status"] == "warn"
    assert poppler["detail"] == _POPPLER_DETAIL


def test_hc_oce_006_ocr_route_description_names_an_engine_not_tesseract():
    paths = app.openapi()["paths"]
    desc = paths["/api/v1/settings/model/ocr"]["patch"]["description"]
    assert desc == _OCR_ROUTE_DESCRIPTION


def _block(path: Path, opener: str, closer: str) -> str:
    """The text from the first line starting with ``opener`` to the first line that is exactly ``closer``."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(opener))
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == closer)
    return "\n".join(lines[start : end + 1])


@pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None, reason="needs bash")
def test_hc_oce_007_dev_sh_reports_missing_ocr_tools_as_status(tmp_path):
    """dev.sh step 3b runs for real under bash, with stubbed status/ok/warn and no OCR tools on PATH."""
    block = _block(_DEV_SH, 'if [ "${HC_SKIP_OCR_SETUP:-}" = "1" ]; then', "fi")
    calls = tmp_path / "calls.log"
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    script = (
        "set -euo pipefail\n"
        'status() { echo "status:$*" >> "$CALLS"; }\n'
        'ok() { echo "ok:$*" >> "$CALLS"; }\n'
        'warn() { echo "warn:$*" >> "$CALLS"; }\n'
        + block
        + '\necho DONE >> "$CALLS"\n'
    )
    env = {k: v for k, v in os.environ.items() if k != "HC_SKIP_OCR_SETUP"} | {
        "CALLS": str(calls),
        # An empty PATH dir: command -v finds neither tesseract nor pdftoppm.
        "PATH": str(stub_bin),
    }
    done = subprocess.run(
        [shutil.which("bash"), "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert done.returncode == 0, (done.stdout, done.stderr)
    lines = calls.read_text().splitlines()
    assert lines and lines[-1] == "DONE", lines
    got = lines[:-1]
    assert f"status:{_TESSERACT_STATUS_LINE}" in got, got
    assert f"status:{_POPPLER_STATUS_LINE}" in got, got
    assert not [c for c in got if c.startswith("warn:")], got


def test_hc_oce_008_env_example_names_the_bundled_reader():
    text = _ENV_EXAMPLE.read_text(encoding="utf-8")
    for line in _ENV_LINES:
        assert line in text.splitlines(), line
    assert "sets this from PATH detection" not in text
