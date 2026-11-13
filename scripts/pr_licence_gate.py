#!/usr/bin/env python3
"""PR scope-versus-licence gate (AGENTIC-EVAL-LICENCE). Stdlib only; a CI and dev tool, not product code.

Question it answers: did this PR touch only the files its queue row licenses, and did it avoid the
ask-first files unless the owner said so? It reads the build queue and the owner-decisions record from a
live ref (default origin/main), never from the PR head, so a PR cannot license itself.

    pr_licence_gate.py [--title T] [--pr N] [--base HEAD^1] [--head HEAD] [--ref origin/main] [--repo-root DIR]
    pr_licence_gate.py --backtest N [--ref origin/main]        # last N merged non-BATCH PRs, needs gh

The title and PR number come from PR_TITLE and PR_NUMBER when the flags are absent (CI passes them by
env, never by `${{ }}` inside a run block). LICENCE_GATE_MODE=warn downgrades every FAIL to a WARN
(printed as "downgraded") and exits 0; the default is fail (exit 1 on any FAIL).

Verdicts, per changed path (added, modified or deleted between --base and --head):
    FAIL ask-first          path is an ask-first file and no owner-decisions row names the queue ID or
                            #PR together with the file, and no EVAL-WAIVE:<ID>:ask-first is recorded.
                            (api/profiles.py is a WARN. The gate's own script, test and fixtures are
                            ask-first too: owner 1e.)
    FAIL outside-licence    non-test file that no licence token covers.
    FAIL no-queue-id        non-BATCH title that names no queue row id.
    FAIL batch-non-md       BATCH title and a changed file that is not .md (docs/INDEX.md and
                            docs/_link_graph.json excepted).
    WARN test-outside-licence  existing test file (modified or deleted) outside the licence. New test
                            files are allowed.
    WARN over-broad-token   a matching licence token is a directory of fewer than three segments, or a
                            leading wildcard.

Licence, per queue row id found in the title (union over all ids): backtick tokens from the row's
`files` and `ask-first` cells, plus backtick tokens from the plan section the row links (a
`file.md#anchor` link in any cell, resolved against the queue's folder), plus the alias map below, plus
docs/INDEX.md, docs/_link_graph.json and docs/agentic/recurring-failures.md (CLAUDE.md records a new recurrence in the same commit). A token is expanded (be/ -> src/backend/, fe/ -> src/frontend/,
e2e/ -> src/frontend/e2e/, {a,b} braces, a :line suffix dropped) and matches a path by exact path, directory
prefix, trailing path, basename, stem (name without its extension) or glob.

The queue and owner-decisions files are found by glob (git ls-tree), never named here: a docs file named
by a tracked script stops being docs-only for scripts/change_scope.py (HC-SLG-012 guards this).
"""

from __future__ import annotations

import fnmatch
import json
import os
import posixpath
import re
import subprocess
import sys
from typing import Callable, NamedTuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from queue_drift import parse  # noqa: E402  one queue parser, no second one

QUEUE_GLOB = "docs/plans/*build-program/" + "queue" + ".md"
OWNER_GLOB = "docs/capstone-report/owner-decisions-*.md"

# Owner list (CLAUDE.md section 1 plus the owner's 2026-11-12 additions). Level FAIL or WARN.
ASK_FIRST: tuple[tuple[re.Pattern, str], ...] = tuple(
    (re.compile(rx), level)
    for rx, level in (
        (r"(^|/)modules/interpret_safety\.py$", "FAIL"),
        (r"(^|/)modules/redaction\.py$", "FAIL"),
        (r"(^|/)modules/faithfulness\.py$", "FAIL"),
        (r"(^|/)modules/verifier_agent\.py$", "FAIL"),
        (r"(^|/)core/auth\.py$", "FAIL"),
        (r"(^|/)core/security\.py$", "FAIL"),
        (r"(^|/)core/document_crypto\.py$", "FAIL"),
        (r"(^|/)core/profile_database\.py$", "FAIL"),
        (r"(^|/)api/profiles\.py$", "WARN"),
        # the gate itself (owner 1e): later rows that edit it need an owner row of their own
        (r"^scripts/pr_licence_gate\.py$", "FAIL"),
        (r"^src/backend/tests/test_pr_licence_gate\.py$", "FAIL"),
        (r"^src/backend/tests/fixtures/agentic_eval/", "FAIL"),
    )
)
# One concrete path per pattern, for the parity test against rsi-loop.js (HC-SLG-011).
ASK_FIRST_SAMPLES = tuple(
    (p, "WARN" if p.endswith("api/profiles.py") else "FAIL")
    for p in (
        "src/backend/modules/interpret_safety.py",
        "src/backend/modules/redaction.py",
        "src/backend/modules/faithfulness.py",
        "src/backend/modules/verifier_agent.py",
        "src/backend/core/auth.py",
        "src/backend/core/security.py",
        "src/backend/core/document_crypto.py",
        "src/backend/core/profile_database.py",
        "src/backend/api/profiles.py",
        "scripts/pr_licence_gate.py",
        "src/backend/tests/test_pr_licence_gate.py",
        "src/backend/tests/fixtures/agentic_eval/fixture_queue.md",
    )
)

