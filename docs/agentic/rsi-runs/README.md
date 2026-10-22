# RSI run archive

**Last Updated:** 2026-10-21
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
| `session-log.jsonl` | Copy of `.claude/logs/session-log.jsonl` as it stood at archive time (cumulative on that machine) |
| `summary.json` | The rsi-loop result for that run: clusters, candidates, metrics. Copy `.claude/logs/rsi/summary-<run_id>.json` when the run wrote one; otherwise copy the workflow result |

## Runs

| Folder | run_id | Tool calls | Clusters | Candidates | Note |
|---|---|---|---|---|---|
| [2026-10-21-laptop](2026-10-21-laptop/summary.json) | `2026-10-21-local` | 344 | 6 | 0 | First run with the mod loaded. The cloud run `2026-10-21-cloud` logged 0 calls because the mod was not loaded |

## Adding a run (for example, from the GPU box)

1. Start the session with `--plugin-dir .claude/mods/asclexis-rsi` and run `rsi-loop`.
2. Make the folder: `mkdir -p docs/agentic/rsi-runs/$(date -u +%F)-gpubox`.
3. Copy `.claude/logs/rsi/<date>.jsonl` to `rsi-log.jsonl` and `.claude/logs/session-log.jsonl` to `session-log.jsonl`, and add the run's `summary.json`.
4. Check for secrets: `grep -ciE 'token|secret|password|api[_-]?key|bearer' <folder>/*.jsonl` must print 0 for each file.
5. Add a row to the Runs table, then commit in a docs PR.

To combine the runs, deduplicate on `ts` + session id, because `session-log.jsonl` copies are cumulative per machine:
`cat docs/agentic/rsi-runs/*/rsi-log.jsonl | sort -u > /tmp/rsi-all.jsonl`.
