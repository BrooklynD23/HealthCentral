"""
Profile management API endpoints.

Handles profile creation, authentication, and access control.
"""

import base64
import os
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
    generate_recovery_code,
    generate_salt,
    hash_password,
    normalize_recovery_code,
    seal_key_with_dpapi,
    unseal_key_with_dpapi,
    revoke_jwt_token,
    KeySealingError,
)
from core.rate_limiter import auth_rate_limiter, recovery_rate_limiter
from core.profile_database import get_profile_db_manager
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
from core.audit import create_audit_log, log_profile_event
from models import (
    AdherencePattern,
    AuditLog,
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

# PROF-DEL-001: fixed, locale-stable confirmation phrase. Deliberately not the
# profile display name — that would put a patient identifier in the request body.
PROFILE_DELETE_CONFIRMATION = "DELETE MY HEALTH DATA"

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
    has_recovery_code: bool
    created_at: str

    @classmethod
    def from_model(cls, profile: Profile) -> "ProfileListResponse":
        return cls(
            id=profile.id,
            display_name=profile.display_name,
            has_password=profile.password_hash is not None,
            # Whether to offer "Forgot password?" on the unlock screen. Derived
            # from file existence, so it cannot desync from the actual seal.
            has_recovery_code=get_profile_db_manager().has_recovery_key(profile.id),
            created_at=profile.created_at.isoformat(),
        )


class ProfileUnlock(BaseModel):
    """Request model for unlocking a profile."""

    password: str


class ProfileCreateResponse(TokenResponse):
    """Session token plus the one-time recovery code shown at creation."""

    recovery_code: str


class ProfileRecoverRequest(BaseModel):
    """Request model for unlocking a profile with its recovery code."""

    recovery_code: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Same strength bar as profile creation — recovery must not be a
        back door to a weaker password."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class RecoveryCodeResponse(BaseModel):
    """A freshly generated recovery code, returned exactly once."""

    recovery_code: str
    replaced_existing: bool


class RecoveryResponse(TokenResponse):
    """Session token plus the rotated recovery code, shown once."""

    recovery_code: str


class ProfileDeleteRequest(BaseModel):
    """Request model for irreversibly deleting a profile (PROF-DEL-001).

    ``confirmation_phrase`` is a fixed constant rather than the profile's
    display name: it is deterministic for e2e tests and it keeps a
    patient-identifying string out of the request body (and therefore out of
    any request log).
    """

    password: str
    confirmation_phrase: str
    export_acknowledged: bool = False


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


@router.post("/", response_model=ProfileCreateResponse, status_code=status.HTTP_201_CREATED)
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

    # SEC-RECOV-001: seal a second copy of the same DEK under a one-time
    # recovery code, so a forgotten password is no longer permanent loss of the
    # record. Done after the profile row is committed so a failure here cannot
    # orphan a half-created profile.
    recovery_code = _issue_recovery_code(profile_id, encryption_key)
    await log_profile_event(
        db=db,
        event="recovery_code_generated",
        profile_id=profile_id,
        profile_name=profile_data.display_name,
        details={"trigger": "profile_create"},
    )
    await db.commit()

    # Return session token for immediate access
    token = create_session_token(profile)
    return ProfileCreateResponse(**token.model_dump(), recovery_code=recovery_code)


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


def _atomic_write(path: Path, data: bytes) -> None:
    """Write a key artifact atomically.

    A half-written sealed key is an unopenable vault, so the new bytes land in
    a sibling temp file and are moved into place with os.replace.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _issue_recovery_code(profile_id: str, dek: bytes) -> str:
    """Seal a second copy of ``dek`` under a fresh recovery code and return it.

    The code itself is never persisted, logged, or hashed — only the seal it
    derives. A stored hash would be an offline verification oracle with no
    operational upside.

    ``force_password=True`` is mandatory here: a DPAPI-sealed recovery copy
    would be tied to the current OS user account and therefore useless after
    the reinstall it exists to survive.
    """
    code = generate_recovery_code()
    sealed, method = seal_key_with_dpapi(
        dek,
        fallback_password=normalize_recovery_code(code),
        force_password=True,
    )

    manager = get_profile_db_manager()
    _atomic_write(manager._get_profile_recovery_key_path(profile_id), sealed)
    _atomic_write(manager._get_profile_recovery_method_path(profile_id), method.encode())
    return code


def _unseal_dek_with_recovery_code(profile_id: str, code: str) -> bytes:
    """Recover the DEK from the recovery-sealed copy.

    Raises KeySealingError if the code is wrong — Fernet is authenticated, so
    a bad code fails to decrypt. There is deliberately no stored verifier.
    """
    manager = get_profile_db_manager()
    key_path = manager._get_profile_recovery_key_path(profile_id)
    method_path = manager._get_profile_recovery_method_path(profile_id)

    if not key_path.exists():
        raise KeySealingError("This profile has no recovery code")

    method = method_path.read_text().strip() if method_path.exists() else "password"
    return unseal_key_with_dpapi(
        key_path.read_bytes(), method, fallback_password=normalize_recovery_code(code)
    )


@router.post("/{profile_id}/recovery-code", response_model=RecoveryCodeResponse)
async def issue_recovery_code(
    profile_id: str,
    payload: ProfileUnlock,
    session: Session = Depends(require_profile_access()),
    db: AsyncSession = Depends(get_db),
):
    """Generate (or replace) this profile's recovery code (SEC-RECOV-001).

    Serves both backfill for profiles created before recovery codes existed and
    user-initiated rotation. Requires the password: it is both a re-auth and
    the only way to unseal the DEK that the new copy will re-seal.

    The code is returned exactly once and is not recoverable afterwards.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    if await authenticate_profile(profile_id, payload.password, db) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
        )

    manager = get_profile_db_manager()
    key_path = manager._get_profile_key_path(profile_id)
    method_path = manager._get_profile_key_method_path(profile_id)
    if not key_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Vault key not found"
        )

    method = method_path.read_text().strip() if method_path.exists() else "password"
    try:
        dek = unseal_key_with_dpapi(
            key_path.read_bytes(), method, fallback_password=payload.password
        )
        had_previous = manager.has_recovery_key(profile_id)
        code = _issue_recovery_code(profile_id, dek)
    except KeySealingError as exc:
        logger.error("Recovery code generation failed for a profile")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate a recovery code",
        ) from exc

    await log_profile_event(
        db=db,
        event="recovery_code_generated",
        profile_id=profile_id,
        profile_name=profile.display_name,
        details={"trigger": "user_request" if had_previous else "backfill"},
    )
    await db.commit()

    return RecoveryCodeResponse(recovery_code=code, replaced_existing=had_previous)


