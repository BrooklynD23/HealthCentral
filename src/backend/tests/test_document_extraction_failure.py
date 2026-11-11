"""HC-EXL-001..005 — raw exception text must not reach logs or the import response.

DOC-EXC-LOGGING (queue: IMPORT-FAILED-REASON + DOCS-VISIT-EXC-LOG; plan
docs/plans/2026-11-07-seven-rows-plan.md). The four exception handlers in
api/documents.py interpolated `{e}`/`{chunk_error}` verbatim; parser and DB
errors can embed paths, tokens and document text. The sites must log only
`type(exc).__name__` (the delete path's precedent, api/documents.py unlink
warning), and the 201 response must carry `extraction_error` as the exception
type name — or null on success — so a failed import says *why* without leaking
the message.
"""

from __future__ import annotations

import io
import logging
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import models  # noqa: F401  register every profile table
import modules
from api import documents as documents_api
from api.documents import router as documents_router
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from core.time import utcnow
from models import Document
from modules.ingest import ImportResult
from tests.support.routes import route_client


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


class _FakeMasterDb:
    """Enough of the master DB for audit rows (add + commit)."""

    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None


class _FakeIngestModule:
    """Ingest stub: accepts the upload, returns a lab_pdf ImportResult."""

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
            metadata={},
            encrypted=True,
        )


