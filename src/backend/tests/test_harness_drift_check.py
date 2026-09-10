"""Regression coverage for the harness drift checker."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "harness_drift_check.py"
SPEC = importlib.util.spec_from_file_location("harness_drift_check_root", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
harness_drift_check = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = harness_drift_check
SPEC.loader.exec_module(harness_drift_check)

find_drift = harness_drift_check.find_drift
main = harness_drift_check.main


def _write_doc(repo_root: Path, text: str) -> None:
    agentic_dir = repo_root / "docs" / "agentic"
    agentic_dir.mkdir(parents=True, exist_ok=True)
    (agentic_dir / "harness.md").write_text(text, encoding="utf-8")


def test_passes_when_every_named_path_exists(tmp_path: Path, capsys) -> None:
    """A doc naming a path that actually exists should not be flagged."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "docs_lint.py").write_text("# ok\n", encoding="utf-8")
    _write_doc(tmp_path, "Run `scripts/docs_lint.py` before committing.\n")

    exit_code = main(["--repo-root", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Harness drift check passed" in captured.out


def test_fails_and_reports_missing_path_with_file_and_line(tmp_path: Path) -> None:
    """A doc naming a path that does not exist should fail with that path reported."""
    _write_doc(
        tmp_path,
        "# Harness\n\nSubagent definitions live in `.claude/agents/`.\n",
    )

    errors = find_drift(tmp_path)

    assert errors == ["docs/agentic/harness.md:3: missing path '.claude/agents/'"]


def test_skips_ambiguous_tokens(tmp_path: Path) -> None:
    """Commands, globs, symbol refs, and home-relative paths should be skipped."""
    _write_doc(
        tmp_path,
        "\n".join(
            [
                "Run `python3 scripts/does_not_exist.py` as an example command.",
                "Do not use `skills/asclexis-*` (a glob) or `~/venvs/ghost/bin/python`.",
                "See `modules/rag.py::_sanitize_chunk_text` for the symbol reference.",
                "",
            ]
        ),
    )

    errors = find_drift(tmp_path)

    assert errors == []


def test_resolves_paths_via_source_root_fallback(tmp_path: Path) -> None:
    """A module path written relative to src/backend/ should resolve there."""
    module_dir = tmp_path / "src" / "backend" / "modules"
    module_dir.mkdir(parents=True)
    (module_dir / "redaction.py").write_text("# ok\n", encoding="utf-8")
    _write_doc(tmp_path, "Ask before touching `modules/redaction.py`.\n")

    assert find_drift(tmp_path) == []
