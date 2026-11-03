"""Shared test-engine factory with production FK enforcement (SQL-FK-001)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from core.database import install_sqlite_foreign_keys


def fk_profile_engine() -> AsyncEngine:
    """In-memory profile-vault engine with ``PRAGMA foreign_keys=ON``.

    Plain ``create_async_engine("sqlite+aiosqlite://")`` leaves the pragma OFF,
    so an ``ondelete=`` is inert and a test passes against a schema the app no
    longer runs. Use this when the assertion depends on FK actions.

    Trap: ``create_all`` leaves ``badge_definition`` empty, so the first logged
    dose in a consumer's test fails the badge FK. Seed it as
    ``test_medications_routes_http.py`` does.
    """
    engine = create_async_engine("sqlite+aiosqlite://")
    install_sqlite_foreign_keys(engine.sync_engine)
    return engine
