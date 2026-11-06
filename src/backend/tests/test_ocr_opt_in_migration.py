"""HC-OOM-001..004 -- OCR-OPT-IN-MIGRATION: profiles saved with OCR on are switched off.

``006_ocr_preference`` added ``ocr_preference_enabled`` with a server default of
1, and the model has defaulted to False since OCR-DEFAULT-ON (#498). A settings
row written before that, by a tier save, a voice toggle or hardware detection,
still holds 1. Migration ``018_ocr_opt_in`` sets every such row to 0; the patient
opts in again in Settings.

Every vault here is a real file vault walked up through Alembic, not an in-memory
``create_all`` engine, because the point is what the migration does to a vault
written by an older revision.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from alembic import command
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.documents import router as documents_router  # noqa: E402
from api.model_settings import router as model_settings_router  # noqa: E402
from core import migrations  # noqa: E402
from core.config import settings  # noqa: E402
from tests.support.migrations import PROFILE_HEAD  # noqa: E402
from tests.support.routes import route_client  # noqa: E402
from tests.test_fk_enforcement import _pragma_on_vault_engine  # noqa: E402
from tests.test_fk_migration_017 import (  # noqa: E402
    KEY,
    _alembic_cfg,
    _connect,
    _insert,
    _rev,
    _unversioned,
)
from tests.test_ocr_rapid import (  # noqa: E402
    _column_page,
    _CommitTrackingMasterDb,
    _engine_present,
    _image_only_pdf,
    _stub_vault,
)

REV_017 = "017_fk_cascade_alignment"
PROFILE = "profile-a"


def _vault_at_017(tmp_path: Path, monkeypatch, *, ocr: int = 1) -> Path:
    """A file vault at 017 holding one settings row saved with OCR ``ocr``."""
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "vault.db"
    command.upgrade(_alembic_cfg(path), REV_017)
    conn = _connect(path)
    try:
        _insert(conn, "user_model_settings", id="S1", profile_id=PROFILE, ocr_preference_enabled=ocr)
        conn.commit()
    finally:
        conn.close()
    return path


def _ocr_values(path: Path) -> list[int]:
    conn = _connect(path)
    try:
        return [r[0] for r in conn.execute("SELECT ocr_preference_enabled FROM user_model_settings ORDER BY id")]
    finally:
        conn.close()


def test_hc_oom_001_a_vault_at_017_with_ocr_on_reads_off_after_the_upgrade(tmp_path, monkeypatch):
    path = _vault_at_017(tmp_path, monkeypatch)
    assert _ocr_values(path) == [1], "the seed must hold the old default"

    migrations.run_profile_migration(path, KEY)

    assert _rev(path) == PROFILE_HEAD
    assert _ocr_values(path) == [0]


def test_hc_oom_002_an_unversioned_vault_with_the_017_schema_and_ocr_on_reads_off_after_open(
    tmp_path, monkeypatch
):
    """The matcher must not stamp such a vault at the data-only revision: the UPDATE would never run."""
    path = _vault_at_017(tmp_path, monkeypatch)
    _unversioned(path)

    migrations.run_profile_migration(path, KEY)

    assert _rev(path) == PROFILE_HEAD
    assert _ocr_values(path) == [0]
