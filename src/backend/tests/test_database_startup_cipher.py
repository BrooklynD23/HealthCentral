"""HC-SQLC-009, 009b: master-DB startup check for SQLCipher (SQLCIPHER-WHEEL).

init_database() must refuse when encryption is required and the importable
module is not real SQLCipher (empty cipher_version), and must log one CRITICAL
line when encryption is off and SQLCipher is missing, never a quiet warning.
"""

from __future__ import annotations

import logging

import pytest

import core.database as database
from core.config import settings


@pytest.mark.asyncio
async def test_hc_sqlc_009_required_but_module_is_not_sqlcipher_refuses(monkeypatch):
    monkeypatch.setattr(settings, "database_encryption_required", True)
    monkeypatch.setattr(database, "is_sqlcipher_available", lambda: True)
    for empty in (None, ""):
        monkeypatch.setattr(database, "verify_cipher_version", lambda empty=empty: empty)
        with pytest.raises(RuntimeError, match="SQLCipher"):
            await database.init_database()


@pytest.mark.asyncio
async def test_hc_sqlc_009_required_and_real_sqlcipher_starts(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_encryption_required", True)
    monkeypatch.setattr(database, "is_sqlcipher_available", lambda: True)
    monkeypatch.setattr(database, "verify_cipher_version", lambda: "4.20.0 community")
    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))
    await database.init_database()


@pytest.mark.asyncio
async def test_hc_sqlc_009b_not_required_and_unavailable_logs_critical(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(settings, "database_encryption_required", False)
    monkeypatch.setattr(database, "is_sqlcipher_available", lambda: False)
    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))
    caplog.set_level(logging.DEBUG)

    await database.init_database()  # does not raise

    critical = [r for r in caplog.records if r.levelno == logging.CRITICAL]
    assert len(critical) == 1
    assert "not be encrypted" in critical[0].getMessage()
