#!/usr/bin/env python3
"""
Harness-drift checker for HealthCentral.

Usage:
  python3 scripts/harness_drift_check.py

Every backtick-quoted, path-shaped token in docs/agentic/*.md is asserted to
exist on disk (checked against the repo root, then against src/backend/ and
src/frontend/, since this repo's docs routinely write module paths relative
to those source roots — e.g. `modules/redaction.py` for
`src/backend/modules/redaction.py`). It exists so a claim like "subagent
definitions live in `.claude/agents/`" cannot sit in a doc pointing at
nothing (see docs/agentic/harness.md's Subagent rules section).

Deliberately conservative: when a token is ambiguous (a shell command, a
glob, a symbol reference, a home-relative path, a bare filename with no repo
root to check it against) it is skipped rather than flagged. A noisy check
nobody trusts is worse than a quiet gap.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DOCS_GLOB = "docs/agentic/*.md"
SOURCE_ROOTS = ("", "src/backend/", "src/frontend/")

# First word of a backtick span that marks the whole span as a shell command
# example, not a path assertion — its embedded paths are illustrative.
COMMAND_VERBS = {
    "cd", "python", "python3", "bash", "sh", "npx", "npm", "node", "pytest",
    "grep", "git", "make", "echo", "source", "export", "ls", "find", "curl",
    "wget",
}

# Bare filenames conventionally referenced without a path prefix because they
# live at the repo root.
ROOT_ALLOWLIST = {
    "README.md", "AGENT.md", "CLAUDE.md", "CONTRIBUTING.md",
    "feature_list.json", "dev.ps1", "dev.bat",
}

FILE_EXTENSIONS = (
    ".py", ".md", ".json", ".sh", ".ts", ".tsx", ".js", ".jsx", ".yml",
    ".yaml", ".ps1", ".bat", ".toml", ".cfg", ".ini", ".txt",
)

DISALLOWED_CHARS = set("\"'(){}<>=*?$,\\|")

_BACKTICK_SPAN = re.compile(r"`([^`]+)`")
_TRAILING_LOCATOR = re.compile(r":[\d,\-]+$")


def _strip_trailing_locator(token: str) -> str:
    """Drop a trailing `:44-51` / `:92,95` line/range locator."""
    return _TRAILING_LOCATOR.sub("", token)


def _is_checkable(token: str) -> bool:
    if "::" in token:
        return False  # symbol reference (file.py::symbol), not a plain path
    if token.startswith("~"):
        return False  # home-relative; not resolvable against the repo tree
    if any(ch in DISALLOWED_CHARS for ch in token):
        return False
    if token.endswith("/"):
        return "/" in token[:-1] or token not in ("/",)
    if any(token.endswith(ext) for ext in FILE_EXTENSIONS):
        return "/" in token or token in ROOT_ALLOWLIST
    return False


def _resolve(repo_root: Path, token: str) -> bool:
    for root in SOURCE_ROOTS:
        if (repo_root / root / token).exists():
            return True
    return False


def _extract_candidates(span: str) -> list[str]:
    """Pull path-shaped tokens out of one backtick span's words.

    A span whose first word is a shell verb (`python3 scripts/foo.py`, `git
    add`, `cd src/frontend`) is treated as a command example in full — paths
    inside it are illustrative, and e.g. a `cd`-relative `tests/` would false
    -positive if checked against the repo root directly.
    """
    words = span.split()
    if not words:
        return []
    if words[0] in COMMAND_VERBS:
        return []
    return [_strip_trailing_locator(w) for w in words]


def find_drift(repo_root: Path) -> list[str]:
    errors: list[str] = []

    for doc_path in sorted(repo_root.glob(DOCS_GLOB)):
        rel_doc = doc_path.relative_to(repo_root).as_posix()
        text = doc_path.read_text(encoding="utf-8")

        for line_no, line in enumerate(text.splitlines(), start=1):
            for span in _BACKTICK_SPAN.findall(line):
                for token in _extract_candidates(span):
                    if not _is_checkable(token):
                        continue
                    if not _resolve(repo_root, token):
                        errors.append(f"{rel_doc}:{line_no}: missing path '{token}'")

    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assert paths named in docs/agentic/*.md actually exist"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Path to repository root (default: inferred from script location)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    errors = find_drift(repo_root)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"\nHarness drift check failed with {len(errors)} error(s).")
        return 1

    print("Harness drift check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
