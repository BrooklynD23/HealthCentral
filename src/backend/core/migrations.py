"""
Alembic migration utilities with baseline detection.

Provides safe migration execution for:
- Master database (profiles, audit logs, knowledge base)
- Per-profile SQLCipher encrypted vaults

Key features:
- Baseline detection: an existing master DB without alembic_version is stamped at
  head (not migrated). A profile vault without it is stamped at the newest revision
  its schema matches, then upgraded; one that matches none is refused.
- Pre-017 snapshot: a verified encrypted copy before revision 017 runs on a vault
  that already has data (see ``_ensure_pre017_snapshot``).
- Startup-safe execution: Alembic calls run synchronously at startup/login gates
- SQLCipher support: Profile migrations use PRAGMA key for encryption
"""

import asyncio
import logging
import os
import shutil
import sqlite3
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, inspect, text

from .config import settings
from .sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available
from .time import UTC, utcfromtimestamp, utcnow

logger = logging.getLogger(__name__)

# Path to alembic.ini relative to backend root
ALEMBIC_INI_PATH = Path(__file__).parent.parent / "alembic.ini"


def _get_alembic_config(section: str = "master") -> Config:
    """
    Get Alembic config for the specified section.

    Args:
        section: "master" or "profile"

    Returns:
        Configured Alembic Config object
    """
    config = Config(str(ALEMBIC_INI_PATH), ini_section=section)
    # Set script_location based on section
    script_location = Path(__file__).parent.parent / "migrations" / section
    config.set_main_option("script_location", str(script_location))
    return config


def _key_to_hex(key: bytes) -> str:
    """
    Convert a raw key to hex string for SQLCipher PRAGMA.

    Matches PerProfileDatabaseManager._key_to_hex() semantics.
    """
    import base64

    # If key is base64 encoded (Fernet key format), decode it first
    if len(key) == 44:  # Base64-encoded 32 bytes
        key = base64.urlsafe_b64decode(key)

    if len(key) != 32:
        raise ValueError(f"Encryption key must be 32 bytes, got {len(key)}")

    return key.hex().upper()


def _check_baseline_needed(connection, expected_tables: list[str]) -> tuple[bool, bool]:
    """
    Check if baseline stamping is needed for an existing database.

    Args:
        connection: SQLAlchemy connection
        expected_tables: List of table names expected in the schema

    Returns:
        Tuple of (has_tables, has_alembic_version)
    """
    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())

    # Check for expected tables
    has_tables = any(table in existing_tables for table in expected_tables)

    # Check for alembic_version table
    has_alembic_version = "alembic_version" in existing_tables

    return has_tables, has_alembic_version


def _get_sync_master_url() -> str:
    """
    Get sync database URL for master database.

    Converts async URL to sync URL for Alembic.
    """
    async_url = settings.database_url
    return async_url.replace("sqlite+aiosqlite://", "sqlite://")


# =============================================================================
# Master Database Migrations
# =============================================================================


def run_master_migrations() -> None:
    """
    Run migrations for the master database with baseline detection.

    Baseline logic:
    - If tables exist but no alembic_version → stamp head (don't migrate)
    - If no tables → upgrade head (create schema)
    - If alembic_version exists → upgrade head (run pending migrations)
    """
    logger.info("Running master database migrations...")

    # Ensure data directory exists
    if settings.app_mode == "local":
        data_dir = Path(settings.app_data_path)
        data_dir.mkdir(parents=True, exist_ok=True)

    # Expected master tables for baseline detection
    expected_tables = [
        "profiles",
        "audit_logs",
        "biomarker_knowledge",
        "intervention_mappings",
        "biomarker_relationships",
    ]

    # Create sync engine for baseline check
    sync_url = _get_sync_master_url()
    engine = create_engine(sync_url)

    try:
        with engine.connect() as connection:
            has_tables, has_alembic_version = _check_baseline_needed(
                connection, expected_tables
            )

            config = _get_alembic_config("master")

            if has_tables and not has_alembic_version:
                # Existing DB without alembic_version: stamp head
                logger.info(
                    "Master DB has existing tables but no alembic_version. "
                    "Stamping head to baseline."
                )
                command.stamp(config, "head")
                logger.info("Master database baselined successfully.")
            else:
                current_revision = None
                if has_alembic_version:
                    current_revision = MigrationContext.configure(
                        connection
                    ).get_current_revision()
                    heads = set(ScriptDirectory.from_config(config).get_heads())
                    if current_revision in heads:
                        logger.info(
                            "Master database already at head revision %s.",
                            current_revision,
                        )
                        return

                # Either empty DB or has pending migrations: upgrade
                logger.info(
                    "Running master database upgrade to head from revision %s...",
                    current_revision or "<empty>",
                )
                command.upgrade(config, "head")
                logger.info("Master database migrations completed.")

    finally:
        engine.dispose()


