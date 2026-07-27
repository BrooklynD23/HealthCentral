"""MED-CORR-001 — GET /medications/{id}/correlations.

Only a frontend heuristic existed (`src/frontend/src/utils/correlation.ts`);
`docs/plans/roadmap_gap_closure.md` had marked the endpoint "COMPLETE" though
it was never built. This ports the same overlap rule to the backend so there
is one definition rather than two that can drift.

Test IDs: HC-MCORR-0NN.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

import api.medications as medications_api
from core.auth import Session


def _session(profile_id: str = "profile-a") -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="T",
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )


def _medication(*, started, ended=None, profile_id="profile-a"):
    return SimpleNamespace(
        id="11111111-1111-4111-8111-111111111111",
        profile_id=profile_id,
        name="Metformin",
        started_at=started,
        ended_at=ended,
    )


def _observation(*, analyte="Glucose", collected, verified=True, value=100.0):
    return SimpleNamespace(
        id=str(uuid.uuid4()),
        analyte_canonical=analyte,
        value=value,
        value_text=None,
        unit="mg/dL",
        ref_low=70.0,
        ref_high=99.0,
        flag="H",
        is_abnormal=True,
        collected_at=collected,
        user_verified=verified,
    )


def _where_clause(statement: str) -> str:
    """Just the WHERE portion — `user_verified` also appears in the SELECT
    column list, so a naive substring check would always match."""
    upper = statement.upper()
    start = upper.find("WHERE")
    return statement[start:] if start != -1 else ""


class _ProfileDb:
    """Returns the medication first, then observations, then the undated count.

    The route's filtering is expressed in SQL, so these tests assert on the
    *query* the route builds rather than re-implementing the filter in Python.
    """

    def __init__(self, medication, observations, undated_count=0):
        self._medication = medication
        self._observations = observations
        self._undated_count = undated_count
        self.statements: list[str] = []
        self._call = 0

    async def execute(self, stmt):
        self.statements.append(str(stmt))
        self._call += 1
        if self._call == 1:
            return SimpleNamespace(scalar_one_or_none=lambda: self._medication)
        if self._call == 2:
            rows = self._observations
            return SimpleNamespace(
                scalars=lambda: SimpleNamespace(all=lambda: rows)
            )
        return SimpleNamespace(scalar_one=lambda: self._undated_count)


async def _call(profile_db, **kwargs):
    with patch.object(medications_api, "audit_and_commit", AsyncMock()) as audit:
        response = await medications_api.get_medication_correlations(
            medication_id="11111111-1111-4111-8111-111111111111",
            session=_session(),
            master_db=AsyncMock(),
            profile_db=profile_db,
            analyte=kwargs.get("analyte"),
            verified_only=kwargs.get("verified_only", True),
        )
    return response, audit


@pytest.mark.asyncio
async def test_hc_mcorr_001_returns_observations_in_the_active_window():
    med = _medication(
        started=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ended=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    obs = [
        _observation(collected=datetime(2026, 2, 1, tzinfo=timezone.utc)),
        _observation(collected=datetime(2026, 5, 1, tzinfo=timezone.utc), analyte="A1c"),
    ]
    response, _ = await _call(_ProfileDb(med, obs))

    assert response.observation_count == 2
    assert response.analytes == ["A1c", "Glucose"]
    assert response.started_at == "2026-01-01T00:00:00+00:00"
    assert response.ended_at == "2026-06-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_hc_mcorr_002_query_bounds_match_the_frontend_overlap_rule():
    """started_at <= collected_at AND (ended_at IS NULL OR collected_at <= ended_at)
    — the same rule as utils/correlation.ts, now in one place."""
    med = _medication(
        started=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ended=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    db = _ProfileDb(med, [])
    await _call(db)

    obs_query = db.statements[1]
    where = _where_clause(obs_query)
    assert "collected_at >=" in where
    assert "collected_at <=" in where
    assert "IS NOT NULL" in where.upper()


@pytest.mark.asyncio
async def test_hc_mcorr_003_open_ended_medication_has_no_upper_bound():
    med = _medication(started=datetime(2026, 1, 1, tzinfo=timezone.utc), ended=None)
    db = _ProfileDb(med, [])
    response, _ = await _call(db)

    assert response.ended_at is None
    assert "collected_at <=" not in _where_clause(db.statements[1])


@pytest.mark.asyncio
async def test_hc_mcorr_004_undated_observations_are_excluded_but_counted():
    """Mirrors the existing rule: undated observations are listed elsewhere but
    never placed on a timeline. Counting them keeps the omission visible."""
    med = _medication(started=datetime(2026, 1, 1, tzinfo=timezone.utc))
    response, _ = await _call(_ProfileDb(med, [], undated_count=3))

    assert response.observation_count == 0
    assert response.excluded_undated_count == 3


@pytest.mark.asyncio
async def test_hc_mcorr_005_defaults_to_verified_observations_only():
    """An unverified extraction is not a fact worth correlating against."""
    med = _medication(started=datetime(2026, 1, 1, tzinfo=timezone.utc))
    db = _ProfileDb(med, [])
    await _call(db)

    assert "user_verified" in _where_clause(db.statements[1])


@pytest.mark.asyncio
async def test_hc_mcorr_005b_verified_only_can_be_disabled():
    med = _medication(started=datetime(2026, 1, 1, tzinfo=timezone.utc))
    db = _ProfileDb(med, [])
    await _call(db, verified_only=False)

    assert "user_verified" not in _where_clause(db.statements[1])


@pytest.mark.asyncio
async def test_hc_mcorr_006_analyte_filter_is_applied():
    med = _medication(started=datetime(2026, 1, 1, tzinfo=timezone.utc))
    db = _ProfileDb(med, [])
    await _call(db, analyte="Glucose")

    assert "analyte_canonical" in _where_clause(db.statements[1])


@pytest.mark.asyncio
async def test_hc_mcorr_007_missing_medication_returns_404():
    with pytest.raises(HTTPException) as exc:
        await _call(_ProfileDb(None, []))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_hc_mcorr_008_other_profile_is_rejected():
    """Per-profile isolation: a medication belonging to another profile must
    not be readable even with a valid session."""
    med = _medication(
        started=datetime(2026, 1, 1, tzinfo=timezone.utc), profile_id="profile-b"
    )
    with pytest.raises(HTTPException) as exc:
        await _call(_ProfileDb(med, []))
    assert exc.value.status_code in (403, 404)


@pytest.mark.asyncio
async def test_hc_mcorr_009_invalid_uuid_rejected():
    with patch.object(medications_api, "audit_and_commit", AsyncMock()):
        with pytest.raises(HTTPException) as exc:
            await medications_api.get_medication_correlations(
                medication_id="not-a-uuid",
                session=_session(),
                master_db=AsyncMock(),
                profile_db=_ProfileDb(None, []),
                analyte=None,
                verified_only=True,
            )
    assert exc.value.status_code in (400, 422)


@pytest.mark.asyncio
async def test_hc_mcorr_010_route_is_audit_logged():
    """Audit logging on every route that touches observation data."""
    med = _medication(started=datetime(2026, 1, 1, tzinfo=timezone.utc))
    _, audit = await _call(_ProfileDb(med, [_observation(
        collected=datetime(2026, 2, 1, tzinfo=timezone.utc))]))

    audit.assert_awaited_once()
    details = audit.await_args.kwargs["details"]
    assert details["count"] == 1
    # AUDIT-PHI-001: no analyte or medication name in the audit row.
    assert "analyte" not in details
    assert "medication_name" not in details
