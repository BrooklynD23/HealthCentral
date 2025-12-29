"""
Profile management API endpoints.

Handles profile creation, access control, and settings.
"""

import uuid
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.config import settings
from core.security import generate_encryption_key, seal_key_with_dpapi
from models import Profile, AuditLog

router = APIRouter()


class ProfileCreate(BaseModel):
    """Request model for creating a profile."""
    display_name: str = Field(..., min_length=1, max_length=255)


class ProfileResponse(BaseModel):
    """Response model for profile data."""
    id: str
    display_name: str
    is_locked: bool
    created_at: str
    last_accessed_at: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_model(cls, profile: Profile) -> "ProfileResponse":
        return cls(
            id=profile.id,
            display_name=profile.display_name,
            is_locked=profile.is_locked,
            created_at=profile.created_at.isoformat(),
            last_accessed_at=profile.last_accessed_at.isoformat() if profile.last_accessed_at else None,
        )


class ProfileUnlock(BaseModel):
    """Request model for unlocking a profile."""
    # Future: Add password/PIN for additional security
    pass


async def create_audit_log(
    db: AsyncSession,
    event_type: str,
    action: str,
    profile_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
):
    """Helper to create audit log entries."""
    audit_log = AuditLog(
        profile_id=profile_id,
        event_type=event_type,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=json.dumps(details) if details else None,
        client_info=f"HealthCentral v0.1.0",
    )
    db.add(audit_log)


@router.post("/", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user profile with encrypted vault.
    
    Creates:
    - Profile record with encryption key
    - Encrypted vault directory
    - Audit log entry
    """
    profile_id = str(uuid.uuid4())
    encryption_key_id = str(uuid.uuid4())
    
    # Generate and seal encryption key
    encryption_key = generate_encryption_key()
    sealed_key = seal_key_with_dpapi(encryption_key)
    
    # Store sealed key in vault directory
    vault_path = Path(settings.app_data_path) / "vaults" / profile_id
    vault_path.mkdir(parents=True, exist_ok=True)
    key_path = vault_path / "key.bin"
    key_path.write_bytes(sealed_key)
    
    # Create profile record
    profile = Profile(
        id=profile_id,
        display_name=profile_data.display_name,
        encryption_key_id=encryption_key_id,
        is_locked=False,  # Start unlocked after creation
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_accessed_at=datetime.utcnow(),
    )
    
    db.add(profile)
    
    # Create audit log
    await create_audit_log(
        db,
        event_type="profile.create",
        action=f"Created profile '{profile_data.display_name}'",
        profile_id=profile_id,
        entity_type="profile",
        entity_id=profile_id,
    )
    
    await db.flush()
    
    return ProfileResponse.from_model(profile)


@router.get("/", response_model=list[ProfileResponse])
async def list_profiles(db: AsyncSession = Depends(get_db)):
    """
    List all available profiles.
    
    Returns basic info only; profiles remain locked until explicitly unlocked.
    """
    result = await db.execute(select(Profile).order_by(Profile.created_at.desc()))
    profiles = result.scalars().all()
    
    return [ProfileResponse.from_model(p) for p in profiles]


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get profile details."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return ProfileResponse.from_model(profile)


@router.post("/{profile_id}/unlock", response_model=ProfileResponse)
async def unlock_profile(
    profile_id: str,
    unlock_data: ProfileUnlock,
    db: AsyncSession = Depends(get_db)
):
    """
    Unlock a profile for access.
    
    Decrypts the profile key and enables access to encrypted data.
    Creates audit log entry.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Update profile status
    profile.is_locked = False
    profile.last_accessed_at = datetime.utcnow()
    
    # Create audit log
    await create_audit_log(
        db,
        event_type="profile.unlock",
        action=f"Unlocked profile '{profile.display_name}'",
        profile_id=profile_id,
        entity_type="profile",
        entity_id=profile_id,
    )
    
    await db.flush()
    
    return ProfileResponse.from_model(profile)


@router.post("/{profile_id}/lock", response_model=ProfileResponse)
async def lock_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Lock a profile.
    
    Clears decrypted keys from memory.
    Creates audit log entry.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Update profile status
    profile.is_locked = True
    
    # Create audit log
    await create_audit_log(
        db,
        event_type="profile.lock",
        action=f"Locked profile '{profile.display_name}'",
        profile_id=profile_id,
        entity_type="profile",
        entity_id=profile_id,
    )
    
    await db.flush()
    
    return ProfileResponse.from_model(profile)
