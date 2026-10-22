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


# ---------------------------------------------------------------------------
# LLAMA-SERIAL
# ---------------------------------------------------------------------------

def _wait_entered(state, timeout=5):
    assert state.entered.wait(timeout=timeout), "fake model was never entered"


@pytest.mark.asyncio
async def test_hc_lck_001_concurrent_calls_enter_model_one_at_a_time(state, model_file):
    import asyncio

    provider = _provider(model_file)
    assert provider._ensure_initialized() is True
    t1 = asyncio.ensure_future(provider.generate_async(MSGS, _config(timeout=10)))
    await asyncio.get_running_loop().run_in_executor(None, _wait_entered, state)
    t2 = asyncio.ensure_future(provider.generate_async(MSGS, _config(timeout=10)))
    try:
        await asyncio.sleep(0.3)  # bounded window for a second thread to barge in
    finally:
        state.gate.set()
    r1, r2 = await asyncio.wait_for(asyncio.gather(t1, t2), timeout=10)
    assert state.max_active == 1
    assert state.total == 2
    assert r1.text == "ok" and r2.text == "ok"


@pytest.mark.asyncio
async def test_hc_lck_002_timed_out_call_never_enters_model_later(state, model_file):
    import asyncio

    provider = _provider(model_file)
    assert provider._ensure_initialized() is True
    try:
        r1 = await provider.generate_async(MSGS, _config(timeout=0.2))
        assert r1.finish_reason == "timeout"
        assert state.total == 1  # call 1 is still blocked inside the model
        r2 = await provider.generate_async(MSGS, _config(timeout=0.2))
        assert r2.finish_reason == "timeout"
    finally:
        state.gate.set()
    await asyncio.sleep(0.3)  # let any wrongly-queued call reach the model
    assert state.total == 1
    assert state.max_active == 1


def test_hc_lck_003_unload_waits_for_running_generation(state, model_file):
    provider = _provider(model_file)
    assert provider._ensure_initialized() is True
    model_alive_at_exit = []
    state.after_gate = lambda: model_alive_at_exit.append(provider._model is not None)
    unload_done = threading.Event()
    results = []

    gen = threading.Thread(target=lambda: results.append(provider.generate(MSGS, _config())))
    unl = threading.Thread(target=lambda: (provider.unload(), unload_done.set()))
    try:
        gen.start()
        _wait_entered(state)
        unl.start()
        assert not unload_done.wait(timeout=0.3), "unload() finished during a generation"
        assert provider._model is not None
    finally:
        state.gate.set()
    gen.join(timeout=10)
    unl.join(timeout=10)
    assert unload_done.is_set()
    assert model_alive_at_exit == [True]
    assert results and results[0].text == "ok"
    assert provider._model is None


def test_hc_lck_004_is_available_does_not_wait_for_generation(state, model_file):
    provider = _provider(model_file)
    assert provider._ensure_initialized() is True
    gen = threading.Thread(target=lambda: provider.generate(MSGS, _config()))
    out = []
    probe = threading.Thread(target=lambda: out.append((provider.is_available(), time.monotonic())))
    try:
        gen.start()
        _wait_entered(state)
        start = time.monotonic()
        probe.start()
        probe.join(timeout=2)
        assert out, "is_available() blocked behind a running generation"
        available, finished = out[0]
        assert available is True
        assert finished - start < 0.1
    finally:
        state.gate.set()
    gen.join(timeout=10)


# ---------------------------------------------------------------------------
# LLAMA-GPU-LAYERS
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_factory(monkeypatch):
    import core.llm.factory as factory

    monkeypatch.setattr(factory, "_active_provider", None)
    yield factory


def test_hc_gpu_001_settings_field_and_env(monkeypatch):
    from core.config import Settings

    monkeypatch.delenv("LLM_N_GPU_LAYERS", raising=False)
    assert Settings(_env_file=None).llm_n_gpu_layers == 0
    monkeypatch.setenv("LLM_N_GPU_LAYERS", "20")
    assert Settings(_env_file=None).llm_n_gpu_layers == 20


def test_hc_gpu_002_factory_passes_layers_llama_cpp_branch(monkeypatch, clean_factory):
    from core.config import settings

    monkeypatch.setitem(settings.__dict__, "llm_provider", "llama_cpp")
    monkeypatch.setitem(settings.__dict__, "llm_n_gpu_layers", 20)
    provider = clean_factory.get_provider(force_new=True)
    assert isinstance(provider, lcp.LlamaCppProvider)
    assert provider._n_gpu_layers == 20


def test_hc_gpu_002_factory_passes_layers_ollama_fallback(monkeypatch, clean_factory):
    from core.config import settings
    from core.llm.ollama_provider import OllamaProvider

    monkeypatch.setitem(settings.__dict__, "llm_provider", "ollama")
    monkeypatch.setitem(settings.__dict__, "llm_n_gpu_layers", 20)
    monkeypatch.setattr(OllamaProvider, "is_available", lambda self: False)
    provider = clean_factory.get_provider(force_new=True)
    assert isinstance(provider, lcp.LlamaCppProvider)
    assert provider._n_gpu_layers == 20


def test_hc_gpu_003_warns_once_without_path_when_no_gpu_build(
    state, model_file, monkeypatch, caplog
):
    import logging

    # raising=False: the helper does not exist before the fix (RED must be an assertion).
    monkeypatch.setattr(lcp, "_gpu_offload_supported", lambda: False, raising=False)
    with caplog.at_level(logging.WARNING, logger="core.llm.llama_cpp_provider"):
        assert _provider(model_file, n_gpu_layers=20)._ensure_initialized() is True
    warnings = [
        r for r in caplog.records
        if r.name == "core.llm.llama_cpp_provider" and r.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    text = warnings[0].getMessage()
    assert "20" in text
    assert str(model_file) not in text and model_file.name not in text
    assert state.ctor_kwargs[0]["n_gpu_layers"] == 20

    # Default 0: no warning, and the GPU probe is not even consulted.
    caplog.clear()
    monkeypatch.setattr(
        lcp, "_gpu_offload_supported", lambda: pytest.fail("probed with 0 layers"), raising=False
    )
    with caplog.at_level(logging.WARNING, logger="core.llm.llama_cpp_provider"):
        assert _provider(model_file)._ensure_initialized() is True
    assert not [r for r in caplog.records if r.name == "core.llm.llama_cpp_provider"]
