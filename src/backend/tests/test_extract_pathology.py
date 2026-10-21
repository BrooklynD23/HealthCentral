"""Tests for pathology entity extractor."""

import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

from modules import extract_pathology
from modules.extract_pathology import extract_pathology_entities


class TestExtractPathologyEntities:
    def test_extracts_specimen_type(self):
        text = "SURGICAL PATHOLOGY\nSPECIMEN: Left breast biopsy\nDIAGNOSIS: Benign"
        entities = extract_pathology_entities(text)
        types = [e for e in entities if e["entity_type"] == "specimen_type"]
        assert len(types) == 1
        assert types[0]["entity_value"] == "biopsy"

    def test_extracts_diagnosis(self):
        text = "DIAGNOSIS: Invasive ductal carcinoma, grade 2\nMARGINS: Clear"
        entities = extract_pathology_entities(text)
        dx = [e for e in entities if e["entity_type"] == "diagnosis"]
        assert len(dx) == 1
        assert "ductal carcinoma" in dx[0]["entity_value"]

    def test_extracts_margins(self):
        text = "DIAGNOSIS: Carcinoma\nMARGINS: Negative for tumor, closest margin 2mm"
        entities = extract_pathology_entities(text)
        margins = [e for e in entities if e["entity_type"] == "margins"]
        assert len(margins) == 1
        assert "Negative" in margins[0]["entity_value"]

    def test_extracts_stage(self):
        text = "DIAGNOSIS: Adenocarcinoma\nStage: pT2N0M0"
        entities = extract_pathology_entities(text)
        stage = [e for e in entities if e["entity_type"] == "stage"]
        assert len(stage) == 1
        assert "pT2N0M0" in stage[0]["entity_value"]

    def test_empty_text_returns_empty(self):
        entities = extract_pathology_entities("")
        assert entities == []


BACKEND_DIR = Path(__file__).resolve().parent.parent

_CHILD = (
    "import time\n"
    "from modules.extract_pathology import extract_pathology_entities\n"
    "t = {text!r}\n"
    "s = time.perf_counter()\n"
    "e = extract_pathology_entities(t)\n"
    "d = time.perf_counter() - s\n"
    "print(d, any(x['entity_type'] == 'grade' for x in e))\n"
)