async def run_master_migrations_async() -> None:
    """
    Async wrapper for master migrations.

    Alembic's synchronous migration runner can hang when scheduled through the
    event-loop executor in this app's startup path. Run it directly here:
    startup cannot serve requests until migrations finish anyway.
    """
    run_master_migrations()



# =============================================================================
# Pre-017 snapshot (C-P6 / P6-SNAPSHOT)
# =============================================================================

# Migration 017 deletes orphan child rows and nulls dangling links, and its
# downgrade restores neither. So an existing, non-empty vault is copied first.
# The copy is the encrypted file itself, never decrypted: same key, same bytes.
_SNAPSHOT_REVISION = "017_fk_cascade_alignment"
# Neither name may end in ".db": scripts/backup.py collects vaults with
# rglob("*.db"), and a snapshot in a backup would outlive the profile's delete.
_SNAPSHOT_NAME = "vault.pre017.snapshot"
_SNAPSHOT_TMP_NAME = "vault.pre017.snapshot.tmp"
_SNAPSHOT_SIDECARS = ("-wal", "-shm", "-journal")
# A snapshot is purged on the first open this long (or longer) after it was made.
_SNAPSHOT_MAX_AGE = timedelta(days=30)
# How long the WAL checkpoint may wait for a reader before the snapshot is refused.
_SNAPSHOT_BUSY_TIMEOUT_S = 5.0


class ProfileMigrationRefused(RuntimeError):
    """A profile migration was refused before it changed anything.

    The text is fixed words only: core/auth.py logs ``{e}`` for any failure to
    open a vault, and an OSError's own text carries the file path. The cause is
    deliberately not chained for the same reason. The step and exception class
    go to the log in ``_refuse``.
    """


class _SnapshotInvalid(Exception):
    """A snapshot check failed (nothing path-like in the text, by construction)."""


def _refuse(what: str, step: str, exc: Exception) -> ProfileMigrationRefused:
    """Log once (step and exception class only) and build the refusal to raise."""
    logger.error("Profile migration refused: %s failed at step %s (%s)", what, step, type(exc).__name__)
    return ProfileMigrationRefused(f"Profile migration refused: {what} failed at step {step}")


def _snapshot_paths(vault_path: Path) -> tuple[Path, Path]:
    return vault_path.with_name(_SNAPSHOT_NAME), vault_path.with_name(_SNAPSHOT_TMP_NAME)


def _with_sidecars(path: Path) -> list[Path]:
    return [path] + [path.with_name(path.name + suffix) for suffix in _SNAPSHOT_SIDECARS]


def _unlink_quietly(paths) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass  # best effort on a failure path; the original error is what matters


def _open_keyed(path: Path, hex_key: str, timeout: float = 5.0):
    """Raw DBAPI connection on ``path`` with the vault key set.

    Same rule as the migration engine's connect listener: SQLCipher with
    PRAGMA key and a sqlite_master read when available, stdlib sqlite3
    otherwise.
    """
    if not is_sqlcipher_available():
        return sqlite3.connect(str(path), timeout=timeout)
    conn = get_sqlcipher_module().connect(str(path), timeout=timeout)
    try:
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA cipher_version")
            row = cursor.fetchone()
            if not row or not row[0]:
                if settings.database_encryption_required:
                    raise RuntimeError("SQLCipher is not available but database encryption is required.")
                return conn
            cursor.execute(f"PRAGMA key = \"x'{hex_key}'\"")
            cursor.execute("SELECT count(*) FROM sqlite_master")
            cursor.fetchone()
        finally:
            cursor.close()
    except BaseException:
        conn.close()
        raise
    return conn


