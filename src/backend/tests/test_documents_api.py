"""
Tests for document import API behavior.

Phase C duplicate imports are warn-only: a new document is still created.
"""

from __future__ import annotations

import sys
import io
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from fastapi import UploadFile
import pytest

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.documents import router as documents_router
from api import documents as documents_api
from core.auth import Session, get_profile_db_session
from core.time import utcnow
from models import CarePlanTask, Document
from modules.ingest import ImportResult
from tests.support.routes import route_client
import modules


class _ScalarResult:
    def __init__(self, one=None, all_items=None):
        self._one = one
        self._all_items = all_items or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return self

    def all(self):
        return self._all_items


class _FakeProfileDb:
    def __init__(self, existing_doc: Document, obs_count: int = 0):
        self._existing_doc = existing_doc
        self._obs_count = obs_count
        self._execute_calls = 0
        self._added = []

    async def execute(self, _stmt):
        self._execute_calls += 1
        if self._execute_calls == 1:
            return _ScalarResult(one=self._existing_doc)
        return _ScalarResult(all_items=[object() for _ in range(self._obs_count)])

    async def commit(self):
        return None

    def add(self, obj):
        self._added.append(obj)


class _FakeMasterDb:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None


class _FailingMasterDb(_FakeMasterDb):
    async def commit(self):
        raise RuntimeError("audit commit failed")


class _FakeIngestModule:
    def __init__(self, *_args, **_kwargs):
        pass

    async def import_document(self, **_kwargs):
        return ImportResult(
            document_id=str(uuid.uuid4()),
            path_hash="a" * 64,
            content_hash="b" * 64,
            doc_type="lab_pdf",
            page_count=1,
            is_duplicate=False,
            metadata={"original_filename": "duplicate.pdf"},
            encrypted=True,
        )


@pytest.mark.asyncio
async def test_HC_DUP_006_duplicate_returns_201_with_warning(monkeypatch):
    """
    API-IMPORT-DEDUP-HTTP-001

    Exact duplicate content warns but still creates the new document.
    """
    profile_id = str(uuid.uuid4())
    existing_doc = Document(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        path_hash="c" * 64,
        content_hash="b" * 64,  # matches fake ingest content hash
        doc_type="lab_pdf",
        source="existing.pdf",
        status="parsed",
        page_count=1,
        metadata_json="{}",
        imported_at=utcnow(),
    )
    profile_db = _FakeProfileDb(existing_doc=existing_doc, obs_count=2)

    monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _profile_id: b"x" * 32)
    monkeypatch.setattr(modules, "IngestModule", _FakeIngestModule)

    async def _mock_pipeline(**_kwargs):
        return {
            "observations_extracted": 0,
            "needs_verification": True,
            "extracted_text": "",
        }

    async def _mock_classify(**_kwargs):
        return None

    async def _mock_confidences(*_args, **_kwargs):
        return {}

    monkeypatch.setattr(documents_api, "_run_extraction_pipeline", _mock_pipeline)
    monkeypatch.setattr(documents_api, "_classify_and_extract_entities", _mock_classify)
    monkeypatch.setattr(documents_api, "_document_extraction_confidences", _mock_confidences)

    response = await documents_api.import_document(
        session=Session(
            profile_id=profile_id,
            profile_name="Test Profile",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ),
        file=UploadFile(filename="duplicate.pdf", file=io.BytesIO(b"%PDF-1.4\n%fake\n")),
        profile_db=profile_db,
        master_db=_FakeMasterDb(),
    )

    import_route = next(route for route in documents_router.routes if route.path == "/import")
    assert import_route.status_code == 201
    body = response.model_dump(mode="json")
    assert body["document"]["id"] != existing_doc.id
    assert body["duplicate_warning"] == {
        "match_type": "content_hash",
        "document_id": existing_doc.id,
        "title": "existing.pdf",
    }
    assert len(profile_db._added) == 1


class _FakeNewImportProfileDb:
    """Profile DB that returns no existing doc (new import scenario)."""

    def __init__(self):
        self._added = []
        self._execute_calls = 0

    async def execute(self, _stmt):
        self._execute_calls += 1
        return _ScalarResult(one=None)

    async def commit(self):
        return None

    def add(self, obj):
        self._added.append(obj)


