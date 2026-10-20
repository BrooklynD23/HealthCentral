"""RSI-T2-EVAL: legacy RAG citation eval (Track-2 measurement for RSI-4).

Drives the real POST /assistant/chat legacy route over HTTP through
tests/legacy_eval/harness.py::legacy_chat_client (imported read-only), as the
MM-1 count script did: fixed synthetic chunks, retrieval faked, and the
external-runner lookup patched to the ModelRunner facade so the real local model
generates. Everything after the runner is product code (validate_response,
faithfulness, the G-B5 abstain mapping, SAFE-CHAT).

Run from src/backend on the model machine, with no pytest running:

    python scripts/legacy_cite_eval.py --models gemma4:e4b,llama3.1:8b \\
        --out-dir ~/asclexis-evals/t2e-<sha> [--baseline <json>] [--questions <json>] \\
        [--sealed] [--repeats 1]

One subprocess per model (core.config.settings reads LLM_PROVIDER/LLM_MODEL once
at import). Writes <out-dir>/legacy_cite_eval.json and .md. --sealed writes counts,
rates, the error histogram and the questions file's sha256 only, never question,
response or chunk text. Refuses to run inside pytest (exit 3). Exits 1 when any
question never reached the model (no_model) or the route failed (error).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True  # before any import that could write __pycache__

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

SCHEMA_VERSION = 1
DEFAULT_QUESTIONS = BACKEND / "tests" / "fixtures" / "legacy_cite_eval" / "questions_v1.json"
# Order matters: classify() applies the rules top to bottom.
KINDS = ("error", "no_model", "timeout", "escalated", "abstained", "answered_cited", "answered_uncited")
NO_MODEL_TEXT = "knowledge base only"
TIMEOUT_TEXT = "unable to fully process your question within the time limit"
REFUSE_MSG = "refusing to run a real-model eval inside pytest"
# [cite:N] plus D11 context labels the model echoes inline ([USER_OBSERVATION:3], [YOUR_RESULTS:2], [REFERENCE:1]).
_CITE_MARKER = re.compile(r"\[(?:cite|[A-Z][A-Z_]*):\d+\]")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


# --------------------------------------------------------------------------- fixture

def fixture_sha256(path: Path) -> str:
    """sha256 of the file with CRLF normalised to LF (a Windows checkout must match)."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_questions(path: Path) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc.get("questions"), list) or not isinstance(doc.get("chunks"), list):
        raise ValueError(f"{path}: needs 'questions' and 'chunks' lists")
    return doc


def build_chunks(doc: dict) -> list:
    from modules.rag import RetrievedChunk

    return [RetrievedChunk(**spec) for spec in doc["chunks"]]


# --------------------------------------------------------------------------- classify

def classify(body: dict, finish_reason: str | None = None, status_code: int = 200) -> str:
    """One kind per question (plan 'Metric definitions'; `error` and the
    finish_reason timeout signal are additions, see the PR body)."""
    from modules.agent.guardrails.templates import ABSTAIN_TEMPLATE, ESCALATE_TEMPLATE

    if status_code != 200:
        return "error"
    full = body.get("full_response") or ""
    if NO_MODEL_TEXT in full:
        return "no_model"
    # G-B5 maps the runner's timeout text to ABSTAIN_TEMPLATE, so the recorded
    # finish_reason is the signal that still sees a timeout.
    if TIMEOUT_TEXT in full or finish_reason == "timeout":
        return "timeout"
    if full == ESCALATE_TEMPLATE:
        return "escalated"
    if full == "**UNCERTAINTY**\n" + ABSTAIN_TEMPLATE:
        return "abstained"
    if any(seg.get("citations") for seg in body.get("segments") or []):
        return "answered_cited"
    return "answered_uncited"


def _numbers(text: str) -> set[float]:
    return {float(n) for n in _NUMBER.findall(_CITE_MARKER.sub("", text))}


def cite_value_mismatches(body: dict, chunk_text_by_doc: dict[str, str]) -> int:
    """Diagnostic only (never changes the kind): report_facts segments holding a
    number that appears in none of the chunks the segment cites."""
    bad = 0
    for seg in body.get("segments") or []:
        if seg.get("segment_type") != "report_facts" or not seg.get("citations"):
            continue
        cited: set[float] = set()
        for c in seg["citations"]:
            cited |= _numbers(chunk_text_by_doc.get(c.get("doc_id") or "", c.get("text_snippet") or ""))
        if _numbers(seg.get("content") or "") - cited:
            bad += 1
    return bad


# --------------------------------------------------------------------------- run

