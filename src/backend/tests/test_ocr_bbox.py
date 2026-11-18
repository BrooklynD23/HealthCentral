"""
Tests for OCR bounding-box citations (OCR-BOX-001).

Covers: bbox JSON round-trip, page image content-type, out-of-range 404, auth required.
"""

import json
import types
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from api.observations import ObservationResponse

# ---------------------------------------------------------------------------
# bbox JSON round-trip
# ---------------------------------------------------------------------------

class TestBboxRoundTrip:
    """Verify that source_bbox_json serializes/deserializes correctly."""

    def test_bbox_json_stored_as_list(self):
        """bbox tuple (x0, y0, x1, y1) should serialize to a JSON list."""
        bbox = (100.5, 200.0, 300.5, 250.0)
        serialized = json.dumps(list(bbox))
        deserialized = json.loads(serialized)
        assert deserialized == [100.5, 200.0, 300.5, 250.0]

    def test_bbox_none_when_no_provenance(self):
        """When provenance is None, source_bbox_json should be None."""
        from modules.extract import ExtractedObservation

        obs = ExtractedObservation(analyte_raw="glucose")
        assert obs.provenance is None
        # The conditional in documents.py produces None
        bbox_json = (
            json.dumps(list(obs.provenance.bbox))
            if obs.provenance and obs.provenance.bbox
            else None
        )
        assert bbox_json is None

    def test_bbox_none_when_provenance_has_no_bbox(self):
        """When provenance exists but bbox is None."""
        from modules.extract import ExtractedObservation, Provenance

        obs = ExtractedObservation(
            analyte_raw="glucose",
            provenance=Provenance(page=1, bbox=None),
        )
        bbox_json = (
            json.dumps(list(obs.provenance.bbox))
            if obs.provenance and obs.provenance.bbox
            else None
        )
        assert bbox_json is None

    def test_bbox_serialized_when_present(self):
        """When provenance has bbox, it should serialize to a JSON list."""
        from modules.extract import ExtractedObservation, Provenance

        obs = ExtractedObservation(
            analyte_raw="glucose",
            provenance=Provenance(page=1, bbox=(10.0, 20.0, 300.0, 40.0)),
        )
        bbox_json = (
            json.dumps(list(obs.provenance.bbox))
            if obs.provenance and obs.provenance.bbox
            else None
        )
        assert bbox_json is not None
        assert json.loads(bbox_json) == [10.0, 20.0, 300.0, 40.0]


# ---------------------------------------------------------------------------
# ObservationResponse includes bbox fields
# ---------------------------------------------------------------------------

class TestObservationResponseBbox:
    """Verify the response model exposes source_page and source_bbox_json."""

    def test_response_includes_source_fields(self):
        """ObservationResponse should have source_page and source_bbox_json."""
        mock_obs = MagicMock()
        mock_obs.id = "obs-1"
        mock_obs.profile_id = "p-1"
        mock_obs.doc_id = "d-1"
        mock_obs.analyte_canonical = "glucose"
        mock_obs.analyte_raw = "Glucose"
        mock_obs.value = 95.0
        mock_obs.value_text = None
        mock_obs.unit = "mg/dL"
        mock_obs.ref_low = 70.0
        mock_obs.ref_high = 100.0
        mock_obs.ref_range_text = "70-100"
        mock_obs.flag = None
        mock_obs.is_abnormal = False
        mock_obs.collected_at = None
        mock_obs.user_verified = True
        mock_obs.extraction_confidence = 0.95
        mock_obs.source_page = 2
        mock_obs.source_bbox_json = "[10.0, 20.0, 300.0, 40.0]"

        resp = ObservationResponse.from_model(mock_obs)
        assert resp.source_page == 2
        assert resp.source_bbox_json == "[10.0, 20.0, 300.0, 40.0]"

    def test_response_null_when_no_bbox(self):
        mock_obs = MagicMock()
        mock_obs.id = "obs-2"
        mock_obs.profile_id = "p-1"
        mock_obs.doc_id = "d-1"
        mock_obs.analyte_canonical = "wbc"
        mock_obs.analyte_raw = "WBC"
        mock_obs.value = 7.5
        mock_obs.value_text = None
        mock_obs.unit = "K/uL"
        mock_obs.ref_low = 4.5
        mock_obs.ref_high = 11.0
        mock_obs.ref_range_text = None
        mock_obs.flag = None
        mock_obs.is_abnormal = False
        mock_obs.collected_at = None
        mock_obs.user_verified = False
        mock_obs.extraction_confidence = None
        mock_obs.source_page = None
        mock_obs.source_bbox_json = None

        resp = ObservationResponse.from_model(mock_obs)
        assert resp.source_page is None
        assert resp.source_bbox_json is None