@pytest.mark.asyncio
async def test_api_import_dedup_http_002_new_import_returns_201(monkeypatch):
    """
    API-IMPORT-DEDUP-HTTP-002

    New (non-duplicate) import should return 201 with the created document.
    """
    profile_id = str(uuid.uuid4())
    profile_db = _FakeNewImportProfileDb()

    monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _profile_id: b"x" * 32)
    monkeypatch.setattr(modules, "IngestModule", _FakeIngestModule)

    async def _mock_pipeline(**_kwargs):
        return {
            "observations_extracted": 0,
            "needs_verification": True,
            "extracted_text": "",
        }

    async def _mock_classify(**_kwargs):
        return None

    async def _mock_confidences(*_args, **_kwargs):
        return {}

    monkeypatch.setattr(documents_api, "_run_extraction_pipeline", _mock_pipeline)
    monkeypatch.setattr(documents_api, "_classify_and_extract_entities", _mock_classify)
    monkeypatch.setattr(documents_api, "_document_extraction_confidences", _mock_confidences)

    # Mock decrypted doc + extraction to avoid real PDF processing
    mock_extraction = MagicMock()
    mock_extraction.observations = []
    mock_extraction.collection_dates = []

    async def _mock_extract_from_pdf(*_args, **_kwargs):
        return mock_extraction

    monkeypatch.setattr(
        "modules.extract.ExtractModule.extract_from_pdf",
        _mock_extract_from_pdf,
    )
    monkeypatch.setattr(
        documents_api,
        "get_decrypted_document",
        lambda _pid, _did: b"fake-pdf",
    )

    response = await documents_api.import_document(
        session=Session(
            profile_id=profile_id,
            profile_name="Test Profile",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ),
        file=UploadFile(filename="new_report.pdf", file=io.BytesIO(b"%PDF-1.4\n%fake\n")),
        profile_db=profile_db,
        master_db=_FakeMasterDb(),
    )

    assert response.duplicate_warning is None


def test_document_text_pages_split_helper_handles_ocr_formfeed():
    """OCR text should split into per-page segments for chunking/page preview."""
    text = "page one text\fpage two text\f\n\fpage three"
    pages = documents_api._split_extracted_text_pages(text)
    assert pages == ["page one text", "page two text", "page three"]


class _FakeSingleDocProfileDb:
    """Profile DB that returns a single fixed document for any query."""

    def __init__(self, document: Document):
        self._document = document

    async def execute(self, _stmt):
        return _ScalarResult(one=self._document)


@pytest.mark.asyncio
async def test_hc_documents_101_get_document_creates_view_audit_log():
    """
    HC-DOCUMENTS-101

    GET /documents/{document_id} must write a 'document.view' AuditLog row
    to the master database (audit logging on every route that touches
    documents, per CLAUDE.md).
    """
    profile_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())
    document = Document(
        id=document_id,
        profile_id=profile_id,
        path_hash="d" * 64,
        content_hash="e" * 64,
        doc_type="lab_pdf",
        source="report.pdf",
        status="parsed",
        page_count=1,
        metadata_json="{}",
        imported_at=utcnow(),
    )
    profile_db = _FakeSingleDocProfileDb(document)
    master_db = _FakeMasterDb()

    response = await documents_api.get_document(
        document_id=document_id,
        session=Session(
            profile_id=profile_id,
            profile_name="Test Profile",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ),
        profile_db=profile_db,
        master_db=master_db,
    )

    assert response.id == document_id
    assert len(master_db.added) == 1
    audit_log = master_db.added[0]
    assert audit_log.event_type == "document.view"
    assert audit_log.entity_id == document_id
    assert audit_log.profile_id == profile_id


@pytest.mark.asyncio
async def test_hc_documents_103_get_document_fails_closed_on_audit_failure():
    """
    HC-DOCUMENTS-103

    GET /documents/{document_id} must fail closed if the audit commit fails.
    """
    profile_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())
    document = Document(
        id=document_id,
        profile_id=profile_id,
        path_hash="d" * 64,
        content_hash="e" * 64,
        doc_type="lab_pdf",
        source="report.pdf",
        status="parsed",
        page_count=1,
        metadata_json="{}",
        imported_at=utcnow(),
    )
    profile_db = _FakeSingleDocProfileDb(document)
    master_db = _FailingMasterDb()

    with pytest.raises(RuntimeError):
        await documents_api.get_document(
            document_id=document_id,
            session=Session(
                profile_id=profile_id,
                profile_name="Test Profile",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            ),
            profile_db=profile_db,
            master_db=master_db,
        )

    assert len(master_db.added) == 1


