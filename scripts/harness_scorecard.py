#!/usr/bin/env python3
"""Recording-only harness scorecard for Asclexis (stdlib + gh CLI). Read-only, never gates anything.

Usage: harness_scorecard.py --since 2026-11-05 --until 2026-11-12 [--out FILE] [--ledger FILE]

One row per PR merged into main inside [since, until): did the first CI attempt pass, how many pushes
after open, how many L0 corrections, blocked/escalated retitles, later revert. Then a weekly table.
Every number shows its n, its window and the command that produced it. Output is metadata only: PR
numbers, dates, counts, short class tokens. It never prints a PR title, PR body, commit message or diff.

L0 corrections come from two places (the ledger is the backfill for work before the trailer existed):
  1. commits carrying an `Asclexis-Correction: <class>` trailer (L0, or a subagent L0 sends, adds it to a
     fix commit made after the builder reports; the builder never adds it);
  2. ledger lines (JSON, one per line: pr, class, optional commit, optional mode) not already covered by a
     trailer commit.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from statistics import median

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_check as ev  # noqa: E402  (pure parser and comparer, AGENTIC-EVAL-EVIDENCE)

REPO = "BrooklynD23/HealthCentral"
DEFAULT_LEDGER = os.path.expanduser("~/hc-quiet-logs/perf-monitor/l0-corrections.jsonl")
SMALL_N = 10
CMDS = []
CALLS = 0

QUERY = (
    "query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){"
    "pullRequest(number:$number){commits(first:100){totalCount nodes{commit{oid messageBody}}} "
    "timelineItems(first:100,itemTypes:[RENAMED_TITLE_EVENT,HEAD_REF_FORCE_PUSHED_EVENT]){totalCount nodes{"
    "__typename ... on RenamedTitleEvent{currentTitle} ... on HeadRefForcePushedEvent{afterCommit{oid}}}}}}}"
)
EVIDENCE_QUERY = (
    "query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){"
    "pullRequest(number:$number){body createdAt lastEditedAt headRefOid commits(last:1){nodes{commit{oid committedDate}}}}}}"
)
TRAILER_RE = re.compile(r"^Asclexis-Correction:[ \t]*(\S+)", re.I | re.M)
COSIGN_RE = re.compile(r"^Co-Authored-By:[ \t]*Claude[ \t]+(\w+)", re.I | re.M)
REVERT_RE = re.compile(r"This reverts commit ([0-9a-z]{4,40})")


def parse_ts(s):
    s = s.strip()
    if len(s) == 10:
        s += "T00:00:00Z"
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def _json_stream(text):
    """gh api --paginate prints one JSON document per page, back to back. Flatten lists."""
    dec, i, items, n, was_list = json.JSONDecoder(), 0, [], len(text), False
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        obj, i = dec.raw_decode(text, i)
        was_list = was_list or isinstance(obj, list)
        items.extend(obj) if isinstance(obj, list) else items.append(obj)
    return items if was_list or len(items) != 1 else items[0]


def gh(args, raw=False):
    """Run gh with retry on rate limit. Returns parsed JSON (raw text when raw=True), or None on failure."""
    global CALLS
    cmd = ["gh"] + args
    if args[0] in ("run", "pr"):
        cmd += ["-R", REPO]
    CMDS.append(" ".join(cmd))
    for attempt in range(4):
        CALLS += 1
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0:
            time.sleep(0.3)
            if raw:
                return p.stdout
            return _json_stream(p.stdout) if p.stdout.strip() else None
        err = p.stderr.lower()
        if "rate limit" in err or "403" in err or "502" in err or "503" in err:
            time.sleep(20 * (attempt + 1))
            continue
        sys.stderr.write(f"gh failed: {' '.join(cmd[:4])}\n{p.stderr[:200]}\n")
        return None
    return None


def _clean(token):
    return re.sub(r"[^A-Za-z0-9_.:-]", "", token)[:40]


def classify_first_ci(runs):
    """First completed non-cancelled CI run on the first head after open.

    green = success and run_attempt 1; not_green = anything else completed (a later attempt means an earlier
    one did not finish green, inferred); superseded = every run on the first head was concurrency-cancelled;
    pending = nothing completed yet; no_ci = no run at all (docs-only PRs can skip CI jobs but still get a run).
    """
    if not runs:
        return "no_ci"
    runs = sorted(runs, key=lambda r: r["createdAt"])
    first_head = runs[0]["headSha"]
    on_head = [r for r in runs if r["headSha"] == first_head]
    live = [r for r in on_head if r.get("conclusion") != "cancelled"]
    if not live:
        return "superseded"
    done = [r for r in live if r.get("status") == "completed"]
    if not done:
        return "pending"
    r = done[0]
    return "green" if r.get("conclusion") == "success" and r.get("attempt", 1) == 1 else "not_green"


def count_pushes(runs, force_oids):
    heads = {r["headSha"] for r in runs} | set(force_oids)
    return max(0, len(heads) - 1)


def parse_trailers(commit_nodes):
    out = []
    for n in commit_nodes:
        c = n["commit"]
        m = TRAILER_RE.search(c.get("messageBody") or "")
        if m:
            out.append({"oid": c["oid"], "class": _clean(m.group(1))})
    return out


def cosign_heuristic(commit_nodes):
    """Commits co-signed by a different Claude model family than the first co-signed commit. A heuristic only."""
    fams = []
    for n in commit_nodes:
        m = COSIGN_RE.search(n["commit"].get("messageBody") or "")
        if m:
            fams.append(m.group(1).lower())
    return sum(1 for f in fams if f != fams[0]) if fams else 0


def count_retitles(timeline_nodes):
    return sum(
        1
        for n in timeline_nodes
        if n.get("__typename") == "RenamedTitleEvent"
        and (n.get("currentTitle") or "").startswith(("[blocked:", "[escalated:"))
    )


def _same_sha(a, b):
    return a == b or (min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)))


def is_reverted(merge_oid, pr_oids, main_commits):
    """A main commit that says "This reverts commit <merge or PR commit sha>", unless it is a PR's own commit."""
    targets = [t for t in [merge_oid, *pr_oids] if t]
    for c in main_commits:
        if c.get("sha") in pr_oids:
            continue  # in-PR revert
        for sha in REVERT_RE.findall(c.get("commit", {}).get("message") or ""):
            if any(_same_sha(sha, t) for t in targets):
                return True
    return False


