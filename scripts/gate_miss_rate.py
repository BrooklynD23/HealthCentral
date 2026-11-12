#!/usr/bin/env python3
"""Aggregate a Playwright JSON report (run with --repeat-each) into a per-test miss-rate table.

Usage: gate_miss_rate.py REPORT.json [--out summary.md]

Recording policy (WF-NIGHTLY-GATES): always exits 0. The nightly records the rate;
it does not fail on a miss. A missing or unreadable report is written into the
summary, not raised.
"""
import argparse
import json
import sys
from pathlib import Path

PASS = {"passed"}
NOT_RUN = {"skipped"}


def _walk(suite, trail):
    title = suite.get("title", "")
    # Top-level file suites repeat the file name; keep only describe titles.
    here = trail + ([title] if title and title != suite.get("file") else [])
    for spec in suite.get("specs", []):
        yield here, spec
    for child in suite.get("suites", []):
        yield from _walk(child, here)


def aggregate(report):
    """Return rows sorted by miss rate: dict(file, title, project, failures, runs, rate)."""
    acc = {}
    for top in report.get("suites", []):
        for trail, spec in _walk(top, []):
            for test in spec.get("tests", []):
                results = test.get("results") or []
                if not results:
                    continue
                status = results[-1].get("status")  # final attempt; the nightly uses retries=0
                if status in NOT_RUN:
                    continue
                key = (spec.get("file", top.get("file", "")), " > ".join(trail + [spec["title"]]), test.get("projectName", ""))
                row = acc.setdefault(key, {"file": key[0], "title": key[1], "project": key[2], "failures": 0, "runs": 0})
                row["runs"] += 1
                if status not in PASS:
                    row["failures"] += 1
    rows = list(acc.values())
    for r in rows:
        r["rate"] = 100.0 * r["failures"] / r["runs"]
    return sorted(rows, key=lambda r: (-r["rate"], r["file"], r["title"]))


def render(rows):
    total_f = sum(r["failures"] for r in rows)
    total_r = sum(r["runs"] for r in rows)
    lines = [
        "## Nightly timing gates: miss rate",
        "",
        f"{total_f} misses in {total_r} runs across {len(rows)} tests. Recording only; this job never fails on a miss.",
        "",
        "| Test | Misses / runs | Miss rate |",
        "|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['file']}: {r['title']} | {r['failures']} / {r['runs']} | {r['rate']:.1f}% |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--out", help="write the markdown here (default: stdout)")
    args = ap.parse_args(argv)
    try:
        text = render(aggregate(json.loads(Path(args.report).read_text())))
    except (OSError, ValueError) as exc:
        text = f"## Nightly timing gates: miss rate\n\nNo report to aggregate ({exc}).\n"
    if args.out:
        Path(args.out).write_text(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