@pytest.mark.asyncio
async def test_hc_documents_104_list_documents_fails_closed_on_audit_failure(monkeypatch):
    """
    HC-DOCUMENTS-104

    GET /documents/ must fail closed if the audit commit fails.
    """
    profile_id = str(uuid.uuid4())
    document = Document(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        path_hash="f" * 64,
        content_hash="a" * 64,
        doc_type="lab_pdf",
        source="report2.pdf",
        status="parsed",
        page_count=1,
        metadata_json="{}",
        imported_at=utcnow(),
    )

    class _FakeListProfileDb:
        async def execute(self, _stmt):
            return _ScalarResult(all_items=[document])

    profile_db = _FakeListProfileDb()
    master_db = _FailingMasterDb()

    monkeypatch.setattr(
        documents_api,
        "_document_extraction_confidences",
        AsyncMock(return_value={}),
    )
    with pytest.raises(RuntimeError):
        await documents_api.list_documents(
            session=Session(
                profile_id=profile_id,
                profile_name="Test Profile",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            ),
            doc_status=None,
            doc_type=None,
            profile_db=profile_db,
            master_db=master_db,
        )

    assert len(master_db.added) == 1


@pytest.mark.asyncio
async def test_hc_documents_102_list_documents_creates_view_audit_log(monkeypatch):
    """
    HC-DOCUMENTS-102

    GET /documents/ must write a single 'document.view' AuditLog row
    (once per request, not once per item) to the master database.
    """
    profile_id = str(uuid.uuid4())
    document = Document(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        path_hash="f" * 64,
        content_hash="a" * 64,
        doc_type="lab_pdf",
        source="report2.pdf",
        status="parsed",
        page_count=1,
        metadata_json="{}",
        imported_at=utcnow(),
    )

    class _FakeListProfileDb:
        async def execute(self, _stmt):
            return _ScalarResult(all_items=[document])

    profile_db = _FakeListProfileDb()
    master_db = _FakeMasterDb()

    monkeypatch.setattr(
        documents_api,
        "_document_extraction_confidences",
        AsyncMock(return_value={}),
    )
    response = await documents_api.list_documents(
        session=Session(
            profile_id=profile_id,
            profile_name="Test Profile",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ),
        doc_status=None,
        doc_type=None,
        profile_db=profile_db,
        master_db=master_db,
    )

    assert len(response) == 1
    assert len(master_db.added) == 1
    audit_log = master_db.added[0]
    assert audit_log.event_type == "document.view"
    assert audit_log.profile_id == profile_id


def _pin_cleanup_document(profile_id: str, *, doc_type: str = "visit_note_pdf") -> Document:
    return Document(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        path_hash="d" * 64,
        content_hash="e" * 64,
        doc_type=doc_type,
        source="cleanup.pdf",
        status="parsed",
        page_count=1,
        metadata_json="{}",
        imported_at=utcnow(),
    )


@pytest.mark.asyncio
async def test_HC_PIN_011_document_delete_prunes_pin_targets_before_commit(
    monkeypatch,
):
    profile_id = str(uuid.uuid4())
    document = _pin_cleanup_document(profile_id)
    profile_db = AsyncMock()
    profile_db.execute.return_value = _ScalarResult(one=document)
    cleanup = AsyncMock()
    monkeypatch.setattr(documents_api, "_prune_document_pin_targets", cleanup)
    monkeypatch.setattr(documents_api, "log_document_event", AsyncMock())

    await documents_api.delete_document(
        document.id,
        Session(
            profile_id=profile_id,
            profile_name="Test Profile",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ),
        profile_db,
        AsyncMock(),
    )

    cleanup.assert_awaited_once_with(
        profile_db, document.id, include_document=True
    )
    profile_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_HC_PIN_012_reprocess_prunes_recreated_targets_before_extraction(
    monkeypatch,
):
    profile_id = str(uuid.uuid4())
    document = _pin_cleanup_document(profile_id)
    profile_db = AsyncMock()
    profile_db.execute.return_value = _ScalarResult(one=document)
    call_order = []

    async def cleanup(*_args, **_kwargs):
        call_order.append("cleanup")

    async def pipeline(**_kwargs):
        call_order.append("pipeline")
        return {
            "observations_extracted": 0,
            "needs_verification": True,
            "extracted_text": "",
        }

    monkeypatch.setattr(documents_api, "_prune_document_pin_targets", cleanup)
    monkeypatch.setattr(documents_api, "_run_extraction_pipeline", pipeline)
    monkeypatch.setattr(
        documents_api, "_classify_and_extract_entities", AsyncMock()
    )
    monkeypatch.setattr(documents_api, "log_document_event", AsyncMock())

    await documents_api.reprocess_document(
        document.id,
        Session(
            profile_id=profile_id,
            profile_name="Test Profile",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ),
        False,
        profile_db,
        AsyncMock(),
    )

    assert call_order == ["cleanup", "pipeline"]
    profile_db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Entity lifecycle on delete/reprocess (real per-profile DB)
