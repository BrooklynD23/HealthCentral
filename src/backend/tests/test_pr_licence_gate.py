"""scripts/pr_licence_gate.py: PR scope-versus-licence gate (AGENTIC-EVAL-LICENCE, dev/CI tool, stdlib only).

HC-SLG-001  ask-first file with no matching owner-decisions row: FAIL
HC-SLG-002  an owner row naming the queue ID or #PR (and the file) licenses it
HC-SLG-003  EVAL-WAIVE:<ID>:ask-first in owner-decisions licenses it
HC-SLG-004  non-test source outside the row licence: FAIL; inside: pass
HC-SLG-005  non-BATCH PR with no queue ID: FAIL
HC-SLG-006  BATCH PR touching a non-.md file: FAIL (index files excepted)
HC-SLG-007  existing test file outside the licence: WARN; new test file: allowed
HC-SLG-008  over-broad licence token: WARN
HC-SLG-009  token expansion: be/ fe/ e2e/, braces, :line, dir prefix, basename, stem
HC-SLG-009b queue_drift.parse keeps a header->cell map (one queue parser)
HC-SLG-010  plan-section tokens, alias map, union over all IDs in the title
HC-SLG-011  parity with the rsi-loop.js DENY ask-first regexes (owner list is a superset)
HC-SLG-012  the build queue still classifies docs_only=true (change_scope trap), found by glob
HC-SLG-013  end to end in a throwaway git repo: diff, live ref, glob lookup, exit codes, warn mode

Self-reference rule (HC-SCOPE-015): this file never holds the queue file's path or quoted basename.
It finds the queue by glob, and the fixtures use other names.
"""

from __future__ import annotations

import importlib.util
import os
import posixpath
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "scripts"
FIX = Path(__file__).resolve().parent / "fixtures" / "agentic_eval"
QUEUE_GLOB = "docs/plans/*build-program/" + "queue" + ".md"  # parts: see the self-reference rule


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
qd = _load("queue_drift")

QUEUE = (FIX / "fixture_queue.md").read_text(encoding="utf-8")
OWNER = (FIX / "fixture_owner.md").read_text(encoding="utf-8")
PLAN = (FIX / "fixture_plan.md").read_text(encoding="utf-8")
QPATH = "plans/fixture_queue.md"


def _read(path: str):
    return {"plans/fixture_plan.md": PLAN}.get(posixpath.normpath(path))


def run(title, changes, pr=None, owner=OWNER, queue=QUEUE):
    """changes: list of (status, path). Returns the findings."""
    return gate.evaluate(title, pr, changes, queue, QPATH, owner, _read)


def levels(findings, level):
    return sorted((f.code, f.path) for f in findings if f.level == level)


A = "src/backend/modules/redaction.py"


def test_hc_slg_001_ask_first_without_owner_row_fails():
    for path in (
        "src/backend/modules/interpret_safety.py",
        "src/backend/modules/redaction.py",
        "src/backend/modules/faithfulness.py",
        "src/backend/modules/verifier_agent.py",
        "src/backend/core/auth.py",
        "src/backend/core/security.py",
        "src/backend/core/document_crypto.py",
        "src/backend/core/profile_database.py",
    ):
        f = run("fix(x): thing (ROW-PLAN-EXTRA)", [("M", path)], pr=5)
        assert ("ask-first", path) in levels(f, "FAIL"), path
    # api/profiles.py is a WARN, not a FAIL
    f = run("fix(x): thing (ROW-PLAN-EXTRA)", [("M", "src/backend/api/profiles.py")], pr=5)
    assert ("ask-first", "src/backend/api/profiles.py") in levels(f, "WARN")
    assert not [x for x in f if x.code == "ask-first" and x.level == "FAIL"]
    # the gate's own files need an owner row too (owner 1e)
    for own in (
        "scripts/pr_licence_gate.py",
        "src/backend/tests/test_pr_licence_gate.py",
        "src/backend/tests/fixtures/agentic_eval/fixture_queue.md",
    ):
        f = run("fix(x): thing (ROW-PLAN-EXTRA)", [("M", own)], pr=5)
        assert ("ask-first", own) in levels(f, "FAIL"), own


