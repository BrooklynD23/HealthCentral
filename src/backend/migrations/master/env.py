"""
Alembic environment for master database migrations.

Master database contains:
- profiles (user accounts)
- audit_logs (HIPAA-compliant audit trail)
- biomarker_knowledge, intervention_mappings, biomarker_relationships (knowledge base)

This env.py is used for both offline (SQL generation) and online (direct DB) modes.
"""

import logging
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool, text

from alembic import context

# Import master database base and models to populate metadata
from core.database import Base
from core.config import settings

# Import all master models to register them with Base.metadata
from models import profile, audit, knowledge_base  # noqa: F401

logger = logging.getLogger("alembic.env")

# Alembic Config object
config = context.config

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def get_sync_url() -> str:
    """
    Convert async database URL to sync URL for Alembic.

    settings.database_url returns: sqlite+aiosqlite:///data/healthcentral.db
    We need: sqlite:///data/healthcentral.db
    """
    async_url = settings.database_url
    # Replace aiosqlite with plain sqlite driver
    sync_url = async_url.replace("sqlite+aiosqlite://", "sqlite://")
    return sync_url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL script without connecting to the database.
    """
    url = get_sync_url()
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
    Run migrations in 'online' mode.

    Creates an engine and runs migrations directly against the database.
    """
    # Ensure data directory exists
    if settings.app_mode == "local":
        data_dir = Path(settings.app_data_path)
        data_dir.mkdir(parents=True, exist_ok=True)

    # Build configuration for engine
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_sync_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
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