# ---------------------------------------------------------------------------

import pytest_asyncio  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from core.profile_database import ProfileDatabaseBase  # noqa: E402
from models.document_category import DocumentCategory, DocumentEntity  # noqa: E402


@pytest_asyncio.fixture
async def entity_profile_db():
    from models import Pinboard, PinboardItem  # noqa: F401 -- register tables

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _entity_row(
    doc_id: str,
    *,
    entity_type: str = "medication_change",
    quote: str = "Start metoprolol 25 mg",
    verified: bool | None = None,
) -> DocumentEntity:
    return DocumentEntity(
        id=str(uuid.uuid4()),
        doc_id=doc_id,
        category="visit_notes",
        entity_type=entity_type,
        entity_value=quote.lower(),
        confidence=0.8,
        quote=quote,
        verified_by_user=verified,
    )


def _real_db_session(profile_id: str) -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="Test Profile",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )


@pytest.mark.asyncio
async def test_HC_ENT_030_delete_document_removes_entities_and_categories(
    entity_profile_db, monkeypatch
):
    """Deleting a document must delete its extracted entities/categories:
    entity quotes carry verbatim document text and must not remain
    exportable after the document is gone."""
    profile_id = str(uuid.uuid4())
    document = _pin_cleanup_document(profile_id)
    entity_profile_db.add(document)
    entity_profile_db.add(_entity_row(document.id, verified=True))
    entity_profile_db.add(DocumentCategory(
        id=str(uuid.uuid4()),
        doc_id=document.id,
        category="visit_notes",
        confidence=0.9,
        classified_by="rule",
    ))
    await entity_profile_db.commit()
    monkeypatch.setattr(documents_api, "log_document_event", AsyncMock())

    await documents_api.delete_document(
        document.id,
        _real_db_session(profile_id),
        entity_profile_db,
        AsyncMock(),
    )

    remaining_entities = await entity_profile_db.execute(
        select(DocumentEntity).where(DocumentEntity.doc_id == document.id)
    )
    assert remaining_entities.scalars().all() == []
    remaining_categories = await entity_profile_db.execute(
        select(DocumentCategory).where(DocumentCategory.doc_id == document.id)
    )
    assert remaining_categories.scalars().all() == []


def _care_task(
    doc_id: str,
    entity_id: str | None = None,
    *,
    quote: str = "Repeat CBC in 4 weeks",
) -> CarePlanTask:
    return CarePlanTask(
        id=str(uuid.uuid4()),
        title="Repeat CBC",
        status="open",
        source_document_id=doc_id,
        source_entity_id=entity_id,
        source_quote=quote,
        user_note="ask about the iron result",
    )


@pytest.mark.asyncio
async def test_HC_CAREQ_001_delete_document_clears_care_task_quote_and_provenance(
    entity_profile_db, monkeypatch
):
    """CARE-QUOTE-001. `source_quote` is verbatim clinician text, held to the
    same standard as the entity quotes deleted directly above: it must not
    outlive the document it was taken from.

    The task itself survives — a follow-up the patient still has to do does not
    stop being real because they deleted the PDF — but its provenance and its
    verbatim text go with the document."""
    profile_id = str(uuid.uuid4())
    document = _pin_cleanup_document(profile_id)
    entity = _entity_row(document.id, quote="Repeat CBC in 4 weeks")
    entity_profile_db.add(document)
    entity_profile_db.add(entity)
    entity_profile_db.add(_care_task(document.id, entity.id))
    await entity_profile_db.commit()
    monkeypatch.setattr(documents_api, "log_document_event", AsyncMock())

    await documents_api.delete_document(
        document.id,
        _real_db_session(profile_id),
        entity_profile_db,
        AsyncMock(),
    )

    result = await entity_profile_db.execute(select(CarePlanTask))
    tasks = result.scalars().all()

    assert len(tasks) == 1, "the follow-up itself must survive the document"
    task = tasks[0]
    assert task.source_quote is None, (
        "verbatim clinician text outlived the deleted document"
    )
    assert task.source_document_id is None
    assert task.source_entity_id is None