ALWAYS_LICENSED = ("docs/INDEX.md", "docs/_link_graph.json", "docs/agentic/recurring-failures.md")
# Prose phrases in a files cell that name a file without backticks.
ALIASES = (
    ("the runbook", "docs/plans/*build-program/RUNBOOK.md"),
    ("the builder brief", ".claude/workflows/build-item.js"),
)
# The queue writes fe/pages/X.tsx for src/frontend/src/pages/X.tsx, and fe/src/... or fe/e2e/... in full.
PREFIXES = (("be/", "src/backend/"), ("fe/src/", "src/frontend/src/"), ("fe/e2e/", "src/frontend/e2e/"),
            ("fe/", "src/frontend/src/"), ("e2e/", "src/frontend/e2e/"))
TEST_RE = re.compile(r"(^|/)(tests?|__tests__|e2e)/|\.(test|spec)\.[A-Za-z0-9]+$|(^|/)test_[^/]*\.py$|(^|/)conftest\.py$")
NOT_RE = re.compile(r"\*\*Not\*\*.*?(?:\.(?=\s)|;|$)")  # "**Not** `x.ts`, `y.ts`." names files the row excludes
BATCH_RE = re.compile(r"(?<![A-Z0-9-])BATCH-[A-Z0-9-]+")


class Finding(NamedTuple):
    level: str  # FAIL or WARN
    code: str
    path: str
    msg: str


def ask_first_level(path: str) -> str | None:
    for rx, level in ASK_FIRST:
        if rx.search(path):
            return level
    return None


def _braces(token: str) -> list[str]:
    m = re.search(r"\{([^{}]*)\}", token)
    if not m:
        return [token]
    out: list[str] = []
    for alt in m.group(1).split(","):
        out += _braces(token[: m.start()] + alt.strip() + token[m.end():])
    return out


def expand(token: str) -> list[str]:
    token = re.sub(r":\d+(?:[-,]\d+)*$", "", token.strip())
    out = []
    for t in _braces(token):
        for short, full in PREFIXES:
            if t.startswith(short):
                t = full + t[len(short):]
                break
        out.append(t)
    return out


def _stem(name: str) -> str:
    return name.rsplit(".", 1)[0] if "." in name.lstrip(".") else name


def matches(path: str, token: str) -> bool:
    if not token:
        return False
    if any(ch in token for ch in "*?"):
        return fnmatch.fnmatchcase(path, token) or fnmatch.fnmatchcase(path.rsplit("/", 1)[-1], token)
    if path == token:
        return True
    base = path.rsplit("/", 1)[-1]
    if "/" not in token:
        return base == token or _stem(base) == token
    t = token.rstrip("/")
    if path.startswith(t + "/") or path.endswith("/" + t) or ("/" + path).find("/" + t + "/") >= 0:
        return True
    return path.rsplit(".", 1)[0] == t


def over_broad(token: str) -> bool:
    if token.startswith(("*", "?", "**")):
        return True
    if "*" in token or "?" in token:
        return False
    is_dir = token.endswith("/") or not re.search(r"\.[A-Za-z0-9]+$", token.rsplit("/", 1)[-1])
    return "/" in token and is_dir and len([s for s in token.split("/") if s]) < 3


def _backticks(text: str) -> list[str]:
    return [t.strip() for t in re.findall(r"`([^`\n]+)`", text) if " " not in t.strip()]


