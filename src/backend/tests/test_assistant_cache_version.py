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
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from api.assistant import _profile_version
from core.profile_database import ProfileDatabaseBase
from models import care_plan_task, medication  # noqa: F401  register tables
from models.care_plan_task import CarePlanTask
from models.document import Document
from models.document_category import DocumentCategory, DocumentEntity
from models.medication import Medication
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


# --- HC-CACHE-VER-009..013: every source an agent tool reads is in the key
# (AGENT-CACHE-CARETASKS, owner gate CACHE-STALE (c)).

EMPTY_VERSION = "o:0:|d:0:|t:0:|m:0:|a:0:|e:0:|r:0:"


async def _changed(db: AsyncSession, before: str) -> bool:
    return await _profile_version(PROFILE, db) != before


async def _add_task(db: AsyncSession, *, status: str = "open", quote: str | None = None,
                    doc_id: str | None = None) -> CarePlanTask:
    task = CarePlanTask(
        id=str(uuid.uuid4()), title="Book MRI", status=status,
        source_document_id=doc_id, source_quote=quote,
    )
    db.add(task)
    await db.commit()
    return task


async def _add_unverified_doc(db: AsyncSession, doc_id: str = "doc-u") -> Document:
    doc = Document(
        id=doc_id, profile_id=PROFILE, path_hash="p" * 64, content_hash=doc_id.ljust(64, "c"),
        doc_type="visit_note_pdf", status="parsed", imported_at=BASE,
    )
    db.add(doc)
    await db.commit()
    return doc


@pytest.mark.asyncio
async def test_hc_cache_ver_009_care_task_insert_changes_version(profile_db):
    before = await _profile_version(PROFILE, profile_db)
    await _add_task(profile_db)
    assert await _changed(profile_db, before), "task insert left the cache version unchanged"


@pytest.mark.asyncio
async def test_hc_cache_ver_009_care_task_status_change_changes_version(profile_db):
    task = await _add_task(profile_db)
    before = await _profile_version(PROFILE, profile_db)
    task.status = "done"
    await profile_db.commit()
    assert await _changed(profile_db, before), "marking a task done left the version unchanged"


@pytest.mark.asyncio
async def test_hc_cache_ver_009_core_quote_clear_changes_version(profile_db):
    """api/documents.py:1878-1882 clears provenance with a Core update."""
    doc = await _add_unverified_doc(profile_db)
    await _add_task(profile_db, quote="Schedule MRI of the left knee", doc_id=doc.id)
    before = await _profile_version(PROFILE, profile_db)
    await profile_db.execute(
        update(CarePlanTask)
        .where(CarePlanTask.source_document_id == doc.id)
        .values(source_document_id=None, source_entity_id=None, source_quote=None)
    )
    await profile_db.commit()
    assert await _changed(profile_db, before), "Core quote clear left the version unchanged"


async def _add_med_change(db: AsyncSession, verified) -> DocumentEntity:
    await _add_unverified_doc(db)
    entity = DocumentEntity(
        id=str(uuid.uuid4()), doc_id="doc-u", category="visit_notes",
        entity_type="medication_change", entity_value="Start metformin 500 mg",
        confidence=0.9, quote="Start metformin 500 mg", verified_by_user=verified,
    )
    db.add(entity)
    await db.commit()
    return entity


@pytest.mark.asyncio
async def test_hc_cache_ver_010_verifying_a_medication_change_changes_version(profile_db):
    entity = await _add_med_change(profile_db, None)
    before = await _profile_version(PROFILE, profile_db)
    entity.verified_by_user = True
    await profile_db.commit()
    assert await _changed(profile_db, before)
    # Same row count, different content (a reprocess): only the m: hash sees it.
    verified = await _profile_version(PROFILE, profile_db)
    entity.entity_value = "Start metformin 1000 mg"
    await profile_db.commit()
    assert await _changed(profile_db, verified), "m: hash missed a same-count content change"


@pytest.mark.asyncio
async def test_hc_cache_ver_010_unverifying_a_medication_change_changes_version(profile_db):
    entity = await _add_med_change(profile_db, True)
    before = await _profile_version(PROFILE, profile_db)
    entity.verified_by_user = False
    await profile_db.commit()
    assert await _changed(profile_db, before)


