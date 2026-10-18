"""HC-M06 extraction golden set (HC-EXTR-NNN).

Synthetic, fictional lab reports rendered to real PDFs at test time and run
through ExtractModule.extract_from_pdf (pdfplumber). Precision/recall per field,
thresholds from the measured baseline (never lowered), and a check that the eval
card at docs/agentic/eval-cards/extraction.md matches what the code measures.

Measured baseline (dataset 2026.10-v1, Python 3.11.17), identical for each field:
    tp=26 fp=0 fn=2  ->  precision 1.00, recall 26/28 = 0.9286
Rule (owner S-C3-2): measured - 0.05, floored to 2 decimals, never lowered:
    precision 1.00 -> 0.95;  recall 0.9286 - 0.05 = 0.8786 -> 0.87
"""

from __future__ import annotations

import asyncio
import io
import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pdfplumber
import pytest

from modules.extract import ExtractModule
from tests.support.minimal_pdf import minimal_pdf

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "extraction_golden"
MANIFEST = json.loads((GOLDEN_DIR / "manifest.json").read_text(encoding="utf-8"))
CARD = Path(__file__).resolve().parents[3] / "docs" / "agentic" / "eval-cards" / "extraction.md"
FIELDS = ("analyte", "unit", "date")
IDENTIFIER_LABELS = re.compile(r"(?i)\b(patient|name|dob|birth|mrn|ssn|address|phone|email)\b")
# (min precision, min recall) per field; derived per the module docstring. Never lower.
THRESHOLDS: dict[str, tuple[float, float]] = {
    "analyte": (0.95, 0.87),
    "unit": (0.95, 0.87),
    "date": (0.95, 0.87),
}


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def test_hc_extr_001_golden_set_is_synthetic_and_renders():
    assert MANIFEST["synthetic"] is True
    assert re.fullmatch(r"\d{4}\.\d{2}-v\d+", MANIFEST["dataset_version"])
    ids = [d["id"] for d in MANIFEST["documents"]]
    assert len(ids) == len(set(ids)) >= 8
    for doc in MANIFEST["documents"]:
        lines = [line for page in doc["pages"] for line in page]
        assert not [l for l in lines if IDENTIFIER_LABELS.search(l)], doc["id"]
        with pdfplumber.open(io.BytesIO(minimal_pdf(doc["pages"]))) as pdf:
            text = _norm("\n".join(p.extract_text() or "" for p in pdf.pages))
        for line in lines:
            assert _norm(line) in text, (doc["id"], line)


@lru_cache(maxsize=1)
def _score() -> dict[str, dict[str, int]]:
    totals = {f: {"tp": 0, "fp": 0, "fn": 0} for f in FIELDS}
    for doc in MANIFEST["documents"]:
        result = asyncio.run(ExtractModule().extract_from_pdf(io.BytesIO(minimal_pdf(doc["pages"])), doc["id"]))
        for field in FIELDS:
            def exp_key(e):
                return (_norm(e["analyte"]),) if field == "analyte" else (_norm(e["analyte"]), e[field])
            def got_key(o):
                if field == "analyte":
                    return (_norm(o.analyte_raw),)
                return (_norm(o.analyte_raw), o.unit if field == "unit" else o.collected_at)
            expected = Counter(exp_key(e) for e in doc["expected"])
            got = Counter(got_key(o) for o in result.observations)
            tp = sum((expected & got).values())
            totals[field]["tp"] += tp
            totals[field]["fp"] += sum(got.values()) - tp
            totals[field]["fn"] += sum(expected.values()) - tp
    return totals


@pytest.mark.parametrize("field", FIELDS)
def test_hc_extr_002_precision_recall_meet_thresholds(field):
    c = _score()[field]
    assert field in THRESHOLDS, f"no threshold recorded for {field}; measured {c}"
    precision = c["tp"] / (c["tp"] + c["fp"]) if (c["tp"] + c["fp"]) else 0.0
    recall = c["tp"] / (c["tp"] + c["fn"])
    min_p, min_r = THRESHOLDS[field]
    assert precision >= min_p, f"{field}: precision {precision:.2f} < {min_p} ({c}); never lower the bar"
    assert recall >= min_r, f"{field}: recall {recall:.2f} < {min_r} ({c}); never lower the bar"


def _card_block() -> dict:
    text = CARD.read_text(encoding="utf-8")
    m = re.search(r"<!-- eval-card:current:start -->\s*```json\s*(\{.*?\})\s*```\s*<!-- eval-card:current:end -->", text, re.S)
    assert m, f"{CARD} has no eval-card:current block"
    return json.loads(m.group(1))


def test_hc_extr_003_eval_card_matches_measurement():
    measured = {
        "dataset_version": MANIFEST["dataset_version"],
        "parser_version": ExtractModule().parser_version,
        "fields": _score(),
    }
    assert _card_block() == measured, "eval card is stale; record a run with:\n" + json.dumps(measured, indent=2)
    assert f"| {MANIFEST['dataset_version']} |" in CARD.read_text(encoding="utf-8"), "no run-log row for this dataset version"
