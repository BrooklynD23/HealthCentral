"""LlamaCppProvider fixes found on the 2026-10-22 GPU-box runs.

LLAMA-CHAT-FORMAT: the provider must not pass ``chat_format="auto"`` (an
invalid handler name in llama-cpp-python 0.3.35; the default ``None`` reads the
GGUF chat template).
LLAMA-SERIAL: one native model must never be entered by two threads, and must
never be freed while a generation runs.
LLAMA-GPU-LAYERS: ``LLM_N_GPU_LAYERS`` reaches the provider from the factory.

No real model is loaded: ``_load_llama_class`` returns a recording fake.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import core.llm.llama_cpp_provider as lcp  # noqa: E402
from core.llm.provider import ChatMessage  # noqa: E402
from core.model_runner import InferenceConfig  # noqa: E402


class _FakeState:
    """Shared, lock-protected record of what the fake native model saw."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.ctor_kwargs: list = []
        self.active = 0
        self.max_active = 0
        self.total = 0
        self.entered = threading.Event()
        self.gate = threading.Event()  # generation blocks until this is set
        self.after_gate = None  # optional callable run just before returning


def _make_fake_llama(state: _FakeState):
    class _FakeLlama:
        def __init__(self, **kwargs):
            state.ctor_kwargs.append(kwargs)

        def create_chat_completion(self, **kwargs):
            with state.lock:
                state.active += 1
                state.total += 1
                state.max_active = max(state.max_active, state.active)
            state.entered.set()
            try:
                state.gate.wait(timeout=10)  # bounded: threads always end
                if state.after_gate is not None:
                    state.after_gate()
            finally:
                with state.lock:
                    state.active -= 1
            return {
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"completion_tokens": 1},
            }

    return _FakeLlama


@pytest.fixture
def state(monkeypatch):
    st = _FakeState()
    monkeypatch.setattr(lcp, "_load_llama_class", lambda: _make_fake_llama(st))
    yield st
    st.gate.set()  # never leave a blocked thread behind


@pytest.fixture
def model_file(tmp_path):
    p = tmp_path / "secret-model-name.gguf"
    p.write_bytes(b"GGUF")
    return p


def _provider(model_file, **kwargs):
    return lcp.LlamaCppProvider(model_path=str(model_file), **kwargs)


def _config(timeout=5):
    return InferenceConfig(
        max_tokens=16, temperature=0.1, top_p=0.9, stop_sequences=None,
        timeout_seconds=timeout,
    )


MSGS = [ChatMessage(role="user", content="hi")]


# ---------------------------------------------------------------------------
# LLAMA-CHAT-FORMAT
# ---------------------------------------------------------------------------

def test_hc_lcf_001_no_chat_format_kwarg(state, model_file):
    provider = _provider(model_file)
    assert provider._ensure_initialized() is True
    assert len(state.ctor_kwargs) == 1
    assert "chat_format" not in state.ctor_kwargs[0]
