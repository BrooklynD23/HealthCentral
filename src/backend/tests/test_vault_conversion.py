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
import threading
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
def _sqlcipher_needed(monkeypatch):
    _require_sqlcipher()
    # The product gate is Windows only; these tests run the conversion on every platform.
    # HC-SQLC-018 puts the real gate back.
    monkeypatch.setattr(_vc(), "_CONVERSION_PLATFORMS", ("win32", "linux", "darwin"), raising=False)


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
            CREATE TRIGGER trg_obs AFTER INSERT ON observations BEGIN SELECT 1; END;
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
    original = vault.read_bytes()
    assert _convert(vault) is True  # leaves nothing; recreate the crash state by hand
    shutil_copy = tmp_path / "vault.plain.bak"
    shutil_copy.write_bytes(original)  # a real copy: same tables and row counts
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

    assert str(info.value) == _vc().MSG_RECOVER
    assert copy.exists() and _sha(vault) == before


# -- HC-SQLC-013 ---------------------------------------------------------------------


def _insert_real_rows(vault: Path) -> list[str]:
    """One row into every real table the migrations made that accepts a generated row."""
    conn = sqlite3.connect(vault)
    done: list[str] = []
    try:
        names = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                "AND name <> 'alembic_version' AND name NOT LIKE '%\\_fts%' ESCAPE '\\' "
                "AND sql NOT LIKE 'CREATE VIRTUAL%'"
            ).fetchall()
        ]
        for name in names:
            cols = conn.execute(f'PRAGMA table_info("{name}")').fetchall()
            values = []
            for _cid, col, ctype, notnull, default, pk in cols:
                if default is not None or (not notnull and not pk):
                    values.append(None if default is None else None)
                    continue
                t = (ctype or "").upper()
                if "INT" in t or "BOOL" in t:
                    values.append(1)
                elif any(k in t for k in ("REAL", "FLOA", "DOUB", "NUMERIC", "DECIMAL")):
                    values.append(1.5)
                else:
                    values.append(f"hc-sqlc-{name}-{col}")
            names_sql = ", ".join(f'"{c[1]}"' for c, v in zip(cols, values) if v is not None)
            if not names_sql:
                continue
            marks = ", ".join("?" for v in values if v is not None)
            try:
                conn.execute(
                    f'INSERT INTO "{name}" ({names_sql}) VALUES ({marks})', [v for v in values if v is not None]
                )
                conn.commit()
                done.append(name)
            except sqlite3.Error:
                conn.rollback()
    finally:
        conn.close()
    return done


