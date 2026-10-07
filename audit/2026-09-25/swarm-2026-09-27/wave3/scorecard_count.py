"""Count the specs-compliance-matrix scorecard.

Rule (matrix Scorecard paragraph): rows in sections 1-10, each counted once by
the first bold word of its Status cell; table cells are split on unescaped
pipes outside code spans.

Usage: scorecard_count.py [path]   (reads stdin when no path is given)
       scorecard_count.py -v path  (also prints "ID status" per row)
"""

from __future__ import annotations

import re
import sys
from collections import Counter

ORDER = (
    "enforced",
    "tested",
    "implemented",
    "partial",
    "gap",
    "contradicted",
    "owner-gated",
    "unknown",
)
SECTION = re.compile(r"^## (\d+)\. ")
ROW_ID = re.compile(r"^[A-Z]+-\d+$")
BOLD = re.compile(r"\*\*([A-Za-z-]+)\*\*")


def split_cells(line: str) -> list[str]:
    """Split one table line on unescaped pipes that are outside code spans."""
    cells: list[str] = []
    buf: list[str] = []
    in_code = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line):
            buf.append(line[i : i + 2])
            i += 2
            continue
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    cells.append("".join(buf).strip())
    return cells[1:-1]


def count(text: str) -> tuple[list[tuple[str, str]], list[str]]:
    rows: list[tuple[str, str]] = []
    problems: list[str] = []
    section = 0
    status_col: int | None = None
    for line in text.splitlines():
        match = SECTION.match(line)
        if match:
            section = int(match.group(1))
            status_col = None
            continue
        if line.startswith("## "):
            section = 0
            continue
        if not 1 <= section <= 10 or not line.startswith("|"):
            continue
        cells = split_cells(line)
        if "Status" in cells:
            status_col = cells.index("Status")
            width = len(cells)
            continue
        if status_col is None or not cells or not ROW_ID.match(cells[0]):
            continue
        if len(cells) != width:
            problems.append(f"{cells[0]}: {len(cells)} cells, header has {width}")
        bold = BOLD.search(cells[status_col]) if status_col < len(cells) else None
        if not bold or bold.group(1) not in ORDER:
            problems.append(f"{cells[0]}: no status word in Status cell")
            continue
        rows.append((cells[0], bold.group(1)))
    return rows, problems


def main(argv: list[str]) -> int:
    verbose = "-v" in argv
    paths = [a for a in argv[1:] if a != "-v"]
    if paths:
        with open(paths[0], encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    rows, problems = count(text)
    tally = Counter(status for _, status in rows)
    if verbose:
        for row_id, status in rows:
            sys.stdout.write(f"{row_id} {status}\n")
    summary = " · ".join(f"{tally[name]} {name}" for name in ORDER)
    sys.stdout.write(f"{len(rows)} requirement rows: {summary}\n")
    for problem in problems:
        sys.stdout.write(f"PROBLEM {problem}\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
