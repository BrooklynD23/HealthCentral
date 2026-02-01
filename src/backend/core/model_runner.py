"""
Local LLM Model Runner.

Provides inference capabilities using llama-cpp-python for local model execution.
Supports configurable model loading, timeouts, and resource management.

Sprint 6: LLM Integration for RAG Assistant
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class InferenceConfig:
    """Configuration for LLM inference."""
    max_tokens: int = 1024
    temperature: float = 0.1  # Low temperature for factual responses
    top_p: float = 0.9
    stop_sequences: list[str] | None = None
    timeout_seconds: int = 60


@dataclass
class InferenceResult:
    """Result from LLM inference."""
    text: str
    tokens_generated: int
    finish_reason: str  # "stop", "length", "timeout"
    model_name: str


class ModelRunner:
    """
    Local LLM inference runner using llama-cpp-python.

    Manages model loading, inference execution, and resource cleanup.
    Designed for privacy-first local execution without external API calls.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: int = 4096,
        n_threads: int = 0,
    ):
        """
        Initialize the model runner.

        Args:
            model_path: Path to GGUF model file. If None, uses default from settings.
            n_ctx: Context window size (default 4096)
            n_threads: Number of CPU threads (0 = auto-detect)
        """
        self._model = None
        self._model_path = model_path
        self._n_ctx = n_ctx
        self._n_threads = n_threads if n_threads > 0 else settings.inference_threads
        self._initialized = False

    def _find_model_path(self) -> Optional[Path]:
        """
        Find the model file to use.

        Looks in order:
        1. Explicitly provided path
        2. Settings default
        3. Common model names in models directory
        4. Auto-download if enabled and no model found
        """
        if self._model_path:
            path = Path(self._model_path)
            if path.exists():
                return path

        models_dir = Path(settings.models_path)
        if not models_dir.exists():
            models_dir.mkdir(parents=True, exist_ok=True)

        # Look for GGUF files matching common patterns
        search_patterns = [
            f"{settings.default_chat_model}*.gguf",
            "phi-3*.gguf",
            "llama*.gguf",
            "mistral*.gguf",
            "qwen*.gguf",
            "*.gguf",
        ]

        for pattern in search_patterns:
            matches = list(models_dir.glob(pattern))
            if matches:
                # Prefer quantized versions (smaller, faster)
                for match in matches:
                    if "q4" in match.name.lower() or "q5" in match.name.lower():
                        return match
                return matches[0]

        return None

    def ensure_model_available(self, auto_download: bool = True) -> Optional[Path]:
        """
        Ensure a model is available, optionally downloading if needed.

        Args:
            auto_download: If True, download a model when none exists

        Returns:
            Path to available model or None
        """
        path = self._find_model_path()
        if path:
            return path

        if not auto_download:
            return None

        # Try to auto-download using ModelSelector
        try:
            from modules.model_selector import get_model_selector

            selector = get_model_selector()
            downloaded = selector.ensure_model_available(tier="low")
            return downloaded
        except Exception as e:
            logger.warning(f"Auto-download failed: {e}")
            return None

    def _ensure_initialized(self) -> bool:
        """
        Lazy initialization of the LLM model.

        Returns True if model is ready, False if initialization failed.
        """
        if self._initialized:
            return self._model is not None

        self._initialized = True
        model_path = self._find_model_path()

        if not model_path:
            logger.warning(
                f"No LLM model found. Please download a GGUF model to {settings.models_path}"
            )
            return False

        try:
            from llama_cpp import Llama

            logger.info(f"Loading LLM model from {model_path}")

            self._model = Llama(
                model_path=str(model_path),
                n_ctx=self._n_ctx,
                n_threads=self._n_threads if self._n_threads > 0 else None,
                verbose=settings.debug,
            )

            logger.info(f"LLM model loaded successfully: {model_path.name}")
            return True

        except ImportError:
            logger.error(
                "llama-cpp-python not installed. "
                "Install with: pip install llama-cpp-python"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to load LLM model: {e}")
            return False

    def is_available(self) -> bool:
        """Check if the model is available for inference."""
        return self._ensure_initialized()

    def generate(
        self,
        prompt: str,
        config: Optional[InferenceConfig] = None,
    ) -> InferenceResult:
        """
        Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the model
            config: Inference configuration (uses defaults if not provided)

        Returns:
            InferenceResult with generated text and metadata

        Raises:
            RuntimeError: If model is not available
        """
        if not self._ensure_initialized():
            raise RuntimeError(
                "LLM model not available. Please download a GGUF model."
            )

        if config is None:
            config = InferenceConfig()

        stop = config.stop_sequences or []

        try:
            result = self._model(
                prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                stop=stop,
                echo=False,
            )

            generated_text = result["choices"][0]["text"]
            finish_reason = result["choices"][0].get("finish_reason", "stop")
            tokens_generated = result.get("usage", {}).get("completion_tokens", 0)

            return InferenceResult(
                text=generated_text.strip(),
                tokens_generated=tokens_generated,
                finish_reason=finish_reason,
                model_name=self._model_path or settings.default_chat_model,
            )

        except Exception as e:
            logger.error(f"LLM inference failed: {e}")
            raise RuntimeError(f"LLM inference failed: {e}")

    async def generate_async(
        self,
        prompt: str,
        config: Optional[InferenceConfig] = None,
    ) -> InferenceResult:
        """
        Async wrapper for generate() with timeout support.

        Args:
            prompt: The prompt to send to the model
            config: Inference configuration (uses defaults if not provided)

        Returns:
            InferenceResult with generated text and metadata

        Raises:
            asyncio.TimeoutError: If generation exceeds timeout
            RuntimeError: If model is not available or inference fails
        """
        if config is None:
            config = InferenceConfig()

        # Run the sync generation in a thread pool
        loop = asyncio.get_event_loop()

        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.generate(prompt, config)
                ),
                timeout=config.timeout_seconds,
            )
            return result

        except asyncio.TimeoutError:
            logger.warning(f"LLM generation timed out after {config.timeout_seconds}s")
            return InferenceResult(
                text="I apologize, but generating a response is taking longer than expected. Please try again with a simpler question.",
                tokens_generated=0,
                finish_reason="timeout",
                model_name=self._model_path or settings.default_chat_model,
            )

    def unload(self):
        """Unload the model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            self._initialized = False
            logger.info("LLM model unloaded")


# Global model runner instance
_model_runner: Optional[ModelRunner] = None


def get_model_runner() -> ModelRunner:
    """Get or create the global model runner instance."""
    global _model_runner
    if _model_runner is None:
        _model_runner = ModelRunner()
    return _model_runner


def reset_model_runner():
    """Reset the global model runner (for testing)."""
    global _model_runner
    if _model_runner is not None:
        _model_runner.unload()
        _model_runner = None
