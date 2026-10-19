"""HC-EMB-005..008 — what fail-closed means on each retrieval/ingest surface.

Owner decisions D8 + D8-delivery (2026-09-27): runtime "fails closed if
absent". The patient-visible form (existing knowledge-fallback template on
legacy chat; existing 501 on grounded interpretation) is owner-gated as Q-FC in
docs/plans/2026-09-27-W08-bundled-embedding-model.md.
"""

from __future__ import annotations

import struct
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import models  # noqa: F401  register every profile table
from core.profile_database import ProfileDatabaseBase
from core.time import utcnow
from models import Chunk, Document, Embedding

UNIT = [1.0] + [0.0] * 383
BLOB = struct.pack("384f", *UNIT)
# Patient-visible 501 detail, copied VERBATIM from the signed Q-FC line in
# docs/plans/2026-09-27-W08-bundled-embedding-model.md. Deliberately a literal,
# not modules.rag.EMBEDDING_UNAVAILABLE_MESSAGE: a wording change in product code
# must fail this test. Change it only when a new Q-FC line is signed.
QFC_APPROVED_DETAIL = "Document search is unavailable because the local embedding model is not installed."


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest.fixture
def absent_model(tmp_path, monkeypatch):
    from core.config import settings

    path = tmp_path / "absent-model"
    monkeypatch.setattr(settings, "embedding_model_path", str(path))
    return path


def _document(profile_id: str = "profile-emb") -> Document:
    return Document(
        id=str(uuid.uuid4()), profile_id=profile_id, path_hash="0" * 64, content_hash="1" * 64,
        doc_type="pdf", status="verified", imported_at=utcnow(),
    )


async def _seed_one_chunk(profile_db, profile_id: str = "profile-emb") -> Document:
    doc = _document(profile_id)
    profile_db.add_all([
        doc,
        Chunk(id="chunk-1", doc_id=doc.id, chunk_index=0, text="LDL 128 mg/dL"),
        Embedding(chunk_id="chunk-1", model_name="all-MiniLM-L6-v2", vector_blob=BLOB, dimensions=384),
    ])
    await profile_db.commit()
    return doc


class _SentinelRunner:
    def __init__(self):
        self.calls = 0

    def is_available(self):
        return True

    async def generate_async(self, prompt, config):
        self.calls += 1
        return SimpleNamespace(text="ANSWER-SENTINEL from retrieval", finish_reason="stop")


@pytest.mark.asyncio
async def test_hc_emb_005_legacy_chat_fails_closed_over_http(profile_db, absent_model, monkeypatch):
    import api.assistant as assistant_api
    from api.assistant import router as assistant_router
    from core.auth import get_profile_db_session
    from tests.support.routes import route_client

    profile_id = str(uuid.uuid4())
    await _seed_one_chunk(profile_db, profile_id)
    runner = _SentinelRunner()
    monkeypatch.setattr("core.external_runner.get_runner_for_request", AsyncMock(return_value=runner))
    monkeypatch.setattr(assistant_api, "is_agent_enabled", lambda _settings: False)
    monkeypatch.setattr(assistant_api, "_rag_module", None)

    with route_client(assistant_router, "/assistant", profile_id=profile_id) as client:
        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        resp = client.post("/assistant/chat", json={"question": "What is my LDL?", "include_references": False})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert runner.calls == 0, "the LLM answered from retrieval that ran without the bundled embedding model"
    assert "ANSWER-SENTINEL" not in body["full_response"]
    assert body["verification"]["enabled"] is False  # existing knowledge-fallback shape


@pytest.mark.asyncio
async def test_hc_emb_006a_retrieval_raises_model_unavailable_without_path(profile_db, absent_model):
    from modules.rag import ModelUnavailableError, RAGModule

    doc = await _seed_one_chunk(profile_db)
    rag = RAGModule(enable_verification=False)
    with pytest.raises(ModelUnavailableError) as info:
        await rag._search_vectors_async(query="LDL", profile_id=doc.profile_id, profile_db=profile_db)
    message = str(info.value)
    assert "embedding model" in message.lower()
    # api/interpretations.py returns this text as a 501 detail to the patient.
    assert str(absent_model) not in message


@pytest.mark.asyncio
async def test_hc_emb_006b_empty_profile_needs_no_embedding(profile_db, absent_model):
    from modules.rag import RAGModule

    rag = RAGModule(enable_verification=False)
    assert await rag._search_vectors_async(query="LDL", profile_id="p", profile_db=profile_db) == []


