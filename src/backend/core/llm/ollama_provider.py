"""
core.llm.ollama_provider — OllamaProvider.

Talks to a locally-running Ollama daemon at http://localhost:11434.

Privacy guarantees:
  - ONLY localhost connections are permitted (127.0.0.1 / ::1).
  - Any attempt to set a non-local base_url raises ValueError at construction
    time so there is no code path that can accidentally phone home.
  - httpx is used (already a project dependency); no extra deps required.

Graceful degradation:
  - If Ollama is not running, is_available() returns False and generate()
    raises ProviderUnavailableError (not RuntimeError) so callers can fall
    back to LlamaCppProvider without crashing.

Python 3.10-compatible: no 3.11+ syntax.
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, List, Optional

from .provider import CapabilityFlags, ChatMessage, ProviderUnavailableError

logger = logging.getLogger(__name__)

# Default local Ollama endpoint.  Non-local URLs are rejected at construction.
_DEFAULT_BASE_URL = "http://127.0.0.1:11434"

# Allowed localhost representations (scheme-stripped, lower-cased hostname).
_LOCAL_HOSTNAMES = frozenset({"localhost", "127.0.0.1", "::1", "[::1]"})

_OLLAMA_CONNECT_TIMEOUT = 5.0   # seconds for initial connection attempt
_OLLAMA_READ_TIMEOUT    = 300.0  # seconds for full response (large models are slow)


def _assert_localhost(url: str) -> None:
    """
    Raise ValueError if *url* does not resolve to localhost.

    This is a hard privacy guard — no cloud calls from product code paths.
    """
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower().strip("[]")
    if host not in _LOCAL_HOSTNAMES:
        raise ValueError(
            f"OllamaProvider: refusing non-local base_url '{url}'. "
            "Only localhost connections are permitted (privacy guarantee). "
            f"Hostname '{host}' is not in {sorted(_LOCAL_HOSTNAMES)}."
        )


class OllamaProvider:
    """
    Optional LLM provider that delegates inference to a local Ollama daemon.

    Usage::

        provider = OllamaProvider(model="gemma4:12b")
        if provider.is_available():
            result = await provider.generate_async(messages, config)
    """

    def __init__(
        self,
        model: str = "gemma4:12b",
        base_url: str = _DEFAULT_BASE_URL,
    ):
        _assert_localhost(base_url)  # privacy guard — raises if non-local
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._available: Optional[bool] = None  # cached probe result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_client(self):
        """Build a synchronous httpx.Client with conservative timeouts."""
        try:
            import httpx
        except ImportError as exc:
            raise ProviderUnavailableError(
                "httpx is required for OllamaProvider. "
                "Install with: pip install httpx"
            ) from exc
        return httpx.Client(
            base_url=self._base_url,
            timeout=httpx.Timeout(
                connect=_OLLAMA_CONNECT_TIMEOUT,
                read=_OLLAMA_READ_TIMEOUT,
                write=30.0,
                pool=5.0,
            ),
        )

    def _make_async_client(self):
        """Build an async httpx.AsyncClient."""
        try:
            import httpx
        except ImportError as exc:
            raise ProviderUnavailableError(
                "httpx is required for OllamaProvider. "
                "Install with: pip install httpx"
            ) from exc
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(
                connect=_OLLAMA_CONNECT_TIMEOUT,
                read=_OLLAMA_READ_TIMEOUT,
                write=30.0,
                pool=5.0,
            ),
        )

    def _probe_sync(self) -> bool:
        """Return True if Ollama is reachable (GET /api/tags)."""
        try:
            client = self._make_client()
            with client:
                resp = client.get("/api/tags", timeout=_OLLAMA_CONNECT_TIMEOUT)
                return resp.status_code == 200
        except Exception:
            return False

    def _build_request_body(self, messages: List[ChatMessage], config) -> dict:
        """Build the /api/chat request payload."""
        return {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "num_predict": config.max_tokens,
                "temperature": config.temperature,
                "top_p": config.top_p,
                "stop": list(config.stop_sequences or []),
            },
        }

    # ------------------------------------------------------------------
    # ProviderProtocol implementation
    # ------------------------------------------------------------------

    def capabilities(self) -> CapabilityFlags:
        model_lower = self._model.lower()
        # Gemma 4 family supports multimodal + function calling
        is_gemma4 = "gemma4" in model_lower or "gemma-4" in model_lower
        # Large context: Gemma 4 supports 256K; others default to 8K
        ctx = 262144 if is_gemma4 else 8192

        return CapabilityFlags(
            context_len=ctx,
            multimodal=is_gemma4,
            function_calling=is_gemma4,
            streaming=True,
            provider_name="ollama",
            model_name=self._model,
        )

    def is_available(self) -> bool:
        if self._available is None:
            self._available = self._probe_sync()
        return self._available

    def health_check(self) -> dict:
        try:
            reachable = self._probe_sync()
            self._available = reachable
            return {
                "healthy": reachable,
                "provider": "ollama",
                "base_url": self._base_url,
                "model": self._model,
                "detail": "daemon reachable" if reachable else "Ollama not running",
            }
        except Exception as exc:
            return {
                "healthy": False,
                "provider": "ollama",
                "detail": str(exc),
            }

    def generate(self, messages: List[ChatMessage], config) -> object:
        """Synchronous inference via Ollama /api/chat."""
        from core.model_runner import InferenceResult

        if not self.is_available():
            raise ProviderUnavailableError(
                f"OllamaProvider: Ollama daemon not reachable at {self._base_url}. "
                "Start Ollama with: ollama serve"
            )

        body = self._build_request_body(messages, config)
        try:
            client = self._make_client()
            with client:
                resp = client.post("/api/chat", json=body)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            self._available = None  # invalidate cache; daemon may have stopped
            raise RuntimeError(f"OllamaProvider: inference failed: {exc}") from exc

        message = data.get("message", {})
        text = message.get("content", "")
        finish_reason = "stop" if data.get("done") else "length"
        tokens = data.get("eval_count", 0)

        return InferenceResult(
            text=text.strip(),
            tokens_generated=tokens,
            finish_reason=finish_reason,
            model_name=self._model,
        )

    async def generate_async(self, messages: List[ChatMessage], config) -> object:
        """Async inference via Ollama /api/chat with timeout."""
        from core.model_runner import InferenceResult

        if not self.is_available():
            raise ProviderUnavailableError(
                f"OllamaProvider: Ollama daemon not reachable at {self._base_url}. "
                "Start Ollama with: ollama serve"
            )

        body = self._build_request_body(messages, config)
        try:
            async with self._make_async_client() as client:
                resp = await asyncio.wait_for(
                    client.post("/api/chat", json=body),
                    timeout=config.timeout_seconds,
                )
                resp.raise_for_status()
                data = resp.json()
        except asyncio.TimeoutError:
            logger.warning(
                "OllamaProvider: generation timed out after %ds",
                config.timeout_seconds,
            )
            return InferenceResult(
                text=(
                    "I apologize, but generating a response is taking longer than "
                    "expected. Please try again with a simpler question."
                ),
                tokens_generated=0,
                finish_reason="timeout",
                model_name=self._model,
            )
        except Exception as exc:
            self._available = None
            raise RuntimeError(f"OllamaProvider: async inference failed: {exc}") from exc

        message = data.get("message", {})
        text = message.get("content", "")
        finish_reason = "stop" if data.get("done") else "length"
        tokens = data.get("eval_count", 0)

        return InferenceResult(
            text=text.strip(),
            tokens_generated=tokens,
            finish_reason=finish_reason,
            model_name=self._model,
        )

    async def generate_stream(
        self, messages: List[ChatMessage], config
    ) -> AsyncIterator[str]:
        """Streaming inference via Ollama /api/chat with stream=True."""
        import json as _json

        if not self.is_available():
            raise ProviderUnavailableError(
                f"OllamaProvider: Ollama not reachable at {self._base_url}."
            )

        body = dict(self._build_request_body(messages, config))
        body["stream"] = True

        try:
            async with self._make_async_client() as client:
                async with client.stream("POST", "/api/chat", json=body) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = _json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                yield token
                            if chunk.get("done"):
                                break
                        except Exception:
                            continue
        except Exception as exc:
            self._available = None
            raise RuntimeError(f"OllamaProvider: stream failed: {exc}") from exc

    def load(self) -> None:
        """No explicit load step for Ollama; probe to warm the cache."""
        self._available = self._probe_sync()

    def unload(self) -> None:
        """No-op — model lifecycle is managed by the Ollama daemon."""
        self._available = None
