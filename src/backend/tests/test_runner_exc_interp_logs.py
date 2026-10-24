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
