"""EXTRACT-REGEX-NEWLINES: imaging and visit-note section patterns on newline runs."""

import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

from modules import extract_imaging, extract_visit_notes
from modules.extract_imaging import extract_imaging_entities
from modules.extract_visit_notes import extract_visit_note_entities

BACKEND_DIR = Path(__file__).resolve().parent.parent

_IMG = ("modules.extract_imaging", "extract_imaging_entities")
_VIS = ("modules.extract_visit_notes", "extract_visit_note_entities")

# label -> (module, function, entity_type)
_KIND = {
    "FINDINGS": (*_IMG, "finding"),
    "IMPRESSION": (*_IMG, "impression"),
    "ASSESSMENT": (*_VIS, "assessment"),
    "PLAN": (*_VIS, "plan"),
    "VITALS": (*_VIS, "vitals"),
}

_CHILD = (
    "import sys, time\n"
    "from {mod} import {fn}\n"
    "t = sys.stdin.read()\n"
    "s = time.perf_counter()\n"
    "e = {fn}(t)\n"
    "d = time.perf_counter() - s\n"
    "print(d, sum(1 for x in e if x['entity_type'] == {et!r}))\n"
)


def _run_child(label, text):
    mod, fn, et = _KIND[label]
    try:
        r = subprocess.run(
            [sys.executable, "-c", _CHILD.format(mod=mod, fn=fn, et=et)],
            input=text, cwd=BACKEND_DIR, timeout=10, capture_output=True, text=True,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"{label} pattern did not finish within 10 s (ReDoS)")
    assert r.returncode == 0, r.stderr
    return float(r.stdout.split()[0])


_LABELS = ["FINDINGS", "IMPRESSION", "ASSESSMENT", "PLAN", "VITALS"]


@pytest.mark.parametrize(
    "label,run",
    [(lb, run) for lb in _LABELS for run in ("\n", " \n")],
    ids=[f"{lb}-{n}" for lb in _LABELS for n in ("nl50000", "spnl50000")],
)
def test_hc_enl_001_linear_on_newline_runs(label, run):
    assert _run_child(label, label + ":x" + run * 50000) < 1.0


@pytest.mark.parametrize(
    "label,text",
    [
        ("FINDINGS", "FINDINGS:" + " \n" * 16000),
        ("IMPRESSION", "IMPRESSION:" + "\n" * 50000),
        ("ASSESSMENT", "ASSESSMENT:" + " \n" * 16000),
        ("PLAN", "PLAN:" + "\t\n " * 20000),
        ("VITALS", "VITALS:" + " \n" * 16000),
        ("ASSESSMENT", "ASSESSMENT: " * 20000),
    ],
    ids=["findings-empty-spnl16000", "impression-empty-nl50000",
         "assessment-empty-spnl16000", "plan-empty-tabnlsp20000",
         "vitals-empty-spnl16000", "assessment-repeated-labels20000"],
)
def test_hc_enl_002_whitespace_and_repeated_labels_linear(label, text):
    assert _run_child(label, text) < 1.0


def _entities(label, text):
    fn = extract_imaging_entities if _KIND[label][0] == _IMG[0] else extract_visit_note_entities
    return [e for e in fn(text) if e["entity_type"] == _KIND[label][2]]


@pytest.mark.parametrize(
    "label,text",
    [
        ("FINDINGS", "FINDINGS:   \n\n"),
        ("FINDINGS", "Findings"),
        ("IMPRESSION", "IMPRESSION:"),
        ("ASSESSMENT", "ASSESSMENT:" + " \n" * 1000),
        ("ASSESSMENT", "A/P:"),
        ("PLAN", "PLAN:   \n\n"),
        ("VITALS", "Vitals"),
        ("VITALS", "VITAL SIGNS: \t\n"),
    ],
    ids=["findings-blank-nls", "findings-no-colon", "impression-bare", "assessment-spnl1000",
         "ap-bare", "plan-blank-nls", "vitals-no-colon", "vital-signs-tab-nl"],
)
def test_hc_enl_003_empty_label_gives_no_entity(label, text):
    assert _entities(label, text) == []


