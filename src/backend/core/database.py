"""
Database configuration and session management.

Phase 3 Architecture:
- Master database: Profile metadata, audit logs (uses Base)
- Per-profile databases: Encrypted SQLCipher DBs for sensitive data
  (uses ProfileDatabaseBase from profile_database.py)

Supports:
- SQLite with SQLCipher encryption (local mode)
- PostgreSQL (future server mode)

Uses repository pattern for database abstraction.
"""

import logging
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings
from .sqlcipher_driver import is_sqlcipher_available, verify_cipher_version

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base for MASTER database models.

    Only Profile and AuditLog use this base.
    Document, Observation, Chunk, Embedding use ProfileDatabaseBase.
    """
    pass


# Create async engine based on configuration (master database)
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Session factory for master database
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_database() -> None:
    """
    Initialize the MASTER database directories and verify SQLCipher.

    Phase 3: Schema creation is handled by Alembic migrations.
    This function only:
    - Verifies SQLCipher availability if encryption is required
    - Creates necessary directories (data, logs, vaults)

    Migrations are run separately via run_master_migrations_async()
    in the FastAPI lifespan handler.
    """
    # Verify SQLCipher availability if encryption is required
    if settings.database_encryption_required:
        if not is_sqlcipher_available():
            logger.critical(
                "SQLCipher REQUIRED but not available. "
                "Install: pip install sqlcipher3-binary"
            )
            raise RuntimeError("SQLCipher required but not available")
        version = verify_cipher_version()
        logger.info(f"SQLCipher available: version {version}")

    # Ensure data directory exists (local mode)
    if settings.app_mode == "local":
        data_dir = Path(settings.app_data_path)
        data_dir.mkdir(parents=True, exist_ok=True)

        # Also create logs directory
        logs_dir = Path(settings.log_file_path).parent
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Create vaults directory for per-profile databases
        vaults_dir = data_dir / "vaults"
        vaults_dir.mkdir(parents=True, exist_ok=True)

    # Note: Schema creation removed - now handled by Alembic migrations
    # See core/migrations.py:run_master_migrations()


async def close_database() -> None:
    """Close database connections."""
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.
    
    Usage in FastAPI routes:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
