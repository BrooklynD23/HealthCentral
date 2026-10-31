# RSI run archive

**Last Updated:** 2026-10-31
**Owner:** repository owner (the L0 session that runs rsi-loop adds its run folder)
**Refresh Trigger:** each rsi-loop run on any machine, or a change to the rsi-log or session-log row format.

rsi-loop reads two logs that are git-ignored, so they stay on the machine that wrote them:
- `.claude/logs/rsi/<date>.jsonl`, written by the `asclexis-rsi` mod when the session starts with `--plugin-dir .claude/mods/asclexis-rsi`;
- `.claude/logs/session-log.jsonl`, written by `.claude/hooks/session_log.py`.

This folder keeps a committed copy of them, so runs from different machines (the laptop and the RTX 3080 GPU box) can be combined later for the report on how RSI developed. Both logs hold metadata only: tool names, ok and exit codes, durations, error classes and file paths. They hold no command text, no output and no patient data. Scan for secrets before you commit a copy.

## Layout

One folder per machine and date: `<YYYY-MM-DD>-<machine>/`.

| File | What it is |
|---|---|
| `rsi-log.jsonl` | Copy of `.claude/logs/rsi/<date>.jsonl` (rows per the rsi contract: `kind` tool or session) |
| `session-log.jsonl` | **Windowed** copy of `.claude/logs/session-log.jsonl`: only the rows in the folder's window (see Windows below), not the cumulative file. Applies from `2026-10-22-gpubox` on (owner RSI-ARCHIVE-SIZE, `docs/capstone-report/owner-decisions-2026-09-27.md:404`); `2026-10-21-laptop` keeps its earlier cumulative copy |
| `summary.json` | The rsi-loop result for that run: clusters, candidates, metrics. Copy `.claude/logs/rsi/summary-<run_id>.json` when the run wrote one; otherwise copy the workflow result |
| `summary-dry.json` | Only in `2026-10-24-gpubox`: the dry run's result object (`run_id` `2026-10-24-gpubox-dry`, `dry_run` true), with the workflow progress and prompt or result previews left out |

## Windows

Exact cuts, in UTC. Each folder is cut once at archive time. The live session keeps writing after that, so later rows are not archived.

