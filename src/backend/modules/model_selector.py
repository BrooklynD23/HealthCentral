"""
Model selector module for tiered LLM inference.

Phase 0.3: Tiered Hardware Model System

Manages model loading, selection, and async-safe inference using
asyncio.to_thread() for synchronous llama-cpp operations.
"""

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models import UserModelSettings
from .hardware_detection import (
    HardwareProfile,
    detect_hardware,
    can_run_tier,
    get_recommended_tier,
    TIER_ORDER,
)

logger = logging.getLogger(__name__)


# Tier to model mapping (centralized configuration)
TIER_MODEL_CONFIG: dict[str, dict[str, Any]] = {
    "low": {
        "repo": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        "filename": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "context_size": 2048,
        "n_gpu_layers": 0,  # CPU-only default
        "description": "Qwen2.5 0.5B - Fast, lightweight",
    },
    "mid": {
        "repo": "microsoft/Phi-3-mini-4k-instruct-gguf",
        "filename": None,  # Discover at download time
        "filename_pattern": "q4_k_m",  # Prefer Q4_K_M quantization
        "context_size": 4096,
        "n_gpu_layers": 0,
        "description": "Phi-3-mini - Balanced quality",
    },
    "high": {
        "repo": "BioMistral/BioMistral-7B-GGUF",
        "filename": None,  # Discover at download time
        "filename_pattern": "q4_k_m",
        "context_size": 4096,
        "n_gpu_layers": 0,  # GPU optional bonus
        "description": "BioMistral-7B - Medical-specialized",
    },
}

# Fallback order when model unavailable
TIER_FALLBACK_ORDER = ["high", "mid", "low", "template"]


@dataclass
class DownloadProgress:
    """Progress tracking for model downloads."""
    tier: str
    status: str  # "pending", "downloading", "completed", "failed"
    progress: float = 0.0  # 0.0 to 1.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    path: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "tier": self.tier,
            "status": self.status,
            "progress": self.progress,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "path": self.path,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadProgress":
        """Create from dictionary."""
        started_at = data.get("started_at")
        completed_at = data.get("completed_at")
        return cls(
            tier=data.get("tier", "low"),
            status=data.get("status", "pending"),
            progress=data.get("progress", 0.0),
            downloaded_bytes=data.get("downloaded_bytes", 0),
            total_bytes=data.get("total_bytes", 0),
            path=data.get("path"),
            error=data.get("error"),
            started_at=datetime.fromisoformat(started_at) if started_at else None,
            completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
        )


