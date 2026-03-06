"""Tests for document import classification integration.

Verifies that classify_document is called during import and that
DocumentCategory + DocumentEntity records are persisted correctly.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.document_classifier import classify_document, ClassificationResult
from modules.extract_imaging import extract_imaging_entities
from modules.extract_pathology import extract_pathology_entities
from modules.extract_visit_notes import extract_visit_note_entities


# ---------------------------------------------------------------------------
# Unit tests: classifier produces correct categories for full documents
# ---------------------------------------------------------------------------


class TestClassificationIntegration:
    def test_imaging_report_classifies_correctly(self) -> None:
        text = """RADIOLOGY REPORT

Patient: John Doe
Date: 03/04/2026
Ordering Provider: Dr. Smith

MRI of lumbar spine without contrast

TECHNIQUE: Multiplanar multisequence MRI of the lumbar spine.

FINDINGS:
Normal alignment. No fracture or subluxation.
Disc heights are maintained. No significant disc herniation.
The spinal canal is patent. No spinal stenosis.

IMPRESSION:
Normal MRI of the lumbar spine. No acute abnormality.
"""
        result = classify_document(text)
        assert result.category == "imaging"
        assert result.confidence >= 0.9

    def test_pathology_report_classifies_correctly(self) -> None:
        text = """SURGICAL PATHOLOGY REPORT

Specimen: Left breast, needle core biopsy
Site: Left breast, 2 o'clock

DIAGNOSIS: Invasive ductal carcinoma, grade 2
Nottingham grade: 2/3 (tubules 2, nuclei 2, mitoses 1)
MARGINS: N/A (core biopsy)

Signed by: Dr. Jane Pathologist
"""
        result = classify_document(text)
        assert result.category == "pathology"
        assert result.confidence >= 0.9

    def test_visit_notes_classifies_correctly(self) -> None:
        text = """PROGRESS NOTE

Chief Complaint: Follow-up for diabetes management
History of Present Illness: Patient returns for 3-month follow-up.

VITAL SIGNS: BP 128/82, HR 76, Temp 98.4
ASSESSMENT: Type 2 DM, well controlled on current regimen.
PLAN: Continue metformin 1000mg BID. Recheck A1c in 3 months.

