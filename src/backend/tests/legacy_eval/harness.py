"""Legacy RAG eval harness: W-4 / owner decision G-B5 (2026-09-27).

Drives POST /assistant/chat over HTTP (tests/support/routes.py::route_client),
so FastAPI's dependency graph runs. Only these are faked:
  - auth + master DB (route_client), and the profile DB session (AsyncMock);
  - session / history / memory helpers and the agent flag (forced off, so the
    request takes the legacy rag.query branch);
  - RAGModule.retrieve_context -> the case's fixed chunks;
  - the external-runner lookup returns a FakeRunner whose generate_async
    yields the case's model output and finish_reason ("stop" or "timeout").
RAGModule._generate_with_runner is REAL, including its timeout branch.
Everything after the runner is real product code: validate_response (claim
extraction, verify_all_claims, FaithfulnessScorer at the unchanged 0.6
threshold), the G-B5 abstain mapping, response formatting, and the
_append_turns call site. Fixture text is synthetic; it holds no patient data.
"""

from __future__ import annotations

import asyncio
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

CHAT_PATH = "/assistant/chat"

CHUNK_SETS: dict[str, tuple[dict, ...]] = {
    "glucose": (
        {
            "chunk_id": "1",
            "source_type": "user_observation",
            "doc_id": "doc-1",
            "doc_title": "Your Glucose Result",
            "page": 1,
            "text": "Glucose: 95 mg/dL (reference range 70-100 mg/dL), collected 2026-01-10.",
            "relevance_score": 0.95,
            "is_user_verified": True,
        },
        {
            "chunk_id": "2",
            "source_type": "reference",
            "doc_id": None,
            "doc_title": "Medical Reference",
            "page": None,
            "text": (
                "Glucose is a simple sugar that is the primary source of energy for the "
                "body's cells. Normal fasting glucose is typically 70-100 mg/dL."
            ),
            "relevance_score": 0.8,
        },
    ),
}


def build_chunks(chunk_set: str) -> list:
    """Return fresh RetrievedChunk objects for a named fixture set."""
    from modules.rag import RetrievedChunk

    return [RetrievedChunk(**spec) for spec in CHUNK_SETS[chunk_set]]


class FakeRunner:
    """Stands in for the runner get_runner_for_request would return. Test-only."""

    def __init__(self, text: str, finish_reason: str = "stop") -> None:
        self._result = SimpleNamespace(text=text, finish_reason=finish_reason)

    def is_available(self) -> bool:
        return True

    async def generate_async(self, prompt: str, config: object) -> SimpleNamespace:
        return self._result


def generated_text(model_output: str, finish_reason: str = "stop") -> str:
    """What the REAL RAGModule._generate_with_runner returns for this runner output."""
    from modules.rag import RAGModule

    rag = RAGModule(enable_verification=True)
    return asyncio.run(rag._generate_with_runner("prompt", FakeRunner(model_output, finish_reason)))


@contextmanager
def legacy_chat_client(
    chunks: list, model_output: str, finish_reason: str = "stop"
) -> Iterator[tuple[object, AsyncMock]]:
    """Yield (TestClient, append_turns_mock) wired to the legacy chat path."""
    import api.assistant as assistant_api
    from core.auth import get_profile_db_session
    from modules.rag import RAGModule
    from tests.support.routes import route_client

    profile_db = AsyncMock()
    # SAFE-CHAT's audit_and_commit calls create_audit_log -> synchronous db.add (core/audit.py:252);
    # route_client's default AsyncMock would turn that into an unawaited coroutine.
    master = MagicMock()
    master.commit = AsyncMock()
    master.flush = AsyncMock()
    master.refresh = AsyncMock()
    chat_session = SimpleNamespace(id="sess-legacy-eval", updated_at=None)
    append_turns = AsyncMock(return_value="turn-legacy-eval")

    async def _profile_db_override():
        yield profile_db

    with ExitStack() as stack:
        stack.enter_context(patch.object(assistant_api, "is_agent_enabled", return_value=False))
        stack.enter_context(patch.object(assistant_api, "_get_user_model_settings", AsyncMock(return_value=None)))
        stack.enter_context(patch.object(assistant_api, "_get_or_create_session", AsyncMock(return_value=chat_session)))
        stack.enter_context(patch.object(assistant_api, "_load_session_history", AsyncMock(return_value=[])))
        stack.enter_context(patch.object(assistant_api, "_effective_use_memory", AsyncMock(return_value=False)))
        stack.enter_context(patch.object(assistant_api, "_append_turns", append_turns))
        stack.enter_context(
            patch(
                "core.external_runner.get_runner_for_request",
                AsyncMock(return_value=FakeRunner(model_output, finish_reason)),
            )
        )
        stack.enter_context(patch.object(RAGModule, "retrieve_context", AsyncMock(return_value=chunks)))
        client = stack.enter_context(route_client(assistant_api.router, "/assistant", master_db=master))
        client.app.dependency_overrides[get_profile_db_session] = _profile_db_override
        yield client, append_turns
