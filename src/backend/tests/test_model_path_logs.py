"""LLM-PATH-LOG: the two LLM loaders must log the GGUF file name, not its path.

The model path can contain the OS user name (home directory), so it must not
reach INFO logs. Blind spot: only records on the two named loggers are
checked, so a path logged by another logger or via print() is not seen.
"""
import logging
import sys
import types
from pathlib import Path
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


# --- LLM-PATH-LOG-M2M3: the six remaining loader log lines -----------------


def _assert_no_path(caplog, tmp_path, level, needle):
    recs = [r for r in caplog.records if r.levelno == level]
    assert recs, (level, _messages(caplog))
    assert any(needle in r.getMessage() for r in recs), _messages(caplog)
    for m in _messages(caplog):
        assert "jane-doe-home" not in m, m
        assert str(tmp_path) not in m, m


def _tier():
    return next(t for t in TIER_MODEL_CONFIG if t != "template")


def _stub_llama(monkeypatch, exc):
    def boom(**kwargs):
        raise exc

    fake = types.ModuleType("llama_cpp")
    fake.Llama = boom
    monkeypatch.setitem(sys.modules, "llama_cpp", fake)


def _stub_hf(monkeypatch, download):
    fake = types.ModuleType("huggingface_hub")
    fake.list_repo_files = lambda repo_id, **k: ["x.gguf"]
    fake.hf_hub_download = download
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)


def test_hc_mpath_003_provider_no_model_warning_omits_directory(
    monkeypatch, tmp_path, caplog
):
    import core.llm.llama_cpp_provider as mod

    provider = mod.LlamaCppProvider()
    monkeypatch.setattr(provider, "_find_model_path", lambda: None)
    monkeypatch.setattr(
        provider._settings, "models_path", str(tmp_path / "jane-doe-home" / "models")
    )
    caplog.set_level(logging.DEBUG, logger="core.llm.llama_cpp_provider")

    assert provider._ensure_initialized() is False
    _assert_no_path(caplog, tmp_path, logging.WARNING, "models")


def test_hc_mpath_004_provider_load_failure_logs_exception_type_only(
    monkeypatch, tmp_path, caplog
):
    import core.llm.llama_cpp_provider as mod
    import modules.model_integrity as integrity

    model_path = tmp_path / "jane-doe-home" / "x.gguf"
    provider = mod.LlamaCppProvider()
    monkeypatch.setattr(provider, "_find_model_path", lambda: model_path)
    monkeypatch.setattr(integrity, "verify_and_log", lambda *a, **k: None)

    def boom():
        raise ValueError(f"Failed to load model from file: {model_path}")

    monkeypatch.setattr(mod, "_load_llama_class", boom)
    caplog.set_level(logging.DEBUG, logger="core.llm.llama_cpp_provider")

    assert provider._ensure_initialized() is False
    _assert_no_path(caplog, tmp_path, logging.ERROR, "ValueError")


def test_hc_mpath_005_selector_load_failure_logs_exception_type_only(
    monkeypatch, tmp_path, caplog
):
    model_path = tmp_path / "jane-doe-home" / "x.gguf"
    _stub_llama(monkeypatch, ValueError(f"Failed to load model from file: {model_path}"))
    monkeypatch.setattr(ModelSelector, "get_model_path", lambda self, t: model_path)
    caplog.set_level(logging.DEBUG, logger="modules.model_selector")

    assert ModelSelector().load_model(_tier()) is None
    _assert_no_path(caplog, tmp_path, logging.ERROR, "ValueError")


def test_hc_mpath_006_download_success_logs_file_name_only(
    monkeypatch, tmp_path, caplog
):
    models = tmp_path / "jane-doe-home" / "models"
    _stub_hf(monkeypatch, lambda **kw: str(Path(kw["local_dir"]) / "x.gguf"))
    caplog.set_level(logging.DEBUG, logger="modules.model_selector")

    result = ModelSelector(models_path=str(models)).download_model(_tier())
    assert result == models / "x.gguf"
    _assert_no_path(caplog, tmp_path, logging.INFO, "x.gguf")


def test_hc_mpath_007_existing_model_info_logs_file_name_only(
    monkeypatch, tmp_path, caplog
):
    model_path = tmp_path / "jane-doe-home" / "x.gguf"
    monkeypatch.setattr(ModelSelector, "get_model_path", lambda self, t: model_path)
    caplog.set_level(logging.DEBUG, logger="modules.model_selector")

    assert ModelSelector().ensure_model_available() == model_path
    _assert_no_path(caplog, tmp_path, logging.INFO, "x.gguf")


def test_hc_mpath_008_download_failure_logs_exception_type_only(
    monkeypatch, tmp_path, caplog
):
    models = tmp_path / "jane-doe-home" / "models"

    def boom(**kw):
        raise PermissionError(13, "Permission denied", str(Path(kw["local_dir"]) / "x.gguf"))

    _stub_hf(monkeypatch, boom)
    caplog.set_level(logging.DEBUG, logger="modules.model_selector")

    assert ModelSelector(models_path=str(models)).download_model(_tier()) is None
    _assert_no_path(caplog, tmp_path, logging.ERROR, "PermissionError")
