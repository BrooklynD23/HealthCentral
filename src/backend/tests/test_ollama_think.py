"""HC-OTK: Ollama `think` flag in the /api/chat request body (JUDGE-THINK).

Pure body-construction tests: no network, no daemon.
"""
from __future__ import annotations

from core.llm.ollama_provider import OllamaProvider
from core.llm.provider import ChatMessage
from core.model_runner import InferenceConfig


def _provider() -> OllamaProvider:
    return OllamaProvider(model="test-model", base_url="http://127.0.0.1:11434")


_MSGS = [ChatMessage(role="user", content="hi")]


def test_hc_otk_001_think_false_sent_top_level():
    body = _provider()._build_request_body(_MSGS, InferenceConfig(think=False))
    assert body["think"] is False
    assert "think" not in body["options"]


def test_hc_otk_002_default_body_has_no_think_key():
    body = _provider()._build_request_body(_MSGS, InferenceConfig())
    assert "think" not in body
    assert "think" not in body["options"]
