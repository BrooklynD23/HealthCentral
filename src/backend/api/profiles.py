"""
Profile management API endpoints.

Handles profile creation, authentication, and access control.
"""

import base64
import uuid
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.config import settings
from core.security import (
    generate_encryption_key,
    generate_salt,
    hash_password,
    seal_key_with_dpapi,
    unseal_key_with_dpapi,
    revoke_jwt_token,
    KeySealingError,
)
from core.rate_limiter import auth_rate_limiter
from core.auth import (
    authenticate_profile,
    create_session_token,
    require_auth,
    require_profile_access,
    TokenResponse,
    LoginRequest,
    RequireAuth,
    OptionalAuth,
    Session,
    open_profile_database_on_login,
    close_profile_database_on_logout,
    ProfileDbSession,
)
from core.audit import log_profile_event
from models import (
    AdherencePattern,
    Chunk,
    Document,
    DocumentCategory,
    DocumentEntity,
    DoseTaken,
    EarnedBadge,
    Embedding,
    LabInterpretation,
    Medication,
    MedicationSchedule,
    MemoryItem,
    Observation,
    PanelInterpretation,
    Profile,
    ReminderLog,
    UserModelSettings,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_SYNTHETIC_E2E_PROFILE_PREFIX = "Playwright E2E"


class ProfileCreate(BaseModel):
    """Request model for creating a profile."""

    display_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets minimum security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class ProfileResponse(BaseModel):
    """Response model for profile data."""

    id: str
    display_name: str
    is_locked: bool
    has_password: bool
    created_at: str
    last_accessed_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, profile: Profile) -> "ProfileResponse":
        return cls(
            id=profile.id,
            display_name=profile.display_name,
            is_locked=profile.is_locked,
            has_password=profile.password_hash is not None,
            created_at=profile.created_at.isoformat(),
            last_accessed_at=(
                profile.last_accessed_at.isoformat() if profile.last_accessed_at else None
            ),
        )


class ProfileListResponse(BaseModel):
    """Response model for listing profiles (minimal info for selection)."""

    id: str
    display_name: str
    has_password: bool
    created_at: str

    @classmethod
    def from_model(cls, profile: Profile) -> "ProfileListResponse":
        return cls(
            id=profile.id,
            display_name=profile.display_name,
            has_password=profile.password_hash is not None,
            created_at=profile.created_at.isoformat(),
        )


class ProfileUnlock(BaseModel):
    """Request model for unlocking a profile."""

    password: str


class PasswordChange(BaseModel):
    """Request model for changing profile password."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets minimum security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# =============================================================================
# Public endpoints (no authentication required)
# =============================================================================


@router.get("/", response_model=list[ProfileListResponse])
async def list_profiles(db: AsyncSession = Depends(get_db)):
    """
    List all available profiles.

    Returns minimal info for profile selection screen.
    No authentication required - this is the entry point.
    """
    result = await db.execute(select(Profile).order_by(Profile.created_at.desc()))
    profiles = result.scalars().all()

    return [ProfileListResponse.from_model(p) for p in profiles]


@router.post("/", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new user profile with encrypted vault.

    Creates:
    - Profile record with hashed password
    - Encryption key sealed with password-derived key
    - Encrypted vault directory
    - Audit log entry
    - Session token for immediate access

    The profile is automatically unlocked after creation.
    """
    profile_id = str(uuid.uuid4())
    encryption_key_id = str(uuid.uuid4())

    # Generate password hash and salt
    password_salt = generate_salt()
    password_hash = hash_password(profile_data.password)

    # Generate encryption key and seal it with password
    encryption_key = generate_encryption_key()
    try:
        sealed_key, seal_method = seal_key_with_dpapi(
            encryption_key, fallback_password=profile_data.password
        )
    except KeySealingError as e:
        logger.error(f"Failed to seal encryption key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create secure vault",
        )

    # Store sealed key and seal method in vault directory
    vault_path = Path(settings.app_data_path) / "vaults" / profile_id
    vault_path.mkdir(parents=True, exist_ok=True)

    key_path = vault_path / "key.bin"
    key_path.write_bytes(sealed_key)

    # Store seal method for later unsealing
    method_path = vault_path / "key.method"
    method_path.write_text(seal_method)

    # Create profile record
    profile = Profile(
        id=profile_id,
        display_name=profile_data.display_name,
        encryption_key_id=encryption_key_id,
        password_hash=password_hash,
        password_salt=base64.b64encode(password_salt).decode("ascii"),
        is_locked=False,  # Start unlocked after creation
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_accessed_at=datetime.utcnow(),
    )

    db.add(profile)

    # Create audit log
    await log_profile_event(
        db=db,
        event="create",
        profile_id=profile_id,
        profile_name=profile_data.display_name,
    )

    await db.commit()

    logger.info(f"Created profile: {profile_id} ({profile_data.display_name})")

    # Phase 3: Open the per-profile encrypted database
    await open_profile_database_on_login(profile_id, profile_data.password)

    # Return session token for immediate access
    return create_session_token(profile)


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate and log in to a profile.

    Verifies password and returns a session token.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"login:{client_ip}"
    decision = auth_rate_limiter.check(rate_key)
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again shortly.",
            headers={"Retry-After": str(decision.retry_after_seconds or 1)},
        )

    profile = await authenticate_profile(
        profile_id=login_data.profile_id,
        password=login_data.password,
        db=db,
    )

    if not profile:
        auth_rate_limiter.add_failure(rate_key)
        # Use generic error message to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    auth_rate_limiter.reset(rate_key)

    # Update profile state
    profile.is_locked = False
    profile.last_accessed_at = datetime.utcnow()

    # Create audit log
    await log_profile_event(
        db=db,
        event="login",
        profile_id=profile.id,
        profile_name=profile.display_name,
    )

    await db.commit()

    logger.info(f"Profile logged in: {profile.id}")

    # Phase 3: Open the per-profile encrypted database
    await open_profile_database_on_login(profile.id, login_data.password)

    return create_session_token(profile)


