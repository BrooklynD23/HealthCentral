"""Opt-in data donation consent routes (RSI1-DONATE PR-1).

Session-scoped: the profile comes from the session and the profile vault, never
from the path. Revoke deletes the purpose's donated rows in the same vault
transaction as the consent change (DON-REVOKE a). Audit follows the vault
commit for grant (AUDIT-ORDER C). Revoke deletes irreversibly, so it uses the
A2 started/completed pair (AO-DESIGN D). Audit carries counts and the purpose
only (AUDIT-PHI-001).
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import audit_and_commit, audit_intent, create_audit_log
from core.auth import ProfileDbSession, RequireAuth
from core.database import get_db
from core.time import utcnow
from models.data_donation import DonationConsent
from modules.data_donation import (
    CURRENT_CONSENT_TEXT_VERSION,
    collect,
    delete_derived,
    get_active_consent,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class DonationPurpose(str, Enum):
    FINE_TUNE = "fine_tune"
    SYNTHETIC_SEED = "synthetic_seed"
    AGENT_TRACES = "agent_traces"


class ConsentState(BaseModel):
    purpose: DonationPurpose
    granted: bool
    # True only when the active row was agreed on the current wording.
    current: bool = False
    consent_text_version: Optional[str] = None
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class ConsentList(BaseModel):
    consents: list[ConsentState]


class ConsentUpdate(BaseModel):
    granted: bool
    consent_text_version: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.\-]+$")


class ConsentUpdateResult(BaseModel):
    purpose: DonationPurpose
    granted: bool
    consent_text_version: str
    deleted_count: int = 0


def _state(purpose: DonationPurpose, row: Optional[DonationConsent]) -> ConsentState:
    # granted = active row, whatever its version; current = that row is on the
    # current wording. PR-2 collect must itself refuse rows that are not current.
    if row is None:
        return ConsentState(purpose=purpose, granted=False)
    return ConsentState(
        purpose=purpose,
        granted=row.revoked_at is None,
        current=row.consent_text_version == CURRENT_CONSENT_TEXT_VERSION,
        consent_text_version=row.consent_text_version,
        granted_at=row.granted_at,
        revoked_at=row.revoked_at,
    )


async def _get_active(
    profile_db: ProfileDbSession, profile_id: str, purpose: DonationPurpose
) -> Optional[DonationConsent]:
    return await get_active_consent(profile_db, profile_id, purpose.value)


@router.get("/consents", response_model=ConsentList)
async def list_consents(
    session: RequireAuth,
    profile_db: ProfileDbSession,
    master_db: AsyncSession = Depends(get_db),
):
    """Every purpose with its granted state and consent text version."""
    result = await profile_db.execute(
        select(DonationConsent).where(DonationConsent.profile_id == session.profile_id)
    )
    by_purpose: dict[str, DonationConsent] = {}
    for r in result.scalars().all():
        # Active row wins; otherwise the most recent record of the choice.
        key = (r.revoked_at is None, r.granted_at)
        cur = by_purpose.get(r.purpose)
        if cur is None or key > (cur.revoked_at is None, cur.granted_at):
            by_purpose[r.purpose] = r
    await audit_and_commit(
        master_db,
        create_audit_log,
        event_type="donation.consent.view",
        action="donation.consent.view",
        profile_id=session.profile_id,
        entity_type="donation",
        entity_id="consents",
    )
    return ConsentList(consents=[_state(p, by_purpose.get(p.value)) for p in DonationPurpose])


@router.put("/consents/{purpose}", response_model=ConsentUpdateResult)
async def set_consent(
    purpose: DonationPurpose,
    data: ConsentUpdate,
    session: RequireAuth,
    profile_db: ProfileDbSession,
    master_db: AsyncSession = Depends(get_db),
):
    """Grant or revoke one purpose. Revoke deletes the derived donated rows."""
    profile_id = session.profile_id
    # A grant must name the copy the patient was shown. Revoke is never gated
    # on version: a stale client must always be able to stop and delete.
    if data.granted and data.consent_text_version != CURRENT_CONSENT_TEXT_VERSION:
        raise HTTPException(
            status_code=422,
            detail="Consent text is out of date. Reload and review the current text.",
        )
    row = await _get_active(profile_db, profile_id, purpose)
    deleted = 0
    if data.granted:
        # Same version already active: nothing to change. A new version closes
        # the old record and opens a new one, so earlier choices stay dated.
        changed = row is None or row.consent_text_version != CURRENT_CONSENT_TEXT_VERSION
        if changed:
            if row is not None:
                row.revoked_at = utcnow()
                await profile_db.flush()
            profile_db.add(DonationConsent(
                profile_id=profile_id,
                purpose=purpose.value,
                granted_at=utcnow(),
                consent_text_version=CURRENT_CONSENT_TEXT_VERSION,
            ))
        try:
            await profile_db.commit()
        except IntegrityError:
            # Another window opened the active row first (partial unique index).
            await profile_db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Consent changed in another window. Reload to see the current choice.",
            )
        if changed:
            await audit_and_commit(
                master_db,
                create_audit_log,
                event_type="donation.consent.grant",
                action="donation.consent.grant",
                profile_id=profile_id,
                entity_type="donation",
                entity_id=purpose.value,
            )
        version = CURRENT_CONSENT_TEXT_VERSION
    else:
        audit_kwargs = dict(
            event_type="donation.consent.revoke",
            action="donation.consent.revoke",
            profile_id=profile_id,
            entity_type="donation",
            entity_id=purpose.value,
        )
        # A2: the intent row commits before the irreversible delete; a failed
        # audit write stops the revoke with the donated rows intact.
        await audit_intent(master_db, "started", create_audit_log, **audit_kwargs)
        deleted = await delete_derived(profile_db, profile_id, purpose.value)
        if row is not None:
            row.revoked_at = utcnow()
        await profile_db.commit()
        await audit_intent(
            master_db, "completed", create_audit_log, details={"count": deleted}, **audit_kwargs
        )
        version = row.consent_text_version if row is not None else CURRENT_CONSENT_TEXT_VERSION
    return ConsentUpdateResult(
        purpose=purpose,
        granted=data.granted,
        consent_text_version=version,
        deleted_count=deleted,
    )


class CollectRequest(BaseModel):
    confirmed: bool = False


class CollectResult(BaseModel):
    purpose: DonationPurpose
    collected: int
    skipped_existing: int
    skipped_incomplete: int
    dropped: dict[str, int]  # Safe Harbor category -> records dropped
    dropped_total: int
    strict_redaction_count: int


@router.post("/{purpose}/collect", response_model=CollectResult)
async def collect_donation(
    purpose: DonationPurpose,
    data: CollectRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession,
    master_db: AsyncSession = Depends(get_db),
):
    """Copy the profile's rated feedback into the purpose's donated set. Counts only."""
    if not data.confirmed:
        raise HTTPException(status_code=400, detail="Collect requires confirmed=true in the request body.")
    audit_kwargs = dict(
        event_type="donation.collect",
        action="donation.collect",
        profile_id=session.profile_id,
        entity_type="donation",
        entity_id=purpose.value,
    )
    # A2: intent commits first; a failed audit write stops the collect.
    await audit_intent(master_db, "started", create_audit_log, **audit_kwargs)
    counts = await collect(profile_db, session.profile_id, purpose.value)
    await audit_intent(
        master_db, "completed", create_audit_log,
        details={
            "count": counts.collected,
            "dropped_count": counts.dropped_records,
            "skipped_count": counts.skipped_existing,
            "redaction_count": counts.strict_redaction_count,
        },
        **audit_kwargs,
    )
    return CollectResult(
        purpose=purpose,
        collected=counts.collected,
        skipped_existing=counts.skipped_existing,
        skipped_incomplete=counts.skipped_incomplete,
        dropped=counts.dropped,
        dropped_total=counts.dropped_records,
        strict_redaction_count=counts.strict_redaction_count,
    )