- `2026-10-22-gpubox`: `2026-10-21T00:00Z <= ts < 2026-10-23T00:00Z`. Session-log rows 4657, last archived `ts` `2026-10-22T23:56:01.448692Z`. rsi-log is the whole `rsi/2026-10-21.jsonl` and `rsi/2026-10-22.jsonl`, 3167 rows.
- `2026-10-24-gpubox`: `ts >= 2026-10-23T00:00Z`, cut at the last archived `ts` `2026-10-24T07:29:07Z` (last row `2026-10-24T07:29:07.485998Z`). Session-log rows 5600. rsi-log is the whole `rsi/2026-10-23.jsonl` and `rsi/2026-10-24.jsonl` as of the same cut, 2518 rows, last row `2026-10-24T07:29:07.404Z`.
- `2026-10-26-gpubox`: `2026-10-24T07:29:07.485998Z < ts < 2026-10-27T00:00Z` (starts after the `2026-10-24-gpubox` cut, so no row is archived twice). Session-log rows 9668, last archived `ts` `2026-10-26T15:16:53.741751Z`. rsi-log is the rows of `rsi/2026-10-24.jsonl` after the cut plus the whole `rsi/2026-10-26.jsonl`, 2951 rows, last row `2026-10-26T15:16:53.674Z`. There is no `rsi/2026-10-25.jsonl`: the rsi-log has no rows from `2026-10-24T15:15:33.229Z` (last row of `rsi/2026-10-24.jsonl`) to `2026-10-26T02:55:35.360Z` (first row of `rsi/2026-10-26.jsonl`), while a session ran without the mod. The 2026-10-26 handoff's "08:15Z" is the file's local (PDT) mtime, not UTC.
- `2026-10-31-gpubox`: `2026-10-26T15:16:53.741751Z < ts < 2026-10-31T00:00:00Z` for the session-log and `2026-10-26T15:16:53.674Z < ts < 2026-10-31T00:00:00Z` for the rsi-log (starts after the `2026-10-26-gpubox` cut; ends before the run's own session so its rows are excluded). Session-log rows 5982, last archived `ts` `2026-10-30T23:59:57.510687+00:00`. rsi-log is the whole `rsi/2026-10-27.jsonl` and `rsi/2026-10-28.jsonl`, 5299 rows (`rsi/2026-10-26.jsonl` has no row after the cut), last row `2026-10-28T20:54:21.227Z`. There are no `rsi/2026-10-29.jsonl` or `rsi/2026-10-30.jsonl`: the rsi-log has no rows after `2026-10-28T20:54:21.227Z` before the cut, while the session-log has rows through 10-30 (the mod was not loaded for those days). The run wrote no `summary-<run_id>.json` (only `summary-2026-10-24-gpubox.json` exists in `.claude/logs/rsi/`), so `summary.json` is the workflow result (`wf_e5b0ec9e-d37`, args `{"since":"2026-10-26"}`) with `run_id` and `workflow_run` added.
- `2026-10-21-laptop`: earlier cumulative copy, not trimmed.

## Runs

| Folder | run_id | Tool calls | Clusters | Candidates | Note |
|---|---|---|---|---|---|
| [2026-10-21-laptop](2026-10-21-laptop/summary.json) | `2026-10-21-local` | 344 | 6 | 0 | First run with the mod loaded. The cloud run `2026-10-21-cloud` logged 0 calls because the mod was not loaded |
| [2026-10-22-gpubox](2026-10-22-gpubox/summary.json) | `none` | 3167 | — | — | no rsi-loop; archive only |
| [2026-10-24-gpubox](2026-10-24-gpubox/summary.json) | `2026-10-24-gpubox` | 8210 (mined by rsi-loop since 2026-10-21; this folder's rsi-log holds 2518 rows, 2026-10-23..24) | 33 | 1 | mod loaded; dry run first (0 candidates, Codex proposer validated, #303); real run opened RSI PR #341 (owner merges) |
| [2026-10-26-gpubox](2026-10-26-gpubox/summary.json) | `2026-10-26-gpubox` | 2489 (mined since 2026-10-24T07:18Z, per the handoff) | not recorded | 0 | mod loaded; Claude and Codex both returned "nothing worth proposing". `summary.json` is reconstructed from the 2026-10-26 handoff §1, since the run wrote no summary file |
| [2026-10-31-gpubox](2026-10-31-gpubox/summary.json) | `2026-10-31-gpubox` | 7499 (mined since 2026-10-26) | 15 | 0 | mod loaded; Opus and Codex reflections on the top 3 clusters (Bash no-such-file 39, already covered by rule no-such-file-path; Bash other 26, unclassified; Bash exit-1 15, generic) both returned nothing worth proposing; no PR |

## Adding a run (for example, from the GPU box)

1. Start the session with `--plugin-dir .claude/mods/asclexis-rsi` and run `rsi-loop`.
2. Make the folder: `mkdir -p docs/agentic/rsi-runs/$(date -u +%F)-gpubox`.
3. Copy `.claude/logs/rsi/<date>.jsonl` to `rsi-log.jsonl`. For `session-log.jsonl`, copy only the rows whose `ts` falls in the folder's window (not the cumulative file; see Windows), and add the run's `summary.json`.
4. Check for secrets: `grep -ciE 'token|secret|password|api[_-]?key|bearer' <folder>/*.jsonl <folder>/*.json` must print 0 for each file, except that a summary file may print 1 for the literal metric key `tokens_per_item`. To verify: `grep -oiE 'token[a-z_]*|secret|password|api[_-]?key|bearer' <file> | sort | uniq -c` must list only `tokens_per_item`, or nothing.
5. Add a row to the Runs table, then commit in a docs PR.

To combine the runs, deduplicate on `ts` + session id, because `session-log.jsonl` copies are cumulative per machine:
`cat docs/agentic/rsi-runs/*/rsi-log.jsonl | sort -u > /tmp/rsi-all.jsonl`.
