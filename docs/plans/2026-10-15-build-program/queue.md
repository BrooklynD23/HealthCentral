# Build Program 2026-10-15 — Execution Queue

**Last Updated:** 2026-10-16 (D-2 rev 2: Q1 answered; E-1a spec and ordering)
**Owner:** repository owner
**Status:** PROPOSED (L0 contracts reconciler). This is the single execution queue for lanes A–F. **No owner approval is recorded here**; every gate keeps its state in [owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md).
**Refresh Trigger:** any item below changing status; any merge of #95, #97, #99, #82, #84, #74, #72, #94 or #68; any owner answer to a gate listed here; any edit to [contracts.md](contracts.md).
**Base measured:** `origin/main` @ `3b2236c` (2026-10-15); collected slot 1574.

Rules: [contracts.md](contracts.md) §b (shared files), §c (migrations), §d (count slots). Path shorthand: `be/` = `src/backend/`, `fe/` = `src/frontend/src/`; "slots" = the `CLAUDE.md` / `AGENT.md` collected-count lines, which are exempt from the no-shared-file rule (§b rule 3).

**Scheduling rules**

1. **Code slots:** at most 12 code items run at once (box-wide, all lanes; `build-wave` default `max`; owner cap 30 agents, 2026-10-16). Every pytest run goes through `scripts/pyslot.sh` (3 machine-wide slots on the 22 GiB WSL box). Lane docs that say "at most 2 code L1s" are superseded by this rule.
2. **No shared files:** two items that run at the same time never share a file (slots, `docs/INDEX.md` and `docs/_link_graph.json` excepted).
3. **Waves are dependency layers**, not dates. An item may start in an earlier wave if its dependencies are merged, its execution gates are answered, a slot is free and rules 1–2 hold.
4. **No-slot items** (docs, owner merges, PR landings with no pytest) run beside code items, subject to rule 2.
5. Humans merge, in any order that respects real code dependencies. Slots and the index are updated by L0's post-merge batch (contracts §d, SLOT-RULE-2).

Totals: 51 items. 7 ready now (E-1, E-3, D-0, C-PMIG, E-7, F-3, and B-3 for the next free slot). Waves 6–14 plus a docs tail.


**Owner answers 2026-10-15** ([owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md) rows MM-HOST, S-3 + S-6, Q-RUFF, CI-SEED):
- **E-1:** merge now waits on a new item **E-1a** (close O-3 in `be/modules/redaction.py` for underscore-joined identifiers; ask-first: its diff needs its own owner yes). E-1 may still be built to PR.
- **E-3:** Task 7 uses ruff's full default ruleset, so a cleanup item **E-3a** (repo-wide ruff fixes, many files, runs alone) lands before Task 7. Task 8 Step 4 CI seed is allowed (`seed/<gate>`, no PR, deleted after).
- **MM-1, MM-2, MM-4:** run later on the owner's RTX 3080 machine. B-7, B-4 and B-9 stay needs-model-machine.