def _pre017_snapshot_pending(config: Config, current_revision: Optional[str]) -> bool:
    """True when revision 017 is above ``current_revision`` in the script chain.

    Asks ScriptDirectory rather than comparing with head, so a vault at 017 or
    later (a future 018 included) is never "pending". Unknown revision on
    either side fails closed: take the snapshot.
    """
    if current_revision is None:
        return True
    try:
        script = ScriptDirectory.from_config(config)
        script.get_revision(_SNAPSHOT_REVISION)
        applied = {r.revision for r in script.walk_revisions(base="base", head=current_revision)}
    except Exception:
        return True
    return _SNAPSHOT_REVISION not in applied


def _verify_snapshot(path: Path, hex_key: str) -> None:
    """Raise unless ``path`` opens with the vault key, has tables, and
    PRAGMA quick_check returns exactly one row, ``ok``."""
    conn = _open_keyed(path, hex_key)
    try:
        tables = conn.execute("SELECT count(*) FROM sqlite_master").fetchone()[0]
        rows = [tuple(r) for r in conn.execute("PRAGMA quick_check").fetchall()]
    finally:
        conn.close()
    if not tables:
        raise _SnapshotInvalid("empty database")
    if rows != [("ok",)]:
        raise _SnapshotInvalid("quick_check")


def _checkpoint_wal(vault_path: Path, hex_key: str) -> None:
    """Fold the WAL into the main file so a plain file copy is complete."""
    conn = _open_keyed(vault_path, hex_key, timeout=_SNAPSHOT_BUSY_TIMEOUT_S)
    try:
        busy = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0]
        if busy != 0:
            raise _SnapshotInvalid("checkpoint busy")
        wal = vault_path.with_name(vault_path.name + "-wal")
        if wal.exists() and wal.stat().st_size > 0:
            raise _SnapshotInvalid("wal not empty")
    finally:
        conn.close()


def _fsync_file(path: Path) -> None:
    with open(path, "rb+") as handle:
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_dir(directory: Path) -> None:
    if os.name == "nt":
        return  # Windows cannot open a directory for fsync; nothing to sync there
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _ensure_pre017_snapshot(vault_path: Path, hex_key: str) -> None:
    """Make sure a verified, encrypted copy of the vault exists, or refuse.

    Keep-first: a snapshot that already exists and still verifies is kept, so a
    retry after a failed upgrade cannot replace the pristine copy with a copy of
    a partly cleaned vault. One that does not verify is replaced through the
    temp name. A failed attempt never touches the final name.

    Raises ProfileMigrationRefused on any failure; the vault is untouched.
    """
    snap, tmp = _snapshot_paths(vault_path)
    step = "inspect"
    try:
        if snap.exists():
            step = "verify-existing"
            try:
                _verify_snapshot(snap, hex_key)
                return
            except Exception:
                pass  # does not verify: replace it below
        step = "clear-temp"
        for stale in _with_sidecars(tmp):
            stale.unlink(missing_ok=True)
        step = "checkpoint"
        _checkpoint_wal(vault_path, hex_key)
        step = "copy"
        shutil.copy2(vault_path, tmp)
        step = "sync"
        _fsync_file(tmp)
        step = "verify"
        if tmp.stat().st_size != vault_path.stat().st_size:
            raise _SnapshotInvalid("size")
        _verify_snapshot(tmp, hex_key)
        # copy2 keeps the vault's mtime, which would make a new snapshot look as
        # old as the vault and be purged on the next open. Stamp it now, as UTC:
        # utcnow() is naive, and .timestamp() on a naive value reads it as local.
        step = "stamp-time"
        now = utcnow().replace(tzinfo=UTC).timestamp()
        os.utime(tmp, (now, now))
        step = "publish"
        for stale in _with_sidecars(tmp)[1:] + _with_sidecars(snap)[1:]:
            stale.unlink(missing_ok=True)
        os.replace(tmp, snap)
        step = "sync-dir"
        _fsync_dir(snap.parent)
    except Exception as exc:
        _unlink_quietly(_with_sidecars(tmp))
        raise _refuse("pre-017 snapshot", step, exc) from None
    # No audit row exists for this copy, so this line is the only trace that the
    # retention rule started. WARNING, not INFO: alembic.ini sets root to WARN and
    # nothing raises this logger, so an INFO line never reaches the log in the
    # running app. Event words only: no path, no key.
    logger.warning("Pre-017 snapshot created and verified; it is purged on the first open 30 days or more later")