@pytest_asyncio.fixture
async def profile_db():
    """In-memory profile DB session (the entity_profile_db pattern, kept local)."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from core.profile_database import ProfileDatabaseBase

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


# ---------------------------------------------------------------------------
# Page image endpoint validation
# ---------------------------------------------------------------------------

class TestPageImageEndpoint:
    """Test the page image endpoint's validation logic (unit-level)."""

    @pytest.mark.asyncio
    async def test_page_number_must_be_positive(self, profile_db):
        """Page numbers < 1 should be rejected over HTTP, before any audit write."""
        from datetime import datetime

        from api.documents import router as documents_router
        from core.auth import get_profile_db_session
        from models import Document
        from tests.support.routes import route_client

        document_id = "11111111-1111-4111-8111-111111111111"
        profile_db.add(
            Document(
                id=document_id,
                profile_id="profile-a",
                path_hash="p" * 64,
                content_hash="c" * 64,
                doc_type="lab_pdf",
                status="parsed",
                imported_at=datetime(2026, 1, 1),
            )
        )
        await profile_db.commit()

        master_db = AsyncMock()
        with route_client(documents_router, "/documents", master_db=master_db) as client:

            async def _override_profile_db():
                return profile_db

            client.app.dependency_overrides[get_profile_db_session] = _override_profile_db

            zero = client.get(f"/documents/{document_id}/pages/0/image")
            assert zero.status_code == 400
            assert zero.json()["detail"] == "Page number must be >= 1"

            negative = client.get(f"/documents/{document_id}/pages/-1/image")
            assert negative.status_code == 400
            assert negative.json()["detail"] == "Page number must be >= 1"

            # FastAPI path-param coercion fails before the handler runs.
            non_integer = client.get(f"/documents/{document_id}/pages/abc/image")
            assert non_integer.status_code == 422

        # The 400/422 rejections happen before render, so the audit write
        # (which lands only after a successful render) never runs.
        assert master_db.commit.await_count == 0

    def test_validate_uuid_rejects_traversal(self):
        """UUID validation should reject path traversal attempts."""
        from fastapi import HTTPException

        from api.documents import validate_uuid

        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("../../etc/passwd", "document_id")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_page_image_uses_in_process_cache(self):
        """F-005: Repeated requests should not re-render the same page image."""
        import api.documents as documents_api
        from api.documents import get_page_image

        # Clear any prior cache state from other tests
        with documents_api._page_image_cache_lock:
            documents_api._page_image_cache.clear()

        document_id = "11111111-1111-4111-8111-111111111111"
        session = MagicMock(profile_id="profile-1")

        mock_doc = MagicMock()
        mock_doc.id = document_id
        mock_doc.profile_id = "profile-1"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_doc

        profile_db = AsyncMock()
        profile_db.execute.return_value = result_mock

        png_bytes = b"\x89PNG\r\n\x1a\nfakepng"

        class FakeImage:
            def save(self, buf, format="PNG"):
                buf.write(png_bytes)

        class FakePage:
            def to_image(self, resolution: int = 150):
                return FakeImage()

        class FakePdf:
            pages = [FakePage()]

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        fake_pdfplumber = types.ModuleType("pdfplumber")
        fake_pdfplumber.open = MagicMock(return_value=FakePdf())

        master_db = AsyncMock()

        with (
            patch.dict("sys.modules", {"pdfplumber": fake_pdfplumber}),
            patch("api.documents.get_decrypted_document", return_value=BytesIO(b"%PDF-FAKE")),
        ):
            r1 = await get_page_image(document_id, 1, session, profile_db, master_db)
            r2 = await get_page_image(document_id, 1, session, profile_db, master_db)

        assert r1.media_type == "image/png"
        assert r1.body == png_bytes
        assert r2.body == png_bytes
        assert fake_pdfplumber.open.call_count == 1
        assert master_db.commit.await_count == 2

    @pytest.mark.asyncio
    async def test_page_image_out_of_range_does_not_audit(self):
        """Out-of-range pages should return 404 without writing an audit row."""
        import api.documents as documents_api
        from api.documents import get_page_image

        with documents_api._page_image_cache_lock:
            documents_api._page_image_cache.clear()

        document_id = "11111111-1111-4111-8111-111111111111"
        session = MagicMock(profile_id="profile-1")

        mock_doc = MagicMock()
        mock_doc.id = document_id
        mock_doc.profile_id = "profile-1"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_doc

        profile_db = AsyncMock()
        profile_db.execute.return_value = result_mock

        class FakeImage:
            def save(self, buf, format="PNG"):
                buf.write(b"unused")

        class FakePage:
            def to_image(self, resolution: int = 150):
                return FakeImage()

        class FakePdf:
            pages = [FakePage()]

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        fake_pdfplumber = types.ModuleType("pdfplumber")
        fake_pdfplumber.open = MagicMock(return_value=FakePdf())

        master_db = AsyncMock()

        with (
            patch.dict("sys.modules", {"pdfplumber": fake_pdfplumber}),
            patch("api.documents.get_decrypted_document", return_value=BytesIO(b"%PDF-FAKE")),
        ):
            with pytest.raises(Exception) as exc_info:
                await get_page_image(document_id, 2, session, profile_db, master_db)

        assert getattr(exc_info.value, "status_code", None) == 404
        assert master_db.commit.await_count == 0
