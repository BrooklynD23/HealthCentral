"""Property tests for the lab extractor (HC-PROP-001..005, HYPOTHESIS-EXTRACT).

These pin current behaviour of ``modules/extract.py`` with Hypothesis.
HC-PROP-005 asserts ref_low <= ref_high: RANGE-ORDER is closed (owner answer
2026-11-07: swap the bounds; ref_range_text/provenance keep the printed order
verbatim).
"""

import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

from hypothesis import example, given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.extract import ExtractedObservation, ExtractModule

PROP_SETTINGS = dict(derandomize=True, database=None, max_examples=200, deadline=None)

_MODULE = ExtractModule()

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Formats copied from ExtractModule._normalize_date_str (extract.py).
_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%m-%d-%Y",
    "%m-%d-%y",
    "%B %d, %Y",
    "%B %d %Y",
    "%b %d, %Y",
    "%b %d %Y",
    "%d-%b-%Y",
]

_plausible_dates = st.dates(min_value=date(1950, 1, 1), max_value=date.today())

_lab_lines = st.builds(
    lambda name, sep, val, unit, lo, hi: f"{name}{sep}{val} {unit} ({lo}-{hi})",
    st.sampled_from(["Glucose", "HbA1c", "LDL Cholesterol", "TSH", "Hemoglobin", "Na"]),
    st.sampled_from([": ", " ", ":  ", "\t"]),
    st.one_of(st.integers(-1000, 10**9).map(str), st.floats(allow_nan=False).map(str), st.text(max_size=8)),
    st.sampled_from(["mg/dL", "%", "mmol/L", "", "x10^3/uL"]),
    st.one_of(st.integers(-100, 1000).map(str), st.text(max_size=5)),
    st.one_of(st.integers(-100, 1000).map(str), st.text(max_size=5)),
)


def _render(d: date, fmt: str) -> str:
    return datetime(d.year, d.month, d.day, 8, 30, 15).strftime(fmt)


@settings(**PROP_SETTINGS)
@given(line=st.one_of(st.text(), _lab_lines), page=st.integers(0, 1000))
def test_hc_prop_001_parse_text_line_never_raises(line, page):
    result = _MODULE._parse_text_line(line, page)
    assert result is None or isinstance(result, ExtractedObservation)


@settings(**PROP_SETTINGS)
@given(
    text=st.one_of(
        st.text(),
        st.builds(
            lambda pre, d, fmt, post: f"{pre} {_render(d, fmt)} {post}",
            st.text(max_size=40),
            _plausible_dates,
            st.sampled_from(_DATE_FORMATS),
            st.text(max_size=40),
        ),
        st.builds(
            lambda label, d, fmt: f"{label}: {_render(d, fmt)}",
            st.sampled_from(["Collected", "Collection Date", "Date of Service", "Drawn on"]),
            _plausible_dates,
            st.sampled_from(_DATE_FORMATS),
        ),
    )
)
def test_hc_prop_002_extract_dates_iso_and_plausible(text):
    for s in _MODULE._extract_dates(text):
        assert _ISO_RE.match(s), s
        parsed = datetime.strptime(s, "%Y-%m-%d")
        assert ExtractModule._date_is_plausible(parsed), s


@settings(**PROP_SETTINGS)
@given(d=_plausible_dates, fmt=st.sampled_from(_DATE_FORMATS))
def test_hc_prop_003_dob_date_never_returned(d, fmt):
    rendered = _render(d, fmt)
    result = _MODULE._extract_dates(f"DOB: {rendered}")
    assert d.isoformat() not in result, (rendered, result)


@settings(**PROP_SETTINGS)
@given(
    n=st.integers(0, 20000),
    label=st.sampled_from(
        ["Collected", "Collection Date", "Date of Service", "Specimen Date", "Drawn on", "Accession Date"]
    ),
)
def test_hc_prop_004_extract_dates_linear_on_padding(n, label):
    text = label + " " * n + "2024-01-15"
    start = time.perf_counter()
    _MODULE._extract_dates(text)
    assert time.perf_counter() - start < 1.0


@settings(**PROP_SETTINGS)
@given(line=_lab_lines)
@example("Glucose: 105 mg/dL (99-70)")
@example("Glucose 105 mg/dL (99-70)")
@example("Glucose 105 mg/dL 99-70")
def test_hc_prop_005_parsed_bounds_never_inverted(line):
    """HC-PROP-005 (RANGE-ORDER): a lab interval is low->high by definition, so
    no parsed observation may store ref_low > ref_high. The explicit examples
    cover the colon, alt and column forms of a backwards-printed "99-70"."""
    result = _MODULE._parse_text_line(line, 1)
    if result is not None and result.ref_low is not None and result.ref_high is not None:
        assert result.ref_low <= result.ref_high, (
            f"inverted bounds {result.ref_low}>{result.ref_high} from {line!r}"
        )
