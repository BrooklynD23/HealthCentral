"""HC-AGENTS-001..007 — the five checked-in Claude Code subagent definitions.
(HC-AGENTS-008 is a manual gate; it is appended here only after owner sign-off OG-3.)

Owner decisions D1 / D1-scope (docs/capstone-report/owner-decisions-2026-09-27.md):
author all five subagents named in docs/agentic/harness.md, un-ignore
.claude/agents/, commit them. Four are read-only scanners; the fifth,
windows-bootstrap-engineer, has Edit plus a declared write scope.

These tests pin the *declaration*. Claude Code enforces the `tools` allowlist
at runtime. It does not enforce `write_scope`: unknown frontmatter keys are
ignored. That bound holds through the agent's instructions and the
orchestrator's `git diff --name-only` review (docs/agentic/harness.md).
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"

SCANNERS = (
    "docs-consistency-scanner",
    "dependency-policy-auditor",
    "agentic-roadmap-researcher",
    "verification-engineer",
)
IMPLEMENTER = "windows-bootstrap-engineer"
ALL_AGENTS = SCANNERS + (IMPLEMENTER,)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    """Run git in the repo root. Fails (never skips) without git: a skip would
    read as a pass for a test whose whole job is to say what git will track."""
    if shutil.which("git") is None:
        pytest.fail("git is required: these tests check what git will track")
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )


def test_hc_agents_001_agent_files_are_not_gitignored() -> None:
    """HC-AGENTS-001. `--no-index` matters: without it, check-ignore never
    reports a *tracked* path, so this would pass vacuously once committed.
    Exit 0 = ignored, 1 = not ignored, 128 = error."""
    still_ignored = [
        name
        for name in ALL_AGENTS
        if _git("check-ignore", "--no-index", "-q", f".claude/agents/{name}.md").returncode != 1
    ]
    assert still_ignored == [], f"still ignored by .gitignore: {still_ignored}"


def test_hc_agents_002_unignore_stays_narrow() -> None:
    """HC-AGENTS-002. Only .claude/agents/ (beside the existing .claude/skills/)
    is un-ignored. Settings and hooks stay ignored: D1 licenses no hook, and
    CS4610_Report_Demo/README.md states no .claude/settings.json exists."""
    must_stay_ignored = [
        ".claude/settings.json",
        ".claude/settings.local.json",
        ".claude/hooks/pre_tool_use.sh",
    ]
    exposed = [
        rel
        for rel in must_stay_ignored
        if _git("check-ignore", "--no-index", "-q", rel).returncode != 0
    ]
    assert exposed == [], f"un-ignore is too wide; now trackable: {exposed}"


READ_ONLY_TOOLS = {"Read", "Grep", "Glob"}
IMPLEMENTER_TOOLS = {"Read", "Grep", "Glob", "Edit"}
# Write-capable per the Claude Code sub-agents docs (Bash/PowerShell "can include
# write operations"). MultiEdit is listed defensively for older clients.
WRITE_CAPABLE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash", "PowerShell"}
IMPLEMENTER_WRITE_SCOPE = ["dev.ps1", "dev.bat"]
ALLOWED_KEYS = {"name", "description", "tools", "model", "write_scope"}
SCANNER_MODEL = "haiku"
IMPLEMENTER_MODEL = "opus"
SCANNER_LIMIT_LINE = "You cannot edit files, run commands, or access the network."
IMPLEMENTER_LIMIT_LINE = "You cannot create files, run commands, or access the network."
DISPATCH_LINE = "Run only in a fresh source-only git worktree."
ASK_FIRST_PATHS = (
    "src/backend/modules/interpret_safety.py",
    "src/backend/modules/redaction.py",
    "src/backend/modules/faithfulness.py",
    "src/backend/modules/verifier_agent.py",
    "src/backend/core/auth.py",
)
ASK_FIRST_LABEL = "ASK-FIRST: owner approval required before any edit."
ASK_FIRST_NO_PATCH = "Never propose a patch to them."


def _split_frontmatter(path: Path) -> tuple[dict, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        pytest.fail(f"{path.name}: line 1 must be exactly '---' (no BOM)")
    try:
        end = lines.index("---", 1)
    except ValueError:
        pytest.fail(f"{path.name}: frontmatter has no closing '---' line")
    meta = yaml.safe_load("\n".join(lines[1:end]))
    if not isinstance(meta, dict):
        pytest.fail(f"{path.name}: frontmatter is not a YAML mapping")
    return meta, "\n".join(lines[end + 1 :])


def _load(name: str) -> tuple[dict, str]:
    path = AGENTS_DIR / f"{name}.md"
    if not path.is_file():
        pytest.fail(f"missing {path.relative_to(REPO_ROOT).as_posix()}")
    return _split_frontmatter(path)


def _tools(meta: dict) -> list[str]:
    raw = meta.get("tools")
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else str(raw).split(",")
    return [str(item).strip() for item in items if str(item).strip()]


def test_hc_agents_003_exactly_the_five_named_agents_are_tracked() -> None:
    """HC-AGENTS-003. No extra file (a sixth agent, a README, an editor
    backup) and every file is in git's index — the drift check only sees disk."""
    expected = sorted(f"{name}.md" for name in ALL_AGENTS)
    on_disk = sorted(p.name for p in AGENTS_DIR.iterdir()) if AGENTS_DIR.is_dir() else []
    assert on_disk == expected
    tracked = sorted(_git("ls-files", "--", ".claude/agents").stdout.split())
    assert tracked == [f".claude/agents/{name}" for name in expected]


