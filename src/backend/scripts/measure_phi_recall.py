"""Per-category PHI recall for strict redaction, the second pass, and their union (RSI1-DONATE).

Usage: python scripts/measure_phi_recall.py [extra_corpus.json]
A planted identifier counts as caught by strict when it is gone from the
strict output; by the second pass when detect() flags the category on the raw
text; by the union when strict removed it or the second pass flags the strict
output (the order collect() runs them).

Default report (counts only, no text): R1, R2, R1 + R2, and R2-gate (R2's items
at odd index per category, in file order; the half that gates donation).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.phi_second_pass import (  # noqa: E402
    PhiNerUnavailableError,
    detect,
    ensure_model,
    resolve_phi_ner_model_dir,
    rule_hits,
)
from modules.redaction import RedactionEngine  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
FIXTURES = BACKEND / "tests/fixtures/phi_recall"
DEFAULT_CORPUS = FIXTURES / "corpus_v1.json"
R2_CORPUS = FIXTURES / "corpus_v2.json"
# G, the false-drop set: must_allow texts of these prohibited-pattern files, plus the served answers.
G_PROHIBITED = ("held_out_dev", "held_out_final", "held_out_final2", "in_sample")
TARGET_CANARY = 1.0
TARGET_CATEGORY = 0.95


def _leaks(planted: str, redacted: str) -> bool:
    """True if the planted string or any token of 3+ chars of it survives."""
    if planted in redacted:
        return True
    return any(t in redacted for t in planted.replace("-", " ").split() if len(t) >= 3)


def measure(corpus: dict, detect_fn=detect) -> dict[str, dict]:
    """Return {category: {n, strict, second, union, canary_n, canary_union}} (counts)."""
    engine = RedactionEngine(policy_level="strict")
    out: dict[str, dict] = {}
    for category, items in corpus["categories"].items():
        row = dict.fromkeys(("strict", "second", "union", "canary_n", "canary_union"), 0)
        row["n"] = len(items)
        for item in items:
            redacted = engine.redact(item["text"]).text
            strict = not _leaks(item["planted"], redacted)
            second = any(h.category == category for h in detect_fn(item["text"]))
            union = strict or bool(detect_fn(redacted))
            row["strict"] += strict
            row["second"] += second
            row["union"] += union
            if item.get("canary"):
                row["canary_n"] += 1
                row["canary_union"] += union
        out[category] = row
    return out


def merge_corpora(a: dict, b: dict) -> dict:
    """Per-category concatenation of two corpora (items keep their order: a, then b)."""
    cats = {c: list(a["categories"].get(c, [])) + list(b["categories"].get(c, []))
            for c in list(a["categories"]) + [c for c in b["categories"] if c not in a["categories"]]}
    return {"categories": cats}


def gate_half(corpus: dict) -> dict:
    """R2-gate: the items at odd index per category, in file order."""
    return {"categories": {c: items[1::2] for c, items in corpus["categories"].items()}}


def g_texts() -> list[str]:
    """G: 546 must_allow texts plus 2 served answers (548). Counts only are ever printed."""
    texts: list[str] = []
    for name in G_PROHIBITED:
        data = json.loads((BACKEND / "tests/fixtures/prohibited_patterns" / f"{name}.json").read_text(encoding="utf-8"))
        texts += [item["text"] for item in data["must_allow"]]
    for path in sorted((BACKEND / "tests/legacy_eval/golden").glob("answer-*.json")):
        texts.append(json.loads(path.read_text(encoding="utf-8"))["model_output"])
    return texts


def false_drops(detect_fn) -> tuple[int, int]:
    """(texts flagged, texts) when detect_fn runs on the strict output of each G text."""
    engine = RedactionEngine(policy_level="strict")
    texts = g_texts()
    return sum(1 for t in texts if detect_fn(engine.redact(t).text)), len(texts)


def false_positives(corpus: dict) -> int:
    """Non-PHI sentences the second pass flags (over-redaction check)."""
    return sum(1 for s in corpus.get("non_phi", []) if detect(s))


def format_table(result: dict[str, dict]) -> str:
    lines = ["| category | n | strict | second | union | union % |", "|---|---|---|---|---|---|"]
    for cat, r in result.items():
        pct = 100 * r["union"] / r["n"] if r["n"] else 0
        lines.append(f"| {cat} | {r['n']} | {r['strict']}/{r['n']} | {r['second']}/{r['n']} | {r['union']}/{r['n']} | {pct:.0f}% |")
    return "\n".join(lines)


def canary_line(result: dict[str, dict]) -> str:
    n = sum(r["canary_n"] for r in result.values())
    u = sum(r["canary_union"] for r in result.values())
    return f"canaries caught {u}/{n}"


def meets_target(result: dict[str, dict]) -> bool:
    return all(
        r["canary_union"] >= TARGET_CANARY * r["canary_n"] and r["union"] >= TARGET_CATEGORY * r["n"]
        for r in result.values()
    )


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _report(label: str, corpus: dict) -> bool:
    result = measure(corpus)
    print(f"\n## {label}")
    print(format_table(result))
    print(canary_line(result))
    ok = meets_target(result)
    print(f"DON-RECALL target (100% canaries, >=95% per category): {'MET' if ok else 'NOT MET'}")
    return ok


def main(argv: list[str]) -> int:
    # A missing or failed bundle stops the run with the reason: never rules-only numbers.
    try:
        ensure_model()
    except PhiNerUnavailableError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print(f"model directory checked: {resolve_phi_ner_model_dir()}", file=sys.stderr)
        return 2
    r1 = _load(Path(argv[1]) if len(argv) > 1 else DEFAULT_CORPUS)
    r2 = _load(R2_CORPUS)
    met = [
        _report("R1 (corpus_v1.json)", r1),
        _report("R2 (corpus_v2.json)", r2),
        _report("R1 + R2", merge_corpora(r1, r2)),
    ]
    gate_ok = _report("R2-gate (R2 items at odd index per category)", gate_half(r2))
    print(f"\nnon-PHI sentences flagged by second pass (R1): {false_positives(r1)}/{len(r1.get('non_phi', []))}")
    c0, n = false_drops(rule_hits)
    c1, _ = false_drops(detect)
    print(f"G false drops (strict output, {n} texts): C0 rules only {c0}/{n} ({100 * c0 / n:.1f}%); "
          f"C1 rules + on-device model {c1}/{n} ({100 * c1 / n:.1f}%)")
    return 0 if all(met) and gate_ok else 1



if __name__ == "__main__":
    sys.exit(main(sys.argv))
