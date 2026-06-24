# Standup Log — Agent Overhaul

> **Format (keep it):** one dated block per working day. Three lines:
> *Yesterday / Today / Blocker*. Append at the **top** (newest first). Two
> minutes, not a status report. This is the solo-engineer memory between
> sprints (AGILE_PLAN §3).

---

## 2026-06-24 (S2)
- **Yesterday:** S2-1 (`compute_trend`, `check_verification`, `lookup_reference`,
  `retrieve_chunks` — four typed, read-only, audited tools, registered), S2-2
  (reflect node + hard `MAX_STEPS=5` budget — `graph.run_agent` is now the real
  plan→act→reflect→(loop|draft)→guard(passthrough)→terminal loop; over-budget
  → graceful abstain via `ABSTAIN_TEMPLATE`), S2-3 (`graph.replay` reconstructs
  the terminal from `RunLog.steps` without re-calling any tool — verified by a
  test that makes `registry.get` raise during replay), and S2-4 (eval harness,
  `tests/agent/eval_harness.py`, materializes a golden case's vault into an
  in-memory profile DB and runs `run_agent`; both seed cases —
  `grounded-ldl-trend`, `abstain-unverified-ldl` — pass) implemented and merged
  (commit fbb4fe7). The deterministic planner now also routes trend questions
  straight to `compute_trend` and routes analyte-named "why" questions with no
  verified rows through `check_verification` → abstain. Three S2 skip-stubs in
  `test_s2_loop.py` flipped to live assertions. Suite went from 27 passed/15
  skipped to **30 passed, 12 skipped** — zero failures, flag-off legacy path
  untouched. **R1 ships** — all three R1-backing RELEASE_CHECKLIST rows (1, 2,
  8) are now `[x]`.
- **Today:** Closing out S2 tracking docs (checklist, sprint/phase status,
  reconciliation) and marking R1 shipped/accepted. Next up: S3 kickoff (guard
  node — advice gate ×2, unmapped-claim drop, abstain/escalate — Release R2).
- **Blocker:** None for S2 functionally — the loop closes and the eval harness
  runs green. Two deliberate AC deviations carried forward, not blocking:
  `retrieve_chunks` uses a deterministic text-match fallback rather than the
  RAG vector retriever, because the real vector path needs `Embedding` rows
  that golden/unit fixtures don't generate; and `lookup_reference` reads the
  master DB directly via `core.database.async_session_maker` rather than
  `ctx.db_session` (which is profile-scoped), since `BiomarkerKnowledge` lives
  in the master DB, not a profile DB. Both captured as new reconciliation
  items — see RECONCILIATION.md R-10, R-11.

## 2026-06-24 (S1)
- **Yesterday:** S1-1 (typed tool registry), S1-2 (`query_observations`), S1-3
  (plan→act→draft single-step path), and S1-4 (per-node audit emission)
  implemented and merged (commit 0f09cd3). The three S1 skip-stubs in
  `test_s1_first_tool.py` flipped to live assertions — verified-only filtering,
  flag-on answer with ≥1 citation, and exactly one audit event each from
  plan/act/draft. Suite went from 24 passed/18 skipped to **27 passed, 15
  skipped** — zero failures, flag-off legacy path untouched.
- **Today:** Closing out S1 tracking docs (checklist, sprint/phase status,
  reconciliation) and prepping S2 kickoff (reflect node + step budget loop,
  `compute_trend`/`retrieve_chunks`/`lookup_reference`/`check_verification`).
- **Blocker:** None for S1 functionally — the single-step path is green. Two
  deliberate scope deferrals carried forward by design, not blocking: the
  planner is deterministic/keyword-based for S1 (LLM seam is injectable via
  the `planner` param, no live model called yet), and `graph.py`'s guard node
  is a trivial passthrough (`_passthrough_guard`) awaiting S3's real
  advice/groundedness/confidence gates. New reconciliation item opened for the
  `ToolContext` Protocol's `run_id`/`step_index` extension — see
  RECONCILIATION.md R-9.

## 2026-06-24 (S0)
- **Yesterday:** S0-2 (`is_agent_enabled`) and S0-3 (`emit_audit_event`) implemented
  and merged (commit 3e63df2). The two S0 skip-stubs in `test_s0_foundation.py`
  flipped to live assertions; suite went from 22 passed/20 skipped to **24
  passed, 18 skipped** — zero failures.
- **Today:** Closing out S0 tracking docs (checklist, sprint/phase status,
  reconciliation) and prepping S1 kickoff (typed tool registry, `query_observations`).
- **Blocker:** None for S0 — it's foundational only (flag helper + audit helper,
  both off/no-op by default). Flagging for S1/S5 planning: `UserModelSettings`
  has no `agent_enabled` column yet, so no live caller can persist the flag ON
  until a migration lands (see RECONCILIATION.md R-8).

## 2026-06-23 (S0)
- **Yesterday:** Inception week opened (2026-06-22). Planning bundle ingested.
- **Today:** PM-orchestrator pass — grounding, exploration, PRD + phase + sprint
  docs, and Sprint 0–7 code/test scaffolds committed (flag OFF, stubs only).
- **Blocker:** WSL proof-bundle venv (`.wsl-pytest-venv`) points at a Windows
  path and can't run in this container; scaffolds validated with a throwaway
  `pydantic`/`pytest` install instead. Flagged in RECONCILIATION.md.

<!-- New entries go ABOVE this line. Template:
## YYYY-MM-DD (S#)
- **Yesterday:**
- **Today:**
- **Blocker:**
-->
