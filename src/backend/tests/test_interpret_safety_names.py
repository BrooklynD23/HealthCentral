"""WBC-CRITICAL-NAME: the critical-value table is keyed by the stored analyte name.

`NormalizeModule.normalize_analyte` turns "WBC" / "White Blood Cell Count" /
"Leukocytes" into `white_blood_cells`, and that is what `observations.analyte_canonical`
holds. `InterpretationSafetyGuard.DEFAULT_CRITICAL_THRESHOLDS` was keyed `wbc`, so a
critical white cell count (1.0 or 50.0) was never flagged for physician review.

Signed gate: owner-decisions-2026-09-27.md, WBC-CRITICAL-NAME ("Fix it, sweep names").
The gate licenses exactly one added key, `white_blood_cells`, in interpret_safety.py.

HC-WCN-001/002: real normalizer + real guard flag 1.0 and 50.0.
HC-WCN-003: non-critical and boundary values stay unflagged (green before and after).
HC-WCN-004: the table carries the stored name, `wbc` kept identical.
HC-WCN-005: every table key is a producible canonical name or is kept deliberately
(green before and after; it guards future drift).
HC-WCN-006/007: end to end through the real InterpretModule.interpret_observation.
HC-WCN-008: the second call site, interpret_with_model.
HC-WCN-009: the log line names the analyte only (CRIT-LOG-SCRUB class).

No mocks of NormalizeModule or the guard. Analyte names always come from the
normalizer, never hard-coded as the stored name.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import models  # noqa: F401  register every table on both bases
from core.database import Base
from core.profile_database import ProfileDatabaseBase
from models import Observation
from models.knowledge_base import BiomarkerKnowledge
from modules.interpret import InterpretModule
from modules.interpret_safety import InterpretationSafetyGuard
from modules.knowledge_loader import KnowledgeLoader
from modules.normalize import NormalizeModule

LOGGER_NAME = "modules.interpret_safety"
PROFILE_ID = "profile-wcn"
COLLECTED = datetime(2026, 3, 1, 9, 0, 0)
WBC_RAW_NAMES = ["WBC", "wbc", "White Blood Cell Count", "Leukocytes"]
EXPECTED_LIMITS = {"critical_low": 2.0, "critical_high": 30.0}

# Table keys that are NOT a name the normalizer produces, kept on purpose.
# `wbc`: the WBC-CRITICAL-NAME row requires this key to stay, and the normalizer
# never produces it (normalize_analyte("wbc") gives `white_blood_cells`). The only
# reason recorded for keeping it is that row requirement; no other is claimed.
KEPT_DELIBERATELY = {
    "wbc": "WBC-CRITICAL-NAME row: key stays; normalizer never produces it",
}


def _canonical(raw: str) -> str:
    return NormalizeModule().normalize_analyte(raw).canonical_name


def _is_producible(name: str) -> bool:
    """True when the normalizer maps something to `name`.

    `normalize_analyte` echoes an unknown name back as its own canonical name, so
    `_canonical(name) == name` alone would accept any typo; the name must also be
    one of the normalizer's known canonical names.
    """
    return name in NormalizeModule.ANALYTE_SYNONYMS and _canonical(name) == name


def _unexplained_keys(table: dict, kept: dict) -> list[str]:
    """Keys that are neither a producible canonical name nor listed in `kept`."""
    return [k for k in table if k not in kept and not _is_producible(k)]


# --- HC-WCN-001..004: the guard, fed real normalized names ------------------


@pytest.mark.parametrize("raw", WBC_RAW_NAMES)
def test_hc_wcn_001_critical_low_white_cells_flagged(raw):
    name = _canonical(raw)
    result = InterpretationSafetyGuard().check_critical_value(name, 1.0)
    assert result.requires_physician_review is True, f"{raw!r} -> {name!r} not flagged"
    assert result.warnings == ["critical_low_value"]


@pytest.mark.parametrize("raw", WBC_RAW_NAMES)
def test_hc_wcn_002_critical_high_white_cells_flagged(raw):
    name = _canonical(raw)
    result = InterpretationSafetyGuard().check_critical_value(name, 50.0)
    assert result.requires_physician_review is True, f"{raw!r} -> {name!r} not flagged"
    assert result.warnings == ["critical_high_value"]


@pytest.mark.parametrize("value", [7.0, 2.0, 30.0])
def test_hc_wcn_003_non_critical_and_boundary_values_not_flagged(value):
    """Green before and after the fix: 2.0 and 30.0 are inside (strict inequality)."""
    result = InterpretationSafetyGuard().check_critical_value(_canonical("WBC"), value)
    assert result.requires_physician_review is False
    assert result.warnings == []
    assert "value_not_critical" in result.checks_passed


def test_hc_wcn_004_table_has_stored_name_and_keeps_wbc():
    table = InterpretationSafetyGuard.DEFAULT_CRITICAL_THRESHOLDS
    assert table.get(_canonical("WBC")) == EXPECTED_LIMITS
    assert table.get("white_blood_cells") == EXPECTED_LIMITS
    assert table.get("wbc") == EXPECTED_LIMITS


def test_hc_wcn_005_every_key_is_canonical_or_kept_deliberately():
    """Green before and after. It fails if a key drifts from the normalizer's names."""
    table = InterpretationSafetyGuard.DEFAULT_CRITICAL_THRESHOLDS
    assert _unexplained_keys(table, KEPT_DELIBERATELY) == []
    for key in KEPT_DELIBERATELY:
        assert key in table, f"kept key {key!r} is no longer in the table"
        assert not _is_producible(key), f"{key!r} is producible now; drop it from KEPT_DELIBERATELY"


# --- HC-WCN-006/007: end to end through InterpretModule.interpret_observation


