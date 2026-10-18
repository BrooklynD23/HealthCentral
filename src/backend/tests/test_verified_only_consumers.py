"""W-3 / owner decision D4 (2026-09-27): verified-only legacy RAG, labelled trends.

HC-VER-001..004. Retrieval tests use a REAL in-memory SQLite session: every
pre-existing legacy-retrieval test uses a fake session that ignores WHERE
clauses, so it cannot see a verification filter (recurring-failures #1).
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

import api.observations as observations_api  # noqa: E402
from api.observations import router as observations_router  # noqa: E402
from core.auth import get_profile_db_session  # noqa: E402
from core.profile_database import ProfileDatabaseBase  # noqa: E402
from models import Chunk, Document, Embedding, Observation  # noqa: E402
from modules.rag import RAGModule  # noqa: E402
from tests.support.routes import route_client  # noqa: E402

PROFILE = "profile-w03"


# ── HC-VER-002: trends over HTTP ─────────────────────────────────────────────

class _Scalars:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def all(self) -> list:
        return self._rows


class _Result:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def scalars(self) -> _Scalars:
        return _Scalars(self._rows)


class _FakeProfileDb:
    """Returns the seeded rows whatever the statement: fine here, because the
    trends route must NOT filter by verification (D4: trends may show them)."""

    def __init__(self, rows: list) -> None:
        self._rows = rows

    async def execute(self, _stmt) -> _Result:
        return _Result(self._rows)


def _trend_row(*, value: float, collected_at: datetime, user_verified: bool) -> SimpleNamespace:
    return SimpleNamespace(
        id=str(uuid.uuid4()), profile_id=PROFILE, doc_id="doc-a",
        analyte_canonical="glucose", analyte_raw="Glucose",
        value=value, value_text=None, unit="mg/dL",
        ref_low=70.0, ref_high=99.0, ref_range_text=None,
        flag=None, is_abnormal=False, collected_at=collected_at,
        user_verified=user_verified, extraction_confidence=0.9,
        source_page=None, source_bbox_json=None,
    )


def test_hc_ver_002_trend_points_carry_user_verified_over_http(monkeypatch) -> None:
    rows = [
        _trend_row(value=90.0, collected_at=datetime(2025, 1, 10), user_verified=True),
        _trend_row(value=130.0, collected_at=datetime(2025, 6, 10), user_verified=False),
    ]
    monkeypatch.setattr(
        observations_api, "log_observation_event", AsyncMock(return_value=object())
    )

    async def _override_profile_db():
        return _FakeProfileDb(rows)

    with route_client(observations_router, "/observations", profile_id=PROFILE) as client:
        # route_client overrides auth + master DB only; add the profile DB here
        # rather than editing tests/support/routes.py (owned by P7 / G-B1).
        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        response = client.get("/observations/trends/glucose")

    assert response.status_code == 200, response.text
    points = response.json()["data_points"]
    # Both points are still shown (D4: trends MAY show unverified) and each
    # carries its own row's flag — a constant True or False fails this.
    assert [(p["value"], p["user_verified"]) for p in points] == [
        (90.0, True),
        (130.0, False),
    ]
# ── real profile DB + legacy RAG helpers ────────────────────────────────────

@pytest_asyncio.fixture
async def real_profile_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


class _StubEmbedder:
    """Deterministic stand-in: the test never loads or downloads a model, so it
    does not depend on the environment the way test_api_rag_index_002b does."""

    def embed_text(self, text: str) -> list[float]:
        return [1.0, 0.0]

    def blob_to_vector(self, blob: bytes) -> list[float]:
        return [1.0, 0.0]

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        return 1.0


class _CapturingRunner:
    """ModelRunner-shaped fake: records every prompt the legacy path would send."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def is_available(self) -> bool:
        return True

    async def generate_async(self, prompt: str, config) -> SimpleNamespace:
        self.prompts.append(prompt)
        return SimpleNamespace(
            text="UNCERTAINTIES:\nI don't have enough information", finish_reason="stop"
        )


def _document(doc_id: str, status: str) -> Document:
    return Document(
        id=doc_id, profile_id=PROFILE, path_hash="x" * 64,
        content_hash=uuid.uuid4().hex * 2, doc_type="lab_pdf",
        source=f"{doc_id}.pdf", status=status, imported_at=datetime(2025, 1, 1),
    )


def _ldl(obs_id: str, doc_id: str, value: float, verified: bool, collected_at: datetime) -> Observation:
    return Observation(
        id=obs_id, profile_id=PROFILE, doc_id=doc_id,
        analyte_canonical="ldl_cholesterol", analyte_raw="LDL Cholesterol",
        value=value, unit="mg/dL", collected_at=collected_at, user_verified=verified,
    )


def _rag() -> tuple[RAGModule, _CapturingRunner]:
    rag = RAGModule(enable_verification=False)
    rag._embedder = _StubEmbedder()
    return rag, _CapturingRunner()


