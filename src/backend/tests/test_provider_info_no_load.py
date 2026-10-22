"""HC-MDL-005 — GET /settings/model/provider must not load a model.

The chat page now reads this endpoint on open (CHAT-MODEL-BADGE). `available`
used to come from `provider.is_available()`, which for llama_cpp runs
`_ensure_initialized`: a synchronous GGUF load inside an async handler. Opening
the chat page must report the provider, not start a model.

Goes through HTTP via `route_client` so the `RequireAuth` dependency is real.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.model_settings import router  # noqa: E402
from core.config import settings  # noqa: E402
from tests.support.routes import route_client  # noqa: E402


class _FakeLlama:
    def __init__(self, *args, **kwargs):
        pass


def test_hc_mdl_005_provider_info_does_not_load_llama_cpp_model(monkeypatch, tmp_path):
    # A real-looking GGUF in models_path, so the old code path reaches the loader.
    (tmp_path / "phi-3-mini-q4_k_m.gguf").write_bytes(b"GGUF")
    monkeypatch.setattr(settings, "models_path", str(tmp_path))
    monkeypatch.setattr(settings, "llm_provider", "llama_cpp")
    monkeypatch.setattr(settings, "llm_model", "")
    monkeypatch.setattr("core.llm.factory._active_provider", None)

    load_calls: list[int] = []

    def _recording_loader():
        load_calls.append(1)
        return _FakeLlama

    monkeypatch.setattr("core.llm.llama_cpp_provider._load_llama_class", _recording_loader)

    with route_client(router, "/settings/model") as client:
        resp = client.get("/settings/model/provider")

    assert resp.status_code == 200, resp.text
    assert load_calls == [], "GET /settings/model/provider triggered a model load"
    body = resp.json()
    assert body["capabilities"]["provider_name"] == "llama_cpp"
    assert body["available"] is False
