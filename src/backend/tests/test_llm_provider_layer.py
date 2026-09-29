"""
tests/test_llm_provider_layer.py

Unit tests for the model-agnostic LLM provider layer.

Covered:
  - ProviderProtocol structural interface
  - CapabilityFlags dataclass
  - LlamaCppProvider (llama_cpp import mocked — no real model needed)
  - OllamaProvider (httpx mocked — no real daemon needed)
  - OllamaProvider localhost enforcement
  - ModelRunner facade routing
  - factory.get_provider() provider selection
  - model_selector TIER_MODEL_CONFIG Gemma 4 entries
  - hardware_detection TIER_REQUIREMENTS Gemma 4 entries

Python 3.10-compatible: no 3.11+ syntax.
"""

from __future__ import annotations

import asyncio
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup: ensure src/backend is importable
# ---------------------------------------------------------------------------
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine in a fresh event loop (avoids closed-loop issues in pytest)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def _make_inference_config(**kwargs):
    from core.model_runner import InferenceConfig
    defaults = dict(max_tokens=64, temperature=0.1, top_p=0.9,
                    stop_sequences=None, timeout_seconds=30)
    defaults.update(kwargs)
    return InferenceConfig(**defaults)


def _make_inference_result(**kwargs):
    from core.model_runner import InferenceResult
    defaults = dict(text="hello", tokens_generated=5,
                    finish_reason="stop", model_name="test")
    defaults.update(kwargs)
    return InferenceResult(**defaults)


# ===========================================================================
# 1. CapabilityFlags
# ===========================================================================

class TestCapabilityFlags:
    def test_defaults(self):
        from core.llm.provider import CapabilityFlags
        caps = CapabilityFlags()
        assert caps.context_len == 4096
        assert caps.multimodal is False
        assert caps.function_calling is False
        assert caps.streaming is False

    def test_custom_values(self):
        from core.llm.provider import CapabilityFlags
        caps = CapabilityFlags(
            context_len=262144,
            multimodal=True,
            function_calling=True,
            streaming=True,
            provider_name="ollama",
            model_name="gemma4:12b",
        )
        assert caps.context_len == 262144
        assert caps.multimodal is True
        assert caps.provider_name == "ollama"
        assert caps.model_name == "gemma4:12b"


# ===========================================================================
# 2. LlamaCppProvider — mocked llama_cpp
# ===========================================================================