def _section(text: str, anchor: str) -> str:
    """The markdown section whose GitHub slug is `anchor` (up to the next heading of the same or a higher level)."""
    lines = text.splitlines()
    start, level = None, 0
    for n, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if not m:
            continue
        slug = re.sub(r"[^a-z0-9 _-]", "", m.group(2).lower().replace("`", "")).replace(" ", "-")
        if start is None:
            if slug == anchor:
                start, level = n, len(m.group(1))
        elif len(m.group(1)) <= level:
            return "\n".join(lines[start:n])
    return "\n".join(lines[start:]) if start is not None else ""


def _title_ids(title: str, ids: set[str]) -> list[str]:
    found: list[str] = []
    rest = title
    for i in sorted(ids, key=len, reverse=True):
        rx = re.compile(rf"(?<![A-Z0-9-]){re.escape(i)}(?![A-Z0-9-])")
        if rx.search(rest):
            found.append(i)
            rest = rx.sub(" ", rest)
    return found


def licence_tokens(row: dict, queue_path: str, read_file: Callable[[str], str | None]) -> list[str]:
    cells = row["c"]
    tokens: list[str] = []
    for name in ("files", "ask-first"):
        tokens += _backticks(NOT_RE.sub("", cells.get(name, "")))
    prose = (cells.get("files", "") + " " + cells.get("ask-first", "")).lower()
    for phrase, target in ALIASES:
        if phrase in prose:
            tokens.append(target)
    for cell in cells.values():
        for rel, anchor in re.findall(r"\]\(([^)#\s]+\.md)#([^)\s]+)\)", cell):
            text = read_file(posixpath.normpath(posixpath.join(posixpath.dirname(queue_path), rel)))
            if text:
                tokens += _backticks(_section(text, anchor))
    return tokens


def _owner_row_licenses(owner_text: str, ids: list[str], pr: int | None, path: str) -> bool:
    base = path.rsplit("/", 1)[-1]
    for line in owner_text.splitlines():
        if not line.startswith("|") or base not in line:
            continue
        if any(re.search(rf"(?<![A-Z0-9-]){re.escape(i)}(?![A-Z0-9-])", line) for i in ids):
            return True
        if pr is not None and re.search(rf"#{pr}(?!\d)", line):
            return True
    return False


def evaluate(
    title: str,
    pr: int | None,
    changes: list[tuple[str, str]],
    queue_text: str,
    queue_path: str,
    owner_text: str,
    read_file: Callable[[str], str | None],
) -> list[Finding]:
    """changes: (status, path) with status A, M or D. Pure: all inputs are passed in."""
    out: list[Finding] = []
    rows = {r["i"]: r for r in parse(queue_text)}
    ids = _title_ids(title, set(rows))
    is_batch = bool(BATCH_RE.search(title))

    # ask-first, then batch rule, then licence
    for status, path in changes:
        level = ask_first_level(path)
        if level and not _owner_row_licenses(owner_text, ids, pr, path) and not any(
            f"EVAL-WAIVE:{i}:ask-first" in owner_text for i in ids
        ):
            out.append(Finding(level, "ask-first", path, "ask-first file with no owner-decisions row naming the queue ID or #PR (or an EVAL-WAIVE)"))

    if is_batch:
        for status, path in changes:
            if not path.endswith(".md") and path not in ALWAYS_LICENSED:
                out.append(Finding("FAIL", "batch-non-md", path, "BATCH PRs may change only .md files"))
        return out
    if not ids:
        out.append(Finding("FAIL", "no-queue-id", "", "title names no queue row id and is not a BATCH PR"))
        return out

    tokens: list[str] = []
    for i in ids:
        for raw in licence_tokens(rows[i], queue_path, read_file):
            tokens += expand(raw)
    tokens += list(ALWAYS_LICENSED)
    broad_seen: set[str] = set()
    for status, path in changes:
        hit = [t for t in tokens if matches(path, t)]
        if hit:
            for t in hit:
                if over_broad(t) and t not in broad_seen:
                    broad_seen.add(t)
                    out.append(Finding("WARN", "over-broad-token", path, f"licence token `{t}` is over-broad"))
            continue
        if TEST_RE.search(path):
            if status != "A":
                out.append(Finding("WARN", "test-outside-licence", path, "existing test file changed outside the licence"))
            continue
        out.append(Finding("FAIL", "outside-licence", path, "non-test file outside the row licence"))
    return out