Provider: Dr. Smith
"""
        result = classify_document(text)
        assert result.category == "visit_notes"
        assert result.confidence >= 0.8


# ---------------------------------------------------------------------------
# Integration: _classify_and_extract_entities wiring
# ---------------------------------------------------------------------------


class TestClassifyAndExtractEntities:
    """Test that the classification pipeline correctly persists records."""

    @pytest.mark.asyncio
    async def test_imaging_creates_category_and_entities(self) -> None:
        """Imaging text should produce a DocumentCategory + entities."""
        from api.documents import _classify_and_extract_entities

        imaging_text = (
            "RADIOLOGY REPORT\n"
            "MRI brain without contrast\n"
            "FINDINGS: No acute intracranial abnormality.\n"
            "IMPRESSION: Normal MRI brain.\n"
        )

        added_objects: list[object] = []

        mock_db = AsyncMock()
        mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        with patch("api.documents._get_document_text", return_value=imaging_text):
            await _classify_and_extract_entities(
                profile_db=mock_db,
                profile_id="test-profile",
                doc_id="test-doc-id",
                doc_type="lab_pdf",
            )

        mock_db.commit.assert_awaited_once()

        # Should have 1 DocumentCategory + N entities
        from models.document_category import DocumentCategory, DocumentEntity

        categories = [o for o in added_objects if isinstance(o, DocumentCategory)]
        entities = [o for o in added_objects if isinstance(o, DocumentEntity)]

        assert len(categories) == 1
        assert categories[0].category == "imaging"
        assert categories[0].doc_id == "test-doc-id"
        assert categories[0].confidence >= 0.9
        assert len(entities) > 0
        assert all(e.category == "imaging" for e in entities)

    @pytest.mark.asyncio
    async def test_pathology_creates_category_and_entities(self) -> None:
        from api.documents import _classify_and_extract_entities

        text = (
            "SURGICAL PATHOLOGY REPORT\n"
            "Specimen: Biopsy of colon\n"
            "DIAGNOSIS: Adenocarcinoma, moderately differentiated.\n"
            "MARGINS: Negative\n"
        )

        added_objects: list[object] = []
        mock_db = AsyncMock()
        mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        with patch("api.documents._get_document_text", return_value=text):
            await _classify_and_extract_entities(
                profile_db=mock_db,
                profile_id="test-profile",
                doc_id="test-doc-id",
                doc_type="lab_pdf",
            )

        from models.document_category import DocumentCategory, DocumentEntity

        categories = [o for o in added_objects if isinstance(o, DocumentCategory)]
        entities = [o for o in added_objects if isinstance(o, DocumentEntity)]

        assert len(categories) == 1
        assert categories[0].category == "pathology"
        assert len(entities) > 0

    @pytest.mark.asyncio
    async def test_unknown_text_creates_no_records(self) -> None:
        from api.documents import _classify_and_extract_entities

        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        with patch("api.documents._get_document_text", return_value="Random text with no keywords."):
            await _classify_and_extract_entities(
                profile_db=mock_db,
                profile_id="test-profile",
                doc_id="test-doc-id",
                doc_type="lab_pdf",
            )

        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_empty_text_creates_no_records(self) -> None:
        from api.documents import _classify_and_extract_entities

        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        with patch("api.documents._get_document_text", return_value=""):
            await _classify_and_extract_entities(
                profile_db=mock_db,
                profile_id="test-profile",
                doc_id="test-doc-id",
                doc_type="lab_pdf",
            )

        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_text_extraction_failure_is_nonfatal(self) -> None:
        from api.documents import _classify_and_extract_entities

        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        with patch("api.documents._get_document_text", side_effect=RuntimeError("decrypt fail")):
            # Should not raise
            await _classify_and_extract_entities(
                profile_db=mock_db,
                profile_id="test-profile",
                doc_id="test-doc-id",
                doc_type="lab_pdf",
            )

        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_lab_category_creates_category_but_no_entities(self) -> None:
        """Lab docs classify as 'lab' but have no dedicated extractor (handled by extract module)."""
        from api.documents import _classify_and_extract_entities

        text = "LABORATORY RESULTS\nGlucose: 95 mg/dL\nReference Range: 70-100 mg/dL\nCBC results normal."

        added_objects: list[object] = []
        mock_db = AsyncMock()
        mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        with patch("api.documents._get_document_text", return_value=text):
            await _classify_and_extract_entities(
                profile_db=mock_db,
                profile_id="test-profile",
                doc_id="test-doc-id",
                doc_type="lab_pdf",
            )

        from models.document_category import DocumentCategory, DocumentEntity

        categories = [o for o in added_objects if isinstance(o, DocumentCategory)]
        entities = [o for o in added_objects if isinstance(o, DocumentEntity)]

        assert len(categories) == 1
        assert categories[0].category == "lab"
        # Lab has no dedicated entity extractor — entities come from extract module
        assert len(entities) == 0


# ---------------------------------------------------------------------------
# Regression: scanned PDF / image classification paths
# ---------------------------------------------------------------------------


class TestScannedAndImageClassification:
    """Verify _get_document_text branches correctly by doc_type."""

    @pytest.mark.asyncio
    async def test_scanned_pdf_uses_pre_extracted_text(self) -> None:
        """lab_pdf_scanned should use pre_extracted_text and classify the result."""
        from api.documents import _classify_and_extract_entities

        imaging_text = (
            "RADIOLOGY REPORT\n"
            "CT chest with contrast\n"
            "FINDINGS: No pulmonary embolism.\n"
            "IMPRESSION: Negative for PE.\n"
        )

        added_objects: list[object] = []
        mock_db = AsyncMock()
        mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        await _classify_and_extract_entities(
            profile_db=mock_db,
            profile_id="test-profile",
            doc_id="scanned-doc",
            doc_type="lab_pdf_scanned",
            pre_extracted_text=imaging_text,
        )

        from models.document_category import DocumentCategory

        categories = [o for o in added_objects if isinstance(o, DocumentCategory)]
        assert len(categories) == 1
        assert categories[0].category == "imaging"

    @pytest.mark.asyncio
    async def test_image_uses_pre_extracted_text(self) -> None:
        """lab_image should use pre_extracted_text and classify the result."""
        from api.documents import _classify_and_extract_entities

        pathology_text = (
            "SURGICAL PATHOLOGY REPORT\n"
            "Specimen: Skin biopsy\n"
            "DIAGNOSIS: Basal cell carcinoma.\n"
            "MARGINS: Clear\n"
        )

        added_objects: list[object] = []
        mock_db = AsyncMock()
        mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        await _classify_and_extract_entities(
            profile_db=mock_db,
            profile_id="test-profile",
            doc_id="image-doc",
            doc_type="lab_image",
            pre_extracted_text=pathology_text,
        )

        from models.document_category import DocumentCategory

        categories = [o for o in added_objects if isinstance(o, DocumentCategory)]
        assert len(categories) == 1
        assert categories[0].category == "pathology"

    @pytest.mark.asyncio
    async def test_no_pre_extracted_text_falls_back_to_get_document_text(self) -> None:
        """When pre_extracted_text is None, _get_document_text is called as fallback."""
        from api.documents import _classify_and_extract_entities

        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        with patch(
            "api.documents._get_document_text", return_value=""
        ) as mock_get_text:
            await _classify_and_extract_entities(
                profile_db=mock_db,
                profile_id="test-profile",
                doc_id="scanned-doc",
                doc_type="lab_pdf_scanned",
            )
            mock_get_text.assert_called_once()

        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# Regression: non-fatal failure handling
# ---------------------------------------------------------------------------


class TestNonFatalFailures:
    """Verify that classification/entity/persistence failures never propagate."""

    @pytest.mark.asyncio
    async def test_classifier_exception_is_swallowed(self) -> None:
        """If classify_document raises, _classify_and_extract_entities returns silently."""
        from api.documents import _classify_and_extract_entities

        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        with patch(
            "api.documents._get_document_text", return_value="RADIOLOGY REPORT\nMRI brain"
        ), patch(
            "api.documents.classify_document", side_effect=RuntimeError("classifier boom")
        ):
            await _classify_and_extract_entities(
                profile_db=mock_db,
                profile_id="test-profile",
                doc_id="test-doc",
                doc_type="lab_pdf",
            )

        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_extractor_failure_still_persists_category(self) -> None:
        """If entity extractor raises, the category should still be persisted."""
        from api.documents import _classify_and_extract_entities

        imaging_text = (
            "RADIOLOGY REPORT\n"
            "MRI brain without contrast\n"
            "FINDINGS: Normal.\n"
            "IMPRESSION: Normal MRI brain.\n"
        )

        added_objects: list[object] = []
        mock_db = AsyncMock()
        mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        with patch(
            "api.documents._get_document_text", return_value=imaging_text
        ), patch.dict(
            "api.documents._CATEGORY_EXTRACTORS",
            {"imaging": MagicMock(side_effect=RuntimeError("extractor boom"))},
        ):
            await _classify_and_extract_entities(
                profile_db=mock_db,
                profile_id="test-profile",
                doc_id="test-doc",
                doc_type="lab_pdf",
            )

        from models.document_category import DocumentCategory, DocumentEntity

        categories = [o for o in added_objects if isinstance(o, DocumentCategory)]
        entities = [o for o in added_objects if isinstance(o, DocumentEntity)]

        # Category should still be persisted even though extractor failed
        assert len(categories) == 1
        assert categories[0].category == "imaging"
        assert len(entities) == 0
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_commit_failure_triggers_rollback(self) -> None:
        """If profile_db.commit() raises, rollback should be called and no exception propagated."""
        from api.documents import _classify_and_extract_entities

        imaging_text = (
            "RADIOLOGY REPORT\n"
            "CT abdomen\n"
            "FINDINGS: No abnormality.\n"
            "IMPRESSION: Normal CT.\n"
        )

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock(side_effect=RuntimeError("commit boom"))
        mock_db.rollback = AsyncMock()

        with patch("api.documents._get_document_text", return_value=imaging_text):
            # Should not raise
            await _classify_and_extract_entities(
                profile_db=mock_db,
                profile_id="test-profile",
                doc_id="test-doc",
                doc_type="lab_pdf",
            )

        mock_db.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_malformed_entity_payload_is_swallowed(self) -> None:
        """If extractor returns bad entity dicts, persistence should not crash the import."""
        from api.documents import _classify_and_extract_entities

        imaging_text = (
            "RADIOLOGY REPORT\n"
            "MRI spine\n"
            "FINDINGS: Disc herniation.\n"
            "IMPRESSION: L4-L5 disc herniation.\n"
        )

        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        bad_entities = [{"wrong_key": "value"}]  # Missing entity_type, entity_value, confidence

        with patch(
            "api.documents._get_document_text", return_value=imaging_text
        ), patch.dict(
            "api.documents._CATEGORY_EXTRACTORS",
            {"imaging": MagicMock(return_value=bad_entities)},
        ):
            # Should not raise even with malformed entity payloads
            await _classify_and_extract_entities(
                profile_db=mock_db,
                profile_id="test-profile",
                doc_id="test-doc",
                doc_type="lab_pdf",
            )

        # The KeyError on ent["entity_type"] should be caught by Stage 4 try/except
        # and trigger a rollback instead of crashing
        mock_db.rollback.assert_awaited_once()
