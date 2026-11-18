"""HC-MDL-004/005 — GET /settings/model/provider?probe=false must not load a model.

The chat page reads this endpoint on open (CHAT-MODEL-BADGE) only to name the
active model. `available=provider.is_available()` runs `_ensure_initialized` on
llama_cpp: a synchronous GGUF load inside an async handler. `probe=false` skips
it and reports `available: null`; the default stays exactly as it was.

Goes through HTTP via `route_client` so the `RequireAuth` dependency is real.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.model_settings import router  # noqa: E402
from core.config import settings  # noqa: E402
from core.llm import factory  # noqa: E402
from tests.support.routes import route_client  # noqa: E402

URL = "/settings/model/provider"


class _Recorder:
    """Stands in for llama_cpp.Llama and records every construction."""

    constructed = 0

    def __init__(self, *args, **kwargs):
        type(self).constructed += 1


@pytest.fixture
def default_llama_cpp(monkeypatch, tmp_path):
    """Default config (llama_cpp, no LLM_MODEL) with a dummy GGUF the loader can find."""
    (tmp_path / "phi-3-mini-q4_k_m.gguf").write_bytes(b"GGUF")
    monkeypatch.setattr(settings, "models_path", str(tmp_path))
    monkeypatch.setattr(settings, "llm_provider", "llama_cpp")
    monkeypatch.setattr(settings, "llm_model", "")
    monkeypatch.setattr("core.llm.llama_cpp_provider._load_llama_class", lambda: _Recorder)
    _Recorder.constructed = 0
    factory._active_provider = None
    try:
        yield _Recorder
    finally:
        factory._active_provider = None
        _Recorder.constructed = 0


def test_hc_mdl_004_probe_false_does_not_load_the_model(default_llama_cpp):
    rec = default_llama_cpp

    with route_client(router, "/settings/model") as client:
        resp = client.get(URL, params={"probe": "false"})

        assert resp.status_code == 200, resp.text
        assert rec.constructed == 0, "probe=false constructed the model"
        body = resp.json()
        assert body["available"] is None
        assert body["capabilities"]["provider_name"] == "llama_cpp"

        # Control: with a fresh provider cache the default call DOES load, so the
        # zero above cannot be an artefact of the fake or the dummy GGUF.
        factory._active_provider = None
        resp = client.get(URL)
        assert resp.status_code == 200, resp.text
        assert rec.constructed == 1, "default call should load (control)"


def test_hc_mdl_005_default_call_is_unchanged(default_llama_cpp):
    rec = default_llama_cpp
    with route_client(router, "/settings/model") as client:
        resp = client.get(URL)

    assert resp.status_code == 200, resp.text
    # The setup reaches the constructor, so HC-MDL-004's "not constructed" can fail.
    assert rec.constructed == 1
    body = resp.json()
    assert isinstance(body["available"], bool)
    assert set(body) == {
        "llm_provider",
        "llm_model",
        "ollama_base_url",
        "available",
        "capabilities",
    }
