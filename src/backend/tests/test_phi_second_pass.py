"""RSI1-DONATE PR-2 Task 3: second PHI detector and recall (HC-DON-010..013)."""

from __future__ import annotations

import json
import subprocess
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
    out = subprocess.run(
        ["git", "grep", "--untracked", "-nE", r"^(from|import) modules\.redaction", "--", "modules/phi_second_pass.py"],
        cwd=BACKEND, capture_output=True, text=True,
    )
    assert out.returncode == 1 and out.stdout == ""


def test_hc_don_013_corpus_meets_recall_target():
    from scripts.measure_phi_recall import meets_target, measure

    result = measure(_corpus())
    assert meets_target(result), result