class TestLlamaCppProvider:
    """All tests mock out llama_cpp so no native library is required."""

    def _make_provider(self, model_path="/fake/model.gguf"):
        from core.llm.llama_cpp_provider import LlamaCppProvider
        return LlamaCppProvider(model_path=model_path)

    def _mock_llama_class(self, provider, response_text="test response"):
        """Patch _load_llama_class and pre-initialise the provider's model."""
        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = {
            "choices": [{"message": {"content": response_text}, "finish_reason": "stop"}],
            "usage": {"completion_tokens": 10},
        }
        # Bypass file-existence check and model loading
        provider._initialized = True
        provider._model = mock_model
        return mock_model

    # --- is_available ---

    def test_is_available_false_when_no_model_file(self):
        from core.llm.llama_cpp_provider import LlamaCppProvider
        p = LlamaCppProvider(model_path="/nonexistent/path.gguf")
        # _find_model_path returns None -> _ensure_initialized returns False
        assert p.is_available() is False

    def test_is_available_true_when_model_loaded(self):
        p = self._make_provider()
        self._mock_llama_class(p)
        assert p.is_available() is True

    # --- capabilities ---

    def test_capabilities_default_model(self):
        from core.llm.llama_cpp_provider import LlamaCppProvider
        p = LlamaCppProvider()
        caps = p.capabilities()
        assert caps.provider_name == "llama_cpp"
        assert isinstance(caps.context_len, int)

    def test_capabilities_gemma4_path(self):
        from core.llm.llama_cpp_provider import LlamaCppProvider
        p = LlamaCppProvider(model_path="/models/gemma4-12b-q4_k_m.gguf")
        caps = p.capabilities()
        assert caps.multimodal is True
        assert caps.function_calling is True

    def test_capabilities_non_gemma4(self):
        from core.llm.llama_cpp_provider import LlamaCppProvider
        p = LlamaCppProvider(model_path="/models/phi-3-mini.gguf")
        caps = p.capabilities()
        assert caps.multimodal is False
        assert caps.function_calling is False

    # --- generate ---

    def test_generate_returns_inference_result(self):
        from core.llm.provider import ChatMessage
        p = self._make_provider()
        self._mock_llama_class(p, response_text="glucose is normal")
        cfg = _make_inference_config()
        msgs = [ChatMessage(role="user", content="What is glucose?")]
        result = p.generate(msgs, cfg)
        from core.model_runner import InferenceResult
        assert isinstance(result, InferenceResult)
        assert result.text == "glucose is normal"
        assert result.finish_reason == "stop"

    def test_generate_raises_unavailable_when_no_model(self):
        from core.llm.llama_cpp_provider import LlamaCppProvider
        from core.llm.provider import ChatMessage, ProviderUnavailableError
        p = LlamaCppProvider(model_path="/nonexistent.gguf")
        cfg = _make_inference_config()
        msgs = [ChatMessage(role="user", content="hello")]
        with pytest.raises(ProviderUnavailableError):
            p.generate(msgs, cfg)

    def test_generate_uses_chat_completion_api(self):
        from core.llm.provider import ChatMessage
        p = self._make_provider()
        mock_model = self._mock_llama_class(p)
        cfg = _make_inference_config()
        msgs = [ChatMessage(role="user", content="test")]
        p.generate(msgs, cfg)
        mock_model.create_chat_completion.assert_called_once()
        call_kwargs = mock_model.create_chat_completion.call_args
        assert call_kwargs is not None
        # messages param should be in the call
        passed_messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
        assert any(m["role"] == "user" for m in passed_messages)

    # --- generate_async ---

    def test_generate_async_returns_result(self):
        from core.llm.provider import ChatMessage
        p = self._make_provider()
        self._mock_llama_class(p, response_text="async response")
        cfg = _make_inference_config()
        msgs = [ChatMessage(role="user", content="async?")]
        result = _run(p.generate_async(msgs, cfg))
        from core.model_runner import InferenceResult
        assert isinstance(result, InferenceResult)
        assert result.text == "async response"

    def test_generate_async_timeout_returns_graceful_message(self):
        from core.llm.provider import ChatMessage
        from core.llm.llama_cpp_provider import LlamaCppProvider
        import time

        p = LlamaCppProvider(model_path="/fake/model.gguf")
        p._initialized = True
        # Simulate a very slow model
        slow_model = MagicMock()
        def _slow_complete(**kwargs):
            time.sleep(5)
            return {"choices": [{"message": {"content": "late"}, "finish_reason": "stop"}], "usage": {}}
        slow_model.create_chat_completion.side_effect = _slow_complete
        p._model = slow_model

        cfg = _make_inference_config(timeout_seconds=1)
        msgs = [ChatMessage(role="user", content="slow")]
        result = _run(p.generate_async(msgs, cfg))
        from core.model_runner import InferenceResult
        assert isinstance(result, InferenceResult)
        assert result.finish_reason == "timeout"
        assert "apologize" in result.text.lower() or "longer" in result.text.lower()

    # --- unload ---

    def test_unload_clears_model(self):
        p = self._make_provider()
        self._mock_llama_class(p)
        assert p._model is not None
        p.unload()
        assert p._model is None
        assert p._initialized is False

    # --- health_check ---

    def test_health_check_loaded(self):
        p = self._make_provider()
        self._mock_llama_class(p)
        h = p.health_check()
        assert h["healthy"] is True
        assert h["provider"] == "llama_cpp"

    def test_health_check_not_loaded(self):
        from core.llm.llama_cpp_provider import LlamaCppProvider
        p = LlamaCppProvider(model_path="/nonexistent.gguf")
        h = p.health_check()
        assert h["healthy"] is False


# ===========================================================================
# 3. OllamaProvider — mocked httpx
# ===========================================================================

