"""LEGACY-CITE-PROMPT Task 1: a response schema rides InferenceConfig to the providers.

HC-LCP-001  Ollama body carries top-level "format" only when a schema is set
HC-LCP-002  llama.cpp generate passes response_format only when a schema is set
HC-LCP-003  ModelRunner.generate_async forwards the same InferenceConfig object
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from core.llm.provider import ChatMessage
from core.model_runner import InferenceConfig, InferenceResult, ModelRunner

SCHEMA = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
MSGS = [ChatMessage(role="user", content="hi")]


def test_hc_lcp_001_ollama_body_has_format_only_with_schema():
    from core.llm.ollama_provider import OllamaProvider

    p = OllamaProvider(model="m", base_url="http://127.0.0.1:11434")
    with_schema = p._build_request_body(MSGS, InferenceConfig(response_schema=SCHEMA))
    assert with_schema["format"] == SCHEMA
    assert "format" not in with_schema["options"]

    plain = p._build_request_body(MSGS, InferenceConfig())
    assert "format" not in plain
    assert set(plain) == {"model", "messages", "stream", "options"}


def test_hc_lcp_002_llama_cpp_response_format_only_with_schema():
    from core.llm.llama_cpp_provider import LlamaCppProvider

    p = LlamaCppProvider(model_path="/fake/model.gguf")
    model = MagicMock()
    model.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
        "usage": {"completion_tokens": 1},
    }
    p._initialized = True
    p._model = model

    p.generate(MSGS, InferenceConfig(response_schema=SCHEMA))
    kwargs = model.create_chat_completion.call_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object", "schema": SCHEMA}

    model.create_chat_completion.reset_mock()
    p.generate(MSGS, InferenceConfig())
    assert "response_format" not in model.create_chat_completion.call_args.kwargs


def test_hc_lcp_003_model_runner_forwards_same_config_object():
    seen = []

    class SpyProvider:
        async def generate_async(self, messages, config):
            seen.append(config)
            return InferenceResult(text="x", tokens_generated=1, finish_reason="stop", model_name="spy")

    cfg = InferenceConfig(response_schema=SCHEMA)
    asyncio.run(ModelRunner(_provider=SpyProvider()).generate_async("p", cfg))
    assert seen == [cfg] and seen[0] is cfg
    assert seen[0].response_schema == SCHEMA
