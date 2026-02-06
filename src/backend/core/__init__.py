"""
Core module - Configuration, security, database, and authentication utilities.
"""

from .config import settings
from .database import get_db, init_database, close_database
from .audit import create_audit_log, log_profile_event, log_document_event, log_observation_event
from .auth import (
    RequireAuth,
    OptionalAuth,
    Session,
    TokenResponse,
    LoginRequest,
    authenticate_profile,
    create_session_token,
    get_current_session,
    require_auth,
    require_profile_access,
)

__all__ = [
    "settings",
    "get_db",
    "init_database",
    "close_database",
    "create_audit_log",
    "log_profile_event",
    "log_document_event",
    "log_observation_event",
    # Auth exports
    "RequireAuth",
    "OptionalAuth",
    "Session",
    "TokenResponse",
    "LoginRequest",
    "authenticate_profile",
    "create_session_token",
    "get_current_session",
    "require_auth",
    "require_profile_access",
]
