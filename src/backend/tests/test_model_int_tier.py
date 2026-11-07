"""MODEL-INT-TIER: the load-time integrity check is keyed by the loaded file.

`LlamaCppProvider` used to ask `Settings` for `llm_model_tier`, which does not
exist, so every load was checked against tier "low" whatever file it loaded.
The provider loads the first GGUF it finds, so the loaded file's name is the
only true key: the manifest entry whose `filename` matches (case-folded), else
"unrecognised".

Blind spot: only records on the "modules.model_integrity" logger are checked.
The provider's own log lines are covered by HC-MPATH-001, not here.
"""
import hashlib
import json
import logging
from unittest.mock import MagicMock

import pytest

import core.llm.llama_cpp_provider as provider_mod
import modules.model_integrity as integrity

_LOGGER = "modules.model_integrity"
_GOOD_BYTES = b"pretend gguf bytes"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_manifest(tmp_path, models):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"manifest_version": 1, "models": models}), encoding="utf-8")
    return path


def _load(monkeypatch, tmp_path, caplog, manifest_models, model_file):
    """Run `_ensure_initialized` on `model_file` against a temp manifest."""
    manifest = _write_manifest(tmp_path, manifest_models)
    monkeypatch.setattr(integrity, "_DEFAULT_MANIFEST", manifest)
    monkeypatch.setattr(
        provider_mod, "_load_llama_class", lambda: MagicMock(return_value=MagicMock())
    )
    integrity.clear_hash_cache()
    provider = provider_mod.LlamaCppProvider()
    monkeypatch.setattr(provider, "_find_model_path", lambda: model_file)
    caplog.set_level(logging.DEBUG, logger=_LOGGER)

    assert provider._ensure_initialized() is True
    return [r for r in caplog.records if r.name == _LOGGER]


@pytest.fixture(autouse=True)
def _clean_cache():
    integrity.clear_hash_cache()
    yield
    integrity.clear_hash_cache()


def test_hc_mtier_001_loaded_file_name_selects_manifest_key(monkeypatch, tmp_path, caplog):
    model = tmp_path / "phi-3-mini-q4_k_m.gguf"
    model.write_bytes(_GOOD_BYTES)
    models = {
        # Upper-case in the manifest, lower-case on disk: matched case-folded.
        "mid": {"filename": "PHI-3-Mini-Q4_K_M.gguf", "sha256": _sha(_GOOD_BYTES)},
        "low": {"filename": "qwen-low.gguf", "sha256": _sha(b"something else")},
    }

    recs = _load(monkeypatch, tmp_path, caplog, models, model)

    msgs = [r.getMessage() for r in recs]
    assert len(recs) == 1, msgs
    assert recs[0].levelno == logging.INFO, msgs
    assert "tier 'mid'" in msgs[0] and "matches its pinned SHA256" in msgs[0], msgs
    assert not any(r.levelno >= logging.WARNING for r in recs), msgs
    assert not any(model.name in m or str(tmp_path) in m for m in msgs), msgs


def test_hc_mtier_002_unrelated_file_is_not_checked_against_low(monkeypatch, tmp_path, caplog):
    model = tmp_path / "other.gguf"
    model.write_bytes(_GOOD_BYTES)
    models = {"low": {"filename": "qwen-low.gguf", "sha256": _sha(b"low's real bytes")}}

    recs = _load(monkeypatch, tmp_path, caplog, models, model)

    msgs = [r.getMessage() for r in recs]
    assert not any(r.levelno >= logging.ERROR for r in recs), msgs
    assert len(recs) == 1, msgs
    assert recs[0].levelno == logging.WARNING, msgs
    assert "No manifest entry for tier 'unrecognised'" in msgs[0], msgs
    assert not any("'low'" in m for m in msgs), msgs
    assert not any(model.name in m or str(tmp_path) in m for m in msgs), msgs


def test_hc_mtier_003_file_named_as_low_with_wrong_bytes_is_a_mismatch(
    monkeypatch, tmp_path, caplog
):
    model = tmp_path / "qwen-low.gguf"
    model.write_bytes(b"tampered bytes")
    models = {"low": {"filename": "qwen-low.gguf", "sha256": _sha(_GOOD_BYTES)}}

    recs = _load(monkeypatch, tmp_path, caplog, models, model)

    msgs = [r.getMessage() for r in recs]
    errors = [r for r in recs if r.levelno == logging.ERROR]
    assert len(errors) == 1, msgs
    assert "tier 'low'" in errors[0].getMessage(), msgs
    assert "does NOT match" in errors[0].getMessage(), msgs


def test_hc_mtier_004_nothing_is_hashed_when_no_entry_names_the_file(
    monkeypatch, tmp_path, caplog
):
    model = tmp_path / "other.gguf"
    model.write_bytes(_GOOD_BYTES)
    models = {
        "low": {"filename": "qwen-low.gguf", "sha256": _sha(_GOOD_BYTES)},
        # Pattern-only entry: filename is null and must be skipped, not matched.
        "mid": {"filename": None, "filename_pattern": "gguf", "sha256": _sha(_GOOD_BYTES)},
    }
    calls = []
    real = integrity.compute_sha256

    def spy(path, **kwargs):
        calls.append(path)
        return real(path, **kwargs)

    monkeypatch.setattr(integrity, "compute_sha256", spy)

    recs = _load(monkeypatch, tmp_path, caplog, models, model)

    assert calls == [], calls
    assert [r.levelno for r in recs] == [logging.WARNING], [r.getMessage() for r in recs]
