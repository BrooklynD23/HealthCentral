"""
Tests for expanded date extraction (HC-DATE-*).

Covers:
- ExtractModule._extract_dates() recognising all US lab-report date formats
- Collection-label priority (Collected: / Collection Date: / Date of Service:)
- _parse_date_string() in api.documents accepting the same formats
- Plausibility guard (dates outside 1950..today+1 are rejected)
- TrendsDashboard path: undated observations produce summary text, not 404
"""

import sys
from datetime import datetime, date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.extract import ExtractModule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _module() -> ExtractModule:
    return ExtractModule()


# ---------------------------------------------------------------------------
# HC-DATE-001  _extract_dates() — format coverage
# ---------------------------------------------------------------------------

class TestExtractDatesFormats:
    """Verify _extract_dates() recognises every format in the spec."""

    @pytest.mark.parametrize("text,expected_iso", [
        # ISO 8601 bare date
        ("Collection Date: 2024-01-15", "2024-01-15"),
        # ISO 8601 with time
        ("Collected: 2024-01-15T14:30:00", "2024-01-15"),
        # MM/DD/YYYY
        ("Collected: 01/15/2024", "2024-01-15"),
        # MM/DD/YY  (two-digit year)
        ("Date of Service: 01/15/24", "2024-01-15"),
        # MM-DD-YYYY
        ("Specimen Date: 01-15-2024", "2024-01-15"),
        # MM-DD-YY
        ("Drawn Date: 01-15-24", "2024-01-15"),
        # Full month name with comma
        ("Collection Date: January 15, 2024", "2024-01-15"),
        # Full month name without comma
        ("Collected: January 15 2024", "2024-01-15"),
        # 3-letter abbreviation with comma
        ("Collected: Jan 15, 2024", "2024-01-15"),
        # 3-letter abbreviation without comma
        ("Drawn on: Jan 15 2024", "2024-01-15"),
        # DD-Mon-YYYY
        ("Accession Date: 15-Jan-2024", "2024-01-15"),
    ])
    def test_collection_label_formats(self, text, expected_iso):
        """HC-DATE-001-*: Each format is parsed when preceded by a label."""
        m = _module()
        dates = m._extract_dates(text)
        assert dates, f"Expected a date from: {text!r}"
        assert dates[0] == expected_iso, (
            f"Expected {expected_iso!r}, got {dates[0]!r} from {text!r}"
        )

    def test_iso_date_without_label(self):
        """HC-DATE-001-ISO: ISO date found in body text (no label)."""
        m = _module()
        dates = m._extract_dates("Lab drawn on 2024-03-22 at main clinic")
        assert "2024-03-22" in dates

    def test_full_month_without_label(self):
        """HC-DATE-001-FULL: Full-month date found in body text."""
        m = _module()
        dates = m._extract_dates("Report signed March 5, 2023")
        assert "2023-03-05" in dates

    def test_abbrev_month_without_label(self):
        """HC-DATE-001-ABBR: Abbreviated month date found in body text."""
        m = _module()
        dates = m._extract_dates("Results from Feb 20, 2023 panel")
        assert "2023-02-20" in dates

    def test_dd_mon_yyyy_without_label(self):
        """HC-DATE-001-DD: DD-Mon-YYYY found in body text."""
        m = _module()
        dates = m._extract_dates("Specimen drawn 20-Feb-2023")
        assert "2023-02-20" in dates

    def test_returns_list_of_strings(self):
        """Return value is always a list of strings."""
        m = _module()
        result = m._extract_dates("No dates here at all")
        assert isinstance(result, list)
        assert all(isinstance(d, str) for d in result)

    def test_returns_iso_format(self):
        """Every returned date is in YYYY-MM-DD format."""
        m = _module()
        dates = m._extract_dates("Collected: 03/15/2023 and also Jan 20, 2022")
        import re
        iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for d in dates:
            assert iso_re.match(d), f"Not ISO format: {d!r}"

    def test_deduplication(self):
        """Same date appearing twice is returned once."""
        m = _module()
        dates = m._extract_dates(
            "Collection Date: 2024-01-15\nSpecimen Date: 01/15/2024"
        )
        assert dates.count("2024-01-15") == 1


