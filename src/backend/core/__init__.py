"""
Core module - Configuration, security, and database utilities.
"""

from .config import settings
from .database import get_db, init_database, close_database
from .audit import create_audit_log, log_profile_event, log_document_event, log_observation_event

__all__ = [
    "settings",
    "get_db",
    "init_database",
    "close_database",
    "create_audit_log",
    "log_profile_event",
    "log_document_event",
    "log_observation_event",
]
