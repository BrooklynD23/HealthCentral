"""Comma-qualified analyte names (NORMALIZE-COMMA-NAMES, HC-NCN-001..004).

Labs print "Cholesterol, Total" / "Glucose, Serum". These must reach the
existing canonical analytes so trend grouping and unit conversion see one
series. Urine-qualified and front-qualified names must NOT merge into serum
analytes. Medical data path.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.normalize import NormalizeModule


def _assert_unmapped(raw: str) -> None:
    """Unknown-analyte fallback shape: raw-derived name, 'other', not a known key."""
    result = NormalizeModule().normalize_analyte(raw)
    assert result.canonical_name == raw.lower().strip().replace(" ", "_")
    assert result.category == "other"
    assert result.canonical_name not in NormalizeModule.ANALYTE_SYNONYMS
    assert result.display_name == raw.strip()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Cholesterol, Total", "total_cholesterol"),
        ("Glucose, Serum", "glucose"),
        ("Vitamin D, 25-Hydroxy", "vitamin_d"),
    ],
)
def test_hc_ncn_001_comma_names_map_to_existing_analyte(raw, expected):
    assert NormalizeModule().normalize_analyte(raw).canonical_name == expected


def test_hc_ncn_002_front_qualifier_not_stripped():
    _assert_unmapped("Urine, Protein")


def test_hc_ncn_003_existing_keys_and_synonyms_unchanged():
    module = NormalizeModule()
    for key, synonyms in NormalizeModule.ANALYTE_SYNONYMS.items():
        for name in (key, *synonyms):
            assert module.normalize_analyte(name).canonical_name == key, name


def test_hc_ncn_004_urine_qualifier_not_merged_into_serum():
    for raw in ("Glucose, Urine", "Creatinine, Urine", "Albumin, Urine"):
        _assert_unmapped(raw)
