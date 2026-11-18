"""scripts/queue_drift.py: dashboard-versus-queue drift check (dev tool).

HC-QDR-001  table parsing: the status column is found by header, per table
HC-QDR-002  a table with no status column is skipped
HC-QDR-003  done / closed / superseded bucket
HC-QDR-004  "in flight" bucket
HC-QDR-005  owner bucket: kind, owner-section text, bundled, linux half
HC-QDR-006  blocked bucket, ahead of an open PR
HC-QDR-007  open PR title matches by whole id (UI-PG does not match UI-PG-ASK)
HC-QDR-008  ready bucket
HC-QDR-009  anything else falls back to blocked
HC-QDR-010  compare reports missing, extra and bucket changes
HC-QDR-011  main exits 0 with no drift and 1 with drift
HC-QDR-012  the queue path is required: no path is a usage error (2)
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "queue_drift.py"


def _load():
    spec = importlib.util.spec_from_file_location("queue_drift_under_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


qd = _load()


def _row(status, kind="", section="Rows", i="X-1"):
    return {"i": i, "l": "", "k": kind, "s": section, "t": status}


TWO_TABLES = """\
## Wave 1

| ID | Lane | Kind | Status |
|---|---|---|---|
| `A-1` | B | PRODUCT | **ready** |
| ~~A-2~~ | E | DOCS | done 2026-10-01 |

## Owner questions

