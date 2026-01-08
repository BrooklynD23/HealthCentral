"""
Authentication and session management for HealthCentral.

Provides:
- JWT-based session tokens
- Profile authentication dependencies
- Session validation middleware
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from .security import (
    create_access_token,
    verify_token,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from models import Profile

logger = logging.getLogger(__name__)


# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class Session:
    """Represents an authenticated user session."""

    profile_id: str
    profile_name: str
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.now(timezone.utc) > self.expires_at


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    profile_id: str
    profile_name: str


class LoginRequest(BaseModel):
    """Request model for profile login."""

    profile_id: str
    password: str


async def authenticate_profile(
    profile_id: str,
    password: str,
    db: AsyncSession,
) -> Optional[Profile]:
    """
    Authenticate a profile with password.

    Args:
        profile_id: The profile UUID
        password: The plaintext password
        db: Database session

    Returns:
        Profile if authentication succeeds, None otherwise
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()

    if not profile:
        logger.warning(f"Authentication failed: profile not found: {profile_id}")
        return None

    if not profile.password_hash:
        logger.warning(f"Authentication failed: profile has no password set: {profile_id}")
        return None

    if not verify_password(password, profile.password_hash):
        logger.warning(f"Authentication failed: invalid password for profile: {profile_id}")
        return None

    return profile


def create_session_token(profile: Profile) -> TokenResponse:
    """
    Create a session token for an authenticated profile.

    Args:
        profile: The authenticated profile

    Returns:
        TokenResponse with JWT and metadata
    """
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = datetime.now(timezone.utc) + expires_delta

    token_data = {
        "sub": profile.id,
        "name": profile.display_name,
        "type": "session",
    }

    access_token = create_access_token(token_data, expires_delta)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(expires_delta.total_seconds()),
        profile_id=profile.id,
        profile_name=profile.display_name,
    )


async def get_current_session(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    db: AsyncSession = Depends(get_db),
) -> Optional[Session]:
    """
    Get the current session from the authorization header.

    This dependency is optional - returns None if no valid token.
    Use require_auth for endpoints that require authentication.

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        Session if valid token provided, None otherwise
    """
    if not credentials:
        return None

    payload = verify_token(credentials.credentials)
    if not payload:
        return None

    # Validate token type
    if payload.get("type") != "session":
        return None

    profile_id = payload.get("sub")
    if not profile_id:
        return None

    # Verify profile still exists
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        return None

    # Parse expiration
    exp_timestamp = payload.get("exp")
    if not exp_timestamp:
        return None

    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

    return Session(
        profile_id=profile_id,
        profile_name=payload.get("name", ""),
        expires_at=expires_at,
    )


async def require_auth(
    session: Annotated[Optional[Session], Depends(get_current_session)],
) -> Session:
    """
    Require authentication for an endpoint.

    Raises HTTPException 401 if not authenticated.

    Args:
        session: Current session from get_current_session

    Returns:
        Valid Session

    Raises:
        HTTPException: 401 if not authenticated
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if session.is_expired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return session


def require_profile_access(profile_id_param: str = "profile_id"):
    """
    Factory for creating a dependency that requires access to a specific profile.

    Verifies that the authenticated session's profile_id matches the
    profile_id parameter in the request.

    Args:
        profile_id_param: Name of the path parameter containing profile_id

    Returns:
        Dependency function
    """
    async def verify_profile_access(
        request: Request,
        session: Session = Depends(require_auth),
    ) -> Session:
        """Verify the session has access to the requested profile."""
        # Get profile_id from path parameters
        profile_id = request.path_params.get(profile_id_param)

        if not profile_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {profile_id_param} parameter",
            )

        if session.profile_id != profile_id:
            logger.warning(
                f"Profile access denied: session profile {session.profile_id} "
                f"attempted to access {profile_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this profile",
            )

        return session

    return verify_profile_access


# Convenience dependency for common case
RequireAuth = Annotated[Session, Depends(require_auth)]
OptionalAuth = Annotated[Optional[Session], Depends(get_current_session)]
