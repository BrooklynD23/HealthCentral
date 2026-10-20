"""LLM-PATH-LOG: the two LLM loaders must log the GGUF file name, not its path.

The model path can contain the OS user name (home directory), so it must not
reach INFO logs. Blind spot: only records on the two named loggers are
checked, so a path logged by another logger or via print() is not seen.
"""
import logging
import sys
import types
from unittest.mock import MagicMock

from modules.model_selector import TIER_MODEL_CONFIG, ModelSelector


def _messages(caplog):
    return [r.getMessage() for r in caplog.records]


def _assert_name_only(caplog, tmp_path):
    msgs = _messages(caplog)
    assert any("x.gguf" in m for m in msgs), msgs  # not vacuous
    for m in msgs:
        assert "jane-doe-home" not in m, m
        assert str(tmp_path) not in m, m


def test_hc_mpath_001_llama_cpp_provider_logs_file_name_only(
    monkeypatch, tmp_path, caplog
):
    import core.llm.llama_cpp_provider as mod
    import modules.model_integrity as integrity

    model_path = tmp_path / "jane-doe-home" / "x.gguf"
    provider = mod.LlamaCppProvider()
    monkeypatch.setattr(provider, "_find_model_path", lambda: model_path)
    monkeypatch.setattr(
        mod, "_load_llama_class", lambda: MagicMock(return_value=MagicMock())
    )
    monkeypatch.setattr(integrity, "verify_and_log", lambda *a, **k: None)
    caplog.set_level(logging.DEBUG, logger="core.llm.llama_cpp_provider")

    assert provider._ensure_initialized() is True
    _assert_name_only(caplog, tmp_path)


def test_hc_mpath_002_model_selector_logs_file_name_only(
    monkeypatch, tmp_path, caplog
):
    model_path = tmp_path / "jane-doe-home" / "x.gguf"
    tier = next(t for t in TIER_MODEL_CONFIG if t != "template")
    fake_model = object()
    fake_llama_cpp = types.ModuleType("llama_cpp")
    fake_llama_cpp.Llama = lambda **kwargs: fake_model
    monkeypatch.setitem(sys.modules, "llama_cpp", fake_llama_cpp)
    monkeypatch.setattr(ModelSelector, "get_model_path", lambda self, t: model_path)
    caplog.set_level(logging.DEBUG, logger="modules.model_selector")

    assert ModelSelector().load_model(tier) is fake_model
    _assert_name_only(caplog, tmp_path)