@pytest.mark.asyncio
async def test_HC_CAREQ_002_delete_document_preserves_the_rest_of_the_task(
    entity_profile_db, monkeypatch
):
    """The cleanup is surgical: only provenance and the verbatim quote are
    cleared. Title, status and the user's own note are the patient's data, not
    the document's, and must be untouched."""
    profile_id = str(uuid.uuid4())
    document = _pin_cleanup_document(profile_id)
    entity_profile_db.add(document)
    entity_profile_db.add(_care_task(document.id))
    await entity_profile_db.commit()
    monkeypatch.setattr(documents_api, "log_document_event", AsyncMock())

    await documents_api.delete_document(
        document.id,
        _real_db_session(profile_id),
        entity_profile_db,
        AsyncMock(),
    )

    result = await entity_profile_db.execute(select(CarePlanTask))
    task = result.scalars().one()
    assert task.title == "Repeat CBC"
    assert task.status == "open"
    assert task.user_note == "ask about the iron result"


@pytest.mark.asyncio
async def test_HC_CAREQ_003_delete_document_leaves_other_documents_tasks_alone(
    entity_profile_db, monkeypatch
):
    """Scoping guard. The clearing UPDATE must key on the document being
    deleted — a broad `UPDATE care_plan_task SET source_quote=NULL` would pass
    HC-CAREQ-001 while silently stripping every other document's tasks."""
    profile_id = str(uuid.uuid4())
    doomed = _pin_cleanup_document(profile_id)
    survivor = _pin_cleanup_document(profile_id)
    entity_profile_db.add(doomed)
    entity_profile_db.add(survivor)
    entity_profile_db.add(_care_task(doomed.id))
    entity_profile_db.add(_care_task(survivor.id, quote="Book eye exam"))
    await entity_profile_db.commit()
    monkeypatch.setattr(documents_api, "log_document_event", AsyncMock())

    await documents_api.delete_document(
        doomed.id,
        _real_db_session(profile_id),
        entity_profile_db,
        AsyncMock(),
    )

    result = await entity_profile_db.execute(
        select(CarePlanTask).where(CarePlanTask.source_document_id == survivor.id)
    )
    kept = result.scalars().one()
    assert kept.source_quote == "Book eye exam"
    assert kept.source_document_id == survivor.id


class _CommitTrackingMasterDb(_FakeMasterDb):
    """`_FakeMasterDb` records adds but not commits, so a route that adds an
    AuditLog row and then silently skips `await master_db.commit()` is
    invisible to a plain "was a row added" assertion (review loop 1,
    mutation M3 survived). Record how many rows existed at each commit call
    so a test can assert a specific row was actually committed."""

    def __init__(self) -> None:
        super().__init__()
        self.commit_snapshots: list[int] = []

    async def commit(self) -> None:
        self.commit_snapshots.append(len(self.added))


