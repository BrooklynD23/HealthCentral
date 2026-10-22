"""RUNNER-EXC-CHAIN: the two route handlers that catch a runner failure must
not log it through `logger.exception`.

`ModelRunner` (RUNNER-EXC-LOG, #285) keeps its own message type-only but still
raises `RuntimeError(...) from exc`, so the provider exception, whose text can
carry prompt/PHI fragments, is the `__cause__`. A traceback prints that chain.
Each record is therefore checked through `logging.Formatter().format(record)`,
which includes `exc_text`, not just `getMessage()`.

HC-REL-004  POST /interpretations/observations/{id}/interpret-grounded -> 503
HC-REL-005  POST /assistant/chat (agent off)                          -> 500

Both go through HTTP (route_client) with a REAL ModelRunner whose fake provider
raises; RAGModule._generate_with_runner and ModelRunner.generate_async are real.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.assistant as assistant_api
import api.interpretations as interpretations_api
import models  # noqa: F401  register every table on both bases
from core.auth import get_profile_db_session
from core.database import Base
from core.model_runner import ModelRunner
from core.profile_database import ProfileDatabaseBase
from models import Observation
from modules.rag import RAGModule
from tests.legacy_eval.harness import build_chunks
from tests.support.routes import route_client

CANARY = "canary glucose 182 SECRET"
PROFILE_ID = "profile-a"  # route_client's default session profile_id


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def log_records():
    root = logging.getLogger()
    handler = _ListHandler()
    old_level = root.level
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)
    try:
        yield handler.records
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)


class _RaisingProvider:
    """Provider whose inference raises the canary, as a failing backend would."""

    def is_available(self) -> bool:
        return True

    async def generate_async(self, messages, config):
        raise RuntimeError(CANARY)


def _real_runner() -> ModelRunner:
    return ModelRunner(_provider=_RaisingProvider())


def _formatted(records) -> list[str]:
    fmt = logging.Formatter()
    return [fmt.format(r) for r in records]


def _assert_chain_clean(records, logger_name: str, message: str) -> None:
    errors = [
        r for r in records if r.levelno == logging.ERROR and r.name == logger_name
    ]
    assert len(errors) == 1, [(r.name, r.levelno, r.getMessage()) for r in records]
    # Type name only: str(exc) would add the exception text (review round 1).
    assert errors[0].getMessage() == f"{message}: RuntimeError"
    assert errors[0].exc_info is None
    for text in _formatted(records):
        assert CANARY not in text
        assert "SECRET" not in text


async def _engine_session(base):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
    return AsyncSession(engine, expire_on_commit=False), engine


@pytest_asyncio.fixture
async def dbs():
    profile_db, p_engine = await _engine_session(ProfileDatabaseBase)
    master_db, m_engine = await _engine_session(Base)
    obs = Observation(
        id=str(uuid.uuid4()), profile_id=PROFILE_ID, doc_id=str(uuid.uuid4()),
        analyte_canonical="ldl", analyte_raw="LDL Cholesterol", value=120.0,
        unit="mg/dL", ref_low=0.0, ref_high=130.0, collected_at=datetime(2026, 3, 1, 9),
    )
    profile_db.add(obs)
    await profile_db.commit()
    try:
        yield profile_db, master_db, obs.id
    finally:
        await profile_db.close()
        await master_db.close()
        await p_engine.dispose()
        await m_engine.dispose()


def _rag_with_real_generation() -> RAGModule:
    """A RAGModule whose retrieval is stubbed; generation is the real code path."""
    with patch("modules.rag.get_model_runner") as runner, patch("modules.rag.EmbeddingsModule"):
        runner.return_value = MagicMock(is_available=MagicMock(return_value=True))
        rag = RAGModule(enable_verification=True)
    rag.retrieve_context = AsyncMock(return_value=build_chunks("glucose"))
    return rag


@pytest.mark.asyncio
async def test_hc_rel_004_grounded_route_503_does_not_log_provider_text(dbs, log_records):
    profile_db, master_db, obs_id = dbs
    with patch.object(
        interpretations_api, "get_rag_module", return_value=_rag_with_real_generation()
    ), patch(
        "core.external_runner.get_runner_for_request",
        AsyncMock(return_value=_real_runner()),
    ), route_client(
        interpretations_api.router, "/interpretations",
        profile_id=PROFILE_ID, master_db=master_db,
    ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        resp = client.post(
            f"/interpretations/observations/{obs_id}/interpret-grounded"
        )
    assert resp.status_code == 503, resp.text
    assert CANARY not in resp.text
    _assert_chain_clean(
        log_records, "api.interpretations", "Grounded interpretation inference failed"
    )


def test_hc_rel_005_chat_route_500_does_not_log_provider_text(log_records):
    profile_db = AsyncMock()
    master = MagicMock()
    master.commit = AsyncMock()
    master.flush = AsyncMock()
    master.refresh = AsyncMock()
    chat_session = SimpleNamespace(id="sess-exc-chain", updated_at=None)

    async def _profile_db_override():
        yield profile_db

    with patch.object(assistant_api, "get_rag_module", return_value=_rag_with_real_generation()), \
        patch.object(assistant_api, "is_agent_enabled", return_value=False), \
        patch.object(assistant_api, "_get_user_model_settings", AsyncMock(return_value=None)), \
        patch.object(assistant_api, "_get_or_create_session", AsyncMock(return_value=chat_session)), \
        patch.object(assistant_api, "_load_session_history", AsyncMock(return_value=[])), \
        patch.object(assistant_api, "_effective_use_memory", AsyncMock(return_value=False)), \
        patch("core.external_runner.get_runner_for_request", AsyncMock(return_value=_real_runner())), \
        route_client(assistant_api.router, "/assistant", master_db=master) as client:
        client.app.dependency_overrides[get_profile_db_session] = _profile_db_override
        resp = client.post("/assistant/chat", json={"question": "What was my glucose?"})
    assert resp.status_code == 500, resp.text
    assert CANARY not in resp.text
    _assert_chain_clean(log_records, "api.assistant", "Assistant chat request failed")