def test_hc_slg_002_owner_row_naming_id_or_pr_licenses_it():
    # by queue ID in the title
    f = run("fix(x): thing (ROW-ASK)", [("M", A)], pr=5)
    assert not [x for x in f if x.code == "ask-first"]
    # by #PR number alone (row "ROW-OTHER (gate on #88)" names core/security.py)
    sec = "src/backend/core/security.py"
    f = run("fix(x): thing (ROW-PLAN-EXTRA)", [("M", sec)], pr=88)
    assert not [x for x in f if x.code == "ask-first"]
    # a different PR number, no ID match: still FAIL
    f = run("fix(x): thing (ROW-PLAN-EXTRA)", [("M", sec)], pr=89)
    assert ("ask-first", sec) in levels(f, "FAIL")
    # #8 must not match #88
    f = run("fix(x): thing (ROW-PLAN-EXTRA)", [("M", sec)], pr=8)
    assert ("ask-first", sec) in levels(f, "FAIL")
    # a row naming the ID but not the file does not license it
    other = "src/backend/core/auth.py"
    f = run("fix(x): thing (ROW-ASK)", [("M", other)], pr=5)
    assert ("ask-first", other) in levels(f, "FAIL")


def test_hc_slg_003_waiver_licenses_ask_first():
    f = run("fix(x): thing (ROW-ONE)", [("M", "src/backend/core/auth.py")], pr=5)
    assert not [x for x in f if x.code == "ask-first"]
    f = run("fix(x): thing (ROW-ONE)", [("M", "src/backend/core/auth.py")], pr=5, owner=OWNER.replace("EVAL-WAIVE:ROW-ONE:ask-first", "x"))
    assert ("ask-first", "src/backend/core/auth.py") in levels(f, "FAIL")
    # the waiver is for the weaken pass, not this one
    f = run("fix(x): thing (ROW-ONE)", [("M", "src/backend/core/auth.py")], pr=5, owner=OWNER.replace(":ask-first", ":weaken"))
    assert ("ask-first", "src/backend/core/auth.py") in levels(f, "FAIL")


def test_hc_slg_004_non_test_source_outside_licence_fails():
    f = run("fix(x): thing (ROW-ONE)", [("M", "src/backend/api/widgets.py"), ("M", "src/backend/api/other.py")])
    assert levels(f, "FAIL") == [("outside-licence", "src/backend/api/other.py")]
    assert levels(f, "WARN") == []


def test_hc_slg_005_non_batch_pr_needs_a_queue_id():
    f = run("fix(x): thing with no id", [("M", "src/backend/api/widgets.py")])
    assert [x.code for x in f if x.level == "FAIL"] == ["no-queue-id"]
    f = run("fix(x): thing (NOT-A-ROW)", [("M", "src/backend/api/widgets.py")])
    assert [x.code for x in f if x.level == "FAIL"] == ["no-queue-id"]
    # whole-id match: UI-PG alone does not pick up UI-PG-ASK's files, and the reverse
    f = run("feat(ui): x (UI-PG-ASK)", [("M", "src/frontend/src/pg.tsx")])
    assert levels(f, "FAIL") == [("outside-licence", "src/frontend/src/pg.tsx")]


def test_hc_slg_006_batch_pr_may_touch_only_markdown():
    f = run("docs: batch (BATCH-1112X)", [("M", "docs/a.md"), ("M", "docs/INDEX.md"), ("M", "docs/_link_graph.json")])
    assert levels(f, "FAIL") == []
    f = run("docs: batch (BATCH-1112X)", [("M", "docs/a.md"), ("M", "scripts/x.py"), ("A", "src/x.json")])
    assert levels(f, "FAIL") == [("batch-non-md", "scripts/x.py"), ("batch-non-md", "src/x.json")]
    # a BATCH id needs no queue row
    assert not [x for x in f if x.code == "no-queue-id"]


def test_hc_slg_007_tests_new_allowed_existing_warn():
    new = ("A", "src/backend/tests/test_brand_new.py")
    old = ("M", "src/backend/tests/test_other_existing.py")
    f = run("fix(x): thing (ROW-ONE)", [new, old, ("D", "src/frontend/e2e/gone.spec.ts")])
    assert levels(f, "FAIL") == []
    assert levels(f, "WARN") == [
        ("test-outside-licence", "src/backend/tests/test_other_existing.py"),
        ("test-outside-licence", "src/frontend/e2e/gone.spec.ts"),
    ]
    # an existing test inside the licence is fine
    f = run("fix(x): thing (ROW-ONE)", [("M", "src/backend/tests/test_widgets.py")])
    assert f == []


def test_hc_slg_008_over_broad_token_warns():
    f = run("fix(x): thing (ROW-BROAD)", [("M", "src/backend/api/anything.py")])
    assert levels(f, "FAIL") == []
    assert [x.code for x in f if x.level == "WARN"] == ["over-broad-token"]
    f = run("fix(x): thing (ROW-ONE)", [("M", "src/backend/api/widgets.py")])
    assert f == []