def load_ledger(path):
    rows = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except FileNotFoundError:
        return None
    return rows


def collect(runner, since, until, ledger):
    prs = runner(["pr", "list", "--state", "merged", "--base", "main", "--search",
                  f"merged:{since:%Y-%m-%d}..{until:%Y-%m-%d}", "--json",
                  "number,headRefName,baseRefName,createdAt,mergedAt,mergeCommit", "--limit", "200"]) or []
    prs = [p for p in prs if since <= parse_ts(p["mergedAt"]) < until]
    prs.sort(key=lambda p: p["mergedAt"])
    main_commits = []
    if prs:
        main_commits = runner(["api", f"repos/{REPO}/commits?sha=main&since={prs[0]['mergedAt']}&per_page=100",
                               "--paginate"]) or []
    records = []
    for p in prs:
        d = runner(["api", "graphql", "-f", f"query={QUERY}", "-f", f"owner={REPO.split('/')[0]}",
                    "-f", f"name={REPO.split('/')[1]}", "-F", f"number={p['number']}"])
        pr = ((d or {}).get("data") or {}).get("repository", {}).get("pullRequest") or {}
        commits = (pr.get("commits") or {}).get("nodes") or []
        tl = (pr.get("timelineItems") or {}).get("nodes") or []
        lo, hi = parse_ts(p["createdAt"]) - timedelta(minutes=2), parse_ts(p["mergedAt"]) + timedelta(hours=1)
        runs = runner(["run", "list", "--workflow", "ci.yml", "--event", "pull_request", "--branch",
                       p["headRefName"], "--json", "databaseId,headSha,conclusion,status,createdAt,attempt",
                       "--limit", "100"]) or []
        runs = [r for r in runs if lo <= parse_ts(r["createdAt"]) <= hi]
        force = [n["afterCommit"]["oid"] for n in tl
                 if n.get("__typename") == "HeadRefForcePushedEvent" and n.get("afterCommit")]
        trailers = parse_trailers(commits)
        t_oids = {t["oid"] for t in trailers}
        extra = [e for e in ledger if e.get("pr") == p["number"] and e.get("commit") not in t_oids]
        pr_oids = {c["commit"]["oid"] for c in commits}
        records.append({
            "number": p["number"],
            "merged": p["mergedAt"],
            "first_ci": classify_first_ci(runs),
            "pushes": count_pushes(runs, force),
            "corrections": len(trailers) + len(extra),
            "correction_classes": [t["class"] for t in trailers] + [_clean(str(e.get("class", "?"))) for e in extra],
            "cosign_heuristic": cosign_heuristic(commits),
            "retitles": count_retitles(tl),
            "branch": p["headRefName"],
            "reverted": is_reverted((p.get("mergeCommit") or {}).get("oid"), pr_oids, main_commits),
            # timelineItems.totalCount counts every event type even when filtered (seen live), so use the page size
            "truncated": (pr.get("commits") or {}).get("totalCount", 0) > len(commits) or len(tl) >= 100,
            "no_detail": not pr,
        })
    return records


def gh_text(args):
    return gh(args, raw=True)


