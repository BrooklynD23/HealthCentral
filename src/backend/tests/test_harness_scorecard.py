"""HC-HSC-001..007: recording-only harness scorecard (AGENTIC-EVAL-SCORECARD).

The script is loaded by path and driven by a fake gh runner that replays synthetic JSON shaped like the
real gh output (tests/fixtures/harness_scorecard/gh_fixture.json). What this cannot see: whether the live
GitHub GraphQL/REST shapes drift from the fixture, or whether a real concurrency cancel looks like the
synthetic one. The acceptance run against live gh covers that once; nothing here re-checks it.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "harness_scorecard" / "gh_fixture.json").read_text())

_spec = importlib.util.spec_from_file_location("harness_scorecard", REPO_ROOT / "scripts" / "harness_scorecard.py")
hs = importlib.util.module_from_spec(_spec)
sys.modules["harness_scorecard"] = hs
_spec.loader.exec_module(hs)


def fake_runner(args):
    if args[:2] == ["pr", "list"]:
        return FIXTURE["pr_list"]
    if args[:2] == ["api", "graphql"]:
        num = next(a.split("=", 1)[1] for a in args if a.startswith("number="))
        return {"data": {"repository": {"pullRequest": FIXTURE["graphql"][num]}}}
    if args[0] == "run":
        return FIXTURE["runs"][args[args.index("--branch") + 1]]
    if args[0] == "api" and "commits" in args[1]:
        return FIXTURE["main_commits"]
    raise AssertionError(f"unexpected gh call {args}")


LEDGER = [
    {"pr": 102, "class": "path-assumption", "commit": "c102b", "mode": None},
    {"pr": 105, "class": "stale-generated-index", "mode": 8},
]


def collect():
    return hs.collect(fake_runner, hs.parse_ts("2026-11-05"), hs.parse_ts("2026-11-12"), LEDGER)


def by_pr(records):
    return {r["number"]: r for r in records}


def test_hc_hsc_001_first_ci_attempt_classification():
    r = by_pr(collect())
    assert r[101]["first_ci"] == "green"
    assert r[102]["first_ci"] == "not_green"      # first completed run failed
    assert r[103]["first_ci"] == "superseded"     # only run on the first head was concurrency-cancelled
    assert r[104]["first_ci"] == "not_green"      # run_attempt 2 is a re-run, not a first attempt
    assert r[105]["first_ci"] == "no_ci"
    # all runs on the first head cancelled (concurrency) -> superseded, not red
    runs = [
        {"headSha": "x1", "conclusion": "cancelled", "status": "completed", "createdAt": "2026-11-08T08:00:00Z", "attempt": 1},
        {"headSha": "x2", "conclusion": "failure", "status": "completed", "createdAt": "2026-11-08T09:00:00Z", "attempt": 1},
    ]
    assert hs.classify_first_ci(runs) == "superseded"
    assert hs.classify_first_ci([]) == "no_ci"


def test_hc_hsc_002_pushes_after_open_is_distinct_heads_union_force_pushes():
    r = by_pr(collect())
    assert r[101]["pushes"] == 0
    assert r[102]["pushes"] == 2                  # 3 distinct heads -> 2 pushes after open
    # 103: heads s103a, s103b from CI; force-push event names s103b again -> union, not double counted
    assert r[103]["pushes"] == 1
    runs = [{"headSha": "a", "createdAt": "1"}, {"headSha": "a", "createdAt": "2"}]
    assert hs.count_pushes(runs, ["a"]) == 0
    assert hs.count_pushes(runs, ["a", "b"]) == 1  # force push to a head CI never saw still counts


def test_hc_hsc_003_corrections_from_trailer_and_ledger_with_labelled_heuristic():
    r = by_pr(collect())
    # 102: two trailer commits (case-insensitive key) + ledger entry whose commit is already a trailer -> 2, not 3
    assert r[102]["corrections"] == 2
    assert sorted(r[102]["correction_classes"]) == ["path-assumption", "stale-index"]
    assert r[105]["corrections"] == 1             # ledger-only entry counts
    assert r[101]["corrections"] == 0
    # builder commit has no trailer: the Sonnet-authored commit is never counted
    assert hs.parse_trailers([{"commit": {"oid": "z", "messageBody": "Co-Authored-By: Claude Sonnet 5.5 <n@x>"}}]) == []
    # heuristic: commits whose Co-Authored-By family differs from the first commit's
    assert r[102]["cosign_heuristic"] == 1
    assert r[101]["cosign_heuristic"] == 0
    text = hs.render(collect(), hs.parse_ts("2026-11-05"), hs.parse_ts("2026-11-12"), [])
    assert "heuristic" in text.lower()


def test_hc_hsc_004_blocked_or_escalated_retitles_only():
    r = by_pr(collect())
    assert r[102]["retitles"] == 1                # [blocked:claude]; the final plain retitle is not counted
    assert r[103]["retitles"] == 1                # [escalated:claude]
    assert r[101]["retitles"] == 0


def test_hc_hsc_005_reverted_by_later_main_commit_excluding_in_pr_reverts():
    r = by_pr(collect())
    assert r[104]["reverted"] is True             # later main commit reverts merge sha m104
    assert r[105]["reverted"] is False            # revert of c105a lives inside PR 105's own commits
    assert r[101]["reverted"] is False


def test_hc_hsc_006_weekly_table_has_n_window_command_and_small_n_label():
    recs = collect()
    since, until = hs.parse_ts("2026-11-05"), hs.parse_ts("2026-11-12")
    text = hs.render(recs, since, until, ["gh pr list ..."])
    assert "| Week |" in text and "small n" in text
    week_lines = [ln for ln in text.splitlines() if ln.startswith("| 2026-W")]
    assert len(week_lines) == 2                   # PRs 101,102 in W45; 103,104,105 in W46
    assert all("2026-11-" in ln and "gh pr list" in ln for ln in week_lines)
    # 10 or more PRs in a week: no small-n label on that row
    many = [dict(recs[0], number=1000 + i) for i in range(10)]
    big = hs.render(many, since, until, ["gh pr list ..."])
    row = next(ln for ln in big.splitlines() if ln.startswith("| 2026-W"))
    assert "small n" not in row


def test_hc_hsc_007_metadata_only_and_empty_evidence_column(tmp_path):
    recs = collect()
    text = hs.render(recs, hs.parse_ts("2026-11-05"), hs.parse_ts("2026-11-12"), [])
    for secret in ("SECRET-TITLE-TEXT", "SECRET-BODY-TEXT", "fix after report", "noreply@anthropic.com"):
        assert secret not in text
    # live gh reports timelineItems.totalCount for all event types even when filtered (101 mimics it): no warning
    assert "WARNING" not in text
    header = next(ln for ln in text.splitlines() if ln.startswith("| PR |"))
    cells = [c.strip() for c in header.strip("|").split("|")]
    ev = cells.index("Evidence")
    rows = [ln for ln in text.splitlines() if ln.startswith("| #")]
    assert len(rows) == 5                         # #106 merged outside the window
    for ln in rows:
        assert [c.strip() for c in ln.strip("|").split("|")][ev] == ""
    # end to end through main(): writes the file, uses only the injected runner, reads the ledger file
    ledger = tmp_path / "l.jsonl"
    ledger.write_text("\n".join(json.dumps(x) for x in LEDGER) + "\n")
    out = tmp_path / "sc.md"
    rc = hs.main(["--since", "2026-11-05", "--until", "2026-11-12", "--out", str(out), "--ledger", str(ledger)], runner=fake_runner)
    assert rc == 0 and out.read_text().count("| #") >= 5
    with pytest.raises(SystemExit):
        hs.main(["--since", "2026-11-05"], runner=fake_runner)
