"""
Phase C tests for cross-unit historical comparison in interpretation.

These tests pin the comparison-unit behavior for historical lab values so
interpretation trends, narrative text, and stored context JSON all use the
same unit basis.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.interpret import InterpretModule


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


def _obs(*, analyte, value, unit, collected_at):
    return SimpleNamespace(
        id=str(uuid.uuid4()),
        profile_id=str(uuid.uuid4()),
        analyte_canonical=analyte,
        analyte_raw=analyte,
        value=value,
        value_text=None,
        unit=unit,
        ref_low=None,
        ref_high=None,
        ref_range_text=None,
        flag=None,
        is_abnormal=False,
        collected_at=collected_at,
        user_verified=False,
        extraction_confidence=0.9,
        source_page=None,
        source_bbox_json=None,
    )


def _module() -> InterpretModule:
    knowledge_loader = SimpleNamespace(
        get_biomarker_knowledge=AsyncMock(return_value=None),
    )
    recommendation_engine = SimpleNamespace(
        generate_recommendations=AsyncMock(return_value=None),
    )
    return InterpretModule(
        knowledge_loader=knowledge_loader,
        safety_guard=SimpleNamespace(),
        recommendation_engine=recommendation_engine,
        model_selector=SimpleNamespace(),
    )


@pytest.mark.asyncio
async def test_HC_INTERP_001_history_converted_to_canonical():
    module = _module()
    current = _obs(
        analyte="glucose",
        value=5.22,
        unit="mmol/L",
        collected_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )
    history = [
        _obs(
            analyte="glucose",
            value=94.0,
            unit="mg/dL",
            collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
    ]
    context = await module._assemble_context(
        observation=current,
        profile_db=_FakeProfileDb(history),
        master_db=AsyncMock(),
    )

    assert context.comparison_unit == "mg/dL"
    assert context.comparison_current_value == pytest.approx(94.0, abs=0.5)
    assert len(context.historical_values) == 1
    assert context.historical_values[0][1] == pytest.approx(94.0, abs=0.5)
    assert context.trend_direction == "stable"


@pytest.mark.asyncio
async def test_HC_INTERP_002_unconvertible_history_point_dropped():
    module = _module()
    current = _obs(
        analyte="glucose",
        value=5.22,
        unit="mmol/L",
        collected_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )
    history = [
        _obs(
            analyte="glucose",
            value=94.0,
            unit="mg/dL",
            collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
        _obs(
            analyte="glucose",
            value=90.0,
            unit="mg%",
            collected_at=datetime(2023, 12, 1, tzinfo=timezone.utc),
        ),
    ]
    context = await module._assemble_context(
        observation=current,
        profile_db=_FakeProfileDb(history),
        master_db=AsyncMock(),
    )

    assert context.comparison_unit == "mg/dL"
    assert len(context.historical_values) == 1
    assert context.historical_values[0][1] == pytest.approx(94.0, abs=0.5)
    assert context.comparison_current_value == pytest.approx(94.0, abs=0.5)


@pytest.mark.asyncio
async def test_HC_INTERP_003_unconvertible_current_matches_identical_unit_only():
    module = _module()
    current = _obs(
        analyte="sodium",
        value=155.0,
        unit="MMOL/L",
        collected_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )
    history = [
        _obs(
            analyte="sodium",
            value=138.0,
            unit="mmol/l",
            collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
        _obs(
            analyte="sodium",
            value=10.0,
            unit="mEq/L",
            collected_at=datetime(2023, 12, 1, tzinfo=timezone.utc),
        ),
    ]
    context = await module._assemble_context(
        observation=current,
        profile_db=_FakeProfileDb(history),
        master_db=AsyncMock(),
    )

    assert context.comparison_unit == "MMOL/L"
    assert context.comparison_current_value == 155.0
    assert len(context.historical_values) == 1
    assert context.historical_values[0][1] == 138.0
    assert context.trend_direction == "increasing"


@pytest.mark.asyncio
async def test_HC_INTERP_004_narrative_uses_comparison_unit():
    module = _module()
    current = _obs(
        analyte="glucose",
        value=5.22,
        unit="mmol/L",
        collected_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )
    history = [
        _obs(
            analyte="glucose",
            value=94.0,
            unit="mg/dL",
            collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
    ]
    context = await module._assemble_context(
        observation=current,
        profile_db=_FakeProfileDb(history),
        master_db=AsyncMock(),
    )
    text, advice = await module._generate_interpretation(context, AsyncMock())

    assert advice is None
    assert "previous result of 94" in text
    assert "mg/dL" in text
    assert text.count("(values compared in mg/dL)") == 1
    assert "decreased" not in text


@pytest.mark.asyncio
async def test_HC_INTERP_005_context_json_change_in_canonical():
    module = _module()
    current = _obs(
        analyte="glucose",
        value=5.22,
        unit="mmol/L",
        collected_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )
    history = [
        _obs(
            analyte="glucose",
            value=94.0,
            unit="mg/dL",
            collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
    ]
    context = await module._assemble_context(
        observation=current,
        profile_db=_FakeProfileDb(history),
        master_db=AsyncMock(),
    )
    payload = json.loads(module._build_context_json(context))

    assert payload["comparison_unit"] == "mg/dL"
    # 5.22 mmol/L converts to ~94.04 mg/dL (factor 18.0156), not bit-exact
    # equal to the 94.0 mg/dL history point; tolerance reflects that rounding,
    # not a real clinical change.
    assert payload["change"] == pytest.approx(0.0, abs=0.1)
    assert payload["change_percent"] == pytest.approx(0.0, abs=0.2)