@router.post("/{profile_id}/recover", response_model=RecoveryResponse)
async def recover_profile(
    profile_id: str,
    payload: ProfileRecoverRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Unlock a profile with its recovery code and set a new password.

    Unauthenticated by necessity — the caller has lost the password, which is
    the only other credential. Rate-limited because each attempt costs a
    600k-iteration PBKDF2: 160 bits of entropy is not brute-forceable, but an
    unbounded endpoint is a local CPU-exhaustion vector.

    Write order is chosen for crash safety: the primary key files are replaced
    before the password hash is committed. A crash in between leaves the old
    hash with a new-password seal — login fails cleanly and the recovery code
    still works. The inverse order would leave auth accepting a password that
    cannot open the vault.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"recover:{client_ip}:{profile_id}"
    decision = recovery_rate_limiter.check(rate_key)
    if not decision.allowed:
        # No audit row here: the attempts that produced the limit were already
        # logged, and writing on rejection would make this a write amplifier.
        logger.warning("Recovery attempts rate-limited for a profile")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many recovery attempts. Try again later.",
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )

    async def _fail(reason: str, detail: str, code: int) -> None:
        recovery_rate_limiter.add_failure(rate_key)
        await log_profile_event(
            db=db,
            event="recovery_failed",
            profile_id=profile_id,
            profile_name=profile.display_name,
            details={"reason": reason},
        )
        # Commit before raising so the failed attempt cannot be lost to rollback.
        await db.commit()
        raise HTTPException(status_code=code, detail=detail)

    try:
        normalize_recovery_code(payload.recovery_code)
    except ValueError:
        # Rejected before any key derivation — a malformed code costs no PBKDF2.
        await _fail("malformed_code", "That recovery code is not valid.", 400)

    try:
        dek = _unseal_dek_with_recovery_code(profile_id, payload.recovery_code)
    except KeySealingError:
        reason = (
            "no_recovery_seal"
            if not get_profile_db_manager().has_recovery_key(profile_id)
            else "invalid_code"
        )
        await _fail(reason, "That recovery code is not valid.", 401)

    # Re-seal the primary copy under the new password, atomically.
    manager = get_profile_db_manager()
    try:
        sealed_key, seal_method = seal_key_with_dpapi(
            dek, fallback_password=payload.new_password
        )
    except KeySealingError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not re-seal the vault key",
        ) from exc

    _atomic_write(manager._get_profile_key_path(profile_id), sealed_key)
    _atomic_write(manager._get_profile_key_method_path(profile_id), seal_method.encode())

    profile.password_hash = hash_password(payload.new_password)
    profile.password_salt = base64.b64encode(generate_salt()).decode("ascii")
    profile.is_locked = False
    profile.last_accessed_at = datetime.utcnow()

    # Rotate the recovery code rather than invalidating it: plain invalidation
    # would leave the user with *no* recovery until they remember to generate
    # one, a durability regression in the feature whose whole point is
    # durability. Rotation gives one-time-use semantics and keeps the invariant
    # "there is always exactly one valid recovery code".
    new_code = _issue_recovery_code(profile_id, dek)

    recovery_rate_limiter.reset(rate_key)

    await log_profile_event(
        db=db, event="recovered", profile_id=profile_id,
        profile_name=profile.display_name,
        details={"password_reset": True, "recovery_rotated": True},
    )
    await log_profile_event(
        db=db, event="recovery_code_generated", profile_id=profile_id,
        profile_name=profile.display_name,
        details={"trigger": "post_recovery"},
    )
    await db.commit()

    await open_profile_database_on_login(profile_id, payload.new_password)

    logger.info("Profile access recovered with a recovery code")

    token = create_session_token(profile)
    return RecoveryResponse(
        **token.model_dump(),
        recovery_code=new_code,
    )


