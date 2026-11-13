"""scripts/pr_licence_gate.py weaken pass: test-weakening detector (AGENTIC-EVAL-WEAKEN, dev/CI tool, stdlib only).

HC-TWD-001  unconditional skip / xfail / test.skip() / it.skip / describe.skip / fixme added: FAIL
HC-TWD-002  .only added: FAIL
HC-TWD-003  retries added or raised: FAIL (lowered or unchanged: pass)
HC-TWD-004  numeric bound loosened in a gate file or gate-named test: FAIL; direction rule; == change WARN
HC-TWD-005  test function deleted: FAIL, unless a same-prefix HC-ID test (or the same name elsewhere) is added
HC-TWD-006  conditional skip (skipif, test.skip(cond), in-body pytest.skip): WARN
HC-TWD-007  bound loosened in an ordinary test: WARN
HC-TWD-008  assertion loosening (== to in, toBe to toBeTruthy, toEqual to toMatchObject, status set, assert removed): WARN
HC-TWD-009  EVAL-WAIVE:<ID>:weaken in owner-decisions downgrades the FAILs
HC-TWD-010  scope: product code and non-source files (.txt, .diff) are never scanned
HC-TWD-011  a comment, docstring or test name that says retries or skip is not flagged
HC-TWD-012  a withInfraRetry-style helper is not flagged (the judge row owns whether it hides a flake)
HC-TWD-013  end to end in a throwaway git repo: diff, exit code, waiver

Every before/after text lives in fixtures/weaken/weaken_cases.txt (a .txt, which the detector never
scans) so this file holds no trigger text that a later edit of it could be flagged for. The fixture queue
rows and the self-reference rule of test_pr_licence_gate.py apply here too: no queue file name below.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "scripts"
FIX = Path(__file__).resolve().parent / "fixtures" / "agentic_eval"
WFIX = Path(__file__).resolve().parent / "fixtures" / "weaken"  # outside the gate-owned dir: a new file there is ask-first


def _load(name: str):
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(name + "_under_test", SCRIPTS / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


gate = _load("pr_licence_gate")
QUEUE = (FIX / "fixture_queue.md").read_text(encoding="utf-8")
OWNER = (FIX / "fixture_owner.md").read_text(encoding="utf-8")


def _cases() -> dict[str, tuple[str, str | None, str | None]]:
    out: dict[str, tuple[str, str | None, str | None]] = {}
    name = path = side = None
    buf: list[str] = []
    cur: dict[str, str | None] = {}

    def flush():
        if side:
            text = "\n".join(buf)
            cur[side] = None if text == "@@@ absent" else "" if text == "@@@ empty" else text + "\n"

    for line in (WFIX / "weaken_cases.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("@@@ case "):
            flush()
            if name:
                out[name] = (path, cur.get("old"), cur.get("new"))
            _, _, name, path = line.split(" ", 3)
            side, buf, cur = None, [], {}
        elif line in ("@@@ old", "@@@ new"):
            flush()
            side, buf = line.split()[1], []
        else:
            buf.append(line)
    flush()
    out[name] = (path, cur.get("old"), cur.get("new"))
    return out


CASES = _cases()


def scan(*names: str):
    return gate.weaken_scan([(CASES[n][0],) + CASES[n][1:] for n in names])


def codes(findings, level):
    return sorted(f.code for f in findings if f.level == level)


def only(names, level, code):
    for n in names:
        f = scan(n)
        assert codes(f, level) == [code], (n, f)


def clean(names):
    for n in names:
        assert scan(n) == [], (n, scan(n))


def test_hc_twd_001_unconditional_skip_fails():
    only(("skip_py", "skipif_true_py", "xfail_py", "it_skip_js", "test_skip_bare_js", "describe_skip_js",
          "fixme_js", "xit_js"), "FAIL", "weaken-skip")
    # a conditional xfail is only a warning
    only(("xfail_cond_py",), "WARN", "weaken-cond-skip")


def test_hc_twd_002_only_fails():
    only(("only_js", "only_describe_js"), "FAIL", "weaken-only")


def test_hc_twd_003_retries_added_or_raised_fails():
    only(("retries_added_pw", "retries_raised_pw", "retries_configure_js", "reruns_toml", "retry_vitest",
          "flaky_mark_py"), "FAIL", "weaken-retries")
    clean(("retries_same_pw", "retries_lowered_pw", "retries_flag_zero_yml"))  # --retries=0 plus other numbers


def test_hc_twd_004_gate_bound_loosened_fails_by_direction():
    only(("bound_up_gate_js", "bound_lower_gate_py", "bound_upper_gate_py", "bound_gate_named_test",
          "bound_workflow_cov"), "FAIL", "weaken-bound")
    clean(("bound_down_gate_js", "bound_lower_raised_gate_py", "bound_unknown_key", "bound_comment_only"))
    # == changes warn (never fail), and only in a gate
    only(("bound_eq_gate_py",), "WARN", "weaken-bound")


def test_hc_twd_005_deleted_test_fails_unless_replaced():
    only(("deleted_py", "deleted_file_py", "deleted_js", "other_prefix_py"), "FAIL", "weaken-deleted-test")
    clean(("renamed_hc_py", "split_hc_py", "clean_py", "renamed_title_js"))  # a retitled JS test is a net-zero change
    # a test moved to another file in the same diff passes; with only the removal it fails
    assert scan("moved_a_py", "moved_b_py") == []
    assert codes(scan("moved_a_py"), "FAIL") == ["weaken-deleted-test"]
    # naming: the finding says which test went
    assert "test_b" in scan("deleted_py")[0].msg


def test_hc_twd_006_conditional_skip_warns():
    only(("skipif_py", "skip_cond_js", "inbody_skip_py", "skipif_vitest_js"), "WARN", "weaken-cond-skip")


def test_hc_twd_007_bound_loosened_in_ordinary_test_warns():
    only(("bound_ordinary_test",), "WARN", "weaken-bound")


def test_hc_twd_008_assertion_loosening_warns():
    only(("assert_eq_in_py", "assert_tobe_truthy_js", "assert_tobe_defined_js", "assert_toequal_match_js",
          "assert_status_set_js", "assert_removed_py"), "WARN", "weaken-assert")
    clean(("assert_added_py", "assert_tightened_py"))


def test_hc_twd_009_waiver_downgrades_fail_to_warn():
    files = [CASES["skip_py"], CASES["only_js"]]
    plain = gate.weaken_evaluate("fix(x): t (ROW-ONE)", files, QUEUE, OWNER)
    assert codes(plain, "FAIL") == ["weaken-only", "weaken-skip"]
    waived = gate.weaken_evaluate("fix(x): t (ROW-ONE)", files, QUEUE, OWNER + "\n| x | EVAL-WAIVE:ROW-ONE:weaken |\n")
    assert codes(waived, "FAIL") == [] and len(waived) == 2 and all("waived" in f.msg for f in waived)
    # a waiver for another row, or for another check, does not count
    for text in ("EVAL-WAIVE:ROW-BRACE:weaken", "EVAL-WAIVE:ROW-ONE:ask-first"):
        other = gate.weaken_evaluate("fix(x): t (ROW-ONE)", files, QUEUE, OWNER + "\n" + text + "\n")
        assert len(codes(other, "FAIL")) == 2, text


def test_hc_twd_010_scope_is_test_sources_and_gate_files_only():
    clean(("product_code_skip_py", "txt_fixture", "diff_fixture"))
    # the same weakening text in a test source or a gate file is seen
    assert gate.weaken_scope("src/backend/tests/test_a.py") and gate.weaken_scope("e2e/x.spec.ts")
    assert gate.weaken_scope(".github/workflows/ci.yml") and gate.weaken_scope("src/frontend/playwright.config.ts")
    assert gate.weaken_scope("scripts/security_gate.py") and gate.weaken_scope("src/frontend/scripts/check-bundle.mjs")
    assert not gate.weaken_scope("src/backend/modules/x.py") and not gate.weaken_scope("docs/agentic/evals.md")


def test_hc_twd_011_comment_docstring_or_test_name_is_not_flagged():
    clean(("comments_py", "comments_js", "string_url_js"))


def test_hc_twd_012_infra_retry_helper_is_not_flagged():
    clean(("infra_retry_js", "infra_retry_py"))


def _git(cwd, *args, env=None):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True, env=env)


def test_hc_twd_013_cli_end_to_end_in_a_throwaway_repo(tmp_path):
    repo = tmp_path / "r"
    (repo / "docs" / "plans" / "2026-01-01-build-program").mkdir(parents=True)
    (repo / "docs" / "capstone-report").mkdir(parents=True)
    (repo / "src" / "backend" / "tests").mkdir(parents=True)
    (repo / "docs" / "plans" / "2026-01-01-build-program" / ("queue" + ".md")).write_text(QUEUE, encoding="utf-8")
    (repo / "docs" / "capstone-report" / "owner-decisions-2026-01-01.md").write_text(OWNER, encoding="utf-8")
    path, old, new = CASES["skip_py"]
    (repo / "src" / "backend" / "tests" / "test_widgets.py").write_text(old, encoding="utf-8")
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base", env=env)
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "checkout", "-q", "-b", "pr")
    (repo / "src" / "backend" / "tests" / "test_widgets.py").write_text(new, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "pr", env=env)

    def run(title, extra=None):
        e = dict(os.environ, PR_TITLE=title, PR_NUMBER="5")
        e.pop("LICENCE_GATE_MODE", None)
        e.update(extra or {})
        return subprocess.run([sys.executable, str(SCRIPTS / "pr_licence_gate.py"), "--repo-root", str(repo),
                               "--base", "origin/main", "--head", "HEAD"], capture_output=True, text=True, env=e)

    bad = run("fix(x): t (ROW-ONE)")
    assert bad.returncode == 1, bad.stdout + bad.stderr
    assert "FAIL weaken-skip src/backend/tests/test_widgets.py" in bad.stdout
    assert run("fix(x): t (ROW-ONE)", {"LICENCE_GATE_MODE": "warn"}).returncode == 0