**Owner answers 2026-10-16** ([owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md) rows E1A-BUILD, MERGE-AUTH, E1A-REV3, D2-Q1, IBF-1 + SCF-RULING, IUV-1, AAD-ROW, P6-Q1 (+Q4, Q5), P6-Q3, RR500-MAP, SCA-RULING + SCH-RULING):
- **Closed, no code:** SAFE-CHAT-AGENT, SAFE-CHAT-FALLBACK, SAFE-CHAT-HISTORY (option A).
- **Now ready:** B-2 (pin test HC-SIE-001 only), B-6 (option b: omit the unverified value), RAG-RUNTIME-500 (503 + fixed sentence), ASSIST-AGENT-DATES (all four filters), C-P6 (seeded dev vault for Task 1; listener edit in `core/profile_database.py` licensed). B-2, B-6 and RAG-RUNTIME-500 still never run together (shared `api/interpretations.py`).
- **D-2:** owner chose automatic re-learn; blocked until its plan delta (D-2 rev 2) merges.
- **E-1a:** rev 3 approved (qualifier words, `#` / `no.` separators); merge if the diff matches rev 3. E-1 merges after E-1a.
- **Done:** D-1 (#104), D-3 (#109), E-7 (#103), F-3 (#102). Collected 1613 on `527bc22`.


**Status 2026-10-16 (second batch)** (owner row P6-ORPHAN):
- **Merged:** E-1a (#108), E-1 / W-2 (#106), B-2 (#112), C-P6 Task 1 orphan-audit tool (#113), RAG-RUNTIME-500 (#114), D-2 (#115, profile migration `013_adaptive_windows_local`), B-6 (#116). Collected 1683 on `33f42eb`.
- **C-P6 Tasks 2-5:** wait for the owner's real-vault orphan counts (P6-ORPHAN). The FK migration takes the next free revision, `014`.
- **New rows (not yet planned):**
  - **E-1b** (ask-first `modules/redaction.py`): strict misses a parenthesised qualifier (`mrn_(hospital):_…`), `#` / `no.` after a bare label (`patient_#:_…`), and `-` as separator (`mrn_-_…`). Needs a plan and an owner yes.
  - **REDACT-EMAIL-REDOS** (ask-first `modules/redaction.py`): the existing `email` rule is quadratic; `"mrn"+"._"*20000` takes 0.81 s. Needs a plan and an owner yes.
  - **MED-STREAK-GRACE:** the per-medication streak (`api/medications.py:1244`, `modules/adherence_patterns.py:441-449`) still resets each morning and disagrees with the gamification widget (D-3 follow-up). Needs an owner ruling (lane-D Q2).
  - **AUDIT-MISSING-MED:** pre-existing missing audit calls at `api/medications.py:1105` and `api/notifications.py:416` (D-1 follow-up; CLAUDE.md audit-logging invariant).
  - **EXPORT-TODAY-TZ:** `modules/export.py:454` dates the doctor summary with the UTC `today`.

**Status 2026-10-16 (third batch)** (owner rows MM1-RERUN, MERGE-72; TASK_LIST MM-1, MM-3, MM-4):
- **Merged:** W-4 legacy abstain (#72, `cfc1e50`) after MM-1. #61 closed, branch kept (PR61-CLOSE). Collected 1690 on `cfc1e50` (MM-3: `1690 passed` with a real embedding model).
- **Model host:** the owner's RTX 3080 WSL box now runs Ollama 0.40.5 with `gemma4:e4b`, `llama3.1:8b`, `qwen3:8b`, `gemma3:12b` (MM-HOST). Needs-model-machine items (B-7, B-4, B-9) can run there; MM-2 stays blocked on OW-3.
- **New rows (not yet planned):**
  - **LEGACY-CITE-PROMPT** (owner yes, MERGE-72): tighten `RAGModule.SYSTEM_PROMPT` (`be/modules/rag.py:125`): show a `[cite:N]` example on a REPORT FACTS line and forbid references outside the context. G-B5 stays unchanged. Acceptance: re-run the MM-1 script on the four local models and post the counts (MM-1: 15-20/20 abstained, 11-20/20 `Report facts section missing citations`).
  - **CHAT-FACT-ROUTING:** the agent chat answers deterministically without the model. `Is my LDL cholesterol high?` / `Explain my cholesterol results.` abstain with LDL/HDL verified; open questions dump every fact with raw analyte ids and ISO timestamps (MM-4).
  - **INTERP-RENDER:** the interpretation card shows raw `**` markdown and `[KB:uuid]` / `[INT:uuid]` markers, the gauge axis goes negative (`-29.7`), and the footer says `Model: template` after a 19.3 s Ollama call (MM-4).
  - **INTERP-ADVICE-WORDING** (owner review; no-medical-advice invariant): template text `Lifestyle changes and possibly medication may help reduce this risk.` (MM-4).
  - **LOCAL-HF-HUB** (local-first invariant): backend startup logs `You are sending unauthenticated requests to the HF Hub`; embeddings load without `HF_HUB_OFFLINE` (MM-4).
  - **DEV-SH-CC:** `dev.sh` dies when `llama-cpp-python` cannot compile (no C compiler); its pip fallback only drops SQLCipher. Check for a compiler up front or skip it when `LLM_PROVIDER=ollama` (MM-4).
  - **EXTRACT-FORMATS:** the text-PDF parser reads only `Analyte: value unit (range)` lines; a column-layout report gave `0 values extracted`; `mIU/L` is not in the unit list (MM-4).

---

## Wave 6 — start now

| id | lane | kind | depends_on | owner gates | ask-first | files | est h | runtime | status |
|---|---|---|---|---|---|---|---|---|---|
| E-1 | E | PRODUCT (code slot 1) | — | S-3/O-3, S-6 (merge only); O-2 signed | `be/modules/redaction.py` (**called only**, never edited) | `be/tests/test_export_redaction.py`, `be/modules/export.py`, `be/api/export.py`, `docs/plans/2026-09-27-W02-doctor-summary-redaction.md`, slots | 6 | claude | **ready** (merge blocked: S-3, S-6, E-1a merged; on rebase over E-1a, remove the O-3 strict xfail per [E-1a plan](../2026-10-16-E1a-redaction-underscore-phi.md) Task 4) |
| E-3 | E | PRODUCT (code slot 2) | — | Q-RUFF (Task 7), CI-SEED (Task 8 Step 4), Q-COV (threshold only) | — | `.github/workflows/ci.yml`, `be/tests/test_migration_heads.py`, `docs/architecture/ci-and-quality-gates.md`, `docs/features/TASK_LIST.md` (own row), slots | 5 | any | **ready** (Tasks 7 and 8.4 blocked: Q-RUFF, CI-SEED) |
| E-1a | E | PRODUCT (code) | — (not E-1: E-1's merge waits on E-1a, queue `:23`; the O-3 xfail is removed by whichever PR merges second, see spec §Ordering) | S-3 answered "Close the gap first"; the `redaction.py` diff needs its own owner yes before merge | `be/modules/redaction.py` (**edited**) | `be/modules/redaction.py`, `be/tests/test_redaction.py`; `be/tests/test_export_redaction.py` only if E-1 merged first | 3 | claude | **ready** (build to draft PR; merge needs owner yes on the diff). Spec: [E-1a plan](../2026-10-16-E1a-redaction-underscore-phi.md); acceptance: its §Acceptance rows 1–8 |
| E-3a | E | PRODUCT (code, **runs alone**) | — | Q-RUFF answered "Full default ruleset" | none edited (ruff fixes in ask-first files are excluded and listed for the owner) | repo-wide Python under `src/backend/` and `scripts/`, plus `pyproject.toml` / `ruff.toml` | 4 | claude | **ready**; no other code item in the same run |
| D-0 | D | OWNER (no slot) | — | owner merges #95 → #97 → #99 → #82 → #84 | — | slots, `docs/INDEX.md`, `docs/_link_graph.json`, `docs/reviews/README.md` | 2 | claude | **done** 2026-10-16 (#95, #97, #99, #82, #84 merged; main `d64c3fb`, 1604 collected) |
| C-PMIG | C | DOCS (no slot) | — | OW-W13 (optional, R-13) | — | `docs/plans/2026-10-15-build-program/lane-C-schema-lifecycle.md` | 0.5 | any | **ready** (lands with this build-program docs commit) |
| E-7 | E | DOCS (no slot) | — | — | — | `docs/plans/2026-10-09-AUDIT-ORDER.md`, `docs/capstone-report/implementation-program.md` (`:488-489` only) | 0.5 | any | **ready** |
| F-3 | F | DOCS (no slot) | — | — | — | `docs/architecture/README.md`, `docs/architecture/backend.md` | 0.5 | any | **ready** |

The B-3 Codex plan review (R-22) also runs in Wave 6. It is a review, not a code slot.

## Wave 7

| id | lane | kind | depends_on | owner gates | ask-first | files | est h | runtime | status |
|---|---|---|---|---|---|---|---|---|---|
| B-3 | B | PRODUCT (code) | Codex review of §B-3; rebases on #72, #95, W-3, W-8, G-C5, RAG-RUNTIME-500, B-2, B-6 as they land (parked draft, R-5) | PR3-TIER, PR3-S5N (the tasks they govern are skipped until answered, RUNBOOK §4 step 3); merge only after B-4 signed | — | `be/modules/agent/guardrails/advice_judge.py`, `be/modules/rag.py`, `be/api/assistant.py`, `be/api/interpretations.py`, `be/scripts/measure_prohibited_patterns.py`, `be/tests/test_advice_judge.py`, `be/tests/test_rag_pipeline.py`, `be/tests/test_safe_chat_prohibited.py`, `be/tests/test_safe_interp_grounded.py`, `be/tests/test_assist_utc_http.py` (after #95), `be/tests/legacy_eval/harness.py` (after #72), slots | 8 | claude | **ready** for the next free slot; draft until B-4 |
| D-1 | D | PRODUCT (code) | #97, #99 (D-0) | — | — | `be/core/time.py` (append after `:27`), `be/api/medications.py`, `be/api/notifications.py`, `be/modules/notification_scheduler.py`, `be/modules/adherence_patterns.py`, `be/tests/test_time_source.py`, `be/tests/test_medications_routes_http.py`, `be/tests/test_notification_routes_http.py`, `be/tests/test_notification_scheduler_wiring.py`, slots | 4 | claude | blocked: #97, #99 not merged |
| E-4 | E | PRODUCT (landing #74, no slot) | E-3 merged | TW4-SHOTS, #74 merge | — | `docs/INDEX.md`, `docs/_link_graph.json`, `.github/workflows/ci.yml`, `src/frontend/package.json`, `src/frontend/package-lock.json` | 3 | claude | blocked: E-3 (`ci.yml`), TW4-SHOTS |
| F-1 | F | DOCS (no slot) | E-3 merged (`TASK_LIST.md`) | P4D-PIPELINES-127 (commit 2 only) | — | `docs/architecture/pipelines.md`, `docs/features/00_features_index.md`, `docs/features/04_self_improvement_loop.md`, `docs/features/TASK_LIST.md` (`:63` only) | 1 | any | blocked: E-3 running on `TASK_LIST.md` (commit 1 has no gate) |
| F-2 | F | DOCS (no slot) | — | P4D-N10-WORDING | — | `skills/asclexis-guardrails/SKILL.md` | 0.5 | claude | blocked: owner P4D-N10-WORDING |
| G-C5-PLAN | A | DOCS (no slot) | — | Q5b, GC5-PLAN, GC5-MODEL | plan covers `be/modules/verifier_agent.py` | `docs/plans/2026-10-15-build-program/lane-A-rag-assistant.md` (or a new plan file) | 3 | claude | blocked: owner Q5b, GC5-PLAN |

## Wave 8

| id | lane | kind | depends_on | owner gates | ask-first | files | est h | runtime | status |
|---|---|---|---|---|---|---|---|---|---|
| D-2 | D | PRODUCT (code) | D-1 (#104 merged), #97, C-PMIG | Q1 answered 2026-10-16: re-learn automatically (lane D §D-2 rev 2) | — (no `core/auth.py` edit; re-learn runs in the existing scheduler pass) | `be/models/medication.py`, `be/migrations/profile/versions/NNN_adaptive_windows_local.py`, `be/modules/notification_scheduler.py`, `be/modules/adherence_patterns.py`, `be/api/medications.py`, `be/tests/test_notification_scheduler_wiring.py`, `be/tests/test_adherence_patterns_tz_http.py`, head literal (`be/tests/test_care_tasks.py`, `be/tests/test_profile_migrations_sqlcipher_fallback.py`, `be/tests/test_source_spans.py`, or `be/tests/support/migrations.py` after C-P6), slots | 7 | claude | ready |
| D-3 | D | PRODUCT (code) | #84, D-1 | — | — | `be/api/gamification.py`, `be/tests/test_gamification_api.py`, slots | 1 | any | blocked: #84, D-1 |
| E-5 | E | OWNER (measure, no slot) | E-4 | NPM-AUDIT-CI (default: do not add) | — | `docs/capstone-report/implementation-program.md` (own row) | 1 | any | blocked: E-4 |
| F-11 | F | OWNER (`gh pr close 61`, no `--delete-branch`) | #72 merged | PR61-CLOSE answered | — | — | 0.1 | any | blocked: #72 (needs MM-1) |

D-2 and D-3 share no file, so they may hold both slots.

## Wave 9 — gated small-code pool (2 at a time)

Run in the order the owner answers gates. **Never pair:** any two of {RAG-RUNTIME-500, B-2, B-6} (`api/interpretations.py` + test file; contracts §b); B-1 with C-GAM2B (`SettingsPage.tsx`); any two of {ASSIST-AGENT-DATES, SAFE-CHAT-FALLBACK B, SAFE-CHAT-HISTORY B} (`api/assistant.py`); C-GAM2B with D-2 if D-2 is still open (head literal).

| id | lane | kind | depends_on | owner gates | ask-first | files | est h | runtime | status |
|---|---|---|---|---|---|---|---|---|---|
| RAG-RUNTIME-500 | A | PRODUCT | file queue (contracts §b); before B-5 | RR500-MAP | — | `be/api/interpretations.py`, `be/tests/test_safe_interp_grounded.py`, slots | 1 | any | blocked: owner RR500-MAP |
| B-2 | B | PRODUCT | file queue | IBF-1 (asked with SCF-RULING, R-1) | — | `be/tests/test_safe_interp_grounded.py`, slots | 1 | any | blocked: owner IBF-1 |
| B-6 | B | PRODUCT | file queue | IUV-1 (= W-3 O-3) | — | `be/api/interpretations.py`, `be/tests/test_safe_interp_grounded.py`, slots | 1.5 | any | blocked: owner IUV-1 |
| B-1 | B | PRODUCT | #74 (E-4) | BGS-1 | — | `fe/components/settings/ExternalApiBreakGlassWarning.tsx`, `fe/pages/ExplainAssistant.tsx`, `fe/pages/LabInterpreter.tsx`, `fe/pages/SettingsPage.tsx`, `fe/__tests__/ExternalApiBreakGlassWarning.test.tsx` | 2 | any (vitest on Windows/CI) | blocked: E-4; owner BGS-1 |
| C-GAM2B | C | PRODUCT | #84, C-PMIG | GAM2B-PATH (GAM2-PLAN-APPROVAL signed) | — | `be/models/model_settings.py`, `be/migrations/profile/versions/NNN_streaks_hidden.py`, `be/api/model_settings.py`, `be/tests/test_gamification_settings.py`, `be/tests/test_audit_order_guard.py`, head literal (`be/tests/test_care_tasks.py`, `be/tests/test_profile_migrations_sqlcipher_fallback.py`, `be/tests/test_source_spans.py`, or `be/tests/support/migrations.py` after C-P6), `fe/services/modelSettings.ts`, `fe/pages/SettingsPage.tsx`, `fe/components/medication-coach/AchievementsWidget.tsx`, `fe/components/medication-coach/AdherenceDashboard.tsx`, `fe/__tests__/Gamification.test.tsx`, slots | 4 | devin | blocked: #84; owner GAM2B-PATH |
| ASSIST-AGENT-DATES | A | PRODUCT | #95 (merged) | AAD-ROW (all four filters) + AAD-SEMANTICS (ADD), both answered | — | `be/api/assistant.py`, `be/modules/agent/state.py`, `be/modules/agent/graph.py`, `be/modules/agent/cache.py`, `be/modules/agent/nodes/plan.py`, `be/modules/agent/tools/query_observations.py`, `be/modules/agent/tools/compute_trend.py`, `be/modules/agent/tools/retrieve_chunks.py`, `be/tests/test_assist_agent_dates_http.py`, `be/tests/test_audit_order_guard.py` (only if a new unresolved call lands in `_serve_via_agent`), slots | 4 | claude | ready (owner AAD-ROW + AAD-SEMANTICS); PR #119 |
| C-BKUP | C | PRODUCT | — | BKUP-FOLLOWUPS | — | `be/scripts/backup.py`, `be/tests/test_backup.py`, slots | 2 | claude | blocked: owner BKUP-FOLLOWUPS |
| C-VAULTSC | C | PRODUCT (tests) | — | VAULT-SIDECAR | `be/tests/security/test_vault_ciphertext.py` (encryption tests) | `be/tests/security/test_vault_ciphertext.py`, slots | 1.5 | claude | blocked: owner VAULT-SIDECAR |
| C-DUPAUD | C | PRODUCT | — | DUP-AUDIT-KEY | `be/core/audit.py` | `be/core/audit.py`, `be/tests/test_audit_phi_minimization.py`, `be/tests/test_documents_api.py`, slots | 0.5 | any | blocked: owner DUP-AUDIT-KEY; not beside C-P6 |
| D-4 | D | PRODUCT | — | CORRELATION-NORMALISE go | — | `be/monitoring/correlation.py`, `be/tests/monitoring/test_correlation.py`, slots | 0.5 | any | blocked: owner go |
| SAFE-CHAT-AGENT | A | OWNER → PRODUCT if B | — | SCA-RULING (rec. A: close) | — (imports `PROHIBITED_PATTERNS` only) | `be/modules/agent/guardrails/guard.py`, `be/tests/agent/test_guard_prohibited_floor.py` | 1.5 | any | blocked: owner SCA-RULING; no code if A |
| SAFE-CHAT-FALLBACK | A | OWNER → PRODUCT if B/C | — | SCF-RULING (with IBF-1, R-1; rec. A) | — | `be/api/assistant.py` (B), `be/scripts/seed_knowledge_base.py` (C) | 0.5 | any | blocked: owner SCF-RULING; no code if A |
| SAFE-CHAT-HISTORY | A | OWNER → PRODUCT if B | — | SCH-RULING (rec. A) | — | `be/api/assistant.py` | 0.5 | any | blocked: owner SCH-RULING; no code if A |
| B-8 | B | PRODUCT | B-7 (MM-1), #72 | S-C3-2, GC3A-LEDGER | — | `be/tests/support/minimal_pdf.py`, `be/tests/fixtures/extraction_golden/manifest.json`, `be/tests/test_extraction_golden.py`, `docs/agentic/eval-cards/extraction.md`, `docs/agentic/evals.md`, `docs/INDEX.md`, `docs/_link_graph.json`, slots | 5 | codex | blocked: #72 (MM-1); owner S-C3-2, GC3A-LEDGER |
| F-10 | F | DOCS + harness (no slot; count-moving) | #95, #97, #99, #82, #84, #74, #72 merged | PR68-SYNC, HOOKS-COMMIT answered; OW-5 | — | slots, `docs/INDEX.md`, `docs/_link_graph.json`, `docs/capstone-report/owner-decisions-2026-09-27.md`, `docs/features/TASK_LIST.md`, `CS4610_Report_Demo/README.md`, `.gitignore`, `.claude/settings.json`, `.claude/hooks/session_log.py`, `be/tests/test_session_log_hook.py`, `be/tests/test_claude_agent_definitions.py`, `docs/plans/2026-10-10-rsi-loop-applicability-report.md`, `docs/plans/2026-10-10-rsi-audit-handoff-prompt.md` | 1.5 | claude | blocked: #74, #72 (and D-0); merges last of the open-PR set (§d step 7) |

## Wave 10

| id | lane | kind | depends_on | owner gates | ask-first | files | est h | runtime | status |
|---|---|---|---|---|---|---|---|---|---|
| C-P6 | C | PRODUCT (code) | — | D5 signed; P6-Q1, P6-Q3, P6-ORPHAN, P6-Q4, P6-Q5 | `be/core/database.py` (SQLCipher setup; FK pragma edit named by D5), `be/core/profile_database.py`, `be/core/migrations.py`, `be/api/profiles.py` | `be/core/fk_audit.py`, `be/scripts/fk_orphan_audit.py`, `be/migrations/profile/versions/NNN_fk_cascade_alignment.py`, `be/models/document_category.py`, `be/models/care_plan_task.py`, `be/models/observation.py`, `be/core/database.py`, `be/core/profile_database.py`, `be/core/migrations.py`, `be/migrations/profile/env.py`, `be/api/profiles.py`, `be/tests/support/migrations.py`, `be/tests/support/db.py`, `be/tests/test_fk_audit.py`, `be/tests/test_fk_migration_013.py` (rename to its real number), `be/tests/test_fk_enforcement.py`, `be/tests/test_care_tasks.py`, `be/tests/test_profile_migrations_sqlcipher_fallback.py`, `be/tests/test_source_spans.py`, `be/tests/test_profile_deletion.py`, `be/tests/test_documents_api.py`, `docs/features/TASK_LIST.md` (own row), slots | 7 | claude | blocked: owner P6-Q1, P6-Q3 (then P6-ORPHAN after the Task 1 report) |
| W-3 | A | PRODUCT (code) | #72, #95, E-4 (#74) before Task 5; B-3 either order (R-2) | O-5 (Task 3), O-1 = VERIFIED-FALLBACK (Task 7), O-2 veto (Task 6) | — | `be/api/observations.py`, `be/modules/rag.py`, `be/api/assistant.py`, `fe/services/types.ts`, `fe/pages/TrendsDashboard.tsx`, `fe/components/lab-interpreter/InterpretedTrendChart.tsx`, `fe/components/TrendVerificationMarkers.tsx`, `fe/__tests__/TrendsDashboard.test.tsx`, `fe/__tests__/TrendVerificationMarkers.test.tsx`, `fe/__tests__/InterpretedTrendChart.test.tsx`, `be/tests/test_verified_only_consumers.py`, slots | 6 | claude (vitest on Windows/CI) | blocked: #72 (MM-1), E-4; owner O-5, O-1, O-2 |

## Wave 11

| id | lane | kind | depends_on | owner gates | ask-first | files | est h | runtime | status |
|---|---|---|---|---|---|---|---|---|---|
| C-P7 | C | PRODUCT (code) | C-P6 | P7-ROUTE, RESET-AUDIT-OWNER signed; N-02 | `be/api/profiles.py` | `be/api/profiles.py`, `be/tests/support/routes.py`, `be/tests/test_profile_test_reset.py`, slots | 2 | codex | blocked: C-P6; owner N-02 |
| W-8 | A | PRODUCT (code) | W-3, E-3, #72; last on `ci.yml` | Q-FC, Q-HASH, VERIFIED-FALLBACK (= O-1); Q-OFFLINE and EMB-REV answered | — | `be/modules/embeddings.py`, `be/core/config.py`, `.gitignore`, `config/.env.example`, `be/scripts/download_models.py`, `.github/workflows/ci.yml`, `be/modules/rag.py`, `be/api/documents.py`, `be/tests/test_embedding_bundle.py`, `be/tests/test_embedding_fail_closed_paths.py`, `docs/capstone-report/architecture-engineering-contract.md`, `docs/capstone-report/specs-compliance-matrix.md`, `docs/capstone-report/architecture-overview.md`, `docs/capstone-report/claims-ledger.md`, `docs/architecture/ci-and-quality-gates.md`, `docs/architecture/performance-scalability-review.md`, slots | 8 | claude (Task 4 needs one network fetch on the owner host or CI) | blocked: W-3; owner Q-FC, Q-HASH |

## Wave 12

| id | lane | kind | depends_on | owner gates | ask-first | files | est h | runtime | status |
|---|---|---|---|---|---|---|---|---|---|
| E-2 | E | PRODUCT (code) | C-P6, C-P7 | OG-1, Q-AUD-LIST | `be/api/profiles.py` | `be/tests/test_profile_route_guards.py`, `be/tests/test_profile_route_audit.py`, `be/tests/support/master_db.py`, `be/tests/support/routes.py`, `be/tests/test_audit_order_guard.py`, `be/api/profiles.py`, slots | 8 | claude | blocked: C-P7; owner OG-1, Q-AUD-LIST |
| G-C5 | A | PRODUCT (code) | G-C5-PLAN, W-8 (if Q5b = A), #72; last on `rag.py` | GC5-ASKFIRST (`verifier_agent.py:304-317`), Q5a, plus open questions (absent model with flag on; ModelRunner applicability) | `be/modules/verifier_agent.py` | `be/modules/verifier_agent.py`, `be/modules/rag.py`, `be/api/assistant.py`, `be/modules/embeddings.py`, `be/scripts/download_models.py`, `config/model_manifest.json`, `be/core/config.py`, `config/.env.example`, `be/tests/test_gc5_nli_flag.py`, slots | 6 | claude (+ Codex, security review) | blocked: G-C5-PLAN, W-8; owner GC5-ASKFIRST, Q5a |

## Wave 13

| id | lane | kind | depends_on | owner gates | ask-first | files | est h | runtime | status |
|---|---|---|---|---|---|---|---|---|---|
| B-5 | B | PRODUCT (code) | B-3 merged, B-2, last in the `api/interpretations.py` queue (after RAG-RUNTIME-500, B-6); P6/P7 dropped (R-6) | W7-SPILL, IBF-1 | — | `docs/plans/2026-09-27-W07-tiered-interpretation-via-modelrunner.md`, `be/modules/interpret.py`, `be/modules/model_selector.py`, `be/api/interpretations.py`, `be/tests/test_llm_import_boundary.py`, `be/tests/test_interpret_tiered.py`, `be/tests/test_audit_order_guard.py`, slots | 10 | claude (+ Codex round) | blocked: B-3 merge (B-4/MM-2); owner W7-SPILL, IBF-1 |

The second slot takes any Wave 9 leftover that shares no file with B-5 (so not RAG-RUNTIME-500, B-2 or B-6).

## Wave 14

| id | lane | kind | depends_on | owner gates | ask-first | files | est h | runtime | status |
|---|---|---|---|---|---|---|---|---|---|
| C-GC1 | C | PRODUCT (code) | E-1, C-P6, C-P7 | S-C1-1, S-C1-2, RESET-APPEND | `be/api/profiles.py` | `be/models/export_artifact.py`, `be/models/__init__.py`, `be/migrations/profile/versions/NNN_export_artifacts.py`, `be/api/export.py`, `be/api/pinboards.py`, `be/api/profiles.py`, `be/tests/test_export_artifact_persistence.py`, `be/tests/test_visit_prep_packet.py`, `be/tests/test_fhir_export.py`, `be/tests/test_audit_order_guard.py`, `be/tests/support/migrations.py`, slots | 6 | claude (+ Codex, security review) | blocked: E-1 merge, C-P7; owner S-C1-1, S-C1-2 |

C-GC1, E-2 and B-5 all edit `be/tests/test_audit_order_guard.py`, and C-GC1 and E-2 also share `be/api/profiles.py`, so each gets its own wave (R-9). If B-5 is ready first, B-5 and C-GC1 swap waves; they still never run together.

## Docs tail (no slot; fires on triggers)

| id | lane | kind | depends_on | owner gates | ask-first | files | est h | runtime | status |
|---|---|---|---|---|---|---|---|---|---|
| F-5 | F | DOCS | F-1, F-3; one PR per trigger: F1 ← W-3, F2 ← E-1, F3 ← B-5, F4 ← #72, F5 ← W-8 (contracts I-22) | — | — | `docs/architecture/pipelines.md`, `docs/architecture/README.md`, `docs/architecture/backend.md`, `docs/architecture/ci-and-quality-gates.md` | 2.5 | any | blocked: each trigger returns 0 hits today |
| F-6 | F | DOCS | E-1, W-3 merged with Variant-I PR bodies (I-21) | W10B-RC, W10B-SPLIT, W10B-D4-EXTRAS, S6 stop gate | — | `docs/compliance/data-privacy.md` | 1.5 | claude | blocked: E-1, W-3; owner W10B-* |
| F-13 | F | DOCS | #94 merged, F-1 | — | — | `docs/features/TASK_LIST.md` (own `OW-W*` subsection + OM-1/OM-2/OW-W5 notes only) | 0.5 | any | blocked: #94 |
| F-9 | F | DOCS + demo | F-10, W-8 (`claims-ledger.md`) | SHOW-DATE, SHOW-AUDIT, O-1…O-7 | — | `docs/plans/2026-09-27-senior-report-showcase-plan.md`, `docs/capstone-report/claims-ledger.md`, `CS4610_Report_Demo/README.md`, `docs/reviews/reviewer-log.tsv` | 8 | claude | blocked: F-10, W-8; owner SHOW-DATE, SHOW-AUDIT |

---

## Owner-blocked and model-machine items

### Owner or model-machine work items

| id | lane | what | depends_on | gates | unblocks | runtime | status |
|---|---|---|---|---|---|---|---|
| B-7 (MM-1) | B | W-4 20-question real-model count on #72 | — | W4-20Q-HOST answered (owner runs it) | #72 merge → W-3, W-8, B-8, G-C5, F-11, F-5 F4, F-10 | any (model machine) | needs-model-machine |
| B-4 (OW-3 → MM-2) | B | sealed set S5, judge measurement, owner signs numbers | B-3 PR head frozen as a draft | OW-3, sign-off on 2s / 90% / 5% / tier-2 | B-3 merge → B-5 → F-5 F3 | any (model machine) | blocked: B-3 draft; owner OW-3 |
| B-9 (MM-3, MM-4) | B | full suite with an embedding model; real-app smoke | B-3 (MM-4 judge check); **not** F-13 (R-11) | — | evidence only | any (model machine) | needs-model-machine |
| E-6 | E | W-1 `/agents` runtime smoke | F-10 only for the optional test edit | W1-SMOKE-RUN | `docs/agentic/harness.md` claim; optional `be/tests/test_claude_agent_definitions.py` fix | claude | blocked: owner W1-SMOKE-RUN |
| F-4 | F | `docs/compliance/hipaa-controls.md:169` key-rotation row | — | P8-B2-ORDER | — | any | blocked: owner |
| F-7 | F | G-C2 OpenWiki run + review (`openwiki/README.md`, `AGENT.md`, `docs/00_architecture_plans_index.md`, `docs/INDEX.md`, `docs/_link_graph.json`) | — | G-C2-DEFER in force; S-C2-1…3, GC2-CLAUDE-66, OW-4 | OpenWiki navigation | claude | blocked: owner |
| F-8 | F | RTN nightly doc-drift routine (`docs/plans/2026-09-27-nightly-doc-drift-routine-spec.md`) | — | RTN §9 Q1–Q6 | routine creation | claude | blocked: owner |
| F-12 | F | wearables (#94) consumer map; no code | #94 merged | M0, OW-W0, OW-W3, OW-W6…OW-W13, RESET-APPEND | all WEAR code waves | claude | blocked: owner M0, #94 merge |

### Owner questions, grouped for asking (at most 4 per prompt, orchestration §2 step 3)

| Prompt | Gates | Unblocks |
|---|---|---|
| 1 (now) | S-3/O-3 + S-6 (one question), Q-RUFF, CI-SEED, R-5 parked-draft veto | E-1 merge; E-3 Tasks 7 and 8.4; B-3 draft rule |
| 2 | P4D-PIPELINES-127, P4D-N10-WORDING, BGS-1 (TW4-SHOTS is already answered, `owner-decisions:140`: the owner compares the screenshots; E-4 waits on that action, not a question) | E-4 → E-5, B-1, W-3 Task 5; F-1 commit 2; F-2 |
| 3 (safety rulings) | IBF-1 + SCF-RULING (one question, R-1), IUV-1 (= W-3 O-3, R-7), RR500-MAP, PR3-TIER + PR3-S5N | B-2, SAFE-CHAT-FALLBACK, B-6, RAG-RUNTIME-500, B-3/B-4 |
| 4 | ~~D-2 Q1~~ (answered 2026-10-16), GAM2B-PATH, AAD-ROW (+ scope), CORRELATION-NORMALISE | D-2, C-GAM2B, ASSIST-AGENT-DATES, D-4 |
| 5 | BKUP-FOLLOWUPS, VAULT-SIDECAR, DUP-AUDIT-KEY, SCA-RULING + SCH-RULING | C-BKUP, C-VAULTSC, C-DUPAUD, SAFE-CHAT-AGENT/HISTORY |
| 6 | P6-Q1, P6-Q3, P6-Q4 + P6-Q5, N-02 | C-P6 Task 1 → P6-ORPHAN → C-P7 |
| 7 | O-5, O-1 (= VERIFIED-FALLBACK), O-2 veto, Q-FC + Q-HASH | W-3, W-8 |
| 8 | OG-1, Q-AUD-LIST, S-C1-1 + S-C1-2, RESET-APPEND | E-2, C-GC1, WEAR reset rows |
| 9 | Q5b + GC5-PLAN + GC5-MODEL, Q5a, W7-SPILL, S-C3-2 + GC3A-LEDGER | G-C5-PLAN → G-C5; B-5; B-8 |
| later | GC5-ASKFIRST (after the plan exists), P6-ORPHAN (after the Task 1 report), NPM-AUDIT-CI, W1-SMOKE-RUN, P8-B2-ORDER, W10B-*, RTN §9, SHOW-*, M0 + OW-W*, OW-W13 (optional, R-13), GATE-12 conftest item (contracts §e owner list 5) | E-5, E-6, F-4, F-6, F-8, F-9, F-12 |

Back to: [contracts](contracts.md) · [implementation program](../../capstone-report/implementation-program.md)