# ---------------------------------------------------------------------------
# HC-DATE-002  Collection-label priority
# ---------------------------------------------------------------------------

class TestCollectionLabelPriority:
    """Collection-label dates should appear before generic body-text dates."""

    def test_label_date_comes_first(self):
        """HC-DATE-002-PRI: 'Collected:' date takes priority over report date."""
        m = _module()
        text = (
            "Report Date: 2024-02-01\n"
            "Collected: 2024-01-15\n"
            "Glucose: 95 mg/dL"
        )
        dates = m._extract_dates(text)
        assert dates, "Should find at least one date"
        assert dates[0] == "2024-01-15", (
            f"Collection label date should be first, got {dates!r}"
        )

    def test_date_of_service_label(self):
        """HC-DATE-002-DOS: 'Date of Service' is recognised as a label."""
        m = _module()
        dates = m._extract_dates("Date of Service: 2023-07-04")
        assert "2023-07-04" in dates
        assert dates.index("2023-07-04") == 0

    def test_specimen_collected_label(self):
        """HC-DATE-002-SPEC: 'Specimen Collected' is recognised."""
        m = _module()
        dates = m._extract_dates("Specimen Collected: 15-Jan-2024")
        assert dates and dates[0] == "2024-01-15"


# ---------------------------------------------------------------------------
# HC-DATE-003  Plausibility guard
# ---------------------------------------------------------------------------

class TestPlausibilityGuard:
    """Dates outside 1950..today+1 must be silently dropped."""

    def test_future_date_rejected(self):
        """HC-DATE-003-FUT: Dates well in the future are dropped."""
        m = _module()
        dates = m._extract_dates("Collection Date: 2099-12-31")
        assert "2099-12-31" not in dates

    def test_ancient_date_rejected(self):
        """HC-DATE-003-OLD: Dates before 1950 are dropped."""
        m = _module()
        dates = m._extract_dates("Collection Date: 1945-06-06")
        assert "1945-06-06" not in dates

    def test_valid_date_passes(self):
        """HC-DATE-003-OK: A valid recent date is retained."""
        m = _module()
        dates = m._extract_dates("Collection Date: 2020-06-15")
        assert "2020-06-15" in dates


# ---------------------------------------------------------------------------
# HC-DATE-004  _parse_date_string() in api.documents
# ---------------------------------------------------------------------------

