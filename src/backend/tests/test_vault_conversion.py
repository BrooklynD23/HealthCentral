"""HC-SQLC-001..008, 012, 013: one-time conversion of a plaintext vault to SQLCipher.

SQLCIPHER-WHEEL. Windows machines that ran the launcher before the sqlcipher3
wheel existed hold plaintext vaults. Once SQLCipher is importable the open path
keys every vault, so without a conversion those vaults would fail with "file is
not a database". core/vault_conversion.py converts them on the next login.

Every test builds a real vault file and reads the bytes on disk. Nothing here
mocks the SQLCipher module.
"""

from __future__ import annotations

import base64
import hashlib
import importlib
import logging
import os
import sqlite3
from pathlib import Path

import aiosqlite.core
import pytest
from sqlalchemy import text

import core.sqlcipher_driver as sqlcipher_driver
from core.config import settings
from core.profile_database import (
    ProfileDatabaseEncryptionError,
    get_profile_db_manager,
)
from core.security import generate_encryption_key, seal_key_with_dpapi
from tests.support.migrations import PROFILE_HEAD

PLAIN_HEADER = b"SQLite format 3\x00"
HEX_KEY = "AB" * 32  # synthetic, test-only
OTHER_HEX_KEY = "CD" * 32
PROFILE = "hc-sqlc-profile"
PASSWORD = "Sqlc-Pass-2026"
CANARY = "HC-SQLC-CANARY-glucose-91c2"
FIXED_MESSAGE = "Could not convert this profile to encrypted storage. Your existing data was not changed."


def _vc():
    """Import inside each test so a missing module is a per-test failure (RED)."""
    return importlib.import_module("core.vault_conversion")


def _require_sqlcipher() -> None:
    if sqlcipher_driver.is_sqlcipher_available():
        return
    if os.environ.get("CI", "").lower() == "true" or os.environ.get("HC_REQUIRE_SQLCIPHER") == "1":
        pytest.fail("sqlcipher3 is not importable but CI / HC_REQUIRE_SQLCIPHER=1 requires it", pytrace=False)
    pytest.skip("needs sqlcipher3; set HC_REQUIRE_SQLCIPHER=1 to make this a failure")


@pytest.fixture(autouse=True)
def _sqlcipher_needed():
    _require_sqlcipher()


def _make_plain_vault(path: Path, *, user_version: int = 7) -> None:
    """A plaintext vault: three tables, a foreign key, an index, a view, an FTS5 table."""
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            f"""
            CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);
            INSERT INTO alembic_version VALUES ('019_export_artifacts');
            CREATE TABLE documents (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE observations (
                id INTEGER PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id),
                note TEXT
            );
            CREATE INDEX ix_obs_doc ON observations(document_id);
            CREATE VIEW v_obs AS SELECT id, note FROM observations;
            CREATE VIRTUAL TABLE search_records_fts USING fts5(title, content);
            INSERT INTO documents VALUES (1, 'a'), (2, 'b'), (3, 'c');
            INSERT INTO observations VALUES (1, 1, '{CANARY}'), (2, 2, 'x'), (3, 3, 'y'), (4, 3, 'z');
            INSERT INTO search_records_fts VALUES ('t1', '{CANARY}'), ('t2', 'other');
            PRAGMA user_version = {user_version};
            """
        )
        conn.commit()
    finally:
        conn.close()


def _open_keyed(path: Path, hex_key: str = HEX_KEY):
    conn = sqlcipher_driver.get_sqlcipher_module().connect(str(path))
    conn.execute(f"PRAGMA key = \"x'{hex_key}'\"")
    return conn


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _convert(path: Path, hex_key: str = HEX_KEY):
    return _vc().convert_plaintext_vault_if_needed(path, hex_key)


def _leftovers(vault_dir: Path) -> list[str]:
    return sorted(p.name for p in vault_dir.iterdir() if p.name != "vault.db")


# -- HC-SQLC-001 ---------------------------------------------------------------------


