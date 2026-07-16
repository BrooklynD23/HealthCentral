"""HC-M20 pinboard tests (HC-PIN-NNN)."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth import Session
from core.time import utcnow
from core.profile_database import ProfileDatabaseBase


def _session(profile_id: str = "test-profile") -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="Test Profile",
        expires_at=utcnow() + timedelta(hours=1),
    )


class _Scalars:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class _Result:
    def __init__(self, one=None, items=None):
        self.one = one
        self.items = items or []

    def scalar_one_or_none(self):
        return self.one

    def scalars(self):
        return _Scalars(self.items)


def _pinboard(**overrides):
    from models.pinboard import Pinboard

    fields = {
        "id": str(uuid.uuid4()),
        "name": "Next appointment",
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }
    fields.update(overrides)
    return Pinboard(**fields)


def _item(pinboard_id: str, **overrides):
    from models.pinboard import PinboardItem

    fields = {
        "id": str(uuid.uuid4()),
        "pinboard_id": pinboard_id,
        "item_type": "document",
        "item_id": str(uuid.uuid4()),
        "created_at": utcnow(),
    }
    fields.update(overrides)
    return PinboardItem(**fields)


@pytest_asyncio.fixture
async def real_profile_db():
    from models import Pinboard, PinboardItem  # noqa: F401 -- register tables

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_hc_pin_001_create_rename_list_delete_are_profile_scoped_and_audited(monkeypatch):
    from api.pinboards import (
        PinboardCreateRequest,
        PinboardUpdateRequest,
        create_pinboard,
        delete_pinboard,
        list_pinboards,
        rename_pinboard,
    )

    board = _pinboard()
    profile_db = AsyncMock()
    profile_db.add = MagicMock()
    profile_db.execute.side_effect = [
        _Result(items=[board]),
        _Result(one=board),
        _Result(one=board),
    ]
    audit = AsyncMock()
    monkeypatch.setattr("api.pinboards.log_pinboard_event", audit)
    master_db = AsyncMock()

    created = await create_pinboard(
        PinboardCreateRequest(name="  Next appointment  "),
        _session(), profile_db, master_db,
    )
    assert created.name == "Next appointment"
    profile_db.add.assert_called_once()
    await list_pinboards(_session(), profile_db, master_db)
    renamed = await rename_pinboard(
        board.id, PinboardUpdateRequest(name="Records to discuss"),
        _session(), profile_db, master_db,
    )
    assert renamed.name == "Records to discuss"
    await delete_pinboard(board.id, _session(), profile_db, master_db)
    assert profile_db.commit.await_count == 3
    assert profile_db.delete.await_count == 1
    assert audit.await_count == 4
    assert {call.kwargs["event"] for call in audit.await_args_list} == {
        "create", "view", "update", "delete"
    }
    for call in audit.await_args_list:
        assert "Next appointment" not in str(call.kwargs.get("details"))
        assert "Records to discuss" not in str(call.kwargs.get("details"))


@pytest.mark.asyncio
async def test_hc_pin_002_add_list_remove_and_duplicate_conflict(monkeypatch):
    from api.pinboards import (
        PinboardItemCreateRequest,
        add_pinboard_item,
        list_pinboard_items,
        remove_pinboard_item,
    )

    board = _pinboard()
    document_id = str(uuid.uuid4())
    item = _item(board.id, item_id=document_id)
    document = type("Document", (), {"id": document_id, "profile_id": "test-profile"})()
    profile_db = AsyncMock()
    profile_db.add = MagicMock()
    profile_db.execute.side_effect = [
        _Result(one=board), _Result(one=document), _Result(one=None),
        _Result(one=board), _Result(items=[item]),
        _Result(one=board), _Result(one=item),
        _Result(one=board), _Result(one=document), _Result(one=item),
    ]
    audit = AsyncMock()
    monkeypatch.setattr("api.pinboards.log_pinboard_event", audit)
    monkeypatch.setattr(
        "api.pinboards._prune_stale_items",
        AsyncMock(side_effect=lambda _db, items, _profile_id: items),
    )
    master_db = AsyncMock()

    added = await add_pinboard_item(
        board.id, PinboardItemCreateRequest(item_type="document", item_id=document_id),
        _session(), profile_db, master_db,
    )
    assert added.item_type == "document"
    listed = await list_pinboard_items(board.id, _session(), profile_db, master_db)
    assert [entry.item_id for entry in listed] == [document_id]
    await remove_pinboard_item(item.id, board.id, _session(), profile_db, master_db)
    with pytest.raises(HTTPException) as exc:
        await add_pinboard_item(
            board.id, PinboardItemCreateRequest(item_type="document", item_id=document_id),
            _session(), profile_db, master_db,
        )
    assert exc.value.status_code == 409
    assert audit.await_count == 3


@pytest.mark.asyncio
async def test_hc_pin_003_rejects_unknown_item_type_before_persistence():
    from pydantic import ValidationError
    from api.pinboards import PinboardItemCreateRequest

    with pytest.raises(ValidationError):
        PinboardItemCreateRequest(item_type="medication", item_id=str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_hc_pin_004_export_requires_explicit_confirmation():
    from api.pinboards import PinboardExportRequest, export_pinboard_packet

    with pytest.raises(HTTPException) as exc:
        await export_pinboard_packet(
            str(uuid.uuid4()), PinboardExportRequest(confirm=False),
            _session(), AsyncMock(), AsyncMock(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_hc_pin_005_export_excludes_unverified_and_invokes_existing_redaction(monkeypatch):
    from api.pinboards import PinboardExportRequest, export_pinboard_packet
    from models.pinboard import PinboardItem

    board = _pinboard(name="Visit records")
    verified_id = str(uuid.uuid4())
    unverified_id = str(uuid.uuid4())
    items = [
        PinboardItem(id=str(uuid.uuid4()), pinboard_id=board.id,
                     item_type="observation", item_id=verified_id, created_at=utcnow()),
        PinboardItem(id=str(uuid.uuid4()), pinboard_id=board.id,
                     item_type="observation", item_id=unverified_id, created_at=utcnow()),
    ]
    verified = type("Observation", (), {
        "id": verified_id, "analyte_canonical": "hemoglobin_a1c",
        "analyte_raw": "A1c", "value": 7.2, "value_text": None, "unit": "%",
        "ref_low": 4.0, "ref_high": 5.6, "flag": "H", "is_abnormal": True,
        "user_verified": True,
        "collected_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
    })()
    unverified = type("Observation", (), {
        "id": unverified_id, "analyte_canonical": "private-unverified-marker",
        "analyte_raw": "marker", "value": 1.0, "value_text": None, "unit": "",
        "ref_low": 0.0, "ref_high": 2.0, "flag": "H", "is_abnormal": True,
        "user_verified": False,
        "collected_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
    })()
    profile_db = AsyncMock()
    profile_db.execute.side_effect = [
        _Result(one=board), _Result(items=items), _Result(items=[verified, unverified]),
    ]
    from modules.redaction import RedactionEngine
    original = RedactionEngine.redact
    redaction_spy = MagicMock()
    def tracked(self, text):
        redaction_spy(text)
        return original(self, text)
    monkeypatch.setattr(RedactionEngine, "redact", tracked)
    audit = AsyncMock()
    monkeypatch.setattr("api.pinboards.log_pinboard_event", audit)
    monkeypatch.setattr(
        "api.pinboards._prune_stale_items",
        AsyncMock(side_effect=lambda _db, current_items, _profile_id: current_items),
    )

    response = await export_pinboard_packet(
        board.id,
        PinboardExportRequest(reason_for_visit="Call 555-123-4567", confirm=True),
        _session(), profile_db, AsyncMock(),
    )
    assert "hemoglobin_a1c" in response.markdown
    assert "private-unverified-marker" not in response.markdown
    assert "555-123-4567" not in response.markdown
    assert redaction_spy.call_count > 0
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["event"] == "export"


def test_hc_pin_006_migration_012_has_exact_parent_and_unique_item_key():
    migration = Path(__file__).parent.parent / "migrations/profile/versions/012_pinboards.py"
    text = migration.read_text(encoding="utf-8")
    assert 'revision: str = "012_pinboards"' in text
    assert 'down_revision: Union[str, None] = "011_care_plan_tasks"' in text
    assert 'sa.UniqueConstraint("pinboard_id", "item_type", "item_id"' in text


@pytest.mark.asyncio
async def test_hc_pin_007_unique_constraint_race_returns_conflict(monkeypatch):
    from sqlalchemy.exc import IntegrityError
    from api.pinboards import PinboardItemCreateRequest, add_pinboard_item

    board = _pinboard()
    document_id = str(uuid.uuid4())
    document = type("Document", (), {"id": document_id, "profile_id": "test-profile"})()
    profile_db = AsyncMock()
    profile_db.add = MagicMock()
    profile_db.execute.side_effect = [
        _Result(one=board), _Result(one=document), _Result(one=None),
    ]
    profile_db.commit.side_effect = IntegrityError("insert", {}, Exception("unique"))
    monkeypatch.setattr("api.pinboards.log_pinboard_event", AsyncMock())

    with pytest.raises(HTTPException) as exc:
        await add_pinboard_item(
            board.id,
            PinboardItemCreateRequest(item_type="document", item_id=document_id),
            _session(), profile_db, AsyncMock(),
        )
    assert exc.value.status_code == 409
    profile_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_hc_pin_008_export_excludes_unverified_source_documents(monkeypatch):
    from api.pinboards import PinboardExportRequest, export_pinboard_packet

    board = _pinboard()
    verified_id = str(uuid.uuid4())
    unverified_id = str(uuid.uuid4())
    items = [
        _item(board.id, item_id=verified_id),
        _item(board.id, item_id=unverified_id),
    ]
    verified = type("Document", (), {
        "id": verified_id,
        "source": "verified-record.pdf",
        "collection_date": datetime(2026, 6, 1, tzinfo=timezone.utc),
        "status": "verified",
    })()
    unverified = type("Document", (), {
        "id": unverified_id,
        "source": "unverified-private-record.pdf",
        "collection_date": datetime(2026, 6, 2, tzinfo=timezone.utc),
        "status": "parsed",
    })()
    profile_db = AsyncMock()
    profile_db.execute.side_effect = [
        _Result(one=board),
        _Result(items=items),
        _Result(items=[verified, unverified]),
    ]
    monkeypatch.setattr("api.pinboards.log_pinboard_event", AsyncMock())
    monkeypatch.setattr(
        "api.pinboards._prune_stale_items",
        AsyncMock(side_effect=lambda _db, current_items, _profile_id: current_items),
    )

    response = await export_pinboard_packet(
        board.id,
        PinboardExportRequest(confirm=True),
        _session(),
        profile_db,
        AsyncMock(),
    )

    assert "verified-record.pdf" in response.markdown
    assert "unverified-private-record.pdf" not in response.markdown


@pytest.mark.asyncio
async def test_hc_pin_009_list_prunes_stale_polymorphic_targets(
    real_profile_db, monkeypatch
):
    from api.pinboards import list_pinboard_items
    from models import PinboardItem

    board = _pinboard()
    stale = _item(board.id, item_type="observation", item_id=str(uuid.uuid4()))
    real_profile_db.add_all([board, stale])
    await real_profile_db.commit()
    monkeypatch.setattr("api.pinboards.log_pinboard_event", AsyncMock())

    response = await list_pinboard_items(
        board.id, _session(), real_profile_db, AsyncMock()
    )

    assert response == []
    remaining = await real_profile_db.execute(
        select(PinboardItem).where(PinboardItem.id == stale.id)
    )
    assert remaining.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_hc_pin_010_export_skips_and_prunes_stale_targets(
    real_profile_db, monkeypatch
):
    from api.pinboards import PinboardExportRequest, export_pinboard_packet
    from models import PinboardItem

    board = _pinboard()
    stale = _item(board.id, item_type="document", item_id=str(uuid.uuid4()))
    real_profile_db.add_all([board, stale])
    await real_profile_db.commit()
    monkeypatch.setattr("api.pinboards.log_pinboard_event", AsyncMock())

    response = await export_pinboard_packet(
        board.id,
        PinboardExportRequest(confirm=True),
        _session(),
        real_profile_db,
        AsyncMock(),
    )

    assert "Source Documents" not in response.section_titles
    remaining = await real_profile_db.execute(
        select(PinboardItem).where(PinboardItem.id == stale.id)
    )
    assert remaining.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_hc_pin_013_export_renders_selected_verified_normal_observation(
    monkeypatch,
):
    from api.pinboards import PinboardExportRequest, export_pinboard_packet

    board = _pinboard()
    observation_id = str(uuid.uuid4())
    items = [
        _item(
            board.id,
            item_type="observation",
            item_id=observation_id,
        )
    ]
    normal = type("Observation", (), {
        "id": observation_id,
        "analyte_canonical": "sodium",
        "analyte_raw": "Sodium",
        "value": 140.0,
        "value_text": None,
        "unit": "mmol/L",
        "ref_low": 135.0,
        "ref_high": 145.0,
        "flag": None,
        "is_abnormal": False,
        "user_verified": True,
        "collected_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
    })()
    profile_db = AsyncMock()
    profile_db.execute.side_effect = [
        _Result(one=board),
        _Result(items=items),
        _Result(items=[normal]),
    ]
    monkeypatch.setattr("api.pinboards.log_pinboard_event", AsyncMock())
    monkeypatch.setattr(
        "api.pinboards._prune_stale_items",
        AsyncMock(side_effect=lambda _db, current_items, _profile_id: current_items),
    )

    response = await export_pinboard_packet(
        board.id,
        PinboardExportRequest(confirm=True),
        _session(),
        profile_db,
        AsyncMock(),
    )

    assert "Selected Lab Results (verified)" in response.section_titles
    assert "sodium: 140.0 mmol/L" in response.markdown


@pytest.mark.asyncio
async def test_hc_pin_014_question_pin_requires_live_source_document(
    real_profile_db,
):
    """A verified entity orphaned by a document delete is not a valid
    question source: its quote is verbatim text of a deleted document."""
    from api.pinboards import PinboardItemCreateRequest, _validate_item_target
    from models.document_category import DocumentEntity

    orphan = DocumentEntity(
        id=str(uuid.uuid4()),
        doc_id=str(uuid.uuid4()),
        category="visit_notes",
        entity_type="medication_change",
        entity_value="start metoprolol 25 mg",
        confidence=0.9,
        quote="Start metoprolol 25 mg",
        verified_by_user=True,
    )
    real_profile_db.add(orphan)
    await real_profile_db.commit()

    with pytest.raises(HTTPException) as exc:
        await _validate_item_target(
            real_profile_db,
            PinboardItemCreateRequest(item_type="question", item_id=orphan.id),
            _session(),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_hc_pin_015_list_prunes_question_pins_of_deleted_documents(
    real_profile_db, monkeypatch
):
    from api.pinboards import list_pinboard_items
    from models import PinboardItem
    from models.document_category import DocumentEntity

    board = _pinboard()
    orphan = DocumentEntity(
        id=str(uuid.uuid4()),
        doc_id=str(uuid.uuid4()),
        category="visit_notes",
        entity_type="medication_change",
        entity_value="start metoprolol 25 mg",
        confidence=0.9,
        quote="Start metoprolol 25 mg",
        verified_by_user=True,
    )
    pin = _item(board.id, item_type="question", item_id=orphan.id)
    real_profile_db.add_all([board, orphan, pin])
    await real_profile_db.commit()
    monkeypatch.setattr("api.pinboards.log_pinboard_event", AsyncMock())

    response = await list_pinboard_items(
        board.id, _session(), real_profile_db, AsyncMock()
    )

    assert response == []
    remaining = await real_profile_db.execute(
        select(PinboardItem).where(PinboardItem.id == pin.id)
    )
    assert remaining.scalar_one_or_none() is None
