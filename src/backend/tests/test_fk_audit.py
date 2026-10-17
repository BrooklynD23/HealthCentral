"""HC-FKA: report-only orphan detection for every declared + logical FK."""
import pytest
import pytest_asyncio
from sqlalchemy import ForeignKey, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import models  # noqa: F401  registers every model on both metadatas
import models.response_feedback  # noqa: F401  not exported by models/__init__
from core.profile_database import ProfileDatabaseBase
from core.fk_audit import (
    LOGICAL_CHECKS,
    MASTER_CHECKS,
    PROFILE_CHECKS,
    find_orphans,
)


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


@pytest.mark.asyncio
async def test_hc_fka_001_clean_vault_has_no_orphans(profile_db):
    findings = await find_orphans(profile_db, PROFILE_CHECKS + LOGICAL_CHECKS)
    assert findings == []


@pytest.mark.asyncio
async def test_hc_fka_002_finds_seeded_orphan(profile_db):
    """FKs are off in test engines, so a dangling child can be inserted raw."""
    await profile_db.execute(text(
        "INSERT INTO embeddings (id, chunk_id, model_name, vector_blob, "
        "dimensions, created_at) VALUES ('e1', 'ghost-chunk', 'm', x'00', 3, datetime('now'))"
    ))
    await profile_db.commit()
    findings = await find_orphans(profile_db, PROFILE_CHECKS)
    hit = [f for f in findings if f.check_id == "P3"]
    assert len(hit) == 1 and hit[0].count == 1 and hit[0].sample_ids == ["e1"]


@pytest.mark.asyncio
async def test_hc_fka_003_logical_checks_flagged_not_enforced(profile_db):
    await profile_db.execute(text(
        "INSERT INTO response_feedback (id, profile_id, session_id, turn_id, "
        "rating, created_at, updated_at) VALUES ('f1', 'p', 'ghost-session', "
        "'ghost-turn', 1, datetime('now'), datetime('now'))"
    ))
    await profile_db.commit()
    findings = await find_orphans(profile_db, LOGICAL_CHECKS)
    assert {f.check_id for f in findings} == {"L1", "L2"}
    assert all(f.enforced is False for f in findings)


def _declared(metadata):
    return {
        (fk.parent.table.name, fk.parent.name, fk.column.table.name, fk.column.name)
        for t in metadata.tables.values()
        for fk in t.foreign_keys
    }


def _listed(checks):
    return {
        (c.child_table, c.child_column, c.parent_table, c.parent_column)
        for c in checks
    }


def test_hc_fka_004_every_declared_fk_has_a_check():
    from core.database import Base

    missing = [
        ("profile", fk)
        for fk in sorted(_declared(ProfileDatabaseBase.metadata) - _listed(PROFILE_CHECKS))
    ] + [
        ("master", fk)
        for fk in sorted(_declared(Base.metadata) - _listed(MASTER_CHECKS))
    ]
    assert not missing, f"declared FK(s) with no audit check: {missing}"
