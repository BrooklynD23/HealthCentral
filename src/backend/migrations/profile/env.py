"""
Alembic environment for per-profile SQLCipher database migrations.

Profile databases contain:
- documents, observations, chunks, embeddings (RAG pipeline)
- lab_interpretations, panel_interpretations (AI interpretations)
- medications, medication_schedules, doses_taken, adherence_patterns, reminder_logs
- user_model_settings

This env.py requires runtime configuration:
- vault_path: Path to the SQLCipher database file
- encryption_key: Raw 32-byte encryption key (hex-encoded for PRAGMA key)

These are passed via context.config.attributes from the migration runner.
"""

import logging
from logging.config import fileConfig

from sqlalchemy import create_engine, event, pool

from alembic import context

# Import profile database base and models to populate metadata
from core.profile_database import ProfileDatabaseBase
from core.config import settings
from core.sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available

# Import all profile models to register them with ProfileDatabaseBase.metadata
from models import (  # noqa: F401
    document,
    observation,
    chunk,
    embedding,
    interpretation,
    medication,
    model_settings,
)

logger = logging.getLogger("alembic.env")

# Alembic Config object
config = context.config

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = ProfileDatabaseBase.metadata


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


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL script without connecting to the database.
    Profile migrations in offline mode won't include PRAGMA key setup.
    """
    # Get vault path from config attributes (set by migration runner)
    vault_path = config.attributes.get("vault_path")
    if not vault_path:
        raise RuntimeError(
            "Profile migrations require vault_path in config.attributes. "
            "Use core.migrations.run_profile_migration() to run profile migrations."
        )

    url = f"sqlite:///{vault_path}"
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode with SQLCipher support.

    Creates a sync engine with SQLCipher PRAGMA key set on connect.
    """
    # Get vault path and encryption key from config attributes
    vault_path = config.attributes.get("vault_path")
    encryption_key = config.attributes.get("encryption_key")

    if not vault_path:
        raise RuntimeError(
            "Profile migrations require vault_path in config.attributes. "
            "Use core.migrations.run_profile_migration() to run profile migrations."
        )

    if not encryption_key:
        raise RuntimeError(
            "Profile migrations require encryption_key in config.attributes. "
            "Use core.migrations.run_profile_migration() to run profile migrations."
        )

    # Check SQLCipher availability
    if settings.database_encryption_required and not is_sqlcipher_available():
        raise RuntimeError(
            "SQLCipher is required but not available. "
            "Install: pip install sqlcipher3-binary"
        )

    # Convert key to hex format for PRAGMA key
    hex_key = _key_to_hex(encryption_key)

    # Build sync database URL
    url = f"sqlite:///{vault_path}"

    # Create engine with SQLCipher module if available
    connect_args = {}
    creator = None

    if is_sqlcipher_available():
        sqlcipher_module = get_sqlcipher_module()

        def _creator():
            """Create connection using SQLCipher module."""
            return sqlcipher_module.connect(str(vault_path))

        creator = _creator

    engine = create_engine(
        url,
        poolclass=pool.NullPool,
        creator=creator,
    )

    # Register event to set PRAGMA key on every connection
    @event.listens_for(engine, "connect")
    def set_cipher_key(dbapi_connection, connection_record):
        """Set SQLCipher PRAGMA key before any operations."""
        cursor = dbapi_connection.cursor()

        # Check if SQLCipher is available
        cursor.execute("PRAGMA cipher_version")
        cipher_version = cursor.fetchone()

        if not cipher_version or not cipher_version[0]:
            if settings.database_encryption_required:
                cursor.close()
                raise RuntimeError(
                    "SQLCipher is not available but database encryption is required."
                )
            else:
                logger.warning(
                    "SQLCipher not available - profile database will be UNENCRYPTED."
                )
                cursor.close()
                return

        logger.debug(f"SQLCipher version: {cipher_version[0]}")

        # Use raw key mode (no PBKDF2 overhead)
        # Format: PRAGMA key = "x'<hex_key>'"
        cursor.execute(f"PRAGMA key = \"x'{hex_key}'\"")

        # Verify the key worked
        try:
            cursor.execute("SELECT count(*) FROM sqlite_master")
        except Exception as e:
            logger.error(f"SQLCipher key verification failed: {e}")
            cursor.close()
            raise

        cursor.close()

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
