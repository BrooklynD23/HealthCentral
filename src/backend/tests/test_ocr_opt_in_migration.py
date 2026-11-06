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


# ---------------------------------------------------------------------------
# HTTP: what the patient sees (I-9: route_client with a real migrated vault)
# ---------------------------------------------------------------------------


def _scan_pdf() -> dict:
    return {"file": ("scan.pdf", _image_only_pdf(_column_page()), "application/pdf")}


def _client_for(vault: Path, engine, monkeypatch, tmp_path):
    """One HTTP client for the documents and settings routes over the vault at ``vault``."""
    _stub_vault(monkeypatch, tmp_path)
    router = APIRouter()
    router.include_router(documents_router, prefix="/documents")
    router.include_router(model_settings_router, prefix="/settings/model")
    return route_client(
        router,
        "",
        profile_id=PROFILE,
        master_db=_CommitTrackingMasterDb(),
        profile_db=async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )


@pytest.mark.asyncio
async def test_hc_oom_003_a_profile_saved_with_ocr_on_is_off_waits_on_the_scan_and_can_opt_in(
    tmp_path, monkeypatch
):
    path = _vault_at_017(tmp_path, monkeypatch)
    migrations.run_profile_migration(path, KEY)
    reads = _engine_present(monkeypatch)
    engine = _pragma_on_vault_engine(path)
    try:
        with _client_for(path, engine, monkeypatch, tmp_path) as client:
            current = client.get("/settings/model")
            assert current.status_code == 200, current.text
            assert current.json()["ocr_preference_enabled"] is False, current.json()
            assert current.json()["ocr_effective"] is False, current.json()
            assert "user_disabled" in current.json()["ocr_blockers"], current.json()

            imported = client.post("/documents/import", files=_scan_pdf())
            assert imported.status_code == 201, imported.text
            assert imported.json()["document"]["status"] == "pending_ocr", imported.json()["document"]
            assert imported.json()["observations_extracted"] == 0
            assert reads == [], "OCR is off after the upgrade: no page may reach the OCR reader"
            doc_id = imported.json()["document"]["id"]

            opted = client.patch("/settings/model/ocr", json={"ocr_preference_enabled": True})
            assert opted.status_code == 200, opted.text
            assert opted.json()["ocr_preference_enabled"] is True, opted.json()
            assert opted.json()["ocr_effective"] is True, opted.json()

            reprocessed = client.post(f"/documents/{doc_id}/reprocess")
            assert reprocessed.status_code == 200, reprocessed.text
            assert reprocessed.json()["document"]["status"] == "parsed", reprocessed.json()["document"]
            assert reads, "the patient opted in again: the waiting scan must now be read"
    finally:
        await engine.dispose()
    assert _ocr_values(path) == [1], "the patient's new choice is stored"


@pytest.mark.asyncio
async def test_hc_oom_003b_a_fresh_profile_is_unchanged_and_a_later_opt_in_survives_reopening(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "database_encryption_required", False)
    path = tmp_path / "fresh" / "vault.db"
    migrations.run_profile_migration(path, KEY)
    assert _rev(path) == PROFILE_HEAD
    _engine_present(monkeypatch)
    engine = _pragma_on_vault_engine(path)
    try:
        with _client_for(path, engine, monkeypatch, tmp_path) as client:
            current = client.get("/settings/model").json()
            assert current["ocr_preference_enabled"] is False and current["ocr_effective"] is False, current
            assert _ocr_values(path) == [], "reading the setting must not create a row"

            opted = client.patch("/settings/model/ocr", json={"ocr_preference_enabled": True})
            assert opted.status_code == 200, opted.text
    finally:
        await engine.dispose()

    migrations.run_profile_migration(path, KEY)  # opened again, already at head

    assert _ocr_values(path) == [1], "018 must not run again over a choice made after it"


def test_hc_oom_004_the_pre_017_snapshot_is_not_taken_again_for_a_vault_already_at_017(
    tmp_path, monkeypatch
):
    path = _vault_at_017(tmp_path, monkeypatch)
    taken: list = []
    monkeypatch.setattr(migrations, "_ensure_pre017_snapshot", lambda *a, **k: taken.append(a))
    assert migrations._SNAPSHOT_REVISION == REV_017

    migrations.run_profile_migration(path, KEY)

    assert _ocr_values(path) == [0], "018 ran"
    assert taken == [], "017 is already applied: no snapshot call"
    assert list(path.parent.glob("vault.pre017*")) == [], "and no snapshot file"