class TestOllamaProvider:

    def _make_provider(self, model="gemma4:12b"):
        from core.llm.ollama_provider import OllamaProvider
        return OllamaProvider(model=model, base_url="http://127.0.0.1:11434")

    def _mock_probe_available(self, provider):
        provider._available = True

    def _mock_probe_unavailable(self, provider):
        provider._available = False

    # --- localhost enforcement ---

    def test_refuses_non_local_url(self):
        from core.llm.ollama_provider import OllamaProvider
        with pytest.raises(ValueError, match="non-local"):
            OllamaProvider(base_url="http://remote-server.example.com:11434")

    def test_refuses_public_ip(self):
        from core.llm.ollama_provider import OllamaProvider
        with pytest.raises(ValueError, match="non-local"):
            OllamaProvider(base_url="http://192.168.1.50:11434")

    def test_accepts_127_0_0_1(self):
        from core.llm.ollama_provider import OllamaProvider
        p = OllamaProvider(base_url="http://127.0.0.1:11434")
        assert p._base_url == "http://127.0.0.1:11434"

    def test_accepts_localhost(self):
        from core.llm.ollama_provider import OllamaProvider
        p = OllamaProvider(base_url="http://localhost:11434")
        assert p._base_url == "http://localhost:11434"

    # --- is_available ---

    def test_is_available_true_when_probe_succeeds(self):
        p = self._make_provider()
        with patch.object(p, "_probe_sync", return_value=True):
            assert p.is_available() is True

    def test_is_available_false_when_probe_fails(self):
        p = self._make_provider()
        with patch.object(p, "_probe_sync", return_value=False):
            assert p.is_available() is False

    # --- capabilities ---

    def test_capabilities_gemma4(self):
        p = self._make_provider("gemma4:12b")
        caps = p.capabilities()
        assert caps.multimodal is True
        assert caps.function_calling is True
        assert caps.streaming is True
        assert caps.context_len == 262144
        assert caps.provider_name == "ollama"

    def test_capabilities_non_gemma4(self):
        p = self._make_provider("llama3:8b")
        caps = p.capabilities()
        assert caps.multimodal is False
        assert caps.function_calling is False
        assert caps.context_len == 8192

    # --- generate (mocked httpx.Client) ---

    def test_generate_success(self):
        import httpx
        p = self._make_provider()
        self._mock_probe_available(p)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Your glucose is normal."},
            "done": True,
            "eval_count": 8,
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response

        from core.llm.provider import ChatMessage
        cfg = _make_inference_config()
        msgs = [ChatMessage(role="user", content="glucose?")]

        with patch("core.llm.ollama_provider.OllamaProvider._make_client",
                   return_value=mock_client):
            result = p.generate(msgs, cfg)

        from core.model_runner import InferenceResult
        assert isinstance(result, InferenceResult)
        assert result.text == "Your glucose is normal."
        assert result.tokens_generated == 8
        assert result.finish_reason == "stop"

    def test_generate_raises_unavailable_when_daemon_down(self):
        from core.llm.ollama_provider import OllamaProvider
        from core.llm.provider import ChatMessage, ProviderUnavailableError
        p = OllamaProvider()
        self._mock_probe_unavailable(p)
        cfg = _make_inference_config()
        msgs = [ChatMessage(role="user", content="hi")]
        with pytest.raises(ProviderUnavailableError, match="not reachable"):
            p.generate(msgs, cfg)

    def test_generate_request_body_shape(self):
        """Verify the Ollama API payload has the expected fields."""
        p = self._make_provider("gemma4:e4b")
        self._mock_probe_available(p)

        captured = {}
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "ok"},
            "done": True,
            "eval_count": 3,
        }
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        def _capture_post(url, json=None, **kw):
            captured.update(json or {})
            return mock_response
        mock_client.post.side_effect = _capture_post

        from core.llm.provider import ChatMessage
        cfg = _make_inference_config(max_tokens=512, temperature=0.2)
        msgs = [ChatMessage(role="user", content="hi")]
        with patch("core.llm.ollama_provider.OllamaProvider._make_client",
                   return_value=mock_client):
            p.generate(msgs, cfg)

        assert captured["model"] == "gemma4:e4b"
        assert captured["stream"] is False
        assert captured["options"]["num_predict"] == 512
        assert captured["options"]["temperature"] == pytest.approx(0.2)
        assert "messages" in captured
        assert captured["messages"][0]["role"] == "user"

    # --- generate_async (mocked httpx.AsyncClient) ---

    def test_generate_async_success(self):
        p = self._make_provider()
        self._mock_probe_available(p)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "async glucose"},
            "done": True,
            "eval_count": 4,
        }

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_async_client.post = AsyncMock(return_value=mock_response)

        from core.llm.provider import ChatMessage
        cfg = _make_inference_config()
        msgs = [ChatMessage(role="user", content="async glucose?")]

        with patch("core.llm.ollama_provider.OllamaProvider._make_async_client",
                   return_value=mock_async_client):
            result = _run(p.generate_async(msgs, cfg)
            )

        from core.model_runner import InferenceResult
        assert isinstance(result, InferenceResult)
        assert result.text == "async glucose"

    # --- health_check ---

    def test_health_check_healthy(self):
        p = self._make_provider()
        with patch.object(p, "_probe_sync", return_value=True):
            h = p.health_check()
        assert h["healthy"] is True
        assert h["provider"] == "ollama"

    def test_health_check_unhealthy(self):
        p = self._make_provider()
        with patch.object(p, "_probe_sync", return_value=False):
            h = p.health_check()
        assert h["healthy"] is False

    # --- unload (no-op for Ollama) ---

    def test_unload_is_noop(self):
        p = self._make_provider()
        self._mock_probe_available(p)
        p.unload()  # should not raise
        assert p._available is None  # cache reset


