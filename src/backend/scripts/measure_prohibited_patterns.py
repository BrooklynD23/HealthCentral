"""Read-only measurement of prohibited-pattern lists. Writes nothing.

Run from src/backend:  python scripts/measure_prohibited_patterns.py [--verbose]
Exit code is 0 for the list modes (measurement, not a gate). Imports the live pattern
list and product templates read-only; nothing in product code imports this script.

--judge mode (B-3, plan lane-B §B-3 "--judge CLI contract"):
  HF_HUB_OFFLINE=1 python scripts/measure_prohibited_patterns.py \
      --judge <S5.jsonl> --tier <tier> [--concurrency 2]
  Runs the frozen advice judge over the sealed set S5 twice and prints the §6
  metric table. Exit codes: 0 OK; 2 usage, --tier low, or S5 inside the repo;
  3 bad schema or counts below 180 must_block / 200 must_allow; 4 runner
  unavailable, no GGUF path, or the loaded file is the low-tier file.
"""

import sys

sys.dont_write_bytecode = True  # before any import that could write __pycache__

import argparse
import asyncio
import hashlib
import importlib.util
import json
import re
import subprocess
import time
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
WRAP = ("Here is a summary of your results. ",
        " Please discuss this with your clinician.")
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


def _dedupe(name: str, seen: set[str], block: list[Item],
            allow: list[Item]) -> tuple[list[Item], list[Item]]:
    quoted = set(_read(name).get("quoted_in_author_report", []))
    drop = seen | quoted
    kb = [x for x in block if x[1] not in drop]
    ka = [x for x in allow if x[1] not in drop]
    print(f"dedupe {name}: dropped {len(block) - len(kb)} must-block, "
          f"{len(allow) - len(ka)} must-allow")
    return kb, ka


def build_sets(sealed: list[str], dedupe: bool = False, wrap: bool = False,
               ) -> tuple[dict[str, list[Item]], dict[str, list[Item]]]:
    ins_b, ins_a = _split("in_sample")
    dev_b, dev_a = _split("held_out_dev")
    nr = [(i["group"], i["text"]) for i in _read("must_not_regress")["items"]]
    block = {"in_sample": ins_b, "must_not_regress": nr, "held_out_dev": dev_b}
    allow = {"in_sample": ins_a, "product": product_texts(), "held_out_dev": dev_a}
    seen = {t for d in (block, allow) for v in d.values() for _, t in v}
    for name in sealed:
        b, a = _split(name)
        if dedupe:
            b, a = _dedupe(name, seen, b, a)
        block[name], allow[name] = b, a
        seen |= {t for _, t in _split(name)[0] + _split(name)[1]}
    if dedupe and not sealed:
        print("dedupe: no sealed split loaded, nothing to do")
    if wrap:
        block = {k: [(c, WRAP[0] + t + WRAP[1]) for c, t in v] for k, v in block.items()}
        allow = {k: [(c, WRAP[0] + t + WRAP[1]) for c, t in v] for k, v in allow.items()}
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


def report_timing(lists: dict[str, Compiled]) -> None:
    texts = {
        "colons-1250": ("it: " * 2000)[:1250],
        "colons-2500": ("it: " * 2000)[:2500],
        "labtable-2500": ("LDL: 130 mg/dL  HDL: 50 mg/dL  " * 200)[:2500],
    }
    print("seconds for one whole-list pass:")
    for ln, lst in lists.items():
        cells = []
        for label, text in texts.items():
            t0 = time.perf_counter()
            for _, rx in lst:
                rx.search(text)
            cells.append(f"{label} {time.perf_counter() - t0:.2f}")
        print(f"  {ln}: " + ", ".join(cells))


MIN_MUST_BLOCK, MIN_MUST_ALLOW = 180, 200  # PR3-S5N: the plan's size
LABELS = ("must_block", "must_allow")


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=BACKEND, capture_output=True, text=True,
                             check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip()


def load_s5(path: Path) -> list[dict[str, Any]] | str:
    """Parse and validate S5; returns the rows, or an error message (exit 3)."""
    try:
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError as exc:
        return f"cannot read {path}: {exc}"
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for n, ln in enumerate(lines, 1):
        try:
            row = json.loads(ln)
        except ValueError:
            return f"line {n}: not valid JSON"
        if (not isinstance(row, dict) or set(row) != {"id", "label", "category", "text"}
                or not isinstance(row["id"], str) or not row["id"]
                or row["label"] not in LABELS
                or not (row["category"] is None or isinstance(row["category"], str))
                or not isinstance(row["text"], str) or not row["text"].strip()):
            return f"line {n}: bad schema"
        if row["id"] in seen:
            return f"line {n}: duplicate id {row['id']!r}"
        seen.add(row["id"])
        rows.append(row)
    nb = sum(r["label"] == "must_block" for r in rows)
    na = sum(r["label"] == "must_allow" for r in rows)
    if nb < MIN_MUST_BLOCK or na < MIN_MUST_ALLOW:
        return (f"counts must_block={nb} must_allow={na}; "
                f"need >= {MIN_MUST_BLOCK} and >= {MIN_MUST_ALLOW}")
    return rows


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(q * (len(ordered) - 1))))]


async def _one_pass(rows: list[dict[str, Any]], runner: Any, concurrency: int,
                    ) -> tuple[list[str], list[float]]:
    from modules.agent.guardrails.advice_judge import advice_judge

    sem = asyncio.Semaphore(concurrency)
    verdicts = ["UNAVAILABLE"] * len(rows)
    times = [0.0] * len(rows)

    async def work(i: int) -> None:
        async with sem:
            t0 = time.perf_counter()
            verdicts[i] = await advice_judge(rows[i]["text"], runner)
            times[i] = time.perf_counter() - t0

    await asyncio.gather(*(work(i) for i in range(len(rows))))
    return verdicts, times


