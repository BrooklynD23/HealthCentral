"""Regression tests for profile migrations without SQLCipher installed."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path


def _import_core_submodule(name: str):
    """Import a core submodule without executing core/__init__.py side effects."""
    if "core" not in sys.modules:
        core_package = types.ModuleType("core")
        core_package.__path__ = [str(Path(__file__).resolve().parents[1] / "core")]
        sys.modules["core"] = core_package

    return importlib.import_module(name)


def test_profile_migration_omits_creator_when_sqlcipher_unavailable(
    tmp_path,
    monkeypatch,
) -> None:
    """Profile migrations should work with stdlib sqlite in local dev."""
    migrations = _import_core_submodule("core.migrations")
    settings = _import_core_submodule("core.config").settings
    sqlcipher_driver = _import_core_submodule("core.sqlcipher_driver")

    monkeypatch.setattr(settings, "database_encryption_required", False)
    monkeypatch.setattr(sqlcipher_driver, "SQLCIPHER_AVAILABLE", False)

    vault_path = tmp_path / "vault.db"
    encryption_key = b"0" * 32

    migrations.run_profile_migration(vault_path, encryption_key)

    assert vault_path.exists()
    # Tracks the latest profile migration head; bump when a new profile
    # migration is added (currently 006_ocr_preference).
    assert (
        migrations.get_profile_current_revision(vault_path, encryption_key)
        == "006_ocr_preference"
    )