# ===========================================================================
# 4. ModelRunner facade
# ===========================================================================

class TestModelRunnerFacade:
    """ModelRunner wraps providers; test routing logic with mock providers."""

    def _make_runner_with_mock_provider(self, provider=None):
        from core.model_runner import ModelRunner
        if provider is None:
            provider = MagicMock()
            provider.is_available.return_value = True
            provider.generate.return_value = _make_inference_result(text="facade result")
            provider.generate_async = AsyncMock(
                return_value=_make_inference_result(text="async facade")
            )
            provider.unload = MagicMock()
        return ModelRunner(_provider=provider), provider

    def test_is_available_delegates_to_provider(self):
        runner, mock_p = self._make_runner_with_mock_provider()
        mock_p.is_available.return_value = True
        assert runner.is_available() is True
        mock_p.is_available.return_value = False
        assert runner.is_available() is False

    def test_generate_wraps_prompt_as_user_message(self):
        runner, mock_p = self._make_runner_with_mock_provider()
        from core.model_runner import InferenceConfig
        cfg = _make_inference_config()
        result = runner.generate("What is glucose?", cfg)
        assert mock_p.generate.called
        call_args = mock_p.generate.call_args
        messages = call_args.args[0] if call_args.args else call_args.kwargs.get("messages", [])
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "What is glucose?"

    def test_generate_returns_inference_result(self):
        runner, _ = self._make_runner_with_mock_provider()
        from core.model_runner import InferenceResult
        result = runner.generate("prompt")
        assert isinstance(result, InferenceResult)
        assert result.text == "facade result"

    def test_generate_raises_runtime_error_on_unavailable(self):
        from core.llm.provider import ProviderUnavailableError
        mock_p = MagicMock()
        mock_p.is_available.return_value = False
        mock_p.generate.side_effect = ProviderUnavailableError("not ready")
        runner, _ = self._make_runner_with_mock_provider(provider=mock_p)
        with pytest.raises(RuntimeError, match="not ready"):
            runner.generate("hi")

    def test_generate_async_routes_to_provider(self):
        runner, mock_p = self._make_runner_with_mock_provider()
        from core.model_runner import InferenceResult
        result = _run(runner.generate_async("async prompt")
        )
        assert isinstance(result, InferenceResult)
        assert result.text == "async facade"

    def test_unload_delegates_to_provider(self):
        runner, mock_p = self._make_runner_with_mock_provider()
        runner.unload()
        mock_p.unload.assert_called_once()

    def test_is_available_returns_false_on_exception(self):
        mock_p = MagicMock()
        mock_p.is_available.side_effect = RuntimeError("crash")
        runner, _ = self._make_runner_with_mock_provider(provider=mock_p)
        assert runner.is_available() is False


# ===========================================================================
# 5. factory.get_provider()
# ===========================================================================

