"""One-time conversion of a plaintext profile vault to SQLCipher (SQLCIPHER-WHEEL).

Why this exists: ``profile_database`` applies ``PRAGMA key`` whenever SQLCipher is
importable. A Windows machine that ran the launcher before the ``sqlcipher3``
wheel was pinned holds vaults written as plain SQLite; once the wheel installs,
every one of those vaults would fail with "file is not a database". The owner
chose "convert on next login" (SQLC-OLD-VAULTS).

Rules this module keeps:
- It runs only when SQLCipher is available AND ``PRAGMA cipher_version`` is
  non-empty (a module that imports but is not SQLCipher never converts).
- The only readable copy is never deleted. The plain vault stays in place until
  the verified encrypted copy replaces it atomically; a plain backup
  (``vault.plain.bak``, not ending in ``.db``) is deleted only after the new
  vault reopens with its key and verifies.
- On failure only the temp encrypted file (``vault.enc-tmp``) is deleted. The
  caller gets one fixed message; no path, key, SQL or row text leaves here.
- A crash at any step is recovered on the next open (see ``_recover``).
- Never log the key or the hex key.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import time
from pathlib import Path

from .migrations import _snapshot_paths, _with_sidecars
from .sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available

logger = logging.getLogger(__name__)

PLAIN_HEADER = b"SQLite format 3\x00"
# Fixed, step-accurate messages. None of them carries a path, key, SQL or row text.
FIXED_MESSAGE = (
    "Could not convert this profile to encrypted storage. Your existing data was not changed."
)
MSG_UNVERIFIED = (
    "The encrypted copy of this profile could not be verified after the switch. "
    "A copy of your original data was kept in the profile folder."
)
MSG_RECOVER = (
    "This profile has an unfinished conversion to encrypted storage that could not be verified. "
    "Your data was kept in the profile folder."
)
MSG_PENDING = (
    "This profile's vault file is missing while a conversion to encrypted storage is pending. "
    "Your data was kept in the profile folder."
)
MSG_BUSY = "Another conversion of this profile is already running. Try again in a moment."
MSG_REPLACE_LOST = (
    "The switch to encrypted storage was interrupted. The encrypted copy and your original data "
    "were kept in the profile folder."
)
# The owner decision (SQLCIPHER-WHEEL) is Windows only: elsewhere a plain vault is left as on main.
_CONVERSION_PLATFORMS = ("win32",)
_STALE_LOCK_SECONDS = 600.0
_HEX = frozenset("0123456789abcdefABCDEF")


class _ConversionFailed(Exception):
    """A check failed. Internal: the message never leaves this module."""


def _fail(message: str = FIXED_MESSAGE) -> Exception:
    # Lazy import: profile_database imports this module.
    from .profile_database import ProfileDatabaseEncryptionError

    return ProfileDatabaseEncryptionError(message)


def _current_platform() -> str:
    return sys.platform


def _lock_path(vault_path: Path) -> Path:
    return vault_path.with_suffix(".convert.lock")


def _tmp_path(vault_path: Path) -> Path:
    return vault_path.with_suffix(".enc-tmp")


def _bak_path(vault_path: Path) -> Path:
    return vault_path.with_suffix(".plain.bak")


def _has_plain_header(path: Path) -> bool:
    with open(path, "rb") as handle:
        return handle.read(16) == PLAIN_HEADER


def _fsync_file(path: Path) -> None:
    with open(path, "rb+") as handle:
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_dir(directory: Path) -> None:
    if os.name == "nt":
        return  # Windows cannot open a directory for fsync
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _unlink_all(paths: list[Path]) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


def _sqlcipher_ready() -> bool:
    """SQLCipher importable and the module really reports a cipher version."""
    if not is_sqlcipher_available():
        return False
    try:
        conn = get_sqlcipher_module().connect(":memory:")
        try:
            row = conn.execute("PRAGMA cipher_version").fetchone()
        finally:
            conn.close()
    except Exception:
        return False
    return bool(row and row[0])


def _open_keyed(path: Path, hex_key: str):
    conn = get_sqlcipher_module().connect(str(path))
    try:
        conn.execute(f"PRAGMA key = \"x'{hex_key}'\"")
        conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except BaseException:
        conn.close()
        raise
    return conn


def _checkpoint_plain_wal(vault_path: Path) -> None:
    """Resolve a hot rollback journal, then fold a WAL into the plain main file.

    A plain read makes SQLite roll back a hot ``-journal`` before anything is copied.
    """
    conn = get_sqlcipher_module().connect(str(vault_path), timeout=5.0)
    try:
        conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
    finally:
        conn.close()


def _facts(conn) -> dict:
    """What must survive the copy: row counts, FK violations, alembic revision, user_version."""
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]
    counts = {t: conn.execute('SELECT count(*) FROM "%s"' % t.replace('"', '""')).fetchone()[0] for t in tables}
    alembic = (
        sorted(r[0] for r in conn.execute("SELECT version_num FROM alembic_version").fetchall())
        if "alembic_version" in tables
        else None
    )
    schema = sorted(
        tuple(r)
        for r in conn.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall()
    )
    return {
        "schema": schema,
        "counts": counts,
        "alembic": alembic,
        "user_version": conn.execute("PRAGMA user_version").fetchone()[0],
        # Old vaults can hold orphan rows that migration 017 cleans after the open, so
        # the rule is "the same violations as the source", which is none for a clean vault.
        "fk": sorted(tuple(r) for r in conn.execute("PRAGMA foreign_key_check").fetchall()),
    }


def _export_encrypted_copy(vault_path: Path, tmp: Path, hex_key: str) -> dict:
    """Write ``tmp`` as an encrypted copy of the plain vault; return the source facts."""
    conn = get_sqlcipher_module().connect(str(vault_path))
    try:
        source = _facts(conn)
        # The hex key is validated to 64 hex characters by the caller.
        conn.execute("ATTACH DATABASE ? AS encrypted KEY \"x'%s'\"" % hex_key, (str(tmp),))
        conn.execute("SELECT sqlcipher_export('encrypted')").fetchall()
        # sqlcipher_export does not carry user_version over.
        conn.execute("PRAGMA encrypted.user_version = %d" % int(source["user_version"]))
        conn.execute("DETACH DATABASE encrypted")
    finally:
        conn.close()
    return source


def _verify_encrypted_copy(tmp: Path, hex_key: str, source: dict) -> None:
    if _has_plain_header(tmp):
        raise _ConversionFailed("plain header")
    conn = _open_keyed(tmp, hex_key)
    try:
        if conn.execute("PRAGMA cipher_integrity_check").fetchall():
            raise _ConversionFailed("cipher_integrity_check")
        if [tuple(r) for r in conn.execute("PRAGMA integrity_check").fetchall()] != [("ok",)]:
            raise _ConversionFailed("integrity_check")
        copy = _facts(conn)
    finally:
        conn.close()
    for key in ("schema", "fk", "counts", "alembic", "user_version"):
        if copy[key] != source[key]:
            raise _ConversionFailed(key)


def _verify_keyed_vault(path: Path, hex_key: str) -> None:
    """The vault in place is ciphertext and opens with the key."""
    if _has_plain_header(path):
        raise _ConversionFailed("plain header")
    conn = _open_keyed(path, hex_key)
    try:
        if [tuple(r) for r in conn.execute("PRAGMA quick_check").fetchall()] != [("ok",)]:
            raise _ConversionFailed("quick_check")
    finally:
        conn.close()


def _delete_plain_copies(vault_path: Path) -> None:
    """Delete plaintext pre-017 snapshots, then the plain backup (the backup goes last:
    its presence is what tells the next open that cleanup is still pending).

    An encrypted snapshot is a recovery copy and is never touched.
    """
    try:
        for main in _snapshot_paths(vault_path):
            if main.exists() and (main.stat().st_size == 0 or _has_plain_header(main)):
                _unlink_all(_with_sidecars(main))
        _bak_path(vault_path).unlink(missing_ok=True)
    except OSError as exc:
        # The next open retries: the plain backup (or a plain snapshot) is still listed.
        logger.warning("Plain copy clean-up after vault conversion failed (%s)", type(exc).__name__)


def _plain_facts(path: Path) -> dict:
    conn = get_sqlcipher_module().connect(str(path))
    try:
        return _facts(conn)
    finally:
        conn.close()


def _keyed_facts(path: Path, hex_key: str) -> dict:
    conn = _open_keyed(path, hex_key)
    try:
        return _facts(conn)
    finally:
        conn.close()


def _recover(vault_path: Path, hex_key: str) -> bool:
    """Leftovers of an interrupted conversion, found with the vault already encrypted.

    Returns True when a leftover was found. A vault that does not open with the key keeps
    its plain copy and raises: that copy may be the only readable data. The plain copy is
    deleted only when the encrypted vault holds the same tables, alembic revision and row
    counts as it does; an empty or different vault never licenses the delete.
    """
    tmp, bak = _tmp_path(vault_path), _bak_path(vault_path)
    if not (bak.exists() or tmp.exists()):
        return False
    _verify_keyed_vault(vault_path, hex_key)
    _unlink_all(_with_sidecars(tmp))
    if bak.exists():
        try:
            kept, copy = _keyed_facts(vault_path, hex_key), _plain_facts(bak)
            same = kept["counts"] == copy["counts"] and kept["alembic"] == copy["alembic"]
        except Exception:
            same = False
        if not same:
            logger.warning(
                "An unfinished vault conversion left a plain copy that does not match the "
                "encrypted vault; the copy was kept"
            )
            return True
    _delete_plain_copies(vault_path)
    logger.warning("Finished clean-up of an interrupted vault conversion")
    return True


def _acquire_lock(vault_path: Path) -> Path:
    lock = _lock_path(vault_path)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            age = time.time() - lock.stat().st_mtime
        except OSError:
            age = 0.0
        if age > _STALE_LOCK_SECONDS:
            # Reported, never auto-deleted: a live conversion cannot be told from a dead one here.
            logger.error("A vault conversion lock is older than %d s; remove it by hand if no app is running", int(_STALE_LOCK_SECONDS))
        raise _ConversionFailed("locked") from None
    os.close(fd)
    return lock


def _needs_work(vault_path: Path) -> bool:
    if _tmp_path(vault_path).exists() or _bak_path(vault_path).exists():
        return True
    try:
        return vault_path.exists() and vault_path.stat().st_size >= 16 and _has_plain_header(vault_path)
    except OSError:
        return False


def convert_plaintext_vault_if_needed(vault_path: Path, hex_key: str) -> bool:
    """Convert ``vault_path`` to SQLCipher when it is a plain SQLite file.

    Returns True when a conversion happened, False when there was nothing to do
    (no SQLCipher, not Windows, no file, already encrypted). Raises
    ``ProfileDatabaseEncryptionError`` with a fixed, step-accurate message on any failure.
    Blocking: call it from a worker thread.
    """
    if _current_platform() not in _CONVERSION_PLATFORMS:
        return False
    if not _sqlcipher_ready():
        return False
    if not _needs_work(vault_path):
        return False
    try:
        lock = _acquire_lock(vault_path)
    except Exception as exc:
        logger.error("Vault conversion could not start (%s)", type(exc).__name__)
        raise _fail(MSG_BUSY if isinstance(exc, _ConversionFailed) else FIXED_MESSAGE) from None
    try:
        return _convert_locked(vault_path, hex_key)
    finally:
        lock.unlink(missing_ok=True)


def _convert_locked(vault_path: Path, hex_key: str) -> bool:
    tmp, bak = _tmp_path(vault_path), _bak_path(vault_path)
    step = "start"
    temp_is_ours = False  # True once this call may have written the temp file
    try:
        step = "key-format"
        if len(hex_key) != 64 or not set(hex_key) <= _HEX:
            raise _ConversionFailed("key format")
        step = "inspect"
        if not vault_path.exists() or vault_path.stat().st_size < 16:
            if bak.exists() or tmp.exists():
                # Never let a fresh empty vault be created over a pending conversion.
                step = "pending-missing"
                raise _ConversionFailed("vault missing")
            return False
        if not _has_plain_header(vault_path):
            step = "recover"
            _recover(vault_path, hex_key)
            return False

        step = "checkpoint"
        _checkpoint_plain_wal(vault_path)
        for sidecar in ("-wal", "-journal"):
            leftover = vault_path.with_name(vault_path.name + sidecar)
            if leftover.exists() and leftover.stat().st_size > 0:
                raise _ConversionFailed("sidecar not empty")
        step = "clear-temp"
        temp_is_ours = True
        _unlink_all(_with_sidecars(tmp))
        step = "plain-copy"
        shutil.copyfile(vault_path, bak)
        _fsync_file(bak)
        step = "export"
        source = _export_encrypted_copy(vault_path, tmp, hex_key)
        step = "verify"
        _verify_encrypted_copy(tmp, hex_key, source)
        step = "sync"
        _fsync_file(tmp)
        step = "replace"
        os.replace(tmp, vault_path)
        temp_is_ours = False  # the temp file is now the vault
        _fsync_dir(vault_path.parent)
        step = "reopen"
        _verify_keyed_vault(vault_path, hex_key)
    except Exception as exc:
        vault_present = vault_path.exists()
        if temp_is_ours and vault_present:
            # Only the temp file goes, and only while a vault is still in place: if the
            # replace removed the target and then raised, the temp file is the only
            # encrypted copy.
            try:
                _unlink_all(_with_sidecars(tmp))
            except OSError:
                pass
        # Step name and exception class only: no path, key, SQL or row text.
        logger.error("Vault conversion to encrypted storage failed at step %s (%s)", step, type(exc).__name__)
        if step == "reopen":
            message = MSG_UNVERIFIED
        elif step == "recover":
            message = MSG_RECOVER
        elif step == "pending-missing":
            message = MSG_PENDING
        elif step == "replace" and not vault_present:
            message = MSG_REPLACE_LOST
        else:
            message = FIXED_MESSAGE
        raise _fail(message) from None

    _delete_plain_copies(vault_path)
    logger.warning(
        "Profile vault converted to encrypted storage (%d tables, schema and row counts verified)",
        len(source["counts"]),
    )
    return True
