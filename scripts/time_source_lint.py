#!/usr/bin/env python3
"""Fail on deprecated datetime timestamp helpers in src/backend product code.

CLAUDE.md hard invariant: core.time.utcnow is the single timestamp helper
(core.time.utcfromtimestamp for POSIX timestamps). datetime.utcnow() and
datetime.utcfromtimestamp() are also deprecated from Python 3.12.

AST scan: only executable references count, so comments and docstrings that
name the deprecated helpers (core/time.py does) are not violations.

Scans src/backend/ excluding tests/ (which legitimately mention the literal
string in source assertions, e.g. test_hc_recov_025), matching the bandit
-x src/backend/tests/ precedent in ci.yml.

Usage: python3 scripts/time_source_lint.py
Exit 0 when clean; exit 1 listing file:line for each violation.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOT = REPO_ROOT / "src" / "backend"
EXCLUDE_DIR_NAMES = {"tests", "__pycache__"}
BANNED_ATTRS = {"utcnow", "utcfromtimestamp"}


def _is_datetime(node: ast.expr) -> bool:
    """True for the names `datetime` and `<anything>.datetime`."""
    if isinstance(node, ast.Name):
        return node.id == "datetime"
    return isinstance(node, ast.Attribute) and node.attr == "datetime"


def _violations_in(path: Path) -> list[str]:
    rel = path.relative_to(REPO_ROOT)
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"{rel}:{exc.lineno}: cannot parse ({exc.msg})"]
    lines = source.splitlines()
    return [
        f"{rel}:{node.lineno}: {lines[node.lineno - 1].strip()}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr in BANNED_ATTRS
        and _is_datetime(node.value)
    ]


def _is_excluded(path: Path) -> bool:
    """Skip the top-level tests/ dir and __pycache__ at any depth."""
    parts = path.relative_to(SCAN_ROOT).parts
    return parts[0] == "tests" or "__pycache__" in parts


def find_violations() -> tuple[list[str], int]:
    """Return (violations, number of files scanned)."""
    violations: list[str] = []
    scanned = 0
    for path in sorted(SCAN_ROOT.rglob("*.py")):
        if _is_excluded(path):
            continue
        scanned += 1
        violations.extend(sorted(set(_violations_in(path))))
    return violations, scanned


def main() -> int:
    if not SCAN_ROOT.is_dir():
        print(f"time_source_lint ERROR: scan root {SCAN_ROOT} is not a directory.")
        return 1
    violations, scanned = find_violations()
    if scanned == 0:
        print(f"time_source_lint ERROR: scanned 0 .py files under {SCAN_ROOT}.")
        return 1
    if violations:
        print("Deprecated datetime timestamp helpers found "
              "(use core.time.utcnow / core.time.utcfromtimestamp):")
        for line in violations:
            print(f"  {line}")
        return 1
    print("time_source_lint passed: no datetime.utcnow/utcfromtimestamp "
          f"in {scanned} src/backend product files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
