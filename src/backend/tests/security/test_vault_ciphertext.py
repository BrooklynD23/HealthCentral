"""HC-KEYCT — a profile vault is ciphertext on disk (KEY-02, C-KEY-1).

The suite runs with DATABASE_ENCRYPTION_REQUIRED=false (tests/conftest.py), so
no other pytest proves a vault file is encrypted. These tests turn the
requirement back on for themselves and read the raw bytes.

sqlcipher3-binary publishes Linux wheels only (no win_amd64), so on native
Windows HC-KEYCT-001/002 skip. In CI (CI=true) or with HC_REQUIRE_SQLCIPHER=1
a missing sqlcipher3 is a FAILURE, never a skip (HC-KEYCT-005).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import aiosqlite.core
import pytest
from sqlalchemy import text

import core.sqlcipher_driver as sqlcipher_driver
from core.config import settings
from core.profile_database import get_profile_db_manager
from core.security import generate_encryption_key, seal_key_with_dpapi

SQLITE_PLAINTEXT_HEADER = b"SQLite format 3\x00"
PROFILE = "hc-keyct-profile"
PASSWORD = "Keyct-Pass-2026"
CANARY = "HC-KEYCT-CANARY-glucose-7f3a"


def _require_sqlcipher() -> None:
    if sqlcipher_driver.is_sqlcipher_available():
        return
    if os.environ.get("CI", "").lower() == "true" or os.environ.get("HC_REQUIRE_SQLCIPHER") == "1":
        pytest.fail(
            "KEY-02: sqlcipher3 is not importable, but CI / HC_REQUIRE_SQLCIPHER=1 requires "
            "the on-disk ciphertext proof. Install sqlcipher3-binary (Linux).",
            pytrace=False,
        )
    pytest.skip(
        "KEY-02 needs sqlcipher3 (Linux wheel only). "
        "Set HC_REQUIRE_SQLCIPHER=1 to turn this skip into a failure."
    )


def _assert_vault_ciphertext(vault_dir: Path, canary: str) -> None:
    db = vault_dir / "vault.db"
    assert db.exists(), f"{db} was never written"
    assert db.read_bytes()[:16] != SQLITE_PLAINTEXT_HEADER, (
        "vault.db has a plaintext SQLite header: the vault is NOT encrypted"
    )
    for sidecar in sorted(vault_dir.glob("vault.db*")):
        assert canary.encode() not in sidecar.read_bytes(), (
            f"canary found in plaintext in {sidecar.name}"
        )
    conn = sqlite3.connect(db)  # stdlib sqlite3, no key
    try:
        with pytest.raises(sqlite3.DatabaseError, match="file is not a database"):
            conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
    finally:
        conn.close()


@pytest.fixture
def vault_dir(tmp_path, monkeypatch) -> Path:
    monkeypatch.setattr(aiosqlite.core, "sqlite3", aiosqlite.core.sqlite3)  # restore at teardown: open_profile_database patches it globally
    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))
    monkeypatch.setattr(settings, "database_encryption_required", True)
    vault = tmp_path / "vaults" / PROFILE
    vault.mkdir(parents=True)
    sealed, method = seal_key_with_dpapi(
        generate_encryption_key(), fallback_password=PASSWORD, force_password=True
    )
    (vault / "key.bin").write_bytes(sealed)
    (vault / "key.method").write_text(method)
    return vault


async def _write_canary_and_close() -> None:
    manager = get_profile_db_manager()
    connection = await manager.open_profile_database(PROFILE, PASSWORD)
    try:
        async with connection.get_session() as session:
            await session.execute(text("CREATE TABLE hc_keyct_probe (note TEXT NOT NULL)"))
            await session.execute(
                text("INSERT INTO hc_keyct_probe (note) VALUES (:n)"), {"n": CANARY}
            )
    finally:
        await manager.close_profile_database(PROFILE)


@pytest.mark.asyncio
async def test_hc_keyct_001_vault_file_is_ciphertext_on_disk(vault_dir):
    _require_sqlcipher()
    await _write_canary_and_close()
    _assert_vault_ciphertext(vault_dir, CANARY)


@pytest.mark.asyncio
async def test_hc_keyct_002_the_same_vault_reopens_with_its_key(vault_dir):
    """Positive control: the bytes are a valid SQLCipher DB, not just garbage."""
    _require_sqlcipher()
    await _write_canary_and_close()
    manager = get_profile_db_manager()
    connection = await manager.open_profile_database(PROFILE, PASSWORD)
    try:
        async with connection.get_session() as session:
            note = (await session.execute(text("SELECT note FROM hc_keyct_probe"))).scalar_one()
    finally:
        await manager.close_profile_database(PROFILE)
    assert note == CANARY


@pytest.mark.asyncio
async def test_hc_keyct_003_negative_control_plaintext_vault_is_caught(vault_dir, monkeypatch):
    """Break-it, kept in CI: with SQLCipher off, the real open path writes a
    plaintext vault, and the assertion helper must catch it."""
    monkeypatch.setattr(settings, "database_encryption_required", False)
    monkeypatch.setattr(sqlcipher_driver, "SQLCIPHER_AVAILABLE", False)
    monkeypatch.setattr(aiosqlite.core, "sqlite3", sqlite3)  # undo any earlier sqlcipher patch
    await _write_canary_and_close()
    with pytest.raises(AssertionError, match="plaintext SQLite header"):
        _assert_vault_ciphertext(vault_dir, CANARY)


@pytest.mark.asyncio
async def test_hc_keyct_004_required_encryption_without_sqlcipher_fails_closed(vault_dir, monkeypatch):
    monkeypatch.setattr(sqlcipher_driver, "SQLCIPHER_AVAILABLE", False)
    monkeypatch.setattr(aiosqlite.core, "sqlite3", sqlite3)
    # core/migrations.py:213-217 (main@40f590e) refuses before any file is created.
    with pytest.raises(RuntimeError, match="SQLCipher is required but not available"):
        await get_profile_db_manager().open_profile_database(PROFILE, PASSWORD)
    assert not (vault_dir / "vault.db").exists(), "a vault file was written despite the refusal"
    assert not get_profile_db_manager().is_profile_open(PROFILE)


@pytest.mark.parametrize(
    ("env", "outcome"),
    [({"CI": "true"}, "fail"), ({"HC_REQUIRE_SQLCIPHER": "1"}, "fail"), ({}, "skip")],
    ids=["ci", "forced", "local"],
)
def test_hc_keyct_005_missing_sqlcipher_fails_in_ci_and_skips_locally(monkeypatch, env, outcome):
    monkeypatch.setattr(sqlcipher_driver, "SQLCIPHER_AVAILABLE", False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("HC_REQUIRE_SQLCIPHER", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    expected = pytest.fail.Exception if outcome == "fail" else pytest.skip.Exception
    with pytest.raises(expected):
        _require_sqlcipher()