def purge_pre017_snapshot(vault_path: Path) -> None:
    """Remove the snapshot, its temp copy and their sidecars for one vault.

    Every file is attempted; the first OSError is raised afterwards, so a caller
    that must not leave a copy behind (the synthetic-profile reset) can tell.
    """
    snap, tmp = _snapshot_paths(vault_path)
    first_error: Optional[OSError] = None
    for path in _with_sidecars(snap) + _with_sidecars(tmp):
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            first_error = first_error or exc
    if first_error is not None:
        raise first_error


def _purge_expired_snapshot(vault_path: Path) -> None:
    """Housekeeping at the start of every profile open; never blocks the open.

    A temp copy is an interrupted attempt and goes at any age. The snapshot goes
    once it is 30 days old or more. The age is its own mtime, which
    ``_ensure_pre017_snapshot`` sets to the time it was made.
    """
    snap, tmp = _snapshot_paths(vault_path)
    try:
        for stale in _with_sidecars(tmp):
            stale.unlink(missing_ok=True)
        try:
            made = utcfromtimestamp(snap.stat().st_mtime)
        except FileNotFoundError:
            return
        if utcnow() - made >= _SNAPSHOT_MAX_AGE:
            for old in _with_sidecars(snap):
                old.unlink(missing_ok=True)
            logger.warning("Pre-017 snapshot purged after 30 days")  # WARNING: see _ensure_pre017_snapshot
    except OSError as exc:
        logger.warning("Pre-017 snapshot purge failed (%s)", type(exc).__name__)


# =============================================================================
# Schema match for an unversioned vault (C-P6 / P6-STAMP)
# =============================================================================


def _is_runtime_search_table(name: str) -> bool:
    """``search_records`` and its FTS5 mirror (and the mirror's shadow tables).

    modules/search.py creates them at run time and calls them derived and
    rebuildable, with no migration. A real vault that has used search carries
    them, so they cannot be part of what identifies a revision. Matched by name,
    not as a general tolerance for extra tables.
    """
    return name == "search_records" or name.startswith("search_records_fts")


def _schema_fingerprint(conn) -> tuple:
    """Tables, columns and foreign-key actions of the vault, read-only.

    Columns are (name, upper-cased type, notnull, pk); foreign keys are (from,
    to table, to column, on_delete, on_update). Columns alone are not enough:
    016 and 017 differ only in FK actions. ``alembic_version``, SQLite's own
    tables and the runtime search index are left out, so a stamped and an
    unstamped copy compare equal.
    """
    tables = sorted(
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'"
        ).fetchall()
        if not _is_runtime_search_table(r[0])
    )
    out = []
    for table in tables:
        # table_info: cid, name, type, notnull, dflt_value, pk
        columns = tuple(sorted(
            (str(r[1]), str(r[2] or "").upper(), int(r[3]), int(r[5]))
            for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        ))
        # foreign_key_list: id, seq, table, from, to, on_update, on_delete, match
        fks = tuple(sorted(
            (str(r[3]), str(r[2]), str(r[4]), str(r[6]), str(r[5]))
            for r in conn.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
        ))
        out.append((table, columns, fks))
    return tuple(out)


