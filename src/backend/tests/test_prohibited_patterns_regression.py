"""Pin TODAY's prohibited-pattern behaviour (owner row PARA-1-REDO).

Every sentence in ``must_not_regress.json`` is caught by the current
``InterpretationSafetyGuard`` patterns. This pins existing behaviour only; it
does not claim the patterns are good enough.
"""

import json
import re
from pathlib import Path

from modules.interpret_safety import InterpretationSafetyGuard

FIXTURES = Path(__file__).parent / "fixtures" / "prohibited_patterns"
OWNER_KEY = "named_by_owner_row_PARA-1-REDO"
GROUPS = {
    "diagnosis_plain_you_have",
    "diagnosis_other",
    "certainty",
    "dosing",
    "medication",
    "emergency",
}


def _load() -> dict:
    return json.loads((FIXTURES / "must_not_regress.json").read_text(encoding="utf-8"))


def test_hc_para_001_current_patterns_catch_must_not_regress_set() -> None:
    data = _load()
    compiled = InterpretationSafetyGuard()._compiled_prohibited
    texts = [i["text"] for i in data["items"]] + list(data[OWNER_KEY])
    missed = [t for t in texts if not any(p.search(t) for p, _ in compiled)]
    assert not missed, f"{len(missed)} sentences missed:\n" + "\n".join(missed)


def test_hc_para_002_must_not_regress_fixture_is_intact() -> None:
    data = _load()
    items = data["items"]
    texts = [i["text"] for i in items]
    assert len(items) >= 150
    assert len(set(texts)) == len(texts), "duplicate texts"
    for group in GROUPS:
        assert any(i["group"] == group for i in items), f"empty group {group}"
    multi = re.compile(r"^You have (\S+ )+\S+\.$")
    n = sum(
        1
        for i in items
        if i["group"] == "diagnosis_plain_you_have" and multi.match(i["text"])
    )
    assert n >= 40, f"only {n} multi-word 'You have' items"
    for sentence in data[OWNER_KEY]:
        assert sentence in texts
