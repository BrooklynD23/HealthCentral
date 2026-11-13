"""PR-body evidence claims versus CI (AGENTIC-EVAL-EVIDENCE). Pure: text and dicts in, dicts out.

Imported by scripts/harness_scorecard.py, which does the gh calls. Recording only: nothing here gates a PR.
Only comparable claims are compared; everything else is labelled, never counted as a mismatch.

Scope tags per claim: local-focused (command names a test file, -k, or a sub-path), local-full (whole suite),
ci-quoted (the line says CI or Backend Tests), unknown. A command line ("$ ..." or one holding pytest/vitest)
sets the scope for the result lines in the next few lines. A bare "N tests collected" with no focus marker is
local-full: a collected count describes a collection, not a run.
"""
from __future__ import annotations

import re
from datetime import datetime

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
COUNT_RE = re.compile(r"(?<![#/\d])\b(\d+)\s+(passed|failed|skipped|xfailed|xpassed|errors?)\b")
COLLECTED_RE = re.compile(r"\b(\d+)\s+tests?\s+collected\b|\bcollected\s+(\d+)\s+(?:items?|tests?)?", re.I)
VITEST_RE = re.compile(r"^\W*Tests\s+(?:(\d+)\s+failed\s*\|\s*)?(\d+)\s+passed(?:\s*\|\s*\d+\s+\w+)*\s*\((\d+)\)")
VITEST_FILES_RE = re.compile(r"^\W*Test Files\b")
CI_OK_RE = re.compile(r"\bCI\b.{0,60}\b(SUCCESS|green)\b|\b(?:Backend|Frontend) Tests\b.{0,30}\bSUCCESS\b")
CHECK_NAMES = ("Backend Tests", "Frontend Tests", "Documentation Lint", "Agent Eval Gate", "Security Scan", "RSI Replay")
CI_QUOTE_RE = re.compile(r"\bCI\b|Backend Tests|Frontend Tests|GitHub Actions")
RED_RE = re.compile(r"^\W*RED\b")
GREEN_RE = re.compile(r"^\W*GREEN\b")
STAMP_RE = re.compile(r"^\s*Evidence head:\s*([0-9a-f]{7,40})\b", re.I | re.M)
SUMMARY_RE = re.compile(r"\b\d+\s+(?:passed|failed|skipped|xfailed|xpassed|errors?)\b.*\bin\s+\d+(?:\.\d+)?s\b")
OUTCOMES = ("passed", "failed", "skipped", "xfailed", "xpassed", "errors")
CONTEXT_LINES = 8
PYTEST_VALUE_FLAGS = {"-k", "-m", "-p", "-c", "-n", "--deselect", "--ignore", "--maxfail", "--cov", "--tb", "-o"}
FULL_PATHS = {"tests", "tests/", "src/backend/tests", "src/backend/tests/", ".", "./", "./tests", "./tests/"}


def strip_ansi(s):
    return ANSI_RE.sub("", s or "")


def _command_scope(line):
    """local-full / local-focused for a pytest or vitest command line, else None."""
    low = line
    for tool in ("pytest", "vitest"):
        i = low.find(tool)
        if i < 0:
            continue
        toks = re.split(r"[|;&]+", low[i + len(tool):])[0].split()
        args, skip = [], False
        for t in toks:
            if skip:
                skip = False
                continue
            if t in PYTEST_VALUE_FLAGS:
                if t == "-k" or t == "-m":
                    return "local-focused"
                skip = True
                continue
            if t.startswith("-"):
                continue
            args.append(t)
        if tool == "vitest":
            args = [a for a in args if a != "run"]
            return "local-focused" if args else "local-full"
        return "local-full" if all(a in FULL_PATHS for a in args) else "local-focused"
    return None


def _is_command(line):
    s = line.strip()
    return bool(re.search(r"\b(pytest|vitest)\b", s)) and (s.startswith("$") or "-m pytest" in s or "npx " in s or s.startswith("pytest"))


def _ci_near(line, m):
    """A CI / Backend Tests mention just before the count (60 chars) or just after it (25): the count is CI's."""
    return any(c.end() <= m.start() and m.start() - c.end() <= 60 or m.end() <= c.start() and c.start() - m.end() <= 25
               for c in CI_QUOTE_RE.finditer(line))