class ModelSelector:
    """
    Intelligent model selection with async-safe inference.

    Handles:
    - Hardware detection and tier recommendation
    - User preference storage (UserModelSettings table)
    - Model loading via llama-cpp
    - Async-safe inference using asyncio.to_thread()
    - Fallback chain when model unavailable
    """

    def __init__(self, models_path: Optional[str] = None):
        """
        Initialize the model selector.

        Args:
            models_path: Path to models directory. Defaults to settings.models_path.
        """
        self._models_path = Path(models_path or settings.models_path)
        self._models_path.mkdir(parents=True, exist_ok=True)

        self._loaded_model: Optional[Any] = None  # Llama instance
        self._current_tier: Optional[str] = None
        self._hardware_profile: Optional[HardwareProfile] = None

        # Lock for thread-safe model loading
        self._load_lock = asyncio.Lock()

    @property
    def models_path(self) -> Path:
        """Get the models directory path."""
        return self._models_path

    def detect_hardware_tier(self) -> HardwareProfile:
        """
        Assess system capabilities and return hardware profile.

        Returns:
            HardwareProfile with detection results and recommended tier.
        """
        self._hardware_profile = detect_hardware(str(self._models_path))
        return self._hardware_profile

    async def get_user_preference(
        self,
        profile_id: str,
        db: AsyncSession,
    ) -> Optional[str]:
        """
        Get user's preferred tier from database.

        Args:
            profile_id: User profile ID
            db: Database session

        Returns:
            Preferred tier string or None if not set.
        """
        result = await db.execute(
            select(UserModelSettings).where(
                UserModelSettings.profile_id == profile_id
            )
        )
        settings_row = result.scalar_one_or_none()

        if settings_row:
            return settings_row.preferred_tier
        return None

    async def set_user_preference(
        self,
        profile_id: str,
        tier: str,
        db: AsyncSession,
    ) -> UserModelSettings:
        """
        Save user's preferred tier to database.

        Args:
            profile_id: User profile ID
            tier: Tier string ("low", "mid", "high")
            db: Database session

        Returns:
            Updated UserModelSettings record.
        """
        # Validate tier
        if tier not in TIER_MODEL_CONFIG and tier != "template":
            raise ValueError(f"Invalid tier: {tier}")

        result = await db.execute(
            select(UserModelSettings).where(
                UserModelSettings.profile_id == profile_id
            )
        )
        settings_row = result.scalar_one_or_none()

        if settings_row:
            settings_row.preferred_tier = tier
            settings_row.updated_at = datetime.utcnow()
        else:
            settings_row = UserModelSettings(
                id=str(uuid.uuid4()),
                profile_id=profile_id,
                preferred_tier=tier,
                auto_detect_enabled=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(settings_row)

        await db.flush()
        return settings_row

    async def save_hardware_detection(
        self,
        profile_id: str,
        hardware: HardwareProfile,
        db: AsyncSession,
    ) -> None:
        """
        Save hardware detection results to database.

        Args:
            profile_id: User profile ID
            hardware: Hardware profile from detect_hardware()
            db: Database session
        """
        result = await db.execute(
            select(UserModelSettings).where(
                UserModelSettings.profile_id == profile_id
            )
        )
        settings_row = result.scalar_one_or_none()

        if settings_row:
            settings_row.last_hardware_json = json.dumps(hardware.to_dict())
            settings_row.last_detection_at = datetime.utcnow()
            settings_row.updated_at = datetime.utcnow()
        else:
            settings_row = UserModelSettings(
                id=str(uuid.uuid4()),
                profile_id=profile_id,
                preferred_tier="low",
                auto_detect_enabled=True,
                last_hardware_json=json.dumps(hardware.to_dict()),
                last_detection_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(settings_row)

        await db.flush()

    async def get_active_tier(
        self,
        profile_id: str,
        db: AsyncSession,
    ) -> str:
        """
        Determine the active tier for interpretation.

        Priority: user preference > recommendation > "low" (default)

        Args:
            profile_id: User profile ID
            db: Database session

        Returns:
            Active tier string.
        """
        # Check user preference first
        preference = await self.get_user_preference(profile_id, db)
        if preference:
            # Verify preference is supported by hardware
            if self._hardware_profile is None:
                self.detect_hardware_tier()

            if can_run_tier(self._hardware_profile, preference):
                return preference
            else:
                logger.warning(
                    f"User preference {preference} exceeds hardware capability, "
                    f"using {self._hardware_profile.recommended_tier}"
                )

        # Fall back to recommendation
        if self._hardware_profile is None:
            self.detect_hardware_tier()

        return get_recommended_tier(self._hardware_profile)

    def get_model_path(self, tier: str) -> Optional[Path]:
        """
        Get the local path for a tier's model file.

        Args:
            tier: Tier string

        Returns:
            Path to model file or None if not downloaded.
        """
        if tier not in TIER_MODEL_CONFIG:
            return None

        config = TIER_MODEL_CONFIG[tier]
        filename = config.get("filename")

        if filename:
            model_path = self._models_path / filename
            if model_path.exists():
                return model_path

        # Check for any GGUF file matching the tier
        pattern = config.get("filename_pattern", "")
        for f in self._models_path.glob("*.gguf"):
            if pattern.lower() in f.name.lower():
                return f

        return None

    def is_model_available(self, tier: str) -> bool:
        """
        Check if a tier's model is downloaded and available.

        Args:
            tier: Tier string

        Returns:
            True if model is available locally.
        """
        if tier == "template":
            return True  # Template is always available

        return self.get_model_path(tier) is not None

    def get_fallback_chain(self, tier: str) -> list[str]:
        """
        Return fallback tiers in order for when selected tier unavailable.

        Args:
            tier: Starting tier

        Returns:
            List of tiers to try in order.
        """
        try:
            start_idx = TIER_FALLBACK_ORDER.index(tier)
            return TIER_FALLBACK_ORDER[start_idx:]
        except ValueError:
            return ["low", "template"]

    def load_model(self, tier: str) -> Optional[Any]:
        """
        Load model synchronously (called via to_thread).

        Args:
            tier: Tier to load

        Returns:
            Llama model instance or None if unavailable.
        """
        if tier == "template":
            return None

        model_path = self.get_model_path(tier)
        if not model_path:
            logger.warning(f"Model not found for tier {tier}")
            return None

        try:
            from llama_cpp import Llama

            config = TIER_MODEL_CONFIG[tier]
            context_size = config.get("context_size", 2048)
            n_gpu_layers = config.get("n_gpu_layers", 0)

            logger.info(f"Loading model from {model_path}")
            model = Llama(
                model_path=str(model_path),
                n_ctx=context_size,
                n_gpu_layers=n_gpu_layers,
                verbose=False,
            )

            logger.info(f"Model loaded successfully for tier {tier}")
            return model

        except ImportError:
            logger.error("llama-cpp-python not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to load model for tier {tier}: {e}")
            return None

    async def load_model_async(self, tier: str) -> Optional[Any]:
        """
        Async wrapper for model loading using asyncio.to_thread().

        Args:
            tier: Tier to load

        Returns:
            Llama model instance or None.
        """
        async with self._load_lock:
            # Check if already loaded
            if self._current_tier == tier and self._loaded_model is not None:
                return self._loaded_model

            # Unload previous model
            if self._loaded_model is not None:
                del self._loaded_model
                self._loaded_model = None

            # Load new model in thread pool
            self._loaded_model = await asyncio.to_thread(self.load_model, tier)
            self._current_tier = tier if self._loaded_model else None

            return self._loaded_model

    async def get_model_for_inference(
        self,
        profile_id: str,
        db: AsyncSession,
    ) -> tuple[Optional[Any], str]:
        """
        Get the appropriate model for inference with fallback.

        Tries the active tier, then falls back through the chain
        until a model is found or template mode is reached.

        Args:
            profile_id: User profile ID
            db: Database session

        Returns:
            Tuple of (model or None, active_tier)
        """
        active_tier = await self.get_active_tier(profile_id, db)
        fallback_chain = self.get_fallback_chain(active_tier)

        for tier in fallback_chain:
            if tier == "template":
                return None, "template"

            if self.is_model_available(tier):
                model = await self.load_model_async(tier)
                if model is not None:
                    return model, tier

        return None, "template"

    async def run_inference(
        self,
        model: Any,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.3,
        stop: Optional[list[str]] = None,
    ) -> dict:
        """
        Run inference async-safely using asyncio.to_thread().

        Args:
            model: Llama model instance
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop: Stop sequences

        Returns:
            Generation result dictionary.
        """
        if model is None:
            raise ValueError("Model is None, cannot run inference")

        def _inference():
            return model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or [],
            )

        return await asyncio.to_thread(_inference)

    def list_downloaded_models(self) -> dict[str, dict]:
        """
        List all downloaded models with their information.

        Returns:
            Dictionary mapping tier to model info.
        """
        downloaded = {}

        for tier, config in TIER_MODEL_CONFIG.items():
            model_path = self.get_model_path(tier)
            if model_path:
                size_gb = model_path.stat().st_size / (1024**3)
                downloaded[tier] = {
                    "tier": tier,
                    "path": str(model_path),
                    "filename": model_path.name,
                    "size_gb": round(size_gb, 2),
                    "description": config.get("description", ""),
                }

        return downloaded

    async def get_download_progress(
        self,
        profile_id: str,
        db: AsyncSession,
    ) -> dict[str, DownloadProgress]:
        """
        Get download progress for all tiers from database.

        Args:
            profile_id: User profile ID
            db: Database session

        Returns:
            Dictionary mapping tier to DownloadProgress.
        """
        result = await db.execute(
            select(UserModelSettings).where(
                UserModelSettings.profile_id == profile_id
            )
        )
        settings_row = result.scalar_one_or_none()

        progress = {}
        if settings_row and settings_row.download_state_json:
            state = json.loads(settings_row.download_state_json)
            for tier, data in state.items():
                progress[tier] = DownloadProgress.from_dict(data)

        return progress

    async def update_download_progress(
        self,
        profile_id: str,
        tier: str,
        progress: DownloadProgress,
        db: AsyncSession,
    ) -> None:
        """
        Update download progress in database.

        Args:
            profile_id: User profile ID
            tier: Tier being downloaded
            progress: Current progress
            db: Database session
        """
        result = await db.execute(
            select(UserModelSettings).where(
                UserModelSettings.profile_id == profile_id
            )
        )
        settings_row = result.scalar_one_or_none()

        if not settings_row:
            settings_row = UserModelSettings(
                id=str(uuid.uuid4()),
                profile_id=profile_id,
                preferred_tier="low",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(settings_row)

        # Load existing state
        state = {}
        if settings_row.download_state_json:
            state = json.loads(settings_row.download_state_json)

        # Update tier progress
        state[tier] = progress.to_dict()
        settings_row.download_state_json = json.dumps(state)
        settings_row.updated_at = datetime.utcnow()

        await db.flush()


# Singleton instance
_model_selector: Optional[ModelSelector] = None


def get_model_selector() -> ModelSelector:
    """Get or create the global ModelSelector instance."""
    global _model_selector
    if _model_selector is None:
        _model_selector = ModelSelector()
    return _model_selector