@pytest_asyncio.fixture
async def mixed_db(profile_db):
    """Verified rows plus one unverified document, so the o:/d: parts are
    nonzero and must not be what moves."""
    await _add_verified(profile_db, analyte="LDL", verified_at=BASE)
    await _add_verified_document(profile_db, doc_id="doc-v", verified_at=BASE)
    await _add_unverified_doc(profile_db)
    return profile_db


@pytest.mark.asyncio
async def test_hc_cache_ver_011_unverified_observation_insert_changes_version(mixed_db):
    before = await _profile_version(PROFILE, mixed_db)
    mixed_db.add(Observation(
        id=str(uuid.uuid4()), profile_id=PROFILE, doc_id="doc-u", analyte_canonical="HDL",
        analyte_raw="HDL", value=1.0, unit="mg/dL", collected_at=BASE, user_verified=False,
    ))
    await mixed_db.commit()
    assert await _changed(mixed_db, before)


async def _add_med(db: AsyncSession) -> Medication:
    med = Medication(id=str(uuid.uuid4()), profile_id=PROFILE, name="Atorvastatin", started_at=BASE)
    db.add(med)
    await db.commit()
    return med


@pytest.mark.asyncio
async def test_hc_cache_ver_011_medication_insert_changes_version(mixed_db):
    before = await _profile_version(PROFILE, mixed_db)
    await _add_med(mixed_db)
    assert await _changed(mixed_db, before)


@pytest.mark.asyncio
async def test_hc_cache_ver_011_stopping_a_medication_changes_version(mixed_db):
    med = await _add_med(mixed_db)
    before = await _profile_version(PROFILE, mixed_db)
    med.ended_at = BASE + timedelta(days=3)
    await mixed_db.commit()
    assert await _changed(mixed_db, before)


@pytest.mark.asyncio
async def test_hc_cache_ver_011_classifying_a_document_changes_version(mixed_db):
    before = await _profile_version(PROFILE, mixed_db)
    mixed_db.add(DocumentCategory(
        doc_id="doc-u", category="visit_notes", confidence=1.0, classified_by="t",
    ))
    await mixed_db.commit()
    assert await _changed(mixed_db, before)


@pytest.mark.asyncio
async def test_hc_cache_ver_011_document_collection_date_changes_version(mixed_db):
    mixed_db.add(DocumentCategory(
        doc_id="doc-u", category="visit_notes", confidence=1.0, classified_by="t",
    ))
    await mixed_db.commit()
    before = await _profile_version(PROFILE, mixed_db)
    await mixed_db.execute(
        update(Document).where(Document.id == "doc-u").values(collection_date=BASE)
    )
    await mixed_db.commit()
    assert await _changed(mixed_db, before)


@pytest.mark.asyncio
async def test_hc_cache_ver_012_empty_profile_and_stable_reads(profile_db):
    assert await _profile_version(PROFILE, profile_db) == EMPTY_VERSION
    await _add_verified(profile_db, analyte="LDL", verified_at=BASE)
    await _add_verified_document(profile_db, doc_id="doc-v", verified_at=BASE)
    await _add_unverified_doc(profile_db)
    first = await _profile_version(PROFILE, profile_db)
    second = await _profile_version(PROFILE, profile_db)
    assert first != EMPTY_VERSION
    assert first == second


def test_hc_cache_ver_013_every_registered_tool_is_covered_by_the_key():
    """Tripwire: the owner chose "each future tool must remember the key"."""
    from modules.agent.tools import registry

    covered = {
        "query_observations": "o", "compute_trend": "o", "retrieve_chunks": "d",
        "check_verification": "a", "query_care_tasks": "t",
        "query_medication_changes": "m", "query_timeline": "a,e,r",
        "lookup_reference": "",  # shared knowledge store, no profile data
    }
    assert set(registry._REGISTRY) == set(covered), (
        "the agent tool registry changed: add the new tool's profile data to "
        "api/assistant.py::_profile_version and to this map, or the answer cache "
        "will serve stale answers for it"
    )
