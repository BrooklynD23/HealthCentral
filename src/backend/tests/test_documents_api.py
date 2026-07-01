"""
Tests for document import API behavior.

TDD scaffolding for HC-REM-004:
- Duplicate imports should return 200 (existing document), not 201.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.documents import router as documents_router
from api import documents as documents_api
from core.auth import Session, require_auth, get_profile_db_session
from core.database import get_db
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

    async def execute(self, _stmt):
        self._execute_calls += 1
        if self._execute_calls == 1:
            return _ScalarResult(one=self._existing_doc)
        return _ScalarResult(all_items=[object() for _ in range(self._obs_count)])

    async def commit(self):
        return None

    def add(self, _obj):
        return None


class _FakeMasterDb:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None


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


def test_api_import_dedup_http_001_duplicate_returns_200(monkeypatch):
    """
    API-IMPORT-DEDUP-HTTP-001

    Duplicate import should return 200 with the existing document.
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

    app = FastAPI()
    app.include_router(documents_router, prefix="/documents")

    async def _override_auth():
        return Session(
            profile_id=profile_id,
            profile_name="Test Profile",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    async def _override_profile_db():
        return profile_db

    async def _override_master_db():
        return _FakeMasterDb()

    app.dependency_overrides[require_auth] = _override_auth
    app.dependency_overrides[get_profile_db_session] = _override_profile_db
    app.dependency_overrides[get_db] = _override_master_db

    monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _profile_id: b"x" * 32)
    monkeypatch.setattr(modules, "IngestModule", _FakeIngestModule)

    with TestClient(app) as client:
        response = client.post(
            "/documents/import",
            files={"file": ("duplicate.pdf", b"%PDF-1.4\n%fake\n", "application/pdf")},
        )

    assert response.status_code == 200


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


def test_api_import_dedup_http_002_new_import_returns_201(monkeypatch):
    """
    API-IMPORT-DEDUP-HTTP-002

    New (non-duplicate) import should return 201 with the created document.
    """
    profile_id = str(uuid.uuid4())
    profile_db = _FakeNewImportProfileDb()

    app = FastAPI()
    app.include_router(documents_router, prefix="/documents")

    async def _override_auth():
        return Session(
            profile_id=profile_id,
            profile_name="Test Profile",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    async def _override_profile_db():
        return profile_db

    async def _override_master_db():
        return _FakeMasterDb()

    app.dependency_overrides[require_auth] = _override_auth
    app.dependency_overrides[get_profile_db_session] = _override_profile_db
    app.dependency_overrides[get_db] = _override_master_db

    monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _profile_id: b"x" * 32)
    monkeypatch.setattr(modules, "IngestModule", _FakeIngestModule)

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

    with TestClient(app) as client:
        response = client.post(
            "/documents/import",
            files={"file": ("new_report.pdf", b"%PDF-1.4\n%fake\n", "application/pdf")},
        )

    assert response.status_code == 201


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


def test_hc_documents_101_get_document_creates_view_audit_log():
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

    app = FastAPI()
    app.include_router(documents_router, prefix="/documents")

    async def _override_auth():
        return Session(
            profile_id=profile_id,
            profile_name="Test Profile",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    async def _override_profile_db():
        return profile_db

    async def _override_master_db():
        return master_db

    app.dependency_overrides[require_auth] = _override_auth
    app.dependency_overrides[get_profile_db_session] = _override_profile_db
    app.dependency_overrides[get_db] = _override_master_db

    with TestClient(app) as client:
        response = client.get(f"/documents/{document_id}")

    assert response.status_code == 200
    assert len(master_db.added) == 1
    audit_log = master_db.added[0]
    assert audit_log.event_type == "document.view"
    assert audit_log.entity_id == document_id
    assert audit_log.profile_id == profile_id


def test_hc_documents_102_list_documents_creates_view_audit_log():
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

    app = FastAPI()
    app.include_router(documents_router, prefix="/documents")

    async def _override_auth():
        return Session(
            profile_id=profile_id,
            profile_name="Test Profile",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    async def _override_profile_db():
        return profile_db

    async def _override_master_db():
        return master_db

    app.dependency_overrides[require_auth] = _override_auth
    app.dependency_overrides[get_profile_db_session] = _override_profile_db
    app.dependency_overrides[get_db] = _override_master_db

    with TestClient(app) as client:
        response = client.get("/documents/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert len(master_db.added) == 1
    audit_log = master_db.added[0]
    assert audit_log.event_type == "document.view"
    assert audit_log.profile_id == profile_id