def test_hc_sqlc_001_plain_vault_is_converted_and_keeps_its_data(tmp_path):
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault, user_version=7)
    assert vault.read_bytes()[:16] == PLAIN_HEADER

    assert _convert(vault) is True

    raw = vault.read_bytes()
    assert raw[:16] != PLAIN_HEADER
    assert CANARY.encode() not in raw
    plain = sqlite3.connect(vault)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            plain.execute("SELECT count(*) FROM sqlite_master").fetchone()
    finally:
        plain.close()

    conn = _open_keyed(vault)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 7
        assert conn.execute("SELECT count(*) FROM documents").fetchone()[0] == 3
        assert conn.execute("SELECT count(*) FROM observations").fetchone()[0] == 4
        assert conn.execute("SELECT count(*) FROM search_records_fts").fetchone()[0] == 2
        assert conn.execute("SELECT note FROM v_obs WHERE id = 1").fetchone()[0] == CANARY
        assert conn.execute("SELECT version_num FROM alembic_version").fetchall() == [("019_export_artifacts",)]
        assert conn.execute("PRAGMA cipher_integrity_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        conn.close()
    assert _leftovers(tmp_path) == [], "the plaintext copy and temp file must be gone"


# -- HC-SQLC-002 ---------------------------------------------------------------------


def test_hc_sqlc_002_encrypted_or_missing_vault_is_left_alone(tmp_path):
    missing = tmp_path / "vault.db"
    assert _convert(missing) is False
    assert not missing.exists()

    plain = tmp_path / "src.db"
    _make_plain_vault(plain)
    enc = tmp_path / "enc" / "vault.db"
    enc.parent.mkdir()
    plain.replace(enc)
    assert _convert(enc) is True  # first conversion
    before = _sha(enc)
    assert _convert(enc) is False  # already encrypted: no-op
    assert _sha(enc) == before
    assert _leftovers(enc.parent) == []

    empty = tmp_path / "empty" / "vault.db"
    empty.parent.mkdir()
    empty.write_bytes(b"")
    assert _convert(empty) is False
    assert empty.read_bytes() == b""


# -- HC-SQLC-003 ---------------------------------------------------------------------


def test_hc_sqlc_003_non_empty_wal_is_refused_and_nothing_changes(tmp_path, monkeypatch):
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    wal = tmp_path / "vault.db-wal"
    wal.write_bytes(b"\x00" * 64)
    # The checkpoint step cannot absorb a WAL it cannot read as a WAL; the refusal
    # is on the file left behind, so make sure it is still there after the checkpoint.
    vc = _vc()
    monkeypatch.setattr(vc, "_checkpoint_plain_wal", lambda path: None)
    before = _sha(vault)

    with pytest.raises(ProfileDatabaseEncryptionError) as info:
        _convert(vault)

    assert str(info.value) == FIXED_MESSAGE
    assert _sha(vault) == before
    assert vault.read_bytes()[:16] == PLAIN_HEADER
    assert not (tmp_path / "vault.enc-tmp").exists()
    assert not (tmp_path / "vault.plain.bak").exists()


# -- HC-SQLC-004 ---------------------------------------------------------------------


def test_hc_sqlc_004_failed_verification_leaves_the_original_and_removes_only_the_temp(tmp_path, monkeypatch):
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    before = _sha(vault)
    vc = _vc()

    def boom(*args, **kwargs):
        raise RuntimeError(f"verification blew up on {CANARY} {HEX_KEY}")

    monkeypatch.setattr(vc, "_verify_encrypted_copy", boom)
    with pytest.raises(ProfileDatabaseEncryptionError) as info:
        _convert(vault)

    assert str(info.value) == FIXED_MESSAGE
    assert CANARY not in str(info.value) and HEX_KEY not in str(info.value)
    assert _sha(vault) == before, "the original vault must be byte-identical"
    assert not (tmp_path / "vault.enc-tmp").exists(), "the temp encrypted file must be deleted"
    # the only readable copy is never deleted: the original stays, and the copy stays too
    assert vault.read_bytes()[:16] == PLAIN_HEADER


def test_hc_sqlc_004b_failed_replace_leaves_the_original(tmp_path, monkeypatch):
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    before = _sha(vault)
    vc = _vc()

    def no_replace(src, dst):
        raise PermissionError("locked by another process")

    monkeypatch.setattr(vc.os, "replace", no_replace)
    with pytest.raises(ProfileDatabaseEncryptionError):
        _convert(vault)
    monkeypatch.undo()
    assert _sha(vault) == before
    assert not (tmp_path / "vault.enc-tmp").exists()


# -- HC-SQLC-005 ---------------------------------------------------------------------


def test_hc_sqlc_005_without_sqlcipher_a_plain_vault_is_not_touched(tmp_path, monkeypatch):
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    before = _sha(vault)
    vc = _vc()
    monkeypatch.setattr(vc, "is_sqlcipher_available", lambda: False)

    assert _convert(vault) is False
    assert _sha(vault) == before
    assert _leftovers(tmp_path) == []


def test_hc_sqlc_005b_a_module_with_empty_cipher_version_is_not_touched(tmp_path, monkeypatch):
    """An importable module that is not SQLCipher (stdlib sqlite3) must not convert."""
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    before = _sha(vault)
    vc = _vc()
    monkeypatch.setattr(vc, "get_sqlcipher_module", lambda: sqlite3)

    assert _convert(vault) is False
    assert _sha(vault) == before
    assert _leftovers(tmp_path) == []


# -- HC-SQLC-006 ---------------------------------------------------------------------


def test_hc_sqlc_006_no_key_and_no_patient_text_in_logs(tmp_path, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    ok = tmp_path / "ok" / "vault.db"
    ok.parent.mkdir()
    _make_plain_vault(ok)
    assert _convert(ok) is True

    bad = tmp_path / "bad" / "vault.db"
    bad.parent.mkdir()
    _make_plain_vault(bad)
    monkeypatch.setattr(
        _vc(), "_verify_encrypted_copy",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError(f"{HEX_KEY} {CANARY}")),
    )
    with pytest.raises(ProfileDatabaseEncryptionError):
        _convert(bad)

    log_text = "\n".join(r.getMessage() for r in caplog.records)
    assert "convert" in log_text.lower(), "the conversion must leave one log line"
    assert HEX_KEY not in log_text and HEX_KEY.lower() not in log_text
    assert CANARY not in log_text
    assert "x'" not in log_text


# -- HC-SQLC-007 ---------------------------------------------------------------------


def _write_snapshots(vault_dir: Path, *, plain: bool) -> list[Path]:
    body = PLAIN_HEADER + b"old plaintext rows" if plain else b"\x8f" * 64
    names = [
        "vault.pre017.snapshot",
        "vault.pre017.snapshot.tmp",
        "vault.pre017.snapshot.aside",
        "vault.pre017.snapshot-wal",
        "vault.pre017.snapshot.aside-journal",
    ]
    paths = []
    for name in names:
        path = vault_dir / name
        path.write_bytes(body)
        paths.append(path)
    return paths


def test_hc_sqlc_007_plaintext_pre017_snapshots_are_deleted_after_verified_conversion(tmp_path):
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    snaps = _write_snapshots(tmp_path, plain=True)

    assert _convert(vault) is True

    assert [p.name for p in snaps if p.exists()] == []


def test_hc_sqlc_007b_encrypted_snapshots_are_never_touched(tmp_path):
    """Only a plaintext copy is the leak; an encrypted snapshot is a recovery copy."""
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    snaps = _write_snapshots(tmp_path, plain=False)

    assert _convert(vault) is True

    assert all(p.exists() for p in snaps)


def test_hc_sqlc_007c_snapshots_stay_when_conversion_fails(tmp_path, monkeypatch):
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    snaps = _write_snapshots(tmp_path, plain=True)
    monkeypatch.setattr(
        _vc(), "_verify_encrypted_copy", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
    )

    with pytest.raises(ProfileDatabaseEncryptionError):
        _convert(vault)

    assert all(p.exists() for p in snaps)


# -- HC-SQLC-008 ---------------------------------------------------------------------


@pytest.fixture
def manager_env(tmp_path, monkeypatch):
    monkeypatch.setattr(aiosqlite.core, "sqlite3", aiosqlite.core.sqlite3)  # restore at teardown
    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))
    monkeypatch.setattr(settings, "database_encryption_required", True)
    vault_dir = tmp_path / "vaults" / PROFILE
    vault_dir.mkdir(parents=True)
    key = generate_encryption_key()
    sealed, method = seal_key_with_dpapi(key, fallback_password=PASSWORD, force_password=True)
    (vault_dir / "key.bin").write_bytes(sealed)
    (vault_dir / "key.method").write_text(method)
    hex_key = get_profile_db_manager()._key_to_hex(key)
    return vault_dir, key, hex_key


