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
from core.auth import Session
from models import Document
from modules.ingest import ImportResult
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
        imported_at=datetime.utcnow(),
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
        imported_at=datetime.utcnow(),
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
        imported_at=datetime.utcnow(),
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
        imported_at=datetime.utcnow(),
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
        imported_at=datetime.utcnow(),
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
        imported_at=datetime.utcnow(),
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
