"""HC-SCOPE-001..015: scripts/change_scope.py (the docs-only / backend / frontend / mods rule)
and the .github/workflows/ci.yml wiring that consumes it (HARNESS-SPEEDUP, owner SPEEDUP-1-3).

The script is run by subprocess, as test_docs_lint.py does for its script. Reference-check cases use
throwaway git repos (`--repo-root`), so they do not depend on what this repo tracks today.

Self-reference rule: this file must not contain the literal path or the quoted basename of the queue
file or the owner-decisions file. If it did, `git grep` would find it and those two docs would stop
being skippable. The tests below build those names from parts for that reason (HC-SCOPE-015 guards it).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "change_scope.py"
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"

KEYS = ("docs_only", "backend", "frontend", "mods")
FAIL_CLOSED = {"docs_only": "false", "backend": "true", "frontend": "true", "mods": "true"}

# Design section 1: a job is skipped only when `changes` succeeded and said docs_only=true.
FAIL_CLOSED_IF = (
    "${{ !cancelled() && !(needs.changes.result == 'success' "
    "&& needs.changes.outputs.docs_only == 'true') }}"
)
E2E_IF = (
    "${{ !cancelled() && needs.frontend-tests.result == 'success' "
    "&& needs.backend-tests.result == 'success' }}"
)


def _clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _run_raw(stdin: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *extra],
        input=stdin,
        capture_output=True,
        text=True,
        env=_clean_env(),
        cwd=REPO_ROOT,
        timeout=120,
    )


def scope(paths: list[str], repo_root: Path | None = None) -> dict[str, str]:
    """Run the script and parse its output. Fails unless it is exactly the 4 lines, exit 0."""
    extra = ["--repo-root", str(repo_root)] if repo_root is not None else []
    proc = _run_raw("".join(f"{p}\n" for p in paths), *extra)
    assert proc.returncode == 0, f"exit {proc.returncode}: {proc.stderr}"
    lines = proc.stdout.splitlines()
    assert len(lines) == 4, f"expected 4 lines, got {proc.stdout!r}"
    parsed: dict[str, str] = {}
    for key, line in zip(KEYS, lines):
        name, _, value = line.partition("=")
        assert name == key, f"line order: {proc.stdout!r}"
        assert value in ("true", "false"), f"bad value in {line!r}"
        parsed[name] = value
    return parsed


def make_repo(root: Path, files: dict[str, str]) -> Path:
    """A throwaway git repo with the given tracked files."""
    root.mkdir(parents=True, exist_ok=True)

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
            cwd=root,
            check=True,
            capture_output=True,
            env=_clean_env(),
        )

    git("init", "-q")
    for rel, text in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    git("add", "--", *files)
    git("commit", "-q", "-m", "fixture")
    return root


def real_git_ls_files(*patterns: str) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--", *patterns],
        capture_output=True,
        text=True,
        check=True,
        env=_clean_env(),
    ).stdout
    return out.splitlines()


def only(**flags: str) -> dict[str, str]:
    """Expected result: everything false, except the given keys."""
    expected = {k: "false" for k in KEYS}
    expected.update(flags)
    return expected


# Names built from parts so that this file never holds the literal path or quoted basename (see top).
def queue_path() -> str:
    hits = [p for p in real_git_ls_files("docs/plans") if p.endswith("/" + "queue" + ".md")]
    assert len(hits) == 1, hits
    return hits[0]


# The git grep search set, pinned against scripts/change_scope.py::SEARCH_PATHSPECS by HC-SCOPE-012.
SEARCH_PATHSPECS = ("src", "scripts", ".github", ".claude/mods")

OWNER_DECISIONS_NAME = "owner-decisions-" + "2026-09-27" + ".md"


# --- HC-SCOPE-001..007: the plan's rule --------------------------------------------------------


def test_hc_scope_001_docs_only_when_nothing_references_the_paths(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "r", {"src/backend/tests/test_a.py": "def test_a():\n    pass\n"})
    got = scope(["docs/plans/x.md", "openwiki/README.md", "README.md", "CLAUDE.md"], repo)
    assert got == only(docs_only="true")


def test_hc_scope_002_carve_outs_are_explicit_cases_on_the_real_repo() -> None:
    # Subsumed by the reference check: both paths are named in tracked files under src/ and scripts/.
    for path in ("docs/agentic/harness.md", "THIRD_PARTY_NOTICES.md"):
        got = scope([path])
        assert got["docs_only"] == "false", path
        assert got["backend"] == "true", path


BACKEND_COUPLINGS = (
    "src/backend/main.py",
    "src/backend/requirements.txt",
    "src/backend/requirements-dev.txt",
    "src/backend/migrations/profile/versions/0001_x.py",
    "scripts/docs_lint.py",
    ".github/workflows/ci.yml",
    ".claude/hooks/session_log.py",
    ".claude/agents/some-agent.md",
    ".claude/mods/asclexis-rsi/hooks/logic.ts",
    ".claude/settings.json",
    "dev.sh",
    "THIRD_PARTY_NOTICES.md",
    "docs/agentic/harness.md",
    "src/frontend/src/components/settings/DataDonationCard.tsx",
)


def test_hc_scope_003_every_backend_coupling_sets_backend() -> None:
    for path in BACKEND_COUPLINGS:
        got = scope([path])
        assert got["backend"] == "true", path
        assert got["docs_only"] == "false", path


def test_hc_scope_004_frontend() -> None:
    assert scope(["src/frontend/src/App.tsx"]) == only(frontend="true")
    got = scope(["src/frontend/src/components/settings/DataDonationCard.tsx"])
    assert got["frontend"] == "true"
    assert got["backend"] == "true"
    assert got["docs_only"] == "false"


def test_hc_scope_005_mods() -> None:
    got = scope([".claude/mods/asclexis-rsi/rsi.test.ts"])
    assert got["mods"] == "true"
    assert got["backend"] == "true"
    assert got["docs_only"] == "false"


def test_hc_scope_006_workflow_script_alone_and_mixed(tmp_path: Path) -> None:
    assert scope([".claude/workflows/build-item.js"]) == only()
    repo = make_repo(tmp_path / "r", {"src/backend/tests/test_a.py": "x = 1\n"})
    got = scope(["docs/x.md", "src/backend/main.py"], repo)
    assert got["docs_only"] == "false"
    assert got["backend"] == "true"


@pytest.mark.parametrize(
    "stdin",
    ["", "\n", "../x\n", "/abs/x\n", "a\tb\n", "a\\b\n", "docs/ok.md\nbad\x01name\n", "C:/x.md\n"],
    ids=["empty", "blank", "dotdot", "absolute", "tab", "backslash", "control-in-second", "drive"],
)
def test_hc_scope_007_fail_closed_on_bad_input(stdin: str) -> None:
    proc = _run_raw(stdin)
    assert proc.returncode == 0
    assert proc.stdout.splitlines() == [f"{k}={v}" for k, v in FAIL_CLOSED.items()]


def test_hc_scope_007_fail_closed_when_git_grep_fails(tmp_path: Path) -> None:
    # A path that would otherwise be docs-only, searched in a directory that is not a repo.
    for root in (tmp_path / "missing", tmp_path):
        got = scope(["docs/plans/x.md"], root)
        assert got == FAIL_CLOSED, root


def test_hc_scope_007_fail_closed_on_unknown_argument() -> None:
    proc = _run_raw("docs/x.md\n", "--bogus")
    assert proc.returncode == 0
    assert proc.stdout.splitlines() == [f"{k}={v}" for k, v in FAIL_CLOSED.items()]


# --- HC-SCOPE-008: the ci.yml wiring ------------------------------------------------------------


def _ci() -> dict:
    return yaml.safe_load(CI_YML.read_text(encoding="utf-8"))


def test_hc_scope_008_ci_yml_wiring() -> None:
    data = _ci()
    jobs = data["jobs"]
    trigger = data.get("on", data.get(True))  # PyYAML reads a bare `on` key as True
    assert "paths" not in trigger["push"] and "paths-ignore" not in trigger["push"]
    assert "paths" not in trigger["pull_request"] and "paths-ignore" not in trigger["pull_request"]

    changes = jobs["changes"]
    assert changes["name"] == "Change Scope"
    assert str(changes["outputs"]["docs_only"]).startswith("${{ steps.")
    checkout = next(s for s in changes["steps"] if str(s.get("uses", "")).startswith("actions/checkout"))
    assert str(checkout["with"]["fetch-depth"]) == "2"
    run_text = "\n".join(str(s.get("run", "")) for s in changes["steps"])
    for needle in ("--no-renames", "HEAD^1", "scripts/change_scope.py"):
        assert needle in run_text, needle
    # L0 ruling #3 (#442): classify with the BASE branch's script, never the PR's copy. A PR that
    # broke its own classifier would otherwise fail open. `--repo-root .` keeps the git grep on the
    # PR checkout (the script otherwise searches its own directory, $RUNNER_TEMP, a non-repo).
    assert "git show HEAD^1:scripts/change_scope.py" in run_text
    assert "$RUNNER_TEMP" in run_text
    assert "--repo-root ." in run_text
    assert not re.search(r"python3\s+scripts/change_scope\.py", run_text), (
        "the changes job must not run the checkout's copy of the classifier"
    )

    for name in ("backend-tests", "frontend-tests", "agent-evals", "legacy-evals"):
        job = jobs[name]
        needs = job["needs"] if isinstance(job["needs"], list) else [job["needs"]]
        assert "changes" in needs, name
        assert job["if"] == FAIL_CLOSED_IF, name

    e2e = jobs["e2e-tests"]
    assert e2e["needs"] == ["changes", "frontend-tests", "backend-tests"]
    assert e2e["if"] == E2E_IF

    for name in ("docs-lint", "security-scan", "backend-lint", "rsi-replay"):
        assert "if" not in jobs[name], name
        assert "needs" not in jobs[name], name

    runs = [str(s.get("run", "")) for s in jobs["docs-lint"]["steps"]]
    check_at = next(i for i, r in enumerate(runs) if "generate_docs_index.py --check" in r)
    regen_at = next(i for i, r in enumerate(runs) if r.startswith("python3 scripts/generate_docs_index.py &&"))
    assert check_at < regen_at, "the --check step must run BEFORE the regenerate step"
    assert any("harness_drift_check.py --repo-root ." in r for r in runs)


# --- HC-SCOPE-009..015: the L0 reference-check ruling (PR 442, 2026-11-01) --------------------


def test_hc_scope_009_extraction_card_is_not_docs_only_on_the_real_repo() -> None:
    card = "docs/agentic/eval-cards/extraction.md"
    # The real coupling: HC-EXTR-003 reads the card. Find its referrers with our own git grep
    # (full path or quoted basename), not with the script under test.
    grep = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "grep", "-F", "-l", "-e", card, "-e", '"extraction.md"',
         "-e", "'extraction.md'", "--", "src", "scripts", ".github", ".claude/mods"],
        capture_output=True,
        text=True,
        env=_clean_env(),
    )
    assert "src/backend/tests/test_extraction_golden.py" in grep.stdout.splitlines()
    got = scope([card])
    assert got["docs_only"] == "false"
    assert got["backend"] == "true"


def test_hc_scope_010_queue_file_alone_is_docs_only_on_the_real_repo() -> None:
    path = queue_path()
    got = scope([path])
    if got != only(docs_only="true"):
        # Name the referrers, found with our own git grep (same pathspecs as the script).
        base = path.rsplit("/", 1)[-1]
        grep = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "grep", "-F", "-l", "-e", path, "-e", f'"{base}"',
             "-e", f"'{base}'", "--", *SEARCH_PATHSPECS],
            capture_output=True,
            text=True,
            env=_clean_env(),
        )
        pytest.fail(
            f"{path} is no longer docs-only (got {got}). Referencing files: "
            f"{grep.stdout.split() or 'none found by git grep'}. "
            "by design: queue-file edits must stay docs-only (L0 ruling, #442). "
            "Remove the reference from those files; do not widen the classifier."
        )


def test_hc_scope_011_owner_decisions_alone_is_docs_only_in_a_temp_repo(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "r", {"src/backend/tests/test_a.py": "x = 1\n"})
    assert scope(["docs/capstone-report/" + OWNER_DECISIONS_NAME], repo) == only(docs_only="true")


def test_hc_scope_012_a_mention_in_a_comment_or_a_pathlib_segment_makes_the_path_non_skippable(
    tmp_path: Path,
) -> None:
    repo = make_repo(
        tmp_path / "r",
        {
            "src/backend/tests/test_comment.py": "# see docs/plans/x.md for the design\n",
            "src/backend/tests/test_segments.py": (
                'CARD = ROOT / "docs" / "agentic" / "card-y.md"\n'
            ),
            "scripts/other.py": "# unquoted mention of loose-z.md only\n",
        },
    )
    got = scope(["docs/plans/x.md"], repo)
    assert got["docs_only"] == "false" and got["backend"] == "true"
    got = scope(["docs/agentic/card-y.md"], repo)
    assert got["docs_only"] == "false" and got["backend"] == "true"
    # An unquoted basename is not a reference: the boundary of the rule.
    assert scope(["docs/loose-z.md"], repo) == only(docs_only="true")
    # A referenced docs path forces backend=true even beside a frontend-only change.
    got = scope(["docs/plans/x.md", "src/frontend/src/App.tsx"], repo)
    assert got["backend"] == "true" and got["frontend"] == "true" and got["docs_only"] == "false"

    # The search set: src/ scripts/ .github/ .claude/mods/ and nothing else (L0 ruling #2, #442).
    # One referrer under each pathspec, each naming a different doc: each doc is not docs-only.
    inside = {
        "src/backend/tests/test_a.py": "docs/plans/in-src.md",
        "scripts/a.py": "docs/plans/in-scripts.md",
        ".github/workflows/a.yml": "docs/plans/in-github.md",
        ".claude/mods/m/a.ts": "docs/plans/in-mods.md",
    }
    repo = make_repo(
        tmp_path / "set",
        {
            **{ref: f"# {doc}\n" for ref, doc in inside.items()},
            # Outside the set: a referrer under .claude/workflows/ does not count.
            ".claude/workflows/a.js": "// docs/plans/outside.md\n",
        },
    )
    for referrer, doc in inside.items():
        assert scope([doc], repo)["docs_only"] == "false", f"{referrer} must make {doc} non-skippable"
    assert scope(["docs/plans/outside.md"], repo) == only(docs_only="true")


def test_hc_scope_013_any_non_docs_path_is_not_docs_only(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "r", {"src/backend/tests/test_a.py": "x = 1\n"})
    for path in ("foo.py", "data.json", "src/frontend/src/App.tsx", ".claude/workflows/build-item.js"):
        assert scope([path], repo)["docs_only"] == "false", path
        assert scope(["docs/ok.md", path], repo)["docs_only"] == "false", path


def test_hc_scope_014_generated_index_files_are_covered_by_the_check_step(tmp_path: Path) -> None:
    # ci.yml and tests name both files, so the reference check skips them (ruling item 3).
    assert scope(["docs/INDEX.md", "docs/_link_graph.json"]) == only(docs_only="true")
    repo = make_repo(
        tmp_path / "r",
        {"src/backend/tests/test_a.py": "# reads docs/INDEX.md and docs/_link_graph.json\n"},
    )
    assert scope(["docs/INDEX.md", "docs/_link_graph.json"], repo) == only(docs_only="true")


def test_hc_scope_015_script_and_tests_do_not_name_the_two_skippable_docs() -> None:
    parts = {
        "queue": ("docs/plans/2026-10-15-build-program/", "queue", ".md"),
        "owner-decisions": ("docs/capstone-report/", "owner-decisions-2026-09-27", ".md"),
    }
    for label, (folder, stem, ext) in parts.items():
        literals = (folder + stem + ext, '"' + stem + ext + '"', "'" + stem + ext + "'")
        for file in (SCRIPT, Path(__file__)):
            text = file.read_text(encoding="utf-8")
            for lit in literals:
                assert lit not in text, f"{file.name} holds {lit!r} ({label}): that doc stops being skippable"