@pytest.mark.parametrize(
    "text",
    ["grade" + " " * 1600 + "x", "grade " * 8000, "grade" + " " * 100000 + "x"],
    ids=["spaces-1600", "grade-x8000", "spaces-100000"],
)
def test_hc_path_001_grade_pattern_linear_on_whitespace_runs(text):
    try:
        r = subprocess.run(
            [sys.executable, "-c", _CHILD.format(text=text)],
            cwd=BACKEND_DIR, timeout=10, capture_output=True, text=True,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("GRADE_PATTERN did not finish within 10 s (ReDoS)")
    assert r.returncode == 0, r.stderr
    secs, has_grade = r.stdout.split()
    assert float(secs) < 1.0
    assert has_grade == "False"


_OLD_GRADE = re.compile(
    r"\b(?:grade|Gleason|Nottingham)\s*:?\s*([\w\s/\+]+?)(?:\n|[,;.])",
    re.IGNORECASE,
)
_TOKENS = ["grade", "Gleason", "Nottingham", " ", "\t", "\n", ":", ",", ".", ";",
           "x", "2", "3+4", "/", "-", "=", "II", "score"]


def test_hc_path_002_new_pattern_matches_old_except_empty_values():
    rng = random.Random(1)
    new = extract_pathology.GRADE_PATTERN
    for _ in range(20000):
        t = "".join(rng.choice(_TOKENS) for _ in range(rng.randint(1, 10)))
        old_m, new_m = _OLD_GRADE.search(t), new.search(t)
        old_v = (old_m.start(), old_m.end(), old_m.group(1).strip()) if old_m else None
        new_v = (new_m.start(), new_m.end(), new_m.group(1).strip()) if new_m else None
        if old_v is not None and old_v[2] == "":
            continue
        assert old_v == new_v, t


def _grade(text):
    return [e for e in extract_pathology_entities(text) if e["entity_type"] == "grade"]


@pytest.mark.parametrize(
    "text,value",
    [
        ("Gleason score 3+4, grade group 2", "score 3+4"),
        ("Nottingham grade 2.", "grade 2"),
        ("Grade: 3\n", "3"),
        ("Grade:\n\nII.", "II"),
        ("GRADE: well differentiated (G1);", None),
        ("grade 2", None),
        ("Grade: ,\nGleason 4+3.", "4+3"),
    ],
)
def test_hc_path_003_grade_values(text, value):
    g = _grade(text)
    if value is None:
        assert g == []
    else:
        assert [e["entity_value"] for e in g] == [value]


def test_hc_path_003_grade_value_and_span():
    g = _grade("Histologic grade: 2/3\nMARGINS: clear")
    assert [e["entity_value"] for e in g] == ["2/3"]
    assert (g[0]["char_start"], g[0]["char_end"]) == (11, 21)  # match "grade: 2/3\n" trimmed by with_span


# --- PATH-REGEX-NEWLINES: DIAGNOSIS / SPECIAL_STAINS on newline runs ---------

_CHILD_DX = (
    "import time\n"
    "from modules.extract_pathology import extract_pathology_entities\n"
    "import sys\n"
    "t = sys.stdin.read()\n"
    "s = time.perf_counter()\n"
    "e = extract_pathology_entities(t)\n"
    "d = time.perf_counter() - s\n"
    "print(d, sum(1 for x in e if x['entity_type'] in ('diagnosis', 'special_stains')))\n"
)


@pytest.mark.parametrize(
    "text",
    [
        "DIAGNOSIS:x" + "\n" * 50000,
        "DIAGNOSIS:x" + " \n" * 50000,
        "IHC:x" + "\n" * 50000,
        "IHC:x" + " \n" * 50000,
        "DIAGNOSIS:" + " \n" * 16000,
        "DIAGNOSIS:" + "\n" * 50000,
        "IHC:" + " \n" * 16000,
        "Special stains:" + "\t\n " * 20000,
    ],
    ids=[
        "dx-x-nl50000", "dx-x-spnl50000", "ihc-x-nl50000", "ihc-x-spnl50000",
        "dx-empty-spnl16000", "dx-empty-nl50000", "ihc-empty-spnl16000",
        "stains-empty-tabnlsp20000",
    ],
)
def test_hc_path_004_diagnosis_and_stains_linear_on_newline_runs(text):
    try:
        r = subprocess.run(
            [sys.executable, "-c", _CHILD_DX],
            input=text, cwd=BACKEND_DIR, timeout=10, capture_output=True, text=True,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("DIAGNOSIS/SPECIAL_STAINS pattern did not finish within 10 s (ReDoS)")
    assert r.returncode == 0, r.stderr
    secs, _count = r.stdout.split()
    assert float(secs) < 1.0


def _dx_stains(text):
    return [
        e for e in extract_pathology_entities(text)
        if e["entity_type"] in ("diagnosis", "special_stains")
    ]


@pytest.mark.parametrize(
    "text",
    [
        "DIAGNOSIS:   \n\n",
        "FINAL DIAGNOSIS:",
        "IHC: \t\n",
        "Special stains:",
        "Special stains",
        "DIAGNOSIS:" + " \n" * 1000,
    ],
    ids=["dx-blank-nls", "final-dx-bare", "ihc-tab-nl", "stains-bare-colon",
         "stains-no-colon", "dx-empty-spnl1000"],
)
def test_hc_path_005_empty_label_gives_no_entity(text):
    assert _dx_stains(text) == []


_OLD_DX = re.compile(
    r"(?:DIAGNOSIS|FINAL DIAGNOSIS|PATHOLOGIC DIAGNOSIS):?\s*(.+?)(?=\n\s*[A-Z]{2,}|\Z)",
    re.DOTALL | re.IGNORECASE,
)
_OLD_STAINS = re.compile(
    r"(?:SPECIAL\s+STAINS?|IMMUNOHISTOCHEMISTRY|IHC):?\s*(.+?)(?=\n\s*[A-Z]{2,}|\Z)",
    re.DOTALL | re.IGNORECASE,
)
_PATH_TOKENS = [
    "DIAGNOSIS", "diagnosis", "IHC", "Special stains", "FINAL DIAGNOSIS", ":", " ",
    "\t", "\n", "\n\n", "\r", "AB", "Ab", "x", "MARGINS", "a", ".", "1",
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


@pytest.mark.parametrize(
    "old,new_name",
    [(_OLD_DX, "DIAGNOSIS_PATTERN"), (_OLD_STAINS, "SPECIAL_STAINS_PATTERN")],
    ids=["diagnosis", "special-stains"],
)
def test_hc_path_005b_new_patterns_match_old_except_empty_values(old, new_name):
    rng = random.Random(5)
    new = getattr(extract_pathology, new_name)
    differences = 0
    for _ in range(20000):
        t = "".join(rng.choice(_PATH_TOKENS) for _ in range(rng.randint(1, 12)))
        old_v, new_v = _observable(t, old.search(t)), _observable(t, new.search(t))
        if old_v == new_v:
            continue
        assert old_v is not None and old_v[2] in ("", ":", "s") and new_v is None, (
            t, old_v, new_v)
        differences += 1
    print(f"HC-PATH-005b {new_name}: {differences} differences of 20000")


@pytest.mark.parametrize(
    "text,etype,value",
    [
        ("DIAGNOSIS: Invasive ductal carcinoma, grade 2\nMARGINS: Clear",
         "diagnosis", "Invasive ductal carcinoma, grade 2"),
        ("FINAL DIAGNOSIS: Benign tissue.\n\nMARGINS: clear", "diagnosis", "Benign tissue."),
        ("IHC: CK7 positive  \n GRADE: 2", "special_stains", "CK7 positive"),
        ("DIAGNOSIS: carcinoma\n  1. with necrosis\nMARGINS: clear",
         "diagnosis", "carcinoma\n  1. with necrosis"),
    ],
    ids=["dx-simple", "final-dx-blank-line", "ihc-trailing-space", "dx-multiline"],
)
def test_hc_path_006_values_pinned(text, etype, value):
    got = [e for e in extract_pathology_entities(text) if e["entity_type"] == etype]
    assert [e["entity_value"] for e in got] == [value]
    old = _OLD_DX if etype == "diagnosis" else _OLD_STAINS
    start, end = _observable(text, old.search(text))[:2]
    assert (got[0]["char_start"], got[0]["char_end"]) == (start, end)
