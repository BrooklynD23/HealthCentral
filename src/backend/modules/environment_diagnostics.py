"""
Runtime diagnostics for local tools (OCR stack, models, SQLCipher, GPU).

Used by Settings "Environment & tools" for actionable status and fix hints.
"""

from __future__ import annotations

import shutil
import sys
from typing import Any, Literal

from core.config import settings
from core.sqlcipher_driver import is_sqlcipher_available
from modules.hardware_detection import detect_hardware
from modules.model_selector import get_model_selector


DiagnosticStatus = Literal["ok", "warn", "error"]


def _action(
    *,
    action_type: str,
    label: str,
    command: str | None = None,
    url: str | None = None,
) -> dict[str, str | None]:
    return {"action_type": action_type, "label": label, "command": command, "url": url}


def build_environment_diagnostics() -> list[dict[str, Any]]:
    """Return stable-ordered diagnostic components for the API."""
    components: list[dict[str, Any]] = []

    # --- Tesseract ---
    tess = shutil.which("tesseract")
    if tess:
        components.append(
            {
                "id": "tesseract",
                "label": "Tesseract OCR",
                "status": "ok",
                "detail": f"Found at {tess}",
                "fix_actions": [],
            }
        )
    else:
        components.append(
            {
                "id": "tesseract",
                "label": "Tesseract OCR",
                "status": "error",
                "detail": "Not on PATH — required for OCR of scans and images.",
                "fix_actions": [
                    _action(
                        action_type="copy_command",
                        label="Windows (winget)",
                        command='winget install --id UB-Mannheim.TesseractOCR',
                    ),
                    _action(
                        action_type="copy_command",
                        label="macOS (Homebrew)",
                        command="brew install tesseract",
                    ),
                    _action(
                        action_type="copy_command",
                        label="Debian/Ubuntu",
                        command="sudo apt install tesseract-ocr",
                    ),
                ],
            }
        )

    # --- Python OCR stack ---
    ocr_import_detail_parts: list[str] = []
    ocr_ok = True
    for mod in ("PIL", "pytesseract", "pdf2image"):
        try:
            if mod == "PIL":
                import PIL  # noqa: F401
            elif mod == "pytesseract":
                import pytesseract  # noqa: F401
            else:
                import pdf2image  # noqa: F401
            ocr_import_detail_parts.append(f"{mod}: OK")
        except ImportError:
            ocr_ok = False
            ocr_import_detail_parts.append(f"{mod}: missing")

    components.append(
        {
            "id": "ocr_python",
            "label": "OCR Python libraries",
            "status": "ok" if ocr_ok else "error",
            "detail": "; ".join(ocr_import_detail_parts),
            "fix_actions": []
            if ocr_ok
            else [
                _action(
                    action_type="copy_command",
                    label="Install backend deps",
                    command="pip install pillow pytesseract pdf2image",
                ),
            ],
        }
    )

    # --- Poppler (pdf2image / scanned PDF) ---
    poppler = shutil.which("pdftoppm") or shutil.which("pdftocairo")
    if poppler:
        components.append(
            {
                "id": "poppler",
                "label": "Poppler (pdftoppm)",
                "status": "ok",
                "detail": f"Found at {poppler}",
                "fix_actions": [],
            }
        )
    else:
        components.append(
            {
                "id": "poppler",
                "label": "Poppler (pdftoppm)",
                "status": "warn",
                "detail": "Not on PATH — scanned PDF → image conversion may fail on some systems.",
                "fix_actions": [
                    _action(
                        action_type="copy_command",
                        label="Windows (Chocolatey)",
                        command="choco install poppler",
                    ),
                    _action(
                        action_type="copy_command",
                        label="macOS (Homebrew)",
                        command="brew install poppler",
                    ),
                    _action(
                        action_type="copy_command",
                        label="Debian/Ubuntu",
                        command="sudo apt install poppler-utils",
                    ),
                ],
            }
        )

    # --- SQLCipher ---
    if is_sqlcipher_available():
        components.append(
            {
                "id": "sqlcipher",
                "label": "SQLCipher (profile DB)",
                "status": "ok",
                "detail": "sqlcipher3 driver available.",
                "fix_actions": [],
            }
        )
    else:
        req = settings.database_encryption_required
        is_windows = sys.platform == "win32"
        detail = "sqlcipher3 not available."
        if is_windows:
            detail += (
                " PyPI publishes Linux wheels only for sqlcipher3-binary, so pip usually cannot "
                "install it on Windows; the backend falls back to plain SQLite."
            )
        if req:
            detail += " Encryption is required in this configuration."
        sqlcipher_fixes: list[dict[str, str | None]] = []
        if is_windows:
            sqlcipher_fixes = [
                _action(
                    action_type="copy_command",
                    label="Local dev only (plain SQLite vaults)",
                    command=(
                        "# In .env — development only; do not use in production:\n"
                        "DATABASE_ENCRYPTION_REQUIRED=false"
                    ),
                ),
                _action(
                    action_type="copy_command",
                    label="SQLCipher: run API on Linux or WSL",
                    command=(
                        "# On Linux/WSL in your venv:\n"
                        "pip install sqlcipher3-binary"
                    ),
                ),
            ]
        else:
            sqlcipher_fixes = [
                _action(
                    action_type="copy_command",
                    label="Install wheel",
                    command="pip install sqlcipher3-binary",
                ),
                _action(
                    action_type="copy_command",
                    label="Debian/Ubuntu (before pip if build fails)",
                    command="sudo apt-get install libsqlcipher-dev",
                ),
                _action(
                    action_type="copy_command",
                    label="macOS (before pip if needed)",
                    command="brew install sqlcipher",
                ),
            ]
        components.append(
            {
                "id": "sqlcipher",
                "label": "SQLCipher (profile DB)",
                "status": "error" if req else "warn",
                "detail": detail,
                "fix_actions": sqlcipher_fixes,
            }
        )

    # --- Chat model (active tier) ---
    selector = get_model_selector()
    try:
        hw_path = str(selector.models_path.resolve())
    except Exception:
        hw_path = str(selector.models_path)
    hardware = detect_hardware(hw_path)

    chat_ok_any = False
    tier_detail_parts: list[str] = []
    for tier in ("low", "mid", "high"):
        if selector.is_model_available(tier):
            chat_ok_any = True
            p = selector.get_model_path(tier)
            tier_detail_parts.append(f"{tier}: {p.name if p else tier}")
    if chat_ok_any:
        components.append(
            {
                "id": "chat_model",
                "label": "Local chat model (GGUF)",
                "status": "ok",
                "detail": "At least one tier downloaded: " + "; ".join(tier_detail_parts[:3]),
                "fix_actions": [
                    _action(
                        action_type="open_url",
                        label="Open Settings",
                        url="/settings",
                    ),
                ],
            }
        )
    else:
        components.append(
            {
                "id": "chat_model",
                "label": "Local chat model (GGUF)",
                "status": "warn",
                "detail": "No GGUF model found under models path — assistant uses template fallback.",
                "fix_actions": [
                    _action(
                        action_type="rerun_detection",
                        label="Re-check after download",
                        command=None,
                    ),
                ],
            }
        )

    # --- Embeddings ---
    try:
        import sentence_transformers  # noqa: F401

        emb_status: DiagnosticStatus = "ok"
        emb_detail = "sentence-transformers importable."
    except ImportError:
        emb_status = "warn"
        emb_detail = "sentence-transformers not installed — RAG may use hash fallback embeddings."

    components.append(
        {
            "id": "embeddings",
            "label": "Embeddings (sentence-transformers)",
            "status": emb_status,
            "detail": emb_detail,
            "fix_actions": []
            if emb_status == "ok"
            else [
                _action(
                    action_type="copy_command",
                    label="pip install",
                    command="pip install sentence-transformers",
                ),
            ],
        }
    )

    # --- GPU ---
    if hardware.gpu_available and hardware.gpu_name:
        components.append(
            {
                "id": "gpu",
                "label": "GPU",
                "status": "ok",
                "detail": f"{hardware.gpu_name} ({hardware.gpu_vram_gb or 0:.1f} GB VRAM)",
                "fix_actions": [],
            }
        )
    else:
        components.append(
            {
                "id": "gpu",
                "label": "GPU",
                "status": "warn",
                "detail": "No usable GPU detected — inference runs on CPU.",
                "fix_actions": [],
            }
        )

    return components