def test_hc_agents_004_frontmatter_parses_with_required_fields() -> None:
    """HC-AGENTS-004. A missing `tools` field is the dangerous case: Claude
    Code then grants the subagent every tool, including Edit/Write/Bash."""
    problems: list[str] = []
    for name in ALL_AGENTS:
        meta, body = _load(name)
        if meta.get("name") != name:
            problems.append(f"{name}: name field is {meta.get('name')!r}")
        description = meta.get("description")
        if not isinstance(description, str) or not description.strip():
            problems.append(f"{name}: description missing or empty")
        if "tools" not in meta or not _tools(meta):
            problems.append(f"{name}: no tools field - Claude Code would grant every tool")
        extra = sorted(set(meta) - ALLOWED_KEYS)
        if extra:
            problems.append(f"{name}: keys outside the approved scope: {extra}")
        if not body.strip():
            problems.append(f"{name}: empty body")
    assert problems == []


def test_hc_agents_005_scanners_are_read_only() -> None:
    """HC-AGENTS-005 (handoff W-1 test 2). Exactly Read, Grep, Glob; no write
    tool; the cheap model harness.md promises; no write scope."""
    problems: list[str] = []
    for name in SCANNERS:
        meta, _body = _load(name)
        tools = set(_tools(meta))
        if tools != READ_ONLY_TOOLS:
            problems.append(f"{name}: tools {sorted(tools)} != {sorted(READ_ONLY_TOOLS)}")
        if tools & WRITE_CAPABLE_TOOLS:
            problems.append(f"{name}: write-capable tools {sorted(tools & WRITE_CAPABLE_TOOLS)}")
        if meta.get("model") != SCANNER_MODEL:
            problems.append(f"{name}: model {meta.get('model')!r} != {SCANNER_MODEL!r}")
        if "write_scope" in meta:
            problems.append(f"{name}: a read-only scanner declares write_scope")
    assert problems == []


def test_hc_agents_006_bootstrap_engineer_scope_is_declared_and_bounded() -> None:
    """HC-AGENTS-006. Pins the declaration only: Claude Code does not enforce
    write_scope. No Write/Bash/PowerShell/NotebookEdit, so it cannot create
    files or run commands; Edit alone is the only write path."""
    meta, body = _load(IMPLEMENTER)
    assert set(_tools(meta)) == IMPLEMENTER_TOOLS
    assert meta.get("model") == IMPLEMENTER_MODEL
    assert meta.get("write_scope") == IMPLEMENTER_WRITE_SCOPE
    for rel in IMPLEMENTER_WRITE_SCOPE:
        assert (REPO_ROOT / rel).is_file(), f"write_scope names a missing file: {rel}"
        assert f"`{rel}`" in body, f"body does not restate write_scope entry {rel}"


def test_hc_agents_007_body_states_its_real_tools() -> None:
    """HC-AGENTS-007. The body (the subagent's system prompt) must state the
    same tool list as the frontmatter, the matching limit sentence, the
    patient-data dispatch boundary, and the ask-first list with its label rule
    (CLAUDE.md §1: read allowed, no patches, findings labelled ASK-FIRST), so a
    body cannot describe a capability its tools do not grant or drop a rule."""
    problems: list[str] = []
    for name in ALL_AGENTS:
        meta, body = _load(name)
        tools_line = f"Tools: {', '.join(_tools(meta))}."
        if tools_line not in body:
            problems.append(f"{name}: body lacks {tools_line!r}")
        limit = SCANNER_LIMIT_LINE if name in SCANNERS else IMPLEMENTER_LIMIT_LINE
        if limit not in body:
            problems.append(f"{name}: body lacks {limit!r}")
        if DISPATCH_LINE not in body:
            problems.append(f"{name}: body lacks {DISPATCH_LINE!r}")
        for rel in ASK_FIRST_PATHS:
            if f"`{rel}`" not in body:
                problems.append(f"{name}: ask-first list lacks {rel}")
            if not (REPO_ROOT / rel).is_file():
                problems.append(f"{name}: ask-first path missing on disk: {rel}")
        for rule in (ASK_FIRST_NO_PATCH, ASK_FIRST_LABEL):
            if rule not in body:
                problems.append(f"{name}: body lacks {rule!r}")
    assert problems == []


def _load_drift_check():
    script = REPO_ROOT / "scripts" / "harness_drift_check.py"
    spec = importlib.util.spec_from_file_location("harness_drift_check_agents", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_hc_agents_008_harness_docs_name_every_agent_and_have_no_drift(capsys) -> None:
    """HC-AGENTS-008 (handoff W-1 test 3; in the suite by owner sign-off OG-3).
    harness.md must name each agent by its full path: the drift check skips
    bare names, so only a full path makes it verify that each file exists.
    Then the drift check must pass on the real repo. It checks disk, not git:
    HC-AGENTS-003 is what proves the files are tracked."""
    harness = (REPO_ROOT / "docs" / "agentic" / "harness.md").read_text(encoding="utf-8")
    unnamed = [name for name in ALL_AGENTS if f"`.claude/agents/{name}.md`" not in harness]
    assert unnamed == [], f"harness.md does not name by full path: {unnamed}"
    exit_code = _load_drift_check().main(["--repo-root", str(REPO_ROOT)])
    assert exit_code == 0, capsys.readouterr().out