async def _load_profile_for_delete(profile_id: str, db: AsyncSession) -> Optional[Profile]:
    """Fetch the profile row targeted by a delete, or None if it is already gone."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    return result.scalar_one_or_none()


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: str,
    payload: ProfileDeleteRequest,
    request: Request,
    session: Session = Depends(require_profile_access()),
    db: AsyncSession = Depends(get_db),
):
    """Irreversibly delete a profile and everything belonging to it (PROF-DEL-001).

    Ordering matters and is chosen so that a crash leaves a *recoverable*
    state rather than a corrupt one:

    1. re-authenticate with the password (a session token alone is not enough)
    2. close the profile database, releasing handles and zeroing the in-memory key
    3. **delete the sealed key files first** — destroying the key is the
       cryptographic erase; after this point the vault is unreadable even if
       the database file survives
    4. sweep the whole vault directory (db, WAL/SHM sidecars, encrypted documents)
    5. purge the profile's audit rows, delete the master row, write one
       anonymized tombstone

    What this does **not** claim: overwriting the bytes on disk. SSD
    wear-levelling makes that guarantee false, so the honest claim — and the
    one the UI makes — is file deletion plus key destruction.

    Export-before-erase is handled in the UI: the export routes stream
    downloads rather than writing files server-side, so the client performs the
    export and sets ``export_acknowledged``. Building a second, server-side
    export path that drops a PHI file somewhere with no delivery channel would
    be worse than the problem it solves.
    """
    profile = await _load_profile_for_delete(profile_id, db)
    if profile is None:
        # Already deleted. The frontend treats 404-on-delete as success.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"delete:{client_ip}:{profile_id}"
    decision = auth_rate_limiter.check(rate_key)
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many deletion attempts. Try again later.",
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )

    authenticated = await authenticate_profile(profile_id, payload.password, db)
    if authenticated is None:
        auth_rate_limiter.add_failure(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    if payload.confirmation_phrase != PROFILE_DELETE_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Confirmation phrase must be exactly '{PROFILE_DELETE_CONFIRMATION}'",
        )

    if not payload.export_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Deletion is permanent. Download your data first, then retry "
                "with export_acknowledged set."
            ),
        )

    # A live token must not keep pointing at a profile that no longer exists.
    if session.token_jti:
        revoke_jwt_token(session.token_jti, int(session.expires_at.timestamp()))

    await close_profile_database_on_logout(profile_id)

    from core.profile_database import get_profile_db_manager

    manager = get_profile_db_manager()

    # --- Step 3: the crypto-erase commit point -----------------------------
    # Enumerated from profile_database rather than hardcoded here, so a future
    # sealed copy of the DEK (e.g. a recovery key) is destroyed automatically.
    try:
        for key_path in manager.get_profile_key_paths(profile_id):
            key_path.unlink(missing_ok=True)
    except OSError as exc:
        # Abort *before* the master row goes: leaving it lets the user retry
        # with a re-auth instead of stranding an unreadable orphan vault.
        logger.error("Profile deletion aborted: sealed key could not be destroyed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not destroy the profile encryption key; nothing was deleted.",
        ) from exc

    # --- Step 4: sweep the vault -------------------------------------------
    # The key is already gone, so the data is already cryptographically erased.
    # A filesystem hiccup here (Windows file locks are the usual cause) must
    # not abort the database cleanup; a retry finishes the sweep.
    vault_path = manager.get_profile_vault_path(profile_id)
    try:
        if vault_path.exists():
            shutil.rmtree(vault_path)
    except OSError:
        logger.warning(
            "Vault directory could not be fully removed after key destruction; "
            "data is already unreadable, residual files remain",
        )

    # --- Step 5: master DB, in one transaction ------------------------------
    audit_result = await db.execute(
        delete(AuditLog).where(AuditLog.profile_id == profile_id)
    )
    purged = getattr(audit_result, "rowcount", 0) or 0

    # Core delete(), not db.delete(obj): the ORM cascade would need an eager
    # load of profile.audit_logs and raise MissingGreenlet on the async engine.
    await db.execute(delete(Profile).where(Profile.id == profile_id))

    # The tombstone goes in only after the profile row is gone, with
    # profile_id=None — both the FK requires it and the owner's decision does:
    # it records that a deletion happened, not whose.
    await create_audit_log(
        db=db,
        event_type="profile.delete",
        action="Deleted profile",
        profile_id=None,
        entity_type="profile",
        entity_id=None,
        details={"audit_rows_purged": purged},
    )
    await db.commit()

    logger.info("Profile deleted and vault erased")
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
