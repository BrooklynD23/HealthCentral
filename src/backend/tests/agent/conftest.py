"""Shared fixtures for the agent eval suite.

Golden cases are checked-in JSON (docs/agile/EXPLORATION_SUMMARY.md, decided),
loaded from ``tests/agent/golden/``. Each case is a triple: question + synthetic
vault state + expected behavior (skills/healthcentral-evals).

The ``agent_profile_db`` / ``make_run_context`` fixtures below mirror the
in-memory-SQLite pattern used elsewhere in the backend test suite for
``ProfileDatabaseBase`` models (e.g. tests/test_observation_panel_snapshots.py,
tests/test_rag_pipeline.py use fakes/mocks; here we stand up a real async
SQLite engine via ``StaticPool`` so ``query_observations`` exercises a real
``select(...)`` against the ORM, the same shape production code runs).
"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

GOLDEN_DIR = Path(__file__).parent / "golden"


def load_golden_cases() -> list[dict]:
    """Load every golden case JSON file under tests/agent/golden/."""
    cases: list[dict] = []
    for path in sorted(GOLDEN_DIR.glob("*.json")):
        cases.append(json.loads(path.read_text()))
    return cases


@pytest.fixture
def golden_cases() -> list[dict]:
    return load_golden_cases()


@pytest_asyncio.fixture
async def agent_profile_db():
    """An in-memory async SQLite engine + sessionmaker with the profile schema.

    Mirrors ``PerProfileDatabaseManager._init_profile_schema_for_tests``
    (core/profile_database.py) but against an in-memory engine so agent tests
    don't need a real encrypted vault on disk.
    """
    from core.profile_database import ProfileDatabaseBase
    from models import document, observation  # noqa: F401  (register tables)

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    yield session_maker

    await engine.dispose()


async def seed_document(session_maker, *, profile_id: str, doc_id: str | None = None) -> str:
    """Insert a minimal Document row (Observation's required FK) and return its id."""
    from models.document import Document

    doc_id = doc_id or str(uuid.uuid4())
    async with session_maker() as session:
        session.add(
            Document(
                id=doc_id,
                profile_id=profile_id,
                path_hash="hash",
                content_hash="hash",
                doc_type="lab_pdf",
                status="verified",
                imported_at=datetime.utcnow(),
            )
        )
        await session.commit()
    return doc_id


async def seed_observation(
    session_maker,
    *,
    profile_id: str,
    doc_id: str,
    analyte: str,
    value: float,
    unit: str | None = "mg/dL",
    verified: bool,
    collected_at: datetime | None = None,
    observation_id: str | None = None,
) -> str:
    """Insert one Observation row and return its id."""
    from models.observation import Observation

    observation_id = observation_id or str(uuid.uuid4())
    async with session_maker() as session:
        session.add(
            Observation(
                id=observation_id,
                profile_id=profile_id,
                doc_id=doc_id,
                analyte_canonical=analyte,
                analyte_raw=analyte,
                value=value,
                unit=unit,
                collected_at=collected_at or datetime.utcnow(),
                user_verified=verified,
            )
        )
        await session.commit()
    return observation_id


@pytest.fixture
def make_run_context():
    """Factory returning a ``RunContext`` bound to an in-memory session_maker.

    Usage: ``ctx = make_run_context(session_maker, profile_id="p1")``.
    """
    from modules.agent.graph import RunContext, new_run_id

    def _make(session_maker, *, profile_id: str, run_id: str | None = None):
        @asynccontextmanager
        async def _db_session():
            async with session_maker() as session:
                yield session

        return RunContext(
            profile_id=profile_id,
            run_id=run_id or new_run_id(),
            db_session_factory=_db_session,
        )

    return _make