def test_hc_sqlc_013_real_migrations_to_head_then_convert(tmp_path, monkeypatch):
    """The vault is what the real chain writes (every table, index, FTS shadow table
    and trigger of the profile chain), not a hand-built fixture."""
    import core.migrations as migrations

    key = generate_encryption_key()
    hex_key = base64.urlsafe_b64decode(key).hex().upper()
    vault = tmp_path / "vault.db"
    _migrate_plain_to_head(vault, key, monkeypatch)

    populated = _insert_real_rows(vault)
    assert len(populated) >= 5, populated

    src = sqlite3.connect(vault)
    try:
        tables = [r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        counts = {t: src.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tables}
        user_version = src.execute("PRAGMA user_version").fetchone()[0]
        source_fk = sorted(tuple(r) for r in src.execute("PRAGMA foreign_key_check").fetchall())
    finally:
        src.close()
    assert "alembic_version" in tables and len(tables) > 10
    assert all(counts[t] > 0 for t in populated)

    assert _convert(vault, hex_key) is True

    assert vault.read_bytes()[:16] != PLAIN_HEADER
    conn = _open_keyed(vault, hex_key)
    try:
        after = {t: conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tables}
        assert after == counts
        assert conn.execute("PRAGMA user_version").fetchone()[0] == user_version
        assert conn.execute("SELECT version_num FROM alembic_version").fetchall() == [(PROFILE_HEAD,)]
        # generated rows are FK orphans: the rule is "same violations as the source"
        assert sorted(tuple(r) for r in conn.execute("PRAGMA foreign_key_check").fetchall()) == source_fk
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


# -- HC-SQLC-019: never create a vault over a pending conversion ----------------------


@pytest.mark.parametrize("leftover", ["vault.plain.bak", "vault.enc-tmp"])
@pytest.mark.parametrize("vault_bytes", [None, b""])
def test_hc_sqlc_019_missing_or_empty_vault_with_a_pending_copy_raises_and_keeps_it(
    tmp_path, leftover, vault_bytes
):
    vault = tmp_path / "vault.db"
    copy = tmp_path / leftover
    plain = tmp_path / "src.db"
    _make_plain_vault(plain)
    copy.write_bytes(plain.read_bytes())
    if vault_bytes is not None:
        vault.write_bytes(vault_bytes)
    before = copy.read_bytes()

    with pytest.raises(ProfileDatabaseEncryptionError) as info:
        _convert(vault)

    assert str(info.value) == _vc().MSG_PENDING
    assert copy.read_bytes() == before, "the only data copy must be untouched"
    assert (not vault.exists()) if vault_bytes is None else vault.read_bytes() == b""


def test_hc_sqlc_019b_login_twice_cannot_delete_the_only_copy(tmp_path):
    """The reviewed data-loss path: login 1 creates an empty keyed vault, login 2 used to
    verify the EMPTY vault and delete the plain copy."""
    vault = tmp_path / "vault.db"
    copy = tmp_path / "vault.plain.bak"
    _make_plain_vault(copy)
    with pytest.raises(ProfileDatabaseEncryptionError):
        _convert(vault)  # login 1: nothing may create a vault
    assert not vault.exists()
    # even if something else created an empty keyed vault, the copy must survive
    k = _open_keyed(vault)
    k.execute("CREATE TABLE alembic_version (version_num TEXT)")
    k.commit()
    k.close()
    before = copy.read_bytes()
    _convert(vault)  # login 2: no delete, no matter whether it raises
    assert copy.read_bytes() == before


def test_hc_sqlc_019c_recover_keeps_the_copy_when_the_vault_differs(tmp_path):
    vault = tmp_path / "vault.db"
    plain = tmp_path / "src.db"
    _make_plain_vault(plain)
    _make_plain_vault(vault)
    vault.write_bytes(vault.read_bytes())
    assert _convert(vault) is True
    conn = _open_keyed(vault)
    conn.execute("DELETE FROM observations")
    conn.commit()
    conn.close()
    copy = tmp_path / "vault.plain.bak"
    copy.write_bytes(plain.read_bytes())

    _convert(vault)

    assert copy.exists(), "rows differ, so the plain copy is the only complete data"


# -- HC-SQLC-020: a replace that removed the target keeps the temp file --------------------


def test_hc_sqlc_020_replace_that_loses_the_target_keeps_the_encrypted_temp(tmp_path, monkeypatch):
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    vc = _vc()
    real_replace = os.replace

    def lossy_replace(src, dst):
        if str(src).endswith(".enc-tmp"):
            Path(dst).unlink()
            raise PermissionError("target removed, then the rename failed")
        return real_replace(src, dst)

    monkeypatch.setattr(vc.os, "replace", lossy_replace)
    with pytest.raises(ProfileDatabaseEncryptionError) as info:
        _convert(vault)
    monkeypatch.undo()

    assert str(info.value) == _vc().MSG_REPLACE_LOST
    assert (tmp_path / "vault.enc-tmp").exists(), "the temp file is the only encrypted copy"
    assert (tmp_path / "vault.plain.bak").exists()


# -- HC-SQLC-021: verification really verifies ------------------------------------------------


def _tamper_temp_before_verify(monkeypatch, sql: str) -> None:
    vc = _vc()
    real = vc._verify_encrypted_copy

    def wrapper(tmp, hex_key, source):
        conn = _open_keyed(tmp, hex_key)
        conn.execute(sql)
        conn.commit()
        conn.close()
        return real(tmp, hex_key, source)

    monkeypatch.setattr(vc, "_verify_encrypted_copy", wrapper)


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM observations WHERE id = 4",
        "DROP INDEX ix_obs_doc",
        "DROP TRIGGER trg_obs",
        "DROP VIEW v_obs",
        "PRAGMA user_version = 99",
        "UPDATE alembic_version SET version_num = '000_other'",
    ],
)
def test_hc_sqlc_021_a_tampered_export_is_refused_and_the_original_is_untouched(tmp_path, monkeypatch, sql):
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    before = _sha(vault)
    _tamper_temp_before_verify(monkeypatch, sql)

    with pytest.raises(ProfileDatabaseEncryptionError) as info:
        _convert(vault)

    assert str(info.value) == FIXED_MESSAGE
    assert _sha(vault) == before
    assert not (tmp_path / "vault.enc-tmp").exists()


