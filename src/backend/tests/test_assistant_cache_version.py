"""HC-CACHE-VER-001/002 — the agent answer cache's version must change
whenever the evidence behind an answer changes.

`modules/agent/cache.py` keys cached answers on
`(normalized_question, profile_version)` and documents the guarantee as:
"a stale cached explanation of changed data is a correctness bug."

`api/assistant.py::_profile_version` derives that version from a COUNT of
verified observations. A count is not a version: it goes down as well as up,
so a delete followed by a different verify returns to a value the cache has
already seen, and a stale answer is served for data that no longer exists.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from api.assistant import _profile_version
from core.profile_database import ProfileDatabaseBase
from models.document import Document
from models.observation import Observation

PROFILE = "profile-a"
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _add_verified(db: AsyncSession, *, analyte: str, verified_at: datetime) -> Observation:
    obs = Observation(
        id=str(uuid.uuid4()),
        profile_id=PROFILE,
        doc_id="doc-a",
        analyte_canonical=analyte,
        analyte_raw=analyte,
        value=1.0,
        unit="mg/dL",
        collected_at=BASE,
        user_verified=True,
        verified_at=verified_at,
        updated_at=verified_at,
    )
    db.add(obs)
    await db.commit()
    return obs


@pytest.mark.asyncio
async def test_hc_cache_ver_001_delete_then_verify_changes_version(profile_db):
    """Delete one verified observation, verify a different one. The verified
    COUNT returns to its old value, but the underlying evidence is different,
    so the cache version must not repeat."""
    await _add_verified(profile_db, analyte="LDL", verified_at=BASE)
    doomed = await _add_verified(profile_db, analyte="HDL", verified_at=BASE + timedelta(days=1))

    version_before = await _profile_version(PROFILE, profile_db)

    await profile_db.delete(doomed)
    await profile_db.commit()
    await _add_verified(profile_db, analyte="HbA1c", verified_at=BASE + timedelta(days=2))

    version_after = await _profile_version(PROFILE, profile_db)

    assert version_after != version_before, (
        "cache version repeated after a delete + a different verify: a cached "
        f"answer about the deleted observation is still served (both {version_before})"
    )


@pytest.mark.asyncio
async def test_hc_cache_ver_002_deleting_a_verified_observation_changes_version(profile_db):
    """The simpler half: deleting verified evidence must invalidate answers
    that were grounded in it."""
    await _add_verified(profile_db, analyte="LDL", verified_at=BASE)
    doomed = await _add_verified(profile_db, analyte="HDL", verified_at=BASE + timedelta(days=1))

    version_before = await _profile_version(PROFILE, profile_db)

    await profile_db.delete(doomed)
    await profile_db.commit()

    version_after = await _profile_version(PROFILE, profile_db)

    assert version_after != version_before, (
        "cache version unchanged after deleting a verified observation"
    )


async def _add_verified_document(db: AsyncSession, *, doc_id: str, verified_at: datetime) -> Document:
    doc = Document(
        id=doc_id,
        profile_id=PROFILE,
        path_hash="p" * 64,
        content_hash=doc_id.ljust(64, "c"),
        doc_type="lab_report",
        status="verified",
        imported_at=BASE,
        verified_at=verified_at,
    )
    db.add(doc)
    await db.commit()
    return doc


@pytest.mark.asyncio
async def test_hc_cache_ver_003_deleting_a_verified_document_changes_version(profile_db):
    """`retrieve_chunks` serves chunks only from documents with
    `status == "verified"` (tools/retrieve_chunks.py:73), so deleting such a
    document changes what the agent can ground an answer in — even when no
    verified observation count moves."""
    await _add_verified_document(profile_db, doc_id="doc-keep", verified_at=BASE)
    doomed = await _add_verified_document(
        profile_db, doc_id="doc-drop", verified_at=BASE + timedelta(days=1)
    )

    version_before = await _profile_version(PROFILE, profile_db)

    await profile_db.delete(doomed)
    await profile_db.commit()

    version_after = await _profile_version(PROFILE, profile_db)

    assert version_after != version_before, (
        "cache version unchanged after deleting a verified document: answers "
        "grounded in its chunks are still served from cache"
    )
