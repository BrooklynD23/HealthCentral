"""
Model settings API endpoints.

Handles hardware detection, model tier selection, and model downloads
for the tiered LLM inference system.

Phase 0.3: Tiered Hardware Model System
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from core.auth import RequireAuth, ProfileDbSession, ProfileEncryptionManager
from core.profile_database import get_profile_db_manager
from models import UserModelSettings
from modules.hardware_detection import (
    HardwareProfile,
    detect_hardware,
    can_run_tier,
    get_tier_display_info,
    TIER_REQUIREMENTS,
    TIER_ORDER,
)
from modules.model_selector import (
    ModelSelector,
    DownloadProgress,
    get_model_selector,
    TIER_MODEL_CONFIG,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class TierSetRequest(BaseModel):
    """Request to set preferred model tier."""
    tier: str = Field(
        ...,
        description="Tier to set: 'low', 'mid', 'high'",
        pattern="^(low|mid|high)$",
    )


class TierDownloadRequest(BaseModel):
    """Request to download a model tier."""
    tier: str = Field(
        ...,
        description="Tier to download: 'low', 'mid', 'high'",
        pattern="^(low|mid|high)$",
    )


class HardwareInfoResponse(BaseModel):
    """Hardware detection information."""
    ram_total_gb: float
    ram_available_gb: float
    cpu_cores: int
    cpu_name: Optional[str]
    disk_free_gb: float
    gpu_available: bool
    gpu_vram_gb: Optional[float]
    gpu_name: Optional[str]
    recommended_tier: str
    max_supported_tier: str
    detection_timestamp: str


class TierStatusResponse(BaseModel):
    """Status of a single tier."""
    tier: str
    name: str
    model: Optional[str]
    description: str
    available: bool
    downloaded: bool
    requirements: dict
    can_run: bool


class ModelSettingsResponse(BaseModel):
    """Response for model settings."""
    current_tier: str
    preferred_tier: Optional[str]
    recommended_tier: str
    auto_detect_enabled: bool
    hardware_info: HardwareInfoResponse
    tier_availability: dict[str, TierStatusResponse]


class DownloadProgressResponse(BaseModel):
    """Response for download progress."""
    tier: str
    status: str  # "pending", "downloading", "completed", "failed"
    progress: float
    downloaded_bytes: int
    total_bytes: int
    path: Optional[str]
    error: Optional[str]


class TiersListResponse(BaseModel):
    """Response listing all available tiers."""
    tiers: list[TierStatusResponse]
    recommended_tier: str


class ExternalApiSettingsRequest(BaseModel):
    """Request to set external API settings."""
    use_external_api: bool = False
    provider: str = ""
    api_key: str = ""
    model: str = ""
    consent_acknowledged: bool = False


class ExternalApiSettingsResponse(BaseModel):
    """Response for external API settings (key is masked)."""
    use_external_api: bool
    provider: str
    model: str
    api_key_configured: bool


class TimezoneResponse(BaseModel):
    timezone: str

class TimezoneUpdate(BaseModel):
    timezone: str = Field(..., description="IANA timezone string, e.g. 'America/New_York'")

class VoiceSettingsResponse(BaseModel):
    voice_logging_enabled: bool
    voice_modal_seen: bool

class VoiceSettingsUpdate(BaseModel):
    voice_logging_enabled: Optional[bool] = None
    voice_modal_seen: Optional[bool] = None


async def _get_user_settings(
    profile_id: str,
    profile_db: ProfileDbSession,
) -> Optional[UserModelSettings]:
    """Fetch the profile's model settings row if it exists."""
    result = await profile_db.execute(
        select(UserModelSettings).where(UserModelSettings.profile_id == profile_id)
    )
    return result.scalar_one_or_none()


async def _get_or_create_user_settings(
    profile_id: str,
    profile_db: ProfileDbSession,
) -> UserModelSettings:
    """Load the profile settings row, creating an in-session row if absent."""
    settings = await _get_user_settings(profile_id, profile_db)
    if settings is not None:
        return settings

    settings = UserModelSettings(profile_id=profile_id)
    profile_db.add(settings)
    return settings


# =============================================================================
# API Endpoints
# =============================================================================


