"""
External API model runner for opt-in cloud LLM usage.

Provides request-scoped runner selection so user A's external API preference
doesn't affect user B (who may prefer local inference).

Phase 2E: External API Backend (Opt-in)
"""

import logging
from typing import Optional

from .model_runner import InferenceConfig, InferenceResult
from .config import settings

logger = logging.getLogger(__name__)

FERNET_TOKEN_PREFIX = "gAAAAA"


def _looks_like_fernet_token(value: str) -> bool:
    """Return True when value appears to be a raw Fernet token string."""
    return bool(value and value.startswith(FERNET_TOKEN_PREFIX))


def _get_profile_encryption_manager(profile_id: str):
    """Build an EncryptionManager from the active profile vault key."""
    from .profile_database import get_profile_db_manager
    from .security import EncryptionManager

    db_manager = get_profile_db_manager()
    connection = db_manager.get_connection(profile_id)
    if not connection:
        return None

    return EncryptionManager(connection._encryption_key)


async def _decrypt_or_migrate_api_key(
    *,
    profile_id: str,
    profile_db,
    user_settings,
) -> str:
    """
    Resolve stored API key to plaintext for request-time usage only.

    Supports backward compatibility by migrating legacy plaintext keys to
    encrypted Fernet tokens on first read.
    """
    stored_key = getattr(user_settings, "external_api_key_encrypted", "") or ""
    if not stored_key:
        return ""

    encryption_manager = _get_profile_encryption_manager(profile_id)
    if encryption_manager is None:
        logger.warning(
            "External API runner unavailable: missing active profile encryption context",
            extra={"profile_id": profile_id},
        )
        return ""

    if _looks_like_fernet_token(stored_key):
        try:
            return encryption_manager.decrypt(stored_key.encode("ascii")).decode("utf-8")
        except Exception:
            logger.warning(
                "Failed to decrypt external API key for profile; external API disabled for request",
                extra={"profile_id": profile_id},
            )
            return ""

    # Legacy plaintext value: allow this request, then migrate at rest.
    plaintext_key = stored_key
    try:
        encrypted_key = encryption_manager.encrypt(
            plaintext_key.encode("utf-8")
        ).decode("ascii")
        user_settings.external_api_key_encrypted = encrypted_key
        await profile_db.commit()
        logger.info(
            "Migrated legacy plaintext external API key to encrypted format",
            extra={"profile_id": profile_id},
        )
    except Exception:
        logger.warning(
            "Failed to migrate legacy external API key; using request-time plaintext fallback",
            extra={"profile_id": profile_id},
        )

    return plaintext_key


class ExternalModelRunner:
    """
    External API model runner implementing the same interface as ModelRunner.

    Supports OpenAI and Anthropic API providers.
    """

    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str = "",
    ):
        self._provider = provider
        self._api_key = api_key
        self._model = model or self._default_model()

    def _default_model(self) -> str:
        if self._provider == "openai":
            return "gpt-4o-mini"
        elif self._provider == "anthropic":
            return "claude-sonnet-4-5-20250929"
        return ""

    def is_available(self) -> bool:
        """Check if the external API is configured."""
        return bool(self._provider and self._api_key)

    def generate(
        self,
        prompt: str,
        config: Optional[InferenceConfig] = None,
    ) -> InferenceResult:
        """Synchronous generation (wraps async)."""
        import asyncio
        return asyncio.run(self.generate_async(prompt, config))

    async def generate_async(
        self,
        prompt: str,
        config: Optional[InferenceConfig] = None,
    ) -> InferenceResult:
        """
        Generate a response using an external API.

        Args:
            prompt: The prompt to send
            config: Inference configuration

        Returns:
            InferenceResult with generated text
        """
        if config is None:
            config = InferenceConfig()

        # Apply redaction before sending to external provider (PRIV-RED-001)
        if settings.redaction_enabled:
            from modules.redaction import RedactionEngine

            engine = RedactionEngine(
                policy_level=settings.redaction_policy_level
            )
            redaction_result = engine.redact(prompt)
            if redaction_result.redacted_count > 0:
                logger.info(
                    "Redacted %d PII/PHI items before external API call",
                    redaction_result.redacted_count,
                    extra={"provider": self._provider},
                )
            prompt = redaction_result.text

        try:
            if self._provider == "openai":
                return await self._call_openai(prompt, config)
            elif self._provider == "anthropic":
                return await self._call_anthropic(prompt, config)
            else:
                raise ValueError(f"Unsupported provider: {self._provider}")

        except Exception as e:
            logger.error(
                "External API call failed",
                extra={"provider": self._provider, "error_type": type(e).__name__},
            )
            return InferenceResult(
                text="External API error: request failed",
                tokens_generated=0,
                finish_reason="error",
                model_name=self._model,
            )

    async def _call_openai(self, prompt: str, config: InferenceConfig) -> InferenceResult:
        """Call OpenAI-compatible API."""
        import httpx

        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": config.max_tokens,
                    "temperature": config.temperature,
                    "top_p": config.top_p,
                },
            )
            response.raise_for_status()
            data = response.json()

            text = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("completion_tokens", 0)
            finish = data["choices"][0].get("finish_reason", "stop")

            return InferenceResult(
                text=text.strip(),
                tokens_generated=tokens,
                finish_reason=finish,
                model_name=self._model,
            )

    async def _call_anthropic(self, prompt: str, config: InferenceConfig) -> InferenceResult:
        """Call Anthropic API."""
        import httpx

        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": config.max_tokens,
                    "temperature": config.temperature,
                },
            )
            response.raise_for_status()
            data = response.json()

            text = data["content"][0]["text"]
            tokens = data.get("usage", {}).get("output_tokens", 0)
            finish = data.get("stop_reason", "end_turn")

            return InferenceResult(
                text=text.strip(),
                tokens_generated=tokens,
                finish_reason=finish,
                model_name=self._model,
            )


async def get_runner_for_request(profile_id: str, profile_db) -> Optional["ExternalModelRunner"]:
    """
    Get the appropriate model runner for a request based on user settings.

    If the user has opted into external API usage, returns an ExternalModelRunner.
    Otherwise returns None (caller falls back to default local runner).

    Args:
        profile_id: The authenticated user's profile ID
        profile_db: Profile database session (UserModelSettings is profile-scoped)

    Returns:
        ExternalModelRunner if user has external API configured, None otherwise
    """
    try:
        from sqlalchemy import select
        from models.model_settings import UserModelSettings

        result = await profile_db.execute(
            select(UserModelSettings).where(
                UserModelSettings.profile_id == profile_id
            )
        )
        user_settings = result.scalar_one_or_none()

        if user_settings and getattr(user_settings, "use_external_api", False):
            provider = getattr(user_settings, "external_api_provider", "")
            api_key = await _decrypt_or_migrate_api_key(
                profile_id=profile_id,
                profile_db=profile_db,
                user_settings=user_settings,
            )
            if provider and api_key:
                return ExternalModelRunner(
                    provider=provider,
                    api_key=api_key,
                )
    except Exception:
        logger.debug("Could not load external API settings")

    return None
