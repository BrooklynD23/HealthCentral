"""
Per-profile SQLCipher database management.

Phase 3 Security Architecture:
- Master database: Profile metadata only (list, auth hashes)
- Per-profile databases: SQLCipher-encrypted, isolated data per profile
- Session-bound connections: DB opened on login, closed on logout
- Memory clearing: Keys and connections cleared on lock/logout

This module provides full data isolation between profiles.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, AsyncGenerator
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings
from .security import (
    unseal_key_with_dpapi,
    KeySealingError,
    derive_key_from_password,
)
from .sqlcipher_driver import is_sqlcipher_available, get_sqlcipher_module
from .migrations import run_profile_migration_async

logger = logging.getLogger(__name__)


class ProfileDatabaseEncryptionError(Exception):
    """Raised when profile database encryption is not functional."""
    pass


class ProfileDatabaseBase(DeclarativeBase):
    """SQLAlchemy declarative base for profile-specific models."""
    pass


@dataclass
class ProfileDatabaseConnection:
    """
    Represents an active connection to a profile's encrypted database.

    Holds the async engine, session maker, and encryption key in memory
    for the duration of an active session.
    """
    profile_id: str
    engine: AsyncEngine
    session_maker: async_sessionmaker[AsyncSession]
    _encryption_key: bytes = field(repr=False)  # Sensitive - don't log

    async def close(self) -> None:
        """Close the database connection and clear sensitive data."""
        try:
            await self.engine.dispose()
        except Exception as e:
            logger.warning(f"Error disposing engine for profile {self.profile_id}: {e}")
        finally:
            # Clear the encryption key from memory
            # Note: Python doesn't guarantee memory clearing, but this helps
            self._encryption_key = b'\x00' * len(self._encryption_key)

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session for this profile."""
        async with self.session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