def test_hc_slg_009_token_expansion_and_matching():
    ex = gate.expand
    assert ex("be/api/widgets.py:40-80") == ["src/backend/api/widgets.py"]
    assert ex("fe/src/a.tsx:1,5") == ["src/frontend/src/a.tsx"]
    assert ex("fe/pages/A.tsx") == ["src/frontend/src/pages/A.tsx"]  # the queue's short form
    assert ex("fe/e2e/a.spec.ts") == ["src/frontend/e2e/a.spec.ts"]
    assert ex("e2e/x.spec.ts") == ["src/frontend/e2e/x.spec.ts"]
    assert sorted(ex("be/modules/{alpha,beta}.py")) == ["src/backend/modules/alpha.py", "src/backend/modules/beta.py"]
    assert sorted(ex("a/{b,c}/{d,e}.py")) == ["a/b/d.py", "a/b/e.py", "a/c/d.py", "a/c/e.py"]
    m = gate.matches
    assert m("src/backend/api/widgets.py", "src/backend/api/widgets.py")
    assert m("src/backend/api/widgets.py", "src/backend/api/")  # dir prefix
    assert m("src/backend/api/widgets.py", "src/backend/api")  # dir prefix, no slash
    assert m("src/backend/api/widgets.py", "widgets.py")  # basename
    assert m("src/backend/api/widgets.py", "widgets")  # stem
    assert not m("src/backend/api/widgets_extra.py", "widgets")
    assert not m("src/backend/api/widgets.py", "src/backend/ap")
    assert m("docs/x/RUNBOOK.md", "docs/*/RUNBOOK.md")  # glob
    # through a whole row
    f = run("fix(x): t (ROW-BRACE)", [("M", "src/backend/modules/beta.py"), ("M", "src/backend/api/z.py"),
                                         ("M", "src/frontend/e2e/widgets.spec.ts"), ("M", "scripts/tool_stem.py")])
    assert levels(f, "FAIL") == []


def test_hc_slg_009b_parse_keeps_header_cell_map():
    rows = {r["i"]: r for r in qd.parse(QUEUE)}
    r = rows["ROW-ASK"]
    assert r["c"]["ask-first"] == "`modules/redaction.py`"
    assert r["c"]["files"] == "`be/modules/redaction.py`"
    # old keys unchanged
    assert (r["l"], r["k"], r["t"]) == ("B", "PRODUCT", "**READY**")


def test_hc_slg_010_plan_section_alias_map_and_union():
    # tokens from the linked section only
    f = run("fix(x): t (ROW-PLAN)", [("M", "src/backend/modules/delta.py"), ("M", "src/backend/modules/not_licensed_here.py")])
    assert levels(f, "FAIL") == [("outside-licence", "src/backend/modules/not_licensed_here.py")]
    # alias map: "the RUNBOOK" and "the builder brief"
    f = run("fix(x): t (ROW-PLAN)", [("M", "docs/plans/2026-01-01-build-program/RUNBOOK.md"), ("M", ".claude/workflows/build-item.js")])
    assert levels(f, "FAIL") == []
    # union over every ID in the title
    f = run("fix(x): t (ROW-ONE, ROW-PLAN-EXTRA)", [("M", "src/backend/api/widgets.py"), ("M", "src/backend/modules/gamma.py")])
    assert levels(f, "FAIL") == []
    # a "**Not** `x`" sentence excludes those files from the licence; the short fe/ form expands
    f = run("fix(x): t (ROW-NOT)", [("M", "src/backend/api/yes.py"), ("M", "src/frontend/src/pages/Yes.tsx"), ("M", "src/backend/api/no.py")])
    assert levels(f, "FAIL") == [("outside-licence", "src/backend/api/no.py")]
    # index files are always licensed
    f = run("fix(x): t (ROW-ONE)", [("M", "docs/INDEX.md"), ("M", "docs/_link_graph.json")])
    assert f == []


def _rsi_ask_first_regexes():
    js = (REPO_ROOT / ".claude" / "workflows" / "rsi-loop.js").read_text(encoding="utf-8")
    block = js.split("const DENY = [", 1)[1].split("\n]", 1)[0]
    pairs = re.findall(r"\[/(.+)/[a-z]*, '([^']+)'\]", block)
    return [(re.compile(rx.replace("\\/", "/")), why) for rx, why in pairs if why == "ask-first"]