def parse_claims(body):
    """Claims in a PR body as dicts: kind, n, total (vitest), scope, target, checks, line (index). No text kept."""
    claims = []
    ctx_scope, ctx_age, red = None, 99, False
    for idx, raw in enumerate(strip_ansi(body).splitlines()):
        line = raw.strip()
        if line.startswith("#"):
            ctx_scope, red = None, False
        if _is_command(line):
            ctx_scope, ctx_age = _command_scope(line), 0
        else:
            ctx_age += 1
        ctx = ctx_scope if ctx_age <= CONTEXT_LINES else None
        if RED_RE.search(line):
            red = True
            claims.append({"kind": "red", "scope": ctx or "unknown", "line": idx})
            continue
        if GREEN_RE.search(line):
            red = False
            claims.append({"kind": "green", "scope": ctx or "unknown", "line": idx})
        scope = ctx
        if scope is None and re.search(r"full suite|full backend", line, re.I):
            scope = "local-full"
        if scope is None and re.search(r"focused", line, re.I):
            scope = "local-focused"
        if re.search(r"\.py\b|::|\s-k\s", line) and scope in (None, "local-full"):
            scope = "local-focused"
        target = "frontend" if re.search(r"frontend|vitest", line, re.I) else "backend"
        if VITEST_FILES_RE.search(line):
            continue
        m = VITEST_RE.search(line)
        if m:
            if not red:
                claims.append({"kind": "vitest", "n": int(m.group(2)), "total": int(m.group(3)),
                               "scope": scope or "unknown", "line": idx})
            continue
        if CI_OK_RE.search(line):
            claims.append({"kind": "ci_success", "scope": "ci-quoted", "line": idx,
                           "checks": [c for c in CHECK_NAMES if c in line]})
        if red:
            continue
        for m in COLLECTED_RE.finditer(line):
            n = int(m.group(1) or m.group(2))
            cscope = "ci-quoted" if _ci_near(line, m) else scope
            claims.append({"kind": "collected", "n": n, "scope": cscope or "local-full", "line": idx})
        for m in COUNT_RE.finditer(line):
            kind = "errors" if m.group(2).startswith("error") else m.group(2)
            cscope = "ci-quoted" if _ci_near(line, m) else scope
            claims.append({"kind": kind, "n": int(m.group(1)), "scope": cscope or "unknown", "target": target, "line": idx})
    for c in claims:
        c.setdefault("target", "backend")
    return claims


def parse_pytest_summary(log):
    """Counts from the last pytest summary line of a CI log (-q: no collected line), else None."""
    found = None
    for line in strip_ansi(log).splitlines():
        if SUMMARY_RE.search(line):
            found = line
    if found is None:
        return None
    out = {}
    for m in COUNT_RE.finditer(found):
        out["errors" if m.group(2).startswith("error") else m.group(2)] = int(m.group(1))
    return out


def parse_vitest_summary(log):
    """{"passed": n, "total": n} from the vitest `Tests` line of a CI log, else None."""
    found = None
    for line in strip_ansi(log).splitlines():
        m = VITEST_RE.search(re.sub(r"^\S+Z\s+", "", line))
        if m:
            found = {"passed": int(m.group(2)), "total": int(m.group(3))}
    return found


def _ok_conclusion(c):
    return c in ("SUCCESS", "SKIPPED", "NEUTRAL")


def _compare_one(c, ci):
    kind, scope = c["kind"], c["scope"]
    if kind == "red":
        return "unverifiable"
    if kind == "green" or scope not in ("local-full", "ci-quoted"):
        return "non-comparable"
    backend, frontend, checks = ci.get("backend"), ci.get("frontend"), ci.get("checks") or {}
    if kind == "ci_success":
        picked = {k: v for k, v in checks.items() if not c.get("checks") or k in c["checks"]}
        if not picked or any(v is None for v in picked.values()):
            return "no-ci-data"
        return "match" if all(_ok_conclusion(v) for v in picked.values()) else "mismatch"
    if kind == "vitest" or (kind == "passed" and c.get("target") == "frontend"):
        if kind == "passed" and not frontend:
            return "no-ci-data"
        if not frontend:
            return "no-ci-data"
        ok = c["n"] == frontend["passed"] and (kind != "vitest" or c["total"] == frontend["total"])
        return "match" if ok else "mismatch"
    if c.get("target") == "frontend":
        return "non-comparable"
    if backend is None:
        return "no-ci-data"
    if kind == "collected":
        return "match" if c["n"] == sum(backend.get(k, 0) for k in OUTCOMES) else "mismatch"
    return "match" if c["n"] == backend.get(kind, 0) else "mismatch"


def compare(claims, ci):
    """One result per claim: kind, n, scope, status in match|mismatch|non-comparable|unverifiable|no-ci-data."""
    ci = ci or {}
    return [{"kind": c["kind"], "n": c.get("n"), "scope": c["scope"], "status": _compare_one(c, ci)} for c in claims]


def summarize(results):
    count = {s: sum(r["status"] == s for r in results)
             for s in ("match", "mismatch", "unverifiable", "non-comparable", "no-ci-data")}
    return {"n": len(results), "comparable": count["match"] + count["mismatch"], "match": count["match"],
            "mismatch": count["mismatch"], "unverifiable": count["unverifiable"],
            "non_comparable": count["non-comparable"], "no_ci_data": count["no-ci-data"],
            "comparable_ci_quoted": sum(r["status"] in ("match", "mismatch") and r["scope"] == "ci-quoted" for r in results),
            "mismatch_ci_quoted": sum(r["status"] == "mismatch" and r["scope"] == "ci-quoted" for r in results)}


def _ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def is_stale(last_edited, last_push):
    """True when the body was last edited before the last push (the body can then describe an older head)."""
    if not last_edited or not last_push:
        return False
    return _ts(last_edited) < _ts(last_push)


def stamped_head(body):
    m = STAMP_RE.search(strip_ansi(body))
    return m.group(1).lower() if m else None


def choose_head(body, final_head):
    s = stamped_head(body)
    return (s, "stamped") if s else (final_head, "final")


def same_sha(a, b):
    a, b = (a or "").lower(), (b or "").lower()
    return bool(a and b) and min(len(a), len(b)) >= 7 and (a.startswith(b) or b.startswith(a))


def evidence_cell(summary, stale, head_source):
    if not summary["n"]:
        base = "no claims (n=0)"
    else:
        base = f"{summary['comparable']} comparable, {summary['match']} match, {summary['mismatch']} mismatch (n={summary['n']})"
    if stale:
        base += "; stale body"
    if head_source == "stamped":
        base += "; stamped head"
    return base
