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
from modules.ingest import ImportResult as IngestImportResult
from modules.importers.base import (
    ImportResult as ExternalImportResult,
    ImportedObservation,
    ImportError as ExternalImportError,
)
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
    def add(self, _obj):
        return None

    async def commit(self):
        return None


class _FakeIngestModule:
    def __init__(self, *_args, **_kwargs):
        pass

    async def import_document(self, **_kwargs):
        return IngestImportResult(
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


class _FakeExternalImportProfileDb:
    def __init__(self):
        self._added = []
        self.commit_calls = 0

    async def commit(self):
        self.commit_calls += 1

    def add(self, obj):
        self._added.append(obj)


def _build_documents_app(profile_id: str, profile_db):
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
    return app


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


def test_api_import_external_invalid_source_returns_400(monkeypatch):
    profile_id = str(uuid.uuid4())
    app = _build_documents_app(profile_id=profile_id, profile_db=_FakeExternalImportProfileDb())

    def _raise_invalid_source(_source_type):
        raise ValueError("Unknown source type: bad_source")

    monkeypatch.setattr(documents_api, "get_importer", _raise_invalid_source)

    with TestClient(app) as client:
        response = client.post(
            "/documents/import/external?source_type=bad_source",
            files={"file": ("external.csv", b"test,value\nA,1\n", "text/csv")},
        )

    assert response.status_code == 400
    assert "Unknown source type" in response.json()["detail"]


def test_api_import_external_parse_error_returns_400(monkeypatch):
    profile_id = str(uuid.uuid4())
    app = _build_documents_app(profile_id=profile_id, profile_db=_FakeExternalImportProfileDb())

    class _FailingImporter:
        def safe_parse(self, _file_bytes, _filename):
            raise ValueError("Invalid external payload")

    monkeypatch.setattr(documents_api, "get_importer", lambda _source_type: _FailingImporter())

    with TestClient(app) as client:
        response = client.post(
            "/documents/import/external?source_type=generic_csv",
            files={"file": ("external.csv", b"bad,data\n", "text/csv")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid external payload"


def test_api_import_external_oversized_file_returns_413(monkeypatch):
    profile_id = str(uuid.uuid4())
    app = _build_documents_app(profile_id=profile_id, profile_db=_FakeExternalImportProfileDb())
    monkeypatch.setattr(documents_api.settings, "max_import_file_size_mb", 1)

    oversized = b"x" * (1024 * 1024 + 1)

    with TestClient(app) as client:
        response = client.post(
            "/documents/import/external?source_type=generic_csv",
            files={"file": ("external.csv", oversized, "text/csv")},
        )

    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]


class _StructuredImporter:
    max_error_rate = 0.75

    def safe_parse(self, _file_bytes, _filename):
        return ExternalImportResult(
            observations=[
                ImportedObservation(
                    analyte_raw="Glucose",
                    value=95.0,
                    unit="mg/dL",
                    collected_at=datetime(2024, 1, 15),
                )
            ],
            source_metadata={"source": "generic_csv"},
            errors=[
                ExternalImportError(
                    row=2,
                    field="value",
                    message="Value is missing",
                )
            ],
            warnings=["One row skipped"],
        )


def test_api_import_external_returns_structured_validation(monkeypatch):
    profile_id = str(uuid.uuid4())
    app = _build_documents_app(profile_id=profile_id, profile_db=_FakeExternalImportProfileDb())
    monkeypatch.setattr(documents_api, "get_importer", lambda _source_type: _StructuredImporter())

    with TestClient(app) as client:
        response = client.post(
            "/documents/import/external?source_type=generic_csv",
            files={"file": ("external.csv", b"test,value\nA,1\n", "text/csv")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["error_count"] == 1
    assert payload["errors"][0]["field"] == "value"
    assert payload["validation"]["status"] == "warning"
    assert payload["validation"]["max_error_rate"] == _StructuredImporter.max_error_rate


def test_api_import_external_connectors_list_includes_oauth_scaffolds():
    profile_id = str(uuid.uuid4())
    app = _build_documents_app(profile_id=profile_id, profile_db=_FakeExternalImportProfileDb())

    with TestClient(app) as client:
        response = client.get("/documents/import/external/connectors")

    assert response.status_code == 200
    connectors = response.json()["connectors"]
    connector_ids = {item["connector_id"] for item in connectors}
    assert "generic_csv" in connector_ids
    assert "apple_health_portal" in connector_ids


def test_api_import_external_oauth_start_returns_scaffold_contract():
    profile_id = str(uuid.uuid4())
    app = _build_documents_app(profile_id=profile_id, profile_db=_FakeExternalImportProfileDb())

    documents_api._oauth_start_state_store.clear()

    with TestClient(app) as client:
        response = client.post(
            "/documents/import/external/connectors/apple_health_portal/oauth/start"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "scaffold"
    assert "apple_health_portal" in payload["auth_url"]
    assert payload["state"]
    assert payload["state"] in documents_api._oauth_start_state_store


def test_api_import_external_oauth_start_rejects_unapproved_redirect_uri():
    profile_id = str(uuid.uuid4())
    app = _build_documents_app(profile_id=profile_id, profile_db=_FakeExternalImportProfileDb())

    with TestClient(app) as client:
        response = client.post(
            "/documents/import/external/connectors/apple_health_portal/oauth/start"
            "?redirect_uri=https://evil.example/callback"
        )

    assert response.status_code == 400
    assert "allowed callback list" in response.json()["detail"]


def test_api_import_external_oauth_start_accepts_allowlisted_redirect(monkeypatch):
    profile_id = str(uuid.uuid4())
    app = _build_documents_app(profile_id=profile_id, profile_db=_FakeExternalImportProfileDb())
    monkeypatch.setattr(
        documents_api.settings,
        "oauth_redirect_allowlist",
        "https://trusted.example/oauth/callback",
    )

    with TestClient(app) as client:
        response = client.post(
            "/documents/import/external/connectors/apple_health_portal/oauth/start"
            "?redirect_uri=https://trusted.example/oauth/callback"
        )

    assert response.status_code == 200
    payload = response.json()
    assert "redirect_uri=https%3A%2F%2Ftrusted.example%2Foauth%2Fcallback" in payload["auth_url"]
