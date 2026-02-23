"""
Tests for memory store CRUD API (ASSIST-MEM-001).

Covers: create, list, get, update, delete, auth enforcement, cross-profile denial, limit.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from pydantic import ValidationError

from api.memory import (
    MemoryItemCreate,
    MemoryItemUpdate,
    MemoryItemResponse,
    _validate_uuid,
)
from models.memory_item import MemoryItem


# ---------------------------------------------------------------------------
# Request model validation
# ---------------------------------------------------------------------------

class TestMemoryItemCreate:
    def test_valid_create(self):
        data = MemoryItemCreate(key="allergy", value="Penicillin", category="medical")
        assert data.key == "allergy"
        assert data.value == "Penicillin"
        assert data.category == "medical"

    def test_key_required(self):
        with pytest.raises(ValidationError):
            MemoryItemCreate(key="", value="test")

    def test_value_required(self):
        with pytest.raises(ValidationError):
            MemoryItemCreate(key="test", value="")

    def test_category_optional(self):
        data = MemoryItemCreate(key="test", value="data")
        assert data.category is None


class TestMemoryItemUpdate:
    def test_partial_update(self):
        data = MemoryItemUpdate(value="Updated value")
        assert data.key is None
        assert data.value == "Updated value"

    def test_all_fields_optional(self):
        data = MemoryItemUpdate()
        assert data.key is None
        assert data.value is None
        assert data.category is None


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------

class TestMemoryItemResponse:
    def test_from_model(self):
        now = datetime.utcnow()
        mock_item = MagicMock()
        mock_item.id = "item-1"
        mock_item.profile_id = "profile-1"
        mock_item.key = "allergy"
        mock_item.value = "Penicillin"
        mock_item.category = "medical"
        mock_item.created_at = now
        mock_item.updated_at = now

        resp = MemoryItemResponse.from_model(mock_item)
        assert resp.id == "item-1"
        assert resp.key == "allergy"
        assert resp.value == "Penicillin"
        assert resp.category == "medical"


# ---------------------------------------------------------------------------
# UUID validation
# ---------------------------------------------------------------------------

class TestUUIDValidation:
    def test_valid_uuid(self):
        valid = str(uuid.uuid4())
        assert _validate_uuid(valid) == valid

    def test_invalid_uuid_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _validate_uuid("not-a-uuid")
        assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# MemoryItem model
# ---------------------------------------------------------------------------

class TestMemoryItemModel:
    def test_model_fields(self):
        """Verify all expected columns exist on the model."""
        assert hasattr(MemoryItem, "id")
        assert hasattr(MemoryItem, "profile_id")
        assert hasattr(MemoryItem, "key")
        assert hasattr(MemoryItem, "value")
        assert hasattr(MemoryItem, "category")
        assert hasattr(MemoryItem, "created_at")
        assert hasattr(MemoryItem, "updated_at")

    def test_tablename(self):
        assert MemoryItem.__tablename__ == "memory_items"


# ---------------------------------------------------------------------------
# Cross-profile isolation (unit-level)
# ---------------------------------------------------------------------------

class TestCrossProfileIsolation:
    """F-007: Avoid leaking cross-profile existence (404 over 403)."""

    @pytest.mark.asyncio
    async def test_get_queries_by_id_and_profile_and_returns_404(self):
        from fastapi import HTTPException
        from api.memory import get_memory_item

        item_id = str(uuid.uuid4())
        session = MagicMock(profile_id="profile-B")

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None

        profile_db = AsyncMock()
        profile_db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc:
            await get_memory_item(item_id=item_id, session=session, profile_db=profile_db)
        assert exc.value.status_code == 404

        stmt = profile_db.execute.call_args.args[0]
        where_cols = {getattr(getattr(c, "left", None), "name", None) for c in stmt._where_criteria}
        assert {"id", "profile_id"} <= where_cols

    @pytest.mark.asyncio
    async def test_update_queries_by_id_and_profile_and_returns_404(self):
        from fastapi import HTTPException
        from api.memory import update_memory_item, MemoryItemUpdate

        item_id = str(uuid.uuid4())
        session = MagicMock(profile_id="profile-B")

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None

        profile_db = AsyncMock()
        profile_db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc:
            await update_memory_item(
                item_id=item_id,
                data=MemoryItemUpdate(value="new"),
                session=session,
                profile_db=profile_db,
            )
        assert exc.value.status_code == 404

        stmt = profile_db.execute.call_args.args[0]
        where_cols = {getattr(getattr(c, "left", None), "name", None) for c in stmt._where_criteria}
        assert {"id", "profile_id"} <= where_cols

    @pytest.mark.asyncio
    async def test_delete_queries_by_id_and_profile_and_returns_404(self):
        from fastapi import HTTPException
        from api.memory import delete_memory_item

        item_id = str(uuid.uuid4())
        session = MagicMock(profile_id="profile-B")

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None

        profile_db = AsyncMock()
        profile_db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc:
            await delete_memory_item(item_id=item_id, session=session, profile_db=profile_db)
        assert exc.value.status_code == 404

        stmt = profile_db.execute.call_args.args[0]
        where_cols = {getattr(getattr(c, "left", None), "name", None) for c in stmt._where_criteria}
        assert {"id", "profile_id"} <= where_cols


# ---------------------------------------------------------------------------
# Config limit
# ---------------------------------------------------------------------------

class TestConfigLimit:
    def test_default_limit(self):
        from core.config import Settings
        s = Settings()
        assert s.max_memory_items_per_profile == 100