def _stub_document_store(monkeypatch, tmp_path):
    """Point the vault path at tmp_path and bypass key/ciphertext access."""
    monkeypatch.setattr(
        type(documents_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _pid: b"x" * 32)
    monkeypatch.setattr(modules, "IngestModule", _FakeIngestModule)
    monkeypatch.setattr(
        documents_api, "get_decrypted_document", lambda _pid, _did: io.BytesIO(b"%PDF")
    )


def _post_import(profile_db, master_db):
    """POST /documents/import over HTTP (route_client) and return the response."""
    with route_client(
        documents_router, "/documents", profile_id="profile-a", master_db=master_db
    ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.post(
            "/documents/import",
            files={"file": ("report.pdf", b"%PDF-1.4\n%fake\n", "application/pdf")},
        )


@pytest.mark.asyncio
async def test_hc_exl_001_import_extraction_failure_returns_type_name_not_message(
    profile_db, monkeypatch, tmp_path, caplog
):
    """HC-EXL-001 (the reported defect + the log redaction, through the route).

    An extraction crash whose message carries a secret must still produce a 201
    with status extraction_failed — the response names only the exception type,
    and the secret never reaches the response body or the logs.
    """
    _stub_document_store(monkeypatch, tmp_path)

    class _FailingExtract:
        async def extract_from_pdf(self, *_args, **_kwargs):
            raise RuntimeError("secret-token-xyz path /tmp/phi-file")

    monkeypatch.setattr(documents_api, "ExtractModule", lambda *a, **k: _FailingExtract())
    monkeypatch.setattr(
        documents_api, "_classify_and_extract_entities", AsyncMock()
    )

    master_db = _FakeMasterDb()
    with caplog.at_level(logging.WARNING):
        resp = _post_import(profile_db, master_db)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["document"]["status"] == "extraction_failed", body["document"]
    assert body["extraction_error"] == "RuntimeError", body
    # The exception message must not surface anywhere the patient or a log
    # reader could see it: neither in the response JSON nor in caplog.
    assert "secret-token-xyz" not in resp.text
    assert "/tmp/phi-file" not in resp.text
    assert "Extraction failed" in caplog.text, (
        "the extraction-failure log sink did not fire; this test would prove nothing"
    )
    assert "RuntimeError" in caplog.text
    assert "secret-token-xyz" not in caplog.text
    assert "/tmp/phi-file" not in caplog.text


@pytest.mark.asyncio
async def test_hc_exl_002_llm_assist_failure_logs_type_name_not_message(
    profile_db, monkeypatch, caplog
):
    """HC-EXL-002: the LLM-assist visit-entity pass logs the exception type only."""
    from api.documents import _classify_and_extract_entities

    visit_text = (
        "PROGRESS NOTE\n\n"
        "Chief Complaint: Follow-up for diabetes management\n"
        "History of Present Illness: Patient returns for 3-month follow-up.\n\n"
        "VITAL SIGNS: BP 128/82, HR 76, Temp 98.4\n"
        "ASSESSMENT: Type 2 DM, well controlled on current regimen.\n"
        "PLAN: Continue metformin 1000mg BID. Recheck A1c in 3 months.\n\n"
        "Provider: Dr. Smith\n"
    )

    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    with patch(
        "api.documents._get_document_text", return_value=visit_text
    ), patch(
        "api.documents.llm_assist_visit_entities",
        AsyncMock(side_effect=RuntimeError("sk-live-key")),
    ), caplog.at_level(logging.WARNING):
        await _classify_and_extract_entities(
            profile_db=mock_db,
            profile_id="test-profile",
            doc_id="test-doc",
            doc_type="lab_pdf",
            llm_assist=True,
        )

    assert "LLM-assist entity pass failed" in caplog.text, (
        "the llm-assist failure sink did not fire; this test would prove nothing"
    )
    assert "RuntimeError" in caplog.text
    assert "sk-live-key" not in caplog.text


@pytest.mark.asyncio
async def test_hc_exl_003_entity_extractor_failure_logs_type_name_not_message(
    profile_db, monkeypatch, caplog
):
    """HC-EXL-003: a category entity extractor's exception message stays out of logs."""
    from api.documents import _classify_and_extract_entities

    imaging_text = (
        "RADIOLOGY REPORT\n"
        "MRI brain without contrast\n"
        "FINDINGS: Normal.\n"
        "IMPRESSION: Normal MRI brain.\n"
    )

    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    with patch(
        "api.documents._get_document_text", return_value=imaging_text
    ), patch.dict(
        "api.documents._CATEGORY_EXTRACTORS",
        {"imaging": MagicMock(side_effect=RuntimeError("path /tmp/x"))},
    ), caplog.at_level(logging.WARNING):
        await _classify_and_extract_entities(
            profile_db=mock_db,
            profile_id="test-profile",
            doc_id="test-doc",
            doc_type="lab_pdf",
        )

    assert "Entity extraction failed" in caplog.text, (
        "the entity-extraction failure sink did not fire; this test would prove nothing"
    )
    assert "RuntimeError" in caplog.text
    assert "path /tmp/x" not in caplog.text


@pytest.mark.asyncio
async def test_hc_exl_004_chunking_failure_keeps_prefix_and_logs_type_name(
    profile_db, monkeypatch, tmp_path, caplog
):
    """HC-EXL-004 (pin): a chunking failure still logs a line starting
    "Chunking failed" — HC-EMB-009c pins the prefix — and now carries only the
    exception type name (absent embedding model -> EmbeddingModelUnavailableError).
    """
    absent_model = tmp_path / "absent-model"
    monkeypatch.setattr(documents_api.settings, "embedding_model_path", str(absent_model))

    profile_id = "profile-a"  # route_client's default session profile_id
    document = Document(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        path_hash="0" * 64,
        content_hash="1" * 64,
        doc_type="lab_pdf",
        source="report.pdf",
        status="parsed",
        page_count=1,
        metadata_json="{}",
        imported_at=utcnow(),
    )
    profile_db.add(document)
    await profile_db.commit()
    doc_id = document.id

    extraction = SimpleNamespace(
        observations=[], extracted_text="LDL 128 mg/dL",
        ocr_unavailable=False, collection_dates=[],
    )
    extract_stub = MagicMock()
    extract_stub.return_value.extract_from_pdf = AsyncMock(return_value=extraction)

    monkeypatch.setattr(documents_api, "get_decrypted_document", lambda *a, **k: "unused.pdf")
    monkeypatch.setattr(documents_api, "ExtractModule", extract_stub)
    monkeypatch.setattr(documents_api, "_classify_and_extract_entities", AsyncMock())

    master_db = _FakeMasterDb()
    with route_client(
        documents_router, "/documents", profile_id=profile_id, master_db=master_db
    ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        with caplog.at_level(logging.WARNING):
            resp = client.post(f"/documents/{doc_id}/reprocess")

    assert resp.status_code == 200, resp.text
    chunk_messages = [
        r.getMessage() for r in caplog.records if r.getMessage().startswith("Chunking failed")
    ]
    assert chunk_messages, (
        "the api/documents.py chunking warning sink did not fire; this test would prove nothing"
    )
    assert any("EmbeddingModelUnavailableError" in m for m in chunk_messages), chunk_messages
    assert "absent-model" not in " ".join(chunk_messages)


@pytest.mark.asyncio
async def test_hc_exl_005_successful_import_has_null_extraction_error(
    profile_db, monkeypatch, tmp_path
):
    """HC-EXL-005 (pin): a successful import carries ``extraction_error: null``."""
    _stub_document_store(monkeypatch, tmp_path)

    extraction = SimpleNamespace(
        observations=[], extracted_text="Glucose 95 mg/dL",
        ocr_unavailable=False, collection_dates=[], pages_without_text=None,
    )
    extract_stub = MagicMock()
    extract_stub.return_value.extract_from_pdf = AsyncMock(return_value=extraction)

    monkeypatch.setattr(documents_api, "ExtractModule", extract_stub)
    monkeypatch.setattr(documents_api, "_create_chunks_and_embeddings", AsyncMock(return_value=0))
    monkeypatch.setattr(documents_api, "_classify_and_extract_entities", AsyncMock())

    resp = _post_import(profile_db, _FakeMasterDb())

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["document"]["status"] == "parsed", body["document"]
    assert body["extraction_error"] is None, body
