#!/usr/bin/env python3
"""Check that the progress dashboard artifact matches the build-program queue.

Usage:
    python3 scripts/queue_drift.py <artifact.html> <ref> <queue-path> [--no-prs] [--json out.json]

<artifact.html> is a saved copy of the dashboard page (L0 saves it with
`Artifact read`). Its `const DATA=` line holds the rows the page shows. <ref>
is a git ref (for example origin/main); the queue is read with
`git show <ref>:<queue-path>`. The queue path is a required argument with no
default: scripts/change_scope.py treats a docs file as non-skippable when a
tracked script names it, so naming the queue file here would stop every
queue-only PR from taking the docs-only CI path. The RUNBOOK gives the path.

Network: the only call is `gh pr list --state open` (to find rows with an open
PR). `--no-prs` skips it. Nothing is fetched or written otherwise, except the
optional `--json` output file. This is a dev tool, not product code.

Exit codes: 0 no drift; 2 bad usage; 1 drift (a row missing from the artifact, a row only in
the artifact, or a changed bucket). Duplicate queue ids are reported but are
not drift.

Tables: each markdown table is read by its header row. A table with no header
cell containing "status" is skipped. The row id is the first cell with
backticks, asterisks and tildes removed; the optional `lane` and `kind`
columns are found by header name.

Buckets, first match wins, on the row's status cell (`t`):
    done      starts with done, closed or superseded (optionally wrapped in
              `~~` and `**`)
    inflight  starts with "in flight" (optionally `**`)
    owner     the kind cell contains OWNER; or the row sits in a section whose
              title starts with "owner or model" and the first 120 characters
              of the status contain "owner action" or "bar signed"; or the
              status starts with "bundled" or "linux half"; or the first 40
              characters contain "bundled into #316"
    blocked   starts with blocked (optionally `**`)
    inflight  the row id is a whole-id match in an open PR title (so UI-PG does
              not match UI-PG-ASK)
    ready     starts with ready, or "task 1 ready" (optionally `**`)
    blocked   anything else
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter

SEPARATOR = re.compile(r"^\|[\s:|-]+\|?$")
DONE = re.compile(r"^(~~)?\*{0,2}(done|closed|superseded)\b", re.I)


def cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def column(header: list[str], name: str, exact: bool = True) -> int | None:
    return next((i for i, h in enumerate(header) if (h == name if exact else name in h)), None)


def parse(text: str) -> list[dict]:
    """Return one dict per table row: i id, l lane, k kind, s section, t status, c {lowercase header: cell}."""
    rows: list[dict] = []
    section, header = "", None
    lines = text.splitlines()
    for n, line in enumerate(lines):
        if line.startswith("#"):
            section, header = re.sub(r"^#+\s*", "", line).strip(), None
            continue
        if not line.startswith("|"):
            header = None
            continue
        c = cells(line)
        if n + 1 < len(lines) and SEPARATOR.match(lines[n + 1]):
            header = [x.lower() for x in c]
            continue
        if SEPARATOR.match(line) or not header:
            continue
        st = column(header, "status", exact=False)
        if st is None or st >= len(c):
            continue
        lane, kind = column(header, "lane"), column(header, "kind")
        rows.append(
            dict(
                i=re.sub(r"[`*~]", "", c[0]).strip(),
                l=c[lane] if lane is not None else "",
                k=c[kind] if kind is not None else "",
                s=section,
                t=c[st],
                c={h: c[j] for j, h in enumerate(header) if j < len(c)},
            )
        )
    return rows


def bucket(row: dict, open_prs: dict) -> str:
    t = row["t"]
    if DONE.match(t):
        return "done"
    if re.match(r"^(\*\*)?in flight", t, re.I):
        return "inflight"
    if (
        "OWNER" in row["k"].upper()
        or (
            row["s"].lower().startswith("owner or model")
            and re.search(r"owner action|bar signed", t[:120], re.I)
        )
        or re.match(r"^\*{0,2}(bundled|linux half)", t, re.I)
        or "bundled into #316" in t[:40]
    ):
        return "owner"
    if re.match(r"^\*{0,2}blocked", t, re.I):
        return "blocked"
    if open_prs.get(row["i"]):
        return "inflight"
    if re.match(r"^(task 1 )?\*{0,2}ready", t, re.I):
        return "ready"
    return "blocked"


def match_open_prs(ids: set[str], prs: list[dict]) -> dict:
    """Map row id -> first open PR number whose title names it as a whole id."""
    found: dict = {}
    for p in prs:
        for i in sorted(ids, key=len, reverse=True):
            if re.search(rf"(?<![A-Z0-9-]){re.escape(i)}(?![A-Z0-9-])", p["title"]):
                found.setdefault(i, p["number"])
    return found


def load_artifact(path: str) -> list[dict]:
    with open(path, errors="replace") as f:
        for line in f:
            if line.startswith("const DATA="):
                return json.loads(line[len("const DATA="):].strip().rstrip(";"))["rows"]
    raise SystemExit("no DATA line")


def compare(queue_rows: list[dict], data: list[dict]) -> tuple[list, list, list]:
    """Return (missing from artifact, only in artifact, [(id, artifact, queue)])."""
    a = {r["i"]: r for r in data}
    q = {r["i"]: r for r in queue_rows}
    missing = [i for i in q if i not in a]
    extra = [i for i in a if i not in q]
    changed = [(i, a[i]["b"], q[i]["b"]) for i in q if i in a and a[i]["b"] != q[i]["b"]]
    return missing, extra, changed


def read_queue(ref: str, path: str) -> str:
    return subprocess.check_output(["git", "show", f"{ref}:{path}"], text=True)


def open_pr_list() -> list[dict]:
    out = subprocess.check_output(
        ["gh", "pr", "list", "--state", "open", "--limit", "60", "--json", "number,title,isDraft"],
        text=True,
    )
    return json.loads(out)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 3 or argv[2].startswith("--"):
        print("usage: queue_drift.py <artifact.html> <ref> <queue-path> [--no-prs] [--json out.json]", file=sys.stderr)
        return 2
    html, ref, queue_path = argv[0], argv[1], argv[2]
    rows = parse(read_queue(ref, queue_path))
    prs = [] if "--no-prs" in argv else open_pr_list()
    open_prs = match_open_prs({r["i"] for r in rows}, prs)
    for r in rows:
        r["b"] = bucket(r, open_prs)
    data = load_artifact(html)
    dup = sorted({r["i"] for r in rows if sum(x["i"] == r["i"] for x in rows) > 1})
    missing, extra, changed = compare(rows, data)
    print(f'queue@{ref}: {len(rows)} rows ({len({r["i"] for r in rows})} ids) {dict(Counter(r["b"] for r in rows))}')
    print(f'artifact:   {len(data)} rows {dict(Counter(r["b"] for r in data))}')
    print("duplicate ids in queue:", dup)
    print("missing from artifact:", missing)
    print("only in artifact:", extra)
    print(f"bucket changes: {len(changed)}")
    for c in changed:
        print("  %-28s %-9s -> %s" % c)
    if "--json" in argv:
        with open(argv[argv.index("--json") + 1], "w") as f:
            json.dump(rows, f)
    return 1 if (missing or extra or changed) else 0


if __name__ == "__main__":
    sys.exit(main())
