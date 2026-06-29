"""
core.llm.provider — Abstract provider interface.

Every concrete provider must satisfy ProviderProtocol.  The protocol uses
runtime_checkable so isinstance() works without ABC overhead, but providers
should also inherit from it for IDE support.

Python 3.10-compatible: no 3.11+ syntax.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared data types
# ---------------------------------------------------------------------------


@dataclass
class CapabilityFlags:
    """Capability descriptor returned by every provider."""

    context_len: int = 4096
    """Maximum tokens in the context window (prompt + completion)."""

    multimodal: bool = False
    """Provider/model accepts image inputs alongside text."""

    function_calling: bool = False
    """Provider/model supports native function/tool-calling."""

    streaming: bool = False
    """Provider supports token-by-token streaming."""

    provider_name: str = "unknown"
    """Human-readable provider identifier."""

    model_name: str = "unknown"
    """Active model name/identifier."""


@dataclass
class ChatMessage:
    """Single message in a chat conversation."""

    role: str  # "system" | "user" | "assistant"
    content: str
    images: List[bytes] = field(default_factory=list)
    """Raw image bytes for multimodal turns (empty = text-only)."""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ProviderUnavailableError(RuntimeError):
    """Raised when a provider cannot fulfil a request (not installed / not running)."""


# ---------------------------------------------------------------------------
# Protocol (structural interface)
# ---------------------------------------------------------------------------


@runtime_checkable
class ProviderProtocol(Protocol):
    """
    Structural interface that all LLM providers must satisfy.

    generate() / generate_stream() accept chat-style messages and return
    InferenceResult / async token stream respectively.

    Callers import InferenceResult / InferenceConfig from core.model_runner
    to remain backward-compatible with existing call-sites.
    """

    def capabilities(self) -> CapabilityFlags:
        """Return static capability flags for this provider."""
        ...

    def is_available(self) -> bool:
        """
        Fast synchronous check: is the provider ready for inference?

        For llama-cpp: is the model loaded (or loadable)?
        For Ollama:    is the daemon reachable at localhost:11434?
        """
        ...

    def health_check(self) -> dict:
        """
        Extended health / diagnostic dict.

        Always returns a dict with at least {"healthy": bool, "detail": str}.
        Never raises.
        """
        ...

    def generate(self, messages: List[ChatMessage], config) -> object:
        """
        Synchronous (blocking) text generation.

        Args:
            messages: Chat-style message list (system/user/assistant).
            config:   InferenceConfig instance.

        Returns:
            InferenceResult.

        Raises:
            ProviderUnavailableError: if the provider is not ready.
            RuntimeError: on inference failure.
        """
        ...

    async def generate_async(self, messages: List[ChatMessage], config) -> object:
        """
        Async text generation (wraps generate() in executor by default).

        Raises:
            asyncio.TimeoutError: if config.timeout_seconds exceeded.
            ProviderUnavailableError: if the provider is not ready.
        """
        ...

    async def generate_stream(
        self, messages: List[ChatMessage], config
    ) -> AsyncIterator[str]:
        """
        Async token stream.  Yields partial text strings.

        Not all providers support this; check capabilities().streaming.
        """
        ...

    def load(self) -> None:
        """Eagerly load/warm the model.  No-op if already loaded."""
        ...

    def unload(self) -> None:
        """Release model resources.  No-op if already unloaded."""
        ...
