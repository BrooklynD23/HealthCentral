"""
Tests for cross-lab unit safety in RAGModule._get_observation_chunks
(NORM-UNIT-001 follow-up): the "Trend (last N)" grounded-context string fed
to the LLM must not compute a spurious delta across observations recorded
in different units for the same analyte.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.rag import RAGModule


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


def _obs(*, analyte: str, value: float, unit: str, collected_at: datetime):
    return SimpleNamespace(
        id="obs-1",
        doc_id="doc-1",
        analyte_canonical=analyte,
        value=value,
        unit=unit,
        ref_low=None,
        ref_high=None,
        ref_range_text=None,
        flag=None,
        is_abnormal=False,
        collected_at=collected_at,
        user_verified=False,
    )


@pytest.mark.asyncio
async def test_HC_RAG_TREND_001_mixed_unit_glucose_uses_canonical_conversion():
    """Newest-first rows in mixed glucose units produce a stable trend
    once converted, not a spurious ~94% swing from raw values."""
    rag = RAGModule()
    # order_by(collected_at.desc()) — newest first, matching the real query
    rows = [
        _obs(analyte="glucose", value=5.22, unit="mmol/L",
             collected_at=datetime(2024, 6, 1, tzinfo=timezone.utc)),
        _obs(analyte="glucose", value=94.0, unit="mg/dL",
             collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc)),
    ]
    chunks = await rag._get_observation_chunks(
        query="glucose",
        profile_id="profile-a",
        selected_analytes=["glucose"],
        from_date=None,
        to_date=None,
        profile_db=_FakeProfileDb(rows),
    )

    assert len(chunks) == 1
    text = chunks[0].text
    assert "Trend" in text
    assert "(stable)" in text
    assert "increasing" not in text
    assert "decreasing" not in text


@pytest.mark.asyncio
async def test_HC_RAG_TREND_002_untabled_analyte_mixed_units_omits_trend():
    """An untabled analyte with mixed, unconvertible units gets no Trend
    line rather than a fabricated comparison."""
    rag = RAGModule()
    rows = [
        _obs(analyte="esr", value=2.0, unit="cm/hr",
             collected_at=datetime(2024, 6, 1, tzinfo=timezone.utc)),
        _obs(analyte="esr", value=20.0, unit="mm/hr",
             collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc)),
    ]
    chunks = await rag._get_observation_chunks(
        query="esr",
        profile_id="profile-a",
        selected_analytes=["esr"],
        from_date=None,
        to_date=None,
        profile_db=_FakeProfileDb(rows),
    )

    assert len(chunks) == 1
    assert "Trend" not in chunks[0].text
