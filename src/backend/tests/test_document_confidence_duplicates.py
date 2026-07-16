"""Phase C confidence exposure and duplicate-warning tests."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api import documents as documents_api
from models import Document


PROFILE_A = "profile-a"
PROFILE_B = "profile-b"


def _document(
    profile_id: str,
    *,
    content_hash: str,
    collection_date: datetime | None = None,
    source: str = "existing.pdf",
) -> Document:
    return Document(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        path_hash="p" * 64,
        content_hash=content_hash,
        doc_type="lab_pdf",
        source=source,
        status="parsed",
        collection_date=collection_date,
        imported_at=datetime(2026, 7, 13, 9, 0, 0),
    )


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _ConfidenceDb:
    def __init__(self, observation_rows, entity_rows):
        self._results = iter([_RowsResult(observation_rows), _RowsResult(entity_rows)])

    async def execute(self, _statement):
        return next(self._results)


class _DuplicateResult:
    def __init__(self, document):
        self._document = document

    def scalar_one_or_none(self):
        return self._document


class _DuplicateDb:
    def __init__(self, *documents, error: Exception | None = None):
        self._documents = iter(documents)
        self._error = error

    async def execute(self, _statement):
        if self._error:
            raise self._error
        return _DuplicateResult(next(self._documents, None))


def test_HC_CONF_001_document_response_exposes_zero_confidence():
    doc = _document(PROFILE_A, content_hash="a" * 64)

    response = documents_api.DocumentResponse.from_model(
        doc,
        extraction_confidence=0.0,
    )

    assert response.extraction_confidence == 0.0
    assert response.model_dump()["extraction_confidence"] == 0.0


@pytest.mark.asyncio
async def test_HC_CONF_002_uses_lowest_stored_extraction_confidence():
    doc = _document(PROFILE_A, content_hash="a" * 64)
    profile_db = _ConfidenceDb(
        observation_rows=[(doc.id, 0.85)],
        entity_rows=[(doc.id, 0.35)],
    )

    confidences = await documents_api._document_extraction_confidences(
        profile_db,
        PROFILE_A,
        [doc.id],
    )

    assert confidences == {doc.id: 0.35}


@pytest.mark.asyncio
async def test_HC_DUP_001_exact_hash_match_warns():
    existing = _document(PROFILE_A, content_hash="a" * 64, source="prior.pdf")

    warning = await documents_api._find_duplicate_warning(
        _DuplicateDb(existing),
        PROFILE_A,
        content_hash="a" * 64,
        collection_date=None,
    )

    assert warning is not None
    assert warning.match_type == "content_hash"
    assert warning.document_id == existing.id
    assert warning.title == "prior.pdf"


@pytest.mark.asyncio
async def test_HC_DUP_002_different_content_and_date_does_not_warn():
    warning = await documents_api._find_duplicate_warning(
        _DuplicateDb(None),
        PROFILE_A,
        content_hash="b" * 64,
        collection_date=None,
    )

    assert warning is None


@pytest.mark.asyncio
async def test_HC_DUP_003_same_date_is_secondary_warning():
    collection_date = datetime(2026, 7, 1)
    existing = _document(
        PROFILE_A,
        content_hash="a" * 64,
        collection_date=collection_date,
    )

    warning = await documents_api._find_duplicate_warning(
        _DuplicateDb(None, existing),
        PROFILE_A,
        content_hash="b" * 64,
        collection_date=collection_date,
    )

    assert warning is not None
    assert warning.match_type == "same_date"
    assert warning.document_id == existing.id


@pytest.mark.asyncio
async def test_HC_DUP_004_detection_failure_never_blocks_upload_warning_path():
    warning = await documents_api._find_duplicate_warning(
        _DuplicateDb(error=RuntimeError("database unavailable")),
        PROFILE_A,
        content_hash="a" * 64,
        collection_date=datetime(2026, 7, 1),
    )

    assert warning is None


@pytest.mark.asyncio
async def test_HC_DUP_005_cross_profile_document_does_not_warn():
    other_profile_doc = _document(
        PROFILE_B,
        content_hash="a" * 64,
        collection_date=datetime(2026, 7, 1),
    )

    warning = await documents_api._find_duplicate_warning(
        _DuplicateDb(other_profile_doc, other_profile_doc),
        PROFILE_A,
        content_hash="a" * 64,
        collection_date=datetime(2026, 7, 1),
    )

    assert warning is None


@pytest.mark.asyncio
async def test_HC_CONF_005_rejected_entity_confidence_is_ignored():
    """A low-confidence extraction the user already rejected must not pin
    the document's displayed confidence forever (real per-profile DB)."""
    import pytest  # noqa: F401
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from core.profile_database import ProfileDatabaseBase
    from models.document_category import DocumentEntity

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    db = AsyncSession(engine, expire_on_commit=False)
    try:
        doc = _document(PROFILE_A, content_hash="a" * 64)
        db.add(doc)
        db.add(DocumentEntity(
            id=str(uuid.uuid4()), doc_id=doc.id, category="visit_notes",
            entity_type="medication_change", entity_value="junk",
            confidence=0.1, verified_by_user=False,
        ))
        db.add(DocumentEntity(
            id=str(uuid.uuid4()), doc_id=doc.id, category="visit_notes",
            entity_type="test_ordered", entity_value="repeat cbc",
            confidence=0.9, verified_by_user=None,
        ))
        await db.commit()

        confidences = await documents_api._document_extraction_confidences(
            db, PROFILE_A, [doc.id]
        )
        assert confidences == {doc.id: 0.9}
    finally:
        await db.close()
        await engine.dispose()
