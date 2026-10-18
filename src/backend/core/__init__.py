"""
Core module - Configuration, security, database, and authentication utilities.
"""

from .audit import create_audit_log, log_document_event, log_observation_event, log_profile_event
from .auth import (
    LoginRequest,
    OptionalAuth,
    RequireAuth,
    Session,
    TokenResponse,
    authenticate_profile,
    create_session_token,
    get_current_session,
    require_auth,
    require_profile_access,
)
from .config import settings
from .database import close_database, get_db, init_database

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