@pytest.mark.asyncio
async def test_hc_emb_006c_grounded_interpretation_returns_501_over_http(profile_db, absent_model, monkeypatch):
    """POST /interpretations/observations/{id}/interpret-grounded, through HTTP.

    The route maps ModelUnavailableError to 501 and returns str(exc) as the
    detail (api/interpretations.py:453-457 B@7b2ff1f), so the patient sees this
    text. The wording itself is owner-gated (Q-FC). The interpret module is
    stubbed: this test is about retrieval, and interpret.py sits beside the
    ask-first interpret_safety.py.
    """
    import api.assistant as assistant_api
    import api.interpretations as interpretations_api
    from api.interpretations import router as interpretations_router
    from core.auth import get_profile_db_session
    from models import Observation
    from tests.support.routes import route_client

    profile_id = str(uuid.uuid4())
    doc = await _seed_one_chunk(profile_db, profile_id)
    obs_id = str(uuid.uuid4())  # the route validates UUID format
    profile_db.add(Observation(
        id=obs_id, profile_id=profile_id, doc_id=doc.id, analyte_canonical="ldl",
        analyte_raw="LDL", value=128.0, unit="mg/dL", user_verified=True,
    ))
    await profile_db.commit()

    runner = _SentinelRunner()
    monkeypatch.setattr("core.external_runner.get_runner_for_request", AsyncMock(return_value=runner))
    monkeypatch.setattr(assistant_api, "_rag_module", None)  # get_rag_module is shared with the chat route
    stub = SimpleNamespace(interpret_observation=AsyncMock(
        return_value=SimpleNamespace(success=True, interpretation=SimpleNamespace(), error_message=None)
    ))
    monkeypatch.setattr(interpretations_api, "get_interpret_module", lambda: stub)

    master_db = AsyncMock()
    master_db.add = MagicMock()  # AuditLog rows land here; a bare AsyncMock would hide a dropped row
    with route_client(interpretations_router, "/interpretations", profile_id=profile_id, master_db=master_db) as client:
        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        resp = client.post(f"/interpretations/observations/{obs_id}/interpret-grounded")

    assert resp.status_code == 501, resp.text
    detail = resp.json()["detail"]
    assert detail == QFC_APPROVED_DETAIL  # exact owner-approved wording (Q-FC), not the product constant
    assert str(absent_model) not in detail
    assert runner.calls == 0, "the LLM answered from retrieval that ran without the bundled embedding model"
    # The grounded route audits before rag.query, so the 501 path must still leave the row.
    audit_rows = [c.args[0] for c in master_db.add.call_args_list]
    assert [r.entity_id for r in audit_rows] == [obs_id]


@pytest.mark.asyncio
async def test_hc_emb_007_reprocess_keeps_chunks_when_embedding_unavailable(profile_db, absent_model):
    from api import documents as documents_api
    from modules.embeddings import EmbeddingModelUnavailableError

    doc = await _seed_one_chunk(profile_db)
    with pytest.raises(EmbeddingModelUnavailableError):
        await documents_api._create_chunks_and_embeddings(
            profile_db=profile_db, profile_id=doc.profile_id, doc_id=doc.id,
            extracted_text="Glucose 96 mg/dL (70-100)\fLDL 128 mg/dL", refresh_existing=True,
        )
    # Order-of-effects test: the pipeline caller swallows this error and then
    # COMMITS (api/documents.py `except Exception as chunk_error` then
    # `await profile_db.commit()`). Assert on committed state, not on the
    # session's pending state: commit, then read through a fresh query.
    await profile_db.commit()
    profile_db.expunge_all()
    ids = (await profile_db.execute(select(Chunk.id).where(Chunk.doc_id == doc.id))).scalars().all()
    assert ids == ["chunk-1"], "reprocess deleted the previous chunks although no replacement embeddings could be made"


def _stub_embedding_blob_failure(monkeypatch):
    """Embedding succeeds, then the vector-to-blob step raises (after the old delete on the buggy order)."""
    from modules.embeddings import EmbeddingsModule

    def _embed(self, chunks):
        return [{"model_name": "all-MiniLM-L6-v2", "vector": UNIT, "dimensions": 384} for _ in chunks]

    def _raise(self, vector):
        raise ValueError("blob conversion failed")

    monkeypatch.setattr(EmbeddingsModule, "embed_chunks", _embed)
    monkeypatch.setattr(EmbeddingsModule, "vector_to_blob", _raise)


