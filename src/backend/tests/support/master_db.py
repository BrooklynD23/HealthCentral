"""A real, file-backed master DB for route tests (W-11a).

route_client's default master_db is an AsyncMock. That shows an audit helper was
*called*, never that a row was *committed*. These helpers build a SQLite master
DB on disk. The request uses it through a fresh AsyncSession per request, and
the test reads it back through a separate sync connection, which only sees
committed rows.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session as SyncSession
from sqlalchemy.pool import NullPool

from core.database import Base, get_db
from core.time import utcnow
from models import AuditLog, Profile


@dataclass(frozen=True)
class MasterDb:
    path: Path
    maker: async_sessionmaker[AsyncSession]

    def sync_engine(self) -> Engine:
        return create_engine(f"sqlite:///{self.path}", poolclass=NullPool)


def make_master_db(tmp_path: Path) -> MasterDb:
    path = tmp_path / "master.db"
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    engine.dispose()
    # NullPool: every request opens its connection inside TestClient's own loop.
    async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    return MasterDb(path=path, maker=async_sessionmaker(async_engine, expire_on_commit=False))


def seed_profile(db: MasterDb, profile_id: str, display_name: str) -> None:
    now = utcnow()
    with SyncSession(db.sync_engine()) as session:
        session.add(
            Profile(
                id=profile_id,
                display_name=display_name,
                encryption_key_id=f"key-{profile_id}",
                password_hash=None,  # authenticate_profile() then refuses every password
                password_salt=base64.b64encode(b"\x00" * 16).decode("ascii"),
                is_locked=False,
                created_at=now,
                updated_at=now,
                last_accessed_at=None,
            )
        )
        session.commit()


def use_master(client: TestClient, db: MasterDb) -> None:
    async def _session() -> AsyncIterator[AsyncSession]:
        async with db.maker() as session:
            yield session

    client.app.dependency_overrides[get_db] = _session


def audit_rows(db: MasterDb) -> list[AuditLog]:
    with SyncSession(db.sync_engine(), expire_on_commit=False) as session:
        return list(session.scalars(select(AuditLog).order_by(AuditLog.timestamp)))


def profile_row(db: MasterDb, profile_id: str) -> Optional[Profile]:
    with SyncSession(db.sync_engine(), expire_on_commit=False) as session:
        return session.get(Profile, profile_id)
