"""Regression test: migrations must not disable existing application loggers.

Alembic's env.py calls ``logging.config.fileConfig`` to apply the logging
config from ``alembic.ini``. That function defaults to
``disable_existing_loggers=True``, which silently disables every logger not
named in the ini's ``[loggers]`` section. Because migrations run in-process at
app startup *and* on every profile-vault open, the default would mute all
application loggers — including ``SECURITY_AUDIT`` / break-glass audit trails —
after the first migration. Both env.py files pass
``disable_existing_loggers=False`` to prevent this; this test guards that fix.
"""

from __future__ import annotations

import importlib
import logging
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


def test_profile_migration_keeps_app_loggers_enabled(tmp_path, monkeypatch) -> None:
    """An app logger created before a migration must stay enabled afterward."""
    migrations = _import_core_submodule("core.migrations")
    settings = _import_core_submodule("core.config").settings
    sqlcipher_driver = _import_core_submodule("core.sqlcipher_driver")

    monkeypatch.setattr(settings, "database_encryption_required", False)
    monkeypatch.setattr(sqlcipher_driver, "SQLCIPHER_AVAILABLE", False)

    # Loggers that exist before the migration runs. SECURITY_AUDIT mirrors the
    # real audit logger; the others stand in for core.*/modules.* loggers.
    audit_logger = logging.getLogger("SECURITY_AUDIT")
    core_logger = logging.getLogger("core.regression_probe")
    assert not audit_logger.disabled
    assert not core_logger.disabled

    migrations.run_profile_migration(tmp_path / "vault.db", b"0" * 32)

    # The migration's fileConfig() call must not have disabled them.
    assert not audit_logger.disabled, (
        "SECURITY_AUDIT logger was disabled by migration logging config — "
        "audit trails would be silently dropped. Check disable_existing_loggers."
    )
    assert not core_logger.disabled, (
        "Application logger was disabled by migration logging config — "
        "check disable_existing_loggers=False in migrations env.py."
    )
