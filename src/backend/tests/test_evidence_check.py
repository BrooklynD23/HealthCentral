"""HC-EVH-001..007: PR-body evidence claims versus CI (AGENTIC-EVAL-EVIDENCE, recording only).

scripts/evidence_check.py is pure (text in, dicts out); it is loaded by path. The scorecard wiring is driven by
fake gh runners replaying synthetic JSON. Bodies and logs under tests/fixtures/evidence_check/ are synthetic.
What this cannot see: whether real CI log lines or real PR bodies carry shapes the synthetic ones lack; the one
live scorecard run in the PR body is the only check of that.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
FIX = Path(__file__).parent / "fixtures" / "evidence_check"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ev = _load("evidence_check")
hs = _load("harness_scorecard")
BODY = (FIX / "pr_body_full.md").read_text()
BACKEND_LOG = (FIX / "ci_backend_log.txt").read_text()
FRONTEND_LOG = (FIX / "ci_frontend_log.txt").read_text()
CHECKS = {"Backend Tests": "SUCCESS", "Frontend Tests": "SUCCESS", "Security Scan": "SUCCESS"}


def ci_data():
    return {
        "backend": ev.parse_pytest_summary(BACKEND_LOG),
        "frontend": ev.parse_vitest_summary(FRONTEND_LOG),
        "checks": dict(CHECKS),
    }


def find(claims, kind, n=None, scope=None):
    hit = [c for c in claims if c["kind"] == kind and (n is None or c.get("n") == n) and (scope is None or c["scope"] == scope)]
    assert len(hit) == 1, (kind, n, scope, claims)
    return hit[0]


def test_hc_evh_001_ansi_stripped_claims_parsed_and_scope_tagged():
    assert ev.strip_ansi("\x1b[32m12 passed\x1b[0m in 1s") == "12 passed in 1s"
    claims = ev.parse_claims(BODY)
    assert find(claims, "passed", 12)["scope"] == "local-focused"       # command names one test file
    assert find(claims, "passed", 5164)["scope"] == "local-full"        # pytest tests/ with no file or -k
    assert find(claims, "skipped", 3)["scope"] == "local-full"
    assert find(claims, "collected", 5167)["scope"] == "local-full"
    assert find(claims, "passed", 5170)["scope"] == "ci-quoted"
    v = find(claims, "vitest", 412)
    assert v["total"] == 412 and v["scope"] == "local-full"
    assert find(claims, "vitest", 5)["scope"] == "local-focused"        # vitest run <file>
    assert find(claims, "ci_success")["scope"] == "ci-quoted"
    assert find(claims, "red") and find(claims, "green")
    # warnings are not a claim kind; "Tests passed locally somehow" carries no number so no claim
    assert not [c for c in claims if c.get("n") == 1732]
    assert len([c for c in claims if c["kind"] == "passed"]) == 3        # RED block's "3 failed" is dropped, not a claim
    assert not [c for c in claims if c["kind"] == "failed"]
    # a bare count with no command or keyword context is unknown
    assert ev.parse_claims("we got 7 passed overall")[0]["scope"] == "unknown"
    # a CI word far from the count does not make it CI's; PR refs and ratios are not counts
    far = ev.parse_claims("Backend GREEN: `64 passed, 9 skipped` (-rs); the lane runs under CI later on, see the notes below it")
    assert [c["scope"] for c in far] == ["unknown", "unknown"]
    assert not ev.parse_claims("see #621 failed earlier; 10/10 failed in the span")
    assert ev.parse_claims("5164 passed in CI Backend Tests")[0]["scope"] == "ci-quoted"
    # claims carry no body text
    assert all(set(c) <= {"kind", "n", "total", "scope", "target", "checks", "line"} for c in claims)


def test_hc_evh_002_ci_summary_parsed_and_comparable_claims_match_or_mismatch():
    s = ev.parse_pytest_summary(BACKEND_LOG)
    assert s["passed"] == 5164 and s["skipped"] == 3
    assert ev.parse_pytest_summary("no summary here\n") is None
    assert ev.parse_vitest_summary(FRONTEND_LOG) == {"passed": 412, "total": 412}
    res = ev.compare(ev.parse_claims(BODY), ci_data())
    by = {(r["kind"], r.get("n")): r["status"] for r in res}
    assert by[("passed", 5164)] == "match"
    assert by[("skipped", 3)] == "match"
    assert by[("collected", 5167)] == "match"                           # 5164 + 3 skipped, no collected line in CI -q
    assert by[("vitest", 412)] == "match"
    assert by[("passed", 5170)] == "mismatch"                           # CI-quoted claim differs from the CI line
    # collected sums every outcome kind, including xfailed, xpassed and errors
    ci = {"backend": {"passed": 10, "failed": 1, "skipped": 2, "xfailed": 3, "xpassed": 4, "errors": 5}, "checks": {}}
    r = ev.compare([{"kind": "collected", "n": 25, "scope": "local-full"}], ci)
    assert r[0]["status"] == "match"
    r = ev.compare([{"kind": "collected", "n": 24, "scope": "local-full"}], ci)
    assert r[0]["status"] == "mismatch"
    # vitest total differing is a mismatch
    r = ev.compare([{"kind": "vitest", "n": 412, "total": 413, "scope": "local-full"}], ci_data())
    assert r[0]["status"] == "mismatch"
    # no CI data for the head: not comparable, not a mismatch
    r = ev.compare([{"kind": "passed", "n": 5, "scope": "ci-quoted"}], {"backend": None, "checks": {}})
    assert r[0]["status"] == "no-ci-data"


def test_hc_evh_003_red_unverifiable_focused_and_unknown_never_compared():
    res = ev.compare(ev.parse_claims(BODY), ci_data())
    by = {(r["kind"], r.get("n")): r["status"] for r in res}
    assert by[("red", None)] == "unverifiable"
    assert by[("green", None)] == "non-comparable"                      # focused GREEN
    assert by[("passed", 12)] == "non-comparable"
    assert by[("vitest", 5)] == "non-comparable"
    unknown = ev.compare([{"kind": "passed", "n": 7, "scope": "unknown"}], ci_data())
    assert unknown[0]["status"] == "non-comparable"
    summary = ev.summarize(res)
    assert summary["n"] == len(res) == 10
    assert summary["comparable"] == 6 and summary["match"] == 5 and summary["mismatch"] == 1
    assert summary["unverifiable"] == 1 and summary["non_comparable"] == 3
    assert summary["comparable"] == summary["match"] + summary["mismatch"]
    assert summary["comparable_ci_quoted"] == 2 and summary["mismatch_ci_quoted"] == 1   # 5170 passed (mismatch), CI SUCCESS
    assert ev.evidence_cell(summary, stale=False, head_source="final") == "6 comparable, 5 match, 1 mismatch (n=10)"
    assert "stale body" in ev.evidence_cell(summary, stale=True, head_source="final")
    assert "stamped head" in ev.evidence_cell(summary, stale=False, head_source="stamped")
    assert ev.evidence_cell(ev.summarize([]), stale=False, head_source="final") == "no claims (n=0)"


def test_hc_evh_004_ci_green_claim_vs_check_conclusions():
    claim = [{"kind": "ci_success", "scope": "ci-quoted", "checks": []}]
    ok = {"checks": {"Backend Tests": "SUCCESS", "Docs": "SKIPPED"}}
    assert ev.compare(claim, ok)[0]["status"] == "match"
    bad = {"checks": {"Backend Tests": "SUCCESS", "Frontend Tests": "FAILURE"}}
    assert ev.compare(claim, bad)[0]["status"] == "mismatch"
    pending = {"checks": {"Backend Tests": "SUCCESS", "Frontend Tests": None}}
    assert ev.compare(claim, pending)[0]["status"] == "no-ci-data"
    assert ev.compare(claim, {"checks": {}})[0]["status"] == "no-ci-data"
    # a claim that names one check is judged on that check alone
    named = ev.parse_claims("Backend Tests SUCCESS on the head")
    assert named[0]["kind"] == "ci_success" and named[0]["checks"] == ["Backend Tests"]
    assert ev.compare(named, bad)[0]["status"] == "match"
    named_f = ev.parse_claims("Frontend Tests SUCCESS on the head")
    assert ev.compare(named_f, bad)[0]["status"] == "mismatch"


def test_hc_evh_005_stale_body_and_stamped_head():
    assert ev.is_stale("2026-11-12T10:00:00Z", "2026-11-12T10:05:00Z") is True    # edited before the last push
    assert ev.is_stale("2026-11-12T10:05:00Z", "2026-11-12T10:00:00Z") is False
    assert ev.is_stale("2026-11-12T10:00:00Z", None) is False
    assert ev.is_stale(None, "2026-11-12T10:00:00Z") is False
    assert ev.stamped_head(BODY) == "abc1234def"
    assert ev.stamped_head("no stamp") is None
    assert ev.stamped_head("Evidence head: not-a-sha") is None
    assert ev.choose_head(BODY, "f" * 40) == ("abc1234def", "stamped")
    assert ev.choose_head("nothing", "f" * 40) == ("f" * 40, "final")
    assert ev.same_sha("abc1234def", "abc1234def" + "0" * 30)
    assert not ev.same_sha("abc1234def", "bbb1234def")


def _evidence_runners(head="a1b2c3d4e5f6"):
    """Fake gh for the evidence stage only: PR graphql, run list, run view, job logs."""
    calls = []

    def runner(args):
        calls.append(args)
        if args[:2] == ["api", "graphql"]:
            return {"data": {"repository": {"pullRequest": {
                "body": BODY.replace("abc1234def", head),
                "createdAt": "2026-11-05T08:00:00Z",
                "lastEditedAt": "2026-11-05T09:00:00Z",
                "headRefOid": head,
                "commits": {"nodes": [{"commit": {"oid": head, "committedDate": "2026-11-05T08:30:00Z"}}]},
            }}}}
        if args[0] == "run" and args[1] == "list":
            return [{"databaseId": 77, "headSha": head, "conclusion": "success", "status": "completed",
                     "createdAt": "2026-11-05T08:31:00Z"}]
        if args[:2] == ["run", "view"]:
            return {"jobs": [
                {"name": "Backend Tests", "conclusion": "success", "status": "completed", "databaseId": 501},
                {"name": "Frontend Tests", "conclusion": "success", "status": "completed", "databaseId": 502},
            ]}
        raise AssertionError(f"unexpected gh call {args}")

    def text(args):
        calls.append(args)
        return BACKEND_LOG if args[-1].endswith("/501/logs") else FRONTEND_LOG

    return runner, text, calls


def _rec(number=101, branch="feat/a"):
    return {"number": number, "branch": branch, "merged": "2026-11-06T09:00:00Z", "first_ci": "green", "pushes": 0,
            "corrections": 0, "correction_classes": [], "cosign_heuristic": 0, "retitles": 0, "reverted": False,
            "truncated": False, "no_detail": False}


def test_hc_evh_006_scorecard_evidence_column_filled_with_counts_only():
    rec = _rec()
    runner, text, calls = _evidence_runners()
    hs.collect_evidence([rec], runner, text)
    e = rec["evidence"]
    assert e["comparable"] == 6 and e["match"] == 5 and e["mismatch"] == 1 and e["n"] == 10
    assert e["stale"] is False and e["head_source"] == "stamped"
    assert any(a[:2] == ["run", "view"] for a in calls)
    text_out = hs.render([rec], hs.parse_ts("2026-11-05"), hs.parse_ts("2026-11-12"), [])
    row = next(ln for ln in text_out.splitlines() if ln.startswith("| #101"))
    assert "6 comparable, 5 match, 1 mismatch (n=10)" in row
    assert "Evidence:" in text_out and "5164" not in text_out and "pyslot" not in text_out   # metadata only
    # a stale body is flagged
    stale_rec = _rec()

    def stale_runner(args):
        d = runner(args)
        if args[:2] == ["api", "graphql"]:
            d["data"]["repository"]["pullRequest"]["lastEditedAt"] = "2026-11-05T08:00:00Z"
        return d

    hs.collect_evidence([stale_rec], stale_runner, text)
    assert stale_rec["evidence"]["stale"] is True
    # a PR whose CI cannot be found keeps its claims but reports no CI data, never a false mismatch
    none_rec = _rec()

    def no_runs(args):
        return [] if args[:2] == ["run", "list"] else runner(args)

    hs.collect_evidence([none_rec], no_runs, text)
    assert none_rec["evidence"]["mismatch"] == 0 and none_rec["evidence"]["no_ci_data"] > 0
    # existing behaviour: no evidence key renders an empty cell (HC-HSC-007 keeps this)
    plain = hs.render([_rec(9)], hs.parse_ts("2026-11-05"), hs.parse_ts("2026-11-12"), [])
    assert next(ln for ln in plain.splitlines() if ln.startswith("| #9")).endswith("|  |")


def test_hc_evh_007_build_item_stamps_evidence_head_and_script_stays_pure():
    js = (REPO_ROOT / ".claude" / "workflows" / "build-item.js").read_text(encoding="utf-8")
    assert "Evidence head:" in js
    assert "git rev-parse HEAD" in js[js.index("Evidence head:") - 400: js.index("Evidence head:") + 400]
    src = (REPO_ROOT / "scripts" / "evidence_check.py").read_text(encoding="utf-8")
    imported = {n.names[0].name.split(".")[0] for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Import)}
    imported |= {n.module.split(".")[0] for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom)}
    assert imported <= {"re", "datetime", "__future__"}                 # no subprocess, no network, no files
    # change_scope trap: no new script or test may name the build queue file
    queue = "queue" + ".md"
    for p in (REPO_ROOT / "scripts" / "evidence_check.py", Path(__file__)):
        assert queue not in p.read_text(encoding="utf-8"), p