async def _committed_chunk_state(profile_db, doc_id):
    await profile_db.commit()
    profile_db.expunge_all()
    ids = (await profile_db.execute(select(Chunk.id).where(Chunk.doc_id == doc_id))).scalars().all()
    emb = (await profile_db.execute(select(Embedding.chunk_id))).scalars().all()
    return ids, emb


@pytest.mark.asyncio
async def test_hc_emb_007b_reprocess_keeps_chunks_when_row_build_fails(profile_db, monkeypatch):
    from api import documents as documents_api

    doc = await _seed_one_chunk(profile_db)
    _stub_embedding_blob_failure(monkeypatch)
    with pytest.raises(ValueError):
        await documents_api._create_chunks_and_embeddings(
            profile_db=profile_db, profile_id=doc.profile_id, doc_id=doc.id,
            extracted_text="LDL 128 mg/dL", refresh_existing=True,
        )
    ids, emb = await _committed_chunk_state(profile_db, doc.id)
    assert ids == ["chunk-1"], "old chunks were deleted before the replacement rows were built"
    assert emb == ["chunk-1"], "chunk-1 lost its embedding"


@pytest.mark.asyncio
async def test_hc_emb_007c_reprocess_route_keeps_chunks_when_row_build_fails(profile_db, monkeypatch):
    from api import documents as documents_api
    from api.documents import router as documents_router
    from core.auth import get_profile_db_session
    from tests.support.routes import route_client

    profile_id = str(uuid.uuid4())
    doc = _document(profile_id)
    doc.doc_type = "lab_pdf"
    profile_db.add_all([
        doc,
        Chunk(id="chunk-1", doc_id=doc.id, chunk_index=0, text="LDL 128 mg/dL"),
        Embedding(chunk_id="chunk-1", model_name="all-MiniLM-L6-v2", vector_blob=BLOB, dimensions=384),
    ])
    await profile_db.commit()
    doc_id = doc.id

    extraction = SimpleNamespace(
        observations=[], extracted_text="LDL 128 mg/dL", ocr_unavailable=False, collection_dates=[]
    )
    extract_stub = MagicMock()
    extract_stub.return_value.extract_from_pdf = AsyncMock(return_value=extraction)

    async def _classify(profile_db, doc_id, **kw):
        return None

    monkeypatch.setattr(documents_api, "get_decrypted_document", lambda *a, **k: "unused.pdf")
    monkeypatch.setattr(documents_api, "ExtractModule", extract_stub)
    monkeypatch.setattr(documents_api, "_classify_and_extract_entities", _classify)
    _stub_embedding_blob_failure(monkeypatch)

    master_db = AsyncMock()
    master_db.add = MagicMock()
    with route_client(documents_router, "/documents", profile_id=profile_id, master_db=master_db) as client:
        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        resp = client.post(f"/documents/{doc_id}/reprocess")

    assert resp.status_code == 200, resp.text
    ids, emb = await _committed_chunk_state(profile_db, doc_id)
    assert ids == ["chunk-1"], "the caller committed a half-built reprocess"
    assert emb == ["chunk-1"]


@pytest.mark.asyncio
async def test_hc_emb_008_vector_search_ignores_vectors_from_another_model(profile_db):
    from modules.embeddings import EmbeddingsModule
    from modules.rag import RAGModule

    class _FixedEmbedder(EmbeddingsModule):
        def embed_text(self, text):
            return UNIT

    doc = _document()
    profile_db.add_all([
        doc,
        Chunk(id="chunk-real", doc_id=doc.id, chunk_index=0, text="LDL 128 mg/dL"),
        Chunk(id="chunk-hash", doc_id=doc.id, chunk_index=1, text="LDL 128 mg/dL"),
        Embedding(chunk_id="chunk-real", model_name="all-MiniLM-L6-v2", vector_blob=BLOB, dimensions=384),
        Embedding(chunk_id="chunk-hash", model_name="hash-fallback", vector_blob=BLOB, dimensions=384),
    ])
    await profile_db.commit()
    rag = RAGModule(enable_verification=False)
    rag._embedder = _FixedEmbedder()
    results = await rag._search_vectors_async(query="LDL", profile_id=doc.profile_id, profile_db=profile_db)
    assert [chunk["chunk_id"] for chunk, _ in results] == ["chunk-real"]