# =============================================================================
# Protected endpoints (authentication required)
# =============================================================================


@router.get("/me", response_model=ProfileResponse)
async def get_current_profile(
    session: RequireAuth,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current authenticated profile.

    Returns the profile associated with the session token.
    """
    result = await db.execute(select(Profile).where(Profile.id == session.profile_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    return ProfileResponse.from_model(profile)


@router.post("/logout")
async def logout(
    session: RequireAuth,
    db: AsyncSession = Depends(get_db),
):
    """
    Log out the current session.

    Phase 3: Now closes the per-profile encrypted database and clears
    encryption keys from memory.

    Phase 4: Revokes the current JWT (by `jti`) so it cannot be reused after logout.
    """
    if session.token_jti:
        revoke_jwt_token(session.token_jti, int(session.expires_at.timestamp()))

    result = await db.execute(select(Profile).where(Profile.id == session.profile_id))
    profile = result.scalar_one_or_none()

    if profile:
        profile.is_locked = True

        await log_profile_event(
            db=db,
            event="logout",
            profile_id=profile.id,
            profile_name=profile.display_name,
        )

        await db.commit()

    # Phase 3: Close the per-profile encrypted database and clear keys
    await close_profile_database_on_logout(session.profile_id)

    logger.info(f"Profile logged out: {session.profile_id}")

    return {"status": "logged_out"}


@router.post("/test/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_synthetic_test_profile(
    session: RequireAuth,
    profile_db: ProfileDbSession,
):
    """
    Reset data for the authenticated Playwright synthetic profile.

    This endpoint is intentionally unavailable in production and only accepts
    profiles whose display name starts with the Playwright E2E prefix. It uses
    the normal session JWT path and does not create an auth bypass.
    """
    if settings.app_env == "production":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if not session.profile_name.startswith(_SYNTHETIC_E2E_PROFILE_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test reset is limited to synthetic Playwright profiles",
        )

    try:
        for model in (
            Embedding,
            Chunk,
            DocumentEntity,
            DocumentCategory,
            LabInterpretation,
            PanelInterpretation,
            Observation,
            Document,
            DoseTaken,
            ReminderLog,
            AdherencePattern,
            MedicationSchedule,
            Medication,
            MemoryItem,
            UserModelSettings,
            EarnedBadge,
        ):
            await profile_db.execute(delete(model))

        docs_path = Path(settings.app_data_path) / "vaults" / session.profile_id / "docs"
        if docs_path.exists():
            shutil.rmtree(docs_path)
        docs_path.mkdir(parents=True, exist_ok=True)

        await profile_db.commit()
    except Exception as exc:
        await profile_db.rollback()
        logger.exception("Synthetic profile reset failed for %s", session.profile_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synthetic profile reset failed: {exc}",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: str,
    session: Session = Depends(require_profile_access()),
    db: AsyncSession = Depends(get_db),
):
    """
    Get profile details.

    Requires authentication and access to the specified profile.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    return ProfileResponse.from_model(profile)


@router.post("/{profile_id}/lock", response_model=ProfileResponse)
async def lock_profile(
    profile_id: str,
    session: Session = Depends(require_profile_access()),
    db: AsyncSession = Depends(get_db),
):
    """
    Lock a profile.

    Phase 3: Closes the per-profile encrypted database and clears
    encryption keys from memory, preventing further access until unlock.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    profile.is_locked = True

    await log_profile_event(
        db=db,
        event="lock",
        profile_id=profile_id,
        profile_name=profile.display_name,
    )

    await db.commit()

    # Phase 3: Close the per-profile encrypted database and clear keys
    await close_profile_database_on_logout(profile_id)

    # Revoke the current JWT so the session can't be reused after locking.
    if session.token_jti:
        revoke_jwt_token(session.token_jti, int(session.expires_at.timestamp()))

    logger.info(f"Profile locked: {profile_id}")

    return ProfileResponse.from_model(profile)


@router.post("/{profile_id}/unlock", response_model=TokenResponse)
async def unlock_profile(
    profile_id: str,
    unlock_data: ProfileUnlock,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Unlock a profile with password.

    Phase 3: Re-opens the per-profile encrypted database with the
    provided password.

    Verifies password and returns a new session token.
    This is equivalent to login but uses the profile_id from the path.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"unlock:{client_ip}"
    decision = auth_rate_limiter.check(rate_key)
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many unlock attempts. Please try again shortly.",
            headers={"Retry-After": str(decision.retry_after_seconds or 1)},
        )

    profile = await authenticate_profile(
        profile_id=profile_id,
        password=unlock_data.password,
        db=db,
    )

    if not profile:
        auth_rate_limiter.add_failure(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    auth_rate_limiter.reset(rate_key)

    profile.is_locked = False
    profile.last_accessed_at = datetime.utcnow()

    await log_profile_event(
        db=db,
        event="unlock",
        profile_id=profile_id,
        profile_name=profile.display_name,
    )

    await db.commit()

    # Phase 3: Re-open the per-profile encrypted database
    await open_profile_database_on_login(profile_id, unlock_data.password)

    logger.info(f"Profile unlocked: {profile_id}")

    return create_session_token(profile)


@router.post("/{profile_id}/change-password")
async def change_password(
    profile_id: str,
    password_data: PasswordChange,
    session: Session = Depends(require_profile_access()),
    db: AsyncSession = Depends(get_db),
):
    """
    Change the profile password.

    Requires current password for verification.
    Re-seals the encryption key with the new password.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Verify current password
    verified_profile = await authenticate_profile(
        profile_id=profile_id,
        password=password_data.current_password,
        db=db,
    )

    if not verified_profile:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Load and unseal the existing encryption key
    vault_path = Path(settings.app_data_path) / "vaults" / profile_id
    key_path = vault_path / "key.bin"
    method_path = vault_path / "key.method"

    if not key_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vault key not found",
        )

    sealed_key = key_path.read_bytes()
    seal_method = method_path.read_text().strip() if method_path.exists() else "password"

    try:
        encryption_key = unseal_key_with_dpapi(
            sealed_key,
            seal_method,
            fallback_password=password_data.current_password,
        )
    except KeySealingError as e:
        logger.error(f"Failed to unseal key for password change: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to access vault key",
        )

    # Re-seal with new password
    try:
        new_sealed_key, new_seal_method = seal_key_with_dpapi(
            encryption_key, fallback_password=password_data.new_password
        )
    except KeySealingError as e:
        logger.error(f"Failed to re-seal key with new password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update vault key",
        )

    # Write new sealed key
    key_path.write_bytes(new_sealed_key)
    method_path.write_text(new_seal_method)

    # Update password hash
    new_salt = generate_salt()
    profile.password_hash = hash_password(password_data.new_password)
    profile.password_salt = base64.b64encode(new_salt).decode("ascii")
    profile.updated_at = datetime.utcnow()

    await log_profile_event(
        db=db,
        event="password_change",
        profile_id=profile_id,
        profile_name=profile.display_name,
    )

    await db.commit()

    logger.info(f"Password changed for profile: {profile_id}")

    return {"status": "password_changed"}
