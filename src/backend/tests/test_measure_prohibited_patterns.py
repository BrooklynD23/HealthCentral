"""B-3: `measure_prohibited_patterns.py --judge` (HC-PMJ-001..008).

Plan: docs/plans/2026-10-15-build-program/lane-B-interpretation-eval.md §B-3,
"--judge CLI contract". The script is a recorded measurement, not a gate, but
its contract is testable without a model: synthetic S5-shaped items are
generated in tmp_path (never a real S5 file) and `core.model_runner.get_model_runner`
is monkeypatched to a fake runner.

Exit codes: 0 OK; 2 usage / --tier low / path inside the repo; 3 bad schema or
counts below 180/200; 4 runner unavailable, no GGUF path, or the low-tier file.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND = Path(__file__).resolve().parent.parent
SCRIPT = BACKEND / "scripts" / "measure_prohibited_patterns.py"


def _script():
    spec = importlib.util.spec_from_file_location("measure_prohibited_patterns_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tier() -> str:
    from modules.model_selector import TIER_MODEL_CONFIG

    return next(k for k in TIER_MODEL_CONFIG if k != "low")


class _FakeRunner:
    """Answers BLOCK when the prompt holds BLOCKME, else ALLOW. Counts every call."""

    def __init__(self, gguf: Path | None, available: bool = True):
        self._gguf = gguf
        self._available = available
        self.calls = 0

    def _find_model_path(self):
        return self._gguf

    def is_available(self) -> bool:
        return self._available

    async def generate_async(self, prompt, config):
        self.calls += 1
        verdict = "BLOCK" if "BLOCKME" in prompt else "ALLOW"
        return SimpleNamespace(text=verdict, finish_reason="stop")


def _items(n_block: int = 180, n_allow: int = 200) -> list[dict]:
    """Half the must-block items trip the regex floor, half only the fake judge.
    Ten must-allow items are blocked by the fake judge (added false positives)."""
    rows = []
    for i in range(n_block):
        text = (f"You should take 20 mg of drug{i} daily." if i % 2 == 0
                else f"BLOCKME paraphrased advice number {i}.")
        rows.append({"id": f"b{i}", "label": "must_block", "category": "dosing", "text": text})
    for i in range(n_allow):
        text = f"Your LDL is {i} mg/dL." if i >= 10 else f"BLOCKME but harmless {i}."
        rows.append({"id": f"a{i}", "label": "must_allow", "category": None, "text": text})
    return rows


def _write(path: Path, rows: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def env(tmp_path, monkeypatch):
    gguf = tmp_path / "gemma-4-e4b-it-Q4_K_M.gguf"
    gguf.write_bytes(b"fake-gguf-bytes")
    runner = _FakeRunner(gguf)
    monkeypatch.setattr("core.model_runner.get_model_runner", lambda: runner)
    return SimpleNamespace(tmp=tmp_path, runner=runner, gguf=gguf, mod=_script())


def _run(env, monkeypatch, argv: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["measure_prohibited_patterns.py", *argv])
    try:
        return env.mod.main()
    except SystemExit as exc:  # argparse errors
        return exc.code


def _s5(env, rows=None) -> Path:
    return _write(env.tmp / "s5.jsonl", rows if rows is not None else _items())


def test_hc_pmj_001_judge_flag_is_accepted(env, monkeypatch, capsys):
    rc = _run(env, monkeypatch, ["--judge", str(_s5(env)), "--tier", _tier()])
    assert rc == 0, capsys.readouterr()
    assert env.runner.calls > 0


def test_hc_pmj_002_counts_below_180_and_200_exit_3(env, monkeypatch):
    short_block = _s5(env, _items(n_block=179))
    assert _run(env, monkeypatch, ["--judge", str(short_block), "--tier", _tier()]) == 3
    short_allow = _s5(env, _items(n_allow=199))
    assert _run(env, monkeypatch, ["--judge", str(short_allow), "--tier", _tier()]) == 3
    assert env.runner.calls == 0, "the model ran on an invalid S5"


def test_hc_pmj_003_bad_schema_or_duplicate_id_exits_3(env, monkeypatch):
    good = _items()
    bad_variants = {
        "missing text": [{k: v for k, v in good[0].items() if k != "text"}, *good[1:]],
        "unknown label": [{**good[0], "label": "maybe"}, *good[1:]],
        "duplicate id": [good[0], {**good[1], "id": good[0]["id"]}, *good[2:]],
        "non-string text": [{**good[0], "text": 7}, *good[1:]],
    }
    for name, rows in bad_variants.items():
        path = _s5(env, rows)
        assert _run(env, monkeypatch, ["--judge", str(path), "--tier", _tier()]) == 3, name
    broken = env.tmp / "broken.jsonl"
    broken.write_text('{"id": "x"\n', encoding="utf-8")
    assert _run(env, monkeypatch, ["--judge", str(broken), "--tier", _tier()]) == 3
    assert env.runner.calls == 0


def test_hc_pmj_004_tier_low_is_a_usage_error(env, monkeypatch, capsys):
    rc = _run(env, monkeypatch, ["--judge", str(_s5(env)), "--tier", "low"])
    assert rc == 2
    assert "low tier" in capsys.readouterr().err
    assert _run(env, monkeypatch, ["--judge", str(_s5(env))]) == 2, "--tier is required"
    assert env.runner.calls == 0


def test_hc_pmj_005_two_passes_and_metric_table(env, monkeypatch, capsys):
    rc = _run(env, monkeypatch, ["--judge", str(_s5(env)), "--tier", _tier()])
    out = capsys.readouterr().out
    assert rc == 0
    assert env.runner.calls == 2 * 380, "two full passes over every item"
    for line in (
        "system_recall: 1.000 (180/180)",          # 90 floor + 90 judge
        "judge_added_recall: 0.500 (90/180)",      # the 90 the floor missed
        "added_false_positives: 10",               # BLOCKME must-allow items
        "unavailable_rate: 0.000",
        "two_pass_agreement: 1.000",
        "latency_p50_s:", "latency_p95_s:", "concurrency: 2",
    ):
        assert line in out, (line, out)


def test_hc_pmj_006_output_records_hashes_commit_and_tier(env, monkeypatch, capsys):
    s5 = _s5(env)
    tier = _tier()
    assert _run(env, monkeypatch, ["--judge", str(s5), "--tier", tier]) == 0
    out = capsys.readouterr().out
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=BACKEND, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert f"tier: {tier}" in out
    assert f"gguf_sha256: {hashlib.sha256(env.gguf.read_bytes()).hexdigest()}" in out
    assert f"s5_sha256: {hashlib.sha256(s5.read_bytes()).hexdigest()}" in out
    assert "s5_counts: must_block=180 must_allow=200" in out
    assert f"commit: {head}" in out


def test_hc_pmj_007_low_tier_or_missing_gguf_exits_4(env, monkeypatch, tmp_path):
    from modules.model_selector import TIER_MODEL_CONFIG

    s5 = _s5(env)
    argv = ["--judge", str(s5), "--tier", _tier()]
    low = tmp_path / TIER_MODEL_CONFIG["low"]["filename"]
    low.write_bytes(b"x")
    for runner in (_FakeRunner(low), _FakeRunner(None), _FakeRunner(env.gguf, available=False)):
        monkeypatch.setattr("core.model_runner.get_model_runner", lambda r=runner: r)
        assert _run(env, monkeypatch, argv) == 4
        assert runner.calls == 0, "the judge ran on a runner that must be refused"


def test_hc_pmj_008_s5_path_inside_the_repo_exits_2(env, monkeypatch, capsys):
    toplevel = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=BACKEND, capture_output=True, text=True,
        check=True,
    ).stdout.strip()
    inside = Path(toplevel) / "s5-must-not-live-here.jsonl"
    rc = _run(env, monkeypatch, ["--judge", str(inside), "--tier", _tier()])
    assert rc == 2
    assert "inside the git" in capsys.readouterr().err
    assert env.runner.calls == 0
