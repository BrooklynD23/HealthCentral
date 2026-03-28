"""Regression coverage for the repo hygiene checker."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "repo_hygiene_check.py"
SPEC = importlib.util.spec_from_file_location("repo_hygiene_check_root", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
repo_hygiene_check = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = repo_hygiene_check
SPEC.loader.exec_module(repo_hygiene_check)

APPROVED_HELPER_DIRS = repo_hygiene_check.APPROVED_HELPER_DIRS
find_repo_hygiene_violations = repo_hygiene_check.find_repo_hygiene_violations
format_failure_lines = repo_hygiene_check.format_failure_lines
main = repo_hygiene_check.main


def test_passes_with_only_allowed_helper_dirs_and_normal_project_files(
    tmp_path: Path, capsys
) -> None:
    """Approved helper dirs and ordinary repo files should not fail the check."""
    for directory_name in APPROVED_HELPER_DIRS:
        (tmp_path / directory_name).mkdir()

    (tmp_path / "README.md").write_text("# ok\n", encoding="utf-8")
    (tmp_path / "ROADMAP.md").write_text("# ok\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "security_best_practices_report.md").write_text(
        "nested report is out of scope\n",
        encoding="utf-8",
    )

    exit_code = main(["--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Repo hygiene passed" in captured.out


def test_finds_root_scratch_files_with_stable_sorted_output(tmp_path: Path) -> None:
    """Known root scratch filenames should be reported deterministically."""
    (tmp_path / "security_best_practices_report.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "PLAN.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "HANDOFF-PHASE2.md").write_text("x\n", encoding="utf-8")

    violations = find_repo_hygiene_violations(tmp_path)

    assert [(v.relative_path, v.matched_pattern) for v in violations] == [
        ("HANDOFF-PHASE2.md", "HANDOFF-*.md"),
        ("PLAN.md", "PLAN.md"),
        ("security_best_practices_report.md", "*_report*.md"),
    ]


def test_main_reports_file_level_failures(tmp_path: Path, capsys) -> None:
    """CLI output should name each offending file and return a failing exit code."""
    (tmp_path / "PLAN.md").write_text("temporary plan\n", encoding="utf-8")
    (tmp_path / "HANDOFF-TEAM.md").write_text("temporary handoff\n", encoding="utf-8")

    exit_code = main(["--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert format_failure_lines(find_repo_hygiene_violations(tmp_path)) == [
        "ERROR: root scratch artifact 'HANDOFF-TEAM.md' matches 'HANDOFF-*.md'",
        "ERROR: root scratch artifact 'PLAN.md' matches 'PLAN.md'",
    ]
    assert "HANDOFF-TEAM.md" in captured.out
    assert "PLAN.md" in captured.out
    assert "Repo hygiene failed" in captured.out