def _migrate_plain_to_head(vault: Path, key: bytes, monkeypatch) -> None:
    """Run the REAL profile migrations to head with SQLCipher switched off."""
    import core.migrations as migrations

    with monkeypatch.context() as m:
        m.setattr(settings, "database_encryption_required", False)
        m.setattr(sqlcipher_driver, "SQLCIPHER_AVAILABLE", False)
        migrations.run_profile_migration(vault, key)
    assert vault.read_bytes()[:16] == PLAIN_HEADER


@pytest.mark.asyncio
async def test_hc_sqlc_008_login_converts_a_plain_vault_and_it_opens_keyed(manager_env, monkeypatch):
    vault_dir, key, hex_key = manager_env
    vault = vault_dir / "vault.db"
    _migrate_plain_to_head(vault, key, monkeypatch)
    manager = get_profile_db_manager()

    connection = await manager.open_profile_database(PROFILE, PASSWORD)
    try:
        async with connection.get_session() as session:
            version = (await session.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
    finally:
        await manager.close_profile_database(PROFILE)

    assert version == PROFILE_HEAD
    assert vault.read_bytes()[:16] != PLAIN_HEADER
    assert _leftovers(vault_dir) == ["key.bin", "key.method"]


# -- HC-SQLC-012 ---------------------------------------------------------------------


def test_hc_sqlc_012a_crash_after_replace_deletes_the_copy_on_next_open(tmp_path):
    """The encrypted vault was moved in; the process died before the copy was deleted."""
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    shutil_copy = tmp_path / "vault.plain.bak"
    shutil_copy.write_bytes(vault.read_bytes())
    assert _convert(vault) is True  # leaves nothing; recreate the crash state by hand
    shutil_copy.write_bytes(PLAIN_HEADER + b"stale plaintext copy")
    snap = tmp_path / "vault.pre017.snapshot"
    snap.write_bytes(PLAIN_HEADER + b"old")
    before = _sha(vault)

    assert _convert(vault) is False  # nothing to convert; recovery runs

    assert _sha(vault) == before
    assert not shutil_copy.exists()
    assert not snap.exists()


def test_hc_sqlc_012b_crash_before_replace_redoes_the_conversion(tmp_path):
    """The process died after writing the temp file; the plain vault is untouched."""
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    (tmp_path / "vault.enc-tmp").write_bytes(b"\x01" * 4096)  # half-written ciphertext
    (tmp_path / "vault.plain.bak").write_bytes(vault.read_bytes())

    assert _convert(vault) is True

    assert vault.read_bytes()[:16] != PLAIN_HEADER
    conn = _open_keyed(vault)
    try:
        assert conn.execute("SELECT count(*) FROM observations").fetchone()[0] == 4
    finally:
        conn.close()
    assert _leftovers(tmp_path) == []


def test_hc_sqlc_012c_unreadable_encrypted_vault_never_loses_its_plain_copy(tmp_path):
    """If the vault in place does not open with the key, the copy is the only readable data."""
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    assert _convert(vault, OTHER_HEX_KEY) is True  # encrypted under a different key
    copy = tmp_path / "vault.plain.bak"
    copy.write_bytes(PLAIN_HEADER + b"the only readable copy")
    before = _sha(vault)

    with pytest.raises(ProfileDatabaseEncryptionError) as info:
        _convert(vault, HEX_KEY)

    assert str(info.value) == FIXED_MESSAGE
    assert copy.exists() and _sha(vault) == before


# -- HC-SQLC-013 ---------------------------------------------------------------------


def test_hc_sqlc_013_real_migrations_to_head_then_convert(tmp_path, monkeypatch):
    """The vault is what the real chain writes (every table, index, FTS shadow table
    and trigger of the profile chain), not a hand-built fixture."""
    import core.migrations as migrations

    key = generate_encryption_key()
    hex_key = base64.urlsafe_b64decode(key).hex().upper()
    vault = tmp_path / "vault.db"
    _migrate_plain_to_head(vault, key, monkeypatch)

    src = sqlite3.connect(vault)
    try:
        tables = [r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        counts = {t: src.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tables}
        user_version = src.execute("PRAGMA user_version").fetchone()[0]
    finally:
        src.close()
    assert "alembic_version" in tables and len(tables) > 10

    assert _convert(vault, hex_key) is True

    assert vault.read_bytes()[:16] != PLAIN_HEADER
    conn = _open_keyed(vault, hex_key)
    try:
        after = {t: conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tables}
        assert after == counts
        assert conn.execute("PRAGMA user_version").fetchone()[0] == user_version
        assert conn.execute("SELECT version_num FROM alembic_version").fetchall() == [(PROFILE_HEAD,)]
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()
    # The real keyed migration runner treats the converted vault as already at head.
    assert migrations.get_profile_current_revision(vault, key) == PROFILE_HEAD
    assert _leftovers(tmp_path) == []


# -- foreign-key orphans in an old vault -------------------------------------------------


def test_hc_sqlc_008b_source_orphans_do_not_block_conversion(tmp_path):
    """A pre-017 vault can hold orphan rows; migration 017 cleans them AFTER the open.
    The check is 'no more violations than the source', not 'zero'."""
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    conn = sqlite3.connect(vault)
    conn.execute("INSERT INTO observations VALUES (9, 999, 'orphan')")
    conn.commit()
    conn.close()

    assert _convert(vault) is True

    keyed = _open_keyed(vault)
    try:
        assert keyed.execute("SELECT count(*) FROM observations").fetchone()[0] == 5
    finally:
        keyed.close()
