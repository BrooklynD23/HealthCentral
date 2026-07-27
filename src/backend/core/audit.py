"""
Centralized audit logging for HealthCentral.

Provides HIPAA-compliant audit trail functionality.
All significant operations should be logged through this module.
"""

import json
import logging
import re
from typing import Optional, Any, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

# Deferred import to avoid circular dependency
# models/__init__.py -> profile.py -> core.database -> core/__init__.py -> core.audit -> models
if TYPE_CHECKING:
    from models import AuditLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AUDIT-PHI-001 Phase A — PHI minimization allowlist
#
# Audit rows live in the *unencrypted* master DB — the one place patient-linked
# data escapes the SQLCipher boundary. Everything below is enforced inside
# create_audit_log, the single choke point every log_*_event helper and every
# agent audit event funnels through, so a new call site cannot regress it.
#
# Phase B (encrypting the master DB) is explicitly out of scope and gated.
# ---------------------------------------------------------------------------

# Static action strings. Anything not listed is replaced by the event_type,
# which is itself always a static enum-shaped string.
ALLOWED_ACTIONS: frozenset[str] = frozenset({
    # profile
    "Created profile", "Unlocked profile", "Locked profile", "Deleted profile",
    "Updated profile", "Generated profile recovery code",
    "Recovered profile access with recovery code", "Recovery attempt failed",
    # document
    "Imported document", "Viewed document", "Deleted document",
    "Parsed document", "Verified document",
    # observation
    "Verified observation", "Edited observation", "Deleted observation",
    "Viewed observation",
    # care tasks / pinboards
    "Viewed care plan tasks", "Accepted care plan task", "Updated care plan task",
    "Viewed pinboards", "Created pinboard", "Renamed pinboard", "Deleted pinboard",
    "Added item to pinboard", "Removed item from pinboard", "Exported pinboard packet",
    # export / auth / misc read routes
    "Exported data", "User logged in", "User logged out",
    "Authentication failed", "Session expired",
    "Searched health records", "Viewed timeline", "Viewed highlights",
    "Viewed medication reconciliation", "Exported RL dataset", "Recorded response feedback",
})

# Keys whose *string* values may survive (still subject to _ENUM_VALUE_RE).
STRING_DETAIL_KEYS: frozenset[str] = frozenset({
    "action", "status", "status_filter", "tool_name", "entity_type", "entity_id",
    "item_id", "item_type", "doc_id", "doc_type", "document_id", "export_id",
    "export_type", "format", "packet_id", "summary_id", "source_kind",
    "source_document_id", "source_entity_id", "observation_id", "category",
    "highlight_type", "event_type", "event_type_filter", "decision", "direction",
    "handle", "abstain_reason", "since_date", "trigger", "reason",
})

# Keys holding short lists of opaque identifiers.
ID_LIST_DETAIL_KEYS: frozenset[str] = frozenset({
    "entity_ids", "observation_ids", "chunk_ids", "task_ids", "event_ids",
    "changed_fields",
})

# Keys holding {str: int} count maps.
COUNT_MAP_DETAIL_KEYS: frozenset[str] = frozenset({"resource_counts"})

# Everything writable to `details`. Ids, counts, enums and booleans only —
# no filenames, no analyte or medication names, no free user text.
ALLOWED_DETAIL_KEYS: frozenset[str] = (
    STRING_DETAIL_KEYS
    | ID_LIST_DETAIL_KEYS
    | COUNT_MAP_DETAIL_KEYS
    | frozenset({
        # counts and sizes
        "count", "limit", "page_number", "item_count", "match_count",
        "observation_count", "question_count", "citation_count", "sentence_count",
        "redaction_count", "verified_count", "undated_count", "skipped_count",
        "dropped_count", "surviving_count", "remaining_budget", "step_index",
        "observations_extracted", "observations_imported", "entities_imported",
        "audit_rows_purged", "dpo_pairs", "grpo", "sft",
        # booleans
        "verified", "found", "encrypted", "terminal", "gate_fired", "llm_assist",
        "duplicate_warning", "name_changed", "user_note_changed", "has_correction",
        "provider_filter", "date_filter", "analyte_filter_present",
        "password_reset", "recovery_rotated",
        # numeric ratings
        "rating",
    })
)

