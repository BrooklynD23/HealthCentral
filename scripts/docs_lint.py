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
  8. (DOC-007) Relative markdown links in docs must resolve to an existing file.
  9. (DOC-009) `npm run <script>` references in the frontend README must exist in
     src/frontend/package.json (catches README drift when scripts are renamed/removed).
  10. (DOC-010) README.md, docs/00_architecture_plans_index.md, and
      docs/features/TASK_LIST.md must state an identical "Canonical Doc Order".
  11. (DOC-011) Every doc under docs/ is reachable from the index system --
      an unlinked doc is drift with a timestamp.
  13. (DOC-013) Everything under docs/archive/ carries a Historical Reference
      banner, so retained history cannot be mistaken for live guidance.
"""

from __future__ import annotations

import argparse
import json
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
    "docs/archive/plans/UI-implementation-2-4.md",
    "docs/archive/plans/remaining-features-implementation.md",
    "docs/archive/plans/next-agent-documentation-consolidation.md",
    "docs/archive/plans/sprint-phase-2026-02-13-implementation-plan.md",
    "docs/archive/plans/2026-03-04-handoff.md",
    "docs/archive/plans/2026-02-15-sprint-06-handoff-prompt.md",
    "docs/archive/plans/2026-03-28-roadmap-gsd-m001-m003-historical.md",
    "docs/plans/2026-05-15-cursor-lab-workflow-plan.md",
    "docs/plans/implementation-log/README.md",
    "docs/plans/implementation-log/2024-12-28_project-structure-setup.md",
    "docs/plans/implementation-log/2026-02-04_alembic-dual-migrations.md",
    "docs/plans/implementation-log/2026-06-11_agent-overhaul-plan.md",
    "docs/plans/implementation-log/2026-06-11_breakage-map.md",
    "docs/plans/implementation-log/2026-06-11_verification-report.md",
]

# DOC-010: files whose "Canonical Doc Order" list must be textually identical
# (order + membership) — this is the exact drift that happened once undetected.
CANONICAL_ORDER_DOCS = [
    "README.md",
    "docs/00_architecture_plans_index.md",
    "docs/features/TASK_LIST.md",
]

# Role docs (thin architecture-domain indexes) reuse the same Owner/Refresh
# Trigger ownership check DOC-004 applies to CANONICAL_DOCS.
ROLE_DOCS = [
    "docs/roles/00_roles_index.md",
    "docs/roles/backend-api.md",
    "docs/roles/frontend.md",
    "docs/roles/data-and-migrations.md",
    "docs/roles/ai-llm-pipeline-and-safety.md",
    "docs/roles/security-and-compliance.md",
    "docs/roles/devops-and-ci.md",
    "docs/roles/product-and-prd.md",
]

REQUIRED_SECTIONS: dict[str, list[str]] = {
    "README.md": ["API Overview", "Quick Start"],
    "docs/features/03_features_prd.md": ["Last Updated"],
}

BACKEND_STATUS_DOC = "docs/05_backend_integration_status.md"
TASK_LIST_DOC = "docs/features/TASK_LIST.md"
FEATURE_INDEX_DOC = "docs/features/00_features_index.md"

# DOC-009: frontend README and the package.json it documents.
FRONTEND_README = "src/frontend/README.md"
FRONTEND_PACKAGE_JSON = "src/frontend/package.json"

# DOC-007: extra markdown roots (beyond docs/) whose links are checked.
# AGENT.md and CLAUDE.md are here because agents follow their links first and
# have no way to notice a dead one; they were unchecked until the skills routing
# table added links to both README files.
EXTRA_LINK_ROOTS = ["README.md", FRONTEND_README, "AGENT.md", "CLAUDE.md"]


def _read_text(repo_root: Path, relative_path: str) -> str:
    path = repo_root / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {relative_path}")
    return path.read_text(encoding="utf-8")


_YAML_FRONTMATTER = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


def _top_lines(text: str, count: int = 15) -> str:
    """First `count` lines of the file's actual prose, skipping YAML
    frontmatter if present — a file with real frontmatter (e.g. a vendored
    Cursor/tool plan) shouldn't have its 'near the top' banner window eaten
    by structured metadata that isn't what a reader sees as the top."""
    body = _YAML_FRONTMATTER.sub("", text, count=1)
    return "\n".join(body.splitlines()[:count])


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
    """DOC-004: Canonical docs (and role docs, which reuse the same
    ownership convention) must have Owner and Refresh Trigger fields."""
    errors: list[str] = []
    owner_pattern = re.compile(r"\*\*Owner:\*\*", re.MULTILINE)
    refresh_pattern = re.compile(r"\*\*Refresh Trigger:\*\*", re.MULTILINE)

    for rel_path in CANONICAL_DOCS + ROLE_DOCS:
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


