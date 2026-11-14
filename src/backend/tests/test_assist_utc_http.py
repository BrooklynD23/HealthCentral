"""ASSIST-UTC — chat date filters are compared as naive UTC.

Owner decision ASSIST-UTC (2026-10-14): patch the parsing in modules/rag.py;
malformed dates stay silently ignored, no new 422s.

HC-ASSIST-UTC-001 drives POST /assistant/chat over HTTP through
tests/support/routes.py::route_client into the real legacy rag.query ->
retrieve_context -> _get_observation_chunks / _search_vectors_async date
filters, against a real in-memory profile DB. Only the model call (the
ModelRunner seam) and the embedder's vector math are stubbed.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.assistant as A
from api.assistant import router as assistant_router
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import chat_session, model_settings  # noqa: F401
from models.chunk import Chunk
from models.document import Document
from models.embedding import Embedding
from models.observation import Observation
from tests.legacy_eval.harness import AllowJudge
from tests.support.routes import route_client

PROFILE = "profile-a"  # route_client's default session
# Stored naive UTC: 2026-03-10 20:00 UTC.
STORED_AT = datetime(2026, 3, 10, 20, 0, 0)
OBS_MARKER = "137.25"
DOC_MARKER = "ASSISTUTC-DOC-5c1e"
ANSWER = "REPORT FACTS:\nYour LDL result is listed [cite:1]."


class _MasterDb:
    def add(self, _obj) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def execute(self, *_a, **_k):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        result.scalars.return_value.all.return_value = []
        return result


class _Runner:
    """ModelRunner double: records every prompt it is asked to complete."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def is_available(self) -> bool:
        return True

    async def generate_async(self, prompt, _config):
        self.prompts.append(prompt)
        return MagicMock(text=ANSWER, finish_reason="stop")


async def _seeded_profile_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    db = AsyncSession(engine, expire_on_commit=False)
    db.add(Document(
        id="doc-1", profile_id=PROFILE, path_hash="p", content_hash="c",
        doc_type="pdf", status="verified", collection_date=STORED_AT,
        imported_at=STORED_AT,
    ))
    db.add(Chunk(id="chunk-1", doc_id="doc-1", chunk_index=0, text=DOC_MARKER))
    db.add(Embedding(chunk_id="chunk-1", model_name="m", vector_blob=b"\x00", dimensions=1))
    db.add(Observation(
        id="obs-1", profile_id=PROFILE, doc_id="doc-1",
        analyte_canonical="ldl_cholesterol", analyte_raw="LDL",
        value=137.25, unit="mg/dL", collected_at=STORED_AT,
        user_verified=True,  # D4/O-5: legacy chat reads verified rows only
    ))
    await db.commit()
    return db, engine


def _rag(runner: _Runner):
    with patch("modules.rag.get_model_runner", return_value=runner), \
         patch("modules.rag.EmbeddingsModule"):
        from modules.rag import RAGModule

        rag = RAGModule(enable_verification=False)
    rag._embedder.cosine_similarity.return_value = 0.9
    rag._embedder.config.model_name = "m"
    return rag


async def _chat(filters: dict) -> tuple[object, str]:
    runner = _Runner()
    profile_db, engine = await _seeded_profile_db()
    try:
        with patch.object(A, "get_rag_module", return_value=_rag(runner)), \
             patch.object(A, "is_agent_enabled", return_value=False), \
             patch("modules.rag.get_model_runner", return_value=AllowJudge()):
            with route_client(
                assistant_router, "/assistant", profile_id=PROFILE, master_db=_MasterDb()
            ) as client:

                async def _override_profile_db():
                    return profile_db

                client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
                resp = client.post(
                    "/assistant/chat",
                    json={"question": "what is my ldl?", "include_references": False, **filters},
                )
        return resp, "\n".join(runner.prompts)
    finally:
        await profile_db.close()
        await engine.dispose()


# Row stored at 2026-03-10 20:00 UTC. `included` = the row is inside the window.
CASES = [
    # +05:00 near midnight: 2026-03-11 00:30+05:00 == 2026-03-10 19:30Z.
    ("plus5_from_includes", {"from_date": "2026-03-11T00:30:00+05:00"}, True),
    ("plus5_to_excludes", {"to_date": "2026-03-11T00:30:00+05:00"}, False),
    # -08:00: 13:00-08:00 == 21:00Z.
    ("minus8_to_includes", {"to_date": "2026-03-10T13:00:00-08:00"}, True),
    ("minus8_from_excludes", {"from_date": "2026-03-10T13:00:00-08:00"}, False),
    ("z_from_includes", {"from_date": "2026-03-10T19:30:00Z"}, True),
    ("z_from_excludes", {"from_date": "2026-03-10T20:30:00Z"}, False),
    # Bounds exactly at the stored instant are inclusive.
    ("z_from_equal_includes", {"from_date": "2026-03-10T20:00:00Z"}, True),
    ("plus5_to_equal_includes", {"to_date": "2026-03-11T01:00:00+05:00"}, True),
    ("naive_from_includes", {"from_date": "2026-03-10T19:30:00"}, True),
    ("naive_from_excludes", {"from_date": "2026-03-10T20:30:00"}, False),
    # Malformed: silently ignored as before (no 422, filter not applied).
    ("malformed_from_ignored", {"from_date": "not-a-date"}, True),
    ("malformed_to_ignored", {"to_date": "2026-13-45"}, True),
    ("malformed_both_ignored", {"from_date": "", "to_date": "yesterday"}, True),
    # Parses, but the offset pushes it out of datetime's range: ignored, not a 500.
    ("overflow_from_ignored", {"from_date": "0001-01-01T00:00:00+05:00"}, True),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("name,filters,included", CASES, ids=[c[0] for c in CASES])
async def test_hc_assist_utc_001_chat_date_filters_are_naive_utc(name, filters, included):
    resp, prompt = await _chat(filters)
    assert resp.status_code == 200, resp.text
    if included:
        assert OBS_MARKER in prompt, f"{name}: observation filtered out"
        assert DOC_MARKER in prompt, f"{name}: document chunk filtered out"
    else:
        assert OBS_MARKER not in prompt, f"{name}: observation leaked past the window"
        assert DOC_MARKER not in prompt, f"{name}: document chunk leaked past the window"
        assert resp.json()["insufficient_context"] is True
