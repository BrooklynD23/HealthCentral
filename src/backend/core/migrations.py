"""
Alembic migration utilities with baseline detection.

Provides safe migration execution for:
- Master database (profiles, audit logs, knowledge base)
- Per-profile SQLCipher encrypted vaults

Key features:
- Baseline detection: Existing DBs without alembic_version are stamped (not migrated)
- Startup-safe execution: Alembic calls run synchronously at startup/login gates
- SQLCipher support: Profile migrations use PRAGMA key for encryption
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, inspect, text

from .config import settings
from .sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available

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
# Profile Database Migrations (SQLCipher)
# =============================================================================


def run_profile_migration(
    vault_path: Path,
    encryption_key: bytes,
) -> None:
    """
    Run migrations for a profile's encrypted SQLCipher database.

    Args:
        vault_path: Path to the SQLCipher database file
        encryption_key: Raw 32-byte encryption key

    Baseline logic:
    - If tables exist but no alembic_version → stamp head (don't migrate)
    - If no tables → upgrade head (create schema)
    - If alembic_version exists → upgrade head (run pending migrations)
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
                # Existing DB without alembic_version: stamp head
                logger.info(
                    f"Profile DB at {vault_path} has existing tables but no "
                    "alembic_version. Stamping head to baseline."
                )
                command.stamp(config, "head")
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
                        return

                # Either empty DB or has pending migrations: upgrade
                logger.info(
                    "Running profile database upgrade to head for %s from revision %s...",
                    vault_path,
                    current_revision or "<empty>",
                )
                command.upgrade(config, "head")
                logger.info("Profile database migrations completed.")

    finally:
        engine.dispose()


async def run_profile_migration_async(
    vault_path: Path,
    encryption_key: bytes,
) -> None:
    """
    Async wrapper for profile migrations.

    Runs blocking Alembic/SQLAlchemy work in a worker thread so the event loop
    stays responsive during vault migrations (profile create/login still waits
    for completion).

    Args:
        vault_path: Path to the SQLCipher database file
        encryption_key: Raw 32-byte encryption key
    """
    await asyncio.to_thread(run_profile_migration, vault_path, encryption_key)


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