# ---- git plumbing -------------------------------------------------------------------------------

def _git(root: str, *args: str) -> str:
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, check=True).stdout


def _find(root: str, ref: str, glob: str) -> str | None:
    names = [n for n in _git(root, "ls-tree", "-r", "--name-only", ref).splitlines() if fnmatch.fnmatchcase(n, glob)]
    return sorted(names)[-1] if names else None


def _show(root: str, ref: str, path: str) -> str | None:
    try:
        return _git(root, "show", f"{ref}:{path}")
    except subprocess.CalledProcessError:
        return None


def load_live(root: str, ref: str) -> tuple[str, str, str]:
    q = _find(root, ref, QUEUE_GLOB)
    o = _find(root, ref, OWNER_GLOB)
    if not q:
        raise SystemExit(f"no build queue found at {ref}")
    return _show(root, ref, q) or "", q, (_show(root, ref, o) or "") if o else ""


def changed(root: str, base: str, head: str) -> list[tuple[str, str]]:
    out = []
    for line in _git(root, "diff", "--name-status", "--no-renames", base, head).splitlines():
        st, _, path = line.partition("\t")
        out.append((st[:1], path))
    return out


def report(findings: list[Finding], mode: str) -> int:
    downgraded = mode == "warn"
    for f in findings:
        level = "WARN" if (downgraded and f.level == "FAIL") else f.level
        note = " (downgraded from FAIL: LICENCE_GATE_MODE=warn)" if level != f.level else ""
        print(f"{level} {f.code} {f.path or '-'}: {f.msg}{note}")
    fails = [f for f in findings if f.level == "FAIL"]
    print(f"licence gate: {len(fails)} FAIL, {len([f for f in findings if f.level == 'WARN'])} WARN, mode={mode}")
    return 1 if fails and not downgraded else 0


def backtest(root: str, ref: str, n: int) -> int:
    q_text, q_path, owner = load_live(root, ref)
    listing = json.loads(subprocess.run(
        ["gh", "pr", "list", "--state", "merged", "--limit", str(max(300, n * 4)), "--json", "number,title"],
        capture_output=True, text=True, check=True, cwd=root).stdout)
    prs = [p for p in listing if not BATCH_RE.search(p["title"])][:n]
    read = lambda p: _show(root, ref, p)  # noqa: E731
    fails = 0
    print(f"{'PR':>5}  {'verdict':<7} title / findings")
    for p in prs:
        raw = subprocess.run(
            ["gh", "api", f"repos/{{owner}}/{{repo}}/pulls/{p['number']}/files", "--paginate", "--jq", r'.[]|[.status,.filename]|@tsv'],
            capture_output=True, text=True, check=True, cwd=root).stdout
        ch = [({"added": "A", "removed": "D"}.get(s, "M"), f) for s, _, f in (ln.partition("\t") for ln in raw.splitlines())]
        fs = evaluate(p["title"], p["number"], ch, q_text, q_path, owner, read)
        verdict = "FAIL" if any(f.level == "FAIL" for f in fs) else "WARN" if fs else "pass"
        fails += verdict == "FAIL"
        print(f"{p['number']:>5}  {verdict:<7} {p['title'][:90]}")
        for f in fs:
            print(f"{'':>14}{f.level} {f.code} {f.path or '-'}")
    print(f"backtest: {len(prs)} PRs, {fails} FAIL")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    def opt(name: str, default: str | None = None) -> str | None:
        return argv[argv.index(name) + 1] if name in argv else default

    root = opt("--repo-root", os.getcwd())
    ref = opt("--ref", "origin/main")
    if "--backtest" in argv:
        return backtest(root, ref, int(opt("--backtest")))
    title = opt("--title", os.environ.get("PR_TITLE", ""))
    pr_raw = opt("--pr", os.environ.get("PR_NUMBER", ""))
    pr = int(pr_raw) if pr_raw and pr_raw.isdigit() else None
    mode = os.environ.get("LICENCE_GATE_MODE", "fail")
    q_text, q_path, owner = load_live(root, ref)
    findings = evaluate(title, pr, changed(root, opt("--base", "HEAD^1"), opt("--head", "HEAD")),
                        q_text, q_path, owner, lambda p: _show(root, ref, p))
    return report(findings, mode)


if __name__ == "__main__":
    sys.exit(main())