class _RecordingRunner:
    """Delegates to the runner the route would use and records finish_reason."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.finish_reasons: list[str | None] = []

    def is_available(self) -> bool:
        return self._inner.is_available()

    async def generate_async(self, prompt: str, config: object) -> Any:
        result = await self._inner.generate_async(prompt, config)
        self.finish_reasons.append(getattr(result, "finish_reason", None))
        return result


def _ask(question: str, chunks: list, runner: Any) -> tuple[int, dict, str | None, float]:
    from unittest.mock import AsyncMock, patch

    from tests.legacy_eval.harness import CHAT_PATH, legacy_chat_client

    recorder = _RecordingRunner(runner)
    with legacy_chat_client(chunks, "") as (client, _), patch(
        "core.external_runner.get_runner_for_request", AsyncMock(return_value=recorder)
    ):
        start = time.perf_counter()
        resp = client.post(CHAT_PATH, json={"question": question})
        latency_ms = (time.perf_counter() - start) * 1000.0
    try:
        body = resp.json()
    except ValueError:
        body = {}
    finish = recorder.finish_reasons[-1] if recorder.finish_reasons else None
    return resp.status_code, body, finish, latency_ms


def _real_runner() -> Any:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        raise RuntimeError(REFUSE_MSG)
    import core.model_runner as model_runner

    return model_runner.get_model_runner()


def run_questions(questions: list[str], chunks: list, runner_patch: Any = None) -> list[dict]:
    """Ask every question through the real route. runner_patch=None uses the
    ModelRunner facade (CLI only; refused inside pytest); tests pass a FakeRunner."""
    runner = _real_runner() if runner_patch is None else runner_patch
    text_by_doc = {c.doc_id: c.text for c in chunks if c.doc_id}
    out = []
    for q in questions:
        status, body, finish, latency_ms = _ask(q, chunks, runner)
        kind = classify(body, finish_reason=finish, status_code=status)
        out.append({
            "question": q,
            "kind": kind,
            "status_code": status,
            "finish_reason": finish,
            "validation_errors": list(body.get("validation_errors") or []),
            "latency_ms": round(latency_ms, 1),
            "cite_value_mismatch": cite_value_mismatches(body, text_by_doc) if kind == "answered_cited" else 0,
            "full_response": body.get("full_response", ""),
        })
    return out


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct / 100.0
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo), 1)


def summarise(per_question: list[dict], model: str) -> dict:
    n = len(per_question)
    counts = Counter(r["kind"] for r in per_question)
    errors: Counter = Counter()
    for r in per_question:
        errors.update(r.get("validation_errors") or [])
    latencies = [r["latency_ms"] for r in per_question if r.get("latency_ms") is not None]
    summary: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "model": model, "n": n}
    summary.update({kind: counts.get(kind, 0) for kind in KINDS})
    summary.update({
        "abstain_rate": counts.get("abstained", 0) / n if n else 0.0,
        "cited_answer_rate": counts.get("answered_cited", 0) / n if n else 0.0,
        "validation_errors": dict(errors),
        "latency_ms_p50": _percentile(latencies, 50),
        "latency_ms_p95": _percentile(latencies, 95),
        "cite_value_mismatch": sum(r.get("cite_value_mismatch", 0) for r in per_question),
    })
    return summary


def evaluate(questions_path: Path, model: str, *, sealed: bool = False, repeats: int = 1,
             runner_patch: Any = None) -> dict:
    """One model: an untimed warm-up (real model only), then `repeats` passes."""
    doc = load_questions(questions_path)
    chunks = build_chunks(doc)
    if runner_patch is None:
        run_questions(doc["questions"][:1], chunks)  # discarded: MM-1 lost Q1 to a cold load
    passes = [run_questions(doc["questions"], chunks, runner_patch) for _ in range(repeats)]
    pooled = [dict(r, repeat=i + 1) for i, p in enumerate(passes) for r in p]
    summary = summarise(pooled, model)
    summary["repeats"] = repeats
    if repeats > 1:
        per = [summarise(p, model) for p in passes]
        summary["abstain_rate_range"] = [min(s["abstain_rate"] for s in per), max(s["abstain_rate"] for s in per)]
        summary["cited_answer_rate_range"] = [min(s["cited_answer_rate"] for s in per),
                                              max(s["cited_answer_rate"] for s in per)]
    if not sealed:
        summary["per_question"] = pooled
    return summary


# --------------------------------------------------------------------------- report

def _cmd_output(cmd: list[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return out or "unknown"


def build_report(models: list[dict], questions_path: Path, *, sealed: bool = False) -> dict:
    from core.time import utcnow

    if sealed:
        models = [{k: v for k, v in m.items() if k != "per_question"} for m in models]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": utcnow().isoformat(timespec="seconds"),
        "git_sha": _cmd_output(["git", "-C", str(BACKEND), "rev-parse", "--short", "HEAD"]),
        "ollama_version": _cmd_output(["ollama", "--version"]),
        "questions_sha256": fixture_sha256(questions_path),
        "questions_sha256_note": "sha256 of the file with CRLF normalised to LF",
        "questions_file": "<sealed>" if sealed else Path(questions_path).name,
        "sealed": sealed,
        "models": models,
    }


def _fmt_delta(m: dict, base: dict | None, key: str) -> str:
    # Pooled counts only compare at the same n and repeats; otherwise no number.
    if base is None or base.get("n") != m["n"] or base.get("repeats", 1) != m.get("repeats", 1):
        return "—"
    return f"{m[key] - int(base.get(key, 0)):+d}"


def render_markdown(report: dict, baseline: dict | None = None) -> str:
    cols = ["model", "abstained", "cited", "uncited", "escalated", "timeout", "no-model",
            "abstain rate", "cited-answer rate", "cite-value mismatches"]
    if baseline is not None:
        cols += ["Δ abstain", "Δ cited"]
    base_by_model = {m["model"]: m for m in (baseline or {}).get("models", [])}
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for m in report.get("models", []):
        n = m["n"]
        row = [m["model"], f"{m['abstained']}/{n}", f"{m['answered_cited']}/{n}", f"{m['answered_uncited']}/{n}",
               f"{m['escalated']}/{n}", f"{m['timeout']}/{n}", f"{m['no_model']}/{n}",
               f"{m['abstain_rate']:.2f}", f"{m['cited_answer_rate']:.2f}", str(m["cite_value_mismatch"])]
        if baseline is not None:
            base = base_by_model.get(m["model"])
            row += [_fmt_delta(m, base, "abstained"), _fmt_delta(m, base, "answered_cited")]
        lines.append("| " + " | ".join(row) + " |")
    if report.get("questions_sha256"):
        repeats = ", ".join(f"{m['model']}={m.get('repeats', 1)}" for m in report.get("models", []))
        lines += ["", f"questions_sha256: `{report['questions_sha256']}`; repeats: {repeats}"]
    return "\n".join(lines) + "\n"


def write_outputs(out_dir: Path, report: dict, baseline: dict | None = None) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "legacy_cite_eval.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (out_dir / "legacy_cite_eval.md").write_text(render_markdown(report, baseline), encoding="utf-8")


def _result_line(m: dict) -> str:
    n = m["n"]
    return (f"RESULT {m['model']}: {m['abstained']}/{n} abstained, {m['answered_cited']}/{n} cited, "
            f"{m['answered_uncited']}/{n} uncited, {m['escalated']}/{n} escalated, {m['timeout']}/{n} timeout, "
            f"{m['no_model']}/{n} no-model, {m['error']}/{n} error; validation_errors={m['validation_errors']}")


# --------------------------------------------------------------------------- CLI

def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RSI-T2-EVAL legacy citation eval (model machine only)")
    p.add_argument("--models", help="comma-separated Ollama model ids")
    p.add_argument("--out-dir", type=Path, help="result directory (required; keep it outside the repo)")
    p.add_argument("--baseline", type=Path, help="an earlier legacy_cite_eval.json, for delta columns")
    p.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    p.add_argument("--sealed", action="store_true", help="write counts and the LF-normalised sha256 only, never text")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--one-model", help=argparse.SUPPRESS)
    p.add_argument("--json-out", type=Path, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    if args.repeats < 1:
        p.error("--repeats must be >= 1")
    if args.one_model is None and (not args.models or args.out_dir is None):
        p.error("--models and --out-dir are required")
    if args.one_model is not None and args.json_out is None:
        p.error("--one-model needs --json-out")
    return args


def _child(args: argparse.Namespace) -> int:
    if not _real_runner().is_available():
        print(f"NO LOCAL MODEL for {args.one_model}: check `ollama list` and LLM_MODEL.", file=sys.stderr)
        return 2
    summary = evaluate(args.questions, args.one_model, sealed=args.sealed, repeats=args.repeats)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(_result_line(summary), flush=True)
    return 1 if summary["no_model"] or summary["error"] else 0


def _parent(args: argparse.Namespace) -> int:
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    out_dir = args.out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    questions = args.questions.expanduser().resolve()
    summaries, worst = [], 0
    for model in models:
        json_out = out_dir / (re.sub(r"[^A-Za-z0-9._-]", "_", model) + ".json")
        cmd = [sys.executable, str(Path(__file__).resolve()), "--one-model", model, "--json-out", str(json_out),
               "--questions", str(questions), "--repeats", str(args.repeats)]
        if args.sealed:
            cmd.append("--sealed")
        env = dict(os.environ, LLM_PROVIDER="ollama", LLM_MODEL=model, TEST_MODE="1", HF_HUB_OFFLINE="1")
        print(f"== {model}", flush=True)
        rc = subprocess.run(cmd, cwd=str(BACKEND), env=env, check=False).returncode
        worst = max(worst, rc)
        if rc in (0, 1) and json_out.exists():
            summaries.append(json.loads(json_out.read_text(encoding="utf-8")))
        else:
            print(f"{model}: child exited {rc}; no result", file=sys.stderr)
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
    report = build_report(summaries, questions, sealed=args.sealed)
    write_outputs(out_dir, report, baseline)
    print(render_markdown(report, baseline))
    for m in summaries:
        print(_result_line(m))
    print(f"wrote {out_dir / 'legacy_cite_eval.json'} and {out_dir / 'legacy_cite_eval.md'}")
    return 1 if worst else 0


def main(argv: list[str] | None = None) -> int:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        print(REFUSE_MSG, file=sys.stderr)
        return 3
    args = _parse(argv)
    return _child(args) if args.one_model is not None else _parent(args)


if __name__ == "__main__":
    sys.exit(main())
