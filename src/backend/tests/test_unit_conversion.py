"""Tests for cross-lab unit normalization/conversion (NORM-UNIT-001).

Covers the pure conversion table (`convert_to_canonical`, `canonical_unit_for`)
and the trend endpoint's mixed-unit handling. The endpoint bug being fixed:
a glucose series reported partly in mg/dL and partly in mmol/L produced a
mathematically wrong trend percentage (~-94%) because values were compared
across incompatible units.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.normalize import convert_to_canonical, canonical_unit_for, normalize_unit
from api.observations import get_analyte_trend
from core.auth import Session


# --- Pure conversion table (HC-NORM-2xx) ---------------------------------


def test_HC_NORM_201_glucose_mmol_to_mgdl():
    """5.22 mmol/L glucose converts to ~94 mg/dL (the canonical unit)."""
    conv = convert_to_canonical("glucose", 5.22, "mmol/L")
    assert conv is not None
    assert conv.canonical_unit == "mg/dL"
    assert conv.canonical_value == pytest.approx(94.0, abs=0.5)
    assert conv.converted is True
    assert conv.original_value == 5.22
    assert conv.original_unit == "mmol/L"


def test_HC_NORM_202_glucose_mgdl_passthrough():
    """A value already in the canonical unit is unchanged, converted=False."""
    conv = convert_to_canonical("glucose", 94.0, "mg/dL")
    assert conv is not None
    assert conv.canonical_value == pytest.approx(94.0)
    assert conv.converted is False


def test_HC_NORM_203_creatinine_umol_to_mgdl():
    """88.42 µmol/L creatinine converts to ~1.0 mg/dL."""
    conv = convert_to_canonical("creatinine", 88.42, "umol/L")
    assert conv is not None
    assert conv.canonical_value == pytest.approx(1.0, abs=0.01)


def test_HC_NORM_204_unrecognized_unit_returns_none():
    """A known analyte with an unlisted unit returns None — never guess a factor."""
    assert convert_to_canonical("glucose", 94.0, "mg%") is None


def test_HC_NORM_205_untabled_analyte_has_no_canonical_unit():
    """An analyte with no conversion table entry reports no canonical unit."""
    assert canonical_unit_for("esr") is None
    assert convert_to_canonical("esr", 20.0, "mm/hr") is None


def test_HC_NORM_206_missing_unit_returns_none():
    assert convert_to_canonical("glucose", 94.0, None) is None
    assert convert_to_canonical("glucose", 94.0, "") is None


def test_HC_NORM_207_normalize_unit_variants():
    """Micro sign, greek mu, spacing, and case all normalize to one key."""
    assert normalize_unit("mmol/L") == normalize_unit("MMOL/L ") == "mmol/l"
    assert normalize_unit("µmol/L") == normalize_unit("μmol/L") == "umol/l"


# --- Trend endpoint mixed-unit handling (HC-NORM-21x) --------------------


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _Scalars(self._rows)


class _FakeProfileDb:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, _stmt):
        return _Result(self._rows)


def _session(profile_id: str) -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="T",
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )


def _obs(*, analyte, value, unit, collected_at, ref_low=None, ref_high=None):
    return SimpleNamespace(
        id=str(uuid.uuid4()),
        doc_id="doc-a",
        analyte_canonical=analyte,
        analyte_raw=analyte,
        value=value,
        value_text=None,
        unit=unit,
        ref_low=ref_low,
        ref_high=ref_high,
        ref_range_text=None,
        flag=None,
        is_abnormal=False,
        collected_at=collected_at,
        user_verified=False,
        extraction_confidence=0.9,
        source_page=None,
        source_bbox_json=None,
    )


@pytest.mark.asyncio
async def test_HC_NORM_210_mixed_unit_glucose_is_normalized():
    """Glucose reported in mg/dL then mmol/L charts as one canonical-unit line,
    and the trend summary is not the spurious ~-94% drop."""
    pid = str(uuid.uuid4())
    d1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    d2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
    rows = [
        _obs(analyte="glucose", value=94.0, unit="mg/dL", collected_at=d1),
        _obs(analyte="glucose", value=5.22, unit="mmol/L", collected_at=d2),
    ]
    out = await get_analyte_trend(
        analyte="glucose",
        session=_session(pid),
        profile_db=_FakeProfileDb(rows),
        master_db=AsyncMock(),
    )
    assert out.unit == "mg/dL"
    assert len(out.data_points) == 2
    # Both points now in mg/dL: ~94 and ~94 → essentially stable.
    assert all(p.unit == "mg/dL" for p in out.data_points)
    assert out.data_points[1].value == pytest.approx(94.0, abs=0.5)
    # The second point carries its original reported value for provenance.
    assert out.data_points[1].original_unit == "mmol/L"
    assert out.data_points[1].original_value == 5.22
    assert "decreased by 9" not in out.summary  # no spurious ~-94% drop


@pytest.mark.asyncio
async def test_HC_NORM_211_single_unit_series_unchanged():
    """A consistent-unit series is untouched (no conversion, no original fields)."""
    pid = str(uuid.uuid4())
    d1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    d2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
    rows = [
        _obs(analyte="glucose", value=90.0, unit="mg/dL", collected_at=d1),
        _obs(analyte="glucose", value=100.0, unit="mg/dL", collected_at=d2),
    ]
    out = await get_analyte_trend(
        analyte="glucose",
        session=_session(pid),
        profile_db=_FakeProfileDb(rows),
        master_db=AsyncMock(),
    )
    assert out.unit == "mg/dL"
    assert [p.value for p in out.data_points] == [90.0, 100.0]
    assert all(p.original_value is None for p in out.data_points)


@pytest.mark.asyncio
async def test_HC_NORM_212_untabled_analyte_legacy_behavior():
    """An analyte with no conversion table entry keeps legacy pass-through."""
    pid = str(uuid.uuid4())
    d1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = [_obs(analyte="esr", value=20.0, unit="mm/hr", collected_at=d1)]
    out = await get_analyte_trend(
        analyte="esr",
        session=_session(pid),
        profile_db=_FakeProfileDb(rows),
        master_db=AsyncMock(),
    )
    assert out.unit == "mm/hr"
    assert out.data_points[0].value == 20.0