class PerProfileDatabaseManager:
    """
    Manages per-profile encrypted SQLCipher databases.

    Each profile has its own encrypted database file stored in:
    data/vaults/{profile_id}/vault.db

    The encryption key is derived from the profile's sealed key,
    which is unsealed using the user's password during login.

    Thread-safety: This class uses asyncio locks to ensure thread-safe
    access to the connection pool.
    """

    # Singleton instance
    _instance: Optional["PerProfileDatabaseManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls) -> "PerProfileDatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        # Active connections keyed by profile_id
        self._connections: dict[str, ProfileDatabaseConnection] = {}

        # Lock for connection pool access
        self._pool_lock = asyncio.Lock()

        self._initialized = True

    @classmethod
    def get_instance(cls) -> "PerProfileDatabaseManager":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_profile_db_path(self, profile_id: str) -> Path:
        """Get the path to a profile's encrypted database."""
        vault_path = Path(settings.app_data_path) / "vaults" / profile_id
        return vault_path / "vault.db"

    def _get_profile_key_path(self, profile_id: str) -> Path:
        """Get the path to a profile's sealed encryption key."""
        vault_path = Path(settings.app_data_path) / "vaults" / profile_id
        return vault_path / "key.bin"

    def _get_profile_key_method_path(self, profile_id: str) -> Path:
        """Get the path to a profile's key sealing method file."""
        vault_path = Path(settings.app_data_path) / "vaults" / profile_id
        return vault_path / "key.method"

    def get_profile_vault_path(self, profile_id: str) -> Path:
        """Get the directory holding everything belonging to one profile."""
        return Path(settings.app_data_path) / "vaults" / profile_id

    def get_profile_key_paths(self, profile_id: str) -> list[Path]:
        """Every sealed-key artifact for a profile, in deletion order.

        Deleting these files *is* the cryptographic erase (PROF-DEL-001):
        without the sealed key the SQLCipher vault is unreadable even if the
        database file survives. This is the single enumeration of sealed-key
        artifacts — any future feature that seals another copy of the DEK MUST
        add its paths here, or profile deletion will leave a usable key behind.

        (If DEK rotation is ever implemented, it must reseal every copy listed
        here, not just the primary one.)
        """
        return [
            self._get_profile_key_path(profile_id),
            self._get_profile_key_method_path(profile_id),
        ]

    async def _load_encryption_key(
        self,
        profile_id: str,
        password: str,
    ) -> bytes:
        """
        Load and unseal the encryption key for a profile.

        Args:
            profile_id: The profile UUID
            password: The user's password for key derivation

        Returns:
            The raw 32-byte encryption key

        Raises:
            KeySealingError: If the key cannot be unsealed
            FileNotFoundError: If key files don't exist
        """
        key_path = self._get_profile_key_path(profile_id)
        method_path = self._get_profile_key_method_path(profile_id)

        if not key_path.exists():
            raise FileNotFoundError(f"Vault key not found for profile {profile_id}")

        sealed_key = key_path.read_bytes()
        seal_method = method_path.read_text().strip() if method_path.exists() else "password"

        # Unseal the key using the password
        encryption_key = unseal_key_with_dpapi(
            sealed_key,
            seal_method,
            fallback_password=password,
        )

        return encryption_key

    def _key_to_hex(self, key: bytes) -> str:
        """Convert a raw key to hex string for SQLCipher PRAGMA."""
        # SQLCipher expects a 64-character hex string for raw key mode
        # The key should be 32 bytes (256 bits) for AES-256
        import base64

        # If key is base64 encoded (Fernet key format), decode it first
        if len(key) == 44:  # Base64-encoded 32 bytes
            key = base64.urlsafe_b64decode(key)

        if len(key) != 32:
            raise ValueError(f"Encryption key must be 32 bytes, got {len(key)}")

        return key.hex().upper()

    async def open_profile_database(
        self,
        profile_id: str,
        password: str,
    ) -> ProfileDatabaseConnection:
        """
        Open an encrypted database connection for a profile.

        This should be called during login after password verification.
        The connection is cached and reused until the profile is locked/logged out.

        Args:
            profile_id: The profile UUID
            password: The user's password (for key unsealing)

        Returns:
            ProfileDatabaseConnection for the profile

        Raises:
            KeySealingError: If encryption key cannot be unsealed
            FileNotFoundError: If vault doesn't exist
        """
        async with self._pool_lock:
            # Check if connection already exists
            if profile_id in self._connections:
                logger.debug(f"Reusing existing connection for profile {profile_id}")
                return self._connections[profile_id]

            # Load encryption key
            encryption_key = await self._load_encryption_key(profile_id, password)
            hex_key = self._key_to_hex(encryption_key)

            # Get database path
            db_path = self._get_profile_db_path(profile_id)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Patch aiosqlite to use sqlcipher3 if available
            if is_sqlcipher_available():
                import aiosqlite.core
                aiosqlite.core.sqlite3 = get_sqlcipher_module()
                logger.debug("Patched aiosqlite to use sqlcipher3")

            # Create async engine
            # Note: SQLCipher requires setting the key via PRAGMA before any operations
            # We use the aiosqlite driver with a connect event to set the key
            database_url = f"sqlite+aiosqlite:///{db_path}"

            engine = create_async_engine(
                database_url,
                echo=settings.debug,
                future=True,
            )

            # Register event to set encryption key on every new connection
            # This uses raw hex key mode (x'...') to avoid PBKDF2 overhead
            @event.listens_for(engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                """Set SQLCipher PRAGMA key on connection and verify encryption."""
                cursor = dbapi_connection.cursor()

                # Check if SQLCipher is available
                cursor.execute("PRAGMA cipher_version")
                cipher_version = cursor.fetchone()

                if not cipher_version or not cipher_version[0]:
                    # SQLCipher not available - PRAGMA key will be silently ignored
                    if settings.database_encryption_required:
                        cursor.close()
                        raise ProfileDatabaseEncryptionError(
                            "SQLCipher is not available but database encryption is required. "
                            "Install SQLCipher or set DATABASE_ENCRYPTION_REQUIRED=false for development."
                        )
                    else:
                        logger.warning(
                            "SQLCipher not available - profile database will be UNENCRYPTED. "
                            "This is only acceptable in development mode."
                        )
                        cursor.close()
                        return

                logger.debug(f"SQLCipher version: {cipher_version[0]}")

                # Use raw key mode for direct key usage (no PBKDF2)
                # Format: PRAGMA key = "x'<hex_key>'";
                # Note: SQLCipher PRAGMA statements do not reliably support DB-API
                # parameter binding. `hex_key` is derived internally and constrained
                # to 64 uppercase hex chars to avoid injection/format issues.
                if len(hex_key) != 64 or any(c not in "0123456789ABCDEF" for c in hex_key):
                    cursor.close()
                    raise ProfileDatabaseEncryptionError("Invalid SQLCipher key format")
                cursor.execute(f"PRAGMA key = \"x'{hex_key}'\"")
                # Verify the key worked by querying the database
                try:
                    cursor.execute("SELECT count(*) FROM sqlite_master")
                except Exception as e:
                    logger.error(f"SQLCipher key verification failed: {e}")
                    raise
                cursor.close()

            # Create session maker
            session_maker = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Run profile migrations (with baseline detection)
            # This runs in a thread to avoid blocking the event loop
            await run_profile_migration_async(db_path, encryption_key)

            # Create and cache connection
            connection = ProfileDatabaseConnection(
                profile_id=profile_id,
                engine=engine,
                session_maker=session_maker,
                _encryption_key=encryption_key,
            )
            self._connections[profile_id] = connection

            logger.info(f"Opened encrypted database for profile {profile_id}")
            return connection

    async def _init_profile_schema_for_tests(self, engine: AsyncEngine) -> None:
        """
        Initialize the database schema for tests only.

        DEPRECATED: Normal runtime uses Alembic migrations.
        This method is kept for test environments that need quick schema setup
        without running the full migration machinery.

        Creates all tables defined in profile-specific models.
        """
        # Import all profile-specific models to register with ProfileDatabaseBase
        from models import (
            document,
            observation,
            chunk,
            embedding,
            interpretation,  # Lab interpretations
            medication,      # Medication adherence
            model_settings,  # Model tier settings (Phase 0.3)
        )

        async with engine.begin() as conn:
            await conn.run_sync(ProfileDatabaseBase.metadata.create_all)

    async def close_profile_database(self, profile_id: str) -> None:
        """
        Close and clear the database connection for a profile.

        This should be called on logout/lock to ensure:
        - Database connections are properly closed
        - Encryption keys are cleared from memory
        - Cached data is released

        Args:
            profile_id: The profile UUID
        """
        async with self._pool_lock:
            connection = self._connections.pop(profile_id, None)
            if connection:
                await connection.close()
                logger.info(f"Closed database connection for profile {profile_id}")

    async def close_all(self) -> None:
        """Close all active profile database connections."""
        async with self._pool_lock:
            for profile_id in list(self._connections.keys()):
                connection = self._connections.pop(profile_id)
                await connection.close()
            logger.info("Closed all profile database connections")

    def get_connection(self, profile_id: str) -> Optional[ProfileDatabaseConnection]:
        """
        Get an existing database connection for a profile.

        Returns None if no connection exists (profile not logged in).
        Use open_profile_database() to create a new connection.

        Args:
            profile_id: The profile UUID

        Returns:
            ProfileDatabaseConnection if exists, None otherwise
        """
        return self._connections.get(profile_id)

    def is_profile_connected(self, profile_id: str) -> bool:
        """Check if a profile has an active database connection."""
        return profile_id in self._connections

    async def get_profile_session(
        self,
        profile_id: str,
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session for a profile.

        This is a convenience method that gets the connection and yields a session.
        Raises an error if the profile is not connected.

        Args:
            profile_id: The profile UUID

        Yields:
            AsyncSession for the profile's database

        Raises:
            ValueError: If profile is not connected
        """
        connection = self.get_connection(profile_id)
        if not connection:
            raise ValueError(
                f"Profile {profile_id} is not connected. "
                "Login required to access profile data."
            )

        async with connection.get_session() as session:
            yield session


# Global instance accessor
def get_profile_db_manager() -> PerProfileDatabaseManager:
    """Get the per-profile database manager instance."""
    return PerProfileDatabaseManager.get_instance()
