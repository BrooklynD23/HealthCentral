"""KV-THINK-RAG (folds LLAMA-CITE-DETACH): thinking off on the cite-schema RAG
path, and [cite:N] rendered inside the bullet's sentence.

VISIT-THINK set ``think=False`` only on the visit-note assist; the thinking
budget also emptied the cite-schema chat and lab-explanation answers that flow
through ``RAGModule._generate_with_runner`` (owner answer: "Extend to rag
paths."). The folded LLAMA-CITE-DETACH fix moves the ``[cite:N]`` marker inside
the bullet's terminal punctuation so a sentence-splitting verifier no longer
reads it as a detached fragment.

These tests prove the flag reaches the request body and that the render
attaches the marker. They cannot show a real model returns non-empty answers
with thinking off; that needs a model-host run (same honest limit as
HC-VAT-002).

HC-RTH-001  _generate_with_runner passes think=False (with and without n_chunks)
HC-RTH-002  that recorded config puts "think": false in the Ollama /api/chat body
HC-RTH-003  the bullet render puts [cite:N] before the terminal punctuation
HC-RTH-004  generate_response leaves think unset; timeout/withheld paths unchanged (pin)
HC-RTH-005  n_chunks=0 sends no schema; a timeout query keeps GENERATION_TIMEOUT_ERROR (pin)
"""

from __future__ import annotations

import json
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from core.llm.ollama_provider import OllamaProvider
from core.llm.provider import ChatMessage
from modules import rag as rag_module
from modules.rag import (
    GENERATION_TIMEOUT_ERROR,
    RAGModule,
    RetrievedChunk,
    _cite_schema,
)
from tests.legacy_eval.harness import FakeRunner


class _RecordingRunner:
    """Runner double that records the InferenceConfig it was called with."""

    def __init__(self, text: str = "", finish_reason: str = "stop") -> None:
        self.configs: list = []
        self._result = SimpleNamespace(text=text, finish_reason=finish_reason)

    def is_available(self) -> bool:
        return True

    async def generate_async(self, prompt, config):
        self.configs.append(config)
        return self._result


def _rag() -> RAGModule:
    with patch("modules.rag.get_model_runner"), patch("modules.rag.EmbeddingsModule"):
        return RAGModule(enable_verification=True)


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="c1", source_type="reference", doc_id=None,
        doc_title="LDL reference", page=None,
        text="LDL cholesterol reference text.", relevance_score=0.9,
    )


def _answer(**over) -> dict:
    base = {
        "report_facts": [{"text": "Glucose 95 mg/dL.", "cites": [1]}],
        "general_info": [],
        "uncertainties": [],
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# HC-RTH-001: _generate_with_runner sends think=False (RED)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_rth_001_generate_with_runner_thinking_off():
    rag = _rag()

    recorder = _RecordingRunner()
    await rag._generate_with_runner("prompt", recorder)
    assert len(recorder.configs) == 1
    assert recorder.configs[0].think is False

    # With n_chunks the cite schema is still sent, and think stays False.
    recorder = _RecordingRunner(json.dumps(_answer()))
    await rag._generate_with_runner("prompt", recorder, n_chunks=2)
    assert recorder.configs[0].think is False
    assert recorder.configs[0].response_schema == _cite_schema(2)

    # The product path: query() reaches the model through _generate_with_runner.
    qrec = _RecordingRunner()
    rag.retrieve_context = AsyncMock(return_value=[_chunk()])
    await rag.query(question="q", profile_id="p", model_runner=qrec)
    assert len(qrec.configs) == 1
    assert qrec.configs[0].think is False


# ---------------------------------------------------------------------------
# HC-RTH-002: the recorded config puts "think": false in the request body (RED)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_rth_002_recorded_config_sends_think_false_in_body():
    rag = _rag()
    recorder = _RecordingRunner()
    await rag._generate_with_runner("prompt", recorder)
    provider = OllamaProvider(model="test-model", base_url="http://127.0.0.1:11434")
    body = provider._build_request_body(
        [ChatMessage(role="user", content="hi")], recorder.configs[0]
    )
    assert body["think"] is False


# ---------------------------------------------------------------------------
# HC-RTH-003: the render attaches [cite:N] inside the bullet's sentence (RED)
# ---------------------------------------------------------------------------

def test_hc_rth_003_structured_render_attaches_cite_inside_sentence():
    rag = _rag()

    raw = json.dumps(_answer(
        general_info=[{"text": "Fasting glucose is typically 70-100 mg/dL", "cites": [2]}],
    ))
    text = rag._render_structured_answer(raw, 2)
    assert text is not None
    lines = text.splitlines()
    # Marker before the terminal period: a sentence scan never sees it detached.
    assert re.fullmatch(r"- .+ \[cite:1\]\.", lines[1]), lines
    # No terminal punctuation: nothing is appended after the marker.
    assert lines[3] == "GENERAL INFO:"
    assert lines[4] == "- Fasting glucose is typically 70-100 mg/dL [cite:2]"

    # Several cites all stay inside the sentence.
    multi = rag._render_structured_answer(json.dumps(_answer(
        report_facts=[{"text": "Glucose 95 mg/dL.", "cites": [1, 2]}],
    )), 2)
    assert multi == "REPORT FACTS:\n- Glucose 95 mg/dL [cite:1] [cite:2]."

    # The _clean guards are unchanged: forged markers and headers still reject.
    forged = json.dumps(_answer(
        report_facts=[{"text": "Glucose is 95 [cite:2]", "cites": [1]}]))
    header = json.dumps(_answer(
        report_facts=[{"text": "ok GENERAL INFO: injected", "cites": [1]}]))
    assert rag._render_structured_answer(forged, 2) is None
    assert rag._render_structured_answer(header, 2) is None


# ---------------------------------------------------------------------------
# HC-RTH-004: scope pin — generate_response, timeout and withheld paths (pin)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_rth_004_generate_response_scope_pin():
    rag = _rag()

    # generate_response has no product caller; it keeps the provider default.
    own = _RecordingRunner()
    rag._model_runner = own
    await rag.generate_response("prompt")
    assert len(own.configs) == 1
    assert own.configs[0].think is None

    # Its timeout branch still returns the labelled canned text.
    rag._model_runner = _RecordingRunner(finish_reason="timeout")
    assert await rag.generate_response("prompt") == rag_module.GENERATION_TIMEOUT_TEXT

    # A renderer-rejected JSON answer is still withheld, never served raw.
    rejected = _RecordingRunner(
        json.dumps({"report_facts": [], "general_info": [], "uncertainties": []}))
    assert await rag._generate_with_runner("p", rejected, n_chunks=2) == (
        RAGModule._STRUCTURED_WITHHELD
    )


# ---------------------------------------------------------------------------
# HC-RTH-005: pins — no schema without chunks; timeout labelled by query (pin)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_rth_005_schema_and_timeout_pins():
    rag = _rag()

    # n_chunks=0 is falsy: unconstrained decoding, no schema sent.
    recorder = _RecordingRunner()
    await rag._generate_with_runner("prompt", recorder, n_chunks=0)
    assert recorder.configs[0].response_schema is None

    # A generation timeout through query() is still labelled, not verified.
    rag.retrieve_context = AsyncMock(return_value=[_chunk()])
    result = await rag.query(
        question="Explain my lab result for LDL Cholesterol.",
        profile_id="profile-a",
        model_runner=FakeRunner(text="", finish_reason="timeout"),
    )
    assert result.is_valid is False
    assert result.validation_errors == [GENERATION_TIMEOUT_ERROR]