_FENCED_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _markdown_files(repo_root: Path) -> list[Path]:
    """All markdown whose internal links DOC-007 validates: everything under
    docs/, plus the repo-root and frontend READMEs (the files most prone to
    pointing at moved/renamed paths)."""
    files = sorted((repo_root / "docs").rglob("*.md"))
    for rel in EXTRA_LINK_ROOTS:
        p = repo_root / rel
        if p.exists():
            files.append(p)
    return files


def _read_markdown_corpus(repo_root: Path) -> list[tuple[Path, str]]:
    """Reads every markdown file's raw text exactly once, so callers that
    need multiple passes over the corpus (link extraction, title/summary
    extraction, graph building) don't each re-read every file from disk."""
    return [
        (path, path.read_text(encoding="utf-8", errors="ignore"))
        for path in _markdown_files(repo_root)
    ]


def _iter_markdown_links(repo_root: Path, corpus: list[tuple[Path, str]] | None = None):
    """Shared link-collection pass used by both DOC-007 (validation) and the
    backlink-graph emitter: yields (rel_path, target, resolved_rel_path_or_None)
    for every relative markdown link in the docs corpus. External links,
    in-page anchors, and links inside fenced code blocks are skipped.

    Pass a pre-read `corpus` (see `_read_markdown_corpus`) to avoid re-reading
    every file from disk when the caller also needs the raw text elsewhere."""
    if corpus is None:
        corpus = _read_markdown_corpus(repo_root)
    for path, raw_text in corpus:
        text = _FENCED_BLOCK.sub("", raw_text)
        rel_path = path.relative_to(repo_root).as_posix()
        for match in _MD_LINK.finditer(text):
            target = match.group(1).strip()
            # Drop link titles: [t](path "Title") -> path; and <path> wrappers.
            target = target.split()[0].strip("<>") if target.split() else ""
            if not target or target.startswith(
                ("http://", "https://", "mailto:", "tel:", "#")
            ):
                continue
            path_part = target.split("#")[0].split("?")[0]
            if not path_part:
                continue
            resolved = (path.parent / path_part).resolve()
            if resolved.exists():
                try:
                    resolved_rel = resolved.relative_to(repo_root.resolve()).as_posix()
                except ValueError:
                    resolved_rel = None
            else:
                resolved_rel = None
            yield rel_path, target, resolved_rel


def _check_internal_links(repo_root: Path) -> list[str]:
    """DOC-007: every relative markdown link resolves to an existing path.

    External (http/https/mailto/tel), in-page anchors (#...), and links inside
    fenced code blocks are ignored. Anchors/queries are stripped before
    resolving — we check the file exists, not the anchor."""
    errors: list[str] = []
    for rel_path, target, resolved_rel in _iter_markdown_links(repo_root):
        if resolved_rel is None:
            errors.append(f"{rel_path}: broken internal link -> {target} (DOC-007)")
    return errors


def build_link_graph(
    repo_root: Path, corpus: list[tuple[Path, str]] | None = None
) -> dict[str, dict[str, list[str]]]:
    forward: dict[str, list[str]] = {}
    backward: dict[str, list[str]] = {}

    for rel_path, _target, resolved_rel in _iter_markdown_links(repo_root, corpus=corpus):
        if resolved_rel is None or resolved_rel == rel_path:
            continue
        forward.setdefault(rel_path, [])
        if resolved_rel not in forward[rel_path]:
            forward[rel_path].append(resolved_rel)
        backward.setdefault(resolved_rel, [])
        if rel_path not in backward[resolved_rel]:
            backward[resolved_rel].append(rel_path)

    return {"links_to": forward, "linked_from": backward}


def write_link_graph(repo_root: Path, out_path: str = "docs/_link_graph.json") -> Path:
    """Emit a forward+backward link graph from the same link data DOC-007
    already collects, so an agent can answer 'what links here?' without
    re-deriving structure each session. Not a lint check — purely descriptive,
    never fails the build. Call via `python3 scripts/docs_lint.py --link-graph`."""
    graph = build_link_graph(repo_root)
    dest = repo_root / out_path
    dest.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dest


_CANONICAL_ORDER_LIST_ITEM = re.compile(r"^\d+\.\s+`([^`]+)`", re.MULTILINE)


def _extract_canonical_order(text: str) -> list[str] | None:
    """Pull the numbered `path` list out of a 'Canonical Doc Order' /
    'Documentation Source of Truth' section. Returns None if no such
    section is found (caller decides whether that's an error)."""
    marker = re.search(
        r"(Canonical Doc Order|Documentation Source of Truth)", text
    )
    if not marker:
        return None
    tail = text[marker.end():]
    # Stop at the next heading so we don't pull in unrelated numbered lists.
    next_heading = re.search(r"\n#{1,6}\s", tail)
    if next_heading:
        tail = tail[: next_heading.start()]
    return _CANONICAL_ORDER_LIST_ITEM.findall(tail)


