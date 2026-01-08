"""
Centralized audit logging for HealthCentral.

Provides HIPAA-compliant audit trail functionality.
All significant operations should be logged through this module.
"""

import json
import logging
from typing import Optional, Any, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

# Deferred import to avoid circular dependency
# models/__init__.py -> profile.py -> core.database -> core/__init__.py -> core.audit -> models
if TYPE_CHECKING:
    from models import AuditLog

logger = logging.getLogger(__name__)


def _get_audit_log_class():
    """Lazy import of AuditLog to avoid circular imports."""
    from models.audit import AuditLog
    return AuditLog


async def create_audit_log(
    db: AsyncSession,
    event_type: str,
    action: str,
    profile_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    client_info: str = "HealthCentral v0.1.0",
) -> "AuditLog":
    """
    Create an audit log entry.

    This function centralizes all audit logging to ensure consistency
    and HIPAA compliance across the application.

    Args:
        db: Database session
        event_type: Category of event (e.g., 'profile.create', 'document.import')
        action: Human-readable description of the action
        profile_id: ID of the profile performing or affected by the action
        entity_type: Type of entity affected (e.g., 'profile', 'document', 'observation')
        entity_id: ID of the affected entity
        details: Additional details as a dictionary (will be JSON-serialized)
        client_info: Client/version information

    Returns:
        The created AuditLog instance

    Event Type Conventions:
        - profile.create, profile.unlock, profile.lock, profile.delete
        - document.import, document.view, document.delete
        - observation.verify, observation.edit
        - export.create
        - auth.login, auth.logout, auth.failed
    """
    AuditLog = _get_audit_log_class()
    audit_log = AuditLog(
        profile_id=profile_id,
        event_type=event_type,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=json.dumps(details) if details else None,
        client_info=client_info,
    )
    db.add(audit_log)

    # Log to application logger as well for operational monitoring
    logger.info(
        f"AUDIT: {event_type} - {action}",
        extra={
            "profile_id": profile_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
        }
    )

    return audit_log


# Convenience functions for common audit events

async def log_profile_event(
    db: AsyncSession,
    event: str,
    profile_id: str,
    profile_name: str,
    details: Optional[dict[str, Any]] = None,
) -> "AuditLog":
    """Log a profile-related event."""
    action_map = {
        "create": f"Created profile '{profile_name}'",
        "unlock": f"Unlocked profile '{profile_name}'",
        "lock": f"Locked profile '{profile_name}'",
        "delete": f"Deleted profile '{profile_name}'",
        "update": f"Updated profile '{profile_name}'",
    }
    return await create_audit_log(
        db=db,
        event_type=f"profile.{event}",
        action=action_map.get(event, f"Profile {event}: '{profile_name}'"),
        profile_id=profile_id,
        entity_type="profile",
        entity_id=profile_id,
        details=details,
    )


async def log_document_event(
    db: AsyncSession,
    event: str,
    profile_id: str,
    document_id: str,
    filename: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> "AuditLog":
    """Log a document-related event."""
    name = filename or document_id
    action_map = {
        "import": f"Imported document '{name}'",
        "view": f"Viewed document '{name}'",
        "delete": f"Deleted document '{name}'",
        "parse": f"Parsed document '{name}'",
        "verify": f"Verified document '{name}'",
    }
    return await create_audit_log(
        db=db,
        event_type=f"document.{event}",
        action=action_map.get(event, f"Document {event}: '{name}'"),
        profile_id=profile_id,
        entity_type="document",
        entity_id=document_id,
        details=details,
    )


async def log_observation_event(
    db: AsyncSession,
    event: str,
    profile_id: str,
    observation_id: str,
    analyte: str,
    details: Optional[dict[str, Any]] = None,
) -> "AuditLog":
    """Log an observation-related event."""
    action_map = {
        "verify": f"Verified observation '{analyte}'",
        "edit": f"Edited observation '{analyte}'",
        "delete": f"Deleted observation '{analyte}'",
    }
    return await create_audit_log(
        db=db,
        event_type=f"observation.{event}",
        action=action_map.get(event, f"Observation {event}: '{analyte}'"),
        profile_id=profile_id,
        entity_type="observation",
        entity_id=observation_id,
        details=details,
    )


async def log_export_event(
    db: AsyncSession,
    profile_id: str,
    export_type: str,
    details: Optional[dict[str, Any]] = None,
) -> "AuditLog":
    """Log an export event."""
    return await create_audit_log(
        db=db,
        event_type="export.create",
        action=f"Exported data as {export_type}",
        profile_id=profile_id,
        entity_type="export",
        details=details,
    )


async def log_auth_event(
    db: AsyncSession,
    event: str,
    profile_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> "AuditLog":
    """Log an authentication event."""
    action_map = {
        "login": "User logged in",
        "logout": "User logged out",
        "failed": "Authentication failed",
        "session_expired": "Session expired",
    }
    return await create_audit_log(
        db=db,
        event_type=f"auth.{event}",
        action=action_map.get(event, f"Auth {event}"),
        profile_id=profile_id,
        entity_type="auth",
        details=details,
    )
