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
#
# Gemma 4 family (released 2026-06-03, Apache 2.0):
#   Sizes: E2B, E4B (edge), 12B, 26B MoE (A4B active), 31B dense.
#   Features: multimodal (text+image), 256K context, native function-calling.
#   GGUF sources: unsloth/* and ggml-org/* on Hugging Face.
#   Ollama tags: gemma4:e2b, gemma4:e4b, gemma4:12b, gemma4:26b, gemma4:31b
#   Chat template: auto-detected by llama.cpp from GGUF metadata.
#
# PLACEHOLDER URLs (verify before production):
#   unsloth/gemma-4-e2b-it-GGUF, unsloth/gemma-4-e4b-it-GGUF
#   ggml-org/gemma-4-12b-it-GGUF
TIER_MODEL_CONFIG: dict[str, dict[str, Any]] = {
    # -- low: edge / phone-class (>=8 GB RAM, >=1 GB disk) -----------------------
    "low": {
        "repo": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        "filename": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "context_size": 2048,
        "n_gpu_layers": 0,
        "description": "Qwen2.5 0.5B - Fast, lightweight",
    },
    # -- gemma4-e2b: Gemma 4 E2B edge (>=8 GB RAM, >=2 GB disk) -----------------
    # ~1.5 GB Q4_K_M. PLACEHOLDER: check https://hf.co/unsloth/gemma-4-e2b-it-GGUF
    "gemma4-e2b": {
        "repo": "unsloth/gemma-4-e2b-it-GGUF",
        "filename": None,
        "filename_pattern": "q4_k_m",
        "context_size": 8192,
        "n_gpu_layers": 0,
        "multimodal": True,
        "function_calling": True,
        "description": "Gemma 4 E2B (edge) - Multimodal, 256K ctx, Apache 2.0",
        "ollama_tag": "gemma4:e2b",
    },
    # -- gemma4-e4b: Gemma 4 E4B edge (>=12 GB RAM, >=4 GB disk) ----------------
    # ~2.8 GB Q4_K_M. PLACEHOLDER: check https://hf.co/unsloth/gemma-4-e4b-it-GGUF
    "gemma4-e4b": {
        "repo": "unsloth/gemma-4-e4b-it-GGUF",
        "filename": None,
        "filename_pattern": "q4_k_m",
        "context_size": 16384,
        "n_gpu_layers": 0,
        "multimodal": True,
        "function_calling": True,
        "description": "Gemma 4 E4B (edge) - Multimodal, 256K ctx, Apache 2.0",
        "ollama_tag": "gemma4:e4b",
    },
    # -- mid: balanced quality (>=16 GB RAM, >=3 GB disk) ------------------------
    "mid": {
        "repo": "microsoft/Phi-3-mini-4k-instruct-gguf",
        "filename": None,
        "filename_pattern": "q4_k_m",
        "context_size": 4096,
        "n_gpu_layers": 0,
        "description": "Phi-3-mini - Balanced quality",
    },
    # -- gemma4-12b: Gemma 4 12B dense (>=16 GB RAM, >=8 GB disk) ---------------
    # ~7-8 GB Q4_K_M. PLACEHOLDER: check https://hf.co/ggml-org/gemma-4-12b-it-GGUF
    "gemma4-12b": {
        "repo": "ggml-org/gemma-4-12b-it-GGUF",
        "filename": None,
        "filename_pattern": "q4_k_m",
        "context_size": 32768,
        "n_gpu_layers": 0,
        "multimodal": True,
        "function_calling": True,
        "description": "Gemma 4 12B - Multimodal, 256K ctx, Apache 2.0",
        "ollama_tag": "gemma4:12b",
    },
    # -- high: best quality (>=32 GB RAM, >=5 GB disk) ---------------------------
    "high": {
        "repo": "BioMistral/BioMistral-7B-GGUF",
        "filename": None,
        "filename_pattern": "q4_k_m",
        "context_size": 4096,
        "n_gpu_layers": 0,
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

    def download_model(
        self,
        tier: str,
        progress_callback: Optional[callable] = None,
    ) -> Optional[Path]:
        """
        Download a model for the specified tier from Hugging Face.

        Args:
            tier: Tier to download ("low", "mid", "high")
            progress_callback: Optional callback for progress updates
                              Signature: callback(downloaded_bytes, total_bytes)

        Returns:
            Path to downloaded model or None if failed.
        """
        if tier not in TIER_MODEL_CONFIG:
            logger.error(f"Unknown tier: {tier}")
            return None

        config = TIER_MODEL_CONFIG[tier]
        repo_id = config.get("repo")
        filename = config.get("filename")
        filename_pattern = config.get("filename_pattern", "")

        if not repo_id:
            logger.error(f"No repository configured for tier {tier}")
            return None

        try:
            from huggingface_hub import hf_hub_download, list_repo_files

            # If no specific filename, find one matching the pattern
            if not filename:
                logger.info(f"Discovering model file for {tier} from {repo_id}")
                files = list_repo_files(repo_id)
                gguf_files = [f for f in files if f.endswith(".gguf")]

                if filename_pattern:
                    matching = [f for f in gguf_files if filename_pattern.lower() in f.lower()]
                    if matching:
                        filename = matching[0]
                    elif gguf_files:
                        filename = gguf_files[0]
                elif gguf_files:
                    filename = gguf_files[0]

                if not filename:
                    logger.error(f"No GGUF files found in {repo_id}")
                    return None

            logger.info(f"Downloading {filename} from {repo_id}")

            # Download with progress tracking
            # Use revision pinning for reproducible builds
            revision = config.get("revision", "main")
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                revision=revision,
                local_dir=str(self._models_path),
                local_dir_use_symlinks=False,
            )

            result_path = Path(downloaded_path)
            logger.info(f"Model downloaded to {result_path}")

            return result_path

        except ImportError:
            logger.error(
                "huggingface-hub not installed. "
                "Install with: pip install huggingface-hub"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to download model for tier {tier}: {e}")
            return None

    async def download_model_async(
        self,
        tier: str,
        profile_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[Path]:
        """
        Async wrapper for model downloading.

        Args:
            tier: Tier to download
            profile_id: Optional profile ID for progress tracking
            db: Optional database session for progress updates

        Returns:
            Path to downloaded model or None if failed.
        """
        if profile_id and db:
            progress = DownloadProgress(
                tier=tier,
                status="downloading",
                started_at=datetime.utcnow(),
            )
            await self.update_download_progress(profile_id, tier, progress, db)
            await db.commit()

        try:
            result = await asyncio.to_thread(self.download_model, tier)

            if profile_id and db:
                progress.status = "completed" if result else "failed"
                progress.completed_at = datetime.utcnow()
                progress.path = str(result) if result else None
                await self.update_download_progress(profile_id, tier, progress, db)
                await db.commit()

            return result

        except Exception as e:
            if profile_id and db:
                progress = DownloadProgress(
                    tier=tier,
                    status="failed",
                    error=str(e),
                    completed_at=datetime.utcnow(),
                )
                await self.update_download_progress(profile_id, tier, progress, db)
                await db.commit()
            raise

    def ensure_model_available(self, tier: str = "low") -> Optional[Path]:
        """
        Ensure a model is available, downloading if necessary.

        This is the main entry point for auto-downloading models.

        Args:
            tier: Preferred tier to download if no models exist

        Returns:
            Path to an available model or None.
        """
        # Check if any model is already available
        for check_tier in ["low", "mid", "high"]:
            path = self.get_model_path(check_tier)
            if path:
                logger.info(f"Found existing model for tier {check_tier}: {path}")
                return path

        # No model found, download the requested tier
        logger.info(f"No models found, downloading tier {tier}")
        return self.download_model(tier)

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