def _reference_fingerprints() -> list[tuple[str, tuple]]:
    """(revision, fingerprint) for every profile revision, newest first.

    Built by walking a throwaway vault up the chain one revision at a time,
    with its own Alembic config so its ``fk_cleanup_counts`` cannot mix with
    the real vault's. The 017 step logs one INFO ``total=0`` line; that is this
    walk, not the real vault. Costs several seconds, and only on an unversioned
    vault.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
        ref_path = Path(scratch) / "reference.db"
        ref_key = os.urandom(32)
        ref_hex = _key_to_hex(ref_key)
        config = _get_alembic_config("profile")
        config.attributes["vault_path"] = ref_path
        config.attributes["encryption_key"] = ref_key
        revisions = [r.revision for r in ScriptDirectory.from_config(config).walk_revisions()]
        found: list[tuple[str, tuple]] = []
        for revision in reversed(revisions):  # oldest first
            command.upgrade(config, revision)
            conn = _open_keyed(ref_path, ref_hex)
            try:
                found.append((revision, _schema_fingerprint(conn)))
            finally:
                conn.close()
    found.reverse()
    return found


def _match_unversioned_vault(vault_path: Path, hex_key: str) -> str:
    """The newest revision whose schema the vault matches exactly, or refuse.

    Nothing is written. No match is not guessed at: the vault is left as it is.
    """
    step = "read-vault"
    try:
        conn = _open_keyed(vault_path, hex_key)
        try:
            conn.execute("PRAGMA query_only=ON")
            actual = _schema_fingerprint(conn)
        finally:
            conn.close()
        step = "build-references"
        references = _reference_fingerprints()
    except Exception as exc:
        raise _refuse("schema match", step, exc) from None
    for revision, fingerprint in references:  # newest first
        if fingerprint == actual:
            return revision
    logger.error("Profile migration refused: the schema of an unversioned vault matches no known revision")
    raise ProfileMigrationRefused(
        "Profile migration refused: unversioned vault matches no known revision"
    )


# =============================================================================
# Profile Database Migrations (SQLCipher)
# =============================================================================


def run_profile_migration(
    vault_path: Path,
    encryption_key: bytes,
) -> dict[str, int]:
    """
    Run migrations for a profile's encrypted SQLCipher database.

    Args:
        vault_path: Path to the SQLCipher database file
        encryption_key: Raw 32-byte encryption key

    Returns:
        Per-check orphan counts ({check id: n}) that migration 017 cleaned up
        during this call, for the master audit row. Empty when nothing ran or
        nothing was cleaned (P6-CLEANUP-AUDIT).

    Baseline logic:
    - If tables exist but no alembic_version → fingerprint the schema, stamp the
      newest revision it matches exactly, then upgrade to head. A vault that
      matches no revision is refused (ProfileMigrationRefused) and left alone.
    - If no tables → upgrade head (create schema)
    - If alembic_version exists → upgrade head (run pending migrations)

    Snapshot: before revision 017 runs on a non-empty vault, a verified encrypted
    copy is made beside it (``vault.pre017.snapshot``); if that fails, this
    raises ProfileMigrationRefused and changes nothing. On every call, a snapshot
    that is 30 days old or more is purged first.
    """
    logger.info(f"Running profile database migrations for {vault_path}...")

    # Check SQLCipher availability
    if settings.database_encryption_required and not is_sqlcipher_available():
        raise RuntimeError(
            "SQLCipher is required but not available. "
            "Install: pip install sqlcipher3-binary"
        )

    # Ensure vault directory exists
    vault_path.parent.mkdir(parents=True, exist_ok=True)

    # Before anything else, so it also runs for a vault already at head.
    _purge_expired_snapshot(vault_path)

    # Convert key to hex format
    hex_key = _key_to_hex(encryption_key)

    # Expected profile tables for baseline detection
    expected_tables = [
        "documents",
        "observations",
        "chunks",
        "embeddings",
        "lab_interpretations",
        "panel_interpretations",
        "medications",
        "medication_schedules",
        "doses_taken",
        "adherence_patterns",
        "reminder_logs",
        "user_model_settings",
    ]

    # PRAGMA foreign_keys stays OFF on migration engines on purpose: Alembic batch
    # rebuilds need it off (SQL-FK-001). The runtime engines turn it on.
    # Create sync engine with SQLCipher support
    url = f"sqlite:///{vault_path}"
    creator = None

    if is_sqlcipher_available():
        sqlcipher_module = get_sqlcipher_module()

        def _creator():
            return sqlcipher_module.connect(str(vault_path))

        creator = _creator

    # Never pass creator=None; SQLAlchemy treats it as a callable factory.
    if creator is not None:
        engine = create_engine(url, creator=creator)
    else:
        engine = create_engine(url)

    # Set PRAGMA key on connection
    @event.listens_for(engine, "connect")
    def set_cipher_key(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()

        # Check SQLCipher availability
        cursor.execute("PRAGMA cipher_version")
        cipher_version = cursor.fetchone()

        if not cipher_version or not cipher_version[0]:
            if settings.database_encryption_required:
                cursor.close()
                raise RuntimeError(
                    "SQLCipher is not available but database encryption is required."
                )
            cursor.close()
            return

        # Set PRAGMA key
        cursor.execute(f"PRAGMA key = \"x'{hex_key}'\"")

        # Verify key
        try:
            cursor.execute("SELECT count(*) FROM sqlite_master")
        except Exception as e:
            logger.error(f"SQLCipher key verification failed: {e}")
            cursor.close()
            raise

        cursor.close()

    cleanup_counts: dict[str, int] = {}
    try:
        with engine.connect() as connection:
            has_tables, has_alembic_version = _check_baseline_needed(
                connection, expected_tables
            )

            # Configure Alembic with vault path and encryption key
            config = _get_alembic_config("profile")
            config.attributes["vault_path"] = vault_path
            config.attributes["encryption_key"] = encryption_key

            if has_tables and not has_alembic_version:
                # Existing DB without alembic_version. Stamping head would hide
                # every revision the vault does not have (017's FK actions among
                # them), so stamp the newest revision its schema matches exactly
                # and upgrade the rest. No match: refuse, nothing is written.
                matched = _match_unversioned_vault(vault_path, hex_key)
                logger.info(
                    "Profile DB at %s has existing tables but no alembic_version. "
                    "Stamping revision %s to baseline.",
                    vault_path,
                    matched,
                )
                # Snapshot before the stamp, so a refusal leaves no alembic_version.
                if _pre017_snapshot_pending(config, matched):
                    _ensure_pre017_snapshot(vault_path, hex_key)
                command.stamp(config, matched)
                if matched not in set(ScriptDirectory.from_config(config).get_heads()):
                    command.upgrade(config, "head")
                    cleanup_counts = dict(config.attributes.get("fk_cleanup_counts", {}))
                logger.info("Profile database baselined successfully.")
            else:
                current_revision = None
                if has_alembic_version:
                    current_revision = MigrationContext.configure(
                        connection
                    ).get_current_revision()
                    heads = set(ScriptDirectory.from_config(config).get_heads())
                    if current_revision in heads:
                        logger.info(
                            "Profile database at %s already at head revision %s.",
                            vault_path,
                            current_revision,
                        )
                        return cleanup_counts

                # Revision 017 deletes orphan rows: copy a non-empty vault first
                # and refuse the whole migration if the copy cannot be verified.
                if has_tables and _pre017_snapshot_pending(config, current_revision):
                    _ensure_pre017_snapshot(vault_path, hex_key)

                # Either empty DB or has pending migrations: upgrade
                logger.info(
                    "Running profile database upgrade to head for %s from revision %s...",
                    vault_path,
                    current_revision or "<empty>",
                )
                command.upgrade(config, "head")
                logger.info("Profile database migrations completed.")
                # Written by migration 017 (absent when it did not run).
                cleanup_counts = dict(config.attributes.get("fk_cleanup_counts", {}))

    finally:
        engine.dispose()

    return cleanup_counts


async def run_profile_migration_async(
    vault_path: Path,
    encryption_key: bytes,
) -> dict[str, int]:
    """
    Async wrapper for profile migrations.

    Runs blocking Alembic/SQLAlchemy work in a worker thread so the event loop
    stays responsive during vault migrations (profile create/login still waits
    for completion).

    Args:
        vault_path: Path to the SQLCipher database file
        encryption_key: Raw 32-byte encryption key

    Returns:
        The orphan-cleanup counts from run_profile_migration.
    """
    return await asyncio.to_thread(run_profile_migration, vault_path, encryption_key)


# =============================================================================
# Utility Functions
# =============================================================================


def get_master_current_revision() -> Optional[str]:
    """
    Get the current revision of the master database.

    Returns:
        Current revision string or None if not initialized
    """
    sync_url = _get_sync_master_url()
    engine = create_engine(sync_url)

    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return context.get_current_revision()
    finally:
        engine.dispose()


def get_profile_current_revision(
    vault_path: Path,
    encryption_key: bytes,
) -> Optional[str]:
    """
    Get the current revision of a profile database.

    Args:
        vault_path: Path to the SQLCipher database file
        encryption_key: Raw 32-byte encryption key

    Returns:
        Current revision string or None if not initialized
    """
    hex_key = _key_to_hex(encryption_key)
    url = f"sqlite:///{vault_path}"
    creator = None

    if is_sqlcipher_available():
        sqlcipher_module = get_sqlcipher_module()

        def _creator():
            return sqlcipher_module.connect(str(vault_path))

        creator = _creator

    # Never pass creator=None; SQLAlchemy treats it as a callable factory.
    if creator is not None:
        engine = create_engine(url, creator=creator)
    else:
        engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def set_cipher_key(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA cipher_version")
        cipher_version = cursor.fetchone()

        if cipher_version and cipher_version[0]:
            cursor.execute(f"PRAGMA key = \"x'{hex_key}'\"")
            cursor.execute("SELECT count(*) FROM sqlite_master")

        cursor.close()

    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return context.get_current_revision()
    finally:
        engine.dispose()
