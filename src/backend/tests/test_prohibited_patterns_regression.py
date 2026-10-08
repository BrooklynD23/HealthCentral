"""Pin TODAY's prohibited-pattern behaviour (owner row PARA-1-REDO).

Every sentence in ``must_not_regress.json`` is caught by the current
``InterpretationSafetyGuard`` patterns. This pins existing behaviour only; it
does not claim the patterns are good enough.
"""

import json
import re
from pathlib import Path
from typing import Any

from modules.interpret_safety import InterpretationSafetyGuard

FIXTURES = Path(__file__).parent / "fixtures" / "prohibited_patterns"
OWNER_KEY = "named_by_owner_row_PARA-1-REDO"
OWNER_SENTENCES = [
    "You have kidney disease.",
    "You have type 2 diabetes.",
    "You have hypertension.",
    "You have high cholesterol.",
]
EXPECTED_COUNTS = {
    "diagnosis_plain_you_have": 50,
    "diagnosis_other": 32,
    "certainty": 20,
    "dosing": 18,
    "medication": 20,
    "emergency": 14,
    "reviewer_probe": 16,
    "security_probe": 45,
}
LIVE_PATTERN_COUNT = 11
REACH_SENTENCES = (
    "You have\ndiabetes.",
    "You have  diabetes.",
    "This clearly indicates kidney disease.",
    "This clearly indicate kidney disease.",
    "Take 1000 mg of metformin.",
    "Please increase, after the next visit and the next blood test, your dose.",
    "YOU HAVE DIABETES.",
)


def _load() -> dict[str, Any]:
    return json.loads((FIXTURES / "must_not_regress.json").read_text(encoding="utf-8"))


def _caught(patterns: list[re.Pattern[str]], text: str) -> bool:
    return any(p.search(text) for p in patterns)


def test_hc_para_001_current_patterns_catch_must_not_regress_set() -> None:
    data = _load()
    compiled = [p for p, _ in InterpretationSafetyGuard()._compiled_prohibited]
    texts = [i["text"] for i in data["items"]] + OWNER_SENTENCES
    missed = [t for t in texts if not _caught(compiled, t)]
    assert not missed, f"{len(missed)} sentences missed:\n" + "\n".join(missed)


def test_hc_para_002_must_not_regress_fixture_is_intact() -> None:
    data = _load()
    items = data["items"]
    texts = [i["text"] for i in items]
    counts: dict[str, int] = {}
    for i in items:
        counts[i["group"]] = counts.get(i["group"], 0) + 1
    assert counts == EXPECTED_COUNTS, (
        f"per-group counts {counts} != {EXPECTED_COUNTS}. Change the expected "
        "counts only when adding sentences the live list catches; never to "
        "remove one."
    )
    assert len(items) == 215
    assert len(set(texts)) == len(texts), "duplicate texts"
    multi = re.compile(r"^You have (\S+ )+\S+\.$")
    n = sum(
        1
        for i in items
        if i["group"] == "diagnosis_plain_you_have" and multi.match(i["text"])
    )
    assert n >= 40, f"only {n} multi-word 'You have' items"
    assert data[OWNER_KEY] == OWNER_SENTENCES
    for sentence in OWNER_SENTENCES:
        assert sentence in texts


def test_hc_para_003_every_live_pattern_is_pinned_by_the_set() -> None:
    raw = InterpretationSafetyGuard.PROHIBITED_PATTERNS
    assert len(raw) == LIVE_PATTERN_COUNT, (
        f"live list has {len(raw)} entries, expected {LIVE_PATTERN_COUNT}; "
        "re-measure with scripts/measure_prohibited_patterns.py"
    )
    texts = [i["text"] for i in _load()["items"]]
    for idx, (_, name) in enumerate(raw):
        rest = [re.compile(p, re.IGNORECASE) for j, (p, _) in enumerate(raw) if j != idx]
        assert any(not _caught(rest, t) for t in texts), (
            f"pattern {idx + 1} ({name}) is not pinned: no fixture item depends on it"
        )


def test_hc_para_004_live_patterns_keep_their_reach() -> None:
    compiled = [p for p, _ in InterpretationSafetyGuard()._compiled_prohibited]
    missed = [t for t in REACH_SENTENCES if not _caught(compiled, t)]
    assert not missed, f"{len(missed)} sentences missed: {missed!r}"
