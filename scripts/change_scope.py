#!/usr/bin/env python3
"""Classify a change set: may CI and build-item skip the code jobs? (HARNESS-SPEEDUP, owner SPEEDUP-1-3)

Reads changed paths from stdin, one per line. Prints exactly four lines and exits 0:

    docs_only=<true|false>
    backend=<true|false>
    frontend=<true|false>
    mods=<true|false>

`docs_only` is true only when ALL of these hold:
  - the input is non-empty;
  - every path matches ``^docs/``, ``\\.md$`` or ``^openwiki/``;
  - no path is *referenced* (below);
  - backend, frontend and mods are all false.

A docs path is *referenced* when a tracked file under src/, scripts/, .github/ or .claude/mods/
holds the path as a literal substring, or holds its basename in single or double quotes (pathlib
segments). Some backend test then reads that file, so Backend Tests must run. A comment that merely
mentions a path also makes it non-skippable: that is the safe direction. The two generated index
files are left out of the check, because the CI docs-lint job names them and runs
``generate_docs_index.py --check`` on every PR.

Fail closed: empty input, an absolute path, ``..``, a backslash, a control character, a git error or
any exception prints ``docs_only=false backend=true frontend=true mods=true`` (one per line), exit 0.

Stdlib and git only. ``--repo-root DIR`` picks the checkout that ``git grep`` searches (default: this
script's repo).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

KEYS = ("docs_only", "backend", "frontend", "mods")
FAIL_CLOSED = {"docs_only": False, "backend": True, "frontend": True, "mods": True}

DOCS_RE = re.compile(r"^docs/|\.md$|^openwiki/")

# Paths a backend test reads (or that the CI backend job itself depends on). Beside each pattern: why.
BACKEND_RES = tuple(
    re.compile(p)
    for p in (
        r"^src/backend/",  # the backend itself
        r"(^|/)requirements[^/]*\.txt$",  # dependency pins feed the backend install
        r"(^|/)migrations/",  # Alembic chains
        r"^scripts/",  # test_docs_lint, test_security_gate, test_repo_hygiene_check, test_harness_drift_check load these
        r"^\.github/",  # workflow files are part of the gate
        r"^\.claude/(hooks|agents|mods)/",  # HC-SLOG-004 parity, HC-AGENTS-*
        r"^\.claude/settings\.json$",  # HC-SLOG-004
        r"^dev\.sh$",  # test_dev_sh_prereqs
        r"^THIRD_PARTY_NOTICES\.md$",  # HC-OCR-013
        r"^docs/agentic/harness\.md$",  # HC-AGENTS-008
        r"^src/frontend/src/components/settings/DataDonationCard\.tsx$",  # test_donation_routes_http
    )
)
FRONTEND_RE = re.compile(r"^src/frontend/")
MODS_RE = re.compile(r"^\.claude/mods/")

# Left out of the reference check: ci.yml and docs tests name them; the always-run docs-lint step
# `generate_docs_index.py --check` covers them.
GENERATED = frozenset({"docs/INDEX.md", "docs/_link_graph.json"})
SEARCH_PATHSPECS = ("src", "scripts", ".github", ".claude/mods")


class Unsafe(Exception):
    """The input cannot be trusted; fail closed."""


def _validate(path: str) -> None:
    if (
        path.startswith("/")
        or re.match(r"^[A-Za-z]:", path)
        or ".." in path
        or "\\" in path
        or any(ord(c) < 32 or ord(c) == 127 for c in path)
    ):
        raise Unsafe(path)


def _referenced(candidates: list[str], repo_root: Path) -> bool:
    """True when any candidate (or its quoted basename) appears in a tracked file in the search set."""
    patterns: list[str] = []
    for path in candidates:
        base = path.rsplit("/", 1)[-1]
        patterns += [path, f'"{base}"', f"'{base}'"]
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "grep", "-F", "-l", "-f", "-", "--", *SEARCH_PATHSPECS],
        input="\n".join(patterns) + "\n",
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    raise Unsafe(f"git grep exit {proc.returncode}: {proc.stderr.strip()}")


def classify(paths: list[str], repo_root: Path) -> dict[str, bool]:
    if not paths:
        raise Unsafe("empty input")
    for path in paths:
        _validate(path)
    frontend = any(FRONTEND_RE.search(p) for p in paths)
    mods = any(MODS_RE.search(p) for p in paths)
    backend = any(rx.search(p) for p in paths for rx in BACKEND_RES)
    all_docs = all(DOCS_RE.search(p) for p in paths)
    if not backend:
        candidates = [p for p in paths if DOCS_RE.search(p) and p not in GENERATED]
        if candidates and _referenced(candidates, repo_root):
            backend = True
    docs_only = all_docs and not (backend or frontend or mods)
    return {"docs_only": docs_only, "backend": backend, "frontend": frontend, "mods": mods}


def _repo_root(argv: list[str]) -> Path:
    default = Path(__file__).resolve().parents[1]
    if not argv:
        return default
    if len(argv) == 2 and argv[0] == "--repo-root":
        return Path(argv[1])
    raise Unsafe(f"unknown arguments: {argv}")


def main(argv: list[str]) -> int:
    try:
        repo_root = _repo_root(argv)
        paths = [line for line in sys.stdin.read().split("\n") if line != ""]
        result = classify(paths, repo_root)
    except Exception:  # noqa: BLE001 - every failure must run everything
        result = FAIL_CLOSED
    for key in KEYS:
        print(f"{key}={'true' if result[key] else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
