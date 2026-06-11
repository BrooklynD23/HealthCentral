"""
core.llm.llama_cpp_provider — LlamaCppProvider.

Wraps the existing llama-cpp-python ModelRunner logic.  This is the default
provider for HealthCentral's local-first, privacy-first architecture.

Design notes:
- llama_cpp import is lazy/optional so unit tests run without the native lib.
- Chat formatting defers to llama.cpp's built-in chat_format / chat_handler
  (auto-detected from GGUF metadata) so Gemma 4 templates work automatically.
- generate() preserves the exact timeout / thread-pool behaviour of the old
  ModelRunner so existing call-sites are unaffected.
- Python 3.10-compatible: no 3.11+ syntax.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator, List, Optional

from .provider import CapabilityFlags, ChatMessage, ProviderUnavailableError

logger = logging.getLogger(__name__)

# Imported lazily to avoid hard dependency at module load time.
# Tests mock this with patch("core.llm.llama_cpp_provider._load_llama_class").
_llama_class = None


def _load_llama_class():
    """Return the Llama class or raise ImportError."""
    global _llama_class
    if _llama_class is None:
        from llama_cpp import Llama  # noqa: PLC0415
        _llama_class = Llama
    return _llama_class


class LlamaCppProvider:
    """
    Local LLM provider backed by llama-cpp-python.

    Preserves all existing ModelRunner behaviour (context size, thread count,
    timeout, auto-detect model path, fallback messaging) while implementing the
    ProviderProtocol interface.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: int = 4096,
        n_threads: int = 0,
        n_gpu_layers: int = 0,
    ):
        from core.config import settings  # local import avoids circular dep

        self._model_path = model_path
        self._n_ctx = n_ctx
        self._n_threads = n_threads if n_threads > 0 else settings.inference_threads
        self._n_gpu_layers = n_gpu_layers
        self._model = None
        self._initialized = False
        self._settings = settings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_model_path(self) -> Optional[Path]:
        """Mirror of ModelRunner._find_model_path — locate a GGUF file."""
        if self._model_path:
            p = Path(self._model_path)
            if p.exists():
                return p

        models_dir = Path(self._settings.models_path)
        models_dir.mkdir(parents=True, exist_ok=True)

        patterns = [
            f"{self._settings.default_chat_model}*.gguf",
            "gemma4*.gguf",
            "gemma-4*.gguf",
            "phi-3*.gguf",
            "phi3*.gguf",
            "llama*.gguf",
            "mistral*.gguf",
            "qwen*.gguf",
            "*.gguf",
        ]
        for pat in patterns:
            matches = list(models_dir.glob(pat))
            if matches:
                for m in matches:
                    if "q4" in m.name.lower() or "q5" in m.name.lower():
                        return m
                return matches[0]
        return None

    def _ensure_initialized(self) -> bool:
        """Lazy-load the model.  Returns True if model is ready."""
        if self._initialized:
            return self._model is not None

        self._initialized = True
        model_path = self._find_model_path()

        if not model_path:
            logger.warning(
                "LlamaCppProvider: no GGUF model found in %s",
                self._settings.models_path,
            )
            return False

        try:
            Llama = _load_llama_class()
            logger.info("LlamaCppProvider: loading model from %s", model_path)
            self._model = Llama(
                model_path=str(model_path),
                n_ctx=self._n_ctx,
                n_threads=self._n_threads if self._n_threads > 0 else None,
                n_gpu_layers=self._n_gpu_layers,
                verbose=self._settings.debug,
                # Let llama.cpp auto-detect chat template from GGUF metadata.
                # Works for Gemma 4, Phi-3, Llama-3, Mistral, Qwen2.5, etc.
                # chat_format="auto" is the default; explicit for clarity.
                chat_format="auto",
            )
            logger.info("LlamaCppProvider: model loaded — %s", model_path.name)
            return True

        except ImportError:
            logger.error(
                "llama-cpp-python not installed; "
                "run: pip install llama-cpp-python"
            )
            return False
        except Exception as exc:
            logger.error("LlamaCppProvider: failed to load model: %s", exc)
            return False

    @staticmethod
    def _messages_to_prompt(messages: List[ChatMessage]) -> str:
        """
        Fallback prompt formatter used only when llama.cpp chat_format is
        unavailable (e.g. model loaded without metadata).

        Prefers llama.cpp's built-in chat handler; this method is the last
        resort so callers always get *something*.
        """
        parts = []
        for msg in messages:
            role = msg.role
            if role == "system":
                parts.append(f"<|system|>\n{msg.content}</s>")
            elif role == "user":
                parts.append(f"<|user|>\n{msg.content}</s>")
            elif role == "assistant":
                parts.append(f"<|assistant|>\n{msg.content}</s>")
        parts.append("<|assistant|>")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # ProviderProtocol implementation
    # ------------------------------------------------------------------

    def capabilities(self) -> CapabilityFlags:
        model_name = self._settings.default_chat_model
        if self._model_path:
            model_name = Path(self._model_path).stem

        # Gemma 4 GGUF: multimodal + function_calling available at the model
        # level; we surface the flags so the app layer can gate feature use.
        is_gemma4 = "gemma4" in model_name.lower() or "gemma-4" in model_name.lower()

        return CapabilityFlags(
            context_len=self._n_ctx,
            multimodal=is_gemma4,
            function_calling=is_gemma4,
            streaming=False,  # streaming support requires llama.cpp stream API
            provider_name="llama_cpp",
            model_name=model_name,
        )

    def is_available(self) -> bool:
        return self._ensure_initialized()

    def health_check(self) -> dict:
        try:
            available = self._ensure_initialized()
            path = self._find_model_path()
            return {
                "healthy": available,
                "provider": "llama_cpp",
                "model_path": str(path) if path else None,
                "detail": "model loaded" if available else "model not loaded or not found",
            }
        except Exception as exc:
            return {"healthy": False, "provider": "llama_cpp", "detail": str(exc)}

    def generate(self, messages: List[ChatMessage], config) -> object:
        """
        Synchronous inference.  Returns InferenceResult.

        Uses llama.cpp's create_chat_completion() which auto-applies the
        correct chat template (Gemma 4, Phi-3, etc.) from GGUF metadata.
        Falls back to raw string prompt if chat API unavailable.
        """
        from core.model_runner import InferenceResult  # avoid circular at module level

        if not self._ensure_initialized():
            raise ProviderUnavailableError(
                "LlamaCppProvider: model not available. "
                "Please download a GGUF model to " + self._settings.models_path
            )

        stop = list(config.stop_sequences or [])

        try:
            # Prefer the chat-completion API so the model's built-in template is used.
            llama_messages = [
                {"role": m.role, "content": m.content} for m in messages
            ]
            result = self._model.create_chat_completion(
                messages=llama_messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                stop=stop,
            )
            text = result["choices"][0]["message"]["content"]
            finish_reason = result["choices"][0].get("finish_reason", "stop")
            tokens = result.get("usage", {}).get("completion_tokens", 0)

        except (AttributeError, KeyError):
            # Fallback: raw completion with manually-built prompt
            prompt = self._messages_to_prompt(messages)
            result = self._model(
                prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                stop=stop,
                echo=False,
            )
            text = result["choices"][0]["text"]
            finish_reason = result["choices"][0].get("finish_reason", "stop")
            tokens = result.get("usage", {}).get("completion_tokens", 0)

        model_name = self._model_path or self._settings.default_chat_model
        return InferenceResult(
            text=text.strip(),
            tokens_generated=tokens,
            finish_reason=finish_reason,
            model_name=str(model_name),
        )

    async def generate_async(self, messages: List[ChatMessage], config) -> object:
        """Async wrapper with timeout — mirrors ModelRunner.generate_async()."""
        from core.model_runner import InferenceResult  # avoid circular

        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self.generate(messages, config)),
                timeout=config.timeout_seconds,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(
                "LlamaCppProvider: generation timed out after %ds",
                config.timeout_seconds,
            )
            return InferenceResult(
                text=(
                    "I apologize, but generating a response is taking longer than "
                    "expected. Please try again with a simpler question."
                ),
                tokens_generated=0,
                finish_reason="timeout",
                model_name=self._model_path or self._settings.default_chat_model,
            )

    async def generate_stream(
        self, messages: List[ChatMessage], config
    ) -> AsyncIterator[str]:
        """Streaming not yet implemented for llama-cpp; yields full response as single chunk."""
        result = await self.generate_async(messages, config)
        yield result.text

    def load(self) -> None:
        self._ensure_initialized()

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            self._initialized = False
            logger.info("LlamaCppProvider: model unloaded")
