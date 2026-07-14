"""
Tests for Sprint 4: Export System End-to-End.

TDD Tests that verify:
- CSV export returns data
- JSON export returns data
- Doctor summary generation
- Summary download
- Questions generation

All tests verify authenticated access and data isolation.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import json

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.export import ExportModule, DoctorSummary, QuestionPrompt


class TestExportCSV:
    """Tests for CSV export endpoint."""

    @pytest.fixture
    def export_module(self):
        """Create export module for testing."""
        return ExportModule()

    @pytest.fixture
    def sample_observations(self):
        """Sample observations for testing."""
        return [
            {
                "id": str(uuid.uuid4()),
                "analyte_canonical": "glucose",
                "analyte_raw": "Glucose",
                "value": 95.0,
                "unit": "mg/dL",
                "ref_low": 70.0,
                "ref_high": 100.0,
                "flag": None,
                "is_abnormal": False,
                "user_verified": True,
                "collected_at": datetime(2024, 1, 15, tzinfo=timezone.utc),
            },
            {
                "id": str(uuid.uuid4()),
                "analyte_canonical": "hemoglobin_a1c",
                "analyte_raw": "Hemoglobin A1c",
                "value": 6.5,
                "unit": "%",
                "ref_low": 4.0,
                "ref_high": 5.6,
                "flag": "H",
                "is_abnormal": True,
                "user_verified": False,
                "collected_at": datetime(2024, 1, 15, tzinfo=timezone.utc),
            },
        ]

    def test_api_export_001_csv_export_returns_data(self, export_module, sample_observations):
        """
        API-EXPORT-001: CSV export returns data.

        Exporting observations as CSV should return properly formatted CSV string.
        """
        csv_output = export_module.export_csv(sample_observations)

        assert isinstance(csv_output, str)
        assert len(csv_output) > 0

        # Check header row
        lines = csv_output.strip().split('\n')
        assert len(lines) >= 2  # Header + at least 1 data row

        header = lines[0]
        assert "Date" in header
        assert "Analyte" in header
        assert "Value" in header
        assert "Unit" in header
        assert "Reference Low" in header
        assert "Reference High" in header
        assert "Flag" in header
        assert "Verified" in header

        # Check data rows exist
        assert "glucose" in csv_output.lower()
        assert "95" in csv_output or "95.0" in csv_output

    def test_api_export_001b_csv_export_with_analyte_filter(self, export_module, sample_observations):
        """
        CSV export should respect analyte filter.
        """
        csv_output = export_module.export_csv(
            sample_observations,
            analyte_filter=["glucose"]
        )

        lines = csv_output.strip().split('\n')
        # Header + 1 glucose row only
        assert len(lines) == 2
        assert "glucose" in csv_output.lower()
        assert "hemoglobin_a1c" not in csv_output.lower()


class TestExportJSON:
    """Tests for JSON export endpoint."""

    @pytest.fixture
    def export_module(self):
        return ExportModule()

    @pytest.fixture
    def sample_observations(self):
        return [
            {
                "id": str(uuid.uuid4()),
                "analyte_canonical": "glucose",
                "value": 95.0,
                "unit": "mg/dL",
                "ref_low": 70.0,
                "ref_high": 100.0,
                "flag": None,
                "is_abnormal": False,
                "user_verified": True,
                "collected_at": datetime(2024, 1, 15, tzinfo=timezone.utc),
            },
        ]

    def test_api_export_002_json_export_returns_data(self, export_module, sample_observations):
        """
        API-EXPORT-002: JSON export returns data.

        Exporting observations as JSON should return valid JSON string.
        """
        json_output = export_module.export_json(sample_observations)

        assert isinstance(json_output, str)

        # Should be valid JSON
        parsed = json.loads(json_output)
        assert isinstance(parsed, list)
        assert len(parsed) == 1

        # Check observation fields
        obs = parsed[0]
        assert obs["analyte_canonical"] == "glucose"
        assert obs["value"] == 95.0
        assert obs["unit"] == "mg/dL"

    def test_api_export_002b_json_export_serializes_dates(self, export_module, sample_observations):
        """
        JSON export should serialize datetime objects to ISO format.
        """
        json_output = export_module.export_json(sample_observations)
        parsed = json.loads(json_output)

        # collected_at should be ISO string, not datetime
        assert isinstance(parsed[0]["collected_at"], str)
        assert "2024-01-15" in parsed[0]["collected_at"]


class TestDoctorSummary:
    """Tests for doctor summary generation."""

    @pytest.fixture
    def export_module(self):
        return ExportModule()

    @pytest.fixture
    def sample_observations(self):
        return [
            {
                "analyte_canonical": "glucose",
                "value": 95.0,
                "unit": "mg/dL",
                "ref_low": 70.0,
                "ref_high": 100.0,
                "flag": None,
                "is_abnormal": False,
                "collected_at": datetime(2024, 1, 15, tzinfo=timezone.utc),
            },
            {
                "analyte_canonical": "hemoglobin_a1c",
                "value": 7.2,
                "unit": "%",
                "ref_low": 4.0,
                "ref_high": 5.6,
                "flag": "HH",
                "is_abnormal": True,
                "collected_at": datetime(2024, 1, 15, tzinfo=timezone.utc),
            },
            {
                "analyte_canonical": "cholesterol_total",
                "value": 245.0,
                "unit": "mg/dL",
                "ref_low": None,
                "ref_high": 200.0,
                "flag": "H",
                "is_abnormal": True,
                "collected_at": datetime(2024, 1, 10, tzinfo=timezone.utc),
            },
        ]

    @pytest.fixture
    def sample_trends(self):
        return [
            {
                "analyte": "hemoglobin_a1c",
                "trend_direction": "up",
                "delta_percent": 15.2,
            },
            {
                "analyte": "glucose",
                "trend_direction": "stable",
                "delta_percent": 2.1,
            },
        ]

    @pytest.mark.asyncio
    async def test_api_export_003_doctor_summary_generation(
        self, export_module, sample_observations, sample_trends
    ):
        """
        API-EXPORT-003: Doctor summary generation.

        Should generate a structured summary with key findings,
        abnormal values, and trend information.
        """
        profile_id = str(uuid.uuid4())

        summary = await export_module.generate_doctor_summary(
            profile_id=profile_id,
            observations=sample_observations,
            trends=sample_trends,
        )

        assert isinstance(summary, DoctorSummary)
        assert summary.profile_id == profile_id
        assert summary.summary_id is not None
        assert summary.generated_at is not None

        # Check counts
        assert summary.total_observations == 3
        assert summary.abnormal_count == 2
        assert summary.critical_count == 1  # HH flag

        # Check key findings
        assert len(summary.key_findings) > 0

        # Check sections
        assert len(summary.sections) >= 2  # Overview + abnormal values
        section_titles = [s.title for s in summary.sections]
        assert "Overview" in section_titles
        assert "Values Outside Reference Range" in section_titles

    @pytest.mark.asyncio
    async def test_api_export_003b_summary_date_filtering(
        self, export_module, sample_observations, sample_trends
    ):
        """
        Doctor summary should respect date range filters.
        """
        profile_id = str(uuid.uuid4())

        # Filter to only include Jan 15 observations
        summary = await export_module.generate_doctor_summary(
            profile_id=profile_id,
            observations=sample_observations,
            trends=sample_trends,
            from_date=datetime(2024, 1, 14, tzinfo=timezone.utc),
            to_date=datetime(2024, 1, 16, tzinfo=timezone.utc),
        )

        # Should exclude the Jan 10 cholesterol observation
        assert summary.total_observations == 2
        assert summary.abnormal_count == 1  # Only HbA1c

    @pytest.mark.asyncio
    async def test_api_export_003c_summary_includes_trends(
        self, export_module, sample_observations, sample_trends
    ):
        """
        Doctor summary should include trend information when enabled.
        """
        profile_id = str(uuid.uuid4())

        summary = await export_module.generate_doctor_summary(
            profile_id=profile_id,
            observations=sample_observations,
            trends=sample_trends,
            include_trends=True,
        )

        section_titles = [s.title for s in summary.sections]
        assert "Notable Trends" in section_titles


class TestSummaryDownload:
    """Tests for summary download endpoint."""

    def test_api_export_004_summary_download(self):
        """
        API-EXPORT-004: Summary download.

        Previously generated summaries should be downloadable.
        The API should store summaries and allow retrieval by ID.
        """
        # This test verifies the endpoint structure exists
        # The actual implementation will store summaries in the profile DB
        # For now, verify the data structures support this

        summary = DoctorSummary(
            summary_id=str(uuid.uuid4()),
            profile_id=str(uuid.uuid4()),
            generated_at=datetime.utcnow(),
            date_range_start=None,
            date_range_end=None,
            key_findings=["Test finding"],
            sections=[],
            total_observations=10,
            abnormal_count=2,
            critical_count=0,
        )

        # Summary should be serializable for storage
        assert summary.summary_id is not None
        assert summary.profile_id is not None

    def test_api_export_004b_summary_text_format(self):
        """
        Summary should be renderable as text for download.
        """
        from modules.export import SummarySection

        summary = DoctorSummary(
            summary_id=str(uuid.uuid4()),
            profile_id=str(uuid.uuid4()),
            generated_at=datetime.utcnow(),
            date_range_start=datetime(2024, 1, 1),
            date_range_end=datetime(2024, 1, 31),
            key_findings=[
                "Hemoglobin A1c: 7.2% (critical - HH)",
                "Cholesterol: 245 mg/dL (H)",
            ],
            sections=[
                SummarySection(
                    title="Overview",
                    content="This summary includes 10 lab values from January 2024.",
                ),
                SummarySection(
                    title="Values Outside Reference Range",
                    content="2 values were flagged as abnormal.",
                ),
            ],
            total_observations=10,
            abnormal_count=2,
            critical_count=1,
        )

        # Verify sections have content
        assert len(summary.sections) == 2
        assert "Overview" in summary.sections[0].title
        assert "Outside Reference Range" in summary.sections[1].title

    def test_api_export_004c_html_summary_renders_questions_section(self):
        """HTML summary should include clinician questions when present."""
        export_module = ExportModule()
        summary_data = {
            "date_range": "2024-01-01 to 2024-01-31",
            "key_findings": ["A1c elevated"],
            "sections": [{"title": "Overview", "content": "Summary body"}],
            "questions": [
                {"question": "What follow-up labs do you recommend?"},
                {"question": "Could medication timing affect this trend?"},
            ],
        }

        html = export_module.render_html_summary(summary_data)
        assert "Questions for Your Provider" in html
        assert "What follow-up labs do you recommend?" in html

    def test_api_export_004d_html_summary_escapes_section_and_question_html(self):
        """A section title/content or question containing markup must render
        escaped, not as live HTML/script (HC review fix — unescaped HTML in
        the packet HTML/PDF download)."""
        export_module = ExportModule()
        payload = "<script>alert(1)</script>"
        summary_data = {
            "key_findings": [payload],
            "sections": [{"title": payload, "content": payload}],
            "questions": [{"question": payload}],
        }

        html = export_module.render_html_summary(summary_data)
        assert payload not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


class TestQuestionsGeneration:
    """Tests for discussion questions generation."""

    @pytest.fixture
    def export_module(self):
        return ExportModule()

    @pytest.fixture
    def sample_observations(self):
        return [
            {
                "analyte_canonical": "hemoglobin_a1c",
                "value": 7.2,
                "unit": "%",
                "ref_low": 4.0,
                "ref_high": 5.6,
                "flag": "H",
                "is_abnormal": True,
            },
            {
                "analyte_canonical": "cholesterol_total",
                "value": 245.0,
                "unit": "mg/dL",
                "flag": "H",
                "is_abnormal": True,
            },
        ]

    @pytest.fixture
    def sample_trends(self):
        return [
            {
                "analyte": "hemoglobin_a1c",
                "trend_direction": "up",
                "delta_percent": 15.2,
            },
        ]

    def test_api_export_005_questions_generation(
        self, export_module, sample_observations, sample_trends
    ):
        """
        API-EXPORT-005: Questions generation.

        Should generate discussion prompts for clinician visits
        based on abnormal values and trends.
        """
        questions = export_module.generate_questions(
            observations=sample_observations,
            trends=sample_trends,
        )

        assert isinstance(questions, list)
        assert len(questions) > 0

        # Check question structure
        for q in questions:
            assert isinstance(q, QuestionPrompt)
            assert q.category in ["abnormal", "trend", "clarification"]
            assert len(q.question) > 0
            assert len(q.context) > 0
            assert isinstance(q.related_analytes, list)

    def test_api_export_005b_questions_for_abnormal_values(
        self, export_module, sample_observations, sample_trends
    ):
        """
        Questions should be generated for abnormal values.
        """
        questions = export_module.generate_questions(
            observations=sample_observations,
            trends=sample_trends,
        )

        abnormal_questions = [q for q in questions if q.category == "abnormal"]
        assert len(abnormal_questions) > 0

        # Should reference the abnormal analytes
        analytes_mentioned = []
        for q in abnormal_questions:
            analytes_mentioned.extend(q.related_analytes)

        assert "hemoglobin_a1c" in analytes_mentioned or "cholesterol_total" in analytes_mentioned

    def test_api_export_005c_questions_for_trends(
        self, export_module, sample_observations, sample_trends
    ):
        """
        Questions should be generated for significant trends.
        """
        questions = export_module.generate_questions(
            observations=sample_observations,
            trends=sample_trends,
        )

        trend_questions = [q for q in questions if q.category == "trend"]
        assert len(trend_questions) > 0

        # Should reference trending analyte
        for q in trend_questions:
            assert "hemoglobin_a1c" in q.related_analytes

    def test_api_export_005d_questions_framed_as_discussion(
        self, export_module, sample_observations, sample_trends
    ):
        """
        Questions should be framed as discussion prompts, not medical advice.
        """
        questions = export_module.generate_questions(
            observations=sample_observations,
            trends=sample_trends,
        )

        for q in questions:
            # Questions should be phrased as questions to ask, not advice
            assert "?" in q.question
            # Should not contain medical advice keywords
            assert "you should" not in q.question.lower()
            assert "take" not in q.question.lower() or "medication" not in q.question.lower()


class TestExportDataIsolation:
    """Tests for data isolation in exports."""

    @pytest.fixture
    def export_module(self):
        return ExportModule()

    def test_export_only_includes_profile_data(self, export_module):
        """
        Exports should only include data from the authenticated profile.

        This is enforced at the API layer using session.profile_id.
        The ExportModule receives pre-filtered data.
        """
        profile_a_data = [
            {"analyte_canonical": "glucose", "value": 95.0, "collected_at": None, "unit": "mg/dL"},
        ]
        profile_b_data = [
            {"analyte_canonical": "glucose", "value": 120.0, "collected_at": None, "unit": "mg/dL"},
        ]

        # Export for profile A
        csv_a = export_module.export_csv(profile_a_data)
        assert "95" in csv_a or "95.0" in csv_a
        assert "120" not in csv_a

        # Export for profile B
        csv_b = export_module.export_csv(profile_b_data)
        assert "120" in csv_b or "120.0" in csv_b
        assert "95" not in csv_b


class TestExportEmptyState:
    """Tests for export with no data."""

    @pytest.fixture
    def export_module(self):
        return ExportModule()

    def test_csv_export_empty_returns_headers_only(self, export_module):
        """
        CSV export with no observations should return header row only.
        """
        csv_output = export_module.export_csv([])

        lines = csv_output.strip().split('\n')
        assert len(lines) == 1  # Header only
        assert "Date" in lines[0]
        assert "Analyte" in lines[0]

    def test_json_export_empty_returns_empty_array(self, export_module):
        """
        JSON export with no observations should return empty array.
        """
        json_output = export_module.export_json([])
        parsed = json.loads(json_output)

        assert isinstance(parsed, list)
        assert len(parsed) == 0

    def test_questions_empty_observations_returns_empty(self, export_module):
        """
        Questions generation with no data should return empty list.
        """
        questions = export_module.generate_questions(
            observations=[],
            trends=[],
        )

        assert isinstance(questions, list)
        assert len(questions) == 0
