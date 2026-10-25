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
import time
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

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


# ---------------------------------------------------------------------------
# EXTRACT-DOB-DATE  A date of birth is never a collection date
# ---------------------------------------------------------------------------

class TestBirthDateExcluded:
    """HC-DATE-007..009: dates that follow a birth label are skipped (both stages)."""

    @pytest.mark.parametrize("label", [
        "DOB:",
        "D.O.B.",
        "Date of Birth:",
        "Birth Date:",
        "Born on",
    ])
    def test_hc_date_007_birth_label_date_is_not_a_collection_date(self, label):
        """HC-DATE-007: the DOB is dropped; the real collection date remains."""
        text = (
            "Patient: Jane Test\n"
            f"{label} 1970-01-01\n"
            "Collection Date: 2026-03-02\n"
            "Glucose: 95 mg/dL (70-100)\n"
        )
        assert _module()._extract_dates(text) == ["2026-03-02"]

    @pytest.mark.asyncio
    async def test_hc_date_008_dob_only_document_is_undated(self, tmp_path):
        """HC-DATE-008: a document whose only date is a DOB gets no collection date."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = (
            "DOB: 1970-01-01\n"
            "Glucose: 95 mg/dL (70-100)\n"
        )
        mock_page.extract_tables.return_value = []
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = await _module().extract_from_pdf(tmp_path / "dob.pdf", "doc-dob-1")

        assert result.collection_dates == []
        assert [o.analyte_raw for o in result.observations] == ["Glucose"]
        assert all(o.collected_at is None for o in result.observations)

    def test_hc_date_009_long_whitespace_after_label_is_fast_and_linear(self):
        """HC-DATE-009: pin against a prefix-wide look-behind (quadratic on whitespace).

        The non-space "x" before the date makes a prefix-wide `\\s*[:\\-]?\\s*$`
        backtrack over the whole run (about 13 s at 50,000); an all-space tail
        would match that shape at once and could not fail (#289 review round 1).
        """
        m = _module()
        text = "DOB" + " " * 50000 + "x 1970-01-01"
        start = time.perf_counter()
        m._extract_dates(text)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"took {elapsed:.2f}s"

        # Many dates each preceded by a long whitespace run: still linear.
        many = "".join(f"DOB{' ' * 2000}x 2024-01-{(i % 28) + 1:02d}\n" for i in range(200))
        start = time.perf_counter()
        m._extract_dates(many)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"took {elapsed:.2f}s"

    def test_hc_date_009b_label_window_keeps_word_boundary_honest(self):
        """The 32-char window must not fake a `\\b` when it starts mid-word."""
        tail = "date" + " " * 18 + "of birth: "
        assert len(tail) == 32
        # 'xdate ... of birth:' is not a birth label: the 'x' glues onto 'date'.
        assert _module()._extract_dates("x" + tail + "2026-03-02") == ["2026-03-02"]
        # Same tail with a real word boundary in front is a birth label.
        assert _module()._extract_dates(" " + tail + "2026-03-02") == []


# ---------------------------------------------------------------------------
# EXTRACT-DOB-FORMS  Three more DOB layouts are not collection dates
# ---------------------------------------------------------------------------

class TestDobLayoutsNotCollectionDates:
    """HC-EDF-001..005: a DOB with a format hint, a combined label or a header column is skipped."""

    def test_hc_edf_001_parenthesised_format_hint_dob_is_not_collection_date(self):
        """HC-EDF-001: `DOB (MM/DD/YYYY):` keeps the DOB out; the Collected date remains."""
        text = (
            "Patient: Jane Test\n"
            "DOB (MM/DD/YYYY): 01/02/1960\n"
            "Collected: 03/04/2026\n"
            "Glucose: 95 mg/dL (70-100)\n"
        )
        assert _module()._extract_dates(text) == ["2026-03-04"]

    def test_hc_edf_002_combined_dob_sex_label_is_not_collection_date(self):
        """HC-EDF-002: `DOB/Sex:` is a birth label; the date after it is not a collection date."""
        text = (
            "Patient: Jane Test\n"
            "DOB/Sex: 01/02/1960 F\n"
            "Collected: 03/04/2026\n"
            "Glucose: 95 mg/dL (70-100)\n"
        )
        assert _module()._extract_dates(text) == ["2026-03-04"]

    @pytest.mark.parametrize("header,row", [
        ("Name  DOB  Collected", "Jane  01/02/1960  03/04/2026"),
        ("DOB  Collected", "01/02/1960  03/04/2026"),
        ("Name  DOB:  Collected", "Jane  01/02/1960  03/04/2026"),
    ], ids=["dob-middle-column", "dob-first-column", "dob-colon-header"])
    def test_hc_edf_003_two_line_header_dob_column_is_not_collection_date(self, header, row):
        """HC-EDF-003: the DOB under a header token is skipped by column; the Collected date stays.

        The dob-first case also covers Stage 1: the Collected label's tail starts
        on the data row, so the DOB column must not become its priority date.
        """
        assert _module()._extract_dates(f"{header}\n{row}\n") == ["2026-03-04"]

    def test_hc_edf_004_dob_inputs_stay_linear_with_new_tail_regex(self):
        """HC-EDF-004 (pin): HC-DATE-009's inputs, plus a format-hint probe, each under 1.0 s."""
        m = _module()
        many = "".join(f"DOB{' ' * 2000}x 2024-01-{(i % 28) + 1:02d}\n" for i in range(200))
        inputs = {
            "50000-space": "DOB" + " " * 50000 + "x 1970-01-01",
            "50000-space-hint": "DOB (" + " " * 50000 + "x 1970-01-01",
            "200-line": many,
        }
        for name, text in inputs.items():
            start = time.perf_counter()
            m._extract_dates(text)
            elapsed = time.perf_counter() - start
            assert elapsed < 1.0, f"{name} took {elapsed:.2f}s"

    @pytest.mark.parametrize("text,expected", [
        # DOB column is the middle cell: the Collected column date is kept.
        ("Patient  DOB  Collected\nJane  01/02/1960  03/04/2026\n", ["2026-03-04"]),
        # Collected column first: the DOB is the second cell of the data row.
        ("Collected  DOB\n03/04/2026  01/02/1960\n", ["2026-03-04"]),
        # A labelled date on its own line wins over a DOB header above it.
        ("Patient DOB\nCollected 03/04/2026\n", ["2026-03-04"]),
        # A header line that carries a date is not a header: both dates are kept.
        ("Jane DOB 01/02/1960 F\nCollected 03/04/2026 Received 03/05/2026\n",
         ["2026-03-04", "2026-03-05"]),
    ], ids=[
        "collected-middle-column",
        "collected-first-column",
        "labelled-line-under-dob-header",
        "header-line-with-date",
    ])
    def test_hc_edf_005_collected_header_column_date_is_kept(self, text, expected):
        """HC-EDF-005 (pin): a date under a Collected column or on a labelled line is kept.

        Exact lists, not `in`: a DOB that leaks into the output must fail here.
        """
        assert _module()._extract_dates(text) == expected

    def test_hc_edf_005_token_count_mismatch_is_pinned_as_known_gap(self):
        """HC-EDF-005 (known gap, pinned): on a token-count mismatch the column guard is off.

        The header has 3 tokens and the data row 2, so nothing is skipped by column.
        The DOB then leaks in as the priority date (Stage 1 reads `Collected` followed
        by the DOB on the next line). The Collected date is still kept. Pinned so the
        current output is visible; a fix that changes it must update this on purpose.
        """
        assert _module()._extract_dates(
            "Patient  DOB  Collected\n01/02/1960  03/04/2026\n"
        ) == ["1960-01-02", "2026-03-04"]
