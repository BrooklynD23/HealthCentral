"""CRIT-DEFAULT-KB-LIMITS (HC-CKB-001..008): potassium and sodium get knowledge-base rows.

Owner answer KB-CONTENT-YES-2 ("Add K + Na KB rows (Recommended)",
docs/capstone-report/owner-decisions-2026-09-27.md). Plan: docs/plans/2026-11-08-batch-1107e-plan.md.

The limits are the ones already in InterpretationSafetyGuard.DEFAULT_CRITICAL_THRESHOLDS
(potassium 2.5/6.5 mmol/L, sodium 120/160 mmol/L), so the badge gains the critical label the
banner already asserts and no alarm boundary moves.

Would not notice: whether 2.5 / 6.5 / 120 / 160 are clinically right (the owner reviews them at
the gate; these tests pin the seeded values verbatim); other analytes (unchanged by construction).
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from models.knowledge_base import BiomarkerKnowledge
from modules.interpret_safety import InterpretationSafetyGuard
from modules.knowledge_loader import KnowledgeLoader
from scripts import seed_knowledge_base as skb
from tests import test_kb_canonical_names as _kcn

# fixtures + helpers reused as-is (assigned, not imported by name, so the fixture arguments below
# are not flagged as redefinitions)
data_root, master, profile_db = _kcn.data_root, _kcn.master, _kcn.profile_db
_interpret_stored, _module = _kcn._interpret_stored, _kcn._module

TEXT_FIELDS = (
    "description", "clinical_significance", "normal_interpretation",
    "high_interpretation", "low_interpretation",
)
# (critical_low, critical_high, [normal low, normal high], loinc codes)
EXPECTED = {
    "potassium": (2.5, 6.5, [3.5, 5.0], ["2823-3", "6298-4"]),
    "sodium": (120.0, 160.0, [135.0, 145.0], ["2951-2", "2947-0"]),
}


def _kb(analyte: str) -> dict:
    return next(d for d in skb.BIOMARKER_DATA if d["analyte_canonical"] == analyte)


@pytest.mark.asyncio
@pytest.mark.parametrize("analyte", ["potassium", "sodium"])
async def test_hc_ckb_001_seeded_rows_carry_the_exact_fields(master, analyte):
    info = await KnowledgeLoader().get_biomarker_knowledge(analyte, master)
    assert info is not None, f"no knowledge-base row for {analyte}"
    low, high, normal, loinc = EXPECTED[analyte]
    assert (info.critical_low, info.critical_high) == (low, high)
    assert info.standard_unit == "mmol/L"
    for field in TEXT_FIELDS:
        assert (getattr(info, field) or "").strip(), field
    row = _kb(analyte)
    assert row["category"] == "cmp"
    assert json.loads(row["panels_json"]) == ["cmp", "bmp"]
    assert json.loads(row["loinc_codes_json"]) == loinc
    assert json.loads(row["unit_conversions_json"]) == {"mEq/L": 1.0}
    ref = json.loads(row["ref_range_adult_json"])
    assert ref["unit"] == "mmol/L"
    assert ref["default"]["normal"] == normal
    # the seeded limits equal the guard's default table, so badge and banner coincide
    defaults = InterpretationSafetyGuard.DEFAULT_CRITICAL_THRESHOLDS[analyte]
    assert (low, high) == (defaults["critical_low"], defaults["critical_high"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "analyte,value,lo,hi,flag,severity,banner",
    [
        ("potassium", 7.0, 3.5, 5.0, "H", "critical_high",
         "Critical high value: 7 mmol/L is above the critical threshold of 6.5 mmol/L."),
        ("potassium", 2.0, 3.5, 5.0, "L", "critical_low",
         "Critical low value: 2 mmol/L is below the critical threshold of 2.5 mmol/L."),
        ("sodium", 118.0, 135.0, 145.0, "L", "critical_low",
         "Critical low value: 118 mmol/L is below the critical threshold of 120 mmol/L."),
        ("sodium", 165.0, 135.0, 145.0, "H", "critical_high",
         "Critical high value: 165 mmol/L is above the critical threshold of 160 mmol/L."),
    ],
)
async def test_hc_ckb_002_critical_mmol_value_gets_the_critical_badge_and_banner(
    master, profile_db, analyte, value, lo, hi, flag, severity, banner
):
    info, card = await _interpret_stored(master, profile_db, analyte, value, lo, hi, "mmol/L", flag)
    assert info is not None
    assert card.severity_level == severity
    assert card.requires_physician_review is True
    assert card.physician_review_reason == banner
    assert f"[KB:{info.id}]" in card.interpretation_text
    # HC-KCN-012 invariant: critical badge <=> review flag
    assert card.severity_level.startswith("critical") == bool(card.requires_physician_review)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "analyte,value,lo,hi,flag,severity,banner",
    [
        ("potassium", 7.0, 3.5, 5.0, "H", "critical_high",
         "Critical high value: 7 mEq/L is above the critical threshold of 6.5 mEq/L."),
        ("sodium", 165.0, 135.0, 145.0, "H", "critical_high",
         "Critical high value: 165 mEq/L is above the critical threshold of 160 mEq/L."),
    ],
)
async def test_hc_ckb_003_critical_meq_value_gets_the_critical_badge_and_banner(
    master, profile_db, analyte, value, lo, hi, flag, severity, banner
):
    info, card = await _interpret_stored(master, profile_db, analyte, value, lo, hi, "mEq/L", flag)
    assert info is not None
    assert card.severity_level == severity
    assert card.requires_physician_review is True
    assert card.physician_review_reason == banner
    assert card.severity_level.startswith("critical") == bool(card.requires_physician_review)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value,unit,flag,severity,banner",
    [
        (4.2, "mmol/L", None, "normal", False),
        (6.0, "mmol/L", "H", "borderline_high", False),  # above range, below critical
        (7.0, "mg/dL", "H", None, False),               # unconvertible unit: no critical badge
        (7.0, None, "H", None, False),                  # no unit: no banner
    ],
)
async def test_hc_ckb_004_controls_no_critical_where_none_is_earned(
    master, profile_db, value, unit, flag, severity, banner
):
    _, card = await _interpret_stored(master, profile_db, "potassium", value, 3.5, 5.0, unit, flag)
    assert not card.severity_level.startswith("critical")
    assert not card.requires_physician_review
    assert not card.physician_review_reason
    if severity is not None:
        assert card.severity_level == severity


async def _reseed(master) -> None:
    engine = create_async_engine(master.get_bind().url)
    try:
        maker = lambda: AsyncSession(engine, expire_on_commit=False)  # noqa: E731
        with patch.object(skb, "async_session_maker", maker):
            await skb.seed_all(skip_db_init=True)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_hc_ckb_005_a_card_saved_before_the_row_existed_is_rebuilt_on_read(master, profile_db):
    await master.execute(delete(BiomarkerKnowledge).where(BiomarkerKnowledge.analyte_canonical == "potassium"))
    await master.commit()
    info, card = await _interpret_stored(master, profile_db, "potassium", 7.0, 3.5, 5.0, "mmol/L", "H")
    assert info is None
    assert card.severity_level == "abnormal_high"          # the old, badge-disagrees card
    assert card.requires_physician_review is True           # the default-table banner
    assert "[KB:" not in card.interpretation_text
    saved_id = card.id

    await _reseed(master)  # the row now exists, as after an app update
    result = await _module()[0].interpret_observation(card.observation_id, profile_db, master)
    assert result.success
    assert result.interpretation.id != saved_id
    assert result.interpretation.severity_level == "critical_high"
    assert result.interpretation.requires_physician_review is True
    assert "[KB:" in result.interpretation.interpretation_text


@pytest.mark.asyncio
async def test_hc_ckb_006_a_same_unit_kb_card_with_a_marker_is_not_rebuilt(master, profile_db):
    """Owner decision (c) of KB-UNIT-BADGE still holds: same unit + KB marker = a KB revision."""
    _, card = await _interpret_stored(master, profile_db, "potassium", 7.0, 3.5, 5.0, "mmol/L", "H")
    assert card.severity_level == "critical_high" and "[KB:" in card.interpretation_text
    card.severity_level = "normal"
    await profile_db.commit()
    result = await _module()[0].interpret_observation(card.observation_id, profile_db, master)
    assert result.interpretation.id == card.id
    assert result.interpretation.severity_level == "normal"


@pytest.mark.asyncio
async def test_hc_ckb_007_a_pre_row_card_for_an_in_range_value_is_untouched(master, profile_db):
    await master.execute(delete(BiomarkerKnowledge).where(BiomarkerKnowledge.analyte_canonical == "potassium"))
    await master.commit()
    _, card = await _interpret_stored(master, profile_db, "potassium", 4.2, 3.5, 5.0, "mmol/L", None)
    assert not card.severity_level.startswith("critical")
    saved_id = card.id
    await _reseed(master)
    module, _ = _module()
    with patch.object(module, "_generate_interpretation", wraps=module._generate_interpretation) as gen:
        result = await module.interpret_observation(card.observation_id, profile_db, master)
    assert result.interpretation.id == saved_id
    gen.assert_not_called()


@pytest.mark.parametrize("analyte", ["potassium", "sodium"])
def test_hc_ckb_008_seeded_text_holds_no_prohibited_pattern(analyte):
    guard = InterpretationSafetyGuard()
    row = _kb(analyte)
    texts = [row["display_name"], *(row[f] for f in TEXT_FIELDS)]
    for field in ("common_causes_high_json", "common_causes_low_json"):
        texts.append("; ".join(json.loads(row[field])))
    for text in texts:
        result = guard.validate_interpretation(text, require_citations=False)
        failed = [c for c in result.checks_failed if c.startswith("prohibited")]
        assert not failed, (analyte, failed, text)
