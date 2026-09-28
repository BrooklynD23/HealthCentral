# Nightly Doc-Drift Routine — Specification

**Last Updated:** 2026-09-27
**Owner:** repository owner
**Refresh Trigger:** a new docs gate script lands, a baseline sentence changes shape, or the routine's run log shows a check that cannot run
**Status:** PROPOSED — not created. The routine is created only after the owner confirms this spec (§9).

A read-only job that runs every night at 00:00 America/Los_Angeles. It runs the repository's docs gates, greps the docs' claims against the code, and writes a dated drift report with proposed fixes. It never commits, pushes, opens a PR or edits a tracked file.

Program context: [implementation-program.md](../capstone-report/implementation-program.md) · recurring failure modes it watches for: [recurring-failures.md](../agentic/recurring-failures.md) #3 (figures asserted instead of measured), #4 (environment-dependent results), #6 (documented commands nobody ran), #8 (stale guidance).

## 1. Platform comparison

| Criterion | Claude Routine (`/schedule`) | Muse | Grok bot |
|---|---|---|---|
| Repo access | **Verified 2026-09-27:** each run is an isolated cloud session with its own git checkout of `https://github.com/BrooklynD23/HealthCentral` (the schedule skill's default source). No local files | **UNVERIFIED.** An agent harness with `bash`, `read_file` and `search` tools (superpowers `references/muse-tools.md`), but not installed on this machine (`which muse` → none). No scheduler or repo integration verified | **UNVERIFIED.** No local install or integration found. Repo access unknown |
| Read-only control | `allowed_tools` list per routine. Omitting `Write`/`Edit` blocks file-edit tools. `Bash` is still needed to run the gates, and `Bash` can run `git push`. So "no commit" is enforced by prompt plus audit, not by the platform (§6) | Unknown | Unknown |
| Schedule | 5-field cron in **UTC**, minimum interval 1 h (schedule skill, 2026-09-27) | Unknown | Unknown |
| Cost | Runs count against the account's Claude usage; per-run cost **UNMEASURED** (measure from the first 3 runs' logs) | Unknown | Unknown |
| Determinism | The gate scripts are deterministic. The LLM part (reading output, writing the report) is not; the prompt pins exact commands and a fixed report template to bound it | Unknown | Unknown |
| Output | The run's final message and log (`list_runs` / `get_run_log`; web: claude.ai/code/routines). Optionally a Claude Docs page via the connected Claude-Docs connector | Unknown | Unknown |

**Default: Claude Routine.** It is the only option whose repo access and scheduling were verified in this setup. Muse and the Grok bot stay as comparisons until someone verifies their repo access.

## 2. Schedule

- **Target:** 00:00 America/Los_Angeles, nightly.
- **Cron is UTC and cannot follow DST.** 00:00 PDT = 07:00 UTC; 00:00 PST = 08:00 UTC.
- **Proposed:** `0 7 * * *`. That is 00:00 while PDT is in effect (until 2026-11-01), then 23:00 PST.
- **Owner choice (§9 Q2):** either accept the one-hour winter shift, or update the cron to `0 8 * * *` on 2026-11-01 and back on 2026-03-08.

## 3. What each run does

All commands run from the checkout root on the default branch (`main`). A check whose script is absent is reported as `SKIPPED (absent on main)`, not as a pass.

