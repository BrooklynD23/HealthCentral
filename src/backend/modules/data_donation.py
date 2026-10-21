"""Opt-in data donation logic (RSI1-DONATE PR-2): collect, delete helpers.

collect() fails closed without an active, current consent and reads no source
rows in that case. Each text field goes through strict redaction (reusing
rl_dataset._redact), then the independent second pass; any hit drops the whole
record, counted by Safe Harbor category and never by value. Results are counts
only. Local-first: no network imports here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import delete, or_, select

from models.chat_session import ChatTurn
from models.data_donation import DonatedRecord, DonationConsent
from models.response_feedback import ResponseFeedback
from modules.phi_second_pass import detect
from modules.redaction import RedactionEngine
from modules.rl_dataset import _redact

# The consent copy version the patient is shown. Must equal CONSENT_TEXT_VERSION
# in src/frontend/src/components/settings/DataDonationCard.tsx (HC-DON-005e).
# Re-exported by api.donation.
CURRENT_CONSENT_TEXT_VERSION = "2026-10-20-v2"

SOURCE_KIND = "response_feedback"


@dataclass(frozen=True)
class CollectCounts:
    """What collect() returns. Counts only: no text, no ids."""

    collected: int = 0
    skipped_existing: int = 0
    skipped_incomplete: int = 0  # rows with no prompt or no response
    dropped_records: int = 0  # records dropped (a record hitting N categories counts once)
    dropped: dict[str, int] = field(default_factory=dict)  # Safe Harbor category -> records
    strict_redaction_count: int = 0

    @property
    def dropped_total(self) -> int:
        return self.dropped_records


async def get_active_consent(
    profile_db, profile_id: str, purpose: str
) -> Optional[DonationConsent]:
    result = await profile_db.execute(
        select(DonationConsent).where(
            DonationConsent.profile_id == profile_id,
            DonationConsent.purpose == purpose,
            DonationConsent.revoked_at.is_(None),
        )
    )
    return result.scalars().first()


async def has_current_consent(profile_db, profile_id: str, purpose: str) -> bool:
    """True only for an active consent agreed on the current wording (DON-STALE)."""
    row = await get_active_consent(profile_db, profile_id, purpose)
    return row is not None and row.consent_text_version == CURRENT_CONSENT_TEXT_VERSION


async def delete_derived(profile_db, profile_id: str, purpose: str) -> int:
    """Delete the purpose's real rows, synthetic children and synthetic rows of the purpose."""
    real_ids = select(DonatedRecord.id).where(
        DonatedRecord.profile_id == profile_id,
        DonatedRecord.purpose == purpose,
        DonatedRecord.origin == "real",
    )
    children = await profile_db.execute(
        delete(DonatedRecord).where(
            DonatedRecord.profile_id == profile_id,
            DonatedRecord.origin == "synthetic",
            DonatedRecord.parent_id.in_(real_ids),
        )
    )
    # Also covers synthetic rows of this purpose whose parent is NULL or dangling.
    rest = await profile_db.execute(
        delete(DonatedRecord).where(
            DonatedRecord.profile_id == profile_id,
            DonatedRecord.purpose == purpose,
            DonatedRecord.origin.in_(("real", "synthetic")),
        )
    )
    return (children.rowcount or 0) + (rest.rowcount or 0)


async def delete_for_session(profile_db, session_id: str) -> int:
    """DON-SRC-DELETE: delete donated copies of one chat session's feedback rows.

    Removes origin="real" rows whose source_id is a ResponseFeedback id of the
    session, plus their synthetic children. Call before the session is deleted
    (feedback rows may cascade). Does not commit: the caller's commit makes it
    atomic with the session delete.
    """
    # client-supplied feedback.session_id is not trusted alone: also key on the
    # session's own turns.
    session_turns = select(ChatTurn.id).where(ChatTurn.session_id == session_id)
    feedback_ids = select(ResponseFeedback.id).where(
        or_(ResponseFeedback.session_id == session_id, ResponseFeedback.turn_id.in_(session_turns))
    )
    real_ids = select(DonatedRecord.id).where(
        DonatedRecord.origin == "real",
        DonatedRecord.source_kind == SOURCE_KIND,
        DonatedRecord.source_id.in_(feedback_ids),
    )
    children = await profile_db.execute(
        delete(DonatedRecord).where(
            DonatedRecord.origin == "synthetic", DonatedRecord.parent_id.in_(real_ids)
        )
    )
    real = await profile_db.execute(
        delete(DonatedRecord).where(
            DonatedRecord.origin == "real",
            DonatedRecord.source_kind == SOURCE_KIND,
            DonatedRecord.source_id.in_(feedback_ids),
        )
    )
    return (children.rowcount or 0) + (real.rowcount or 0)


