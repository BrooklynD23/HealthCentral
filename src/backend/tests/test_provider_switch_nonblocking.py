"""HC-LUL-001/002/003: switching provider must not block the event loop.

PUT /settings/model/provider used to call reset_provider() synchronously.
LlamaCppProvider.unload() takes the model lock, which a running generation
holds, so the whole event loop stalled. These tests go through HTTP with one
shared portal loop (route_client holds the TestClient open with `with`).
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.config
import core.llm.factory as factory
import core.llm.llama_cpp_provider as lcp
from api import model_settings
from core.llm.provider import ChatMessage
from core.model_runner import InferenceConfig
from tests.support.routes import route_client


class _FakeProvider:
    """unload() blocks until released, like a provider mid-generation."""

    def __init__(self, block: bool) -> None:
        self.block = block
        self.entered = threading.Event()
        self.release = threading.Event()
        self.unload_calls = 0

    def unload(self) -> None:
        self.unload_calls += 1
        if self.block:
            self.entered.set()
            self.release.wait(timeout=10)

    def capabilities(self):
        return SimpleNamespace(
            context_len=4096,
            multimodal=False,
            function_calling=False,
            streaming=True,
            provider_name="fake",
            model_name="fake-model",
        )

    def is_available(self) -> bool:
        return True


@pytest.fixture
def providers(monkeypatch):
    first = _FakeProvider(block=True)
    second = _FakeProvider(block=False)
    s = core.config.settings
    monkeypatch.setattr(s, "llm_provider", s.llm_provider)
    monkeypatch.setattr(s, "llm_model", s.llm_model)
    monkeypatch.setattr(factory, "_active_provider", first)

    def fake_get_provider():
        # Like the real factory: build once, then cache in the global.
        if factory._active_provider is None:
            factory._active_provider = second
        return factory._active_provider

    monkeypatch.setattr(factory, "get_provider", fake_get_provider)
    return first, second


def _put_in_thread(client, result: dict) -> threading.Thread:
    def run() -> None:
        result["resp"] = client.put(
            "/settings/model/provider",
            json={"llm_provider": "llama_cpp", "llm_model": ""},
        )

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def test_hc_lul_001_get_answers_while_provider_switch_unloads(providers):
    first, _ = providers
    result: dict = {}
    with route_client(model_settings.router, "/settings/model") as client:
        t = _put_in_thread(client, result)
        try:
            assert first.entered.wait(timeout=5), "unload never started"
            start = time.monotonic()
            resp = client.get("/settings/model/provider?probe=false")
            elapsed = time.monotonic() - start
        finally:
            first.release.set()
            t.join(timeout=10)
    assert resp.status_code == 200
    assert elapsed < 1.0, f"event loop blocked {elapsed:.2f}s by provider switch"


def test_hc_lul_002_switch_completes_and_replaces_provider(providers):
    first, second = providers
    result: dict = {}
    with route_client(model_settings.router, "/settings/model") as client:
        t = _put_in_thread(client, result)
        try:
            assert first.entered.wait(timeout=5), "unload never started"
        finally:
            first.release.set()
            t.join(timeout=10)
    assert result["resp"].status_code == 200
    assert result["resp"].json()["llm_provider"] == "llama_cpp"
    assert first.unload_calls == 1
    assert factory._active_provider is second


def test_hc_lul_003_old_provider_never_reloads_after_a_switch(monkeypatch, tmp_path):
    """A generation queued on the old provider must not rebuild Llama.

    reset_provider runs in a thread now, so requests keep arriving while
    unload() waits on the model lock. The old instance must be detached from
    the factory first and refuse to reload once unloaded.
    """
    loads: list = []
    entered = threading.Event()
    gate = threading.Event()

    class _FakeLlama:
        def __init__(self, **kwargs):
            loads.append(kwargs)

        def create_chat_completion(self, **kwargs):
            entered.set()
            gate.wait(timeout=10)
            return {
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"completion_tokens": 1},
            }

    monkeypatch.setattr(lcp, "_load_llama_class", lambda: _FakeLlama)
    model = tmp_path / "x.gguf"
    model.write_bytes(b"GGUF")
    s = core.config.settings
    monkeypatch.setattr(s, "llm_provider", "llama_cpp")
    monkeypatch.setattr(s, "llm_model", "")
    old = lcp.LlamaCppProvider(model_path=str(model))
    monkeypatch.setattr(factory, "_active_provider", old)

    assert old._ensure_initialized() is True
    assert len(loads) == 1

    msgs = [ChatMessage(role="user", content="hi")]
    cfg = InferenceConfig(
        max_tokens=16, temperature=0.1, top_p=0.9, stop_sequences=None,
        timeout_seconds=5,
    )

    def run(fn):
        def go():
            try:
                fn()
            except Exception:
                pass  # outcome of the stale call is judged by `loads`

        t = threading.Thread(target=go, daemon=True)
        t.start()
        return t

    threads = []
    try:
        threads.append(run(lambda: old.generate(msgs, cfg)))  # holds model lock
        assert entered.wait(timeout=5), "generation never started"
        threads.append(run(factory.reset_provider))  # unload waits on model lock
        deadline = time.monotonic() + 2
        while factory._active_provider is old and time.monotonic() < deadline:
            time.sleep(0.01)
        threads.append(run(lambda: old.generate(msgs, cfg)))  # queued on OLD
        time.sleep(0.2)  # let it reach the model lock
    finally:
        gate.set()
        for t in threads:
            t.join(timeout=10)

    assert len(loads) == 1, "old provider rebuilt Llama after the switch"
    assert factory.get_provider() is not old