def run_judge(s5: str, tier: str | None, concurrency: int) -> int:
    """The --judge mode. Inference goes only through ModelRunner / advice_judge."""
    from modules.model_selector import TIER_MODEL_CONFIG

    allowed = [k for k in TIER_MODEL_CONFIG if k != "low"]
    if tier == "low":
        print("error: the low tier cannot be measured: it fails closed at runtime "
              "(PR3-TIER (A)); pick one of " + ", ".join(allowed), file=sys.stderr)
        return 2
    if tier not in allowed:
        print("error: --tier is required with --judge, one of " + ", ".join(allowed),
              file=sys.stderr)
        return 2
    toplevel = _git("rev-parse", "--show-toplevel")
    if toplevel is None:
        print("error: cannot find the git toplevel to keep S5 outside it", file=sys.stderr)
        return 2
    path = Path(s5).expanduser().resolve()
    if path == Path(toplevel).resolve() or Path(toplevel).resolve() in path.parents:
        print(f"error: S5 path is inside the git toplevel {toplevel}; S5 must live outside "
              "every worktree", file=sys.stderr)
        return 2
    rows = load_s5(path)
    if isinstance(rows, str):
        print(f"error: {rows}", file=sys.stderr)
        return 3

    import core.model_runner as model_runner  # looked up at call time (tests patch it)

    runner = model_runner.get_model_runner()
    finder = getattr(runner, "_find_model_path", None)
    gguf = finder() if finder else None
    low_name = str(TIER_MODEL_CONFIG["low"]["filename"]).casefold()
    if gguf is None or not Path(str(gguf)).is_file():
        print("error: no loaded GGUF file found for the runner", file=sys.stderr)
        return 4
    if Path(str(gguf)).name.casefold() == low_name:
        print("error: the loaded file is the low-tier model; load a higher tier", file=sys.stderr)
        return 4
    if not runner.is_available():
        print("error: runner unavailable", file=sys.stderr)
        return 4

    from modules.interpret_safety import InterpretationSafetyGuard as G

    floor = _compile([(f"C{n}", p) for n, (p, _) in enumerate(G.PROHIBITED_PATTERNS, 1)])
    floor_hit = [first_hit(floor, r["text"]) is not None for r in rows]

    passes: list[list[str]] = []
    times: list[float] = []
    for _ in range(2):
        v, t = asyncio.run(_one_pass(rows, runner, concurrency))
        passes.append(v)
        times += t
    first = passes[0]
    block_idx = [i for i, r in enumerate(rows) if r["label"] == "must_block"]
    allow_idx = [i for i, r in enumerate(rows) if r["label"] == "must_allow"]
    caught = sum(floor_hit[i] or first[i] == "BLOCK" for i in block_idx)
    added = sum((not floor_hit[i]) and first[i] == "BLOCK" for i in block_idx)
    added_fp = sum((not floor_hit[i]) and first[i] == "BLOCK" for i in allow_idx)
    unavailable = sum(v == "UNAVAILABLE" for p in passes for v in p)
    agree = sum(a == b for a, b in zip(*passes))

    head = _git("rev-parse", "HEAD") or "unknown"
    print(f"tier: {tier}")
    print(f"gguf_sha256: {_sha256(Path(str(gguf)))}")
    print(f"s5_sha256: {_sha256(path)}")
    print(f"s5_counts: must_block={len(block_idx)} must_allow={len(allow_idx)}")
    print(f"commit: {head}")
    print(f"passes: 2  concurrency: {concurrency}")
    print(f"system_recall: {caught / len(block_idx):.3f} ({caught}/{len(block_idx)})")
    print(f"judge_added_recall: {added / len(block_idx):.3f} ({added}/{len(block_idx)})")
    print(f"added_false_positives: {added_fp}")
    print(f"false_positive_rate: {added_fp / len(allow_idx):.3f} ({added_fp}/{len(allow_idx)})")
    print(f"unavailable_rate: {unavailable / (2 * len(rows)):.3f}")
    print(f"two_pass_agreement: {agree / len(rows):.3f}")
    print(f"latency_p50_s: {_quantile(times, 0.50):.3f}")
    print(f"latency_p95_s: {_quantile(times, 0.95):.3f}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--final2", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--list", action="append", dest="names")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--dedupe", action="store_true")
    ap.add_argument("--timing", action="store_true")
    ap.add_argument("--wrap", action="store_true")
    ap.add_argument("--judge", metavar="S5_JSONL", help="measure the advice judge on S5")
    ap.add_argument("--tier", help="model tier being measured (not low); required with --judge")
    ap.add_argument("--concurrency", type=int, default=2)
    a = ap.parse_args(argv)
    if a.judge:
        return run_judge(a.judge, a.tier, max(1, a.concurrency))
    sealed = [n for n, on in (("held_out_final", a.final),
                              ("held_out_final2", a.final2)) if on]
    for n in sealed:
        print(f"INCLUDING SEALED {n} SPLIT")
    if a.wrap:
        print("TEXTS ARE WRAPPED in a summary sentence and a clinician sentence")
    lists = load_lists()
    if a.names:
        lists = {k: v for k, v in lists.items() if k == "current" or k in a.names}
    if a.timing:
        report_timing(lists)
        return 0
    block, allow = build_sets(sealed, a.dedupe, a.wrap)
    res = evaluate(lists, block, allow)
    if a.markdown:
        report_markdown(res)
    else:
        for ln, r in res.items():
            report_list(ln, r, a.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