def _screen(engine: RedactionEngine, fields: dict[str, Optional[str]]):
    """Redact each field, then second-pass the result.

    Returns (redacted fields, strict redaction count, set of hit categories).
    """
    out: dict[str, Optional[str]] = {}
    count = 0
    categories: set[str] = set()
    for name, text in fields.items():
        if text is None:
            out[name] = None
            continue
        redacted, n = _redact(engine, text)
        count += n
        categories.update(h.category for h in detect(redacted))
        out[name] = redacted
    return out, count, categories


async def _user_turn_text(profile_db, profile_id: str, assistant_turn_id: str) -> Optional[str]:
    """Text of the user turn that immediately precedes the given assistant turn."""
    a = (await profile_db.execute(
        select(ChatTurn).where(ChatTurn.id == assistant_turn_id, ChatTurn.profile_id == profile_id)
    )).scalars().first()
    if a is None:
        return None
    return (await profile_db.execute(
        select(ChatTurn.content).where(
            ChatTurn.session_id == a.session_id, ChatTurn.profile_id == profile_id,
            ChatTurn.role == "user", ChatTurn.turn_index < a.turn_index,
        ).order_by(ChatTurn.turn_index.desc()).limit(1)
    )).scalars().first()


async def collect(profile_db, profile_id: str, purpose: str) -> CollectCounts:
    """Donate the profile's rated feedback rows for ``purpose``. Counts only."""
    # Fail closed: no active, current consent -> nothing is read (DON-STALE).
    if not await has_current_consent(profile_db, profile_id, purpose):
        return CollectCounts()

    already = set((await profile_db.execute(
        select(DonatedRecord.source_id).where(
            DonatedRecord.profile_id == profile_id,
            DonatedRecord.purpose == purpose,
            DonatedRecord.origin == "real",
            DonatedRecord.source_kind == SOURCE_KIND,
        )
    )).scalars().all())
    rows = (await profile_db.execute(
        select(ResponseFeedback)
        .where(
            ResponseFeedback.profile_id == profile_id,
            # DON-SRC-DELETE: feedback of a deleted session survives (no FK), so
            # only rows whose assistant turn still exists are donatable.
            ResponseFeedback.turn_id.in_(
                select(ChatTurn.id).where(
                    ChatTurn.profile_id == profile_id, ChatTurn.role == "assistant"
                )
            ),
        )
        .order_by(ResponseFeedback.created_at)
    )).scalars().all()

    engine = RedactionEngine(policy_level="strict")
    collected = skipped = incomplete = dropped_records = strict_total = 0
    dropped: dict[str, int] = {}
    for row in rows:
        if row.id in already:
            skipped += 1
            continue
        # The question is the user's own turn, not the client-supplied prompt_snapshot
        # (which can carry retrieved record text).
        question = await _user_turn_text(profile_db, profile_id, row.turn_id)
        if not question or not row.response_text:
            incomplete += 1
            continue
        text, n, categories = _screen(engine, {
            "prompt": question,
            "response": row.response_text,
            "correction": row.correction_text or None,
        })
        if categories:
            dropped_records += 1
            for category in categories:
                dropped[category] = dropped.get(category, 0) + 1
            continue
        profile_db.add(DonatedRecord(
            profile_id=profile_id,
            purpose=purpose,
            origin="real",
            source_kind=SOURCE_KIND,
            source_id=row.id,
            prompt_redacted=text["prompt"],
            response_redacted=text["response"],
            correction_redacted=text["correction"],
            strict_redaction_count=n,
        ))
        collected += 1
        strict_total += n
    await profile_db.commit()
    return CollectCounts(
        collected=collected,
        skipped_existing=skipped,
        skipped_incomplete=incomplete,
        dropped_records=dropped_records,
        dropped=dropped,
        strict_redaction_count=strict_total,
    )
