"""Tests for GET /documents/{id}/category and GET /documents/{id}/entities endpoints."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.documents import (
    get_document_category,
    get_document_entities,
    DocumentCategoryResponse,
    DocumentEntityResponse,
)
from core.auth import Session
from models.document_category import DocumentCategory, DocumentEntity


class _ScalarResult:
    def __init__(self, one: object = None, all_items: list | None = None):
        self._one = one
        self._all_items = all_items or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return self

    def all(self):
        return self._all_items


def _make_session(profile_id: str = "test-profile") -> Session:
    from datetime import timedelta
    return Session(
        profile_id=profile_id,
        profile_name="Test Profile",
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )


def _make_document(doc_id: str, profile_id: str = "test-profile") -> MagicMock:
    doc = MagicMock()
    doc.id = doc_id
    doc.profile_id = profile_id
    return doc


class TestGetDocumentCategory:
    @pytest.mark.asyncio
    async def test_returns_category_when_exists(self) -> None:
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        cat = DocumentCategory(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            category="imaging",
            confidence=0.95,
            classified_by="rule",
        )

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ScalarResult(one=doc)
            return _ScalarResult(one=cat)

        mock_db = AsyncMock()
        mock_db.execute = mock_execute

        session = _make_session()
        result = await get_document_category(doc_id, session, mock_db)

        assert isinstance(result, DocumentCategoryResponse)
        assert result.category == "imaging"
        assert result.confidence == 0.95
        assert result.doc_id == doc_id

    @pytest.mark.asyncio
    async def test_404_when_document_not_found(self) -> None:
        doc_id = str(uuid.uuid4())

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_ScalarResult(one=None))

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_document_category(doc_id, _make_session(), mock_db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_404_when_no_category(self) -> None:
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ScalarResult(one=doc)
            return _ScalarResult(one=None)

        mock_db = AsyncMock()
        mock_db.execute = mock_execute

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_document_category(doc_id, _make_session(), mock_db)
        assert exc_info.value.status_code == 404


    @pytest.mark.asyncio
    async def test_403_when_wrong_profile(self) -> None:
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id, profile_id="other-profile")

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_ScalarResult(one=doc))

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_document_category(doc_id, _make_session("test-profile"), mock_db)
        assert exc_info.value.status_code == 403


class TestGetDocumentEntities:
    @pytest.mark.asyncio
    async def test_returns_entities_list(self) -> None:
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent1 = DocumentEntity(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            category="imaging",
            entity_type="modality",
            entity_value="MRI",
            confidence=0.95,
            source_page=None,
        )
        ent2 = DocumentEntity(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            category="imaging",
            entity_type="body_region",
            entity_value="brain",
            confidence=0.9,
            source_page=1,
        )

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ScalarResult(one=doc)
            return _ScalarResult(all_items=[ent1, ent2])

        mock_db = AsyncMock()
        mock_db.execute = mock_execute

        result = await get_document_entities(doc_id, _make_session(), mock_db)
        assert len(result) == 2
        assert result[0].entity_type == "modality"
        assert result[1].entity_type == "body_region"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_entities(self) -> None:
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ScalarResult(one=doc)
            return _ScalarResult(all_items=[])

        mock_db = AsyncMock()
        mock_db.execute = mock_execute

        result = await get_document_entities(doc_id, _make_session(), mock_db)
        assert result == []

    @pytest.mark.asyncio
    async def test_404_when_document_not_found(self) -> None:
        doc_id = str(uuid.uuid4())

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_ScalarResult(one=None))

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_document_entities(doc_id, _make_session(), mock_db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_403_when_wrong_profile(self) -> None:
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id, profile_id="other-profile")

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_ScalarResult(one=doc))

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_document_entities(doc_id, _make_session("test-profile"), mock_db)
        assert exc_info.value.status_code == 403
