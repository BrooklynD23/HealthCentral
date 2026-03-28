#!/usr/bin/env python3
"""Mechanical repo-root hygiene check for local scratch artifacts.

Usage:
  python3 scripts/repo_hygiene_check.py

The check is intentionally narrow:
- it scans only the repository root;
- it flags known scratch markdown/report filename patterns that should be
  removed or relocated before merge-sensitive work;
- it does not treat approved local helper directories as violations.
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

SCRATCH_FILE_PATTERNS: tuple[str, ...] = (
    "PLAN.md",
    "HANDOFF-*.md",
    "*_report*.md",
)
APPROVED_HELPER_DIRS: frozenset[str] = frozenset({
    ".bg-shell",
    ".wsl-pytest-venv",
})


@dataclass(frozen=True)
class HygieneViolation:
    """A disallowed scratch artifact found at repo root."""

    relative_path: str
    matched_pattern: str


def _matches_scratch_pattern(name: str) -> str | None:
    lower_name = name.lower()
    for pattern in SCRATCH_FILE_PATTERNS:
        if fnmatch.fnmatch(lower_name, pattern.lower()):
            return pattern
    return None


def find_repo_hygiene_violations(repo_root: Path) -> list[HygieneViolation]:
    """Return sorted scratch-artifact violations from the repo root."""
    violations: list[HygieneViolation] = []

    for entry in sorted(repo_root.iterdir(), key=lambda path: path.name.lower()):
        if entry.is_dir():
            # Approved helper directories are explicitly non-issues.
            if entry.name in APPROVED_HELPER_DIRS:
                continue
            continue

        matched_pattern = _matches_scratch_pattern(entry.name)
        if matched_pattern is None:
            continue

        violations.append(
            HygieneViolation(
                relative_path=entry.name,
                matched_pattern=matched_pattern,
            )
        )

    return violations


def format_failure_lines(violations: Iterable[HygieneViolation]) -> list[str]:
    """Render stable file-level failure lines for CLI output."""
    return [
        f"ERROR: root scratch artifact '{violation.relative_path}' matches '{violation.matched_pattern}'"
        for violation in violations
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail when repo-root scratch markdown/report artifacts are present"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Path to repository root (default: inferred from script location)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    if not repo_root.exists() or not repo_root.is_dir():
        print(f"ERROR: repo root does not exist or is not a directory: {repo_root}")
        return 2

    violations = find_repo_hygiene_violations(repo_root)
    if violations:
        for line in format_failure_lines(violations):
            print(line)
        print(
            "\nRepo hygiene failed. Remove or relocate these root scratch artifacts before merge-sensitive work."
        )
        return 1

    print(
        "Repo hygiene passed. No disallowed root scratch markdown/report artifacts were found."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