def _check_canonical_order_consistency(repo_root: Path) -> list[str]:
    """DOC-010: README.md, docs/00_architecture_plans_index.md, and
    docs/features/TASK_LIST.md must each state the identical canonical doc
    order (same paths, same order) — drift here happened once undetected
    (three near-identical-but-not-quite lists) before this check existed."""
    errors: list[str] = []
    orders: dict[str, list[str]] = {}

    for rel_path in CANONICAL_ORDER_DOCS:
        text = _read_text(repo_root, rel_path)
        order = _extract_canonical_order(text)
        if not order:
            errors.append(
                f"{rel_path}: no 'Canonical Doc Order' / 'Documentation Source "
                f"of Truth' numbered list found (DOC-010)"
            )
            continue
        orders[rel_path] = order

    if len(orders) >= 2:
        reference_path, reference_order = next(iter(orders.items()))
        for rel_path, order in orders.items():
            if order != reference_order:
                errors.append(
                    f"{rel_path}: canonical doc order does not match "
                    f"{reference_path} (DOC-010): {order} != {reference_order}"
                )

    return errors


def _check_archive_policy(repo_root: Path) -> list[str]:
    """DOC-013: docs/archive/ holds history, and must read like it.

    Every archived doc carries a Historical Reference banner in its top 15
    lines, and no canonical doc links into the archive as if it were current.
    Without this, archiving degrades into "a folder things got moved to" and
    the next reader cannot tell retained history from live guidance.
    """
    errors: list[str] = []
    archive_dir = repo_root / "docs" / "archive"
    if not archive_dir.is_dir():
        return errors

    for path in sorted(archive_dir.rglob("*.md")):
        rel_path = path.relative_to(repo_root).as_posix()
        if path.name == "README.md" and path.parent == archive_dir:
            continue  # the policy doc itself describes the archive, it is not archived
        head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:15])
        if "Historical Reference" not in head:
            errors.append(
                f"{rel_path}: archived doc missing 'Historical Reference' banner "
                f"in top 15 lines (DOC-013)"
            )
    return errors


def _check_orphaned_docs(repo_root: Path) -> list[str]:
    """DOC-011: every doc under docs/ is discoverable.

    A doc that nothing references is a doc nobody finds and nobody updates --
    it becomes drift with a timestamp. "Discoverable" means either another doc
    links to it (reusing the link data DOC-007 already collects) or it is
    catalogued in the generated flat map `docs/INDEX.md`, which is the
    documented entry point for exactly this purpose.

    This is deliberately weaker than "linked from a hand-maintained index":
    that stricter bar would be the better goal, but enforcing it today would
    fail on a corpus that predates the rule. What this catches now is a doc
    added without regenerating the index, i.e. a file no documented path
    reaches at all.
    """
    entry_points = {
        "docs/INDEX.md",
        "docs/00_architecture_plans_index.md",
        "docs/roles/00_roles_index.md",
    }

    linked: set[str] = set()
    for _source, _target, resolved in _iter_markdown_links(repo_root):
        if resolved:
            linked.add(resolved)

    index_path = repo_root / "docs" / "INDEX.md"
    index_text = index_path.read_text(encoding="utf-8") if index_path.exists() else ""

    errors: list[str] = []
    for path in sorted((repo_root / "docs").rglob("*.md")):
        rel_path = path.relative_to(repo_root).as_posix()
        if rel_path in entry_points or rel_path in linked or rel_path in index_text:
            continue
        errors.append(
            f"{rel_path}: not linked from any doc and absent from docs/INDEX.md "
            f"(DOC-011 orphan) -- run scripts/generate_docs_index.py"
        )
    return errors


def _check_frontend_readme_scripts(repo_root: Path) -> list[str]:
    """DOC-009: every `npm run <script>` in the frontend README is a real script
    in src/frontend/package.json (README drifts when scripts are renamed)."""
    errors: list[str] = []
    # NB: don't strip code fences here — the `npm run ...` commands live inside them.
    readme = _read_text(repo_root, FRONTEND_README)
    package = json.loads(_read_text(repo_root, FRONTEND_PACKAGE_JSON))
    defined = set(package.get("scripts", {}))
    for referenced in sorted(set(re.findall(r"npm run ([A-Za-z0-9:_-]+)", readme))):
        if referenced not in defined:
            errors.append(
                f"{FRONTEND_README}: references undefined npm script "
                f"'npm run {referenced}' (not in {FRONTEND_PACKAGE_JSON}) (DOC-009)"
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
        _check_internal_links,
        _check_frontend_readme_scripts,
        _check_canonical_order_consistency,
        _check_archive_policy,
        _check_orphaned_docs,
    )

    errors: list[str] = []
    for check in checks:
        try:
            errors.extend(check(repo_root))
        except FileNotFoundError as exc:
            errors.append(str(exc))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint Asclexis docs for drift")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Path to repository root (default: inferred from script location)",
    )
    parser.add_argument(
        "--link-graph",
        action="store_true",
        help="Also (re)generate docs/_link_graph.json from the DOC-007 link data",
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

    if args.link_graph:
        dest = write_link_graph(repo_root)
        print(f"Link graph written to {dest.relative_to(repo_root)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
