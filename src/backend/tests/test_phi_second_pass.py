"""RSI1-DONATE PR-2 Task 3: second PHI detector and recall (HC-DON-010..013)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

CORPUS = Path(__file__).parent / "fixtures/phi_recall/corpus_v1.json"
BACKEND = Path(__file__).parent.parent


def _corpus() -> dict:
    return json.loads(CORPUS.read_text())


@pytest.fixture(autouse=True)
def _rules_with_a_model_that_finds_nothing(monkeypatch):
    """Rule-level tests run with a loaded model that finds nothing, so they need no bundle.

    Tests that measure recall with the pinned bundle request ``real_phi_model``.
    """
    from modules import phi_second_pass as psp

    monkeypatch.setattr(psp, "_MODEL_OVERRIDE", _FakePhiModel({}))


@pytest.fixture
def real_phi_model(monkeypatch):
    """The pinned on-device bundle, loaded offline. Absent bundle = failure, never a skip."""
    from modules import phi_second_pass as psp

    monkeypatch.setattr(psp, "_MODEL_OVERRIDE", None)
    monkeypatch.setattr(psp, "_MODEL_CACHE", None)


def test_hc_don_010_detects_each_category_and_no_false_positive_on_labs(real_phi_model):
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


@pytest.mark.parametrize("label", ["name", "patient", "SSN", "MRN", "account", "zip", "VIN", "age"])
@pytest.mark.parametrize("ws", [" ", "\n"])
def test_second_pass_label_whitespace_is_linear(label, ws):
    import time

    from modules.phi_second_pass import detect

    start = time.perf_counter()
    detect(label + ws * 20000 + "x")
    assert time.perf_counter() - start < 1.0


@pytest.mark.parametrize("text,category", [
    ("Admitted on 2024.03.15", "date"),
    ("on 03.15.2024", "date"),
    ("Seen 2024-3-5", "date"),
    ("I was born on the 3rd of March", "date"),
    ("Patient is 101 yrs old", "age_over_89"),
    ("SSN 123.45.6789", "ssn"),
    ("My MRN is A 1234567", "mrn"),
])
def test_second_pass_flags_shape_variants(text, category):
    from modules.phi_second_pass import detect

    assert category in {h.category for h in detect(text)}


def test_second_pass_reference_range_is_not_a_date():
    from modules.phi_second_pass import detect

    assert detect("Hemoglobin 13.5 g/dL (reference 12.0-15.5 g/dL) is within range.") == []


def _r2() -> dict:
    return json.loads((Path(__file__).parent / "fixtures/phi_recall/corpus_v2.json").read_text())


def test_hc_don_013_corpus_meets_recall_target(real_phi_model):
    from scripts.measure_phi_recall import measure, meets_target, merge_corpora

    result = measure(merge_corpora(_corpus(), _r2()))
    assert meets_target(result), result


def test_hc_don_013b_r2_gate_meets_recall_target(real_phi_model):
    from scripts.measure_phi_recall import gate_half, measure, meets_target

    result = measure(gate_half(_r2()))
    assert meets_target(result), result


class _FakePhiModel:
    """Stands in for the verified on-device model: returns (label, span) pairs."""

    def __init__(self, spans_by_text: dict[str, list[tuple[str, str]]]):
        self._spans = spans_by_text

    def labelled_spans(self, text: str) -> list[tuple[str, str]]:
        return [pair for needle, pairs in self._spans.items() if needle in text for pair in pairs]


def test_hc_don_026_model_name_span_drops_record_and_detect_returns_category_only(monkeypatch):
    from modules import phi_second_pass as psp

    # Lowercase name: the rules miss it, so the model's PATIENT span is the only source.
    text = "my sister ana voss called about her lipids today"
    monkeypatch.setattr(psp, "_MODEL_OVERRIDE", _FakePhiModel({"ana voss": [("PATIENT", "ana voss")]}))
    assert psp.rule_hits(text) == []

    hits = psp.detect(text)

    assert [h.category for h in hits] == ["name"]
    for hit in hits:
        assert set(vars(hit)) == {"category"}
        assert all("ana" not in str(v) and "voss" not in str(v) for v in vars(hit).values())
    assert psp.detect("Lipid panel results are in range.") == []


def test_hc_don_027_model_loads_local_files_only_and_makes_no_socket_call(tmp_path, monkeypatch):
    import socket
    from types import SimpleNamespace

    import transformers

    from modules import phi_second_pass as psp

    attempts: list[object] = []

    def _refuse(*args, **kwargs):
        attempts.append(args[:1])
        raise OSError("network blocked by HC-DON-027 guard")

    monkeypatch.setattr(socket.socket, "connect", _refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", _refuse)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse)

    kwargs_seen: list[dict] = []

    class _Stub:
        config = SimpleNamespace(id2label={})

        @classmethod
        def from_pretrained(cls, path, **kwargs):
            kwargs_seen.append(kwargs)
            return cls()

        def eval(self):
            return self

    monkeypatch.setattr(transformers, "AutoTokenizer", _Stub)
    monkeypatch.setattr(transformers, "AutoModelForTokenClassification", _Stub)
    monkeypatch.setattr(psp, "_verify_bundle", lambda directory: None)
    monkeypatch.setattr(psp, "resolve_phi_ner_model_dir", lambda: tmp_path)

    model = psp._load_model()

    assert model is not None
    assert kwargs_seen == [{"local_files_only": True}, {"local_files_only": True}]
    assert attempts == []