_BODY_OLD = r"(.+?)(?=\n\s*[A-Z]{2,}|\Z)"
_OLD = {
    "FINDINGS": (extract_imaging, "FINDINGS_PATTERN", r"FINDINGS?:?\s*" + _BODY_OLD),
    "IMPRESSION": (extract_imaging, "IMPRESSION_PATTERN", r"IMPRESSION:?\s*" + _BODY_OLD),
    "ASSESSMENT": (extract_visit_notes, "ASSESSMENT_PATTERN",
                   r"(?:ASSESSMENT|A/P|ASSESSMENT\s+AND\s+PLAN):?\s*"
                   r"(.+?)(?=\n\s*(?:PLAN|[A-Z]{2,})|\Z)"),
    "PLAN": (extract_visit_notes, "PLAN_PATTERN", r"(?:PLAN):?\s*" + _BODY_OLD),
    "VITALS": (extract_visit_notes, "VITALS_PATTERN",
               r"(?:VITAL\s+SIGNS?|VITALS?):?\s*" + _BODY_OLD),
}
_TOKENS = [
    "FINDINGS", "Findings", "finding", "IMPRESSION", "Impression", "ASSESSMENT", "A/P",
    "Assessment and Plan", "PLAN", "plan", "explanation", "VITALS", "Vital signs", ":",
    " ", "\t", "\n", "\n\n", "\r", "AB", "Ab", "x", "a", ".", "1",
]


def _observable(text, m):
    """(trimmed start, trimmed end, stripped group 1), trimming as with_span does."""
    if m is None:
        return None
    start, end = m.span()
    raw = text[start:end]
    start += len(raw) - len(raw.lstrip())
    end -= len(raw) - len(raw.rstrip())
    if start >= end:
        start = end = None
    return (start, end, m.group(1).strip())


@pytest.mark.parametrize("label", _LABELS)
def test_hc_enl_004_new_pattern_matches_old_except_empty_values(label):
    mod, name, src = _OLD[label]
    old = re.compile(src, re.DOTALL | re.IGNORECASE)
    new = getattr(mod, name)
    rng = random.Random(5)
    differences = 0
    for _ in range(20000):
        t = "".join(rng.choice(_TOKENS) for _ in range(rng.randint(1, 12)))
        old_v, new_v = _observable(t, old.search(t)), _observable(t, new.search(t))
        if old_v == new_v:
            continue
        assert old_v is not None and old_v[2] in ("", ":", "s", "S") and new_v is None, (
            t, old_v, new_v)
        differences += 1
    print(f"HC-ENL-004 {name}: {differences} differences of 20000")


@pytest.mark.parametrize(
    "label,text,value,span",
    [
        ("FINDINGS", "FINDINGS: No acute fracture.\nIMPRESSION: Normal study.",
         "No acute fracture.", (0, 28)),
        ("IMPRESSION", "FINDINGS: No acute fracture.\nIMPRESSION: Normal study.",
         "Normal study.", (29, 54)),
        ("FINDINGS", "Findings:\n  Mild degenerative change.\n  1. small effusion\nIMPRESSION: ok",
         "Mild degenerative change.\n  1. small effusion", (0, 57)),
        ("FINDINGS", "FINDINGS:  Lungs clear.  \n\nIMPRESSION: none", "Lungs clear.", (0, 23)),
        ("ASSESSMENT", "ASSESSMENT: Type 2 diabetes, stable.\nPLAN: Continue metformin.",
         "Type 2 diabetes, stable.", (0, 36)),
        ("PLAN", "ASSESSMENT: Type 2 diabetes, stable.\nPLAN: Continue metformin."
                 "\nFOLLOW-UP: 3 months", "Continue metformin.", (37, 62)),
        ("ASSESSMENT", "A/P: Hypertension\n  - continue lisinopril\nVITALS: BP 130/80",
         "Hypertension\n  - continue lisinopril", (0, 41)),
        ("VITALS", "VITAL SIGNS: BP 120/80, HR 72\nASSESSMENT: well", "BP 120/80, HR 72", (0, 29)),
        ("VITALS", "Vitals: BP 118/76  \n HR 70\nPLAN: none", "BP 118/76", (0, 17)),
    ],
    ids=["finding-simple", "impression-simple", "finding-multiline", "finding-blank-line",
         "assessment-simple", "plan-followup", "ap-multiline", "vital-signs", "vitals-trailing"],
)
def test_hc_enl_005_values_and_spans_pinned(label, text, value, span):
    got = _entities(label, text)
    assert [e["entity_value"] for e in got] == [value]
    assert (got[0]["char_start"], got[0]["char_end"]) == span
