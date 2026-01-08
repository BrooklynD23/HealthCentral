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

from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings


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
    Initialize the MASTER database and create tables.

    Phase 3: Only creates Profile and AuditLog tables.
    Per-profile tables are created when a profile is first accessed.
    """
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

    # Import only MASTER database models
    # Profile and AuditLog use Base (master database)
    from models import profile, audit

    # Create master database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


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