def test_hc_slg_011_owner_list_is_a_superset_of_rsi_loop_ask_first():
    rsi = _rsi_ask_first_regexes()
    assert len(rsi) >= 6, "could not read the DENY list from rsi-loop.js"
    owner_paths = [p for p, _ in gate.ASK_FIRST_SAMPLES]
    # every rsi pattern that can match a real file is matched by the owner list; the ones that match
    # nothing are the known diff, reported here rather than fixed (rsi-loop.js is not this row's file)
    matches_nothing = [rx.pattern for rx, _ in rsi if not any(rx.search(p) for p in owner_paths)]
    print("rsi-loop ask-first patterns matching no owner-list path:", matches_nothing)
    assert matches_nothing == [r"(^|/)security/encryption"]
    # and the reverse: each rsi-matched owner path is a gate FAIL path, and the owner list is strictly larger
    rsi_hit = {p for p in owner_paths if any(rx.search(p) for rx, _ in rsi)}
    assert {p for p, lvl in gate.ASK_FIRST_SAMPLES if lvl == "FAIL"} > rsi_hit
    for p in rsi_hit:
        assert gate.ask_first_level(p) == "FAIL", p
    assert {gate.ask_first_level(p) for p in owner_paths} == {"FAIL", "WARN"}


def test_hc_slg_012_build_queue_still_classifies_docs_only():
    listed = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files", "--", QUEUE_GLOB],
                            capture_output=True, text=True, check=True).stdout.split()
    assert len(listed) == 1, listed
    out = subprocess.run([sys.executable, str(SCRIPTS / "change_scope.py"), "--repo-root", str(REPO_ROOT)],
                         input=listed[0] + "\n", capture_output=True, text=True, check=True).stdout.split()
    assert out == ["docs_only=true", "backend=false", "frontend=false", "mods=false"], out
    # and nothing the gate or its tests add names the queue file (HC-SCOPE-015 for the new files)
    base = listed[0].rsplit("/", 1)[-1]
    for f in (SCRIPTS / "pr_licence_gate.py", Path(__file__), *FIX.iterdir()):
        text = f.read_text(encoding="utf-8")
        assert listed[0] not in text and f'"{base}"' not in text and f"'{base}'" not in text, f.name


def _git(cwd, *args, env=None):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True, env=env)


def _make_repo(tmp_path):
    repo = tmp_path / "r"
    (repo / "docs" / "plans" / "2026-01-01-build-program").mkdir(parents=True)
    (repo / "docs" / "capstone-report").mkdir(parents=True)
    (repo / "src" / "backend" / "api").mkdir(parents=True)
    (repo / "docs" / "plans" / "2026-01-01-build-program" / ("queue" + ".md")).write_text(QUEUE, encoding="utf-8")
    (repo / "docs" / "plans" / "2026-01-01-build-program" / "fixture_plan.md").write_text(PLAN, encoding="utf-8")
    (repo / "docs" / "capstone-report" / "owner-decisions-2026-01-01.md").write_text(OWNER, encoding="utf-8")
    (repo / "src" / "backend" / "api" / "widgets.py").write_text("a = 1\n", encoding="utf-8")
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base", env=env)
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "checkout", "-q", "-b", "pr")
    return repo, env


def _run_cli(repo, title, extra_env=None):
    env = dict(os.environ, PR_TITLE=title, PR_NUMBER="5")
    env.pop("LICENCE_GATE_MODE", None)
    env.update(extra_env or {})
    return subprocess.run([sys.executable, str(SCRIPTS / "pr_licence_gate.py"), "--repo-root", str(repo),
                           "--base", "origin/main", "--head", "HEAD"],
                          capture_output=True, text=True, env=env)


def test_hc_slg_013_cli_end_to_end_in_a_throwaway_repo(tmp_path):
    repo, env = _make_repo(tmp_path)
    (repo / "src" / "backend" / "api" / "widgets.py").write_text("a = 2\n", encoding="utf-8")
    (repo / "src" / "backend" / "api" / "rogue.py").write_text("b = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "pr", env=env)
    bad = _run_cli(repo, "fix(x): t (ROW-ONE)")
    assert bad.returncode == 1, bad.stdout + bad.stderr
    assert "FAIL" in bad.stdout and "src/backend/api/rogue.py" in bad.stdout
    assert "src/backend/api/widgets.py" not in bad.stdout.split("FAIL", 1)[1]
    warn = _run_cli(repo, "fix(x): t (ROW-ONE)", {"LICENCE_GATE_MODE": "warn"})
    assert warn.returncode == 0, warn.stdout
    assert "downgraded" in warn.stdout
    ok = _run_cli(repo, "fix(x): t (ROW-ONE)")  # rogue.py is outside the licence even for ROW-ONE
    assert ok.returncode == 1
    # the queue is read from the live ref, not the PR head: a row added only in the PR does not count
    (repo / "docs" / "plans" / "2026-01-01-build-program" / ("queue" + ".md")).write_text(
        QUEUE + "| NEW-ROW | B | P | none | none | — | `be/api/rogue.py` | 1 | claude | **READY** |\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "pr2", env=env)
    still = _run_cli(repo, "fix(x): t (NEW-ROW)")
    assert still.returncode == 1 and "no-queue-id" in still.stdout