@router.get(
    "",
    response_model=ModelSettingsResponse,
    summary="Get model settings",
    description="Get current model settings including hardware info and tier availability.",
)
async def get_model_settings(
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """Get current model settings and hardware information."""
    selector = get_model_selector()

    # Run hardware detection
    hardware = selector.detect_hardware_tier()

    # Get user settings from database
    user_settings = await _get_user_settings(session.profile_id, profile_db)

    # Determine current tier
    if user_settings and user_settings.preferred_tier:
        preferred_tier = user_settings.preferred_tier
    else:
        preferred_tier = None

    current_tier = await selector.get_active_tier(session.profile_id, profile_db)

    # Build tier availability
    tier_availability = {}
    for tier in TIER_ORDER:
        info = get_tier_display_info(tier)
        tier_availability[tier] = TierStatusResponse(
            tier=tier,
            name=info["name"],
            model=info["model"],
            description=info["description"],
            available=selector.is_model_available(tier),
            downloaded=selector.is_model_available(tier),
            requirements=TIER_REQUIREMENTS.get(tier, {}),
            can_run=can_run_tier(hardware, tier),
        )

    # Add template tier
    template_info = get_tier_display_info("template")
    tier_availability["template"] = TierStatusResponse(
        tier="template",
        name=template_info["name"],
        model=None,
        description=template_info["description"],
        available=True,
        downloaded=True,
        requirements={},
        can_run=True,
    )

    return ModelSettingsResponse(
        current_tier=current_tier,
        preferred_tier=preferred_tier,
        recommended_tier=hardware.recommended_tier,
        auto_detect_enabled=user_settings.auto_detect_enabled if user_settings else True,
        hardware_info=HardwareInfoResponse(
            ram_total_gb=round(hardware.ram_total_gb, 2),
            ram_available_gb=round(hardware.ram_available_gb, 2),
            cpu_cores=hardware.cpu_cores,
            cpu_name=hardware.cpu_name,
            disk_free_gb=round(hardware.disk_free_gb, 2),
            gpu_available=hardware.gpu_available,
            gpu_vram_gb=hardware.gpu_vram_gb,
            gpu_name=hardware.gpu_name,
            recommended_tier=hardware.recommended_tier,
            max_supported_tier=hardware.max_supported_tier,
            detection_timestamp=hardware.detection_timestamp.isoformat(),
        ),
        tier_availability=tier_availability,
    )


@router.post(
    "/detect",
    response_model=HardwareInfoResponse,
    summary="Run hardware detection",
    description="Run hardware detection and save results.",
)
async def run_hardware_detection(
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """Run hardware detection and save results to database."""
    selector = get_model_selector()

    # Run hardware detection
    hardware = selector.detect_hardware_tier()

    # Save to database
    await selector.save_hardware_detection(
        profile_id=session.profile_id,
        hardware=hardware,
        db=profile_db,
    )
    await profile_db.commit()

    logger.info(f"Hardware detection completed for profile {session.profile_id}")

    return HardwareInfoResponse(
        ram_total_gb=round(hardware.ram_total_gb, 2),
        ram_available_gb=round(hardware.ram_available_gb, 2),
        cpu_cores=hardware.cpu_cores,
        cpu_name=hardware.cpu_name,
        disk_free_gb=round(hardware.disk_free_gb, 2),
        gpu_available=hardware.gpu_available,
        gpu_vram_gb=hardware.gpu_vram_gb,
        gpu_name=hardware.gpu_name,
        recommended_tier=hardware.recommended_tier,
        max_supported_tier=hardware.max_supported_tier,
        detection_timestamp=hardware.detection_timestamp.isoformat(),
    )


@router.post(
    "/tier",
    response_model=dict,
    summary="Set preferred tier",
    description="Set the user's preferred model tier.",
)
async def set_model_tier(
    request: TierSetRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """Set user's preferred model tier."""
    selector = get_model_selector()
    tier = request.tier.lower()

    # Validate tier
    if tier not in TIER_MODEL_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {tier}. Valid options: {list(TIER_MODEL_CONFIG.keys())}",
        )

    # Check hardware compatibility
    hardware = selector.detect_hardware_tier()
    if not can_run_tier(hardware, tier):
        logger.warning(
            f"User {session.profile_id} setting tier {tier} which exceeds hardware capability"
        )
        # Allow setting but warn
        warning = f"Your hardware may not support tier '{tier}'. Recommended: {hardware.recommended_tier}"
    else:
        warning = None

    # Save preference
    await selector.set_user_preference(
        profile_id=session.profile_id,
        tier=tier,
        db=profile_db,
    )
    await profile_db.commit()

    logger.info(f"Set model tier to '{tier}' for profile {session.profile_id}")

    response = {
        "success": True,
        "tier": tier,
        "message": f"Model tier set to '{tier}'",
    }
    if warning:
        response["warning"] = warning

    return response


@router.get(
    "/tiers",
    response_model=TiersListResponse,
    summary="List tiers",
    description="List all available tiers with their status.",
)
async def list_tiers(
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """List all available tiers with their status."""
    selector = get_model_selector()
    hardware = selector.detect_hardware_tier()

    tiers = []
    for tier in TIER_ORDER:
        info = get_tier_display_info(tier)
        tiers.append(TierStatusResponse(
            tier=tier,
            name=info["name"],
            model=info["model"],
            description=info["description"],
            available=selector.is_model_available(tier),
            downloaded=selector.is_model_available(tier),
            requirements=TIER_REQUIREMENTS.get(tier, {}),
            can_run=can_run_tier(hardware, tier),
        ))

    # Add template tier
    template_info = get_tier_display_info("template")
    tiers.append(TierStatusResponse(
        tier="template",
        name=template_info["name"],
        model=None,
        description=template_info["description"],
        available=True,
        downloaded=True,
        requirements={},
        can_run=True,
    ))

    return TiersListResponse(
        tiers=tiers,
        recommended_tier=hardware.recommended_tier,
    )


@router.get(
    "/download-progress",
    response_model=dict[str, DownloadProgressResponse],
    summary="Get download progress",
    description="Get download progress for all tiers.",
)
async def get_download_progress(
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """Get download progress for all tiers from database."""
    selector = get_model_selector()

    progress = await selector.get_download_progress(
        profile_id=session.profile_id,
        db=profile_db,
    )

    # Convert to response format
    response = {}
    for tier, prog in progress.items():
        response[tier] = DownloadProgressResponse(
            tier=prog.tier,
            status=prog.status,
            progress=prog.progress,
            downloaded_bytes=prog.downloaded_bytes,
            total_bytes=prog.total_bytes,
            path=prog.path,
            error=prog.error,
        )

    return response


@router.post(
    "/download",
    response_model=dict,
    summary="Start model download",
    description="Start downloading a model for the specified tier.",
)
async def start_model_download(
    request: TierDownloadRequest,
    background_tasks: BackgroundTasks,
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """Start downloading a model in the background."""
    selector = get_model_selector()
    tier = request.tier.lower()

    # Validate tier
    if tier not in TIER_MODEL_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {tier}. Valid options: {list(TIER_MODEL_CONFIG.keys())}",
        )

    # Check if already downloaded
    if selector.is_model_available(tier):
        return {
            "success": True,
            "tier": tier,
            "message": f"Model for tier '{tier}' is already downloaded",
            "status": "completed",
        }

    # Initialize progress
    progress = DownloadProgress(
        tier=tier,
        status="pending",
        progress=0.0,
        started_at=datetime.utcnow(),
    )
    await selector.update_download_progress(
        profile_id=session.profile_id,
        tier=tier,
        progress=progress,
        db=profile_db,
    )
    await profile_db.commit()

    # Start background download
    # Note: Background tasks in FastAPI run after the response is sent
    # For long downloads, consider using a task queue (Celery, etc.)
    background_tasks.add_task(
        _download_model_task,
        tier=tier,
        profile_id=session.profile_id,
        selector=selector,
    )

    logger.info(f"Started model download for tier '{tier}', profile {session.profile_id}")

    return {
        "success": True,
        "tier": tier,
        "message": f"Download started for tier '{tier}'",
        "status": "pending",
    }


@router.get(
    "/external-api",
    response_model=ExternalApiSettingsResponse,
    summary="Get external API settings",
    description="Get external API settings. API key is never returned.",
)
async def get_external_api_settings(
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """Get external API settings with masked key."""
    user_settings = await _get_user_settings(session.profile_id, profile_db)

    if not user_settings:
        return ExternalApiSettingsResponse(
            use_external_api=False,
            provider="",
            model="",
            api_key_configured=False,
        )

    return ExternalApiSettingsResponse(
        use_external_api=getattr(user_settings, "use_external_api", False),
        provider=getattr(user_settings, "external_api_provider", ""),
        model="",
        api_key_configured=bool(getattr(user_settings, "external_api_key_encrypted", "")),
    )


@router.put(
    "/external-api",
    response_model=ExternalApiSettingsResponse,
    summary="Save external API settings",
    description="Save external API settings. Requires consent acknowledgement.",
)
async def save_external_api_settings(
    request: ExternalApiSettingsRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession,
    encryption_manager: ProfileEncryptionManager,
):
    """Save external API settings to profile database."""
    if request.use_external_api and not request.consent_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="consent_acknowledged must be true to enable external API",
        )

    user_settings = await _get_or_create_user_settings(session.profile_id, profile_db)

    user_settings.use_external_api = request.use_external_api
    user_settings.external_api_provider = request.provider

    if request.api_key:
        # Store as Fernet token text (starts with "gAAAAA"), never plaintext.
        encrypted_key = encryption_manager.encrypt(
            request.api_key.encode("utf-8")
        ).decode("ascii")
        user_settings.external_api_key_encrypted = encrypted_key

    await profile_db.commit()

    return ExternalApiSettingsResponse(
        use_external_api=user_settings.use_external_api,
        provider=user_settings.external_api_provider,
        model="",
        api_key_configured=bool(user_settings.external_api_key_encrypted),
    )


async def _write_download_status(
    profile_id: str,
    tier: str,
    selector: ModelSelector,
    download_status: str,
    progress_pct: float = 0.0,
    error: Optional[str] = None,
) -> None:
    """Write download progress to the profile database from a background task."""
    db_manager = get_profile_db_manager()
    connection = db_manager.get_connection(profile_id)
    if connection is None:
        logger.warning(f"Cannot write download status: no connection for profile {profile_id}")
        return

    try:
        async with connection.get_session() as session:
            progress = DownloadProgress(
                tier=tier,
                status=download_status,
                progress=progress_pct,
                started_at=datetime.utcnow(),
                error=error,
            )
            await selector.update_download_progress(
                profile_id=profile_id,
                tier=tier,
                progress=progress,
                db=session,
            )
    except Exception as e:
        logger.error(f"Failed to write download status for tier '{tier}': {e}")


async def _download_model_task(
    tier: str,
    profile_id: str,
    selector: ModelSelector,
) -> None:
    """
    Background task to download a model.

    Writes terminal status (completed/failed) to the profile database.
    """
    try:
        from huggingface_hub import hf_hub_download, list_repo_files

        config = TIER_MODEL_CONFIG[tier]
        repo = config["repo"]

        # Discover GGUF file if not specified
        filename = config.get("filename")
        if not filename:
            files = list_repo_files(repo)
            gguf_files = [f for f in files if f.endswith(".gguf")]
            if not gguf_files:
                raise ValueError(f"No GGUF files found in {repo}")

            pattern = config.get("filename_pattern", "q4_k_m").lower()
            matching = [f for f in gguf_files if pattern in f.lower()]
            filename = matching[0] if matching else gguf_files[0]

        # Download (this blocks but we're in a background task)
        # Use revision pinning for reproducible builds
        revision = config.get("revision", "main")
        local_path = hf_hub_download(
            repo_id=repo,
            filename=filename,
            revision=revision,
            local_dir=str(selector.models_path),
            local_dir_use_symlinks=False,
        )

        logger.info(f"Download completed for tier '{tier}': {local_path}")

        # Write completed status to DB
        await _write_download_status(profile_id, tier, selector, "completed", 100.0)

    except Exception as e:
        logger.error(f"Download failed for tier '{tier}': {e}")
        await _write_download_status(profile_id, tier, selector, "failed", 0.0, str(e))


@router.get("/timezone", response_model=TimezoneResponse)
async def get_timezone(
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """Get profile timezone setting."""
    profile_id = session.profile_id
    settings = await _get_user_settings(profile_id, profile_db)
    return TimezoneResponse(timezone=settings.timezone if settings else "UTC")


@router.put("/timezone", response_model=TimezoneResponse)
async def set_timezone(
    data: TimezoneUpdate,
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """Set profile timezone."""
    from zoneinfo import ZoneInfo
    try:
        ZoneInfo(data.timezone)  # validate
    except (KeyError, ValueError):
        raise HTTPException(status_code=422, detail=f"Invalid timezone: {data.timezone}")

    profile_id = session.profile_id
    settings = await _get_or_create_user_settings(profile_id, profile_db)

    settings.timezone = data.timezone
    await profile_db.commit()
    return TimezoneResponse(timezone=settings.timezone)


@router.get("/voice", response_model=VoiceSettingsResponse)
async def get_voice_settings(
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """Get voice logging preferences."""
    profile_id = session.profile_id
    settings = await _get_user_settings(profile_id, profile_db)
    return VoiceSettingsResponse(
        voice_logging_enabled=settings.voice_logging_enabled if settings else False,
        voice_modal_seen=settings.voice_modal_seen if settings else False,
    )


@router.patch("/voice", response_model=VoiceSettingsResponse)
async def update_voice_settings(
    data: VoiceSettingsUpdate,
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """Update voice logging preferences."""
    profile_id = session.profile_id
    settings = await _get_or_create_user_settings(profile_id, profile_db)

    if data.voice_logging_enabled is not None:
        settings.voice_logging_enabled = data.voice_logging_enabled
    if data.voice_modal_seen is not None:
        settings.voice_modal_seen = data.voice_modal_seen

    await profile_db.commit()
    return VoiceSettingsResponse(
        voice_logging_enabled=settings.voice_logging_enabled,
        voice_modal_seen=settings.voice_modal_seen,
    )
