"""HC-BTK-002: capabilities() names the auto-detected GGUF without loading it."""

from types import SimpleNamespace

import core.llm.llama_cpp_provider as lcp
from core.llm.llama_cpp_provider import LlamaCppProvider


def test_hc_btk_002_capabilities_names_auto_detected_gguf(tmp_path, monkeypatch):
    (tmp_path / "gemma-4-e4b-it-Q4_K_M.gguf").write_bytes(b"x")

    def _no_load():
        raise AssertionError("capabilities() must not load or construct Llama")

    monkeypatch.setattr(lcp, "_load_llama_class", _no_load)

    provider = LlamaCppProvider()  # no model_path
    provider._settings = SimpleNamespace(
        models_path=str(tmp_path), default_chat_model="phi-3-mini"
    )

    assert provider.capabilities().model_name == "gemma-4-e4b-it-Q4_K_M"
