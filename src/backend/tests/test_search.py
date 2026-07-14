"""HC-M21 local cross-record search tests (HC-SRCH-NNN)."""

from __future__ import annotations

import importlib
import asyncio
import sys
import uuid
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.profile_database import ProfileDatabaseBase
from core.auth import Session
from core.time import utcnow
from models import Chunk, Document, DocumentCategory, DocumentEntity, Observation


PROFILE_ID = "search-profile"
DOC_ID = str(uuid.uuid4())
DOC_IMAGING_ID = str(uuid.uuid4())
DOC_LAB_ID = str(uuid.uuid4())


def _document(
    doc_id: str = DOC_ID,
    *,
    source: str = "visit-summary.pdf",
    status: str = "parsed",
    collection_date: datetime | None = datetime(2026, 1, 15, 9, 0),
) -> Document:
    return Document(
        id=doc_id,
        profile_id=PROFILE_ID,
        path_hash="a" * 64,
        content_hash=doc_id.replace("-", "").ljust(64, "0")[:64],
        doc_type="visit_note_pdf",
        source=source,
        status=status,
        collection_date=collection_date,
        imported_at=datetime(2026, 1, 16, 9, 0),
    )


@pytest_asyncio.fixture(autouse=True)
async def _event_loop_ticker():
    """Keep this sandbox's selector ticking so aiosqlite worker callbacks run."""
    async def tick():
        while True:
            await asyncio.sleep(0.01)

    task = asyncio.create_task(tick())
    try:
        yield
    finally:
        task.cancel()


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    session.add(_document())
    session.add(
        _document(
            DOC_IMAGING_ID,
            source="chest-scan.pdf",
            status="verified",
            collection_date=datetime(2025, 5, 20, 8, 0),
        )
    )
    session.add(
        _document(
            DOC_LAB_ID,
            source="lab-panel.pdf",
            collection_date=datetime(2024, 3, 10, 8, 0),
        )
    )
    session.add(
        Chunk(
            id=str(uuid.uuid4()),
            doc_id=DOC_ID,
            chunk_index=0,
            text="The note records a hydration log and follow-up summary.",
        )
    )
    session.add_all(
        [
            DocumentCategory(
                doc_id=DOC_ID,
                category="visit_notes",
                confidence=0.95,
                classified_by="rule",
            ),
            DocumentCategory(
                doc_id=DOC_IMAGING_ID,
                category="imaging",
                confidence=0.95,
                classified_by="rule",
            ),
            DocumentCategory(
                doc_id=DOC_LAB_ID,
                category="lab",
                confidence=0.95,
                classified_by="rule",
            ),
            DocumentEntity(
                doc_id=DOC_ID,
                category="visit_notes",
                entity_type="provider",
                entity_value="Dr Rivera",
                quote="Provider: Dr Rivera",
                confidence=0.95,
                verified_by_user=True,
            ),
            DocumentEntity(
                doc_id=DOC_ID,
                category="visit_notes",
                entity_type="diagnoses",
                entity_value="migraine aura",
                quote="The note says migraine aura was recorded.",
                confidence=0.85,
                verified_by_user=None,
            ),
            DocumentEntity(
                doc_id=DOC_IMAGING_ID,
                category="imaging",
                entity_type="ordering_provider",
                entity_value="Dr Chen",
                quote="Ordering provider: Dr Chen",
                confidence=0.95,
                verified_by_user=True,
            ),
            DocumentEntity(
                doc_id=DOC_IMAGING_ID,
                category="imaging",
                entity_type="finding",
                entity_value="pulmonary nodule",
                quote="The report records a pulmonary nodule.",
                confidence=0.9,
                verified_by_user=True,
            ),
            DocumentEntity(
                doc_id=DOC_IMAGING_ID,
                category="imaging",
                entity_type="finding",
                entity_value="rejected wording",
                quote="Rejected wording",
                confidence=0.8,
                verified_by_user=False,
            ),
            Observation(
                id=str(uuid.uuid4()),
                profile_id=PROFILE_ID,
                doc_id=DOC_ID,
                analyte_canonical="hemoglobin",
                analyte_raw="Hemoglobin",
                value=10.2,
                unit="g/dL",
                collected_at=datetime(2026, 1, 15, 9, 0),
                is_abnormal=False,
                user_verified=True,
            ),
            Observation(
                id=str(uuid.uuid4()),
                profile_id=PROFILE_ID,
                doc_id=DOC_LAB_ID,
                analyte_canonical="glucose",
                analyte_raw="Glucose",
                value=180.0,
                unit="mg/dL",
                collected_at=datetime(2024, 3, 10, 8, 0),
                is_abnormal=True,
                user_verified=False,
            ),
        ]
    )
    await session.commit()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def test_HC_SRCH_001_search_module_declares_runtime_index_api():
    try:
        search = importlib.import_module("modules.search")
    except ModuleNotFoundError:
        pytest.fail("modules.search runtime index is not implemented")

    assert callable(search.ensure_search_index)
    assert callable(search.refresh_search_index)
    assert callable(search.search_records)


