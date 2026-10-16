"""W-2 / owner decision D3 (2026-09-27): doctor-summary redaction (HC-EXPR-NNN).

The doctor summary goes to a third party, so it passes strict
modules/redaction.py before it is stored or rendered, in every download format
(text, html, pdf). CSV and JSON are the patient's own full-fidelity export and
stay byte-for-byte unredacted (named exceptions, W-10).

Scope of the claim: labelled name/DOB/MRN in free-text fields. Underscore-joined
identifiers are a known, owner-gated gap (O-3), pinned by a strict xfail.

Every test drives FastAPI's dependency graph through
tests/support/routes.py::route_client (recurring-failures #1).
"""

from __future__ import annotations

import io
import json
import os
import sys
import types
from contextlib import ExitStack, contextmanager
from datetime import datetime
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import api.export as export_api
from core.auth import get_profile_db_session
from tests.support.routes import route_client

PROFILE_A = "profile-a"
PROFILE_B = "profile-b"

# PHI seeded into the free-text fields the summary renders (unit, flag), in the
# labelled shapes the strict engine documents (name_context, dob, mrn).
PHI_STRINGS = ("Jane", "Doe", "01/02/1980", "A12345")


def _obs(
    obs_id: str,
    analyte: str,
    value: float,
    unit: str,
    flag: str | None,
    collected_at: datetime,
    ref_low: float,
    ref_high: float,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=obs_id,
        profile_id=PROFILE_A,
        analyte_canonical=analyte,
        analyte_raw=analyte,
        value=value,
        value_text=None,
        unit=unit,
        ref_low=ref_low,
        ref_high=ref_high,
        ref_range_text=None,
        flag=flag,
        is_abnormal=flag is not None,
        user_verified=False,
        collected_at=collected_at,
    )


PHI_ROWS = (
    _obs("00000000-0000-4000-8000-000000000001", "glucose", 100.0, "mg/dL", None, datetime(2024, 1, 10), 70.0, 99.0),
    _obs("00000000-0000-4000-8000-000000000002", "glucose", 250.0, "mg/dL", "HH", datetime(2024, 3, 15), 70.0, 99.0),
    _obs("00000000-0000-4000-8000-000000000003", "potassium", 6.1, "mmol/L (Patient: Jane Doe)", "H", datetime(2024, 3, 15), 3.5, 5.1),
    _obs("00000000-0000-4000-8000-000000000004", "hemoglobin", 9.1, "g/dL", "L DOB: 01/02/1980", datetime(2024, 3, 15), 12.0, 16.0),
    _obs("00000000-0000-4000-8000-000000000005", "sodium", 150.0, "mmol/L MRN: A12345", "H", datetime(2024, 3, 15), 135.0, 145.0),
)


class _Scalars:
    def __init__(self, rows: tuple) -> None:
        self._rows = rows

    def all(self) -> list:
        return list(self._rows)


class _Result:
    def __init__(self, rows: tuple) -> None:
        self._rows = rows

    def scalars(self) -> _Scalars:
        return _Scalars(self._rows)


class _FakeProfileDb:
    """Returns the fixture rows for any query (pattern: test_observations_audit.py)."""

    def __init__(self, rows: tuple) -> None:
        self._rows = rows

    async def execute(self, _stmt: object) -> _Result:
        return _Result(self._rows)


@pytest.fixture(autouse=True)
def _fresh_summary_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(export_api, "_summary_store", {})


def _override_profile_db_for(rows: tuple):
    """Dependency override returning a fake vault holding `rows`."""
    fake_db = _FakeProfileDb(rows)

    async def _override_profile_db() -> _FakeProfileDb:
        return fake_db

    return _override_profile_db


@contextmanager
def _export_client(
    profile_id: str = PROFILE_A,
    rows: tuple = PHI_ROWS,
    master_db: object | None = None,
) -> Iterator[TestClient]:
    """route_client for /export over a fixture vault.

    master_db=None: route_client's AsyncMock master DB, with the audit helper
    stubbed. HC-EXPR-003 passes a real AsyncSession so audit rows persist.
    """
    with ExitStack() as stack:
        if master_db is None:
            stack.enter_context(
                patch.object(export_api, "log_export_event", AsyncMock(return_value=object()))
            )
        client = stack.enter_context(
            route_client(export_api.router, "/export", profile_id=profile_id, master_db=master_db)
        )
        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db_for(rows)
        yield client