| # | Check | Command | Pass condition | Notes |
|---|---|---|---|---|
| C1 | Docs lint | `python3 scripts/docs_lint.py` | exit 0, prints `Docs lint passed.` | Present on main |
| C2 | Docs index fresh | `python3 scripts/generate_docs_index.py --check` | exit 0 | Present on main. Stale on the owner's working tree today (2026-09-27); CI runs it too |
| C3 | Harness drift | `python3 scripts/harness_drift_check.py` | exit 0 | Absent on main until P1 lands (branch B `7b2ff1f`) → `SKIPPED` until then |
| C4 | Repo hygiene | `python3 scripts/repo_hygiene_check.py` | exit 0 | Present on main |
| C5 | Collected-test count vs docs | `cd src/backend && python3 -m pytest tests/ --collect-only -q -p no:cacheprovider` (after `pip install -r requirements.txt`) vs the collected numbers in `CLAUDE.md` and `AGENT.md` | the docs' collected counts equal the measured count, and each other | If install or collection fails, report `UNMEASURED` with the error. Compare **collected** counts only, never pass counts (recurring-failures #4). Branch B today: `CLAUDE.md:30` says 1288, `AGENT.md:76` says 1269 |
| C6 | Route count vs docs | Python `ast` scan of `src/backend/api/*.py` for `@router.<method>` decorators (multiline-safe), plus mount prefixes from `api/__init__.py` | every route count or route list a doc states matches | Report each doc line that states a count |
| C7 | Invariant greps | the three commands in §8 C7, verbatim (kept out of this table so no `\|` escaping reaches a shell) | report the counts; flag any doc that claims 0 while the count is > 0 | These track P5, W-7 and S-1. The routine reports; it never judges an invariant "fixed" |
| C8 | Documented commands exist | For each `python …scripts/<x>.py` or `npm run <x>` quoted in `AGENT.md`, `CLAUDE.md` and `docs/`: check the script or npm script exists at the stated path | every quoted script exists | Existence only; the routine does not execute product commands (recurring-failures #6) |

The job never runs the full test suite, never starts the app, never downloads models, and never runs `generate_docs_index.py` without `--check`.

## 4. Report format (fixed template)

```text
# Doc-drift report — <YYYY-MM-DD> (America/Los_Angeles), main @ <short sha>
Environment: <python --version>, cloud routine run <session id>
| # | Check | Result | Evidence (command → first/last lines) |
C1..C8 rows, each PASS / FAIL / SKIPPED (reason) / UNMEASURED (reason)
## Drift found
- <doc path:line> says "<claim>"; measured "<value>" via `<command>`
## Proposed fixes (not applied)
- <doc path:line>: replace "<old>" with "<new>" — evidence: <command>
## Not checked tonight
- <item> — <reason>
```

Every number in the report carries the command that produced it (recurring-failures #3). "No drift" is written only when C1–C8 all ran and passed.

## 5. Where the report goes

- **Default:** the run's final message, readable in the run log (`get_run_log`) and at claude.ai/code/routines.
- **Optional (§9 Q3):** also write it to a dated Claude Docs page through the connected Claude-Docs connector (`connector_uuid 1a59c906-04da-521d-bda7-7f71b9f9e01c`). That is a claude.ai surface, not the repo.
- **Never:** a commit, a branch, a PR, or an edit to a tracked file.

## 6. Guardrails

1. **Tools:** `allowed_tools: ["Bash", "Read", "Glob", "Grep"]`. No `Write`, `Edit` or MCP tools, unless the owner picks the Claude Docs option.
2. **No commit — enforced by prompt, audited after.** The prompt forbids `git add/commit/push/branch/tag`, `gh`, and any edit to a tracked file. `Bash` can still run them, so each morning's check is: `git ls-remote --heads origin` shows no new branches, and the run log shows no `git push` or `gh` call. The first 3 runs are audited this way before the routine is trusted.
3. **No patient data:** the cloud checkout holds only tracked files. `data/` and `*.db` are gitignored (`.gitignore:73-79`). The prompt forbids creating a database or starting the app.
4. **Network:** the only network use is `pip install` for C5, in the cloud sandbox. No product code path runs.
5. **Kill switch:** disable the routine at claude.ai/code/routines. The API cannot delete routines.

## 7. Proposed routine body (not sent)

Sent only after the owner confirms §9. `model` defaults to `claude-sonnet-5`, per the schedule skill's default for routines and the user rule that reserves Sonnet 5 for cost-sensitive bulk work. The owner may choose `claude-opus-5-5` instead (§9 Q4).

```json
{
  "name": "asclexis-nightly-doc-drift",
  "cron_expression": "0 7 * * *",
  "enabled": true,
  "job_config": {
    "ccr": {
      "environment_id": "env_012CLTzohPPrf26mKXAjBtJL",
      "session_context": {
        "model": "claude-sonnet-5",
        "sources": [{"git_repository": {"url": "https://github.com/BrooklynD23/HealthCentral"}}],
        "allowed_tools": ["Bash", "Read", "Glob", "Grep"]
      },
      "events": [{"data": {
        "uuid": "9b871ddc-94d9-466b-b866-cd384fbdc34d",
        "session_id": "",
        "type": "user",
        "parent_tool_use_id": null,
        "message": {"role": "user", "content": "<PROMPT: §8 verbatim>"}
      }}]
    }
  }
}
```

## 8. Routine prompt (verbatim)

```text
You are a READ-ONLY nightly doc-drift checker for the Asclexis repo (this checkout, default branch).
NEVER run git add/commit/push/branch/tag/checkout -b, gh, or any command that edits a tracked file.
NEVER start the app, create a database, download models, or run the full test suite.
Run checks C1-C8 exactly as listed below, from the checkout root. For each, record the command,
exit code, and the first and last 5 lines of output. If a script is absent, record SKIPPED (absent on main).
If a command fails for environment reasons, record UNMEASURED with the error line. Never guess a number.
C1 python3 scripts/docs_lint.py
C2 python3 scripts/generate_docs_index.py --check
C3 python3 scripts/harness_drift_check.py   (if present)
C4 python3 scripts/repo_hygiene_check.py
C5 pip install -r src/backend/requirements.txt, then (cd src/backend && python3 -m pytest tests/ --collect-only -q -p no:cacheprovider);
   compare the collected count with every "collected" number in CLAUDE.md and AGENT.md. Compare collected counts only.
C6 ast-scan src/backend/api/*.py for @router.<method> decorators (multiline-safe) plus prefixes in api/__init__.py;
   compare with any route count/list stated in docs/.
C7 run these three and report each count; flag any doc claiming 0 when the count is > 0:
   grep -rn "datetime\.utcnow" src/backend --include=*.py | grep -v /tests/ | wc -l
   grep -rnE "^[[:space:]]*(from llama_cpp|import llama_cpp)" src/backend --include=*.py | grep -v "core/llm/" | wc -l
   grep -rn "echo=settings.debug" src/backend/core | wc -l
C8 for every `python ...scripts/<x>.py` or `npm run <x>` quoted in AGENT.md, CLAUDE.md, docs/: check that the file or npm script exists.
Then output the report in the fixed template (spec §4). Every number carries its command. Propose fixes as
old->new text with evidence; do not apply them. Write "No drift" only if C1-C8 all ran and passed.
```

## 9. Owner confirmation (unsigned)

| Q | Question | Default |
|---|---|---|
| Q1 | Create the routine as specified (Claude Routine, read-only, never commits)? | — (required) |
| Q2 | DST: keep `0 7 * * *` all year (23:00 in winter), or switch the cron at each DST change? | keep `0 7 * * *` |
| Q3 | Also write each report to a dated Claude Docs page (adds the Claude-Docs connector)? | no — run log only |
| Q4 | Model: `claude-sonnet-5` (lower cost) or `claude-opus-5-5`? | `claude-sonnet-5` |
| Q5 | Run once now as a smoke test after creation (`RemoteTrigger run`), then audit that run per §6.2? | yes |

- [ ] Owner sign-off: ______ (date) — Q1–Q5 answers recorded here verbatim.

## 10. Known limits

- Until P0-B and the plan-set docs commit land, `main` lacks `docs/capstone-report/`, `audit/` and these plans, so the routine checks only what `main` holds.
- C5 needs the backend's dependencies. SQLCipher needs `libsqlcipher-dev`, which the cloud image may lack. If collection fails, C5 reports `UNMEASURED` and does not fail the report.
- Pass counts are out of scope. They vary by environment (the embedding-model test, recurring-failures #4).
