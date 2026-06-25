"""Regression coverage for the docs drift linter's link/README checks.

Covers DOC-007 (internal markdown links resolve) and DOC-009 (frontend README
`npm run` references exist in package.json). Loads the repo-root script the same
way test_repo_hygiene_check.py does.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "docs_lint.py"
SPEC = importlib.util.spec_from_file_location("docs_lint_root", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
docs_lint = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = docs_lint
SPEC.loader.exec_module(docs_lint)

_check_internal_links = docs_lint._check_internal_links
_check_frontend_readme_scripts = docs_lint._check_frontend_readme_scripts


# --- DOC-007: internal markdown links -------------------------------------

def test_doc007_flags_only_the_broken_relative_link(tmp_path: Path) -> None:
    """A missing relative target is reported; external/anchor/fenced links and
    valid targets are not."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "b.md").write_text("# B\n", encoding="utf-8")
    (docs / "a.md").write_text(
        "\n".join(
            [
                "[good](./b.md)",
                "[gone](./missing.md)",
                "[ext](https://example.com/x)",
                "[anchor](#section)",
                "[titled](./b.md \"hover title\")",
                "```",
                "[fenced-broken](./also-missing.md)",
                "```",
            ]
        ),
        encoding="utf-8",
    )

    errors = _check_internal_links(tmp_path)

    assert len(errors) == 1, errors
    assert "missing.md" in errors[0]
    assert "DOC-007" in errors[0]
    # fenced/external/anchor/valid links must not be flagged
    assert not any("also-missing.md" in e for e in errors)


def test_doc007_resolves_links_relative_to_each_file(tmp_path: Path) -> None:
    """A link is resolved against its own file's directory, not the repo root."""
    nested = tmp_path / "docs" / "sub"
    nested.mkdir(parents=True)
    (tmp_path / "docs" / "target.md").write_text("# T\n", encoding="utf-8")
    (nested / "page.md").write_text("[up](../target.md)\n", encoding="utf-8")

    assert _check_internal_links(tmp_path) == []


# --- DOC-009: frontend README npm scripts ---------------------------------

def _write_frontend(tmp_path: Path, readme: str, scripts: dict) -> None:
    fe = tmp_path / "src" / "frontend"
    fe.mkdir(parents=True)
    (fe / "README.md").write_text(readme, encoding="utf-8")
    (fe / "package.json").write_text(json.dumps({"scripts": scripts}), encoding="utf-8")


def test_doc009_flags_undefined_npm_script(tmp_path: Path) -> None:
    _write_frontend(
        tmp_path,
        readme="Run `npm run dev` then `npm run bogus`.\n",
        scripts={"dev": "vite", "build": "tsc && vite build"},
    )

    errors = _check_frontend_readme_scripts(tmp_path)

    assert len(errors) == 1, errors
    assert "bogus" in errors[0]
    assert "DOC-009" in errors[0]


def test_doc009_passes_when_all_scripts_defined(tmp_path: Path) -> None:
    _write_frontend(
        tmp_path,
        readme="```\nnpm run dev\nnpm run build\n```\n",
        scripts={"dev": "vite", "build": "tsc && vite build"},
    )

    assert _check_frontend_readme_scripts(tmp_path) == []


# --- Guard: the real repo must stay clean ---------------------------------

def test_doc007_and_doc009_pass_on_the_real_repo() -> None:
    """These checks are CI gates; assert the live tree satisfies them so the
    test suite catches drift before CI does."""
    assert _check_internal_links(REPO_ROOT) == []
    assert _check_frontend_readme_scripts(REPO_ROOT) == []
