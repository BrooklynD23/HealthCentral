# Session handoff: 2026-10-16 → 2026-10-17 (L0, Opus 5.5)

**Last Updated:** 2026-10-17
**Owner:** repository owner
**Refresh Trigger:** the next L0 session reads this first, works the "Not started" list, and replaces this file with its own handoff.

Read this after [CLAUDE.md](../../CLAUDE.md), [AGENT.md](../../AGENT.md) and the [build-program RUNBOOK](2026-10-15-build-program/RUNBOOK.md). Owner answers quoted here are recorded in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md) (rows dated 2026-10-17). Verify every fact below with `git`/`gh` before acting on it. This is a lead, not a finding.

## 1. What this session did

**Model host.** The owner's RTX 3080 WSL box now runs Ollama 0.40.5 on localhost with `gemma4:e4b`, `llama3.1:8b`, `qwen3:8b` and `gemma3:12b`. `build-essential` is installed. The build venv `~/venvs/asclexis-311` (uv CPython 3.11.17, full requirements including `llama_cpp`) is the RUNBOOK §6 path. `all-MiniLM-L6-v2` is cached, so `test_api_rag_index_002b` passes here.

**Model-machine checks (TASK_LIST MM-1, MM-3, MM-4: done).**
- **MM-1:** abstain counts out of 20 were `gemma4:e4b` 20, `llama3.1:8b` 20, `gemma3:12b` 19 and `qwen3:8b` 15. The abstentions are correct: REPORT FACTS carries no `[cite:N]`, and the models invent ADA/AHA references. Evidence is in #72 comments 6226130965 and 6228253080.
- **MM-3:** `1690 passed` with the real embedding model.
- **MM-4:** `dev.sh` boot plus a headless Playwright walk of setup, import, verify, chat, interpretation and achievements. It produced 6 follow-up queue rows.

**Merged:**

| PR | What |
|---|---|
| #72 | W-4 legacy abstain |
| #118 | post-merge batch: count 1690, MM ticks |
| #119 | ASSIST-AGENT-DATES: all four chat filters, "add" semantics (AAD-SEMANTICS) |
| #120 | post-merge batch: count 1714 |
| #94 | wearables plans (merged by the owner) |
| #74 | Tailwind 4, after the owner's TW4-SHOTS approval |

**Closed:** #61 (superseded by #72; branch kept).

**Opened, not merged at handoff:**

| PR | What | State |
|---|---|---|
| #68 | RSI-loop research and session-log hook | Synced with main per PR68-SYNC: `1721 tests collected` (+7), `1721 passed`. A background watcher was set to merge it once CI is green (owner: "close down #68 ... when green"). If it is still open, check CI and merge. |
| #121 | `build-program` workflow | Sub-orchestrator loop over `build-wave`/`build-item`: Opus unblocker, Opus planner for unplanned rows, optional auto-merge. Docs-only diff; CI green at open. Owner merges. |
| #122 | RSI research package | `docs/research/2026-10-17-rsi-opt-in-data/`: 4 Haiku sweeps, 58 sources, synthesis. CI green. Owner merges. |
| this PR | handoff and owner rows | This file plus 44 owner-decision rows dated 2026-10-17. |

**Owner answers recorded today:**
- Group A: 30 gates, all recommended options. Two were then overridden by the owner: RSI-1 is **build it**, and RSI-4 is **a Claude Code mod, two tracks**.
- RSI-BUILD (cadence, location, order, capstone documentation).
- M0.
- AUTO-MERGE: standing for build-program PRs.
- Group B: O-5, Q-HASH, Q-AUD-LIST, OG-1, GC5-ASKFIRST (approved in advance), P8-B2-ORDER (**Brief 2 first**), W1-SMOKE-RUN, CORRELATION-NORMALISE, RTN-Q1 (**create it**), SHOW-DATE (rule only: freeze = showcase − 7 days; **date still unknown**).

## 2. Not started (do these, in this order, parallel where independent)

1. **Post-merge batch** after #68 (and #74, which moved no tests). Re-measure collected on main; it should be 1721. Update the slots, queue statuses (#72, #74, #94 and #68 merged; E-4 done; F-10 landing) and TASK_LIST OW-2 / OW-5 ticks. One docs PR; merge on green (AUTO-MERGE).
2. **RSI mod, Track 1 (dev harness).** A repo-shipped Claude Code mod at `.claude/mods/asclexis-rsi/`, written with the `plugin-authoring` skill.
   - **Observe:** `tool.call` hooks record metadata only (tool, ok/fail, duration, retries, denials, edit→test-fail cycles) to the git-ignored `.claude/logs/rsi/`. Reuse #68's hook conventions.
   - **Report:** a status-line counter and an `/rsi` scoreboard command.
   - **Guard hooks** promoted from mined failures. Seeds from this session:
     - `pkill -f` matching its own shell (exit 144)
     - Playwright browser path mismatch
     - `gh pr edit` failing on Projects classic, so use `gh api -X PATCH`
     - venv husk files that exit 0 without running anything
     - `llama-cpp-python` with no C compiler
   - **Template:** a general-purpose copy outside the repo (owner: "root directory or global"). Default to `~/.claude/mods-templates/rsi-loop/` and confirm the location with the owner.
   - Validate with `claude plugin validate` and `claude plugin test`.
