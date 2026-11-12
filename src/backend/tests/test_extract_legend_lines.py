"""HC-ELL: legend / target label lines are never read as test results (EXTRACT-LEGEND-LINES, owner LEGEND-LIST)."""
import io

import pytest

from modules.extract import ExtractModule
from tests.support.minimal_pdf import minimal_pdf

LEGEND_LINES = [
    "Target: 100 mg/dL",
    "Goal: 7.0 %",
    "Optimal: 100 mg/dL",
    "Desirable: 200 mg/dL",
    "Target 100 mg/dL",
    "Optimal 100 mg/dL",
    "Desirable 200 mg/dL",
    "Reference range: 70 mg/dL",
    "Normal: 5.7 %",
    "Reference: 70 mg/dL",
    "Recommended: 100 mg/dL",
    "Normal range: 70 mg/dL",
    "GOAL: 7.0 %",
    "Target.: 100 mg/dL",
]

RESULT_LINES = [
    ("Glucose: 95 mg/dL (70-100)", "Glucose", 95.0),
    ("Glucose 95 mg/dL (70-100)", "Glucose", 95.0),
    ("Hemoglobin A1c 5.6 % 4.0-5.6", "Hemoglobin A1c", 5.6),
    ("LDL Cholesterol: 162 mg/dL H", "LDL Cholesterol", 162.0),
    ("Target Cells 2 %", "Target Cells", 2.0),
    ("Normal Lymphocytes 30 %", "Normal Lymphocytes", 30.0),
    ("Goal LDL: 70 mg/dL", "Goal LDL", 70.0),
]


@pytest.mark.parametrize("line", LEGEND_LINES)
def test_hc_ell_001_label_line_is_not_a_result(line):
    assert ExtractModule()._parse_text_line(line, 1) is None


@pytest.mark.parametrize("line,name,value", RESULT_LINES)
def test_hc_ell_002_real_results_still_parse(line, name, value):
    obs = ExtractModule()._parse_text_line(line, 1)
    assert obs is not None
    assert (obs.analyte_raw, obs.value) == (name, value)


def test_hc_ell_002b_therapeutic_range_stays_none():
    assert ExtractModule()._parse_text_line("Therapeutic range 2.0 INR", 1) is None


@pytest.mark.asyncio
async def test_hc_ell_003_footer_legend_line_is_not_an_observation():
    pdf = minimal_pdf([["Glucose: 95 mg/dL (70-100)", "Target: 100 mg/dL"]])
    result = await ExtractModule().extract_from_pdf(io.BytesIO(pdf), "doc")
    assert [(o.analyte_raw, o.value) for o in result.observations] == [("Glucose", 95.0)]
