"""
Tests for Sprint 2: Import → Extract → Normalize → Persist pipeline.

TDD Tests that verify:
- Import triggers extraction pipeline
- Observations are created from PDFs
- Document status is set correctly
- needs_verification is computed
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.extract import ExtractedObservation, ExtractionResult, ExtractModule, Provenance


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
            # _extract_dates() now normalises to ISO-8601 (YYYY-MM-DD)
            assert obs.collected_at == "2024-03-20", (
                f"Expected ISO date '2024-03-20', got {obs.collected_at!r}"
            )


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


class TestExtractFormats:
    """EXTRACT-FORMATS: column layouts, thyroid/SI units, per-page table fallback."""

    @pytest.fixture
    def extract_module(self):
        return ExtractModule()

    @pytest.mark.parametrize(
        "line,analyte,value,unit",
        [
            ("TSH: 2.1 mIU/L (0.4-4.0)", "TSH", 2.1, "mIU/L"),
            ("TSH 2.1 uIU/mL (0.4-4.0)", "TSH", 2.1, "uIU/mL"),
            ("Free T4: 1.2 ng/dL (0.8-1.8)", "Free T4", 1.2, "ng/dL"),
            ("Iron 80 ug/dL (60-170)", "Iron", 80.0, "ug/dL"),
            ("Vitamin D: 75 nmol/L (75-250)", "Vitamin D", 75.0, "nmol/L"),
            ("Creatinine 88 umol/L (60-110)", "Creatinine", 88.0, "umol/L"),
            ("Hemoglobin 135 g/L (120-160)", "Hemoglobin", 135.0, "g/L"),
            ("Ferritin 60 ug/L (15-150)", "Ferritin", 60.0, "ug/L"),
            ("TSH 2.1 \u00b5IU/mL (0.4-4.0)", "TSH", 2.1, "\u00b5IU/mL"),
            ("TSH 2.1 \u03bcIU/mL (0.4-4.0)", "TSH", 2.1, "\u03bcIU/mL"),
        ],
    )
    def test_hc_exf_001_thyroid_and_si_units(self, extract_module, line, analyte, value, unit):
        obs = extract_module._extract_from_text(line, page_num=1, document_id="t")
        assert len(obs) == 1
        assert obs[0].analyte_raw == analyte
        assert obs[0].value == value
        assert obs[0].unit == unit

    def test_hc_exf_002_column_layout_range(self, extract_module):
        obs = extract_module._extract_from_text("TSH 2.10 mIU/L 0.45-4.50", 1, "t")
        assert len(obs) == 1
        assert obs[0].value == 2.10
        assert obs[0].unit == "mIU/L"
        assert obs[0].ref_low == 0.45
        assert obs[0].ref_high == 4.50

    def test_hc_exf_003_column_layout_flag_before_unit(self, extract_module):
        obs = extract_module._extract_from_text("Glucose 105 H mg/dL 70-99", 1, "t")
        assert len(obs) == 1
        assert obs[0].value == 105.0
        assert obs[0].flag == "H"
        assert obs[0].ref_low == 70.0
        assert obs[0].ref_high == 99.0

    def test_hc_exf_004_column_page_only_result_rows(self, extract_module):
        text = "\n".join([
            "TEST RESULT FLAG UNITS REFERENCE INTERVAL",
            "Patient: Jane Doe",
            "MRN 00482913",
            "Collected: 01/15/2026 08:10",
            "Glucose 105 H mg/dL 70-99",
            "Creatinine 0.9 mg/dL 0.6-1.3",
            "TSH 2.10 mIU/L 0.45-4.50",
            "Hemoglobin 13.5 g/dL 12.0-16.0",
            "Sodium 140 mmol/L 135-145",
            "Potassium 4.1 mmol/L 3.5-5.1",
            "LDL Cholesterol 135 H mg/dL <100",
            "Ferritin 60 ng/mL 15-150",
            "Page 1 of 2",
        ])
        obs = extract_module._extract_from_text(text, 1, "t")
        assert [o.analyte_raw for o in obs] == [
            "Glucose", "Creatinine", "TSH", "Hemoglobin",
            "Sodium", "Potassium", "LDL Cholesterol", "Ferritin",
        ]
        by_name = {o.analyte_raw: o for o in obs}
        assert (by_name["Glucose"].value, by_name["Glucose"].unit) == (105.0, "mg/dL")
        assert (by_name["Glucose"].ref_low, by_name["Glucose"].ref_high) == (70.0, 99.0)
        ldl = by_name["LDL Cholesterol"]
        assert (ldl.value, ldl.unit, ldl.flag) == (135.0, "mg/dL", "H")
        assert (ldl.ref_low, ldl.ref_high) == (None, 100.0)
        assert ldl.ref_range_text == "<100"
        assert by_name["Glucose"].ref_range_text == "70-99"
        assert (by_name["Ferritin"].value, by_name["Ferritin"].unit) == (60.0, "ng/mL")

    def test_hc_exf_004b_column_greater_than_range_and_flag_after(self, extract_module):
        obs = extract_module._extract_from_text("Vitamin D 120 ng/mL >30 h", 1, "t")
        assert len(obs) == 1
        assert (obs[0].value, obs[0].ref_low, obs[0].ref_high) == (120.0, 30.0, None)
        assert obs[0].flag == "H"
        assert obs[0].ref_range_text == ">30"

    @pytest.mark.parametrize(
        "line",
        [
            "Glucose 105 98 mg/dL 70-99",
            "Glucose 105 H 98 mg/dL 70-99",
            "Glucose 105 HIGH 98 mg/dL 70-99",
            "Glucose 105 98 mg/dL",
            "Glucose 105 H 98 mg/dL",
            "Glucose 105 98 mg/dL (70-99)",
            "Glucose 105, 98 mg/dL 70-99",
            "Creatinine 120 H 88 umol/L (60-110)",
            "Ferritin 300 H 60 ug/L",
            "Iron 200 H 80 ug/dL (60-170)",
            "Vitamin D 40 L 75 nmol/L (75-250)",
            "Hemoglobin 150 H 135 g/L",
            "Creatinine 120 88 umol/L",
            "Glucose 105H 98 mg/dL 70-99",
            "Creatinine 120H 88 umol/L (60-110)",
            "Glucose 105HI 98 mg/dL 70-99",
            "Glucose 105LO 98 mg/dL 70-99",
            "Glucose 105A 98 mg/dL 70-99",
            "Creatinine 120HI 88 umol/L (60-110)",
        ],
    )
    def test_hc_exf_004c_column_previous_result_not_absorbed_into_analyte(self, extract_module, line):
        # Two numbers before the unit (a flag may sit between them): ambiguous, so no
        # observation. Never "Glucose 105" or a dropped flag on the wrong value.
        assert extract_module._extract_from_text(line, 1, "t") == []

    def test_hc_exf_004d_colon_lines_are_not_guarded(self, extract_module):
        # The previous-result guard covers non-colon matches only.
        result = extract_module._extract_from_text("Vitamin B 12: 400 pg/mL", 1, "t")
        assert [(o.analyte_raw, o.value) for o in result] == [("Vitamin B 12", 400.0)]

    @staticmethod
    def _pdf(page):
        pdf = MagicMock()
        pdf.pages = [page]
        pdf.__enter__ = MagicMock(return_value=pdf)
        pdf.__exit__ = MagicMock(return_value=False)
        return pdf

    @pytest.mark.asyncio
    async def test_hc_exf_005_text_fallback_when_tables_yield_nothing(self, extract_module, tmp_path):
        page = MagicMock()
        page.extract_text.return_value = (
            "MRN: 00482913\nPatient ID: 7731942\nAge: 54\n"
            "Glucose: 95 mg/dL (70-100)\nTSH 2.1 mIU/L (0.4-4.0)"
        )
        page.extract_tables.return_value = [[["Header only", "x"]]]
        with patch("pdfplumber.open", return_value=self._pdf(page)):
            result = await extract_module.extract_from_pdf(tmp_path / "a.pdf", "doc")
        # Identifier lines have no unit, so the fallback must not keep them.
        assert sorted(o.analyte_raw for o in result.observations) == ["Glucose", "TSH"]

    @pytest.mark.asyncio
    async def test_hc_exf_006_no_text_fallback_when_tables_yield(self, extract_module, tmp_path):
        page = MagicMock()
        page.extract_text.return_value = "Glucose: 95 mg/dL (70-100)\nCreatinine: 1.1 mg/dL (0.7-1.3)"
        page.extract_tables.return_value = [
            [
                ["Test Name", "Result", "Units", "Reference Range", "Flag"],
                ["Glucose", "95", "mg/dL", "70-100", ""],
                ["Creatinine", "1.1", "mg/dL", "0.7-1.3", ""],
            ]
        ]
        with patch("pdfplumber.open", return_value=self._pdf(page)), \
                patch.object(ExtractModule, "_extract_from_text") as text_parser:
            result = await extract_module.extract_from_pdf(tmp_path / "b.pdf", "doc")
        assert len(result.observations) == 2
        text_parser.assert_not_called()

    @pytest.mark.asyncio
    async def test_hc_exf_005b_no_tables_page_keeps_unitless_rows(self, extract_module, tmp_path):
        page = MagicMock()
        page.extract_text.return_value = "Glucose: 95 (70-100)"
        page.extract_tables.return_value = []
        with patch("pdfplumber.open", return_value=self._pdf(page)):
            result = await extract_module.extract_from_pdf(tmp_path / "c.pdf", "doc")
        # The unit filter applies only on pages that have tables.
        assert [o.analyte_raw for o in result.observations] == ["Glucose"]


class TestMgPerLiterUnit:
    """EXTRACT-UNIT-MGL: `mg/L` (CRP) is a known unit on all three text-line patterns."""

    @pytest.fixture
    def extract_module(self):
        return ExtractModule()

    @pytest.mark.parametrize(
        "line,pattern",
        [
            ("CRP: 4.2 mg/L (0.0-5.0)", "LINE_PATTERN"),
            # ALT_LINE_PATTERN only takes a parenthesised range; a bare range is a column line.
            ("CRP 4.2 mg/L (0.0-5.0)", "ALT_LINE_PATTERN"),
            ("CRP 4.2 mg/L 0.0-5.0", "COLUMN_LINE_PATTERN"),
            ("CRP   4.2   mg/L   0.0-5.0", "COLUMN_LINE_PATTERN"),
        ],
        ids=["colon", "alt-parenthesised", "column-single-space", "column-padded"],
    )
    def test_hc_exu_001_mg_per_l_line_is_kept(self, extract_module, line, pattern):
        obs = extract_module._extract_from_text(line, page_num=1, document_id="t")
        assert len(obs) == 1
        assert obs[0].analyte_raw == "CRP"
        assert obs[0].value == 4.2
        assert obs[0].unit == "mg/L"
        assert obs[0].ref_low == 0.0
        assert obs[0].ref_high == 5.0
        # The line must reach the pattern this case is meant to exercise (the earlier
        # patterns must not take it), so the three cases cover three different patterns.
        order = ["LINE_PATTERN", "ALT_LINE_PATTERN", "COLUMN_LINE_PATTERN"]
        for name in order[: order.index(pattern)]:
            assert getattr(ExtractModule, name).match(line) is None, name
        assert getattr(ExtractModule, pattern).match(line) is not None

    def test_hc_exu_002_mg_per_dl_keeps_longer_unit(self, extract_module):
        # Pin: `mg/dL` stays listed before `mg/L`/`g/dL` so it is never truncated.
        obs = extract_module._extract_from_text("LDL: 128 mg/dL (0-100)", page_num=1, document_id="t")
        assert len(obs) == 1
        assert obs[0].value == 128.0
        assert obs[0].unit == "mg/dL"


class TestTableCellFullParse:
    """EXTRACT-TABLE-VALUE: a table result cell is parsed whole, not by its first digits."""

    @staticmethod
    def _row(cell, flag_cell="", unit_cell="", flag_col=-1):
        row = ["Analyte", cell, unit_cell, "", flag_cell]
        return ExtractModule()._parse_table_row(
            row, name_col=0, value_col=1, unit_col=2 if unit_cell else -1,
            range_col=-1, flag_col=4 if flag_col < 0 and flag_cell else flag_col, page_num=1,
        )

    def test_hc_etv_001_thousands_separator_is_one_number(self):
        obs = self._row("1,234")
        assert obs.value == 1234.0
        assert obs.value_text is None

    @pytest.mark.parametrize("cell", ["<0.5", ">90", "<=5"])
    def test_hc_etv_002_comparator_is_never_an_exact_number(self, cell):
        obs = self._row(cell)
        assert obs.value is None
        assert obs.value_text == cell

    @pytest.mark.parametrize(
        "cell,flag", [("5.9 H", "H"), ("(H) 5.9", "H"), ("5.9*", "A")]
    )
    def test_hc_etv_003_in_cell_flag_sets_flag(self, cell, flag):
        obs = self._row(cell)
        assert obs.value == 5.9
        assert obs.flag == flag

    def test_hc_etv_004_partial_match_is_text_not_a_number(self):
        obs = self._row("12.5 (calc)")
        assert obs.value is None
        assert obs.value_text == "12.5 (calc)"

    def test_hc_etv_005_flag_column_wins_over_in_cell_flag(self):
        obs = self._row("105 L", flag_cell="H")
        assert obs.value == 105.0
        assert obs.flag == "H"

    def test_hc_etv_006_value_with_unit_in_cell_still_parses(self):
        obs = self._row("4.2 mg/L")
        assert obs.value == 4.2

    @pytest.mark.parametrize(
        "cell",
        [
            pytest.param(" " * 20000 + "x", id="spaces20000-x"),
            pytest.param("5" + " " * 5000 + "x", id="5-spaces5000-x"),
        ],
    )
    def test_hc_etv_008_long_whitespace_run_parses_in_linear_time(self, cell):
        import time

        start = time.perf_counter()
        obs = self._row(cell)
        elapsed = time.perf_counter() - start
        assert obs.value is None
        assert elapsed < 1.0, f"table-cell parse took {elapsed:.2f}s on a whitespace run"

    @pytest.mark.asyncio
    async def test_hc_etv_007_ruled_grid_pdf_through_import(
        self, monkeypatch, tmp_path
    ):
        """Ruled-grid PDF -> real pdfplumber table -> POST /documents/import -> stored rows."""
        import hashlib
        import io

        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        import modules
        from api import documents as documents_api
        from api.documents import router as documents_router
        from core.auth import get_profile_db_session
        from core.profile_database import ProfileDatabaseBase
        from models import Observation
        from modules.ingest import ImportResult
        from tests.support.routes import route_client
        from tests.test_documents_api import _CommitTrackingMasterDb

        rows = [
            ["Test", "Result", "Unit"],
            ["Alpha", "1,234", ""],
            ["Bravo", "<0.5", ""],
            ["Charlie", "5.9 H", ""],
            ["Delta", "4.2 mg/L", ""],
        ]
        col_x, row_h, top = [50, 200, 350, 450], 24, 740
        ops = ["0.5 w"]
        n_rows = len(rows)
        for i in range(n_rows + 1):
            y = top - i * row_h
            ops.append(f"{col_x[0]} {y} m {col_x[-1]} {y} l S")
        for x in col_x:
            ops.append(f"{x} {top} m {x} {top - n_rows * row_h} l S")
        ops += ["BT", "/F1 11 Tf"]
        for r, row in enumerate(rows):
            for c, text in enumerate(row):
                if text:
                    esc = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                    ops.append(f"1 0 0 1 {col_x[c] + 6} {top - r * row_h - 16} Tm ({esc}) Tj")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1")
        objs = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        ]
        out = io.BytesIO()
        out.write(b"%PDF-1.4\n")
        offsets = []
        for number, body in enumerate(objs, start=1):
            offsets.append(out.tell())
            out.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
        xref = out.tell()
        out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
        out.write("".join(f"{o:010d} 00000 n \n" for o in offsets).encode())
        out.write(
            f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
        )
        pdf = out.getvalue()

        stored: dict[str, bytes] = {}

        class _PdfIngest:
            def __init__(self, *_a, **_k):
                pass

            async def import_document(self, *, file, **_k):
                data = file.read()
                doc_id = str(uuid.uuid4())
                stored[doc_id] = data
                return ImportResult(
                    document_id=doc_id,
                    path_hash=hashlib.sha256(doc_id.encode()).hexdigest(),
                    content_hash=hashlib.sha256(data).hexdigest(),
                    doc_type="lab_pdf",
                    page_count=1,
                    is_duplicate=False,
                    metadata={},
                    encrypted=True,
                )

        async def _no_classify(**_k):
            return None

        monkeypatch.setattr(
            type(documents_api.settings), "app_data_path", property(lambda self: tmp_path)
        )
        monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _p: b"x" * 32)
        monkeypatch.setattr(modules, "IngestModule", _PdfIngest)
        monkeypatch.setattr(
            documents_api, "get_decrypted_document", lambda _p, d: io.BytesIO(stored[d])
        )
        monkeypatch.setattr(documents_api, "_classify_and_extract_entities", _no_classify)

        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
        session = AsyncSession(engine, expire_on_commit=False)
        try:
            with route_client(
                documents_router, "/documents", profile_id="profile-a",
                master_db=_CommitTrackingMasterDb(),
            ) as client:

                async def _override_profile_db():
                    return session

                client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
                resp = client.post(
                    "/documents/import",
                    files={"file": ("grid.pdf", pdf, "application/pdf")},
                )
            assert resp.status_code == 201, resp.text
            obs = (await session.execute(select(Observation))).scalars().all()
        finally:
            await session.close()
            await engine.dispose()

        by_name = {o.analyte_raw: o for o in obs}
        assert set(by_name) == {"Alpha", "Bravo", "Charlie", "Delta"}, sorted(by_name)
        assert by_name["Alpha"].value == 1234.0
        assert by_name["Bravo"].value is None
        assert by_name["Bravo"].value_text == "<0.5"
        assert by_name["Charlie"].value == 5.9
        assert by_name["Charlie"].flag == "H"
        assert by_name["Charlie"].is_abnormal is True
        assert by_name["Delta"].value == 4.2