def _export_bytes(path: str) -> bytes:
    """GET /export/{path} over HTTP with the PHI fixture; return the body."""
    with _export_client() as client:
        response = client.get(f"/export/{path}")
    assert response.status_code == 200, response.text
    return response.content


# Captured on the W-2 start tree BEFORE any product change (Task 1 Step 3).
# Escaped bytes literals, not golden files: `.gitattributes` has
# `* text=auto`, which would rewrite the CSV's \r\n endings in a file.
BASELINE_CSV = (
    b'Date,Analyte,Value,Unit,Reference Low,Reference High,Flag,Verified\r\n'
    b'2024-01-10,glucose,100.0,mg/dL,70.0,99.0,,No\r\n'
    b'2024-03-15,glucose,250.0,mg/dL,70.0,99.0,HH,No\r\n'
    b'2024-03-15,hemoglobin,9.1,g/dL,12.0,16.0,L DOB: 01/02/1980,No\r\n'
    b'2024-03-15,potassium,6.1,mmol/L (Patient: Jane Doe),3.5,5.1,H,No\r\n'
    b'2024-03-15,sodium,150.0,mmol/L MRN: A12345,135.0,145.0,H,No\r\n'
)
BASELINE_JSON = (
    b'[\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000001",\n'
    b'    "analyte_canonical": "glucose",\n'
    b'    "analyte_raw": "glucose",\n'
    b'    "value": 100.0,\n'
    b'    "value_text": null,\n'
    b'    "unit": "mg/dL",\n'
    b'    "ref_low": 70.0,\n'
    b'    "ref_high": 99.0,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": null,\n'
    b'    "is_abnormal": false,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-01-10T00:00:00"\n'
    b'  },\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000002",\n'
    b'    "analyte_canonical": "glucose",\n'
    b'    "analyte_raw": "glucose",\n'
    b'    "value": 250.0,\n'
    b'    "value_text": null,\n'
    b'    "unit": "mg/dL",\n'
    b'    "ref_low": 70.0,\n'
    b'    "ref_high": 99.0,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": "HH",\n'
    b'    "is_abnormal": true,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-03-15T00:00:00"\n'
    b'  },\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000003",\n'
    b'    "analyte_canonical": "potassium",\n'
    b'    "analyte_raw": "potassium",\n'
    b'    "value": 6.1,\n'
    b'    "value_text": null,\n'
    b'    "unit": "mmol/L (Patient: Jane Doe)",\n'
    b'    "ref_low": 3.5,\n'
    b'    "ref_high": 5.1,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": "H",\n'
    b'    "is_abnormal": true,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-03-15T00:00:00"\n'
    b'  },\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000004",\n'
    b'    "analyte_canonical": "hemoglobin",\n'
    b'    "analyte_raw": "hemoglobin",\n'
    b'    "value": 9.1,\n'
    b'    "value_text": null,\n'
    b'    "unit": "g/dL",\n'
    b'    "ref_low": 12.0,\n'
    b'    "ref_high": 16.0,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": "L DOB: 01/02/1980",\n'
    b'    "is_abnormal": true,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-03-15T00:00:00"\n'
    b'  },\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000005",\n'
    b'    "analyte_canonical": "sodium",\n'
    b'    "analyte_raw": "sodium",\n'
    b'    "value": 150.0,\n'
    b'    "value_text": null,\n'
    b'    "unit": "mmol/L MRN: A12345",\n'
    b'    "ref_low": 135.0,\n'
    b'    "ref_high": 145.0,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": "H",\n'
    b'    "is_abnormal": true,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-03-15T00:00:00"\n'
    b'  }\n'
    b']'
)


@pytest.mark.parametrize(
    ("path", "baseline"),
    [("csv", BASELINE_CSV), ("json", BASELINE_JSON)],
    ids=["csv", "json"],
)
def test_hc_expr_002_csv_json_unchanged_byte_for_byte(path: str, baseline: bytes) -> None:
    """HC-EXPR-002: CSV/JSON are the patient's own full-fidelity export (D3)."""
    body = _export_bytes(path)
    assert body == baseline
    # Not vacuous: the exception is real, the seeded identifiers are still there.
    for phi in PHI_STRINGS:
        assert phi.encode() in body
