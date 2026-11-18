"""CRIT-DEFAULT-TABLE-UNITS: the default critical table is checked in each row's own unit.

Without a KB row, `InterpretModule._apply_critical_check` used to compare the raw value with
`InterpretationSafetyGuard.DEFAULT_CRITICAL_THRESHOLDS`, whatever unit the patient's lab used.
Now each default row names its unit (`DEFAULT_CRITICAL_UNITS`) and the value goes through the
same rule as the badge (`value_in_kb_unit`). Gate: CRIT-DEFAULT-UNITS (owner answer: show no
banner when the unit is missing or cannot be converted). L0 rulings on PR #518: 6684499411
(R-a: mEq/L is a same-unit spelling for potassium and sodium only; R-b: wbc is read as
white_blood_cells, nothing else is aliased) and 6684505629.

HC-CDU-001: the unit constant and the unchanged table.
HC-CDU-002: one case per row of the 35-row probe table (comment 6684474226).
HC-CDU-003: the four rows whose direction was wrong before.
HC-CDU-004: names without a default row get no default banner (glucose_fasting, hba1c).
HC-CDU-005: exact banner sentences (CRIT-BANNER-WORDING).
HC-CDU-006: mEq/L is not an equivalence for any other analyte.

The cases go through `InterpretModule._apply_critical_check(observation, None, result)`: there is
no route, so `route_client` does not apply. No mocks of the guard or of the unit rule. Rows
that already behave this way on main are regression guards and pass before the fix.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from models import Observation
from modules.interpret import InterpretModule
from modules.interpret_safety import InterpretationSafetyGuard, SafetyValidationResult
from modules.normalize import UNIT_CONVERSIONS

COLLECTED = datetime(2026, 3, 1, 9, 0, 0)


def _check(analyte: str, value: float, unit: str | None) -> SafetyValidationResult:
    """Run the real critical check with no KB row (info is None)."""
    module = InterpretModule(
        knowledge_loader=MagicMock(),
        safety_guard=InterpretationSafetyGuard(),
        recommendation_engine=MagicMock(),
        model_selector=MagicMock(),
    )
    obs = Observation(
        id=str(uuid.uuid4()), profile_id="profile-cdu", doc_id=str(uuid.uuid4()),
        analyte_canonical=analyte, analyte_raw=analyte, value=value,
        unit=unit, collected_at=COLLECTED,
    )
    result = SafetyValidationResult(passed=True)
    module._apply_critical_check(obs, None, result)
    return result


def _direction(result: SafetyValidationResult) -> str | None:
    reason = result.physician_review_reason
    if not result.requires_physician_review:
        assert reason is None
        return None
    assert reason is not None
    if reason.startswith("Critical low value:"):
        return "low"
    if reason.startswith("Critical high value:"):
        return "high"
    raise AssertionError(f"unexpected reason: {reason!r}")


# --- HC-CDU-001: the constant and the table

def test_hc_cdu_001_unit_constant_names_each_row_and_table_is_unchanged():
    guard = InterpretationSafetyGuard
    assert guard.DEFAULT_CRITICAL_UNITS == {
        "glucose": ("mg/dL",),
        "hemoglobin": ("g/dL",),
        "potassium": ("mmol/L", "mEq/L"),
        "sodium": ("mmol/L", "mEq/L"),
        "platelets": ("10^3/uL",),
        "wbc": ("10^3/uL",),
        "white_blood_cells": ("10^3/uL",),
    }
    # Every table row has a unit entry and no unit key sits inside a row (HC-WCN-004).
    assert set(guard.DEFAULT_CRITICAL_UNITS) == set(guard.DEFAULT_CRITICAL_THRESHOLDS)
    assert guard.DEFAULT_CRITICAL_THRESHOLDS == {
        "glucose": {"critical_low": 50, "critical_high": 400},
        "hemoglobin": {"critical_low": 7.0, "critical_high": 20.0},
        "potassium": {"critical_low": 2.5, "critical_high": 6.5},
        "sodium": {"critical_low": 120, "critical_high": 160},
        "platelets": {"critical_low": 50, "critical_high": 1000},
        "wbc": {"critical_low": 2.0, "critical_high": 30.0},
        "white_blood_cells": {"critical_low": 2.0, "critical_high": 30.0},
    }
    # R-a: no new conversion entry for potassium or sodium.
    assert "potassium" not in UNIT_CONVERSIONS
    assert "sodium" not in UNIT_CONVERSIONS


# --- HC-CDU-002: the 35-row probe table, "after" column

PROBE_ROWS = [
    # (analyte, value, unit, expected direction; None = no banner)
    ("glucose", 450, "mg/dL", "high"),
    ("glucose", 40, "mg/dL", "low"),
    ("glucose", 25.0, "mmol/L", "high"),
    ("glucose", 2.0, "mmol/L", "low"),
    ("glucose", 450, None, None),
    ("hemoglobin", 6.0, "g/dL", "low"),
    ("hemoglobin", 21.0, "g/dL", "high"),
    ("hemoglobin", 60, "g/L", "low"),
    ("hemoglobin", 6.0, None, None),
    ("potassium", 6.8, "mmol/L", "high"),
    ("potassium", 2.2, "mmol/L", "low"),
    ("potassium", 6.8, "mEq/L", "high"),
    ("potassium", 2.2, "mEq/L", "low"),
    ("potassium", 6.8, None, None),
    ("sodium", 118, "mmol/L", "low"),
    ("sodium", 165, "mmol/L", "high"),
    ("sodium", 118, "mEq/L", "low"),
    ("sodium", 165, "mEq/L", "high"),
    ("sodium", 118, None, None),
    ("platelets", 30, "10^3/uL", "low"),
    ("platelets", 30, "x10E3/uL", "low"),
    ("platelets", 30, "K/uL", "low"),
    ("platelets", 30, "10*3/uL", "low"),
    ("platelets", 30, "x10^3/uL", "low"),
    ("platelets", 30000, "cells/uL", "low"),
    ("platelets", 30, None, None),
    ("wbc", 1.5, "10^3/uL", "low"),
    ("wbc", 1.5, "x10E3/uL", "low"),
    ("wbc", 1.5, "K/uL", "low"),
    ("wbc", 1.5, None, None),
    ("white_blood_cells", 1.5, "10^3/uL", "low"),
    ("white_blood_cells", 1.5, "x10E3/uL", "low"),
    ("white_blood_cells", 1.5, "K/uL", "low"),
    ("white_blood_cells", 1500, "cells/uL", "low"),
    ("white_blood_cells", 1.5, None, None),
]


def test_hc_cdu_002_probe_table_has_35_rows_and_7_missing_unit_rows():
    assert len(PROBE_ROWS) == 35
    assert sum(1 for r in PROBE_ROWS if r[2] is None) == 7


@pytest.mark.parametrize(
    "analyte,value,unit,expected",
    PROBE_ROWS,
    ids=[f"HC-CDU-002-{a}-{v}-{u}" for a, v, u, _ in PROBE_ROWS],
)
def test_hc_cdu_002_probe_row(analyte, value, unit, expected):
    """Every row with a unit still gets its banner; a missing unit gets none (owner's rule)."""
    assert _direction(_check(analyte, value, unit)) == expected


# --- HC-CDU-003: the four rows whose banner pointed the wrong way

def test_hc_cdu_003_platelets_30000_cells_is_low_not_high():
    result = _check("platelets", 30000, "cells/uL")
    assert _direction(result) == "low"
    assert result.physician_review_reason == (
        "Critical low value: 30000 cells/uL (30.0 x10^3/uL) is below the critical threshold "
        "of 50 x10^3/uL."
    )


def test_hc_cdu_003_glucose_25_mmol_is_high_not_low():
    result = _check("glucose", 25.0, "mmol/L")
    assert _direction(result) == "high"
    assert result.physician_review_reason == (
        "Critical high value: 25 mmol/L (450 mg/dL) is above the critical threshold of 400 mg/dL."
    )


def test_hc_cdu_003_hemoglobin_60_g_per_l_is_low_not_high():
    result = _check("hemoglobin", 60, "g/L")
    assert _direction(result) == "low"
    assert result.physician_review_reason == (
        "Critical low value: 60 g/L (6.0 g/dL) is below the critical threshold of 7 g/dL."
    )


def test_hc_cdu_003_white_cells_1500_cells_is_low_not_high():
    result = _check("white_blood_cells", 1500, "cells/uL")
    assert _direction(result) == "low"
    assert result.physician_review_reason == (
        "Critical low value: 1500 cells/uL (1.5 x10^3/uL) is below the critical threshold "
        "of 2 x10^3/uL."
    )


# --- HC-CDU-004: no default row, no default banner

@pytest.mark.parametrize(
    "analyte,value,unit",
    [
        ("glucose_fasting", 450, "mg/dL"),
        ("glucose_fasting", 25.0, "mmol/L"),
        ("glucose_fasting", 40, "mg/dL"),
        ("hba1c", 12.0, "%"),
        ("hemoglobin_a1c", 12.0, "%"),
    ],
    ids=lambda v: str(v),
)
def test_hc_cdu_004_name_without_a_default_row_gets_no_banner(analyte, value, unit):
    """`glucose_fasting` is not aliased to glucose here: only wbc is mapped (ruling R-b)."""
    result = _check(analyte, value, unit)
    assert result.requires_physician_review is False
    assert result.physician_review_reason is None


# --- HC-CDU-005: exact sentences (CRIT-BANNER-WORDING)

def test_hc_cdu_005_same_unit_has_no_parenthesis():
    assert _check("potassium", 6.8, "mmol/L").physician_review_reason == (
        "Critical high value: 6.8 mmol/L is above the critical threshold of 6.5 mmol/L."
    )


def test_hc_cdu_005_meq_relabel_keeps_the_patients_unit():
    assert _check("potassium", 6.8, "mEq/L").physician_review_reason == (
        "Critical high value: 6.8 mEq/L is above the critical threshold of 6.5 mEq/L."
    )
    assert _check("sodium", 118, "mEq/L").physician_review_reason == (
        "Critical low value: 118 mEq/L is below the critical threshold of 120 mEq/L."
    )


def test_hc_cdu_005_converted_value_sits_in_parentheses():
    assert _check("glucose", 25.0, "mmol/L").physician_review_reason == (
        "Critical high value: 25 mmol/L (450 mg/dL) is above the critical threshold of 400 mg/dL."
    )


def test_hc_cdu_005_count_spelling_relabel_has_no_parenthesis():
    assert _check("platelets", 30, "K/uL").physician_review_reason == (
        "Critical low value: 30 K/uL is below the critical threshold of 50 K/uL."
    )


def test_hc_cdu_005_wbc_row_is_read_as_white_blood_cells():
    assert _check("wbc", 1.5, "K/uL").physician_review_reason == (
        "Critical low value: 1.5 K/uL is below the critical threshold of 2 K/uL."
    )
    assert _check("wbc", 1500, "cells/uL").physician_review_reason == (
        "Critical low value: 1500 cells/uL (1.5 x10^3/uL) is below the critical threshold "
        "of 2 x10^3/uL."
    )


# --- HC-CDU-006: mEq/L is an equivalence for potassium and sodium only

@pytest.mark.parametrize(
    "analyte,value",
    [("glucose", 450), ("glucose", 40), ("hemoglobin", 6.0), ("platelets", 30), ("wbc", 1.5)],
    ids=lambda v: str(v),
)
def test_hc_cdu_006_meq_per_l_is_not_a_unit_for_other_rows(analyte, value):
    result = _check(analyte, value, "mEq/L")
    assert result.requires_physician_review is False
    assert result.physician_review_reason is None


@pytest.mark.parametrize(
    "analyte,value",
    [("potassium", 6.8), ("sodium", 118)],
    ids=lambda v: str(v),
)
def test_hc_cdu_006_unconvertible_unit_gets_no_banner(analyte, value):
    result = _check(analyte, value, "mg/dL")
    assert result.requires_physician_review is False
    assert result.physician_review_reason is None
