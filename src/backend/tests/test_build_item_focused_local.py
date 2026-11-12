"""HC-WFL-001..006: build-item.js runs focused backend tests locally and gates on CI (WF-FOCUSED-LOCAL).

build-item.js is a Workflow script (top-level `return`, `agent`), so it cannot be imported. The pure
helpers fullSuiteStep and ciBackendRule are extracted by name, as the HARNESS-SPEEDUP comment in that
file describes, and run under node. Wiring (the prompts call them) is asserted on the source text.
What this cannot see: whether a Haiku/Opus agent obeys the prompt. It only pins what the prompt says.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = (REPO_ROOT / ".claude" / "workflows" / "build-item.js").read_text(encoding="utf-8")

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")


def _fn(name: str) -> str:
    m = re.search(rf"^function {name}\b.*?^}}", SRC, re.S | re.M)
    assert m, f"function {name} not found in build-item.js"
    return m.group(0)


def _node(expr: str, *names: str):
    js = "\n".join(_fn(n) for n in names) + f"\nprocess.stdout.write(JSON.stringify({expr}))"
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True, timeout=30)
    return json.loads(out.stdout)


def _scope(backend: str) -> dict:
    return {
        "exit_code": 0,
        "output": f"docs_only=false\nbackend={backend}\nfrontend=false\nmods=false",
    }


@needs_node
def test_hc_wfl_001_backend_true_gets_focused_set_and_full_suite_ci() -> None:
    step = _node(
        "fullSuiteStep(fullSuite(SCOPE), parseScope(SCOPE.output))".replace("SCOPE", json.dumps(_scope("true"))),
        "parseScope", "fullSuite", "fullSuiteStep",
    )
    assert "FULL-SUITE-CI" in step
    assert "CI Backend Tests runs the full suite on this PR (WF-FOCUSED-LOCAL)" in step
    assert "src/backend/tests/" in step and "origin/main...HEAD" in step  # diff-derived test files
    assert "acceptance" in step
    assert "--collect-only -q | tail -1" in step
    assert "Do not run tests/ in full" in step
    assert "tests/ -q" not in step.replace("--collect-only -q", "")


@needs_node
def test_hc_wfl_002_backend_false_paths_are_unchanged() -> None:
    plain = _node("fullSuiteStep(false, {docs_only:false,backend:false,frontend:false,mods:false})",
                  "fullSuiteStep")
    assert "SKIPPED-SCOPE" in plain and "FULL-SUITE-CI" not in plain
    docs = _node("fullSuiteStep(false, {docs_only:true,backend:false,frontend:false,mods:false})",
                 "fullSuiteStep")
    assert "SKIPPED-SCOPE" in docs and "CI skips Backend Tests by design" in docs


@needs_node
def test_hc_wfl_003_verify_rule_requires_ci_backend_tests_success_on_head() -> None:
    rule = _node("ciBackendRule(7)", "ciBackendRule")
    assert "gh pr checks 7 --json name,state" in rule
    assert "Backend Tests" in rule and "SUCCESS" in rule
    assert "headRefOid" in rule and "git rev-parse HEAD" in rule
    assert "bounded" in rule and "sleep" in rule
    for bad in ("PENDING", "SKIPPED"):
        assert bad in rule
    assert "never" in rule.lower() and "passed" in rule
    assert '[blocked:claude]' in rule and "FAILED" in rule


def test_hc_wfl_004_prompts_are_wired_to_the_helpers() -> None:
    assert "fullSuiteStep(full, s)" in SRC
    verify = SRC[SRC.index("phase('Verify')"):]
    assert "${ciBackendRule(plan.pr_number)}" in verify
    # The old rule (a full local suite is required for backend=true) must be gone.
    assert "must hold a full backend suite run" not in verify
    # gh pr ready must wait on the CI gate.
    assert "only if the CI Backend Tests gate" in verify


@needs_node
@pytest.mark.parametrize(
    "scope",
    [
        None,
        {"exit_code": 1, "output": "docs_only=false\nbackend=false\nfrontend=false\nmods=false"},
        {"exit_code": 0, "output": ""},
        {"exit_code": 0, "output": "backend=false"},
        {"exit_code": 0, "output": "docs_only=false\nbackend=false\nfrontend=false\nmods=false\nextra=1"},
        {"exit_code": 0, "output": "docs_only=false\nbackend=false\nbackend=false\nmods=false"},
        {"exit_code": 0, "output": "warning: x\nbackend=false"},
    ],
)
def test_hc_wfl_005_malformed_scope_fails_closed_to_focused_plus_ci(scope) -> None:
    s = json.dumps(scope)
    expr = f"(() => {{ const sc = {s}; const p = sc && sc.exit_code === 0 ? parseScope(sc.output) : null; return [fullSuite(sc), fullSuiteStep(fullSuite(sc), p)] }})()"
    full, step = _node(expr, "parseScope", "fullSuite", "fullSuiteStep")
    assert full is True
    assert "FULL-SUITE-CI" in step and "SKIPPED-SCOPE" not in step


def test_hc_wfl_006_verify_treats_unparseable_scope_as_requiring_ci() -> None:
    verify = SRC[SRC.index("phase('Verify')"):]
    assert "fails, or does not print exactly the four lines" in verify
    i = verify.index("fails, or does not print exactly the four lines")
    assert "CI Backend Tests" in verify[i : i + 700]