@pytest.mark.asyncio
async def test_HC_CAREQ_004_delete_document_over_http_clears_care_task_quote(
    entity_profile_db, monkeypatch, tmp_path
):
    """P1-CAREQ-HTTP. HC-CAREQ-001..003 above call `delete_document` directly
    as a plain function with `log_document_event` monkeypatched out — that
    cannot see a broken `Depends(...)` and never exercises the real audit
    write (CLAUDE.md: "a test that calls a route function directly cannot
    see a broken Depends(...)"). Drive the same DELETE over HTTP through
    `route_client` with a real in-memory profile DB and a recording master
    DB, so the FastAPI dependency graph and the CARE-QUOTE-001 audit path
    both run for real."""
    # Nothing should be written under the repo or a real data dir: point the
    # vault path the route touches at pytest's tmp_path.
    monkeypatch.setattr(
        type(documents_api.settings), "app_data_path", property(lambda self: tmp_path)
    )

    profile_id = "profile-a"  # matches route_client's default session profile_id
    document = _pin_cleanup_document(profile_id)
    task = _care_task(document.id)
    entity_profile_db.add(document)
    entity_profile_db.add(task)
    await entity_profile_db.commit()

    master = _CommitTrackingMasterDb()
    with route_client(
        documents_router, "/documents", profile_id=profile_id, master_db=master
    ) as client:

        async def _override_profile_db():
            return entity_profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        resp = client.delete(f"/documents/{document.id}")
        assert 200 <= resp.status_code < 300, resp.text

    # entity_profile_db has expire_on_commit=False, so without this the
    # select below would return the identity-mapped Python object rather
    # than what the route actually committed to the database.
    entity_profile_db.expire_all()

    result = await entity_profile_db.execute(select(CarePlanTask))
    tasks = result.scalars().all()
    assert len(tasks) == 1, "the follow-up itself must survive the document"
    kept = tasks[0]
    assert kept.source_document_id is None
    assert kept.source_entity_id is None
    assert kept.source_quote is None, "verbatim clinician text outlived the deleted document"
    assert kept.title == "Repeat CBC"
    assert kept.status == "open"
    assert kept.user_note == "ask about the iron result"

    audit_rows_with_index = [
        (i, o) for i, o in enumerate(master.added) if type(o).__name__ == "AuditLog"
    ]
    assert audit_rows_with_index, "DELETE /documents/{id} over HTTP wrote no AuditLog row"
    audit_index, row = audit_rows_with_index[0]
    assert row.event_type == "document.delete"
    assert row.entity_type == "document"
    assert row.entity_id == document.id
    assert row.profile_id == profile_id

    # AUDIT-PHI-001 / core/audit.py log_document_event docstring: "filename
    # is accepted for call-site compatibility and is never persisted" — the
    # real filename ("cleanup.pdf", set by _pin_cleanup_document) must not
    # appear anywhere in the committed row.
    row_blob = " ".join(str(getattr(row, c.name)) for c in row.__table__.columns)
    assert document.source not in row_blob, f"filename leaked into audit row: {row_blob}"

    # The route must have committed the master DB, and specifically after
    # the AuditLog row was added — not merely `.add()`-ed and left pending.
    assert len(master.commit_snapshots) == 1, (
        f"expected exactly one master DB commit, got {master.commit_snapshots}"
    )
    assert master.commit_snapshots[0] > audit_index, (
        "AuditLog row was added but the master DB commit that should follow "
        "it never happened"
    )


@pytest.mark.asyncio
async def test_HC_ENT_031_reprocess_reapplies_rejections_by_quote(
    entity_profile_db, monkeypatch
):
    """A user's explicit rejection of an extraction is a safety decision;
    reprocess recreating the same (entity_type, quote) under a new UUID
    must not silently resurface the rejected content as unreviewed."""
    profile_id = str(uuid.uuid4())
    document = _pin_cleanup_document(profile_id)
    entity_profile_db.add(document)
    entity_profile_db.add(
        _entity_row(document.id, quote="Stop aspirin", verified=False)
    )
    await entity_profile_db.commit()

    async def pipeline(**_kwargs):
        return {
            "observations_extracted": 0,
            "needs_verification": True,
            "extracted_text": "",
        }

    async def classify(**_kwargs):
        # Simulate extraction recreating the same span under a new UUID,
        # plus a genuinely new extraction.
        entity_profile_db.add(
            _entity_row(document.id, quote="Stop aspirin", verified=None)
        )
        entity_profile_db.add(_entity_row(
            document.id, entity_type="test_ordered",
            quote="Repeat CBC", verified=None,
        ))

    monkeypatch.setattr(documents_api, "_run_extraction_pipeline", pipeline)
    monkeypatch.setattr(documents_api, "_classify_and_extract_entities", classify)
    monkeypatch.setattr(documents_api, "log_document_event", AsyncMock())

    await documents_api.reprocess_document(
        document.id,
        _real_db_session(profile_id),
        False,
        entity_profile_db,
        AsyncMock(),
    )

    rows = (await entity_profile_db.execute(
        select(DocumentEntity).where(DocumentEntity.doc_id == document.id)
    )).scalars().all()
    by_quote = {row.quote: row.verified_by_user for row in rows}
    assert by_quote == {"Stop aspirin": False, "Repeat CBC": None}


