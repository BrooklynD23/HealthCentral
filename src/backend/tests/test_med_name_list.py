"""MED-NAME-LIST: a curated drug-name list widens the medication cue (names only).

HC-MNL-001  "Can I take ibuprofen?" is a medication question
HC-MNL-002  labelled_names_v1 positives (generic, brand, multi-word) -> medication
HC-MNL-003  labelled_v1 verdicts are identical before/after (flip count printed)
HC-MNL-004  negatives stay none (incl. the out-of-scope 'more insulin' frame-gap pin)
HC-MNL-005  data file loads: lowercase, unique, sorted; the old cue names are in it
HC-MNL-006  word boundaries
HC-MNL-007  before/after report; a missing or empty list fails closed at import
"""

from __future__ import annotations

import importlib
import json
import re
from pathlib import Path

import pytest

from modules.agent.guardrails import classifier as classifier_module
from modules.agent.guardrails.classifier import classify_advice

TESTS = Path(__file__).resolve().parent
FIX = TESTS / "fixtures" / "advice_classifier"
NAMES = json.loads((FIX / "labelled_names_v1.json").read_text())["entries"]
LABELLED = json.loads((FIX / "labelled_v1.json").read_text())["entries"]
LIST_FILE = Path(classifier_module.__file__).parent / "data" / "rxnorm_names.txt"
POSITIVES = [e for e in NAMES if e["expect"] == "advice"]
NEGATIVES = [e for e in NAMES if e["expect"] == "none"]


def _names() -> list[str]:
    return [l for l in LIST_FILE.read_text().splitlines() if l and not l.startswith("#")]


def test_hc_mnl_001_ibuprofen_is_medication():
    assert classify_advice("Can I take ibuprofen?").category == "medication"


@pytest.mark.parametrize("entry", POSITIVES, ids=[e["id"] for e in POSITIVES])
def test_hc_mnl_002_named_drug_positives(entry):
    v = classify_advice(entry["question"])
    assert (v.is_advice_seeking, v.category) == (True, "medication"), entry["question"]


def test_hc_mnl_003_labelled_v1_unchanged():
    """Every labelled_v1 entry still gets its label (owner-decides entries are not asserted)."""
    flips = []
    for e in LABELLED:
        if e["expect"] == "owner":
            continue
        if "draft_ref" in e:
            mod, name = e["draft_ref"].split(":")
            text = getattr(importlib.import_module(mod), name)
        else:
            text = e.get("question") or e["draft_sentence"]
        v = classify_advice(text)
        got = v.category if v.is_advice_seeking else "none"
        want = e["category"] if e["expect"] == "advice" else "none"
        if got != want:
            flips.append((e["id"], want, got))
    print(f"labelled_v1 flips after name list: {len(flips)}")
    assert flips == []


@pytest.mark.parametrize("entry", NEGATIVES, ids=[e["id"] for e in NEGATIVES])
def test_hc_mnl_004_negatives_stay_none(entry):
    v = classify_advice(entry["question"])
    assert (v.is_advice_seeking, v.category) == (False, "none"), entry["question"]


def test_hc_mnl_005_data_file_shape():
    names = _names()
    assert 300 <= len(names) <= 600
    assert names == sorted(set(names))
    assert all(n == n.lower() and n == n.strip() for n in names)
    for old in ("metformin", "lisinopril", "insulin"):
        assert old in names


def test_hc_mnl_006_word_boundaries():
    assert classify_advice("Can I take folic acid daily?").category == "medication"
    assert classify_advice("Can I take Advil?").category == "medication"
    assert classify_advice("Can I take badvil?").category == "none"
    assert classify_advice("Can I take acetaminophenx?").category == "none"
    assert classify_advice("Can I get some advice?").category == "none"


def test_hc_mnl_007_report_and_fail_closed(monkeypatch):
    newly = [e["id"] for e in POSITIVES if classify_advice(e["question"]).category == "medication"]
    print(f"newly medication: {len(newly)}/{len(POSITIVES)}; labelled_v1 entries re-run: {len(LABELLED)}")
    assert len(newly) == len(POSITIVES)
    real = Path.read_text
    try:
        monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: "# only a comment\n" if self.name == "rxnorm_names.txt" else real(self, *a, **k))
        with pytest.raises(Exception):
            importlib.reload(classifier_module)
        monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: (_ for _ in ()).throw(FileNotFoundError()) if self.name == "rxnorm_names.txt" else real(self, *a, **k))
        with pytest.raises(FileNotFoundError):
            importlib.reload(classifier_module)
    finally:
        monkeypatch.undo()
        importlib.reload(classifier_module)
