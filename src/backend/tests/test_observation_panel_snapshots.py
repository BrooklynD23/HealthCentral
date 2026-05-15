"""Tests for panel snapshot grouping API."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.observations import get_panel_snapshots
from core.auth import Session


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


def _obs(
    *,
    profile_id: str,
    doc_id: str,
    analyte: str,
    collected_at: datetime | None,
    conf: float = 0.9,
):
    """Minimal object for ObservationResponse.from_model."""
    return SimpleNamespace(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        doc_id=doc_id,
        analyte_canonical=analyte,
        analyte_raw=analyte,
        value=1.0,
        value_text=None,
        unit="mg/dL",
        ref_low=None,
        ref_high=None,
        ref_range_text=None,
        flag=None,
        is_abnormal=False,
        collected_at=collected_at,
        user_verified=False,
        extraction_confidence=conf,
        source_page=None,
        source_bbox_json=None,
    )


@pytest.mark.asyncio
async def test_panel_snapshots_groups_by_doc_and_day():
    """Two draws on different days produce two snapshots."""
    pid = str(uuid.uuid4())
    d1 = datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    d2 = datetime(2024, 7, 1, 10, 0, 0, tzinfo=timezone.utc)
    rows = [
        _obs(profile_id=pid, doc_id="doc-a", analyte="ldl", collected_at=d2, conf=0.5),
        _obs(profile_id=pid, doc_id="doc-a", analyte="hdl", collected_at=d2, conf=0.9),
        _obs(profile_id=pid, doc_id="doc-b", analyte="ldl", collected_at=d1, conf=0.8),
        _obs(profile_id=pid, doc_id="doc-b", analyte="hdl", collected_at=d1, conf=0.7),
    ]
    out = await get_panel_snapshots(
        panel_id="lipid",
        session=_session(pid),
        profile_db=_FakeProfileDb(rows),
    )
    assert len(out) == 2
    assert out[0].collection_date == "2024-07-01"
    assert out[0].doc_id == "doc-a"
    assert {x.analyte_canonical for x in out[0].observations} == {"ldl", "hdl"}
    assert out[1].collection_date == "2024-06-01"


@pytest.mark.asyncio
async def test_panel_snapshots_dedupes_analyte_per_group():
    pid = str(uuid.uuid4())
    day = datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    rows = [
        _obs(profile_id=pid, doc_id="doc-a", analyte="ldl", collected_at=day, conf=0.5),
        _obs(profile_id=pid, doc_id="doc-a", analyte="ldl", collected_at=day, conf=0.95),
    ]
    out = await get_panel_snapshots(
        panel_id="lipid",
        session=_session(pid),
        profile_db=_FakeProfileDb(rows),
    )
    assert len(out) == 1
    assert len(out[0].observations) == 1
    assert out[0].observations[0].extraction_confidence == 0.95
