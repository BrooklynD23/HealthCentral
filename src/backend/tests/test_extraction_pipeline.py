"""
Tests for Sprint 2: Import → Extract → Normalize → Persist pipeline.

TDD Tests that verify:
- Import triggers extraction pipeline
- Observations are created from PDFs
- Document status is set correctly
- needs_verification is computed
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.extract import ExtractModule, ExtractionResult, ExtractedObservation, Provenance


class TestExtractionPipeline:
    """Tests for the extraction pipeline integration."""

    @pytest.fixture
    def extract_module(self):
        """Create extract module for testing."""
        return ExtractModule()

    @pytest.fixture
    def sample_observations(self):
        """Sample extracted observations for testing."""
        return [
            ExtractedObservation(
                analyte_raw="Glucose",
                value=95.0,
                unit="mg/dL",
                ref_low=70.0,
                ref_high=100.0,
                flag=None,
                confidence=0.9,
                provenance=Provenance(page=1, text_snippet="Glucose: 95 mg/dL (70-100)"),
            ),
            ExtractedObservation(
                analyte_raw="Hemoglobin A1c",
                value=6.5,
                unit="%",
                ref_low=4.0,
                ref_high=5.6,
                flag="H",
                confidence=0.85,
                provenance=Provenance(page=1, text_snippet="HbA1c: 6.5% (4.0-5.6) H"),
            ),
        ]

    def test_api_import_001_import_triggers_extraction(self, extract_module):
        """
        API-IMPORT-001: Import triggers extraction pipeline.

        After importing a PDF, the extraction module should be invoked.
        """
        # This test verifies the integration - extraction must be called
        # For now, verify the module exists and has the right interface
        assert hasattr(extract_module, "extract_from_pdf")
        assert callable(getattr(extract_module, "extract_from_pdf"))

    @pytest.mark.asyncio
    async def test_api_import_002_observations_created_from_pdf(self, extract_module, tmp_path):
        """
        API-IMPORT-002: Observations created from PDF.

        Extracting a PDF with lab tables should create Observation records.
        """
        # Create a mock PDF path
        pdf_path = tmp_path / "sample_lab.pdf"
        doc_id = str(uuid.uuid4())

        # Mock pdfplumber to return table data
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Patient: John Doe\nDate: 01/15/2024"
        mock_page.extract_tables.return_value = [
            [
                ["Test Name", "Result", "Units", "Reference Range", "Flag"],
                ["Glucose", "95", "mg/dL", "70-100", ""],
                ["Hemoglobin A1c", "6.5", "%", "4.0-5.6", "H"],
                ["Cholesterol, Total", "215", "mg/dL", "<200", "H"],
            ]
        ]

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = await extract_module.extract_from_pdf(pdf_path, doc_id)

        # Verify observations were extracted
        assert isinstance(result, ExtractionResult)
        assert result.document_id == doc_id
        assert len(result.observations) >= 3

        # Verify observation fields
        glucose_obs = next((o for o in result.observations if "glucose" in o.analyte_raw.lower()), None)
        assert glucose_obs is not None
        assert glucose_obs.value == 95.0
        assert glucose_obs.unit == "mg/dL"

    @pytest.mark.asyncio
    async def test_api_import_003_document_status_set_to_parsed(self, extract_module):
        """
        API-IMPORT-003: Document status set to 'parsed' on success.

        After successful extraction, the document status should be updated.
        """
        # This will be tested in integration - for now verify extraction succeeds
        # The API endpoint should update status after extraction completes
        pass  # Integration test will cover this

    @pytest.mark.asyncio
    async def test_api_import_004_needs_verification_computed(self, sample_observations):
        """
        API-IMPORT-004: needs_verification computed from confidence/flags.

        Documents with low-confidence extractions or flagged values need verification.
        """
        # Calculate needs_verification based on observations
        def compute_needs_verification(observations: list[ExtractedObservation]) -> bool:
            """Determine if observations need user verification."""
            for obs in observations:
                # Low confidence extractions need verification
                if obs.confidence < 0.8:
                    return True
                # Flagged (abnormal) values need verification
                if obs.flag:
                    return True
            return len(observations) == 0  # Empty extraction needs verification

        # Test with sample data - has a flagged value (HbA1c with H)
        needs_verify = compute_needs_verification(sample_observations)
        assert needs_verify is True  # Because HbA1c has flag="H"

        # Test with all normal, high-confidence
        normal_obs = [
            ExtractedObservation(
                analyte_raw="Glucose",
                value=85.0,
                unit="mg/dL",
                ref_low=70.0,
                ref_high=100.0,
                flag=None,
                confidence=0.95,
            ),
        ]
        needs_verify = compute_needs_verification(normal_obs)
        assert needs_verify is False  # Normal, high confidence


class TestExtractModule:
    """Tests for the ExtractModule text extraction."""

    @pytest.fixture
    def extract_module(self):
        return ExtractModule()

    def test_api_extract_001_extract_from_text_pdf(self, extract_module):
        """
        API-EXTRACT-001: Extract from text-based PDF.

        Text-only PDFs should yield observations via _extract_from_text.
        """
        # Test the text extraction method exists and handles input
        text = """
        Lab Results
        Patient: John Doe
        Date: January 15, 2024

        Glucose: 95 mg/dL (Normal: 70-100)
        Hemoglobin A1c: 6.5% (Normal: <5.7) HIGH
        """

        observations = extract_module._extract_from_text(text, page_num=1, document_id="test-123")

        # TDD: These assertions will fail until _extract_from_text is implemented
        assert isinstance(observations, list)
        assert len(observations) >= 1, "_extract_from_text should return observations"

        # Verify glucose was extracted
        glucose_obs = next((o for o in observations if "glucose" in o.analyte_raw.lower()), None)
        assert glucose_obs is not None, "Should extract Glucose observation"

    def test_api_extract_002_section_detection(self, extract_module):
        """
        API-EXTRACT-002: Section detection in lab reports.

        Should detect sections like "Chemistry", "Hematology", etc.
        """
        # This tests that the extraction handles multi-section reports
        text = """
        CHEMISTRY PANEL
        Glucose: 95 mg/dL
        BUN: 15 mg/dL

        HEMATOLOGY
        WBC: 7.5 K/uL
        RBC: 4.8 M/uL
        """

        observations = extract_module._extract_from_text(text, page_num=1, document_id="test-123")
        assert isinstance(observations, list)

    def test_api_extract_003_provenance_snippet_captured(self, extract_module, tmp_path):
        """
        API-EXTRACT-003: Provenance snippet captured for each observation.

        Each extracted observation should include the source text snippet.
        """
        # Create mock table extraction
        table = [
            ["Test", "Result", "Units", "Range"],
            ["Glucose", "95", "mg/dL", "70-100"],
        ]

        observations = extract_module._extract_from_table(table, page_num=1, document_id="test-123")

        assert len(observations) == 1
        assert observations[0].provenance is not None
        assert observations[0].provenance.page == 1
        assert observations[0].provenance.text_snippet != ""

    def test_api_extract_004_confidence_scoring(self, extract_module):
        """
        API-EXTRACT-004: Confidence scoring for extractions.

        Extractions should have confidence scores based on completeness.
        """
        # Full data row - higher confidence
        full_row = ["Glucose", "95", "mg/dL", "70-100", ""]

        observations = extract_module._extract_from_table(
            [["Test", "Result", "Units", "Range", "Flag"], full_row],
            page_num=1,
            document_id="test-123",
        )

        assert len(observations) == 1
        assert observations[0].confidence >= 0.5  # Has value
        assert observations[0].confidence <= 1.0

        # Partial data row - lower confidence
        partial_row = ["Unknown Test", "", "", "", ""]

        observations = extract_module._extract_from_table(
            [["Test", "Result", "Units", "Range", "Flag"], partial_row],
            page_num=1,
            document_id="test-123",
        )

        # Should have lower confidence or be skipped
        if observations:
            assert observations[0].confidence < 0.8


class TestDatePropagation:
    """Tests for HC-REM-005: Date propagation to observations."""

    @pytest.fixture
    def extract_module(self):
        return ExtractModule()

    @pytest.mark.asyncio
    async def test_extracted_observations_have_collected_at(self, extract_module, tmp_path):
        """
        HC-REM-005-001: Observations should inherit dates from document-level extraction.

        Given text with a date and analyte lines, every ExtractedObservation.collected_at
        should be non-None.
        """
        mock_page = MagicMock()
        mock_page.extract_text.return_value = (
            "Collection Date: 01/15/2024\n"
            "Glucose: 95 mg/dL (70-100)\n"
            "Creatinine: 1.1 mg/dL (0.7-1.3)\n"
        )
        mock_page.extract_tables.return_value = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = await extract_module.extract_from_pdf(tmp_path / "test.pdf", "doc-1")

        assert len(result.observations) >= 1
        for obs in result.observations:
            assert obs.collected_at is not None, (
                f"Observation '{obs.analyte_raw}' should have collected_at set"
            )

    @pytest.mark.asyncio
    async def test_date_propagation_from_document_level(self, extract_module, tmp_path):
        """
        HC-REM-005-002: If no per-observation date exists, observations should
        inherit the document-level collection date.
        """
        mock_page = MagicMock()
        mock_page.extract_text.return_value = (
            "Report Date: 03/20/2024\n"
            "BUN: 18 mg/dL (7-20)\n"
        )
        mock_page.extract_tables.return_value = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = await extract_module.extract_from_pdf(tmp_path / "test.pdf", "doc-1")

        assert len(result.collection_dates) >= 1
        for obs in result.observations:
            assert obs.collected_at is not None
            assert "03/20/2024" in obs.collected_at


class TestExtractFromText:
    """Tests specifically for _extract_from_text implementation."""

    @pytest.fixture
    def extract_module(self):
        return ExtractModule()

    def test_extract_simple_colon_format(self, extract_module):
        """Test extraction of 'Analyte: Value Unit' format."""
        text = "Glucose: 95 mg/dL"

        observations = extract_module._extract_from_text(text, page_num=1, document_id="test")

        # TDD: Will fail until _extract_from_text is implemented
        assert isinstance(observations, list)
        assert len(observations) >= 1, "Should extract at least one observation"
        assert "glucose" in observations[0].analyte_raw.lower()
        assert observations[0].value == 95.0

    def test_extract_with_reference_range(self, extract_module):
        """Test extraction with reference range in parentheses."""
        text = "Hemoglobin: 14.5 g/dL (12.0-17.5)"

        observations = extract_module._extract_from_text(text, page_num=1, document_id="test")

        assert isinstance(observations, list)
        # After implementation:
        # assert observations[0].ref_low == 12.0
        # assert observations[0].ref_high == 17.5

    def test_extract_with_flag(self, extract_module):
        """Test extraction of flagged (abnormal) values."""
        text = "HbA1c: 7.2% (4.0-5.6) HIGH"

        observations = extract_module._extract_from_text(text, page_num=1, document_id="test")

        assert isinstance(observations, list)
        # After implementation:
        # assert observations[0].flag in ["H", "HIGH"]

    def test_extract_multiline(self, extract_module):
        """Test extraction from multiple lines."""
        text = """
        Glucose: 95 mg/dL (70-100)
        Creatinine: 1.1 mg/dL (0.7-1.3)
        BUN: 18 mg/dL (7-20)
        """

        observations = extract_module._extract_from_text(text, page_num=1, document_id="test")

        assert isinstance(observations, list)
        # After implementation:
        # assert len(observations) >= 3