3. **`rsi-loop` workflow (step 2).** `.claude/workflows/rsi-loop.js`, also called as the last stage of `build-program` (cadence: after every run).
   - **Mine:** Haiku clusters failures; Opus writes GEPA-style reflections.
   - **Propose:** small single-purpose edits only.
   - **Gate:** a replay set of past failures plus CI. Reject any candidate that edits tests, gate scripts or thresholds, or touches ask-first files.
   - **PR:** the owner merges. RSI promotions are never agent-merged.
   - **Measure:** before/after per-tool failure rate, retries and tokens per item. Keep an archive of rejected candidates.
4. **App track (step 3), as planned queue items.**
   - **(a) Track-2 eval harness:** generalise the MM-1 script and run it on all four local models. Metrics: abstain rate and cited-answer rate.
   - **(b) LEGACY-CITE-PROMPT with constrained decoding (RSI-3):** an Ollama `format` schema or GBNF grammar. The faithfulness gate stays unchanged.
   - **(c) RSI-1 opt-in donation pipeline:**
     1. consent screen, per purpose and revocable
     2. local `strict` redaction plus a second PHI detector, with recall measured
     3. local-only store (RSI-2)
     4. canary and extraction leak eval
     5. mix real and synthetic data, never replace real

     Ask-first: it **calls** `modules/redaction.py` and never edits it.
5. **Capstone report section** (owner: "will have to be documented for the capstone report too"). Add an "RSI in development and in the application" section under `docs/capstone-report/`: both tracks, the six-step loop, gates and safety rails, the measured baselines (MM-1 counts; this session's tool failures), and results as they land. Source: `docs/research/2026-10-17-rsi-opt-in-data/00-README.md` (#122).
6. **Nightly doc-drift routine (F-8, RTN-Q1 = yes).** Create it with the `schedule` skill per `docs/plans/2026-09-27-nightly-doc-drift-routine-spec.md`, with Q2-Q6 as recorded: `0 7 * * *`, no Docs page, Sonnet, one smoke run, push not enabled.
7. **Run `build-program`** (from #121 once merged) with `{"max_waves": 4, "auto_merge": true}`. Today's answers unblock many rows (Group A/B). The planner stage plans the 12 unplanned rows (E-1b, REDACT-EMAIL-REDOS, MED-STREAK-GRACE, AUDIT-MISSING-MED, EXPORT-TODAY-TZ, LEGACY-CITE-PROMPT, CHAT-FACT-ROUTING, INTERP-RENDER, INTERP-ADVICE-WORDING, LOCAL-HF-HUB, DEV-SH-CC, EXTRACT-FORMATS). Ask-first rows still need the owner's yes on their diff. GC5-ASKFIRST is pre-approved for `verifier_agent.py:304-317` only.

## 3. Still waiting on the owner

| Item | What the owner does | Unblocks |
|---|---|---|
| P6-ORPHAN | Run `scripts/fk_orphan_audit.py --profile <id> --source <copy of real backup>` locally and paste the counts | C-P6 Tasks 2-5 → C-P7 → E-2, C-GC1 |
| OW-3 | Write sealed set S5 outside every worktree; commit only sha256 + counts | B-4, MM-2, the RSI Track-2 sealed gate |
| P8 Brief 2 | Sign it (owner chose "Brief 2 first") | F-4 |
| SHOW-DATE | Give the showcase date (freeze = date − 7) | F-9 |
| G-C2 | Say when to un-defer the OpenWiki run | F-7 |
| Merges | #121, #122 and this PR (docs and harness; not agent-merged by choice) | build-program run, capstone section |

## 4. Gotchas learned this session

- Stop dev servers by port (`lsof -ti:PORT -sTCP:LISTEN | xargs kill`). `pkill -f "<pattern>"` can match the agent's own shell and kill it (exit 144).
- Playwright: launch with `executablePath` = `~/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome`; the bundled revision differs.
- The text-PDF parser reads only `Analyte: value unit (range)` lines; no `mIU/L`.
- `docs/INDEX.md` conflicts on almost every sync. Resolve by regenerating (SLOT-RULE-2a) and merge soon after green, before main moves again.
- Don't run the pytest suite during model runs: the 60 s generation timeout inflates abstain counts.