def test_hc_sqlc_021b_a_vault_that_does_not_reopen_after_the_switch_keeps_the_copy(tmp_path, monkeypatch):
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    vc = _vc()
    real_replace = os.replace

    def replace_then_corrupt(src, dst):
        real_replace(src, dst)
        Path(dst).write_bytes(b"\x01" * 4096)

    monkeypatch.setattr(vc.os, "replace", replace_then_corrupt)
    with pytest.raises(ProfileDatabaseEncryptionError) as info:
        _convert(vault)
    monkeypatch.undo()

    assert str(info.value) == _vc().MSG_UNVERIFIED
    assert (tmp_path / "vault.plain.bak").exists(), "the plain copy must stay when the reopen fails"


# -- HC-SQLC-018: Windows only ---------------------------------------------------------------


def test_hc_sqlc_018_off_windows_a_plain_vault_is_not_converted(tmp_path, monkeypatch):
    vc = _vc()
    monkeypatch.setattr(vc, "_CONVERSION_PLATFORMS", ("win32",))
    monkeypatch.setattr(vc, "_current_platform", lambda: "linux", raising=False)
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    (tmp_path / "vault.plain.bak").write_bytes(PLAIN_HEADER + b"leftover")
    before = _sha(vault)

    assert _convert(vault) is False

    assert _sha(vault) == before
    assert _leftovers(tmp_path) == ["vault.plain.bak"], "nothing created, nothing deleted"
    monkeypatch.setattr(vc, "_current_platform", lambda: "win32", raising=False)
    assert _convert(vault) is True, "the same call on win32 converts"


# -- HC-SQLC-022: one conversion at a time ---------------------------------------------------


def test_hc_sqlc_022_a_second_conversion_is_refused_while_the_first_runs(tmp_path, monkeypatch):
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    vc = _vc()
    inside, release = threading.Event(), threading.Event()
    real_export = vc._export_encrypted_copy

    def slow_export(*args, **kwargs):
        inside.set()
        assert release.wait(30)
        return real_export(*args, **kwargs)

    monkeypatch.setattr(vc, "_export_encrypted_copy", slow_export)
    result: dict = {}
    first = threading.Thread(target=lambda: result.update(first=_convert(vault)))
    first.start()
    assert inside.wait(30)
    try:
        with pytest.raises(ProfileDatabaseEncryptionError) as info:
            _convert(vault)
        assert str(info.value) == vc.MSG_BUSY
    finally:
        release.set()
        first.join(60)

    assert result["first"] is True
    assert _leftovers(tmp_path) == [], "the lock file is removed"


def test_hc_sqlc_022b_a_stale_lock_is_reported_not_deleted(tmp_path, caplog):
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    lock = tmp_path / "vault.convert.lock"
    lock.write_bytes(b"")
    old = lock.stat().st_mtime - 3600
    os.utime(lock, (old, old))
    caplog.set_level(logging.ERROR)

    with pytest.raises(ProfileDatabaseEncryptionError):
        _convert(vault)

    assert lock.exists()
    assert "lock is older" in "\n".join(r.getMessage() for r in caplog.records)


# -- HC-SQLC-023: a hot journal is resolved or refused ------------------------------------


def test_hc_sqlc_023_a_leftover_journal_is_refused_before_the_copy(tmp_path, monkeypatch):
    vault = tmp_path / "vault.db"
    _make_plain_vault(vault)
    (tmp_path / "vault.db-journal").write_bytes(b"\x00" * 512)
    monkeypatch.setattr(_vc(), "_checkpoint_plain_wal", lambda path: None)
    before = _sha(vault)

    with pytest.raises(ProfileDatabaseEncryptionError) as info:
        _convert(vault)

    assert str(info.value) == FIXED_MESSAGE
    assert _sha(vault) == before
    assert not (tmp_path / "vault.plain.bak").exists()
    assert not (tmp_path / "vault.enc-tmp").exists()
