"""HC-LTC: a table row named by a label word is never a test result (LEGEND-TABLE-CELLS, owner LEGEND-LIST (a))."""
from unittest.mock import MagicMock, patch

import pytest

from modules.extract import ExtractModule

HEADER = ["Test", "Result", "Units", "Reference Range"]
LABEL_NAMES = ["Target", "Reference range", "Goal:", "NORMAL"]


def _table(*rows):
    return [HEADER, *rows]


@pytest.mark.parametrize("name", LABEL_NAMES)
@pytest.mark.parametrize("value", ["100", ""])
def test_hc_ltc_001_label_named_row_is_not_an_observation(name, value):
    table = _table([name, value, "mg/dL", ""])
    assert ExtractModule()._extract_from_table(table, 1, "doc") == []


@pytest.mark.parametrize(
    "name,value",
    [("Target Cells", 2.0), ("Normal Lymphocytes", 30.0), ("Goal LDL", 70.0)],
)
def test_hc_ltc_002_real_names_with_label_first_word_still_parse(name, value):
    table = _table(["Glucose", "95", "mg/dL", "70-100"], [name, str(value), "%", ""])
    obs = ExtractModule()._extract_from_table(table, 1, "doc")
    assert [(o.analyte_raw, o.value) for o in obs] == [("Glucose", 95.0), (name, value)]


@pytest.mark.asyncio
async def test_hc_ltc_003_label_rows_dropped_end_to_end(tmp_path):
    page = MagicMock()
    page.extract_text.return_value = ""
    page.extract_tables.return_value = [
        _table(
            ["Glucose", "95", "mg/dL", "70-100"],
            ["Target", "100", "mg/dL", ""],
            ["Reference range", "70", "mg/dL", ""],
            ["Goal:", "", "", ""],
            ["NORMAL", "5.7", "%", ""],
        )
    ]
    pdf = MagicMock()
    pdf.pages = [page]
    pdf.__enter__ = MagicMock(return_value=pdf)
    pdf.__exit__ = MagicMock(return_value=False)
    with patch("pdfplumber.open", return_value=pdf):
        result = await ExtractModule().extract_from_pdf(tmp_path / "a.pdf", "doc")
    assert [(o.analyte_raw, o.value) for o in result.observations] == [("Glucose", 95.0)]
