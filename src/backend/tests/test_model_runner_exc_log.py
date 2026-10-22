"""RUNNER-EXC-LOG: ModelRunner must log/re-raise only the exception type name.

Provider exception text can carry prompt/PHI fragments or filesystem paths,
so it must never reach log records or the re-raised message.
"""
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

CANARY = "canary glucose 182 /home/p/model.gguf"


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def log_records():
    lg = logging.getLogger("core.model_runner")
    handler = _ListHandler()
    old_level = lg.level
    lg.setLevel(logging.DEBUG)
    lg.addHandler(handler)
    try:
        yield handler.records
    finally:
        lg.removeHandler(handler)
        lg.setLevel(old_level)


def _runner(provider):
    from core.model_runner import ModelRunner

    return ModelRunner(_provider=provider)


def _assert_clean(records, level):
    for r in records:
        assert CANARY not in r.getMessage()
        assert r.exc_info is None
    matching = [
        r for r in records
        if r.levelno == level and "RuntimeError" in r.getMessage()
    ]
    assert len(matching) == 1


def test_hc_rel_001_generate_logs_type_name_only(log_records):
    boom = RuntimeError(CANARY)
    provider = MagicMock()
    provider.generate.side_effect = boom
    with pytest.raises(RuntimeError) as ei:
        _runner(provider).generate("hi")
    assert CANARY not in str(ei.value)
    assert ei.value.__cause__ is boom
    _assert_clean(log_records, logging.ERROR)


def test_hc_rel_001_generate_async_logs_type_name_only(log_records):
    boom = RuntimeError(CANARY)
    provider = MagicMock()
    provider.generate_async = AsyncMock(side_effect=boom)
    loop = asyncio.new_event_loop()
    try:
        with pytest.raises(RuntimeError) as ei:
            loop.run_until_complete(_runner(provider).generate_async("hi"))
    finally:
        loop.close()
    assert CANARY not in str(ei.value)
    assert ei.value.__cause__ is boom
    _assert_clean(log_records, logging.ERROR)


def test_hc_rel_002_ensure_model_available_logs_type_name_only(log_records):
    provider = MagicMock()
    provider._find_model_path.return_value = None
    selector = MagicMock()
    selector.ensure_model_available.side_effect = RuntimeError(CANARY)
    with patch("modules.model_selector.get_model_selector", return_value=selector):
        assert _runner(provider).ensure_model_available() is None
    _assert_clean(log_records, logging.WARNING)


def test_hc_rel_003_unload_logs_type_name_only(log_records):
    provider = MagicMock()
    provider.unload.side_effect = RuntimeError(CANARY)
    _runner(provider).unload()
    _assert_clean(log_records, logging.WARNING)
