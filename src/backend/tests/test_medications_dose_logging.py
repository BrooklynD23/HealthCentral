"""Tests for dose logging response contract and badge wiring."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.medications import DoseLog, DoseLogResponse, log_dose
from core.auth import Session
from models import DoseTaken, Medication, UserModelSettings


class _ScalarResult:
    def __init__(self, one=None, all_items=None):
        self._one = one
        self._all_items = all_items or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return self

    def all(self):
        return self._all_items


class _FakeProfileDb:
    def __init__(self, medication: Medication, settings: UserModelSettings):
        self._medication = medication
        self._settings = settings
        self._dose_record: DoseTaken | None = None
        self._added = []
        self._execute_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0

    async def execute(self, _stmt):
        self._execute_calls += 1
        if self._execute_calls == 1:
            return _ScalarResult(one=self._medication)
        if self._execute_calls == 2:
            return _ScalarResult(one=self._settings)
        if self._execute_calls in {3, 4}:
            return _ScalarResult(all_items=[self._dose_record] if self._dose_record else [])
        return _ScalarResult(all_items=[])

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, _obj):
        return None

    async def rollback(self):
        self.rollback_calls += 1

    def add(self, obj):
        self._added.append(obj)
        if isinstance(obj, DoseTaken):
            self._dose_record = obj


@pytest.mark.asyncio
async def test_log_dose_returns_badges_in_response():
    profile_id = str(uuid.uuid4())
    medication_id = str(uuid.uuid4())
    medication = Medication(
        id=medication_id,
        profile_id=profile_id,
        name="Aspirin",
        frequency="once_daily",
        dosage_amount=81.0,
        dosage_unit="mg",
    )
    settings = UserModelSettings(profile_id=profile_id, timezone="UTC")
    profile_db = _FakeProfileDb(medication, settings)
    session = Session(
        profile_id=profile_id,
        profile_name="Test",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    response = await log_dose(
        medication_id=medication_id,
        dose=DoseLog(
            taken_at=datetime(2026, 3, 4, 8, 0, tzinfo=timezone.utc),
            log_method="manual",
        ),
        session=session,
        schedule_id=None,
        profile_db=profile_db,
    )

    assert isinstance(response, DoseLogResponse)
    assert response.dose.medication_id == medication_id
    assert [badge.badge_id for badge in response.newly_earned_badges] == ["first-log"]
    assert profile_db.commit_calls == 2
    assert profile_db.rollback_calls == 0