| ID | Question | Status | Notes |
|---|---|---|---|
| **Q-1** | why | owner action pending | n/a |
"""


def test_hc_qdr_001_status_column_found_by_header_per_table():
    rows = qd.parse(TWO_TABLES)
    assert [(r["i"], r["t"], r["s"]) for r in rows] == [
        ("A-1", "**ready**", "Wave 1"),
        ("A-2", "done 2026-10-01", "Wave 1"),
        ("Q-1", "owner action pending", "Owner questions"),
    ]
    assert (rows[0]["l"], rows[0]["k"]) == ("B", "PRODUCT")
    assert (rows[2]["l"], rows[2]["k"]) == ("", "")  # no lane/kind columns in table 2


def test_hc_qdr_002_table_without_status_column_is_skipped():
    text = "## Notes\n\n| ID | Owner |\n|---|---|\n| N-1 | me |\n\n| ID | Status |\n|---|---|\n| N-2 | ready |\n"
    assert [r["i"] for r in qd.parse(text)] == ["N-2"]


def test_hc_qdr_003_done_closed_superseded():
    for t in ("done", "**done** 2026-10-01", "~~closed~~", "Closed (dup)", "**superseded** by X"):
        assert qd.bucket(_row(t), {}) == "done", t
    assert qd.bucket(_row("undone"), {}) != "done"


def test_hc_qdr_004_in_flight():
    assert qd.bucket(_row("in flight: #5"), {}) == "inflight"
    assert qd.bucket(_row("**in flight:** #5"), {}) == "inflight"


def test_hc_qdr_005_owner_rules():
    assert qd.bucket(_row("pending", kind="owner action"), {}) == "owner"
    owner_sec = "Owner or model-host work"
    assert qd.bucket(_row("owner action: sign", section=owner_sec), {}) == "owner"
    assert qd.bucket(_row("bar signed by owner", section=owner_sec), {}) == "owner"
    # the same text outside that section is not owner
    assert qd.bucket(_row("owner action: sign", section="Wave 1"), {}) == "blocked"
    assert qd.bucket(_row("**bundled** into #9"), {}) == "owner"
    assert qd.bucket(_row("linux half pending"), {}) == "owner"
    assert qd.bucket(_row("ready, bundled into #316"), {}) == "owner"


def test_hc_qdr_006_blocked_beats_open_pr():
    assert qd.bucket(_row("**blocked** on Z"), {}) == "blocked"
    assert qd.bucket(_row("blocked on Z"), {"X-1": 7}) == "blocked"


def test_hc_qdr_007_open_pr_matches_whole_id_only():
    prs = [{"number": 1, "title": "[claim:claude] UI-PG-ASK page"}, {"number": 2, "title": "UI-PG: shell"}]
    found = qd.match_open_prs({"UI-PG", "UI-PG-ASK"}, prs)
    assert found == {"UI-PG-ASK": 1, "UI-PG": 2}
    assert qd.match_open_prs({"UI-PG"}, [prs[0]]) == {}
    assert qd.match_open_prs({"UI"}, [prs[1]]) == {}
    assert qd.bucket(_row("waiting", i="UI-PG"), found) == "inflight"
    assert qd.bucket(_row("waiting", i="UI-OTHER"), found) == "blocked"


def test_hc_qdr_008_ready():
    for t in ("ready", "**ready** now", "task 1 ready", "Task 1 **ready**"):
        assert qd.bucket(_row(t), {}) == "ready", t


def test_hc_qdr_009_fallback_is_blocked():
    assert qd.bucket(_row("waiting on a thing"), {}) == "blocked"
    assert qd.bucket(_row(""), {}) == "blocked"


def _queue_rows():
    return [dict(_row("ready", i="A"), b="ready"), dict(_row("done", i="B"), b="done"), dict(_row("x", i="C"), b="blocked")]


def test_hc_qdr_010_compare_reports_each_kind_of_drift():
    data = [{"i": "A", "b": "inflight"}, {"i": "B", "b": "done"}, {"i": "Z", "b": "done"}]
    missing, extra, changed = qd.compare(_queue_rows(), data)
    assert missing == ["C"]
    assert extra == ["Z"]
    assert changed == [("A", "inflight", "ready")]
    assert qd.compare(_queue_rows(), [{"i": r["i"], "b": r["b"]} for r in _queue_rows()]) == ([], [], [])


def _run_main(tmp_path, monkeypatch, capsys, artifact_rows, extra_args=()):
    queue = "## W\n\n| ID | Status |\n|---|---|\n| A | ready |\n| B | done |\n"
    html = tmp_path / "dash.html"
    html.write_text("<script>\nconst DATA=" + json.dumps({"rows": artifact_rows}) + ";\n</script>\n")
    monkeypatch.setattr(qd, "read_queue", lambda ref, path: queue)
    monkeypatch.setattr(qd, "open_pr_list", lambda: (_ for _ in ()).throw(AssertionError("gh called")))
    code = qd.main([str(html), "origin/main", "q.md", "--no-prs", *extra_args])
    return code, capsys.readouterr().out


def test_hc_qdr_012_missing_queue_path_is_usage_error(capsys):
    assert qd.main(["dash.html", "origin/main"]) == 2
    assert qd.main(["dash.html", "origin/main", "--no-prs"]) == 2
    assert "usage" in capsys.readouterr().err


def test_hc_qdr_011_main_exit_codes(tmp_path, monkeypatch, capsys):
    same = [{"i": "A", "b": "ready"}, {"i": "B", "b": "done"}]
    code, out = _run_main(tmp_path, monkeypatch, capsys, same, ("--json", str(tmp_path / "o.json")))
    assert code == 0
    assert "bucket changes: 0" in out
    assert [r["b"] for r in json.loads((tmp_path / "o.json").read_text())] == ["ready", "done"]

    code, out = _run_main(tmp_path, monkeypatch, capsys, [{"i": "A", "b": "done"}, {"i": "B", "b": "done"}])
    assert code == 1
    assert "A" in out and "done" in out and "-> ready" in out

    code, out = _run_main(tmp_path, monkeypatch, capsys, [{"i": "A", "b": "ready"}])
    assert code == 1
    assert "missing from artifact: ['B']" in out

    code, out = _run_main(tmp_path, monkeypatch, capsys, same + [{"i": "Z", "b": "done"}])
    assert code == 1
    assert "only in artifact: ['Z']" in out
