"""WF-NIGHTLY-GATES: scripts/gate_miss_rate.py aggregates a Playwright JSON report."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).parent / "fixtures" / "playwright_repeat_report.json"


def _load():
    spec = importlib.util.spec_from_file_location("gate_miss_rate", ROOT / "scripts" / "gate_miss_rate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_hc_nightly_001_counts_failures_and_runs_per_test():
    rows = {r["title"]: r for r in _load().aggregate(json.loads(FIXTURE.read_text()))}
    flaky = rows["UI gate G3 > G3 meds route paints under bound"]
    assert (flaky["failures"], flaky["runs"]) == (2, 4)
    clean = rows["UI gate G3 > G3 never misses"]
    assert (clean["failures"], clean["runs"]) == (0, 2)  # skipped is not a run


def test_hc_nightly_002_markdown_table_has_rate_and_exit_is_zero_on_misses(tmp_path, capsys):
    mod = _load()
    out = tmp_path / "summary.md"
    code = mod.main([str(FIXTURE), "--out", str(out)])
    text = out.read_text()
    assert code == 0  # recording policy: a miss never fails the nightly
    assert "| 2 / 4 | 50.0% |" in text
    assert "| 0 / 2 | 0.0% |" in text


def test_hc_nightly_003_missing_report_is_reported_not_crashed(tmp_path):
    out = tmp_path / "s.md"
    assert _load().main([str(tmp_path / "nope.json"), "--out", str(out)]) == 0
    assert "no report" in out.read_text().lower()