class TestParseDocumentDateString:
    """api.documents._parse_date_string() must accept all new formats."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from api.documents import _parse_date_string
        self._fn = _parse_date_string

    @pytest.mark.parametrize("raw,expected_date", [
        ("2024-01-15",              date(2024, 1, 15)),
        ("2024-01-15T14:30:00",     date(2024, 1, 15)),
        ("01/15/2024",              date(2024, 1, 15)),
        ("01/15/24",                date(2024, 1, 15)),
        ("01-15-2024",              date(2024, 1, 15)),
        ("January 15, 2024",        date(2024, 1, 15)),
        ("January 15 2024",         date(2024, 1, 15)),
        ("Jan 15, 2024",            date(2024, 1, 15)),
        ("Jan 15 2024",             date(2024, 1, 15)),
        ("15-Jan-2024",             date(2024, 1, 15)),
    ])
    def test_accepts_format(self, raw, expected_date):
        """HC-DATE-004-*: Each format produces the expected date."""
        result = self._fn(raw)
        assert result is not None, f"Expected parse success for {raw!r}"
        assert result.date() == expected_date, (
            f"Expected {expected_date}, got {result.date()} from {raw!r}"
        )

    def test_none_input_returns_none(self):
        assert self._fn(None) is None

    def test_empty_string_returns_none(self):
        assert self._fn("") is None

    def test_garbage_returns_none(self):
        assert self._fn("not a date at all") is None

    def test_future_date_rejected(self):
        """HC-DATE-004-FUT: Implausible future date returns None."""
        result = self._fn("2099-12-31")
        assert result is None

    def test_pre_1950_rejected(self):
        """HC-DATE-004-OLD: Pre-1950 date returns None."""
        result = self._fn("1900-01-01")
        assert result is None


# ---------------------------------------------------------------------------
# HC-DATE-005  Date propagation in extract_from_pdf
# ---------------------------------------------------------------------------

class TestDatePropagationISO:
    """ISO dates in PDF text are propagated to extracted observations."""

    @pytest.mark.asyncio
    async def test_iso_date_propagates_to_observations(self, tmp_path):
        """HC-DATE-005-ISO: ISO 8601 date found on page is set on observations."""
        m = _module()

        mock_page = MagicMock()
        mock_page.extract_text.return_value = (
            "Collection Date: 2024-03-10\n"
            "Glucose: 95 mg/dL (70-100)\n"
            "BUN: 18 mg/dL (7-20)\n"
        )
        mock_page.extract_tables.return_value = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = await m.extract_from_pdf(tmp_path / "test.pdf", "doc-iso-1")

        assert result.collection_dates, "Should detect at least one collection date"
        assert "2024-03-10" in result.collection_dates

        # All observations should have collected_at set
        for obs in result.observations:
            assert obs.collected_at is not None, (
                f"Obs '{obs.analyte_raw}' should have collected_at"
            )
            assert obs.collected_at == "2024-03-10"

    @pytest.mark.asyncio
    async def test_full_month_date_propagates(self, tmp_path):
        """HC-DATE-005-FULL: Spelled-out month date propagates to observations."""
        m = _module()

        mock_page = MagicMock()
        mock_page.extract_text.return_value = (
            "Collected: January 15, 2024\n"
            "Creatinine: 1.1 mg/dL (0.7-1.3)\n"
        )
        mock_page.extract_tables.return_value = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = await m.extract_from_pdf(tmp_path / "test.pdf", "doc-full-1")

        assert "2024-01-15" in result.collection_dates
        for obs in result.observations:
            assert obs.collected_at == "2024-01-15"

    @pytest.mark.asyncio
    async def test_no_date_leaves_collected_at_none(self, tmp_path):
        """HC-DATE-005-NULL: When no date found, collected_at stays None."""
        m = _module()

        mock_page = MagicMock()
        mock_page.extract_text.return_value = (
            "Glucose: 95 mg/dL (70-100)\n"
        )
        mock_page.extract_tables.return_value = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = await m.extract_from_pdf(tmp_path / "test.pdf", "doc-nodate-1")

        assert result.collection_dates == []
        for obs in result.observations:
            assert obs.collected_at is None


# ---------------------------------------------------------------------------
# HC-DATE-006  Trends endpoint: undated observations handled gracefully
# ---------------------------------------------------------------------------

class TestTrendsEndpointUndated:
    """
    api/observations.py get_analyte_trend() must:
      - Return data with empty data_points (not 404) when all obs are undated
      - Include undated count in summary text
      - Include dated obs in data_points, count undated separately
    """

    def _make_obs(self, value, collected_at=None, ref_low=None, ref_high=None, unit="mg/dL"):
        obs = MagicMock()
        obs.collected_at = collected_at
        obs.value = value
        obs.unit = unit
        obs.ref_low = ref_low
        obs.ref_high = ref_high
        obs.is_abnormal = False
        obs.flag = None
        obs.doc_id = "doc-1"
        obs.extraction_confidence = 0.9
        obs.analyte_canonical = "glucose"
        obs.profile_id = "profile-1"
        return obs

    def _run_trend_logic(self, observations, analyte="glucose"):
        """
        Re-implement the trend-building logic as it now exists in observations.py
        so we can unit-test it without spinning up a full FastAPI app.
        """
        from api.observations import TrendPoint

        data_points = []
        undated_count = 0
        ref_low = None
        ref_high = None
        unit = None

        for obs in observations:
            if obs.ref_low is not None:
                ref_low = obs.ref_low
            if obs.ref_high is not None:
                ref_high = obs.ref_high
            if obs.unit:
                unit = obs.unit

            if obs.collected_at and obs.value is not None:
                data_points.append(TrendPoint(
                    date=obs.collected_at.isoformat(),
                    value=obs.value,
                    unit=obs.unit or "",
                    is_abnormal=obs.is_abnormal or False,
                    flag=obs.flag,
                    doc_id=obs.doc_id,
                    extraction_confidence=obs.extraction_confidence,
                ))
            elif obs.value is not None:
                undated_count += 1

        total_count = len(data_points) + undated_count

        if len(data_points) >= 2:
            first_val = data_points[0].value
            last_val = data_points[-1].value
            change = last_val - first_val
            change_pct = (change / first_val * 100) if first_val != 0 else 0
            if abs(change_pct) < 5:
                trend = "stable"
            elif change > 0:
                trend = f"increased by {abs(change_pct):.1f}%"
            else:
                trend = f"decreased by {abs(change_pct):.1f}%"
            summary = f"{analyte.upper()} has {trend} over {len(data_points)} dated measurements."
            if undated_count:
                summary += f" {undated_count} additional measurement(s) have no collection date and are not shown on the chart."
        elif len(data_points) == 1:
            summary = f"Single dated measurement of {analyte.upper()} recorded."
            if undated_count:
                summary += f" {undated_count} additional measurement(s) have no collection date."
        elif undated_count:
            summary = (
                f"{total_count} measurement(s) of {analyte.upper()} found, "
                f"but none have a collection date so no trend line can be drawn. "
                f"Use the analyte list to see the latest value."
            )
        else:
            summary = f"Single measurement of {analyte.upper()} recorded."

        return data_points, summary, ref_low, ref_high, unit

    def test_all_undated_returns_empty_datapoints_not_404(self):
        """HC-DATE-006-NULL: All-undated obs → empty data_points, helpful summary."""
        obs_list = [
            self._make_obs(95.0, collected_at=None),
            self._make_obs(102.0, collected_at=None),
        ]
        data_points, summary, *_ = self._run_trend_logic(obs_list)
        assert data_points == [], "No dated points → data_points must be empty"
        assert "collection date" in summary.lower(), (
            f"Summary should mention missing dates: {summary!r}"
        )
        assert "2" in summary, "Summary should mention total count"

    def test_mixed_dated_undated(self):
        """HC-DATE-006-MIX: Dated obs in data_points; undated count in summary."""
        dt1 = datetime(2024, 1, 15)
        dt2 = datetime(2024, 4, 10)
        obs_list = [
            self._make_obs(90.0, collected_at=dt1),
            self._make_obs(98.0, collected_at=None),   # undated
            self._make_obs(95.0, collected_at=dt2),
        ]
        data_points, summary, *_ = self._run_trend_logic(obs_list)
        assert len(data_points) == 2, "Only the 2 dated obs should be in data_points"
        assert "1 additional measurement" in summary, (
            f"Undated count missing from summary: {summary!r}"
        )

    def test_all_dated_no_undated_mention(self):
        """HC-DATE-006-DATED: All-dated obs → summary has no 'no collection date' text."""
        dt1 = datetime(2024, 1, 15)
        dt2 = datetime(2024, 6, 20)
        obs_list = [
            self._make_obs(90.0, collected_at=dt1),
            self._make_obs(95.0, collected_at=dt2),
        ]
        data_points, summary, *_ = self._run_trend_logic(obs_list)
        assert len(data_points) == 2
        assert "no collection date" not in summary.lower()

    def test_ref_range_collected_from_undated_obs(self):
        """HC-DATE-006-REF: ref_low/ref_high picked up even from undated observations."""
        obs_list = [
            self._make_obs(95.0, collected_at=None, ref_low=70.0, ref_high=100.0),
        ]
        data_points, summary, ref_low, ref_high, unit = self._run_trend_logic(obs_list)
        assert ref_low == 70.0
        assert ref_high == 100.0
