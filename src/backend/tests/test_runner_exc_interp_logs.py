"""RUNNER-EXC-INTERP: LLM failure handlers must log the exception TYPE only.

A provider exception's text can carry prompt/PHI fragments. Each handler below
used to interpolate `{e}` into its log line (and, in rag.py, into the raised
RuntimeError). Every record is checked through `logging.Formatter().format`,
which includes exc_text, not just getMessage().

The raising object is injected at the runner/selector seam: a provider behind a
real ModelRunner would be stripped by ModelRunner first and could never be RED.

HC-REI-001  RAGModule._generate_with_runner
HC-REI-002  RAGModule.generate_response
HC-REI-003  InterpretModule._llm_interpretation
HC-REI-004  POST /interpretations/batch (HTTP)
HC-REI-005  llm_assist_visit_entities
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.interpretations as interpretations_api
import models  # noqa: F401  register every table on both bases
from core.auth import get_profile_db_session
from core.database import Base
from core.profile_database import ProfileDatabaseBase
from models import Observation
from modules.extract_visit_notes import llm_assist_visit_entities
from modules.interpret import InterpretModule
from modules.rag import RAGModule
from tests.support.routes import route_client

TOKEN = "SECRET-PHI-123"
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


def _assert_no_token(records) -> None:
    fmt = logging.Formatter()
    for r in records:
        assert TOKEN not in fmt.format(r), fmt.format(r)


class _RaisingRunner:
    def is_available(self) -> bool:
        return True

    async def generate_async(self, prompt, config):
        raise RuntimeError(TOKEN)


def _rag() -> RAGModule:
    with patch("modules.rag.get_model_runner") as runner, patch("modules.rag.EmbeddingsModule"):
        runner.return_value = _RaisingRunner()
        return RAGModule(enable_verification=True)


@pytest.mark.asyncio
async def test_hc_rei_001_generate_with_runner_type_only(log_records):
    rag = _rag()
    with pytest.raises(RuntimeError) as ei:
        await rag._generate_with_runner("prompt", _RaisingRunner())
    assert TOKEN not in str(ei.value)
    assert str(ei.value) == "Failed to generate response"
    assert isinstance(ei.value.__cause__, RuntimeError)
    _assert_no_token(log_records)


@pytest.mark.asyncio
async def test_hc_rei_002_generate_response_type_only(log_records):
    rag = _rag()
    with pytest.raises(RuntimeError) as ei:
        await rag.generate_response("prompt")
    assert TOKEN not in str(ei.value)
    assert str(ei.value) == "Failed to generate response"
    assert isinstance(ei.value.__cause__, RuntimeError)
    _assert_no_token(log_records)


@pytest.mark.asyncio
async def test_hc_rei_003_llm_interpretation_type_only(log_records):
    selector = MagicMock()
    selector.run_inference = AsyncMock(side_effect=RuntimeError(TOKEN))
    module = InterpretModule(
        knowledge_loader=MagicMock(),
        safety_guard=MagicMock(),
        recommendation_engine=MagicMock(),
        model_selector=selector,
    )
    module._build_llm_prompt = MagicMock(return_value="prompt")
    module._generate_interpretation = AsyncMock(return_value=("template", None))
    out = await module._llm_interpretation(MagicMock(), MagicMock(), PROFILE_ID, MagicMock())
    assert out == ("template", None)
    module._generate_interpretation.assert_awaited_once()
    assert any("RuntimeError" in r.getMessage() for r in log_records)
    _assert_no_token(log_records)


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


@pytest.mark.asyncio
async def test_hc_rei_004_batch_route_type_only(dbs, log_records):
    profile_db, master_db, obs_id = dbs
    stub = MagicMock()
    stub.interpret_observation = AsyncMock(side_effect=RuntimeError(TOKEN))
    with patch.object(interpretations_api, "get_interpret_module", return_value=stub), \
        route_client(
            interpretations_api.router, "/interpretations",
            profile_id=PROFILE_ID, master_db=master_db,
        ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        resp = client.post(
            "/interpretations/batch", json={"observation_ids": [obs_id]}
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["failed"][0]["error"] == "Internal error"
    assert TOKEN not in resp.text
    assert any("RuntimeError" in r.getMessage() for r in log_records)
    _assert_no_token(log_records)
