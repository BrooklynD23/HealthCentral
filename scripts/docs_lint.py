#!/usr/bin/env python3
"""
Documentation drift linter for HealthCentral.

Usage:
  python3 scripts/docs_lint.py

Baseline rules:
  1. Canonical docs must include a "Last Updated" field.
  2. Historical docs must include a "Historical Reference" banner near the top.
  3. docs/05_backend_integration_status.md must stay classified as historical and must
     not contain stale marker "LLM Required".
  4. docs/features/TASK_LIST.md must include Red/Green/Refactor phases and non-empty
     phase content for active TODO rows.
  5. (DOC-004) Canonical docs must include "Owner:" and "Refresh Trigger:" fields.
  6. (DOC-005) Historical docs must contain inactive-tracker language in the top 15 lines.
  7. (DOC-006) Required sections checklist for key user-facing docs.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


CANONICAL_DOCS = [
    "docs/00_architecture_plans_index.md",
    "docs/features/00_features_index.md",
    "docs/features/TASK_LIST.md",
]

HISTORICAL_DOCS = [
    "docs/05_backend_integration_status.md",
    "docs/06_mvp_to_rag_execution_board.md",
    "docs/plans/UI-implementation-2-4.md",
    "docs/plans/remaining-features-implementation.md",
    "docs/plans/next-agent-documentation-consolidation.md",
    "docs/plans/sprint-phase-2026-02-13-implementation-plan.md",
]

REQUIRED_SECTIONS: dict[str, list[str]] = {
    "README.md": ["API Overview", "Quick Start"],
    "docs/features/03_features_prd.md": ["Last Updated"],
}

BACKEND_STATUS_DOC = "docs/05_backend_integration_status.md"
TASK_LIST_DOC = "docs/features/TASK_LIST.md"
FEATURE_INDEX_DOC = "docs/features/00_features_index.md"


def _read_text(repo_root: Path, relative_path: str) -> str:
    path = repo_root / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {relative_path}")
    return path.read_text(encoding="utf-8")


def _top_lines(text: str, count: int = 15) -> str:
    return "\n".join(text.splitlines()[:count])


def _check_last_updated(repo_root: Path) -> list[str]:
    errors: list[str] = []
    pattern = re.compile(r"^\*\*Last Updated:\*\*\s*\d{4}-\d{2}-\d{2}", re.MULTILINE)

    for rel_path in CANONICAL_DOCS:
        text = _read_text(repo_root, rel_path)
        if not pattern.search(text):
            errors.append(
                f"{rel_path}: missing or malformed '**Last Updated:** YYYY-MM-DD' field"
            )

    return errors


def _check_historical_banners(repo_root: Path) -> list[str]:
    errors: list[str] = []

    for rel_path in HISTORICAL_DOCS:
        text = _read_text(repo_root, rel_path)
        if "Historical Reference" not in _top_lines(text):
            errors.append(
                f"{rel_path}: missing 'Historical Reference' banner near file start"
            )

    return errors


def _check_backend_status_classification(_repo_root: Path) -> list[str]:
    errors: list[str] = []

    if BACKEND_STATUS_DOC in CANONICAL_DOCS:
        errors.append(
            f"{BACKEND_STATUS_DOC}: lint config misclassifies it as canonical; it must remain historical"
        )
    if BACKEND_STATUS_DOC not in HISTORICAL_DOCS:
        errors.append(
            f"{BACKEND_STATUS_DOC}: lint config no longer treats it as historical"
        )

    return errors


def _check_backend_status_stale_marker(repo_root: Path) -> list[str]:
    errors: list[str] = []
    text = _read_text(repo_root, BACKEND_STATUS_DOC)

    if "LLM Required" in text:
        errors.append(
            f"{BACKEND_STATUS_DOC}: historical snapshot contains stale marker 'LLM Required'"
        )

    return errors


def _check_feature_index_not_planning(repo_root: Path) -> list[str]:
    errors: list[str] = []
    text = _read_text(repo_root, FEATURE_INDEX_DOC)

    if re.search(r"\|\s*Planning\s*\|", text):
        errors.append(
            f"{FEATURE_INDEX_DOC}: contains stale status label 'Planning'"
        )

    return errors


def _check_task_list_tdd_phases(repo_root: Path) -> list[str]:
    errors: list[str] = []
    text = _read_text(repo_root, TASK_LIST_DOC)

    for keyword in ("Red:", "Green:", "Refactor"):
        if keyword not in text:
            errors.append(
                f"{TASK_LIST_DOC}: missing required TDD phase keyword '{keyword}'"
            )

    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        if "| [ ] TODO |" not in line:
            continue

        columns = [col.strip() for col in line.strip().strip("|").split("|")]
        if len(columns) < 7:
            errors.append(
                f"{TASK_LIST_DOC}: malformed active-item row (expected >=7 columns): {line}"
            )
            continue

        item_id = columns[0]
        phase_t1, phase_t2, phase_t3 = columns[2], columns[3], columns[4]
        for phase_name, phase_value in (
            ("Phase T1", phase_t1),
            ("Phase T2", phase_t2),
            ("Phase T3", phase_t3),
        ):
            if not phase_value or phase_value in {"TODO", "-", "N/A"}:
                errors.append(
                    f"{TASK_LIST_DOC}: {item_id} has empty {phase_name} details"
                )

    return errors


def _check_canonical_ownership(repo_root: Path) -> list[str]:
    """DOC-004: Canonical docs must have Owner and Refresh Trigger fields."""
    errors: list[str] = []
    owner_pattern = re.compile(r"\*\*Owner:\*\*", re.MULTILINE)
    refresh_pattern = re.compile(r"\*\*Refresh Trigger:\*\*", re.MULTILINE)

    for rel_path in CANONICAL_DOCS:
        text = _read_text(repo_root, rel_path)
        if not owner_pattern.search(text):
            errors.append(f"{rel_path}: missing '**Owner:**' field (DOC-004)")
        if not refresh_pattern.search(text):
            errors.append(f"{rel_path}: missing '**Refresh Trigger:**' field (DOC-004)")

    return errors


def _check_historical_inactive_language(repo_root: Path) -> list[str]:
    """DOC-005: Historical docs must contain inactive-tracker phrase in top 15 lines."""
    errors: list[str] = []
    inactive_pattern = re.compile(
        r"(not\s+(an?\s+)?active\s+tracker|superseded|predates|retained\s+for\s+(sprint\s+)?history)",
        re.IGNORECASE,
    )

    for rel_path in HISTORICAL_DOCS:
        text = _read_text(repo_root, rel_path)
        top = _top_lines(text)
        if not inactive_pattern.search(top):
            errors.append(
                f"{rel_path}: missing inactive-tracker language in top 15 lines (DOC-005)"
            )

    return errors


def _check_required_doc_sections(repo_root: Path) -> list[str]:
    """DOC-006: Key docs must contain required section headings."""
    errors: list[str] = []

    for rel_path, sections in REQUIRED_SECTIONS.items():
        text = _read_text(repo_root, rel_path)
        for section in sections:
            # Match as a markdown heading or bold field
            heading_pattern = re.compile(
                rf"(^#+\s+.*{re.escape(section)}|\*\*{re.escape(section)}[:\*])",
                re.MULTILINE | re.IGNORECASE,
            )
            if not heading_pattern.search(text):
                errors.append(
                    f"{rel_path}: missing required section '{section}' (DOC-006)"
                )

    return errors


def lint_docs(repo_root: Path) -> list[str]:
    checks = (
        _check_last_updated,
        _check_historical_banners,
        _check_backend_status_classification,
        _check_backend_status_stale_marker,
        _check_feature_index_not_planning,
        _check_task_list_tdd_phases,
        _check_canonical_ownership,
        _check_historical_inactive_language,
        _check_required_doc_sections,
    )

    errors: list[str] = []
    for check in checks:
        try:
            errors.extend(check(repo_root))
        except FileNotFoundError as exc:
            errors.append(str(exc))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint HealthCentral docs for drift")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Path to repository root (default: inferred from script location)",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    errors = lint_docs(repo_root)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"\nDocs lint failed with {len(errors)} error(s).")
        return 1

    print("Docs lint passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
