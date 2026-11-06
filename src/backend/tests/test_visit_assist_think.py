"""VISIT-ASSIST-THINK: the visit-note LLM assist must turn thinking off.

With Gemma 4 and thinking on, the assist returned nothing. Only the visit-note
assist sets ``think=False``; the RAG call sites keep the provider default.

The config is captured from the real call sites and then pushed through the real
Ollama request-body builder, so a hand-built ``InferenceConfig`` never stands in.

These tests prove the flag reaches the request body. They cannot show that a
model returns a non-empty answer with thinking off; that needs a model-host run.

HC-VAT-001  llm_assist_visit_entities passes think=False to the runner
HC-VAT-002  that recorded config puts "think": false in the /api/chat body
HC-VAT-003  the two RAG call sites still leave think unset (pin)
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.llm.ollama_provider import OllamaProvider
from core.llm.provider import ChatMessage
from modules.extract_visit_notes import llm_assist_visit_entities
from modules.rag import RAGModule


class _RecordingRunner:
    def __init__(self) -> None:
        self.configs: list = []

    def is_available(self) -> bool:
        return True

    async def generate_async(self, prompt, config):
        self.configs.append(config)
        return SimpleNamespace(text="[]", finish_reason="stop")


async def _visit_assist_config():
    recorder = _RecordingRunner()
    await llm_assist_visit_entities("Visit note text", runner=recorder)
    assert len(recorder.configs) == 1
    return recorder.configs[0]


@pytest.mark.asyncio
async def test_hc_vat_001_visit_assist_config_thinking_off():
    config = await _visit_assist_config()
    assert config.think is False


@pytest.mark.asyncio
async def test_hc_vat_002_recorded_config_sends_think_false_in_body():
    config = await _visit_assist_config()
    provider = OllamaProvider(model="test-model", base_url="http://127.0.0.1:11434")
    body = provider._build_request_body([ChatMessage(role="user", content="hi")], config)
    assert body["think"] is False


@pytest.mark.asyncio
async def test_hc_vat_003_rag_call_sites_leave_think_unset():
    with patch("modules.rag.get_model_runner"), patch("modules.rag.EmbeddingsModule"):
        rag = RAGModule(enable_verification=True)

    # RAGModule.query reaches the model through _generate_with_runner.
    via_runner = _RecordingRunner()
    await rag._generate_with_runner("prompt", via_runner)
    assert len(via_runner.configs) == 1
    assert via_runner.configs[0].think is None

    # generate_response uses the module's own runner.
    own = _RecordingRunner()
    rag._model_runner = own
    await rag.generate_response("prompt")
    assert len(own.configs) == 1
    assert own.configs[0].think is None
