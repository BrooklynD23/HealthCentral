"""RSI1-DONATE PR-2 Task 3: second PHI detector and recall (HC-DON-010..013)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

CORPUS = Path(__file__).parent / "fixtures/phi_recall/corpus_v1.json"
BACKEND = Path(__file__).parent.parent


def _corpus() -> dict:
    return json.loads(CORPUS.read_text())


def test_hc_don_010_detects_each_category_and_no_false_positive_on_labs():
    from modules.phi_second_pass import CATEGORIES, detect

    corpus = _corpus()
    assert set(corpus["categories"]) == set(CATEGORIES)
    for category, items in corpus["categories"].items():
        assert items, category
        for item in items:
            hits = detect(item["text"])
            assert category in {h.category for h in hits}, (category, item["text"])
            # a hit never carries the matched value
            assert all(set(vars(h)) == {"category"} for h in hits)
    non_phi = corpus["non_phi"]
    assert len(non_phi) == 20
    assert [s for s in non_phi if detect(s)] == []
    assert detect("") == [] and detect(None) == []


def test_hc_don_010_uncued_name_pairs_flagged():
    from modules.phi_second_pass import detect

    for text in ("Jane Doe, your LDL is 162 mg/dL.", "Hi John Smith. Your hemoglobin is within range."):
        assert "name" in {h.category for h in detect(text)}, text


def test_hc_don_010_lab_prose_not_flagged_as_name():
    from modules.phi_second_pass import detect

    prose = [
        "PT Results are back. Hemoglobin A1c is 6.8 %.",
        "Vitamin D 22 ng/mL is low. Dr. visits are advised.",
        "Total Cholesterol 214 mg/dL is borderline.",
        "White Blood Cells 11.2 are mildly high; see the Reference Range.",
        "Reference Range for Hemoglobin is 12.0-15.5.",
        "Blood Pressure 128/82 and Heart Rate 72 were recorded.",
    ]
    assert [t for t in prose if "name" in {h.category for h in detect(t)}] == []


def test_hc_don_011_recall_report_can_fail():
    from scripts.measure_phi_recall import measure

    toy = {"categories": {"phone": [
        {"text": "Call 555-123-4567 now.", "planted": "555-123-4567", "canary": True},
        {"text": "Mobile 415.555.0142 works.", "planted": "415.555.0142"},
        {"text": "Ring five five five oh one two three four.", "planted": "five five five oh one two three four"},
    ]}}
    row = measure(toy)["phone"]
    assert (row["union"], row["n"]) == (2, 3)
    assert row["second"] == 2
    assert row["canary_union"] == row["canary_n"] == 1


def test_hc_don_012_second_pass_does_not_import_redaction():
    import ast

    tree = ast.parse((BACKEND / "modules/phi_second_pass.py").read_text())
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names += [node.module or ""] + [a.name for a in node.names]
    assert not [n for n in names if "redaction" in n], names


def test_second_pass_email_scan_is_linear_enough():
    import time

    from modules.phi_second_pass import detect

    start = time.perf_counter()
    detect("a." * 25000)
    assert time.perf_counter() - start < 1.0


def test_hc_don_013_corpus_meets_recall_target():
    from scripts.measure_phi_recall import measure, meets_target

    result = measure(_corpus())
    assert meets_target(result), result
