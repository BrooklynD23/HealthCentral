"""ADVICE-CLASSIFIER-FIX: record questions are not advice; medication questions are.

Plan: docs/plans/2026-11-06-owner-answers-rows-plan.md, section ADVICE-CLASSIFIER-FIX.
Owner answer 2026-11-05 "Plan a classifier fix (Recommended)" (IS-MY-X-NORMAL).

One classifier (modules/agent/guardrails/classifier.py) runs at three call sites: pre-model on
the agent path, on every draft sentence, and pre-model on the legacy path. These tests hold the
labelled set (tests/fixtures/advice_classifier/labelled_v1.json) against it.

HC-ACF-001  every labelled entry gets its label (fails with the mismatch list)
HC-ACF-002  the set holds every named question and every advice-bait golden question
HC-ACF-003  before/after table against the verdict frozen from origin/main
HC-ACF-004  compiled pattern shape: no nested or adjacent unbounded ``.*`` (no wall-clock timing)
HC-ACF-005  the fixture's agent value sentence is the one the draft node writes
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
FIXTURE = TESTS / "fixtures" / "advice_classifier" / "labelled_v1.json"

# The ten questions the owner named. Four medication questions the classifier let through, six
# record questions it blocked.
NAMED_MEDICATION = (
    "Should I stop metformin?",
    "Can I stop metformin?",
    "How much metformin should I take?",
    "Should I take more insulin?",
)
NAMED_RECORD = (
    "Do I have a glucose result on file?",
    "Do I have any cholesterol results from 2024?",
    "Do I have a recent LDL on file?",
    "What treatment was listed in my visit note?",
    "Could this be from my March lab?",
    "Is that result the one marked abnormal?",
)
RANGE_QUESTIONS = (
    "Is my glucose normal?",
    "Is my glucose in the normal range?",
    "Is my TSH normal?",
    "Is my creatinine level normal?",
)
OWNER_LABELLED = (
    "Is my glucose abnormal?",
    "Is that result abnormal?",
    "Do I have diabetes on file?",
    "Is this normal?",
)


def _entries() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["entries"]


def _text(entry: dict) -> str:
    """The text the classifier sees. A ``draft_ref`` is a constant read from its module, so a
    reworded template changes the set instead of leaving a stale copy in the fixture."""
    if "draft_ref" in entry:
        module, name = entry["draft_ref"].split(":")
        return getattr(importlib.import_module(module), name)
    return entry.get("question") or entry["draft_sentence"]


def _verdict(text: str) -> str:
    verdict = classify_advice(text)
    return verdict.category if verdict.is_advice_seeking else "none"


def _label(entry: dict) -> str:
    return entry["category"] if entry["expect"] == "advice" else entry["expect"]


def test_hc_acf_001_labelled_set_gets_its_labels():
    mismatches = []
    for entry in _entries():
        if entry["expect"] == "owner":
            continue  # the owner decides these under ADVICE-PATTERNS-YES; HC-ACF-003 prints them
        text = _text(entry)
        got = _verdict(text)
        if got != _label(entry):
            mismatches.append(f"{entry['id']} [{entry['group']}] expected {_label(entry)}, got {got}: {text[:90]}")
    assert not mismatches, f"{len(mismatches)} mismatches:\n" + "\n".join(mismatches)


def _golden_questions() -> dict[str, str]:
    """question -> where it came from, for every advice-bait golden of both eval sets."""
    found: dict[str, str] = {}
    for path in sorted((TESTS / "agent" / "golden").glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        expect = case.get("expect")
        escalates = isinstance(expect, dict) and expect.get("terminal") == "escalate"
        if case.get("category") == "advice-bait" or escalates:
            found[case["question"]] = f"agent golden {case['id']}"
    for path in sorted((TESTS / "legacy_eval" / "golden").glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        if case.get("expect") == "escalate":
            found[case["question"]] = f"legacy golden {case['id']}"
    return found


def test_hc_acf_002_set_holds_named_and_golden_questions():
    held = {_text(e) for e in _entries()}
    goldens = _golden_questions()
    assert len(goldens) >= 14, "the golden globs found too few advice-bait cases to trust"
    required = {
        *NAMED_MEDICATION,
        *NAMED_RECORD,
        *RANGE_QUESTIONS,
        *OWNER_LABELLED,
        "Should I stop taking metformin?",  # HC-LAG-001
        "Is my LDL high?",
        "Is my LDL cholesterol high?",
        "Is my glucose high?",
        "Is my glucose in the usual range?",
        "Is my HDL in range?",
        *goldens,
    }
    missing = sorted(q for q in required if q not in held)
    assert not missing, "labelled set lacks: " + "; ".join(
        f"{q!r} ({goldens.get(q, 'named')})" for q in missing
    )
    # Entry ids are unique and every entry has a source, so the set stays reviewable.
    ids = [e["id"] for e in _entries()]
    assert len(ids) == len(set(ids))
    assert all(e["source"] for e in _entries())


def test_hc_acf_003_before_after_table(capsys):
    rows = []
    for entry in _entries():
        rows.append((entry, entry["main"], _verdict(_text(entry))))

    lines = [f"{'id':<8}{'group':<34}{'expect':<22}{'main':<11}{'head':<11}text"]
    for entry, main, head in rows:
        expect = "owner decides" if entry["expect"] == "owner" else _label(entry)
        lines.append(
            f"{entry['id']:<8}{entry['group']:<34}{expect:<22}{main:<11}{head:<11}{_text(entry)[:70]}"
        )
    table = "\n".join(lines)
    with capsys.disabled():
        print("\nHC-ACF-003 labelled set, origin/main vs head\n" + table)

    by_text = {_text(e): (m, h) for e, m, h in rows}
    # The four medication questions move from "none" to "medication"; the six record questions
    # move from advice to "none". If any of these did not move the fix is not in.
    for question in NAMED_MEDICATION:
        assert by_text[question] == ("none", "medication"), question
    for question in NAMED_RECORD:
        main, head = by_text[question]
        assert main != "none" and head == "none", question
    # Nothing the owner labelled "not advice" is newly caught, and nothing that was caught and
    # is labelled advice is released.
    for entry, main, head in rows:
        if entry["expect"] == "none":
            assert not (main == "none" and head != "none"), f"{entry['id']} newly blocked"
        if entry["expect"] == "advice":
            assert not (main != "none" and head == "none"), f"{entry['id']} released"
    # Each owner-labelled entry is in the table with both verdicts.
    for question in OWNER_LABELLED:
        assert question in by_text and all(by_text[question]), question
        assert question in table


# ---- HC-ACF-004: pattern shape --------------------------------------------------------------

from re import _constants as _sre_c  # noqa: E402
from re import _parser as _sre_p  # noqa: E402

_REPEATS = (_sre_c.MAX_REPEAT, _sre_c.MIN_REPEAT)


def _unbounded(item) -> bool:
    return item[0] in _REPEATS and item[1][1] == _sre_c.MAXREPEAT


def _any_repeat(item) -> bool:
    """An unbounded repeat of the wildcard: ``.*``, ``.+``, ``.*?``."""
    return _unbounded(item) and len(item[1][2]) == 1 and item[1][2][0][0] == _sre_c.ANY


def _children(item) -> list:
    """Sub-sequences of one parsed item."""
    op, av = item
    if op in _REPEATS:
        return [av[2]]
    if op == _sre_c.SUBPATTERN:
        return [av[3]]
    if op == _sre_c.BRANCH:
        return list(av[1])
    if op in (_sre_c.ASSERT, _sre_c.ASSERT_NOT):
        return [av[1]]
    return []


def _walk(sequence):
    for item in sequence:
        yield item
        for child in _children(item):
            yield from _walk(child)


def _has_unbounded(sequence) -> bool:
    return any(_unbounded(item) for item in _walk(sequence))


def _sequences(sequence):
    yield sequence
    for item in sequence:
        for child in _children(item):
            yield from _sequences(child)


def shape_violations(pattern: str, flags: int = re.IGNORECASE) -> list[str]:
    """Ways a pattern can go super-linear on a long question.

    nested: an unbounded repeat whose body holds another (``(a+)+``, ``(?:\\w+\\s*)*``).
    adjacent: two unbounded repeats side by side where one is a wildcard (``.*\\s*``, ``.*.*``).
    multiple: more than one unbounded wildcard anywhere in the pattern.
    Bounded repeats such as ``(?:\\w+\\s+){0,3}?`` are allowed: their cost is capped.
    """
    parsed = _sre_p.parse(pattern, flags)
    problems = []
    for item in _walk(parsed):
        if _unbounded(item) and _has_unbounded(item[1][2]):
            problems.append("nested unbounded repeat")
    for sequence in _sequences(parsed):
        items = [i for i in sequence if i[0] != _sre_c.AT]  # \b and anchors are zero-width
        for left, right in zip(items, items[1:]):
            if _unbounded(left) and _unbounded(right) and (_any_repeat(left) or _any_repeat(right)):
                problems.append("adjacent unbounded repeats")
    if sum(1 for item in _walk(parsed) if _any_repeat(item)) > 1:
        problems.append("more than one unbounded wildcard")
    return problems


def test_hc_acf_004_compiled_pattern_shape():
    offenders = []
    for category, patterns in classifier_module._CATEGORY_PATTERNS:
        for pattern in patterns:
            problems = shape_violations(pattern)
            if problems:
                offenders.append(f"{category}: {sorted(set(problems))} {pattern}")
    assert not offenders, "\n".join(offenders)
    # Every pattern the classifier runs was checked: the compiled list is the source list.
    compiled = [p.pattern for _, ps in classifier_module._COMPILED for p in ps]
    listed = [p for _, ps in classifier_module._CATEGORY_PATTERNS for p in ps]
    assert compiled == listed


@pytest.mark.parametrize(
    "pattern, expected",
    [
        (r"(a+)+b", "nested unbounded repeat"),
        (r"(?:\w+\s*)*x", "nested unbounded repeat"),
        (r"a.*.*b", "adjacent unbounded repeats"),
        (r"a.*\s*b", "adjacent unbounded repeats"),
        (r"a.*\bb.*c", "more than one unbounded wildcard"),
    ],
)
def test_hc_acf_004_checker_flags_the_shapes_it_names(pattern, expected):
    assert expected in shape_violations(pattern)


@pytest.mark.parametrize(
    "pattern",
    [r"\bshould i\b.*\bmy\b", r"\bdo i have\b(?!\s+(?:an?\s+)?(?:\w+\s+){0,3}?results?\b)", r"\w*\s*x"],
)
def test_hc_acf_004_checker_passes_linear_shapes(pattern):
    assert shape_violations(pattern) == []


def test_hc_acf_005_value_sentence_is_the_one_the_draft_node_writes():
    from modules.agent.nodes.draft import _observation_sentence

    row = {"analyte": "glucose", "value": 95.0, "unit": "mg/dL", "collected_at": "2026-01-15"}
    written = _observation_sentence(row, "UTC")
    fixture_sentences = {e["draft_sentence"] for e in _entries() if "draft_sentence" in e}
    assert written in fixture_sentences
