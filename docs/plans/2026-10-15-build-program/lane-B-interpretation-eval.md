# Lane B — Interpretation and Eval

**Last Updated:** 2026-10-17 (INTERP-RENDER, EXTRACT-FORMATS planned)
**Status:** DESIGN ONLY. Nothing here is implemented, signed or approved. No owner approval is recorded by this doc; every gate below is open unless it cites a row in [owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md).
**Base:** `origin/main` = `3b2236c` (2026-10-15), worktree `hc-wave6-design`. Open PRs assumed to merge as-is: #95, #97, #99, #82, #84, #94, #74, #72, #68, #61.
**Collected-count slot on main:** `CLAUDE.md:30` and `:34` read **1574**; `AGENT.md:76` reads 1574. The orchestrator's "1501" is the slot on PR #95's branch, not main. Every count-changing PR in this lane re-measures with `--collect-only` and rewrites those three tokens (SLOT-RULE). Not re-run here (12 GB box rule).
**Ask-first files:** no item edits `modules/interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py` or `core/auth.py`. B-3 and B-5 add model-prose checks *beside* `interpret_safety`; they read `InterpretationSafetyGuard` only through existing call sites.

## Items

| ID | Item | Kind | Source | Readiness | Depends on |
|---|---|---|---|---|---|
| B-1 | BG-WARN-STALE | PRODUCT (frontend) | [program](../../capstone-report/implementation-program.md) owner-item row BG-WARN-STALE; owner W6-STALE-WARN (`owner-decisions:47`) | ready (BGS-1 answered (a), `owner-decisions:207`) | #74 merged (same 3 pages) |
| B-2 | SAFE-INTERP-EMBEDDED (+ W-7 prohibited-draft fallback) | PRODUCT (test) or DOCS (close) | `wave-3-L1-A.md:249,254`; W-7 pack Q1 | blocked-on-owner (IBF-1) | — |
| B-3 | PARA-1-R3 implementation: `advice_judge` | PRODUCT (safety) | [PARA-1-R3 plan](../../../audit/2026-09-25/waves/scaffold/PARA-1-R3.md) (PR #62); PARA-R3-Q1, Q2Q3, Q4Q5, Q6, Q7, Q8 (`owner-decisions:107,117-120,124`) | ready to code; merge blocked on B-4 | Codex review of §B-3 below; #72 if it merges first (harness) |
| B-4 | OW-3 sealed set S5 → MM-2 judge measurement → owner signs numbers | OWNER + model machine | `TASK_LIST.md:83,91` | blocked-on-owner, then needs-model-machine | B-3 PR head frozen |
| B-5 | W-7 tiered interpretation via ModelRunner | PRODUCT | [W07 plan](../2026-09-27-W07-tiered-interpretation-via-modelrunner.md); [W-7 pack](../../../audit/2026-09-25/waves/scaffold/W-7.md) | blocked-on-item | B-3 merged, IBF-1, plan amendment + Codex round (P6/P7 dropped as hard deps: [contracts](contracts.md#e-rulings-on-peer-review-conflicts) R-6) |
| B-6 | INTERP-UNVERIFIED | PRODUCT | program owner-item row; W-3 plan O-3 (`W03:1332`) | blocked-on-owner (IUV-1) | none for the grounded route; B-5 for the tiered route |
| B-7 | MM-1: W-4 20-question real-model count | OWNER + model machine | `TASK_LIST.md:82`; W4-OQ-2, W4-20Q-HOST (`owner-decisions:105,136`) | needs-model-machine | — |
| B-8 | G-C3a HC-M06 extraction eval card | PRODUCT (tests + doc) | [W11b plan](../2026-09-27-W11b-roadmap-items-gc1-gc4.md) `:1214-1525`; [G-C3a pack](../../../audit/2026-09-25/waves/scaffold/G-C3a.md) | blocked-on-PR (#72) + owner (S-C3-2) | B-7 → #72 merged |
| B-9 | MM-3 full suite with embedding model; MM-4 real-app smoke | OWNER + model machine | `TASK_LIST.md:84-85` | needs-model-machine | MM-4 after B-3 (and B-5 if merged) |
| INTERP-RENDER | interpretation card: raw `**`, `[KB:]`/`[INT:]` markers, negative gauge axis, footer label | PRODUCT (frontend) | queue status 2026-10-16 third batch (MM-4) | ready (footer task: IR-FOOTER) | — |
| EXTRACT-FORMATS | text-PDF parser: column layouts, missing units, table-page fallthrough | PRODUCT | queue status 2026-10-16 third batch (MM-4) | ready | — (EXF-SAMPLE optional) |
| GRADE-PATTERN-REDOS | pathology `GRADE_PATTERN` cubic on whitespace runs | PRODUCT | PR #212 review MINOR; recurring-failures #9 | build allowed, merge blocked on GRADE-REDOS-DIFF ([below](#grade-pattern-redos--the-pathology-grade_pattern-is-cubic-on-whitespace-runs)) | GRADE-REDOS-DIFF (merge only) |

Order: B-1, B-2 and B-6 are owner questions that can be asked now. B-3 codes in parallel. B-7 unblocks B-8. B-5 is last: it needs B-3's judge and B-2's ruling.

## B-1 BG-WARN-STALE

**Goal.** When the external-API status is unknown (query error, or `use_external_api === true` with no `redaction_break_glass` field), the page says so. Today it shows nothing.

**Main today.** The component renders only when `active === true` (`src/frontend/src/components/settings/ExternalApiBreakGlassWarning.tsx:15-16`). Callers: `pages/ExplainAssistant.tsx:475-477`, `pages/LabInterpreter.tsx:194-195` (BG-WARN-INTERP, PR #59), `pages/SettingsPage.tsx:681`. Hook `useExternalApiSettings` has `staleTime: 30_000` (`services/modelSettings.ts:242-247`). HC-EXT-003c pins "absent flag → nothing" (`__tests__/ExternalApiBreakGlassWarning.test.tsx:28`). HC-EXT-005c pins the same at page level on the chat page: with `use_external_api: true` and no flag it asserts `queryByText(/privacy protection override is on/i)` is null (`__tests__/ExplainAssistant.test.tsx:617-623`). The BGS-1 copy contains that phrase, so the notice this item adds for exactly that case fails it.

**Design (option a).**
1. Component gains `unknown?: boolean`. `active === true` wins; else `unknown === true` renders a `role="status"` notice with owner-approved copy (BGS-1); else nothing. HC-EXT-003c stays green unchanged.
2. Each of the 3 pages passes `unknown={isError || (data?.use_external_api === true && data.redaction_break_glass === undefined)}` from the same hook call it already makes.
3. Server side unchanged: audit and refusal already apply (W6-STALE-WARN).

**Test first.** `HC-EXT-003d` (component, `unknown` → status text, no alert); `HC-EXT-003e` (LabInterpreter with the hook mocked to `isError: true` → notice present); `HC-EXT-003f` (component, `active` and `unknown` both true → only the alert, no status; pins Design 1 "`active === true` wins"). `HC-EXT-005c` keeps its id and setup (external API on, no flag) and changes its assertion: the `role="status"` notice with the BGS-1 copy is present, and `queryByRole('alert')` is null. Absence asserted synchronously (recurring-failures #1). Observe all four RED, then GREEN.

**Plan delta (2026-10-17, PR #134 Task 0 block).** Run 1 stopped because the formula in Design 2 fails HC-EXT-005c, and that test file was not on the file list. The formula is the signed scope: the Goal and BGS-1 (a) both name the "external API on, no flag" case, and the copy is owner-approved, so neither changes. HC-EXT-005c pinned the pre-BGS-1 page behaviour that this item exists to change. Its guarantee (no alert on an older backend) is kept and asserted by role instead of a substring the new copy shares; the new positive check makes it stricter. Only that one test changes in `ExplainAssistant.test.tsx`. HC-EXT-005, 005b and 005d stay unchanged: `unknown` is false in each. Measured on the run-1 working tree (formula applied, not committed): `npx vitest run` over ExternalApiBreakGlassWarning, LabInterpreter, ExplainAssistant, ExplainAssistantHistoryRestore, CitationDeepLink, Accessibility and ModelSettingsService → `Tests  1 failed | 57 passed (58)`; the one failure is HC-EXT-005c. Expected delta: backend collected **0**; frontend vitest **+3** (003d, 003e, 003f; 005c is rewritten, not added).

**Acceptance.** `cd src/frontend && npx tsc --noEmit && npx vitest run src/__tests__/ExternalApiBreakGlassWarning.test.tsx src/__tests__/LabInterpreter*.test.tsx src/__tests__/ExplainAssistant.test.tsx`; full vitest in CI (WSL stall rule). Backend collected unchanged.

**Rollback.** Revert the one commit; no data or schema.

**Files.** `src/frontend/src/components/settings/ExternalApiBreakGlassWarning.tsx`, `src/frontend/src/pages/{ExplainAssistant,LabInterpreter,SettingsPage}.tsx`, `src/frontend/src/__tests__/ExternalApiBreakGlassWarning.test.tsx`, `src/frontend/src/__tests__/ExplainAssistant.test.tsx` (HC-EXT-005c only; plan delta 2026-10-17). Rebase after #74 (Tailwind 4 edits all 3 pages, class-only).

## B-2 SAFE-INTERP-EMBEDDED (decided together with W-7's fallback)

**Main today.** On a prohibited match the grounded route swaps segments, `full_response` and verification for `ESCALATE_TEMPLATE` (`api/interpretations.py:576-592`) but still returns `interpretation=InterpretationResponse.from_model(interp_result.interpretation)` (`:595`). That field is the deterministic template/KB interpretation, persisted by `interpret_observation` and served unchanged by `POST /interpret` (`:375`) and `GET /interpretation` (`:606`). It is never model prose (`wave-3-L1-A.md:248`). 7 of 60 seeded KB fields match a prohibited pattern, all false positives (`:249`).

**Why it is one decision with W-7.** W-7's planned fallback for a prohibited LLM draft is the same template text (W07 plan Review Focus 2). PARA-1 was meant to resolve this item; PARA-1-R3 superseded PARA-1 and moves recall to model answers only, so the item has no resolver.

**IBF-1 options.**
- (a) **Close as accepted (recommended).** On a blocked model answer the response may carry the deterministic template interpretation. Stripping it from one route hides nothing: two other routes serve the same text. W-7 keeps its planned template fallback. Add one pin test `HC-SIE-001` in `tests/test_safe_interp_grounded.py`: prohibited grounded answer → `full_response == ESCALATE_TEMPLATE` and `interpretation.interpretation_text` equals the persisted `LabInterpretation` text, never the model answer.
- (b) Blocked responses carry `ESCALATE_TEMPLATE` only: `interpretation` becomes optional and `None` on block (response-model change, `LabInterpreter.tsx` must handle it); W-7 persists nothing on block. Larger; the template text still shows on the other two routes.
- (c) KB content review: rewrite the 7 KB fields (seed data), not code. Can sit beside (a). Same 7 fields as lane A SAFE-CHAT-FALLBACK option C (`scripts/seed_knowledge_base.py`); lane A owns that file, so (c) is asked once, as SCF-RULING C (Peer review P-4).

**Acceptance (a).** `pytest tests/test_safe_interp_grounded.py -q -p no:cacheprovider` → all passed, one more than before; collected +1. Break-it: return `rag_result` text in `interpretation` → HC-SIE-001 FAIL.

## B-3 PARA-1-R3 implementation: `advice_judge`

The merged plan stands. Delta only: what moved on main, what the owner fixed, what is still open.

**Owner answers now binding** (all quoted from owner-decisions): Q1 "C: local answer judge" (`:107`); Q2/Q3 "Fail closed" (`:117`); Q6 "Owner writes and holds it" (`:118`); Q7 "Reuse ESCALATE_TEMPLATE" (`:119`); Q8 "No, new answers only" (`:120`); Q4/Q5 "2s / 90% / 5% / tier-2" (`:124`).

**Anchor delta (main `3b2236c`; after #95 and #72).**

| Plan anchor | Main now | After open PRs | Verdict |
|---|---|---|---|
| seam `modules/rag.py:1276` | `:1276` | `:1276` (#95 adds lines above, net 0 here) | MATCH |
| `ValidatedResponse` `rag.py:103`, flag `:113` | `:101-113` | `:117-127` (#95) | MOVED by #95; anchor on `class ValidatedResponse` |
| `_generate_with_runner` | `:1280` | `:1280` | MATCH |
| chat audit reason `api/assistant.py:891` | `:898` | `:932` (#72) | MOVED |
| grounded audit reason `api/interpretations.py:552` | `:591` | `:591` | MOVED (PR #78 AUDIT-ORDER) |
| `get_model_runner` `core/model_runner.py:239` | `:239` | — | MATCH |
| `LlamaCppProvider` `wait_for` `:277-280`, no `Lock` | `:277`; 0 `Lock` | — | MATCH (R-7 stands) |
| harness `src/backend/scripts/measure_prohibited_patterns.py` | flags `:206-213`, no `--judge` | — | `--judge` still to add |

**Design (unchanged from plan §3 C, §7).**
1. New `src/backend/modules/agent/guardrails/advice_judge.py`: `FROZEN_PROMPT`, `async def advice_judge(text: str, runner: ModelRunner) -> Literal["ALLOW", "BLOCK", "UNAVAILABLE"]`. `InferenceConfig(max_tokens=3, temperature=0.0, timeout_seconds=2)` (Q4 bound 2 s p95; the L1 measures before it is fixed). Whole-response exact match, `finish_reason in {"stop", "length"}`; everything else, and `runner.is_available() is False`, → `UNAVAILABLE`.
2. `modules/rag.py`: `ValidatedResponse.prohibited_reason: str = "prohibited_pattern"`; `query(..., judge_runner=None)`; after `:1276`, if the floor did not fire, `judge_runner or get_model_runner()` (never `model_runner`) is called and a non-`ALLOW` sets `prohibited_advice=True` with `prohibited_reason` `"advice_judge"` or `"advice_judge_unavailable"` (`dataclasses.replace`).
3. `api/assistant.py` and `api/interpretations.py`: audit `details.reason = rag_result.prohibited_reason` at the two lines above. No answer or question text.
4. `measure_prohibited_patterns.py --judge`: runs the frozen judge over a given file with `HF_HUB_OFFLINE=1`, prints the §6 metric table, the tier, the GGUF sha256 and the commit sha.

**Tests (plan §7, IDs `HC-PARA-101…107`; the existing `test_hc_para_00N` set is untouched).** T1 parser, T2 local-only (external fake never sees the judge prompt), T3 chat over HTTP via `tests/support/routes.py::route_client`, T4 grounded route over HTTP, T5 floor-OR (break-it: make it AND → FAIL), T6 unavailable → blocked, T7 `timeout 600 python3 scripts/agent_eval_gate.py` → `All 74 golden cases passed.` Expected collected delta ≈ +12 (T1 parametrized); measured at commit.

**Delta the plan did not have.**
- **D-1 Existing RAG tests.** At least 10 test files fake the runner (`git grep -ln "_generate_with_runner\|generate_async" -- src/backend/tests`). With no local model in CI, the default judge returns `UNAVAILABLE` and fails closed. Each failing test gets an explicit `ALLOW` judge fake; no blanket bypass flag (plan §7). Record the RED list in the PR. Re-take the RED list at the final rebase: peer tests that reach `rag.query` with a faked runner join it. Known now: #95 `tests/test_assist_utc_http.py` patches `modules.rag.get_model_runner` (`:98`), so the default judge gets that fake and returns `UNAVAILABLE`; plus whatever W-3, W-8, G-C5, RAG-RUNTIME-500, B-2 and B-6 add (Peer review P-3).
- **D-2 W-4 legacy gate.** If #72 merges first, `src/backend/tests/legacy_eval/harness.py` must inject an `ALLOW` judge, or the 2 answer cases abstain/escalate and `legacy-evals` goes red for the wrong reason. `escalate-prohibited-advice.json` must still escalate via the floor.
- **D-3 Tier rule (Q4/Q5 "tier-2").** The local runner loads whatever GGUF it finds; it has no tier (W-7 OG-1). Only the `low` tier has a fixed filename (`modules/model_selector.py:53-55`); every other tier is `filename: None` + pattern `q4_k_m` (`:62-130`). A runtime allowlist of "mid or above" would fail closed for every user today. Open: owner gate PR3-TIER.
- **D-4 S5 size.** Plan §6 asks ≥180 must-block / ≥200 must-allow (±5 points at 85 %). The owner's Q6 text says "about 40-60 labeled examples" (`:118`). At 50 items the 90 % recall target carries about ±8 points (Wilson 95 %). Open: owner gate PR3-S5N.
- **D-5 Ship rule.** Plan §10 step 4: "Nothing ships to users until the owner signs the numbers." Smallest way: the PR stays draft; its head is the freeze sha; it merges only after B-4. No feature flag.
- **D-6 Execution plan record.** Plan §10 step 1 asks for a plan file with the owner's answers verbatim. This section is that record; a Codex plan review of it is owed before code (orchestration §5; model order "6.1 sol" then "6-luna high").

**Acceptance.** `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_advice_judge.py tests/test_safe_chat_prohibited.py tests/test_safe_interp_grounded.py tests/test_prohibited_patterns_regression.py tests/test_interpret_safety_adversarial.py tests/test_rag_pipeline.py -q -p no:cacheprovider`; `grep -n llama_cpp src/backend/modules/agent/guardrails/advice_judge.py` → 0; full suite under `flock`; CI 6/6.

**Rollback.** Revert the merge commit: `prohibited_reason` has a default, no migration, no stored data.

## B-4 OW-3 → MM-2 → numbers

1. Freeze: B-3 PR head sha, `FROZEN_PROMPT`, parser, tier list (plan §6 step 1). Committed in the PR. A rebase after MM-2 (other lanes land on `rag.py` / `api/assistant.py` first) keeps the measurement only if `git diff <freeze-sha> HEAD -- src/backend/modules/agent/guardrails/advice_judge.py src/backend/scripts/measure_prohibited_patterns.py` is empty and the `rag.py` seam hunk is unchanged; otherwise MM-2 re-runs (Peer review P-2; part of the Codex review of §B-3).
2. OW-3: owner writes S5 outside every worktree; commits only its sha256 and counts (plan §6 step 3).
3. MM-2 on a model machine: `cd src/backend && HF_HUB_OFFLINE=1 python scripts/measure_prohibited_patterns.py --judge <S5 path>` twice (agreement), per tier; plus R capture (plan §6). Record tier, GGUF sha256, commit sha, p50/p95 latency with 2 concurrent requests (R-7).
4. Owner compares to 2 s / 90 % / 5 % / tier-2 and signs or rejects. Reject → plan fallback: option B for the grounded route only.

## B-5 W-7 tiered interpretation (delta)

The W07 plan stands except where listed. It must not be dispatched unamended (recurring-failures §8).

**Dependencies now.** P1 met. P5 **met** (PR #54; `utcnow` at `model_selector.py:24`, `api/interpretations.py:23`). P6 **not** met (`git grep foreign_keys src/backend/core` → 0). P7 **not** met. W-7 only reads `route_client` (`tests/support/routes.py:27`). L0 ruling R-6 (contracts): P6/P7 are no longer hard dependencies; the plan amendment changes W07 Task 0's ancestry check to P1 + P5 and keeps the re-read of the `route_client` signature at start. **New:** B-3 merged, because the tiered route is a third model-prose surface that does not pass `rag.py:1276` (PARA-1-R3 plan R-6).

**Anchor delta.**

| Plan anchor | Main `3b2236c` | Change |
|---|---|---|
| `model_selector.py:456` `from llama_cpp import Llama` | `:457` | +1 |
| methods to delete `:437-570` | `load_model :438`, `load_model_async :481`, `get_model_for_inference :507`, `run_inference :539` (ends before `list_downloaded_models :573`) | +1/+2 |
| state `:206-211` | `_loaded_model :207`, `_current_tier :208`, `_load_lock :212` | +1 |
| `interpret.py` `:877`, `:903`, `:761` | `:877`, `:903`, `:761` | MATCH |
| `llama_cpp` import sites | exactly 2: `core/llm/llama_cpp_provider.py:36`, `model_selector.py:457` | MATCH |
| `api/interpretations.py` "0 audit calls" (Task 0 item 5, F-3, Stop gate) | helper `_audit_interpretation :38` with `intent=` (PR #78); 7 routes audited | **CHANGED**: drop F-3 / OG-3 |
| Task 3 import "add `from core.audit import audit_and_commit, log_observation_event`" | `:22` already `from core.audit import audit_and_commit, audit_intent, create_audit_log` | use the helper; no new import |
| insert after grounded route "ends `:505`", before `get_interpretation :508` | grounded `:448-603`, `get_interpretation :606` | +98 |
| collected slots | `CLAUDE.md:30,34`, `AGENT.md:76` = 1574 | re-measure |

**Amendments (plan edits in the W-7 PR's first commit).**
1. Audit: the new route calls `_audit_interpretation(master_db, "tiered", ...)` with the AUDIT-ORDER pattern the grounded route uses (`intent="started"` on a regenerate of an existing row, `intent="completed"` after). Assert a persisted audit row, not a mocked call (recurring-failures §1). Break-it row "Delete the `audit_and_commit(...)` call" becomes "Delete the `_audit_interpretation(..., "tiered")` call".
2. Judge: in `_llm_interpretation`, after the `interpret_safety` check passes, `await advice_judge(draft, self._model_runner)`; non-`ALLOW` → template fallback, labelled `template` (HC-INT-012). New test `HC-INT-018` (judge `BLOCK` → template text, not the draft) and `HC-INT-019` (judge `UNAVAILABLE` → template). The local runner is the only runner here, so T2-style privacy holds by construction.
3. Fallback text per IBF-1 (template if (a)).
4. Drop OG-3 (done by PR #48). OG-1 and OG-2 stay unlicensed and out of scope; the OG-2 spill-over (one row per observation) still needs the owner's acknowledgement (W7-SPILL).
5. Codex plan round after the amendments (plan header: "not re-reviewed").

**HC-AUD-ORD-030.** The new committing handler `generate_tiered_interpretation` must get a row in `tests/test_audit_order_guard.py` (table `:59-64`; the guard fails on any unclassified committing handler, `:184`). Expected class `A2`, like `generate_grounded_interpretation` (`:60`). Lanes C (C-GAM2B, C-GC1) and E (E-2) append to the same table: rebase, keep every row (Peer review P-5).

**Acceptance.** Plan's own (collected = start + 23, now + 25 with HC-INT-018/019); `git grep -nE "(^|\s)(import llama_cpp|from llama_cpp)" -- src/backend ':!src/backend/tests'` → only `core/llm/llama_cpp_provider.py`. **Rollback:** plan's own.

## B-6 INTERP-UNVERIFIED

**Main today.** The grounded route builds the model question from `observation.value` / `value_text` whatever `observation.user_verified` says (`api/interpretations.py:506-511`; field `models/observation.py:80`). W-3 (D4) removes unverified values from the RAG *context* but leaves this question string to O-3 (`W03:1332`).

**IUV-1 options.**
IUV-1 **is** W-3 plan gate O-3 (`W03:1332` names INTERP-UNVERIFIED). One question, one answer, recorded under both ids; W-3's default for O-3 is "no change here", so O-3 is not a W-3 merge gate (Peer review P-6).

- (a) Leave it; W-3 follow-up.
- (b) **Recommended.** When `not observation.user_verified`, the question names the analyte and unit only, no value. One conditional, no new copy, D4-consistent. Same rule in W-7's prompt if B-5 lands.
- (c) Most conservative: no model call for an unverified observation; return the template interpretation plus a fixed "verify this result first" segment. Needs owner copy.

**Test first (b).** `HC-IUV-001` over HTTP (`route_client`): unverified observation with value `123.4` → the question passed to a spy `rag.query` does not contain `123.4`; `HC-IUV-002`: verified → contains it. Collected +2.

**Files.** `src/backend/api/interpretations.py`, `src/backend/tests/test_safe_interp_grounded.py`. **Rollback.** Revert one commit.

## B-7 MM-1

Owner on a model machine: run W-4 plan Task 7 Step 6 per PR #72 comment 6116808120; paste the RESULT line on #72. Then #72 merges from main and re-measures collected (OW-5). Nothing for an agent until the line exists.

## B-8 G-C3a (delta)

The W11b plan's Group G-C3a stands. Delta on main `3b2236c`:

| Fact | Then (pack 2026-10-07) | Now |
|---|---|---|
| S-C3-1 on main | absent | **signed**, `owner-decisions:48` |
| S-C3-2 threshold rule | signed | **signed** |
| W-4 | no PR | PR #72 open; adds "Concrete evals" item **8** (`evals.md:27` on its branch). G-C3a appends item **9**, not 8 |
| `ci.yml` backend job runs `run-backend-tests.sh` | `:53` | `:56` |
| `ExtractModule` anchors `extract_from_pdf :114`, `parser_version :91`, `_normalize_date_str :662`, `_extract_from_table :195`, `analyte_raw :35`, `collected_at :44` | — | MATCH |
| `docs/agentic/eval-cards/` | absent | absent |
| ID collision (`hc_extr`, `HC-EXTR`, `extraction_golden`) | 0 | 0 |
| worktree name | `HealthCentral-gc3a` | use `../hc-gc3a` |

GC3A-ORDER becomes moot once #72 merges. GC3A-LEDGER (`feature_list.json` HC-M06 → `completed`) is still unasked.

**Acceptance (plan).** Collected = start + 5; `pytest tests/test_extraction_golden.py -q -p no:cacheprovider` → `5 passed`; HC-EXTR-003 green in CI.

## B-9 MM-3, MM-4

- **MM-3:** `cd src/backend && python -m pytest tests/ --collect-only -q | tail -1` and the full suite on a machine with the embedding model. Expect `test_api_rag_index_002b` to pass there. Record both lines in `TASK_LIST.md`, on the MM-3/MM-4 rows only (own-row rule; no wait on lane F's F-13, contracts R-11).
- **MM-4:** after B-3 merges, add to the smoke: one chat answer and one grounded interpretation on a real local model; record whether either was blocked and the audit `reason`. With break-glass off, confirm no warning; with the hook failing (stop backend), confirm the B-1 notice if B-1 has merged.

## INTERP-RENDER — the interpretation card shows raw markup, a negative gauge axis and a confusing footer

**Source:** queue status 2026-10-16 (third batch, MM-4). Planned on `origin/main` @ `b54f105`. Frontend only. No backend validation changes.

**Facts (re-read on `b54f105`):**
1. **Raw `**`.** `InterpretedResultCard.tsx:107-109` renders `interpretation.interpretation_text` as plain text in a `<p>`. The template path writes `\n\n**What this test measures:** … [KB:<id>]` (`modules/interpret.py:636`). No markdown renderer is in the frontend.
2. **Raw markers.** The backend writes `[KB:<uuid>]` (`interpret.py:600,605,612,636`) and `[INT:<uuid>]` (`interpret.py:1187`, `modules/recommend.py:40`) **on purpose**: `_validate_llm_citations` (`:832`) and `interpret_safety.py:78` gate on them. The card already shows the citations as `CitationTooltip`s (`:110-120`), so the inline markers are noise. Strip them **display-side only**. `interpret_safety.py` is ask-first and is not touched.
3. **Negative axis.** `ReferenceRangeComparison.tsx:20-23` computes `displayMin = refLow - 0.3 * (refHigh - refLow)`. With LDL `0–99` that is `-29.7`, the exact MM-4 value. The labels at `:85` and `:99` are unclamped; only the marker is (`:28`).
4. **Footer `Model: template`** (`InterpretedResultCard.tsx:165`) is **accurate** for the card. `POST /interpretations/...` (`api/interpretations.py:380`) runs `interpret_observation`, the template path (`interpret.py:264`). The 19.3 s Ollama call was most likely the separate **grounded summary** (`interpret-grounded`, shown at `pages/LabInterpreter.tsx:290-296`), which is not persisted as this card. Model-written card text is B-5 (W-7). So the defect is a label patients cannot read, not a wrong value. Task 0 confirms on the model machine, from the MM-4 network log, which request took 19.3 s.

**Design.**
1. A pure helper `formatInterpretationText(text: string): { paragraphs: Array<Array<{ bold: boolean; text: string }>> }` in `src/frontend/src/components/lab-interpreter/formatInterpretationText.ts`. It removes `\s*\[(KB|INT):[^\]\s]+\]`, splits paragraphs on blank lines, and turns `**x**` into bold runs. It renders React nodes only: no `dangerouslySetInnerHTML`, no new dependency. The card uses it for `interpretation_text`; `AdviceSection` uses it for `advice_text`.
2. Gauge: when `refLow >= 0` and `value >= 0`, `displayMin = Math.max(0, refLow - padding)`. Ranges that start below 0 keep today's formula.
3. **Footer (gate IR-FOOTER, its own task):** recommended (a) map `model_tier` to plain text: `template` → `Source: knowledge-base template`, any other tier → `Source: local model (<tier>)`.

**Owner gate IR-FOOTER** (text patients see):
- **(a) Recommended:** the plain labels above.
- (b) Hide the footer tier.
- (c) Keep `Model: <tier>`. The footer then changes when B-5 makes the card model-written.

**Test-first** (vitest + testing-library, new `src/frontend/src/__tests__/InterpretedResultCard.test.tsx`, `HC-IRC-NNN`; RED on `b54f105`):

| Id | Assertion | RED? |
|---|---|---|
| HC-IRC-001 | text `"High. [KB:3f2a-…] More [INT:9c1e-…]."` → rendered text has no `[KB:` / `[INT:`; the citation tooltips still render | yes |
| HC-IRC-002 | `"\n\n**What this test measures:** LDL…"` → a `<strong>` holds `What this test measures:`; no literal `**` | yes |
| HC-IRC-003 | `advice_text` with a marker → stripped in `AdviceSection` too | yes |
| HC-IRC-004 | `ReferenceRangeComparison` value 120, range 0–99 → the min label is `0.0`, not `-29.7` | yes |
| HC-IRC-005 | range −5 to 5 (a signed analyte) → the min label is `-8.0` (today's formula kept) | no (pin) |
| HC-IRC-006 (IR-FOOTER a) | `model_tier: "template"` → footer `Source: knowledge-base template` | yes |

**Files:** `src/frontend/src/components/lab-interpreter/InterpretedResultCard.tsx`, `src/frontend/src/components/lab-interpreter/ReferenceRangeComparison.tsx`, `src/frontend/src/components/lab-interpreter/formatInterpretationText.ts` (new), `src/frontend/src/components/lab-interpreter/AdviceSection.tsx`, and `src/frontend/src/__tests__/InterpretedResultCard.test.tsx` (new).

**Expected collected delta:** backend 0. Frontend: +6 vitest cases (+5 without IR-FOOTER (a)).

**Acceptance:** `cd src/frontend && npx tsc --noEmit` clean; `npx vitest run src/__tests__/InterpretedResultCard.test.tsx src/__tests__/LabInterpreter.test.tsx` all pass. That command runs from Windows or CI (vitest stalls on `/mnt/c`, RUNBOOK §6 step 5). Record the run's location. `npm run lint` clean. **Rollback:** revert.

**Order:** no shared file with B-1 (`pages/LabInterpreter.tsx`) or W-3 (`InterpretedTrendChart.tsx`). B-5 later changes what `model_tier` holds, not this rendering.

## EXTRACT-FORMATS — the text-PDF parser misses column layouts and `mIU/L`

**Source:** queue status 2026-10-16 (third batch, MM-4). A column-layout report gave `0 values extracted`.

**Facts (`b54f105`, `src/backend/modules/extract.py`):**
1. Lines are parsed only by `LINE_PATTERN` (`:333-342`, `Analyte: value unit (range) flag`) and `ALT_LINE_PATTERN` (`:344-353`, `Analyte value unit (range) flag`). Both are anchored `^…$`. The range must sit in **parentheses**, and the flag must come **after** the range. A column row such as `TSH 2.10 mIU/L 0.45-4.50` or `Glucose 105 H mg/dL 70-99` matches neither. `_extract_from_text` (`:358-380`) drops non-matching lines silently.
2. The unit alternation (`:75`, `:336`, `:347`) has no `mIU/L`, `uIU/mL`, `µIU/mL`, `ng/dL`, `ug/dL`, `nmol/L`, `pmol/L` or `umol/L`. `modules/normalize.py` `UNIT_CONVERSIONS` (`:39-60`) converts all of them. For example, `tsh` takes `miu/l` and `uiu/ml`; `free_t4` takes `ng/dl` and `pmol/l`.
3. `extract_from_pdf` runs the text parser **only when `page.extract_tables()` returns nothing** (`:156-160`). A page where pdfplumber detects a table that yields 0 observations gets 0 values, even when its text lines would parse.

**Design (smallest correct; a wrong value on a lab card is a patient-safety defect, so every new match needs a known unit and a whole-line match):**
1. Add the units in `UNIT_CONVERSIONS` that the extractor lacks to one shared `_UNIT_ALT`, used by all three patterns. Task 1 diffs the two lists in the PR body. Spelling variants (`µ`/`u`, case) go through the existing case-insensitive flag; `µ` is added explicitly.
2. A third pattern, `COLUMN_LINE_PATTERN`: analyte, value, optional flag, **required** unit, optional bare range (`a-b`, `<a`, `>a`), optional flag, whitespace-separated, `^…$`. Tried after the two existing patterns, so their matches are unchanged.
3. On a page with tables, run the text parser when the tables gave **0** observations. A page whose tables gave any observation keeps today's behaviour, so no duplicates.

**Test-first** (`src/backend/tests/test_extraction_pipeline.py`, beside `:340-390`, fixture `extract_module`; RED on `b54f105`):

| Id | Assertion | RED? |
|---|---|---|
| HC-EXF-001 ×6 | `TSH: 2.1 mIU/L (0.4-4.0)`, `TSH 2.1 uIU/mL (0.4-4.0)`, `Free T4: 1.2 ng/dL (0.8-1.8)`, `Iron 80 ug/dL (60-170)`, `Vitamin D: 75 nmol/L (75-250)`, `Creatinine 88 umol/L (60-110)` → 1 observation each, value and unit exact | yes ×6 |
| HC-EXF-002 | `TSH 2.10 mIU/L 0.45-4.50` → value 2.10, unit `mIU/L`, ref 0.45–4.50 | yes |
| HC-EXF-003 | `Glucose 105 H mg/dL 70-99` → value 105, flag `H`, ref 70–99 | yes |
| HC-EXF-004 | a 12-line column page (header `TEST RESULT FLAG UNITS REFERENCE INTERVAL`, `Page 1 of 2`, `Collected: 01/15/2026 08:10`, a patient-name line, 8 result rows) → exactly the 8 rows, none from header or footer lines | yes |
| HC-EXF-005 | a fake pdfplumber page whose `extract_tables()` returns one table that yields 0 observations and whose text has 2 result lines → 2 observations | yes |
| HC-EXF-006 | a fake page whose table yields 2 observations → 2 observations, text parser not run (no duplicates) | no (pin) |
| HC-EXF-007 | existing colon and alt cases (`:340-390`) and `test_api_extract_001-004` unchanged | no (pin; existing tests) |

The MM-4 report itself is not in the repo. If the owner can share one de-identified page's `extract_text()` output (optional gate EXF-SAMPLE), it becomes an extra HC-EXF-004 row. The plan does not wait for it.

**Files:** `src/backend/modules/extract.py`, `src/backend/tests/test_extraction_pipeline.py`. **Expected collected delta:** +11 (6 + 1 + 1 + 1 + 1 + 1). **Acceptance:** `pyt tests/test_extraction_pipeline.py tests/test_date_extraction.py tests/test_documents_api.py tests/test_unit_conversion.py tests/test_extraction_golden.py -q` 0 failed (B-8 merged as #140, so its golden set measures this parser; any golden change goes in the PR body for the owner's S-C3-2 rule). Full suite per RUNBOOK §6. **Rollback:** revert. Already-extracted documents are unchanged until a user re-processes them.

**Order:** B-8 (G-C3a golden set) merged as #140, so this PR re-runs `tests/test_extraction_golden.py` (acceptance above) and reports any golden change for the owner's S-C3-2 rule. No shared file.

## GRADE-PATTERN-REDOS — the pathology `GRADE_PATTERN` is cubic on whitespace runs

**Source:** PR #212 (REDACT-WS-REDOS) review MINOR, out of scope there: `modules/extract_pathology.py:28` `GRADE_PATTERN` is worse than quadratic. Re-measured for this plan (table below): 2.46 s at 800 spaces and 16.3 s at 1600 (the #212 review's "1000+ did not finish in 120 s" did not reproduce; it is superseded by the table). Recurring-failures #9 (the same `\s*:?\s*` shape REDACT-WS-REDOS removed from `redaction.py` was left in a sibling module). Planned 2026-10-20 on `origin/main` @ `b2b3f4e`.

**Facts (`b2b3f4e`):**
1. `GRADE_PATTERN = re.compile(r"\b(?:grade|Gleason|Nottingham)\s*:?\s*([\w\s/\+]+?)(?:\n|[,;.])", re.IGNORECASE)` (`src/backend/modules/extract_pathology.py:27-30`), used once: `GRADE_PATTERN.search(text)` (`:89`), value `group(1).strip()`.
2. `extract_pathology_entities` runs on every document typed `pathology` (`src/backend/api/documents.py:926`), so the text is whatever a patient uploads.
3. Three pieces can each take the same spaces: the two `\s*` and the lazy `[\w\s/\+]+?`. With no terminator after the run, every split is tried: O(n³) for one label. Separately, many labels in a row (`"grade " * n`) restart the scan at each label: O(n²).
4. Tests: `tests/test_extract_pathology.py` (5 tests) has no grade test; `tests/test_source_spans.py:81` runs the extractor on a fixed report.

**Measured on `b2b3f4e`** (scratch script, `GRADE_PATTERN.search` and the full `extract_pathology_entities`, not committed):

| Input | `main` | possessive + bounded (design) |
|---|---|---|
| `"grade" + " " * 400 + "x"` | 0.342 s | 0.000 s |
| `"grade" + " " * 800 + "x"` | 2.462 s (`extract_pathology_entities`: 2.09 s) | 0.000 s |
| `"grade" + " " * 1600 + "x"` | 16.32 s | 0.000 s |
| `"grade" + " " * 50000 + "x"` | not run (cubic) | 0.000 s |
| `"grade " * 8000` | 11.36 s | 0.031 s (`"grade " * 50000`: 0.191 s) |
| possessive only (`\s*+:?\s*+`), `"grade " * 8000` | — | 3.866 s (still quadratic, hence the bound) |
| design without the first `+` (`\s*:?\s*+`), `"grade" + " " * 50000 + "x"` | — | 2.605 s (quadratic: 0.435 s at 20,000) |
| `"Gleason:" + "\t" * 1600 + "x"` | 0.03 s (the colon ends the first run) | 0.000 s |

**Design:** `\b(?:grade|Gleason|Nottingham)\s*+:?\s*+([\w\s/\+]{1,200}?)(?:\n|[,;.])` (possessive quantifiers are Python 3.11+, the project floor). The first possessive `\s*+` gives the space run to one piece only (without it: quadratic, measured above), the second stops the value from starting with a space (so no whitespace-only value is captured after a colon), and the `{1,200}` bound stops the restart cost. The flags and the call site stay as they are. Two output changes, both measured:
1. **A label followed only by whitespace and then `,` `;` `.` or a newline no longer yields an empty grade.** On `main`, `"Grade: ,\nGleason 4+3."` gives a grade entity with `entity_value == ""` (span 0-8). With the change the search goes on and finds `"4+3"` (span 9-21). Differential, 200,000 seeded random strings of 1-10 tokens from {`grade`, `Gleason`, `Nottingham`, spaces, tab, newline, `:`, `,`, `.`, `;`, `x`, `2`, `3+4`, `/`, `-`, `=`, `II`, `score`}: **3,650 differ, and in every one `main`'s value is the empty string.** In 3,574 the new pattern finds no grade, and in 76 it finds a **different, later, non-empty grade** where `main` returned `""`. No non-empty value changes. Re-run 2026-10-20 (seed 0: 3,650 / 76; seeds 1, 2, 42: 3,547 / 69, 3,580 / 71, 3,590 / 79; in every seed every differing `main` value is `""`). Examples of the 76 kind (`main` → design, `(start, end, value)`):
   - `"Grade: ,\nGleason 4+3."`: `(0, 8, "")` → `(9, 21, "4+3")`.
   - `"Histologic grade: .\nNottingham grade 2."`: `(11, 19, "")` → `(20, 39, "grade 2")`.
   - `"Gleason: ,\ngrade group 2;"`: `(0, 10, "")` → `(11, 25, "group 2")`.
   - `"Tumor grade: ;\nMargins: clear, grade 3 elsewhere."`: `(6, 14, "")` → `(31, 49, "3 elsewhere")`. The value now comes from a later sentence than the label the reader sees first.
   - From the random corpus: `"2 Gleason  ,gradescore  II."`: `(2, 12, "")` → `(12, 27, "score  II")`; `"Gleason\t,.,II  Gleasonx;"`: `(0, 9, "")` → `(15, 24, "x")`.
2. **A value longer than 200 characters before its terminator is no longer matched at that label.** No such value is in the corpus or in any test. Real grade values are a few characters long (`2/3`, `II`, `score 3+4`).

**Behaviour change, gated (L0 ruling 2026-10-20 on the #222 review).** Change 1 changes what is extracted from a patient's pathology report: empty-value grades are no longer emitted, and in the 76-of-200,000 shape a different, later, non-empty grade is returned instead (examples above). That needs the owner, not L0, so the row gets a merge-only gate **GRADE-REDOS-DIFF**: the owner says yes on the exact `extract_pathology.py` diff, shown with the differential (counts and the examples, re-measured on the PR head). The build is allowed now; the PR stays draft until GRADE-REDOS-DIFF. Exact wording under [Owner gates](#owner-gates), item 8. If the owner picks (b), the implementer redrafts the pattern to keep today's empty match and re-asks GRADE-REDOS-DIFF on that diff. (b) is feasible but not designed: a first candidate measured while fixing this plan, `\s*+:?\s*+(?:([\w/\+][\w\s/\+]{0,199}?)|(?<=\s))(?:\n|[,;.])`, matched `main` on all but 658 of 200,000 strings (each one a whitespace run that ends in a newline) and stayed under 0.25 s on every timing input.

**Pins of today's values** (measured identical on `main` and with the design): `"Gleason score 3+4, grade group 2"` → `"score 3+4"`; `"Nottingham grade 2."` → `"grade 2"`; `"Grade: 3\n"` → `"3"`; `"Histologic grade: 2/3\nMARGINS: clear"` → `"2/3"` (span 11-21); `"Grade:\n\nII."` → `"II"`; `"GRADE: well differentiated (G1);"` → no grade; `"grade 2"` (no terminator) → no grade.

**Test-first** (`src/backend/tests/test_extract_pathology.py`; timing in the style of HC-REDACT-015/017, `time.perf_counter()`, bound 1.0 s):

| Id | Assertion | RED today? |
|---|---|---|
| HC-PATH-001 ×3 (parametrised) | each input runs in a child process (`subprocess.run([sys.executable, "-c", …], cwd=src/backend, timeout=10)`) that times `extract_pathology_entities(s)` with `time.perf_counter()` and prints the seconds and whether a grade entity came back; the test asserts the child finished, the time is under 1.0 s, and no grade entity. Inputs: `"grade" + " " * 1600 + "x"`, `"grade " * 8000`, `"grade" + " " * 50000 + "x"`. The child process is what lets the cubic case fail cleanly (timeout) instead of hanging the suite | yes ×3 (16.3 s, 11.4 s, and a 10 s timeout on `main`) |
| HC-PATH-002 | differential: an inline copy of today's pattern against `GRADE_PATTERN` on 20,000 seeded random strings over the token set above: for each, the same `(start, end, group(1).strip())`, **or** today's value is `""` | no (pin). Measured on 20,000 strings (seed 1): the design gives 0 differences of this kind; mutant `{1,200}` → `{1,5}` gives 829 (fails it). The timing mutants are HC-PATH-001's: drop the bound (`+?`) → `"grade " * 8000` takes 3.87 s; drop the first `+` → the 50,000-space case takes 2.6 s. Both differential-equal, both fail HC-PATH-001 |
| HC-PATH-003 ×8 (parametrised) | the 7 pins above, plus `"Grade: ,\nGleason 4+3."` → `"4+3"` (the documented change 1) | 7 no (pins); the last one yes (`main` gives `""`) |

**Files:** `src/backend/modules/extract_pathology.py` (`:27-30` only), `src/backend/tests/test_extract_pathology.py`, slots. **Re-run, not edited:** `tests/test_source_spans.py`, `tests/test_documents_api.py`.
**Expected collected delta:** +12 (3 + 1 + 8). **Est:** 1 h.
**Acceptance** (from `src/backend`, `pyt` = `bash "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest`): `pyt tests/test_extract_pathology.py tests/test_source_spans.py tests/test_documents_api.py -q -rfE`: 0 failed; RED output for HC-PATH-001 ×3 and the last HC-PATH-003 case; the three mutant outputs (`{1,5}`, no bound, no first `+`); full suite per RUNBOOK §6. **Rollback:** revert. Documents already extracted keep their stored entities until re-processed.
**Order:** build allowed now; merge blocked on GRADE-REDOS-DIFF (PR stays draft). No shared file with any open PR or queued row on `b2b3f4e`. No ask-first file. The other patterns in this module (`SPECIMEN_SITE_PATTERN`, `DIAGNOSIS_PATTERN`, `MARGINS_PATTERN`, `PATHOLOGIST_PATTERN`) were not timed; a reviewer who finds the same shape there raises a new row, not a scope change.

## PATH-REGEX-NEWLINES — `DIAGNOSIS_PATTERN` and `SPECIAL_STAINS_PATTERN` are quadratic on newline runs

**Source:** #238 (GRADE-PATTERN-REDOS) review, out of scope there; the GRADE plan above already said the module's other patterns were not timed. Planned 2026-10-20 on `origin/main` @ `699eb18`. Recurring-failures #9 (the same shape in sibling patterns).

**Facts (`699eb18`):**
1. `DIAGNOSIS_PATTERN` (`src/backend/modules/extract_pathology.py:22-25`) and `SPECIAL_STAINS_PATTERN` (`:42-45`) share the body `(.+?)(?=\n\s*[A-Z]{2,}|\Z)` under `re.DOTALL`. At each step of the lazy body, the lookahead's `\s*` re-scans the rest of a whitespace run, so a run of n newlines costs O(n²).
2. Each runs once per pathology document (`:80`, `:116`), on uploaded text (`src/backend/api/documents.py:926`). Values are `group(1).strip()[:500]`; spans come from `with_span`, which trims whitespace from the full match (`src/backend/modules/extract_spans.py:28-32`).

**Measured on `699eb18`** (scratch script, `Pattern.search`, not committed): `"DIAGNOSIS:x" + "\n" * n` takes 0.006 s at 1,000, 0.026 s at 2,000, 0.125 s at 4,000 and **2.94 s at 20,000**; `"IHC:x" + "\n" * 20000` takes 3.03 s; `" \n"` runs are about twice as slow. A normal report is unaffected (`"FINAL DIAGNOSIS: Benign tissue.\n…"` → `Benign tissue.`).

**Design (one candidate, measured; the implementer may choose another that passes the same tests). Revised after the #248 Codex review (MAJOR 1):** the first candidate kept the label prefix `…:?\s*` and still backtracked (re-measured here: 1.40 s at `"DIAGNOSIS:" + " \n" * 8000`, 5.94 s at 16,000), and on a whitespace-only value its `:?` gave the colon back and captured `:`. Three changes:
1. **Label atomic, separator possessive:** `(?>DIAGNOSIS|FINAL DIAGNOSIS|PATHOLOGIC DIAGNOSIS):?+\s*+` and `(?>SPECIAL\s+STAINS?|IMMUNOHISTOCHEMISTRY|IHC):?+\s*+`. The value can no longer start inside the label (`main` turns a bare `Special stains` into the value `s`) or on the colon, and the whitespace run after the label goes to one piece only.
2. **Body** never stops inside a whitespace run; a run is consumed whole (atomic group) unless it holds a newline followed by `[A-Z]{2,}` or reaches the end: `((?:\S|[^\S\n]+(?![^\S\n]|\n\s*[A-Z]{2,}|\s*\Z)|(?>[^\S\n]*\n\s*)(?![A-Z]{2,}|\Z))+?)`.
3. **Stop:** `(?=\s*\Z|[^\S\n]*\n\s*[A-Z]{2,})`. Flags unchanged (`re.DOTALL | re.IGNORECASE`).
- **Timing (revised candidate):** 0.000 s at 8,000 and 16,000 for `" \n"` after a bare label; 0.001-0.004 s at 50,000 for whitespace-only values (`" \n"`, `"\n"`, `" "`, `"\t\n "`) after a bare label; 0.000 s at 50,000 for `"\n"`, `" \n"`, `"\n "` after `x`; 0.014-0.036 s for `(label + " ") * 20000`. Both patterns.
- **Differential** (200,000 seeded random strings of 1-12 tokens from {`DIAGNOSIS`, `diagnosis`, `IHC`, `Special stains`, `FINAL DIAGNOSIS`, `:`, spaces, tab, `\n`, `\n\n`, `\r`, `AB`, `Ab`, `x`, `MARGINS`, `a`, `.`, `1`}, observable `(trimmed start, trimmed end, value)`): DIAGNOSIS differs on 7,418 strings, where `main`'s value is `""` (6,650) or `":"` (768); SPECIAL_STAINS on 12,456, where `main`'s value is `"s"` (6,197, the label's own last letter), `""` (5,594) or `":"` (665). In **every** difference the candidate returns no entity; it never returns a different non-empty value and never moves to a later label. The pins below are identical on `main` and the candidate. Like GRADE-REDOS-DIFF (a) (`owner-decisions-2026-09-27.md:350`), this changes extracted values, so it has its own merge gate.

**Test-first** (`src/backend/tests/test_extract_pathology.py`, the HC-PATH-001 child-process timing style):

| Id | Assertion | RED today? |
|---|---|---|
| HC-PATH-004 ×8 (parametrised) | `extract_pathology_entities` finishes in a child process in under 1.0 s on: `"DIAGNOSIS:x" + "\n" * 50000`, `"DIAGNOSIS:x" + " \n" * 50000`, `"IHC:x" + "\n" * 50000`, `"IHC:x" + " \n" * 50000`, and the whitespace-only `"DIAGNOSIS:" + " \n" * 16000`, `"DIAGNOSIS:" + "\n" * 50000`, `"IHC:" + " \n" * 16000`, `"Special stains:" + "\t\n " * 20000` | first four: yes (quadratic on `main`); last four: no on `main` (measured 0.00 s each: `\s*` takes the run and the body reaches `\Z`), they guard the first candidate's regression (5.9 s at 16,000) |
| HC-PATH-005 ×6 (parametrised) | exact values, whitespace-only and label-only input: `"DIAGNOSIS:   \n\n"`, `"FINAL DIAGNOSIS:"`, `"IHC: \t\n"`, `"Special stains:"`, `"Special stains"`, `"DIAGNOSIS:" + " \n" * 1000` each give **no** `diagnosis` / `special_stains` entity (not `""`, `":"` or `"s"`) | yes ×6 (`main` gives `""`, `":"` or `"s"`; the first candidate gives `":"`) |
| HC-PATH-005b | differential: inline copies of today's two patterns against the new ones on 20,000 seeded random strings: the same observable triple, **or** today's value is in {`""`, `":"`, `"s"`} **and** the new pattern returns no match. The exception is that narrow on purpose: a new pattern that returns any value where `main` returned an empty one fails it | no (pin); mutants: dropping the `\n\s*[A-Z]{2,}` stop, or making the label non-atomic, fail it |
| HC-PATH-006 ×4 | pins: `"DIAGNOSIS: Invasive ductal carcinoma, grade 2\nMARGINS: Clear"` → `Invasive ductal carcinoma, grade 2`; `"FINAL DIAGNOSIS: Benign tissue.\n\nMARGINS: clear"` → `Benign tissue.` (same trimmed span); `"IHC: CK7 positive  \n GRADE: 2"` → `CK7 positive`; `"DIAGNOSIS: carcinoma\n  1. with necrosis\nMARGINS: clear"` → `carcinoma\n  1. with necrosis` (a numbered line continues the value; `[A-Z]{2,}` runs under `re.IGNORECASE`, so any line starting with two letters ends it) | no (pins; all four measured identical on `main` and the revised candidate) |

**Files:** `src/backend/modules/extract_pathology.py` (`:22-25`, `:42-45` only), `src/backend/tests/test_extract_pathology.py`, slots. **Re-run, not edited:** `tests/test_source_spans.py`, `tests/test_documents_api.py`.
**Expected collected delta:** +19 (8 + 6 + 1 + 4). **Est:** 2 h.
**Acceptance:** `pyt tests/test_extract_pathology.py tests/test_source_spans.py tests/test_documents_api.py -q -rfE`: 0 failed; RED output for the first four HC-PATH-004 cases and HC-PATH-005 ×6; the differential counts pasted in the PR body; full suite per RUNBOOK §6. **Rollback:** revert.
**Owner gate:** **PATH-NL-DIFF** (merge only, open; asked after the draft PR exists), Owner gates item 9 below.
**Order:** build allowed now (GRADE-PATTERN-REDOS merged, #238); merge blocked on PATH-NL-DIFF (PR stays draft). No open PR touches `extract_pathology.py` or its test. No ask-first file.

## Provides

1. `src/backend/modules/agent/guardrails/advice_judge.py`: `async def advice_judge(text: str, runner: core.model_runner.ModelRunner) -> Literal["ALLOW", "BLOCK", "UNAVAILABLE"]`; constant `FROZEN_PROMPT: str`. Never sends to an external runner. (B-3)
2. `modules.rag.ValidatedResponse.prohibited_reason: str`, default `"prohibited_pattern"`, values `"prohibited_pattern" | "advice_judge" | "advice_judge_unavailable"`; `RAGModule.query(..., judge_runner: Optional[ModelRunner] = None)`. Audit rows `assistant.prohibited_blocked` and `interpretation.prohibited_blocked` carry `details.reason` from it. (B-3)
3. `src/backend/scripts/measure_prohibited_patterns.py --judge <file>` (B-3; consumed by MM-2).
4. `POST /api/v1/interpretations/observations/{observation_id}/interpret-tiered?force_regenerate=bool` → 201 `InterpretationResponse`; audit event `interpretation.tiered` via `_audit_interpretation`; `tests/test_llm_import_boundary.py` (HC-LLMB). (B-5)
5. `ExternalApiBreakGlassWarning` prop `unknown?: boolean` (B-1); `docs/agentic/eval-cards/extraction.md` + `evals.md` item 9 (B-8).

## Consumes

1. PR #72 (W-4) merged after MM-1: `tests/legacy_eval/harness.py` and `evals.md` item 8 (B-3 D-2, B-8).
2. PR #74 (Tailwind 4) merged before B-1 (same 3 pages).
3. PR #95 (ASSIST-UTC): `rag.py` line shifts; B-3 anchors on symbols.
4. ~~P6 then P7 merged before B-5~~: dropped by L0 ruling R-6 (contracts). B-5 re-reads the `route_client` signature at start; C-P7's change is two appended keywords with defaults.
5. W-3 (D4) for the context half of INTERP-UNVERIFIED; B-6 (b) does not wait for it.

## Owner gates

None of these is answered. Ask with the wording below; record answers in owner-decisions only when given.

1. **BGS-1 (B-1).** "When the app cannot confirm whether the privacy override is on, should the page say so? (a) yes, a neutral notice, copy: 'Could not confirm this installation's privacy settings. If the privacy protection override is on, external AI requests may leave this device with reduced redaction.' (b) also block external sends until confirmed (larger) (c) close the item as accepted." Recommended (a).
2. **IBF-1 (B-2 + W-7).** Options in §B-2. Recommended (a).
3. **PR3-TIER (B-3).** "Your Q4/Q5 'tier-2' minimum: the app cannot tell which tier a loaded model belongs to, except the `low` file. (a) enforce at measurement only, and block at runtime only when the loaded file is the `low` tier's (b) block unless the loaded file is a pinned mid-or-higher file (fails closed for everyone today) (c) other." Recommended (a).
4. **PR3-S5N (B-3/B-4).** "S5 size: the plan asks 180 + 200 items; your Q6 note says 40-60. Which?" Recommended: the plan's size, or accept ±8 points at 50.
5. **IUV-1 (B-6)**, **W7-SPILL (B-5)**, **S-C3-2** and **GC3A-LEDGER (B-8)**: wording in §B-6, the [W-7 pack](../../../audit/2026-09-25/waves/scaffold/W-7.md) Q3, and the [G-C3a pack](../../../audit/2026-09-25/waves/scaffold/G-C3a.md) §3.
6. **IR-FOOTER (INTERP-RENDER, planned 2026-10-17).** "The lab card footer says `Model: template` even when a local model wrote the separate grounded summary. What should it say? (a) plain source labels: 'Source: knowledge-base template' / 'Source: local model (<tier>)' (b) hide the tier (c) keep as is." Recommended (a).
7. **EXF-SAMPLE (EXTRACT-FORMATS, optional, planned 2026-10-17).** "Can you share the `extract_text()` output of one de-identified page of the column-layout report from MM-4? It becomes a regression row; the fix does not wait for it."
8. **GRADE-REDOS-DIFF (GRADE-PATTERN-REDOS, merge only, added 2026-10-20; asked after the draft PR exists).** "GRADE-REDOS-DIFF: here is the exact `modules/extract_pathology.py` diff for GRADE-PATTERN-REDOS, with RED/GREEN, timing, mutant output and the differential against today's pattern. It changes what is extracted from a pathology report in one shape: a grade label followed only by spaces and then `,` `;` `.` or a newline. Today that gives a grade entity with an empty value. With the diff, no empty grade is emitted; the search goes on, and in some strings (76 of 200,000 in the planning differential) it returns a later, non-empty value, for example `Tumor grade: ;\nMargins: clear, grade 3 elsewhere.` gives `3 elsewhere` instead of an empty grade. Which do you want? (a) Merge this diff: no empty grade, the search goes on to a later label. (b) Keep today's empty match at the first label: the implementer redrafts the pattern to keep it and asks again on that diff (more work; not yet designed). (c) Do not merge; leave the pattern as it is (the slow inputs stay slow)." No option is recommended: the choice is what a patient's report should show.
9. **PATH-NL-DIFF (PATH-REGEX-NEWLINES, merge only, added 2026-10-20; asked after the draft PR exists).** "PATH-NL-DIFF: here is the exact `modules/extract_pathology.py` diff for PATH-REGEX-NEWLINES (`DIAGNOSIS_PATTERN`, `SPECIAL_STAINS_PATTERN`), with RED/GREEN, timing and the differential. Every difference from `main` is a label with no real value, where `main` returns an empty diagnosis or stains value, a bare `:`, or `s` (the last letter of `Special stains`); the new pattern returns no entity there. No non-empty value changes, and no value moves to a later label. (a) merge this diff, as you chose for grades (GRADE-REDOS-DIFF (a)) (Recommended: same class of change, same reasoning) (b) redraft so empty values are kept exactly (zero differences), then ask again (c) leave both patterns as they are."

Owner tasks (no question): OW-3 (S5), MM-1, MM-2, MM-3, MM-4.

## Open questions

1. ~~L0: may W-7 drop P7 as a hard dependency?~~ Ruled yes (contracts R-6).
2. L0: B-3's Codex plan review: run it on §B-3 of this doc, or on a separate `docs/plans/` file? This doc assumes §B-3.
3. B-3 D-1: how many existing tests fail RED once the judge exists is UNMEASURED; it sets the PR size.
4. ~~B-2 (c): who owns KB seed text edits?~~ Resolved in peer review: lane A SAFE-CHAT-FALLBACK option C owns `scripts/seed_knowledge_base.py` (P-4).
5. Main slot reads 1574, open PR branches 1480-1505: each merges from main and re-measures (OW-5); this lane's PRs measure from whatever main is then.

## Peer review (2026-10-15)

Checked against lanes A, C, D, E, F surfaces and the repo at `3b2236c` (+ `origin/fix/assistant-utc`). Changes made in this doc:

| # | Finding (verified) | Change here |
|---|---|---|
| P-1 | `api/interpretations.py` grounded route is edited by 4 items: B-6 question `:506-511`, lane A RAG-RUNTIME-500 `except` at `:531-535`, B-3 audit reason `:591`, B-5 new route after `:603`. `tests/test_safe_interp_grounded.py` gets tests from B-2, B-3, B-6 and RAG-RUNTIME-500. Lane A only orders RAG-RUNTIME-500 against W-7. | File queue below; raised as a conflict with lane A |
| P-2 | `modules/rag.py` and `api/assistant.py` are shared with W-3, W-8, G-C5, ASSIST-AGENT-DATES, #72. B-3 stays draft until B-4, so it must not hold either file; but a rebase after MM-2 changes the "freeze sha". | B-4 step 1: freeze-validity rule |
| P-3 | B-3's RED list (D-1) grows with peer tests that fake the runner; #95 `test_assist_utc_http.py:98` patches `modules.rag.get_model_runner`. | D-1: re-take RED list at final rebase |
| P-4 | B-2 (c) and lane A SCF-RULING C are the same 7 seeded KB fields. | B-2 (c) defers to SCF-RULING C; open question 4 closed |
| P-5 | W-7's new committing handler fails HC-AUD-ORD-030 unless classified in `tests/test_audit_order_guard.py`. Missing from the B-5 file list. | B-5 section + file list |
| P-6 | IUV-1 (B-6) and W-3 O-3 (lane A) are one owner question. | B-6 section |
| P-7 | B-9 and lane F F-13 both edit `TASK_LIST.md` owner-queue lines `:76-104`. | B-9 writes MM rows only; the wait on F-13 is superseded by contracts R-11 |
| P-8 | B-3's `details.reason` values pass `core/audit.py` scrubbing as is: `reason` is in `STRING_DETAIL_KEYS` (`:75`) and `advice_judge_unavailable` matches `_ENUM_VALUE_RE` (`:112`). No `core/audit.py` edit (unlike C-DUPAUD). | none (confirms design) |

**File queue, `src/backend/api/interpretations.py` + `tests/test_safe_interp_grounded.py`.** One non-draft PR at a time; each later PR merges `origin/main` and re-measures the collected slot. Order by readiness: B-2 (HC-SIE-001, test only) and B-6 and RAG-RUNTIME-500 in whichever order their owner gates are answered; then B-3 (draft until B-4); B-5 last (needs B-3). B-3 re-takes its RED list after each of these lands.

**Merge order, `modules/rag.py` / `api/assistant.py`.** B-3 never blocks W-3, W-8, G-C5, ASSIST-AGENT-DATES or #72: they land as they become ready; B-3 rebases on each under the freeze-validity rule (B-4 step 1). If B-4 is signed before any of them, B-3 lands first and they rebase. Hunks are disjoint (B-3: `class ValidatedResponse`, `query` signature, after `:1276`; audit `details` in `api/assistant.py` `:898`/`:932`).

**Not changed here (raised as conflicts):** W-7's P6/P7 hard dependency (lane C `route_client` change is an additive keyword), RAG-RUNTIME-500 ordering (lane A), O-3 = IUV-1 (lane A), `SettingsPage.tsx` overlap with C-GAM2B (lane C), `test_audit_order_guard.py` shared table (lanes C, E).