class TestFactory:

    def test_default_provider_is_llama_cpp(self):
        from core.llm import factory as fac
        fac._active_provider = None
        with patch("core.config.settings") as mock_settings:
            mock_settings.llm_provider = "llama_cpp"
            mock_settings.llm_model = ""
            mock_settings.chat_context_size = 4096
            mock_settings.inference_threads = 0
            mock_settings.models_path = "/tmp/models"
            mock_settings.default_chat_model = "phi-3-mini"
            mock_settings.debug = False
            fac._active_provider = None
            provider = fac.get_provider(force_new=True)
        from core.llm.llama_cpp_provider import LlamaCppProvider
        assert isinstance(provider, LlamaCppProvider)
        fac._active_provider = None

    def test_ollama_provider_selected_when_configured(self):
        from core.llm import factory as fac
        fac._active_provider = None
        with patch("core.config.settings") as mock_settings:
            mock_settings.llm_provider = "ollama"
            mock_settings.llm_model = "gemma4:12b"
            mock_settings.chat_context_size = 4096
            mock_settings.ollama_base_url = "http://127.0.0.1:11434"
            # Patch Ollama probe to simulate daemon available
            with patch("core.llm.ollama_provider.OllamaProvider._probe_sync",
                       return_value=True):
                provider = fac.get_provider(force_new=True)
        from core.llm.ollama_provider import OllamaProvider
        assert isinstance(provider, OllamaProvider)
        fac._active_provider = None

    def test_ollama_falls_back_to_llamacpp_if_daemon_down(self):
        from core.llm import factory as fac
        fac._active_provider = None
        with patch("core.config.settings") as mock_settings:
            mock_settings.llm_provider = "ollama"
            mock_settings.llm_model = "gemma4:12b"
            mock_settings.chat_context_size = 4096
            mock_settings.ollama_base_url = "http://127.0.0.1:11434"
            mock_settings.inference_threads = 0
            mock_settings.models_path = "/tmp/models"
            mock_settings.default_chat_model = "phi-3-mini"
            mock_settings.debug = False
            with patch("core.llm.ollama_provider.OllamaProvider._probe_sync",
                       return_value=False):
                provider = fac.get_provider(force_new=True)
        from core.llm.llama_cpp_provider import LlamaCppProvider
        assert isinstance(provider, LlamaCppProvider)
        fac._active_provider = None

    def test_reset_provider_clears_singleton(self):
        from core.llm import factory as fac
        from core.llm.llama_cpp_provider import LlamaCppProvider
        fac._active_provider = LlamaCppProvider()
        fac.reset_provider()
        assert fac._active_provider is None

    def test_unknown_provider_defaults_to_llamacpp(self):
        from core.llm import factory as fac
        fac._active_provider = None
        with patch("core.config.settings") as mock_settings:
            mock_settings.llm_provider = "foobar_unknown"
            mock_settings.llm_model = ""
            mock_settings.chat_context_size = 4096
            mock_settings.inference_threads = 0
            mock_settings.models_path = "/tmp/models"
            mock_settings.default_chat_model = "phi-3-mini"
            mock_settings.debug = False
            provider = fac.get_provider(force_new=True)
        from core.llm.llama_cpp_provider import LlamaCppProvider
        assert isinstance(provider, LlamaCppProvider)
        fac._active_provider = None


# ===========================================================================
# 6. Model registry — Gemma 4 entries
# ===========================================================================

class TestModelRegistry:

    def test_gemma4_tiers_present(self):
        from modules.model_selector import TIER_MODEL_CONFIG
        assert "gemma4-e2b" in TIER_MODEL_CONFIG
        assert "gemma4-e4b" in TIER_MODEL_CONFIG
        assert "gemma4-12b" in TIER_MODEL_CONFIG

    def test_gemma4_e2b_fields(self):
        from modules.model_selector import TIER_MODEL_CONFIG
        cfg = TIER_MODEL_CONFIG["gemma4-e2b"]
        assert cfg["multimodal"] is True
        assert cfg["function_calling"] is True
        assert cfg["ollama_tag"] == "gemma4:e2b"
        assert "unsloth" in cfg["repo"].lower() or "ggml-org" in cfg["repo"].lower()

    def test_gemma4_e4b_fields(self):
        from modules.model_selector import TIER_MODEL_CONFIG
        cfg = TIER_MODEL_CONFIG["gemma4-e4b"]
        assert cfg["multimodal"] is True
        assert cfg["ollama_tag"] == "gemma4:e4b"
        assert cfg["context_size"] > 4096  # should be >= 16K

    def test_gemma4_12b_fields(self):
        from modules.model_selector import TIER_MODEL_CONFIG
        cfg = TIER_MODEL_CONFIG["gemma4-12b"]
        assert cfg["multimodal"] is True
        assert cfg["function_calling"] is True
        assert cfg["ollama_tag"] == "gemma4:12b"
        assert cfg["context_size"] >= 32768

    def test_mid_tier_is_phi4_mini(self):
        """HC-TIER-001: the mid tier runs Phi-4-mini, not Phi-3-mini.

        Phi-3-mini-4k caps at a 4K context, which is too small to hold
        retrieved chunks plus a tool menu plus a question. Phi-4-mini is the
        same size class and MIT-licensed, with a far larger context. Requires
        llama-cpp-python >= 0.3.35 — Phi-4-mini postdates the 0.3.2 wheel the
        project pinned before this change.
        """
        from modules.model_selector import TIER_MODEL_CONFIG
        cfg = TIER_MODEL_CONFIG["mid"]
        assert "phi-4-mini" in cfg["repo"].lower(), cfg["repo"]
        assert cfg["context_size"] > 4096, (
            "the whole point of the swap is escaping Phi-3-mini's 4K window"
        )

    def test_legacy_tiers_still_present(self):
        from modules.model_selector import TIER_MODEL_CONFIG
        for tier in ("low", "mid", "high"):
            assert tier in TIER_MODEL_CONFIG, f"Legacy tier '{tier}' missing"

    def test_all_tiers_have_repo(self):
        from modules.model_selector import TIER_MODEL_CONFIG
        for tier, cfg in TIER_MODEL_CONFIG.items():
            assert cfg.get("repo"), f"Tier '{tier}' missing 'repo'"


