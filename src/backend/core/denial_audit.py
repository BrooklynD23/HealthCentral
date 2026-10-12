"""AUDIT-ORDER AD-DENIALS B: audit cross-profile 403s, capped per caller.

The row records the caller and the artifact kind only: never the requested
artifact id or the target profile id (AUDIT-PHI-001), so a denial cannot be
joined to the owner's own export rows. Best effort: a failed write is logged
(ids only) and never replaces the 403.
"""

from __future__ import annotations

import logging
import time as _time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core import database
from core.audit import create_audit_log

logger = logging.getLogger(__name__)

DENIAL_CAP = 20
DENIAL_WINDOW_SECONDS = 600

monotonic = _time.monotonic  # module-level name so tests can move the clock

# caller profile_id -> [window_start, written, suppressed]
# ponytail: in-process counter resets on restart (plan §12 item 8); persist if abuse matters.
_state: dict[str, list] = {}


async def _write(db: AsyncSession, event_type: str, caller: str,
                 entity_type: Optional[str], details: Optional[dict] = None) -> None:
    await create_audit_log(
        db=db, event_type=event_type, action=event_type, profile_id=caller,
        entity_type=entity_type, entity_id=None, details=details,
    )


async def _audit(db: AsyncSession, caller: str, entity_type: str) -> None:
    now = monotonic()
    window = _state.get(caller)
    if window is None or now - window[0] >= DENIAL_WINDOW_SECONDS:
        if window is not None and window[2] > 0:
            await _write(db, "denial.suppressed", caller, None, {"count": window[2]})
        window = _state[caller] = [now, 0, 0]
    if window[1] < DENIAL_CAP:
        window[1] += 1
        await _write(db, "denial.cross_profile", caller, entity_type)
    else:
        window[2] += 1
    await db.commit()


async def audit_denial(
    caller_profile_id: str, entity_type: str, db: Optional[AsyncSession] = None
) -> None:
    """Write a capped `denial.cross_profile` row and commit it; never raises."""
    session = db
    try:
        if session is None:
            async with database.async_session_maker() as own:
                session = own
                await _audit(own, caller_profile_id, entity_type)
        else:
            await _audit(session, caller_profile_id, entity_type)
    except Exception:
        logger.error(
            "Denial audit write failed (caller=%s, entity_type=%s)",
            caller_profile_id, entity_type,
        )
        try:
            if session is not None:
                await session.rollback()
        except Exception:
            pass
