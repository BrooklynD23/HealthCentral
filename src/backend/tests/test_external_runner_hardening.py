"""HC-EXT-001…004 — D12 (owner, 2026-09-27): external runner hardening.

"make strict redaction unconditional (remove the dev bypass; keep break-glass
only with audit + UI warning)". See
docs/plans/2026-09-27-W06-external-runner-hardening.md.

No test here touches the network: the provider call is always patched.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.external_runner import ExternalModelRunner
from core.model_runner import InferenceResult

PROFILE = "profile-a"
API_KEY = "test-key-do-not-log"

# Tokens covering every strict rule class that matters here. DOB and MRN are
# strict-ONLY (modules/redaction.py), so they prove the level is strict, not
# merely "some redaction ran".
PHI_PROMPT = (
    "Patient: John Doe DOB: 01/15/1990 MRN: 8834412 SSN 123-45-6789 "
    "takes metformin 500 mg, HbA1c 7.2"
)
REDACTABLE_TOKENS = ("John Doe", "01/15/1990", "8834412", "123-45-6789")


def _runner() -> ExternalModelRunner:
    return ExternalModelRunner(provider="openai", api_key=API_KEY, profile_id=PROFILE)


def _set(mock_settings, *, env: str, enabled: bool, level: str, break_glass: bool) -> None:
    mock_settings.app_env = env
    mock_settings.redaction_enabled = enabled
    mock_settings.redaction_policy_level = level
    mock_settings.external_api_redaction_break_glass = break_glass


def _capturing(sent: list[str], order: list[str] | None = None):
    async def _fake_call(prompt, config):
        if order is not None:
            order.append("dispatch")
        sent.append(prompt)
        return InferenceResult(text="ok", tokens_generated=1, finish_reason="stop", model_name="m")
    return _fake_call


# ---------------------------------------------------------------------------
# HC-EXT-001 — no dev bypass: without break-glass, the prompt is always
# strictly redacted, whatever REDACTION_ENABLED / REDACTION_POLICY_LEVEL say.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "enabled,level",
    [(False, "strict"), (False, "standard"), (True, "standard"), (True, "minimal")],
)
async def test_hc_ext_001_dev_without_break_glass_always_redacts_strictly(enabled, level):
    runner = _runner()
    sent: list[str] = []
    with patch.object(runner, "_call_openai", side_effect=_capturing(sent)), \
         patch("core.external_runner.settings") as s:
        _set(s, env="development", enabled=enabled, level=level, break_glass=False)
        result = await runner.generate_async(PHI_PROMPT)

    assert result.finish_reason == "stop"
    assert len(sent) == 1, "provider was not called exactly once"
    for token in REDACTABLE_TOKENS:
        assert token not in sent[0], f"{token!r} left the device (enabled={enabled}, level={level})"



# ---------------------------------------------------------------------------
# HC-EXT-002 — break-glass writes one audit row, with no PHI, BEFORE dispatch.
# ---------------------------------------------------------------------------

class _RecordingMasterDb:
    """Stands in for a master-DB session; records what would be written."""

    def __init__(self, order: list[str]) -> None:
        self.added: list[object] = []
        self.commits = 0
        self._order = order

    def add(self, obj: object) -> None:
        self._order.append("audit_add")
        self.added.append(obj)

    async def commit(self) -> None:
        self._order.append("audit_commit")
        self.commits += 1

    async def rollback(self) -> None:  # pragma: no cover
        pass

    def audit_rows(self) -> list[object]:
        return [o for o in self.added if type(o).__name__ == "AuditLog"]


def _maker_for(db):
    @asynccontextmanager
    async def _session():
        yield db
    return lambda: _session()


_AUDIT_COLUMNS = (
    "profile_id", "event_type", "action", "entity_type", "entity_id",
    "details_json", "client_info",
)
_MUST_NOT_APPEAR = REDACTABLE_TOKENS + ("John", "Doe", "metformin", "HbA1c", "7.2", API_KEY, "openai")


@pytest.mark.asyncio
@pytest.mark.parametrize("env", ["development", "production"])
@pytest.mark.parametrize(
    "enabled,level,decision",
    [(False, "strict", "unredacted"), (True, "standard", "non_strict")],
)
async def test_hc_ext_002_break_glass_writes_phi_free_audit_row_before_dispatch(env, enabled, level, decision):
    from core.audit import ALLOWED_DETAIL_KEYS

    order: list[str] = []
    sent: list[str] = []
    master = _RecordingMasterDb(order)
    runner = _runner()
    with patch.object(runner, "_call_openai", side_effect=_capturing(sent, order)), \
         patch("core.external_runner.settings") as s, \
         patch("core.database.async_session_maker", _maker_for(master)):
        _set(s, env=env, enabled=enabled, level=level, break_glass=True)
        result = await runner.generate_async(PHI_PROMPT)

    assert result.finish_reason == "stop"
    rows = master.audit_rows()
    assert len(rows) == 1, f"expected one break-glass audit row, got {len(rows)}"
    assert master.commits == 1, "audit row was added but never committed"
    assert order == ["audit_add", "audit_commit", "dispatch"], f"audit row must be committed before dispatch, got {order}"

    row = rows[0]
    assert row.event_type == "security.external_api.break_glass"
    assert row.profile_id == PROFILE
    details = json.loads(row.details_json)
    assert details["trigger"] == "break_glass"
    assert details["decision"] == decision
    assert "_scrubbed" not in details, f"a non-allowlisted key was passed: {details}"
    assert set(details) <= ALLOWED_DETAIL_KEYS

    dump = json.dumps({c: getattr(row, c) for c in _AUDIT_COLUMNS}, default=str)
    for token in _MUST_NOT_APPEAR:
        assert token not in dump, f"{token!r} reached the unencrypted master DB audit row"


# HC-EXT-002b — no audit row, no break-glass: fail closed.
@pytest.mark.asyncio
async def test_hc_ext_002b_break_glass_is_refused_when_audit_cannot_be_written():
    sent: list[str] = []
    runner = _runner()
    with patch.object(runner, "_call_openai", side_effect=_capturing(sent)), \
         patch("core.external_runner.settings") as s, \
         patch("core.external_runner._record_break_glass_audit",
               AsyncMock(side_effect=RuntimeError("master db unavailable"))):
        _set(s, env="production", enabled=False, level="strict", break_glass=True)
        result = await runner.generate_async(PHI_PROMPT)

    assert sent == [], "an unaudited break-glass prompt left the device"
    assert result.finish_reason == "error"
    assert "audit" in result.text.lower()


# HC-EXT-002c — no row when nothing is bypassed (keeps the audit trail meaningful).
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "break_glass,enabled,level",
    [(False, False, "standard"), (True, True, "strict")],
)
async def test_hc_ext_002c_no_break_glass_row_when_redaction_is_strict(break_glass, enabled, level):
    sink = AsyncMock()
    sent: list[str] = []
    runner = _runner()
    with patch.object(runner, "_call_openai", side_effect=_capturing(sent)), \
         patch("core.external_runner.settings") as s, \
         patch("core.external_runner._record_break_glass_audit", sink, create=True):
        _set(s, env="development", enabled=enabled, level=level, break_glass=break_glass)
        await runner.generate_async(PHI_PROMPT)

    sink.assert_not_awaited()
    assert len(sent) == 1 and "123-45-6789" not in sent[0]


# HC-EXT-002d — the row persists in a real master schema (column lengths, FK).
@pytest.mark.asyncio
async def test_hc_ext_002d_break_glass_row_persists_in_real_master_schema(tmp_path):
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    import models  # noqa: F401  (registers master tables on Base.metadata)
    from core.database import Base
    from core.time import utcnow
    from models.audit import AuditLog
    from models.profile import Profile

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'master.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as db:
        now = utcnow()
        db.add(Profile(id=PROFILE, display_name="T", encryption_key_id="k",
                       created_at=now, updated_at=now))
        await db.commit()

    sent: list[str] = []
    runner = _runner()
    try:
        with patch.object(runner, "_call_openai", side_effect=_capturing(sent)), \
             patch("core.external_runner.settings") as s, \
             patch("core.database.async_session_maker", maker):
            _set(s, env="production", enabled=False, level="strict", break_glass=True)
            result = await runner.generate_async(PHI_PROMPT)
        async with maker() as db:
            rows = (await db.execute(select(AuditLog))).scalars().all()
    finally:
        await engine.dispose()

    assert result.finish_reason == "stop"
    assert [r.event_type for r in rows] == ["security.external_api.break_glass"]
    assert rows[0].profile_id == PROFILE