@pytest.mark.asyncio
async def test_HC_SRCH_002_index_ensure_and_refresh_are_idempotent(profile_db):
    from modules.search import ensure_search_index, refresh_search_index

    first_mode = await ensure_search_index(profile_db)
    second_mode = await ensure_search_index(profile_db)
    assert first_mode is True
    assert second_mode is True

    await refresh_search_index(profile_db, PROFILE_ID, use_fts=first_mode)
    await refresh_search_index(profile_db, PROFILE_ID, use_fts=first_mode)

    count = await profile_db.scalar(text("SELECT count(*) FROM search_records"))
    assert count == 9  # 3 documents + 4 non-rejected entities + 2 observations


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query,expected_type",
    [
        ("hydration", "document"),
        ("migraine", "entity"),
        ("hemoglobin", "observation"),
    ],
)
async def test_HC_SRCH_003_matches_documents_entities_and_observations(
    profile_db, query, expected_type
):
    from modules.search import search_records

    results = await search_records(profile_db, PROFILE_ID, query)
    assert results
    assert {result.record_type for result in results} == {expected_type}


@pytest.mark.asyncio
async def test_HC_SRCH_004_provider_filter(profile_db):
    from modules.search import search_records

    results = await search_records(
        profile_db, PROFILE_ID, "provider", provider="Dr Chen"
    )
    assert results
    assert {result.doc_id for result in results} == {DOC_IMAGING_ID}


@pytest.mark.asyncio
async def test_HC_SRCH_005_inclusive_date_range_filter(profile_db):
    from modules.search import search_records

    results = await search_records(
        profile_db,
        PROFILE_ID,
        "report",
        date_from=date(2025, 5, 20),
        date_to=date(2025, 5, 20),
    )
    assert results
    assert {result.doc_id for result in results} == {DOC_IMAGING_ID}


@pytest.mark.asyncio
async def test_HC_SRCH_006_category_filter(profile_db):
    from modules.search import search_records

    results = await search_records(
        profile_db, PROFILE_ID, "nodule", category="imaging"
    )
    assert results
    assert all(result.category == "imaging" for result in results)


@pytest.mark.asyncio
async def test_HC_SRCH_007_highlight_type_filter(profile_db):
    from modules.search import search_records

    results = await search_records(
        profile_db,
        PROFILE_ID,
        "glucose",
        highlight_type="abnormal_value",
    )
    assert len(results) == 1
    assert results[0].record_type == "observation"


@pytest.mark.asyncio
async def test_HC_SRCH_008_results_are_bounded(profile_db):
    from modules.search import search_records

    results = await search_records(profile_db, PROFILE_ID, "provider", limit=1)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_HC_SRCH_009_unverified_is_labeled_and_rejected_is_excluded(profile_db):
    from modules.search import search_records

    (unreviewed,) = await search_records(profile_db, PROFILE_ID, "migraine")
    assert unreviewed.verified_status == "unverified"

    rejected = await search_records(profile_db, PROFILE_ID, "rejected")
    assert rejected == []


@pytest.mark.asyncio
async def test_HC_SRCH_010_fts5_failure_selects_like_fallback(profile_db, monkeypatch):
    import modules.search as search

    monkeypatch.setattr(
        search,
        "_create_fts_table",
        AsyncMock(side_effect=OperationalError("fts5 unavailable", {}, Exception())),
    )
    like_spy = AsyncMock(wraps=search._search_like)
    monkeypatch.setattr(search, "_search_like", like_spy)

    results = await search.search_records(profile_db, PROFILE_ID, "hemoglobin")

    assert results
    like_spy.assert_awaited_once()


@pytest.mark.asyncio
async def test_HC_SRCH_011_route_returns_results_and_writes_minimal_audit(
    profile_db, monkeypatch
):
    try:
        import api.search as search_api
    except ModuleNotFoundError:
        pytest.fail("api.search route is not implemented")

    master_db = AsyncMock()
    audit_mock = AsyncMock(return_value=object())
    monkeypatch.setattr(search_api, "create_audit_log", audit_mock)
    session = Session(
        profile_id=PROFILE_ID,
        profile_name="Search Profile",
        expires_at=utcnow(),
    )

    response = await search_api.get_search_results(
        session=session,
        q="migraine",
        provider=None,
        date_from=None,
        date_to=None,
        category="visit_notes",
        highlight_type="needs_verification",
        limit=20,
        profile_db=profile_db,
        master_db=master_db,
    )

    assert response.count == 1
    assert response.results[0].type == "entity"
    assert response.results[0].verified_status == "unverified"
    audit_mock.assert_awaited_once()
    audit_kwargs = audit_mock.await_args.kwargs
    assert audit_kwargs["event_type"] == "search.view"
    assert audit_kwargs["profile_id"] == PROFILE_ID
    assert "migraine" not in str(audit_kwargs["details"])
    master_db.commit.assert_awaited_once()


def test_HC_SRCH_012_route_declares_query_and_limit_bounds():
    try:
        from api.search import get_search_results
    except ModuleNotFoundError:
        pytest.fail("api.search route is not implemented")

    import inspect

    signature = inspect.signature(get_search_results)
    query_default = signature.parameters["q"].default
    limit_default = signature.parameters["limit"].default
    constraints = {
        type(item).__name__: item for item in query_default.metadata + limit_default.metadata
    }
    assert constraints["MinLen"].min_length == 1
    assert constraints["MaxLen"].max_length == 200
    assert constraints["Ge"].ge == 1
    assert constraints["Le"].le <= 100