# ---------------------------------------------------------------------------
# DOC-DELETE-INTERP (plan docs/plans/2026-10-04-DDI-doc-delete-interpretation.md)
# ---------------------------------------------------------------------------

from sqlalchemy import func  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from models import LabInterpretation, Observation  # noqa: E402


def _ddi_observation(profile_id: str, doc_id: str) -> Observation:
    return Observation(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        doc_id=doc_id,
        analyte_canonical="hemoglobin",
        analyte_raw="Hgb",
        value=14.2,
    )


def _ddi_interpretation(profile_id: str, observation_id: str) -> LabInterpretation:
    # Built by FK only, exactly as modules/interpret.py:254 and :1010 do.
    return LabInterpretation(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        observation_id=observation_id,
        interpretation_text="DDI interpretation text",
        severity_level="normal",
        citations_json="[]",
        model_id="template",
        model_tier="template",
        confidence_score=0.85,
    )


def _ddi_vault_file(tmp_path: Path, profile_id: str, document_id: str) -> Path:
    docs = tmp_path / "vaults" / profile_id / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    path = docs / f"{document_id}.bin"
    path.write_bytes(b"ciphertext")
    return path


async def _ddi_count(db, model, *where) -> int:
    stmt = select(func.count()).select_from(model)
    for clause in where:
        stmt = stmt.where(clause)
    return (await db.execute(stmt)).scalar_one()


