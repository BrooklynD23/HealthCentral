"""
core.model_runner — Thin facade over the active LLM provider.

Public API is unchanged from the original implementation so all existing
call-sites (modules/rag.py, api/interpretations.py, api/assistant.py, etc.)
continue to work without modification.

The actual inference is delegated to the provider selected by
core.llm.factory.get_provider() (LlamaCppProvider by default, OllamaProvider
when LLM_PROVIDER=ollama).

Python 3.10-compatible: no 3.11+ syntax.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types — kept here so existing "from core.model_runner import ..." works
# ---------------------------------------------------------------------------


@dataclass
class InferenceConfig:
    """Configuration for LLM inference."""
    max_tokens: int = 1024
    temperature: float = 0.1
    top_p: float = 0.9
    stop_sequences: Optional[List[str]] = None
    timeout_seconds: int = 60


@dataclass
class InferenceResult:
    """Result from LLM inference."""
    text: str
    tokens_generated: int
    finish_reason: str   # "stop" | "length" | "timeout"
    model_name: str


# ---------------------------------------------------------------------------
# ModelRunner facade
# ---------------------------------------------------------------------------


class ModelRunner:
    """
    Facade over the active LLM provider.

    Exposes the same public API as the original llama-cpp-python implementation:
        is_available()
        generate(prompt, config) -> InferenceResult
        generate_async(prompt, config) -> InferenceResult
        unload()

    Internally converts the legacy prompt-string API to the chat-message API
    expected by providers (wraps the prompt as a single user message).

    Also exposes ensure_model_available() for backward compatibility with
    code that calls it before inference.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: int = 4096,
        n_threads: int = 0,
        # Provider override — used by tests to inject mocks.
        _provider=None,
    ):
        self._model_path = model_path
        self._n_ctx = n_ctx
        self._n_threads = n_threads
        self._provider_override = _provider

    def _get_provider(self):
        """Return the active provider, honouring test overrides."""
        if self._provider_override is not None:
            return self._provider_override
        from core.llm.factory import get_provider
        return get_provider()

    # ------------------------------------------------------------------
    # Legacy helpers (preserve original call-site contracts)
    # ------------------------------------------------------------------

    def _find_model_path(self) -> Optional[Path]:
        """Delegate to provider's path resolution for backward compat."""
        provider = self._get_provider()
        if hasattr(provider, "_find_model_path"):
            return provider._find_model_path()
        return None

    def ensure_model_available(self, auto_download: bool = True) -> Optional[Path]:
        """
        Ensure a model is available, optionally triggering a download.

        Preserved for backward compatibility (called by some startup paths).
        """
        path = self._find_model_path()
        if path:
            return path

        if not auto_download:
            return None

        try:
            from modules.model_selector import get_model_selector
            selector = get_model_selector()
            return selector.ensure_model_available(tier="low")
        except Exception as exc:
            logger.warning("ensure_model_available: auto-download failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Core inference methods
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check if the active provider is ready for inference."""
        try:
            return self._get_provider().is_available()
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        config: Optional[InferenceConfig] = None,
    ) -> InferenceResult:
        """
        Synchronous text generation.

        Wraps *prompt* as a single user message and delegates to the provider.

        Raises:
            RuntimeError: if provider is unavailable or inference fails.
        """
        from core.llm.provider import ChatMessage, ProviderUnavailableError

        if config is None:
            config = InferenceConfig()

        messages = [ChatMessage(role="user", content=prompt)]
        provider = self._get_provider()

        try:
            result = provider.generate(messages, config)
        except ProviderUnavailableError as exc:
            raise RuntimeError(str(exc)) from exc
        except Exception as exc:
            logger.error("ModelRunner.generate failed: %s", exc)
            raise RuntimeError(f"LLM inference failed: {exc}") from exc

        # Ensure the result is an InferenceResult (providers may return their own)
        if not isinstance(result, InferenceResult):
            return InferenceResult(
                text=getattr(result, "text", str(result)),
                tokens_generated=getattr(result, "tokens_generated", 0),
                finish_reason=getattr(result, "finish_reason", "stop"),
                model_name=getattr(result, "model_name", "unknown"),
            )
        return result

    async def generate_async(
        self,
        prompt: str,
        config: Optional[InferenceConfig] = None,
    ) -> InferenceResult:
        """
        Async text generation with timeout.

        Mirrors original ModelRunner.generate_async() contract exactly.
        """
        from core.llm.provider import ChatMessage, ProviderUnavailableError

        if config is None:
            config = InferenceConfig()

        messages = [ChatMessage(role="user", content=prompt)]
        provider = self._get_provider()

        try:
            result = await provider.generate_async(messages, config)
        except ProviderUnavailableError as exc:
            raise RuntimeError(str(exc)) from exc
        except asyncio.TimeoutError:
            logger.warning(
                "ModelRunner.generate_async timed out after %ds",
                config.timeout_seconds,
            )
            return InferenceResult(
                text=(
                    "I apologize, but generating a response is taking longer than "
                    "expected. Please try again with a simpler question."
                ),
                tokens_generated=0,
                finish_reason="timeout",
                model_name="unknown",
            )
        except Exception as exc:
            logger.error("ModelRunner.generate_async failed: %s", exc)
            raise RuntimeError(f"LLM inference failed: {exc}") from exc

        if not isinstance(result, InferenceResult):
            return InferenceResult(
                text=getattr(result, "text", str(result)),
                tokens_generated=getattr(result, "tokens_generated", 0),
                finish_reason=getattr(result, "finish_reason", "stop"),
                model_name=getattr(result, "model_name", "unknown"),
            )
        return result

    def unload(self) -> None:
        """Unload the provider to free memory."""
        try:
            provider = self._get_provider()
            provider.unload()
        except Exception as exc:
            logger.warning("ModelRunner.unload: %s", exc)


# ---------------------------------------------------------------------------
# Module-level singleton — same pattern as the original
# ---------------------------------------------------------------------------

_model_runner: Optional[ModelRunner] = None


def get_model_runner() -> ModelRunner:
    """Get or create the global ModelRunner facade instance."""
    global _model_runner
    if _model_runner is None:
        _model_runner = ModelRunner()
    return _model_runner


def reset_model_runner() -> None:
    """Reset the global model runner (for testing / hot-reload)."""
    global _model_runner
    if _model_runner is not None:
        _model_runner.unload()
        _model_runner = None
