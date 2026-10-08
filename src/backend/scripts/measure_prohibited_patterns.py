"""Read-only measurement of prohibited-pattern lists. Writes nothing.

Run from src/backend:  python scripts/measure_prohibited_patterns.py [--verbose]
Exit code is always 0 (measurement, not a gate). Imports the live pattern list and
product templates read-only; nothing in product code imports this script.
"""

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
FIX = BACKEND / "tests" / "fixtures" / "prohibited_patterns"
KB_FIELDS = (
    "description", "clinical_significance", "normal_interpretation",
    "high_interpretation", "low_interpretation",
)
Compiled = list[tuple[str, re.Pattern[str]]]
Item = tuple[str, str]  # (label, text)


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _compile(pairs: list[tuple[str, str]]) -> Compiled:
    return [(i, re.compile(p, re.IGNORECASE)) for i, p in pairs]


def load_lists() -> dict[str, Compiled]:
    from modules.interpret_safety import InterpretationSafetyGuard as G

    cur = [(f"C{n}", p) for n, (p, _) in enumerate(G.PROHIBITED_PATTERNS, 1)]
    out = {"current": _compile(cur)}
    cand = _load_module("candidates", FIX / "candidates.py")
    lists = getattr(cand, "LISTS", {"plan_18": getattr(cand, "PLAN_18", [])})
    for name, rows in lists.items():
        out[name] = _compile([(r[0], r[1]) for r in rows])
    return out


def _read(name: str) -> dict[str, Any]:
    return json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))


def _split(name: str) -> tuple[list[Item], list[Item]]:
    d = _read(name)
    return ([(x["category"], x["text"]) for x in d["must_block"]],
            [(x["kind"], x["text"]) for x in d["must_allow"]])


def product_texts() -> list[Item]:
    from modules.agent.guardrails.templates import ABSTAIN_TEMPLATE, ESCALATE_TEMPLATE

    seed = _load_module("seed_kb", BACKEND / "scripts" / "seed_knowledge_base.py")
    items: list[Item] = [("template", ESCALATE_TEMPLATE), ("template", ABSTAIN_TEMPLATE)]
    for row in seed.BIOMARKER_DATA:
        items += [("kb:" + f, row[f]) for f in KB_FIELDS if row.get(f)]
    return items


def first_hit(lst: Compiled, text: str) -> tuple[str, str] | None:
    for pid, rx in lst:
        m = rx.search(text)
        if m:
            return pid, m.group(0)
    return None


def build_sets(sealed: list[str]) -> tuple[dict[str, list[Item]], dict[str, list[Item]]]:
    ins_b, ins_a = _split("in_sample")
    dev_b, dev_a = _split("held_out_dev")
    nr = [(i["group"], i["text"]) for i in _read("must_not_regress")["items"]]
    block = {"in_sample": ins_b, "must_not_regress": nr, "held_out_dev": dev_b}
    allow = {"in_sample": ins_a, "product": product_texts(), "held_out_dev": dev_a}
    for name in sealed:
        block[name], allow[name] = _split(name)
    return block, allow


def _pct(n: int, t: int) -> str:
    return f"{n}/{t} ({100.0 * n / t:.1f}%)" if t else f"{n}/0"


def evaluate(lists: dict[str, Compiled], block: dict[str, list[Item]],
             allow: dict[str, list[Item]]) -> dict[str, Any]:
    res: dict[str, Any] = {}
    cur = lists["current"]
    for ln, lst in lists.items():
        r: dict[str, Any] = {"block": {}, "allow": {}}
        for sn, items in block.items():
            hits = [(k, t, first_hit(lst, t)) for k, t in items]
            regress = [t for _, t, h in hits if h is None and first_hit(cur, t)]
            r["block"][sn] = {"hits": hits, "regress": regress}
        for sn, items in allow.items():
            r["allow"][sn] = [(k, t, first_hit(lst, t)) for k, t in items]
        res[ln] = r
    return res


def report_list(name: str, r: dict[str, Any], verbose: bool) -> None:
    print(f"\n=== {name} ===")
    for sn, d in r["block"].items():
        hits = d["hits"]
        caught = sum(1 for *_, h in hits if h)
        print(f"must-block {sn}: caught {_pct(caught, len(hits))}; "
              f"regressions vs current: {len(d['regress'])}")
        tot, got = Counter(k for k, *_ in hits), Counter(k for k, _, h in hits if h)
        print("   " + ", ".join(f"{k} {got[k]}/{tot[k]}" for k in sorted(tot)))
        if verbose:
            _verbose_block(hits, d["regress"])
    for sn, hits in r["allow"].items():
        fp = [x for x in hits if x[2]]
        print(f"must-allow {sn}: false positives {_pct(len(fp), len(hits))}")
        tot, bad = Counter(k for k, *_ in hits), Counter(k for k, _, h in hits if h)
        print("   " + ", ".join(f"{k} {bad[k]}/{tot[k]}" for k in sorted(tot)))
        if verbose:
            for k, t, (pid, sub) in fp:
                print(f"   FP [{pid}] {sub!r}: {t!r}")


def _verbose_block(hits: list[Any], regress: list[str]) -> None:
    for k, t, h in hits:
        print(f"   {'HIT ' + h[0] + ' ' + repr(h[1]) if h else 'MISS'} [{k}]: {t!r}")
    for t in regress:
        print(f"   REGRESSION: {t!r}")


def report_markdown(res: dict[str, Any]) -> None:
    first = next(iter(res.values()))
    bs, als = list(first["block"]), list(first["allow"])
    head = ["list"]
    for s in bs:
        head += [f"{s} recall", f"{s} regr"]
    head += [f"{s} FP" for s in als]
    print("\n| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for ln, r in res.items():
        cells = [ln]
        for s in bs:
            d = r["block"][s]
            n = sum(1 for *_, h in d["hits"] if h)
            cells += [_pct(n, len(d["hits"])), str(len(d["regress"]))]
        for s in als:
            n = sum(1 for *_, h in r["allow"][s] if h)
            cells.append(_pct(n, len(r["allow"][s])))
        print("| " + " | ".join(cells) + " |")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--final2", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--list", action="append", dest="names")
    ap.add_argument("--markdown", action="store_true")
    a = ap.parse_args()
    sealed = [n for n, on in (("held_out_final", a.final),
                              ("held_out_final2", a.final2)) if on]
    for n in sealed:
        print(f"INCLUDING SEALED {n} SPLIT")
    lists = load_lists()
    if a.names:
        lists = {k: v for k, v in lists.items() if k == "current" or k in a.names}
    block, allow = build_sets(sealed)
    res = evaluate(lists, block, allow)
    if a.markdown:
        report_markdown(res)
    else:
        for ln, r in res.items():
            report_list(ln, r, a.verbose)
    return 0


if __name__ == "__main__":
    main()