def _ddi_delete_over_http(profile_db, master, document_id: str, profile_id: str):
    with route_client(
        documents_router, "/documents", profile_id=profile_id, master_db=master
    ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.delete(f"/documents/{document_id}")


@pytest.mark.asyncio
async def test_HC_DDI_001_delete_document_with_interpretation_over_http(
    entity_profile_db, monkeypatch, tmp_path
):
    """HC-DDI-001. A document whose observation has a LabInterpretation must
    delete over HTTP: 2xx, document/observation/interpretation rows gone, the
    encrypted file gone, one committed document.delete audit row. Another
    document's interpretation must survive."""
    monkeypatch.setattr(
        type(documents_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    profile_id = "profile-a"
    document = _pin_cleanup_document(profile_id)
    other = _pin_cleanup_document(profile_id)
    obs = _ddi_observation(profile_id, document.id)
    other_obs = _ddi_observation(profile_id, other.id)
    entity_profile_db.add_all([document, other, obs, other_obs])
    await entity_profile_db.commit()
    entity_profile_db.add_all([
        _ddi_interpretation(profile_id, obs.id),
        _ddi_interpretation(profile_id, other_obs.id),
    ])
    await entity_profile_db.commit()
    # Plain strings: after expire_all() an ORM attribute read would lazy-load
    # synchronously and raise MissingGreenlet under AsyncSession.
    doc_id, obs_id, other_obs_id = document.id, obs.id, other_obs.id
    vault_file = _ddi_vault_file(tmp_path, profile_id, doc_id)

    master = _CommitTrackingMasterDb()
    resp = _ddi_delete_over_http(entity_profile_db, master, doc_id, profile_id)
    assert 200 <= resp.status_code < 300, resp.text

    entity_profile_db.expire_all()
    assert await _ddi_count(entity_profile_db, Document, Document.id == doc_id) == 0
    assert await _ddi_count(entity_profile_db, Observation, Observation.doc_id == doc_id) == 0
    assert await _ddi_count(
        entity_profile_db, LabInterpretation, LabInterpretation.observation_id == obs_id
    ) == 0, "interpretation outlived its observation"
    assert await _ddi_count(
        entity_profile_db, LabInterpretation, LabInterpretation.observation_id == other_obs_id
    ) == 1, "another document's interpretation was deleted"
    assert not vault_file.exists(), "encrypted file survived a successful delete"

    audit = [o for o in master.added if type(o).__name__ == "AuditLog"]
    assert len(audit) == 1 and audit[0].event_type == "document.delete"
    assert audit[0].entity_id == doc_id
    assert master.commit_snapshots and master.commit_snapshots[-1] >= 1


@pytest.mark.asyncio
async def test_HC_DDI_002_failed_commit_keeps_encrypted_file(
    entity_profile_db, monkeypatch, tmp_path
):
    """HC-DDI-002. If the profile-DB commit fails, the encrypted file must
    still be on disk, the document row must survive, and no audit row may be
    written. Today the file is unlinked before the commit."""
    monkeypatch.setattr(
        type(documents_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    profile_id = "profile-a"
    document = _pin_cleanup_document(profile_id)
    entity_profile_db.add(document)
    await entity_profile_db.commit()
    doc_id = document.id  # plain string; rollback() expires the ORM object
    vault_file = _ddi_vault_file(tmp_path, profile_id, doc_id)

    async def _failing_commit():
        raise OperationalError("COMMIT", {}, Exception("simulated disk I/O error"))

    monkeypatch.setattr(entity_profile_db, "commit", _failing_commit)
    master = _CommitTrackingMasterDb()
    with pytest.raises(OperationalError):
        _ddi_delete_over_http(entity_profile_db, master, doc_id, profile_id)

    monkeypatch.undo()  # restores commit and app_data_path
    await entity_profile_db.rollback()
    assert vault_file.exists(), "encrypted file destroyed although the commit failed"
    assert await _ddi_count(entity_profile_db, Document, Document.id == doc_id) == 1
    assert not [o for o in master.added if type(o).__name__ == "AuditLog"]


@pytest.mark.asyncio
async def test_HC_DDI_003_unlink_failure_after_commit_still_audits(
    entity_profile_db, monkeypatch, tmp_path
):
    """HC-DDI-003. If the rows are committed but the file cannot be removed
    (Windows lock, permissions), the request still succeeds, the audit row is
    written, and the log line carries neither the path nor the filename."""
    monkeypatch.setattr(
        type(documents_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    profile_id = "profile-a"
    document = _pin_cleanup_document(profile_id)
    entity_profile_db.add(document)
    await entity_profile_db.commit()
    doc_id, doc_source = document.id, document.source  # plain strings (expire_all below)
    vault_file = _ddi_vault_file(tmp_path, profile_id, doc_id)

    def _locked_unlink(self, *args, **kwargs):
        raise PermissionError(13, "locked", str(self))

    monkeypatch.setattr(Path, "unlink", _locked_unlink)
    warnings: list[str] = []
    monkeypatch.setattr(
        documents_api.logger, "warning",
        lambda msg, *a, **k: warnings.append(msg % a if a else msg),
    )
    master = _CommitTrackingMasterDb()
    resp = _ddi_delete_over_http(entity_profile_db, master, doc_id, profile_id)
    assert 200 <= resp.status_code < 300, resp.text

    entity_profile_db.expire_all()
    assert await _ddi_count(entity_profile_db, Document, Document.id == doc_id) == 0
    assert vault_file.exists()  # unlink was blocked
    audit = [o for o in master.added if type(o).__name__ == "AuditLog"]
    assert len(audit) == 1 and audit[0].event_type == "document.delete"
    assert warnings, "a failed unlink after commit must be logged"
    joined = " ".join(warnings)
    assert str(tmp_path) not in joined and doc_source not in joined


@pytest.mark.asyncio
async def test_HC_DDI_004_interpretation_created_by_fk_still_flushes(entity_profile_db):
    """HC-DDI-004. modules/interpret.py builds LabInterpretation with
    observation_id only. The cascade added for DDI must not make such an
    object an orphan on flush."""
    profile_id = "profile-a"
    document = _pin_cleanup_document(profile_id)
    obs = _ddi_observation(profile_id, document.id)
    entity_profile_db.add_all([document, obs])
    await entity_profile_db.commit()
    obs_id = obs.id  # plain string (expire_all below)
    entity_profile_db.add(_ddi_interpretation(profile_id, obs_id))
    await entity_profile_db.commit()
    entity_profile_db.expire_all()
    assert await _ddi_count(
        entity_profile_db, LabInterpretation, LabInterpretation.observation_id == obs_id
    ) == 1
    # And the ORM delete of the observation now reaches it.
    loaded = (await entity_profile_db.execute(
        select(Observation).where(Observation.id == obs_id)
    )).scalar_one()
    await entity_profile_db.delete(loaded)
    await entity_profile_db.commit()
    assert await _ddi_count(
        entity_profile_db, LabInterpretation, LabInterpretation.observation_id == obs_id
    ) == 0
