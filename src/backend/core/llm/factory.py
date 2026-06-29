"""
core.llm.factory — Provider factory.

Reads LLM_PROVIDER and LLM_MODEL from settings/.env and returns the
appropriate provider instance.  ModelRunner uses this to select the active
provider transparently.

Supported LLM_PROVIDER values:
    "llama_cpp"  (default) — local GGUF via llama-cpp-python
    "ollama"               — local Ollama daemon (localhost only)

Python 3.10-compatible.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_active_provider = None  # module-level singleton


def get_provider(force_new: bool = False):
    """
    Return the active provider configured by settings.

    Reads settings.llm_provider and settings.llm_model.
    Caches the instance module-level (singleton) unless force_new=True.

    Returns:
        A provider instance satisfying ProviderProtocol.
    """
    global _active_provider

    if _active_provider is not None and not force_new:
        return _active_provider

    from core.config import settings  # local to avoid circular import

    provider_name = getattr(settings, "llm_provider", "llama_cpp").lower().strip()
    llm_model = getattr(settings, "llm_model", "").strip()

    logger.info("LLM factory: provider=%s model=%s", provider_name, llm_model or "(auto)")

    if provider_name == "ollama":
        from .ollama_provider import OllamaProvider

        model = llm_model or "gemma4:12b"
        _active_provider = OllamaProvider(model=model)
        if not _active_provider.is_available():
            logger.warning(
                "OllamaProvider requested but daemon is not reachable at localhost:11434; "
                "falling back to LlamaCppProvider."
            )
            from .llama_cpp_provider import LlamaCppProvider
            _active_provider = LlamaCppProvider(
                model_path=None,
                n_ctx=getattr(settings, "chat_context_size", 4096),
            )
    else:
        if provider_name not in ("llama_cpp", "llamacpp", "llama-cpp"):
            logger.warning(
                "Unknown LLM_PROVIDER '%s'; defaulting to llama_cpp.",
                provider_name,
            )
        from .llama_cpp_provider import LlamaCppProvider

        _active_provider = LlamaCppProvider(
            model_path=llm_model if llm_model else None,
            n_ctx=getattr(settings, "chat_context_size", 4096),
        )

    return _active_provider


def reset_provider() -> None:
    """Unload and discard the cached provider (for testing / hot-reload)."""
    global _active_provider
    if _active_provider is not None:
        try:
            _active_provider.unload()
        except Exception:
            pass
        _active_provider = None