# No spaces => free prose cannot pass. Bounded length => no smuggling.
_ENUM_VALUE_RE = re.compile(r"^[A-Za-z0-9_.:/\-]{1,64}$")

# Longer id lists collapse to a count rather than being dropped silently.
_MAX_ID_LIST_LEN = 50


def _scrub_details(details: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Allowlist-filter an audit ``details`` dict (AUDIT-PHI-001).

    Drops every non-allowlisted key and every value whose *shape* could carry
    free text. Records how many entries were dropped as ``_scrubbed`` so the
    minimization is visible without recording what was minimized.

    Never raises: audit is fail-closed on read routes, so an exception here
    would turn a scrubbing bug into a 500 on a GET.
    """
    if not details:
        return None

    scrubbed: dict[str, Any] = {}
    dropped = 0

    for key, value in details.items():
        try:
            if key not in ALLOWED_DETAIL_KEYS:
                dropped += 1
            elif value is None or isinstance(value, bool) or isinstance(value, (int, float)):
                # bool first: it is an int subclass and must stay a bool.
                scrubbed[key] = value
            elif isinstance(value, str):
                if key in STRING_DETAIL_KEYS and _ENUM_VALUE_RE.match(value):
                    scrubbed[key] = value
                else:
                    dropped += 1
            elif isinstance(value, list):
                if key not in ID_LIST_DETAIL_KEYS:
                    dropped += 1
                elif len(value) > _MAX_ID_LIST_LEN:
                    scrubbed[f"{key}_count"] = len(value)
                elif all(isinstance(v, str) and _ENUM_VALUE_RE.match(v) for v in value):
                    scrubbed[key] = list(value)
                else:
                    dropped += 1
            elif isinstance(value, dict):
                if key in COUNT_MAP_DETAIL_KEYS and all(
                    isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool)
                    for k, v in value.items()
                ):
                    scrubbed[key] = dict(value)
                else:
                    dropped += 1
            else:
                dropped += 1
        except Exception:  # pragma: no cover - defensive; must never 500 a route
            dropped += 1

    if dropped:
        scrubbed["_scrubbed"] = dropped
    return scrubbed or None


def _scrub_action(action: str, event_type: str) -> str:
    """Return ``action`` only if it is a registered static template.

    Unregistered actions are replaced by ``event_type`` (always static) rather
    than raising: audit_and_commit is fail-closed, so raising on a string
    registry miss would 500 a production read route. HC-AUD-004 is the
    regression gate that keeps the registry honest instead.
    """
    if action in ALLOWED_ACTIONS:
        return action
    logger.warning(
        "Unregistered audit action replaced by event type (AUDIT-PHI-001)",
        extra={"event_type": event_type},
    )
    return event_type


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
    # AUDIT-PHI-001: minimize before anything is written or logged. This is the
    # single choke point — new call sites inherit it without opting in.
    safe_action = _scrub_action(action, event_type)
    safe_details = _scrub_details(details)

    AuditLog = _get_audit_log_class()
    audit_log = AuditLog(
        profile_id=profile_id,
        event_type=event_type,
        action=safe_action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=json.dumps(safe_details) if safe_details else None,
        client_info=client_info,
    )
    db.add(audit_log)

    # Log to application logger as well for operational monitoring. Uses the
    # scrubbed action: the app log is plaintext too, so echoing the raw string
    # here would be a second copy of the same leak.
    logger.info(
        f"AUDIT: {event_type} - {safe_action}",
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
    """Log a profile-related event.

    ``profile_name`` is accepted for call-site compatibility and is never
    persisted — a display name is patient-identifying and the master DB is
    unencrypted (AUDIT-PHI-001).
    """
    action_map = {
        "create": "Created profile",
        "unlock": "Unlocked profile",
        "lock": "Locked profile",
        "delete": "Deleted profile",
        "update": "Updated profile",
        "recovery_code_generated": "Generated profile recovery code",
        "recovered": "Recovered profile access with recovery code",
        "recovery_failed": "Recovery attempt failed",
    }
    return await create_audit_log(
        db=db,
        event_type=f"profile.{event}",
        action=action_map.get(event, f"profile.{event}"),
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
    """Log a document-related event.

    ``filename`` is accepted for call-site compatibility and is never persisted
    — real filenames are "LabCorp_2026_glucose_JaneDoe.pdf"-shaped, i.e. both
    identifying and clinical (AUDIT-PHI-001). ``document_id`` is the join key
    into the encrypted profile DB where the filename legitimately lives.
    """
    action_map = {
        "import": "Imported document",
        "view": "Viewed document",
        "delete": "Deleted document",
        "parse": "Parsed document",
        "verify": "Verified document",
    }
    return await create_audit_log(
        db=db,
        event_type=f"document.{event}",
        action=action_map.get(event, f"document.{event}"),
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
    """Log an observation-related event.

    ``analyte`` is accepted for call-site compatibility and is never persisted —
    which biomarkers a patient has tested is clinical content (AUDIT-PHI-001).
    """
    action_map = {
        "verify": "Verified observation",
        "edit": "Edited observation",
        "delete": "Deleted observation",
        "view": "Viewed observation",
    }
    return await create_audit_log(
        db=db,
        event_type=f"observation.{event}",
        action=action_map.get(event, f"observation.{event}"),
        profile_id=profile_id,
        entity_type="observation",
        entity_id=observation_id,
        details=details,
    )


async def log_care_task_event(
    db: AsyncSession,
    event: str,
    profile_id: str,
    task_id: str,
    details: Optional[dict[str, Any]] = None,
) -> "AuditLog":
    """Log a care-plan task event (HC-M15)."""
    action_map = {
        "view": "Viewed care plan tasks",
        "create": "Accepted care plan task",
        "update": "Updated care plan task",
    }
    return await create_audit_log(
        db=db,
        event_type=f"care_task.{event}",
        action=action_map.get(event, f"Care plan task {event}"),
        profile_id=profile_id,
        entity_type="care_task",
        entity_id=task_id,
        details=details,
    )


async def log_pinboard_event(
    db: AsyncSession,
    event: str,
    profile_id: str,
    pinboard_id: str,
    details: Optional[dict[str, Any]] = None,
) -> "AuditLog":
    """Log a pinboard or pinboard-item event (HC-M20)."""
    action_map = {
        "view": "Viewed pinboards",
        "create": "Created pinboard",
        "update": "Renamed pinboard",
        "delete": "Deleted pinboard",
        "item_add": "Added item to pinboard",
        "item_remove": "Removed item from pinboard",
        "export": "Exported pinboard packet",
    }
    return await create_audit_log(
        db=db,
        event_type=f"pinboard.{event}",
        action=action_map.get(event, f"Pinboard {event}"),
        profile_id=profile_id,
        entity_type="pinboard",
        entity_id=pinboard_id,
        details=details,
    )


async def log_export_event(
    db: AsyncSession,
    profile_id: str,
    export_type: str,
    details: Optional[dict[str, Any]] = None,
) -> "AuditLog":
    """Log an export event.

    ``export_type`` is enum-valued, so it moves into ``details`` rather than
    being interpolated into the action string (AUDIT-PHI-001: actions stay
    static templates).
    """
    return await create_audit_log(
        db=db,
        event_type="export.create",
        action="Exported data",
        profile_id=profile_id,
        entity_type="export",
        details={**(details or {}), "export_type": export_type},
    )


async def audit_and_commit(
    db: AsyncSession,
    log_fn: Any,
    **log_kwargs: Any,
) -> "AuditLog":
    """Write an audit row and commit it, fail-closed.

    Used by read (view) routes. Any failure propagates to the caller and
    fails the request: a view that cannot be audited must not be served
    (consistent with write routes, which never swallowed audit errors).
    """
    entry = await log_fn(db=db, **log_kwargs)
    await db.commit()
    return entry


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
