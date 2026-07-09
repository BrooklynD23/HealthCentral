"""
Tests for cross-lab unit safety in api.export._compute_trends (NORM-UNIT-001
follow-up): the doctor-summary/questions trend calculation must not produce a
spurious delta when observations for the same analyte were recorded in
different units.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.export import _compute_trends


def _obs(*, analyte: str, value: float, unit: str, collected_at: datetime):
    return {
        "analyte_canonical": analyte,
        "analyte_raw": analyte,
        "value": value,
        "unit": unit,
        "collected_at": collected_at,
    }


def test_HC_EXPORT_TREND_001_mixed_unit_glucose_uses_canonical_conversion():
    """Two glucose readings in different units are compared in canonical
    units instead of producing a spurious ~94% cross-unit delta."""
    observations = [
        _obs(analyte="glucose", value=94.0, unit="mg/dL",
             collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc)),
        _obs(analyte="glucose", value=5.22, unit="mmol/L",
             collected_at=datetime(2024, 6, 1, tzinfo=timezone.utc)),
    ]
    trends = _compute_trends(observations)

    assert len(trends) == 1
    trend = trends[0]
    assert trend["analyte"] == "glucose"
    assert trend["trend_direction"] == "stable"
    assert trend["delta_percent"] < 5


def test_HC_EXPORT_TREND_002_untabled_analyte_mixed_units_skips_trend():
    """An untabled analyte with mixed, unconvertible units produces no
    trend rather than comparing incompatible numbers."""
    observations = [
        _obs(analyte="esr", value=20.0, unit="mm/hr",
             collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc)),
        _obs(analyte="esr", value=2.0, unit="cm/hr",
             collected_at=datetime(2024, 6, 1, tzinfo=timezone.utc)),
    ]
    trends = _compute_trends(observations)

    assert trends == []


def test_HC_EXPORT_TREND_003_single_unit_series_unchanged():
    """A single-unit series still computes the raw percent change as before."""
    observations = [
        _obs(analyte="creatinine", value=1.0, unit="mg/dL",
             collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc)),
        _obs(analyte="creatinine", value=1.5, unit="mg/dL",
             collected_at=datetime(2024, 6, 1, tzinfo=timezone.utc)),
    ]
    trends = _compute_trends(observations)

    assert len(trends) == 1
    assert trends[0]["trend_direction"] == "up"
    assert trends[0]["delta_percent"] == 50.0
