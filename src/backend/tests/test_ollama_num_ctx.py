"""HC-ONC: Ollama num_ctx in the /api/chat request body (OLLAMA-NUM-CTX). No network, no daemon."""
from __future__ import annotations

import asyncio
import json

from core.llm import ollama_provider
from core.llm.ollama_provider import OllamaProvider
from core.llm.provider import ChatMessage
from core.model_runner import InferenceConfig

_MSGS = [ChatMessage(role="user", content="hi")]
_URL = "http://127.0.0.1:11434"


def _provider(model: str = "llama3.1:8b") -> OllamaProvider:
    p = OllamaProvider(model=model, base_url=_URL)
    p._available = True
    return p


class _Resp:
    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": "ok"}, "done": True, "eval_count": 1}

    async def aiter_lines(self):
        yield json.dumps({"message": {"content": "ok"}, "done": True})


class _SyncClient:
    def __init__(self, captured):
        self._captured = captured

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, json=None, **kw):
        self._captured.update(json)
        return _Resp()


class _AsyncClient:
    def __init__(self, captured):
        self._captured = captured

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, **kw):
        self._captured.update(json)
        return _Resp()

    def stream(self, method, url, json=None, **kw):
        self._captured.update(json)
        return _StreamCtx()


class _StreamCtx:
    async def __aenter__(self):
        return _Resp()

    async def __aexit__(self, *a):
        return False


def test_hc_onc_001_generate_sends_num_ctx(monkeypatch):
    sent: dict = {}
    p = _provider()
    monkeypatch.setattr(p, "_make_client", lambda: _SyncClient(sent))
    p.generate(_MSGS, InferenceConfig())
    assert sent["options"]["num_ctx"] == min(ollama_provider._OLLAMA_NUM_CTX, 8192)


def test_hc_onc_001_generate_async_sends_num_ctx(monkeypatch):
    sent: dict = {}
    p = _provider()
    monkeypatch.setattr(p, "_make_async_client", lambda: _AsyncClient(sent))
    asyncio.run(p.generate_async(_MSGS, InferenceConfig()))
    assert sent["options"]["num_ctx"] == min(ollama_provider._OLLAMA_NUM_CTX, 8192)


def test_hc_onc_001_generate_stream_sends_num_ctx(monkeypatch):
    sent: dict = {}
    p = _provider()
    monkeypatch.setattr(p, "_make_async_client", lambda: _AsyncClient(sent))

    async def _drain():
        return [t async for t in p.generate_stream(_MSGS, InferenceConfig())]

    assert asyncio.run(_drain()) == ["ok"]
    assert sent["options"]["num_ctx"] == min(ollama_provider._OLLAMA_NUM_CTX, 8192)


def test_hc_onc_002_num_ctx_capped_at_model_max(monkeypatch):
    monkeypatch.setattr(ollama_provider, "_OLLAMA_NUM_CTX", 16384)
    body = _provider("llama3.1:8b")._build_request_body(_MSGS, InferenceConfig())
    assert body["options"]["num_ctx"] == 8192


def test_hc_onc_003_gemma4_num_ctx_8192():
    body = _provider("gemma4:e4b")._build_request_body(_MSGS, InferenceConfig())
    assert body["options"]["num_ctx"] == 8192
