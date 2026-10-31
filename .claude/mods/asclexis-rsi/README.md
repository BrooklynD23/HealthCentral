# asclexis-rsi (RSI Track 1)

Repo-shipped Claude Code mod: observe, report, guard. Built with the `plugin-authoring` skill.

## What it does
- **Observe:** one `tool.call` hook records one metadata-only row per tool call (and session start/end rows) to `.claude/logs/rsi/<YYYY-MM-DD>.jsonl` (git-ignored). Row: `v, ts, session, kind, tool, ok, duration_ms, denied, guard, hint, error_class, retry, edit_test_fail`.
  - `retry`: same tool + same input fingerprint within the last 5 calls after a failure (non-reversible hash, memory only).
  - `edit_test_fail`: a `pytest|vitest|playwright test|npm test` Bash call failed after an Edit/Write since the last test run.
- **Report:** status line `rsi: N calls · F fail · G guard`, and `/rsi` (this session + last 7 days: per-tool calls/failures/rate, retries, denials, hints by id, edit-to-test-fail cycles).
- **Guard:** `hooks/rules.ts` is a data-only rule table (`before` deny, `after` hint). Seeds: `pkill-self`, `playwright-exec-path`, `gh-pr-edit-projects-classic`, `venv-husk`, `llama-cpp-no-compiler`. A hint is appended to what the model reads after the tool result (`context`) and its id is logged in `hint`.

### Failure modes (decided)
- The deny rules (before `next`) **fail closed**: if the guard code throws, the call is denied (skill guard pattern).
- Logging and hints (after `next`) **fail open**: they run in their own try/catch, writes are fire-and-forget, so telemetry can never block, fail, or alter a call.

## Privacy
Metadata only. Rows never contain command text, file contents, tool output, prompts, or paths. `error_class` is a fixed category from the rule table (or, for non-Bash tool errors, `input-validation`, `no-such-tool`, `edit-not-read`, `read-not-found`, `read-too-large`, `schema-mismatch`, `user-rejected`, `workflow-not-found`, `workflow-bad-script`, `skill-disabled`, `task-not-found`, `task-not-running`, `subagent-limit`, `grep-pattern-rejected`, `permission-denied-auto`; or `exit-144-self-kill`, `timeout`, `edit-no-match`, `permission-denied`, `module-not-found`, `command-not-found`, `no-such-file`, `tests-failed`, `git-fatal`, `syntax-error`, `exit-<n>` (1-255), `other`), never raw text. Logs stay local in the git-ignored `.claude/logs/`. Nothing leaves the machine.

## Load it
```
claude --plugin-dir .claude/mods/asclexis-rsi
# or
CLAUDE_CODE_PLUGIN_DIRS=.claude/mods/asclexis-rsi claude
```
Start Claude from the repo root (the log path is relative to the session working directory). Note: concurrent sessions in the same directory append by read-then-write and can rarely drop a row; one log file is read per call (4 MiB limit, after which that day's rows stop).

## Verify
```
claude plugin validate .claude/mods/asclexis-rsi
claude plugin test .claude/mods/asclexis-rsi
```
Type-check with `tsc` using a tsconfig that includes the engine's `claude-code.d.ts` plus `hooks/`, `rsi.test.ts`, `replay/cases.ts`.

## Rules and replay set
Each rule needs at least one positive and one `pass` case in `replay/cases.ts` (the single source; `{id, rule, tool, input, error_text?, failed?, error_class?, expect: deny|hint|pass}`; `failed` defaults to "error_text is present"; when `error_class` is present the case also asserts the logged row's `error_class` equals it, so a class case uses `"rule": ""` and `"expect": "pass"`). `rsi-loop` proposals may edit only `hooks/rules.ts`, `replay/cases.ts`, and `docs/agentic/recurring-failures.md`.
