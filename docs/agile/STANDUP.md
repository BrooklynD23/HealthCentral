# Standup Log — Agent Overhaul

> **Format (keep it):** one dated block per working day. Three lines:
> *Yesterday / Today / Blocker*. Append at the **top** (newest first). Two
> minutes, not a status report. This is the solo-engineer memory between
> sprints (AGILE_PLAN §3).

---

## 2026-06-24 (S4)
- **Yesterday:** S4-1 (PHI redaction gate, `guardrails/redaction_gate.py` —
  `gate_external_payload` is a thin fail-closed adapter over
  `RedactionEngine(policy_level).redact(payload).text`, no bypass param,
  signature-enforced; verified by grep that the agent graph has no
  external-egress call site today, so the gate stands as the documented
  mandatory chokepoint for any FUTURE agent external-LLM tool, separate from
  `core/external_runner.py`'s existing `/assistant/`-scoped enforcement; two
  extra fail-closed tests added), S4-2 (network-disabled offline integration
  test — monkeypatches `socket` to block `AF_INET`/`AF_INET6` +
  `create_connection`, leaves `AF_UNIX` for asyncio's self-pipe; runs both
  grounded→answer and abstain→abstain through the harness with zero network,
  proving local-first), and S4-3 (golden set grown 6→30: 9 grounded, 8
  abstain, 8 advice-bait, 5 mixed; `test_s4_3_golden_set_categories_pass`
  asserts every case resolves to its expected terminal) implemented and
  merged (commit 43f7a4b). R-12 (planner analyte-synonym gap) is RESOLVED in
  the same commit: `nodes/plan.py` adds `_detect_topics()` — a
  keyword→topic-group mapping (lipid/kidney/glucose/thyroid/electrolyte/
  vitamin/blood_count) plus a kidney→Creatinine single-topic fallback — so a
  multi-topic question now queries `query_observations` with NO narrow
  filter (broaden instead of guessing one exact-match string), letting
  groundedness/guard decide what's actually backed.
  `mixed-partial-grounding.json` now resolves to `answer` with 1 citation,
  the LDL claim grounded and the kidney-function claim dropped; single-topic
  behavior is unchanged; no S1/S2/S3 regressions. Suite went to **40 passed,
  6 skipped**.
- **Today:** Closing out S4 tracking docs (checklist, sprint/phase status,
  reconciliation) and marking R2's local-first/PHI-gate row. Next up: S5
  kickoff (cutover — `/assistant/` served by agent, cache on, flag default
  flip).
- **Blocker:** None for S4 functionally — all three stories are live and
  unit/integration tested, and R-12 is closed. One new reconciliation item
  opened at close-out, not blocking: the mixed golden cases achieve
  `drops_unmapped` by the planner never composing the ungrounded sentence in
  the first place (draft only emits sentences for retrieved evidence),
  rather than by `groundedness.map_sentences` dropping an already-composed
  sentence — so the end-to-end groundedness-DROP path is exercised today
  only by the S3 unit test, not by any golden case. See RECONCILIATION.md
  R-14.

## 2026-06-24 (S3)
- **Yesterday:** S3-1 (advice classifier, `guardrails/classifier.py` — one shared
  instance, called pre-model on the question AND inside the guard on the draft;
  advice-bait questions short-circuit to `escalate` with the fixed
  `ESCALATE_TEMPLATE`, zero tools run, zero generated prose, advice_leakage=0),
  S3-2 (groundedness mapping, `guardrails/groundedness.py` — a sentence survives
  iff it has a citation with a non-empty `source_id`; unmapped sentences dropped
  mechanically; zero survivors → abstain), S3-3 (guard node,
  `guardrails/guard.py` — runs the four-step order advice→groundedness→
  confidence→audit, returns a schema-validated `answer|abstain|escalate`,
  emits `agent.guard`; replaced `graph.py`'s S2 `_passthrough_guard` seam with
  the real guard, and added the pre-model advice gate at the top of
  `run_agent`), and S3-4 (confidence threshold → abstain via the fixed
  `ABSTAIN_TEMPLATE`, no hedging; threshold = the existing faithfulness
  `min_overall_score` (0.6) per PRD §10 Q2, default confidence is 1.0 when
  ≥1 grounded sentence survives with real `source_id`s else 0.0) implemented
  and merged (commit f60e0c1). Suite went to **35 passed, 9 skipped** — zero
  failures, flag-off legacy path untouched.
- **Today:** Closing out S3 tracking docs (checklist, sprint/phase status,
  reconciliation) and marking R2's guard-node backing rows. Next up: S4
  kickoff (PHI redaction gate + offline-verified loop).
- **Blocker:** None for S3 functionally — all four stories are live and unit
  tested. One golden case, `mixed-partial-grounding`, does not yet resolve
  end-to-end through `run_agent`: `nodes/plan.py`'s `_detect_analyte` maps
  "cholesterol" → canonical `"Cholesterol"`, so `query_observations` misses the
  seeded `LDL` row and `check_verification` reports "absent" before the guard
  ever runs — a planner gap, not a guard bug. Captured as a new reconciliation
  item for S4 to fix, alongside the PRD §10 Q2 confidence-threshold choice
  needing client confirmation — see RECONCILIATION.md R-12, R-13.

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