def _ci_for_head(runner, text_runner, branch, sha):
    """CI facts for one head: Backend/Frontend log summaries and check conclusions. Empty when no completed run."""
    ci = {"backend": None, "frontend": None, "checks": {}}
    runs = runner(["run", "list", "--workflow", "ci.yml", "--event", "pull_request", "--branch", branch, "--json",
                   "databaseId,headSha,conclusion,status,createdAt", "--limit", "100"]) or []
    done = [r for r in runs if ev.same_sha(r.get("headSha"), sha) and r.get("status") == "completed"
            and r.get("conclusion") != "cancelled"]
    if not done:
        return ci
    run = max(done, key=lambda r: r["createdAt"])
    jobs = ((runner(["run", "view", str(run["databaseId"]), "--json", "jobs"]) or {}).get("jobs")) or []
    for j in jobs:
        concl = (j.get("conclusion") or "").upper() or None
        ci["checks"][j["name"]] = concl
        if concl is None or j["name"] not in ("Backend Tests", "Frontend Tests"):
            continue
        log = text_runner(["api", f"repos/{REPO}/actions/jobs/{j['databaseId']}/logs"]) or ""
        if j["name"] == "Backend Tests":
            ci["backend"] = ev.parse_pytest_summary(log)
        else:
            ci["frontend"] = ev.parse_vitest_summary(log)
    return ci


def collect_evidence(records, runner, text_runner):
    """Add record["evidence"] (counts only) to each record. The body is read in memory and never stored or printed."""
    for r in records:
        d = runner(["api", "graphql", "-f", f"query={EVIDENCE_QUERY}", "-f", f"owner={REPO.split('/')[0]}",
                    "-f", f"name={REPO.split('/')[1]}", "-F", f"number={r['number']}"])
        v = ((d or {}).get("data") or {}).get("repository", {}).get("pullRequest")
        if not v:
            r["evidence"] = {"unavailable": True}
            continue
        sha, source = ev.choose_head(v.get("body") or "", v.get("headRefOid") or "")
        pushes = [n["commit"]["committedDate"] for n in (v.get("commits") or {}).get("nodes") or []
                  if n.get("commit", {}).get("committedDate")]
        stale = ev.is_stale(v.get("lastEditedAt") or v.get("createdAt"), max(pushes) if pushes else None)
        ci = _ci_for_head(runner, text_runner, r.get("branch", ""), sha)
        summary = ev.summarize(ev.compare(ev.parse_claims(v.get("body") or ""), ci))
        r["evidence"] = dict(summary, stale=stale, head_source=source)


def _evidence_cell(r):
    e = r.get("evidence")
    if not e:
        return ""
    if e.get("unavailable"):
        return "unavailable"
    return ev.evidence_cell(e, e["stale"], e["head_source"])


def _week(ts):
    y, w, _ = parse_ts(ts).isocalendar()
    return f"{y}-W{w:02d}"