async def _ask(rag: RAGModule, runner: _CapturingRunner, db: AsyncSession, question: str, analytes):
    return await rag.query(
        question=question, profile_id=PROFILE, selected_analytes=analytes,
        include_references=False, model_runner=runner, master_db=None, profile_db=db,
    )


# ── HC-VER-001 / HC-VER-004: observations ──────────────────────────────────

@pytest.mark.asyncio
async def test_hc_ver_001_unverified_observation_absent_from_legacy_rag_context(real_profile_db) -> None:
    db = real_profile_db
    db.add_all([_document("doc-v", "verified"), _document("doc-u", "parsed")])
    db.add_all([
        _ldl("obs-v", "doc-v", 101.0, True, datetime(2025, 1, 10)),
        # Newer, so without the filter it becomes "Latest value".
        _ldl("obs-u", "doc-u", 187.0, False, datetime(2025, 6, 10)),
    ])
    await db.commit()
    rag, runner = _rag()

    await _ask(rag, runner, db, "How is my LDL?", ["ldl_cholesterol"])

    # Positive control first: _get_observation_chunks swallows exceptions
    # (modules/rag.py:450-451), so a broken query would make the absence
    # assertion pass vacuously.
    assert len(runner.prompts) == 1, "verified LDL should still reach the model"
    prompt = runner.prompts[0]
    assert "101.0" in prompt, "positive control: verified value missing from context"
    assert "187.0" not in prompt, "unverified value 187.0 reached the legacy RAG prompt"


@pytest.mark.asyncio
async def test_hc_ver_004_only_unverified_data_yields_insufficient_context_without_llm_call(real_profile_db) -> None:
    db = real_profile_db
    db.add(_document("doc-u", "parsed"))
    db.add(_ldl("obs-u", "doc-u", 187.0, False, datetime(2025, 6, 10)))
    await db.commit()
    rag, runner = _rag()

    result = await _ask(rag, runner, db, "How is my LDL?", ["ldl_cholesterol"])

    assert runner.prompts == [], "runner was called with a prompt although only unverified data exists"
    assert result.insufficient_context is True
# ── HC-VER-003: document chunks (vector path, _search_vectors_async) ───────

def _chunk_with_embedding(chunk_id: str, doc_id: str, text: str) -> list:
    return [
        Chunk(id=chunk_id, doc_id=doc_id, chunk_index=0, text=text, page_number=1),
        Embedding(chunk_id=chunk_id, model_name="stub", vector_blob=b"\x00", dimensions=2),
    ]


@pytest.mark.asyncio
async def test_hc_ver_003_unverified_document_chunk_absent_from_legacy_rag_context(real_profile_db) -> None:
    db = real_profile_db
    db.add_all([_document("doc-v", "verified"), _document("doc-u", "parsed")])
    # Distinct tokens: neither may be a substring of the other.
    db.add_all(_chunk_with_embedding("chunk-v", "doc-v", "ALPHA-VERIFIED-CHUNK report text"))
    db.add_all(_chunk_with_embedding("chunk-u", "doc-u", "BRAVO-PENDING-CHUNK report text"))
    await db.commit()
    rag, runner = _rag()

    await _ask(rag, runner, db, "What does my report say?", None)

    assert len(runner.prompts) == 1, "verified document chunk should still reach the model"
    prompt = runner.prompts[0]
    assert "ALPHA-VERIFIED-CHUNK" in prompt, "positive control: verified-document chunk missing"
    assert "BRAVO-PENDING-CHUNK" not in prompt, "unverified-document chunk text reached the legacy RAG prompt"


@pytest.mark.asyncio
async def test_hc_ver_005_knowledge_fallback_cites_verified_values_only(real_profile_db) -> None:
    from unittest.mock import MagicMock, patch

    from api.assistant import ChatRequest, _build_knowledge_fallback
    from modules.knowledge_loader import BiomarkerInfo

    db = real_profile_db
    db.add_all([_document("doc-v", "verified"), _document("doc-u", "parsed")])
    db.add_all([
        _ldl("obs-v", "doc-v", 101.0, True, datetime(2025, 1, 10)),
        _ldl("obs-u", "doc-u", 187.0, False, datetime(2025, 6, 10)),
    ])
    await db.commit()
    info = BiomarkerInfo(
        id="kb-ldl", analyte_canonical="ldl_cholesterol", display_name="LDL Cholesterol",
        description="d", clinical_significance="c", normal_interpretation="n",
        high_interpretation="h", low_interpretation="l", standard_unit="mg/dL", category="lipid",
    )
    with patch("modules.knowledge_loader.get_knowledge_loader") as loader_fn:
        loader = MagicMock()
        loader.get_biomarker_knowledge = AsyncMock(return_value=info)
        loader_fn.return_value = loader
        response = await _build_knowledge_fallback(
            request=ChatRequest(question="How is my LDL?"), profile_id=PROFILE,
            db=AsyncMock(), profile_db=db,
        )

    combined = " ".join(s.content for s in response.segments)
    assert "101.0" in combined, "positive control: verified value missing from fallback"
    assert "187.0" not in combined, "unverified value cited by the no-LLM fallback"