async def _engine_session(base):
    # Copied from tests/test_interpret_withhold_msg.py (not imported across modules).
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
    return AsyncSession(engine, expire_on_commit=False), engine


@pytest_asyncio.fixture
async def dbs():
    profile_db, p_engine = await _engine_session(ProfileDatabaseBase)
    master_db, m_engine = await _engine_session(Base)
    try:
        yield profile_db, master_db
    finally:
        await profile_db.close()
        await master_db.close()
        await p_engine.dispose()
        await m_engine.dispose()


async def _add_observation(profile_db, raw: str, value: float, unit: str) -> str:
    obs = Observation(
        id=str(uuid.uuid4()), profile_id=PROFILE_ID, doc_id=str(uuid.uuid4()),
        analyte_canonical=_canonical(raw), analyte_raw=raw, value=value,
        unit=unit, collected_at=COLLECTED,
    )
    profile_db.add(obs)
    await profile_db.commit()
    return obs.id


async def _add_seeded_wbc_knowledge(master_db):
    """The row as scripts/seed_knowledge_base.py ships it: keyed `wbc`, limits 2.0 / 30.0."""
    master_db.add(BiomarkerKnowledge(
        id=str(uuid.uuid4()), analyte_canonical="wbc",
        display_name="White Blood Cell Count (WBC)",
        description="White blood cells are part of your immune system.",
        clinical_significance="Helps detect infections and immune disorders.",
        normal_interpretation="Within the normal range.",
        high_interpretation="Elevated.", low_interpretation="Low.",
        ref_range_adult_json='{"default": {"normal": [4.5, 11.0]}, "unit": "10^3/uL"}',
        critical_low=2.0, critical_high=30.0,
        standard_unit="10^3/uL", category="cbc", sources_json="[]",
    ))
    await master_db.commit()


async def _interpret(profile_db, master_db, obs_id):
    # A fresh KnowledgeLoader: the module-level one caches per analyte across tests.
    return await InterpretModule(knowledge_loader=KnowledgeLoader()).interpret_observation(
        observation_id=obs_id, profile_db=profile_db, master_db=master_db
    )


async def _assert_end_to_end(profile_db, master_db, raw, value, unit, expect_review):
    obs_id = await _add_observation(profile_db, raw, value, unit)
    result = await _interpret(profile_db, master_db, obs_id)
    # No assertion on generated wording: NO-RANGE-WORDING (#482) is changing it.
    assert result.success is True
    assert result.withheld is False
    assert result.safety_validation.requires_physician_review is expect_review
    assert result.interpretation.requires_physician_review is expect_review


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [1.0, 50.0])
async def test_hc_wcn_006_end_to_end_critical_white_cells_need_physician_review(dbs, value):
    profile_db, master_db = dbs
    await _assert_end_to_end(profile_db, master_db, "WBC", value, "10^3/uL", True)


@pytest.mark.asyncio
async def test_hc_wcn_006_controls_normal_wbc_unflagged_critical_hemoglobin_flagged(dbs):
    profile_db, master_db = dbs
    await _assert_end_to_end(profile_db, master_db, "WBC", 7.0, "10^3/uL", False)
    await _assert_end_to_end(profile_db, master_db, "Hemoglobin", 5.0, "g/dL", True)


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [1.0, 50.0])
async def test_hc_wcn_007_seeded_wbc_knowledge_row_does_not_hide_the_default(dbs, value):
    """Shipped state: the KB row is keyed `wbc`, the stored name is `white_blood_cells`,
    so the KB lookup misses and the default table has to catch the value."""
    profile_db, master_db = dbs
    await _add_seeded_wbc_knowledge(master_db)
    await _assert_end_to_end(profile_db, master_db, "WBC", value, "10^3/uL", True)


# --- HC-WCN-008: the second call site, interpret_with_model ----------------


@pytest.mark.asyncio
async def test_hc_wcn_008_interpret_with_model_flags_critical_white_cells(dbs):
    profile_db, master_db = dbs
    obs_id = await _add_observation(profile_db, "WBC", 1.0, "10^3/uL")
    selector = MagicMock()
    selector.get_model_for_inference = AsyncMock(return_value=(object(), "standard"))
    selector.run_inference = AsyncMock(return_value={"choices": [{"text": (
        "Your White Blood Cells result is listed [KB:white_blood_cells]. "
        "This is educational information only. Please consult your healthcare provider."
    )}]})
    result = await InterpretModule(
        knowledge_loader=KnowledgeLoader(), model_selector=selector
    ).interpret_with_model(
        observation_id=obs_id, profile_id=PROFILE_ID,
        profile_db=profile_db, master_db=master_db,
    )
    selector.run_inference.assert_awaited()
    assert result.safety_validation is not None
    assert result.safety_validation.requires_physician_review is True


# --- HC-WCN-009: security lens, the log names the analyte, not the numbers -


@pytest.mark.parametrize(
    "value, direction", [(1.37, "below critical threshold"), (57.31, "above critical threshold")]
)
def test_hc_wcn_009_critical_white_cell_log_carries_no_value_or_threshold(
    caplog, value, direction
):
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    InterpretationSafetyGuard().check_critical_value(_canonical("WBC"), value)

    hits = [
        r for r in caplog.records
        if r.name == LOGGER_NAME
        and r.levelno == logging.WARNING
        and "white_blood_cells" in r.getMessage()
        and direction in r.getMessage()
    ]
    assert len(hits) == 1, "no critical-value WARNING names white_blood_cells"
    for r in caplog.records:
        text, args = r.getMessage(), str(r.args)
        for needle in (str(value), "2.0", "30.0"):
            assert needle not in text, f"{needle} leaked into log message: {text!r}"
            assert needle not in args, f"{needle} leaked into log args: {args!r}"