def render(records, since, until, cmds, ledger_note=""):
    P = []
    a = P.append
    a(f"# Harness scorecard, window {since:%Y-%m-%d} to {until:%Y-%m-%d} (merged into main)\n")
    a(f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%MZ} by `scripts/harness_scorecard.py`. Recording only: "
      "nothing here gates a PR. Metadata only: no PR title, body, commit message or diff is printed.\n")
    a(f"n = {len(records)} PRs merged into main in the window (by `mergedAt`). " + (ledger_note or "") + "\n")
    a("Definitions: **first CI** = first completed non-cancelled `ci.yml` pull_request run on the first head after open, "
      "`green` only if it succeeded with run_attempt 1 (a later attempt is read as an earlier non-green one, inferred); "
      "`superseded` = every run on the first head was concurrency-cancelled. **Pushes** = distinct head SHAs seen in CI "
      "runs plus force-push events, minus the first head. **L0 corrections** = commits with an "
      "`Asclexis-Correction: <class>` trailer plus ledger lines not already covered by one. **Retitles** = RenamedTitleEvent "
      "whose new title starts `[blocked:` or `[escalated:`. **Reverted** = a later main commit says "
      "`This reverts commit <merge or PR commit sha>` (a revert inside the PR itself is excluded).\n")
    a("## Per PR\n")
    a("| PR | Merged | First CI | Pushes after open | L0 corrections | Correction classes | "
      "Heuristic (other-model co-signed commits, not a measurement) | Blocked/escalated retitles | Reverted | Evidence |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for r in sorted(records, key=lambda r: r["merged"]):
        a(f"| #{r['number']} | {r['merged'][:10]} | {r['first_ci']} | {r['pushes']} | {r['corrections']} | "
          f"{', '.join(r['correction_classes']) or '-'} | {r['cosign_heuristic']} | {r['retitles']} | "
          f"{'yes' if r['reverted'] else 'no'} | {_evidence_cell(r)} |")
    a("")
    evs = [r["evidence"] for r in records if r.get("evidence") and not r["evidence"].get("unavailable")]
    if any(r.get("evidence") for r in records):
        a(f"Evidence: {len(evs)} of {len(records)} PRs read ("
          f"{sum(e['n'] for e in evs)} claims; {sum(e['comparable'] for e in evs)} comparable, "
          f"{sum(e['match'] for e in evs)} match, {sum(e['mismatch'] for e in evs)} mismatch, of which CI-quoted claims "
          f"{sum(e['mismatch_ci_quoted'] for e in evs)} mismatch in {sum(e['comparable_ci_quoted'] for e in evs)} comparable; "
          f"{sum(e['unverifiable'] for e in evs)} unverifiable, {sum(e['non_comparable'] for e in evs)} non-comparable, "
          f"{sum(e['no_ci_data'] for e in evs)} without CI data; {sum(e['stale'] for e in evs)} stale bodies). "
          "Comparable = full-suite or CI-quoted backend counts, collected sums, vitest totals and CI-green claims "
          "checked against the CI Backend/Frontend Tests log and check conclusions for the stamped (else final) head. "
          "Recording only; counts, no body text.\n")
    a("## Weekly (ISO week of merge)\n")
    cmd_cell = cmds[0] if cmds else "n/a"
    a("| Week | Window | n PRs | First CI green (of decided) | Superseded | No CI | Pushes after open (median, total) | "
      "L0 corrections | Retitles | Reverted | Label | Command |")
    a("|---|---|---|---|---|---|---|---|---|---|---|---|")
    weeks = {}
    for r in records:
        weeks.setdefault(_week(r["merged"]), []).append(r)
    for wk in sorted(weeks):
        rs = weeks[wk]
        dates = sorted(r["merged"][:10] for r in rs)
        decided = [r for r in rs if r["first_ci"] in ("green", "not_green")]
        green = sum(r["first_ci"] == "green" for r in rs)
        pushes = [r["pushes"] for r in rs]
        a(f"| {wk} | {dates[0]} to {dates[-1]} | {len(rs)} | {green} of {len(decided)} | "
          f"{sum(r['first_ci'] == 'superseded' for r in rs)} | {sum(r['first_ci'] == 'no_ci' for r in rs)} | "
          f"{median(pushes):g}, {sum(pushes)} | {sum(r['corrections'] for r in rs)} | {sum(r['retitles'] for r in rs)} | "
          f"{sum(r['reverted'] for r in rs)} | {'small n' if len(rs) < SMALL_N else ''} | `{cmd_cell}` |")
    a("")
    a(f"Rows with n under {SMALL_N} are labelled `small n`: read the counts, not the ratios.\n")
    if any(r["truncated"] for r in records):
        a("WARNING: PRs " + ", ".join(f"#{r['number']}" for r in records if r["truncated"]) +
          " have more than 100 commits or timeline events; their counts are lower bounds.\n")
    if any(r["no_detail"] for r in records):
        a("WARNING: GraphQL detail failed for PRs " + ", ".join(f"#{r['number']}" for r in records if r["no_detail"]) +
          "; their trailer, retitle and push counts are missing, not zero.\n")
    a("## Commands\n")
    seen = []
    for c in cmds:
        short = re.sub(r"--json \S+", "--json <fields>", re.sub(r"(--branch |number=)\S+", r"\1<x>", c))
        short = re.sub(r"query=.*? -f owner", "query=<pr detail> -f owner", short)
        if short not in seen:
            seen.append(short)
    for c in seen:
        a(f"- `{c}`")
    a(f"\nAPI calls made: {CALLS}.")
    return "\n".join(P) + "\n"


def main(argv=None, runner=None, evidence_runners=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True)
    ap.add_argument("--until", required=True)
    ap.add_argument("--out")
    ap.add_argument("--ledger", default=DEFAULT_LEDGER)
    ap.add_argument("--no-evidence", action="store_true", help="skip the PR-body evidence column (saves API calls)")
    a = ap.parse_args(argv)
    since, until = parse_ts(a.since), parse_ts(a.until)
    ledger = load_ledger(a.ledger)
    note = "" if ledger is not None else f"Ledger file `{a.ledger}` not found: only trailer corrections are counted."
    recs = collect(runner or gh, since, until, ledger or [])
    if not a.no_evidence:
        pair = evidence_runners or ((gh, gh_text) if runner is None else None)
        if pair:
            collect_evidence(recs, *pair)
    cmds = list(CMDS) if runner is None else ["gh pr list --state merged --base main --search merged:<since>..<until>"]
    text = render(recs, since, until, cmds, note or f"Ledger: `{a.ledger}` ({len(ledger)} lines).")
    if a.out:
        with open(os.path.expanduser(a.out), "w", encoding="utf-8") as f:
            f.write(text)
        sys.stderr.write(f"wrote {a.out}\n")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