# ===========================================================================
# 7. Hardware detection — Gemma 4 tier requirements
# ===========================================================================

class TestHardwareDetectionGemma4:

    def test_gemma4_tiers_in_requirements(self):
        from modules.hardware_detection import TIER_REQUIREMENTS
        assert "gemma4-e2b" in TIER_REQUIREMENTS
        assert "gemma4-e4b" in TIER_REQUIREMENTS
        assert "gemma4-12b" in TIER_REQUIREMENTS

    def test_gemma4_e2b_ram_requirement(self):
        from modules.hardware_detection import TIER_REQUIREMENTS
        req = TIER_REQUIREMENTS["gemma4-e2b"]
        assert req["ram_gb"] <= 8   # should run on 8 GB machines
        assert req["disk_gb"] >= 1

    def test_gemma4_e4b_ram_requirement(self):
        from modules.hardware_detection import TIER_REQUIREMENTS
        req = TIER_REQUIREMENTS["gemma4-e4b"]
        assert req["ram_gb"] <= 16
        assert req["disk_gb"] >= 2

    def test_gemma4_12b_ram_requirement(self):
        from modules.hardware_detection import TIER_REQUIREMENTS
        req = TIER_REQUIREMENTS["gemma4-12b"]
        assert req["ram_gb"] >= 12
        assert req["disk_gb"] >= 6

    def test_tier_order_contains_gemma4(self):
        from modules.hardware_detection import TIER_ORDER
        assert "gemma4-e2b" in TIER_ORDER
        assert "gemma4-e4b" in TIER_ORDER
        assert "gemma4-12b" in TIER_ORDER

    def test_gemma4_12b_requires_more_ram_than_e4b(self):
        from modules.hardware_detection import TIER_REQUIREMENTS
        assert (TIER_REQUIREMENTS["gemma4-12b"]["ram_gb"] >=
                TIER_REQUIREMENTS["gemma4-e4b"]["ram_gb"])

    def test_legacy_tiers_unchanged(self):
        from modules.hardware_detection import TIER_REQUIREMENTS
        assert TIER_REQUIREMENTS["low"]["ram_gb"] == 8
        assert TIER_REQUIREMENTS["mid"]["ram_gb"] == 16
        assert TIER_REQUIREMENTS["high"]["ram_gb"] == 32


# ===========================================================================
# 8. ProviderProtocol — structural isinstance check
# ===========================================================================

class TestProviderProtocol:
    """Verify providers structurally satisfy ProviderProtocol."""

    def test_llama_cpp_satisfies_protocol(self):
        from core.llm.provider import ProviderProtocol
        from core.llm.llama_cpp_provider import LlamaCppProvider
        p = LlamaCppProvider()
        assert isinstance(p, ProviderProtocol)

    def test_ollama_satisfies_protocol(self):
        from core.llm.provider import ProviderProtocol
        from core.llm.ollama_provider import OllamaProvider
        p = OllamaProvider()
        assert isinstance(p, ProviderProtocol)

    def test_mock_provider_satisfies_protocol(self):
        """A correctly shaped object should pass the structural check."""
        from core.llm.provider import ProviderProtocol, CapabilityFlags, ChatMessage

        class MinimalProvider:
            def capabilities(self): return CapabilityFlags()
            def is_available(self): return True
            def health_check(self): return {"healthy": True, "detail": "ok"}
            def generate(self, messages, config): pass
            async def generate_async(self, messages, config): pass
            async def generate_stream(self, messages, config):
                return
                yield  # make it a generator
            def load(self): pass
            def unload(self): pass

        assert isinstance(MinimalProvider(), ProviderProtocol)
