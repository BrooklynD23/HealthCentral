"""Per-category PHI recall for strict redaction, the second pass, and their union (RSI1-DONATE Task 3).

Usage: python scripts/measure_phi_recall.py [corpus.json]
A planted identifier counts as caught by strict when it is gone from the
strict output; by the second pass when detect() flags the category on the raw
text; by the union when strict removed it or the second pass flags the strict
output (the order collect() runs them).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.phi_second_pass import detect  # noqa: E402
from modules.redaction import RedactionEngine  # noqa: E402

DEFAULT_CORPUS = Path(__file__).resolve().parent.parent / "tests/fixtures/phi_recall/corpus_v1.json"
TARGET_CANARY = 1.0
TARGET_CATEGORY = 0.95


def _leaks(planted: str, redacted: str) -> bool:
    """True if the planted string or any token of 3+ chars of it survives."""
    if planted in redacted:
        return True
    return any(t in redacted for t in planted.replace("-", " ").split() if len(t) >= 3)


def measure(corpus: dict) -> dict[str, dict]:
    """Return {category: {n, strict, second, union, canary_n, canary_union}} (counts)."""
    engine = RedactionEngine(policy_level="strict")
    out: dict[str, dict] = {}
    for category, items in corpus["categories"].items():
        row = dict.fromkeys(("strict", "second", "union", "canary_n", "canary_union"), 0)
        row["n"] = len(items)
        for item in items:
            redacted = engine.redact(item["text"]).text
            strict = not _leaks(item["planted"], redacted)
            second = any(h.category == category for h in detect(item["text"]))
            union = strict or bool(detect(redacted))
            row["strict"] += strict
            row["second"] += second
            row["union"] += union
            if item.get("canary"):
                row["canary_n"] += 1
                row["canary_union"] += union
        out[category] = row
    return out


def false_positives(corpus: dict) -> int:
    """Non-PHI sentences the second pass flags (over-redaction check)."""
    return sum(1 for s in corpus.get("non_phi", []) if detect(s))


def format_table(result: dict[str, dict]) -> str:
    lines = ["| category | n | strict | second | union | union % |", "|---|---|---|---|---|---|"]
    for cat, r in result.items():
        pct = 100 * r["union"] / r["n"] if r["n"] else 0
        lines.append(f"| {cat} | {r['n']} | {r['strict']}/{r['n']} | {r['second']}/{r['n']} | {r['union']}/{r['n']} | {pct:.0f}% |")
    return "\n".join(lines)


def meets_target(result: dict[str, dict]) -> bool:
    return all(
        r["canary_union"] >= TARGET_CANARY * r["canary_n"] and r["union"] >= TARGET_CATEGORY * r["n"]
        for r in result.values()
    )


def main(argv: list[str]) -> int:
    corpus = json.loads(Path(argv[1] if len(argv) > 1 else DEFAULT_CORPUS).read_text())
    result = measure(corpus)
    print(format_table(result))
    print(f"non-PHI sentences flagged by second pass: {false_positives(corpus)}/{len(corpus.get('non_phi', []))}")
    ok = meets_target(result)
    print("DON-RECALL target (100% canaries, >=95% per category):", "MET" if ok else "NOT MET")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
