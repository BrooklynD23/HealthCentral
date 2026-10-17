# Lane A — RAG + assistant: build-program design

**Last Updated:** 2026-10-15
**Owner:** repository owner
**Status:** PROPOSED — design only, not approved for execution. No owner approval is recorded here that is not already in [owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md). Every "Recommended" below is the lane designer's, not the owner's.
**Refresh Trigger:** any of #72 (W-4), #95 (ASSIST-UTC), #74 (Tailwind 4) merging; any owner answer to a gate in [Owner gates](#owner-gates); any commit to `src/backend/api/assistant.py`, `src/backend/modules/rag.py`, `src/backend/api/interpretations.py` or `src/backend/modules/agent/**`.
**Base measured:** `origin/main` @ `3b2236c` (2026-10-15). Every `file:line` without a ref was re-read at this base. Open PRs were read with `git show origin/<branch>:<path>` / `gh pr view`; they are assumed to merge as-is.

Read-only design. No product file was edited. Existing merged plans are not rewritten; this file gives a **delta** for each (W-3, W-8) and a compact design for items with no plan.

## Items

| ID | Kind | Source | Plan | Readiness | Blocked by |
|---|---|---|---|---|---|
| W-3 | PRODUCT | program row `implementation-program.md:436` | [W03](../2026-09-27-W03-verified-only-rag-and-trend-labels.md) (delta below) | blocked-on-PR | #72 (W-4, plan prerequisite), #95 (adjacent `rag.py` hunks); O-5 / O-1 / O-2 gate tasks 3 / 7 / 6 |
| W-8 | PRODUCT | program row `:441` | [W08](../2026-09-27-W08-bundled-embedding-model.md) (delta below) | blocked-on-item | W-3, W-11a PR-3 = lane E E-3 (hard, plan §Shared-file order); `ci.yml` last per lane E (E-3 → #74 → #72 → W-8); Q-FC, Q-HASH, VERIFIED-FALLBACK unsigned |
| G-C5-PLAN | DOCS | program row `:411`, `:450`; [scaffold pack](../../../audit/2026-09-25/waves/scaffold/G-C5.md) | none (design below = plan brief) | blocked-on-owner | Q5b (and GC5-PLAN) |
| G-C5 | PRODUCT | same | none | blocked-on-item | G-C5-PLAN, W-8 (if Q5b = A), W-4 (#72, for the byte-identical gate) |
| SAFE-CHAT-AGENT | OWNER (→ PRODUCT if B) | program owner item `:498` (a); [wave-3-L1-A](../../../audit/2026-09-25/waves/wave-3-L1-A.md) "Other paths" 2 | none | blocked-on-owner | SCA-RULING |
| SAFE-CHAT-FALLBACK | OWNER | `:498` (b); wave-3-L1-A Codex diff row | none | blocked-on-owner | SCF-RULING |
| SAFE-CHAT-HISTORY | OWNER | `:498` (c); wave-3-L1-A "Other paths" 5 | none | blocked-on-owner | SCH-RULING |
| ASSIST-AGENT-DATES | PRODUCT | #95 body "Scope note"; `docs/reviews/2026-10-14/ASSIST-UTC-diff-codereview.md` (on `fix/assistant-utc`) MEDIUM row | none | ready | AAD-ROW + AAD-SEMANTICS answered; #95 merged (provides the parser) |
| RAG-RUNTIME-500 | PRODUCT | program owner item `:495`; wave-3-L1-A Phase 4 owner item 4 | none | blocked-on-owner | RR500-MAP; serial with W-7 on `api/interpretations.py` |

Collected-count note: the lane baseline is **1574** (`CLAUDE.md:30`, `AGENT.md:76` on `3b2236c`; confirmed by L0 in the peer-review round). 1501 was #95's own branch value. Not re-measured here (no pytest on this box). Ground rule 8 (SLOT-RULE): every lane-A PR runs `--collect-only` **after its final rebase** onto `origin/main` and writes the measured number into both slots in the same commit. It never adds its own delta to a number copied from a doc. Lane D's D-0 chain (#95 → #97 → #99 → #82 → #84) runs first, so lane-A PRs start from whatever D-0 measured.

## W-3 — delta to the merged plan

The plan stays valid in scope (D4: "Label, exclude from RAG"), tasks, test IDs (HC-VER-001…005, HC-VER-FE-001…003) and stop gates. What changed on main since it was written (`main@40f590e`):

1. **Prerequisites now met:** P1, P5 (`98bd3c7`, PR #54), W-10 (PR #53), W-5 (PR #34), D9. **Still unmet:** W-4 (#72, CI green; merge waits on the owner's 20-question model-host run, W4-20Q-HOST). The plan's W-4 dependency is about `api/assistant.py` (Task 7 only); #72 does not touch `modules/rag.py`, `api/observations.py` or the frontend (`git diff --name-only origin/main...origin/fix/w4-legacy-abstain`).
2. **New ordering constraint, #95:** ASSIST-UTC rewrites the 4 date-filter blocks in `modules/rag.py` (`:336-347` observations, `:557+` documents) directly below W-3's two hunks. Branch W-3 after #95 merges so the hunks do not collide.
3. **New ordering constraint, #74 (Tailwind 4, draft):** edits `src/frontend/src/pages/TrendsDashboard.tsx`, which W-3 Task 5 edits. Serialize; whichever lands second rebases.
4. **Corrected anchors** (re-read at `3b2236c`; the plan's Task 0 Step 5 re-grep still applies):

| Plan anchor (`main@40f590e`) | Now | Note |
|---|---|---|
| `api/observations.py` `TrendPoint :156-168` | `:157-169` | no `user_verified` field yet |
| `api/observations.py` point construction `:608-618` | `:609-619` | |
| `modules/rag.py` observation statement `:323-332` | `:325-334` (`where` `:327-331`) | after #95 the date blocks below it change |
| `modules/rag.py` swallow `:450-451` | `:452-453` | absence tests still need the positive control |
| `modules/rag.py` vector statement `:549-553` | `:551-555` | `is_user_verified` computed `:609` |
| `modules/rag.py` insufficient-context text `:1236-1245` | `:1240-1249` | O-4 |
| `modules/rag.py` 0.6 faithfulness `:862` | `:866` | never lowered |
| `api/assistant.py` `_fetch_latest_obs` `where` `:1280-1284` | `:1367-1371` (function `:1359-1377`) | #72 adds ~30 lines above; re-grep after it merges |
| `src/frontend/src/services/types.ts` `TrendPoint :192-204` | `:192` | unchanged |
| `TrendsDashboard.tsx` `chartData :145-156`, `Line :479-487` | `:145`, `:479` | #74 will move these |
| `InterpretedTrendChart.tsx` `chartData :36-43`, badge `:78-81`, `Line :158-166` | `:36`, `:79`, `:158` | unchanged |

5. **Gates:** O-5, O-1 (= VERIFIED-FALLBACK), O-2 veto, O-3, O-4 are all still unsigned (no row in owner-decisions; the `O-2` row at `owner-decisions:84` is W-2's, not W-3's). Tasks 1, 2, 4, 5 and 6 can run without any of them. W-3 changes nothing for O-3 or O-4, so neither blocks W-3:
   - **O-3 = INTERP-UNVERIFIED = lane B item B-6 (gate IUV-1).** Lane B owns the question-string fix in `api/interpretations.py`. W-3 supplies only the context half (Task 2).
   - **O-4 = MSG-UNVERIFIED** (program `:461`, text at `rag.py:1240-1249`). No lane owned it, so lane A takes it. If the owner opens it and gives the wording, it becomes a one-string commit at the end of the W-3 PR. Lane A never writes patient-facing wording itself.
6. **Wearables (#94) does not conflict:** its A3 rule keeps wearable rows out of `observations`, and WEAR-08 Task 7 asserts `rag.py` / `api/observations.py` / `TrendsDashboard.tsx` are untouched by wearables.
7. **Acceptance unchanged:** collected = start + 5 (−1 per skipped task); agent golden set IDENTICAL (`scripts/agent_eval_gate.py`); vitest +8. Add: `scripts/legacy_eval_gate.py` (from #72) still passes after Task 2/3.
8. **Variant-I contract (lane F, F-6):** HC-VER-002 already calls `route_client` inside its own test body (plan Task 1, `W03:379`). The W-3 PR body must also paste the red-first output for each new test ID (HC-VER-001…005) and at least one break-it run. If any of these is missing, W-10b keeps `data-privacy.md` DP-3 at U.
9. **B-3 advice judge (lane B):** after B-3, `RAGModule.query` calls `judge_runner or get_model_runner()` after `:1276`. It never uses the capturing `model_runner`, so HC-VER-001's `len(runner.prompts) == 1` still holds. However, on a host with a real GGUF the global runner would run a real judge. So if B-3 lands first, W-3's `_ask` helper passes `judge_runner=` an ALLOW fake. If W-3 lands first, B-3 adds `tests/test_verified_only_consumers.py` to its RED list. HC-VER-004 returns before generation and is unaffected.

## W-8 — delta to the merged plan

Scope (D8 + D8-delivery), tasks and test IDs (HC-EMB-001…008) stay valid. Changes:

1. **Owner answers since the plan:** Q-OFFLINE answered "Per call" and EMB-REV answered "Approve this pin" (`owner-decisions:85-86`, 2026-10-08). The plan's own sign-off lines (`W08 :1385-1390`) are still unticked; Task 0 Step 3 ticks them **citing those rows**, nothing more. Still unsigned: **Q-FC**, **Q-HASH**, **VERIFIED-FALLBACK** (= W-3 O-1).
2. **Hard prerequisites unchanged and still unmet:** W-3 (shared `_search_vectors_async` statement, now `rag.py:551-555`) and W-11a PR-3 (`ci.yml`, `docs/architecture/ci-and-quality-gates.md`). `ci.yml` order is owned by lane E: E-3 (W-11a PR-3) → #74 → #72 (W-4, `legacy-evals`) → **W-8 last**. E-3 and #72 may swap. #72 is a rebase trigger for W-8, not a hard dependency. W-8's Task 4 fetch step goes into the `backend-tests` job **before** E-3's `Run backend tests (with coverage report)` step, and the coverage step stays as it is. Before opening the PR, W-8 asks lane E to confirm the job list.
2a. **Docs files W-8 edits (plan `W08:143`, `:1307-1312`):** `docs/capstone-report/{architecture-engineering-contract,specs-compliance-matrix,architecture-overview,claims-ledger}.md` and `docs/architecture/{ci-and-quality-gates,performance-scalability-review}.md`. Shared with:
   - #72, which edits the contract and the matrix; W-8 is already after #72.
   - E-3 Task 9 (`ci-and-quality-gates.md`).
   - F-5 F4 (`ci-and-quality-gates.md`, triggered by #72).
   - F-9 SHOWCASE (`claims-ledger.md`; lane F already serializes it).

   The plan's canonical order "W-8 → P4 F4" (`W08:170`) is dropped. F4 will usually land first because #72 lands before W-8, so W-8 rebases onto it and re-reads `:58`.
3. **Corrected anchors:** `modules/embeddings.py:18,34-35,56` (unchanged); product callers `api/documents.py:852` and `modules/rag.py:170`; `core/config.py:118` `embedding_dimensions`; dead `DEFAULT_EMBEDDINGS_MODEL` at `config/.env.example:87-89`; `.gitignore:85-86` (`/models/`); `scripts/download_models.py` subcommands at `:317-328` (no `embedding` yet).
4. **CI today:** `backend-tests` installs CPU torch (`ci.yml:50-52`) and still has no model-fetch step, so `test_api_rag_index_002b` passes in CI only through the implicit fetch W-8 removes. Task 4's explicit fetch step is still required.
5. **Interaction with RAG-RUNTIME-500:** W-8's `EmbeddingModelUnavailableError` subclasses `RuntimeError` (`W08 :427`), but Task 5 wraps it into `ModelUnavailableError` in `rag.py` (`W08 :1079-1081`), so the grounded route still returns 501, not RAG-RUNTIME-500's 503. HC-EMB-006c guards that.
6. **Runtime:** Task 4 needs one real network fetch (owner host or CI). Everything else is offline.

## G-C5 — HC-M11 NLI cross-encoder behind the default-off flag (design, no plan yet)

**Goal:** a local NLI cross-encoder behind the existing flag `use_llm_entailment`, default off. Flag off ⇒ legacy eval output byte-identical. No threshold change.

**Measured on main (new since the scaffold pack):**
- The flag is dead end to end. `core/config.py:157` defines `use_llm_entailment` and nothing reads it. `get_rag_module` builds `VerificationConfig(min_faithfulness_score=0.6, fail_on_contradiction=True)` (`api/assistant.py:205-218`), but `rag.py:1007` calls `verify_all_claims(claims_to_verify)` **without** a config. `verify_all_claims` then builds `VerifierAgent(None)` (`verifier_agent.py:470-484`), so `RAGModule.verifier`'s config (`rag.py:176`) never reaches claim verification.
- Passing `self.verifier.config` at `:1007` is behaviour-identical today, because production's values equal the `VerificationConfig` defaults (`verifier_agent.py:76-88`: 0.7, 1, True, 0.6, False).
- Hook: `_check_entailment` routes to `_check_entailment_llm` when the flag is on (`verifier_agent.py:223-224`); that body is a stub that calls the rules (`:304-317`).
- `faithfulness.py` needs **no edit**: `score_response(..., per_claim_entailment=...)` already exists (`:362-366`).

**Smallest design (ponytail):**

| # | File | Hunk | Ask-first |
|---|---|---|---|
| 1 | `src/backend/modules/rag.py:1007` | `verify_all_claims(claims_to_verify, self.verifier.config)` | no |
| 2 | `src/backend/api/assistant.py:210-213` | add `use_llm_entailment=app_settings.use_llm_entailment` | no |
| 3 | `src/backend/modules/verifier_agent.py:304-317` | body of `_check_entailment_llm` only: score `(source.text, claim)` with the cross-encoder, then map contradiction/entailment/neutral to `EntailmentResult`; model absent → `return self._check_entailment_rules(claim, source)` (today's exact behaviour) | **yes (GC5-ASKFIRST)** |
| 4 | `src/backend/modules/embeddings.py` | `load_local_cross_encoder()`: per-call `local_files_only=True` on a resolved local dir (Q-OFFLINE pattern, W-8's resolver), raising W-8's `EmbeddingModelUnavailableError` | no |
| 5 | `src/backend/scripts/download_models.py`, `config/model_manifest.json`, `core/config.py` (`nli_model_path`), `config/.env.example` | `nli` subcommand copied from W-8's `embedding` subcommand; revision + sha256 pin | no |

Skipped: feeding `per_claim_entailment` into `faithfulness.score_response` (a second `rag.py` hunk). Add it only if the owner wants the faithfulness score, not just the verifier, to change when the flag is on (open question 4).

**Test-first steps:**
1. RED: `tests/test_gc5_nli_flag.py::test_hc_gc5_001_flag_reaches_verifier`. With `use_llm_entailment=True` in `VerificationConfig`, a stubbed `_check_entailment_llm` must be called through `RAGModule.validate_response`. It fails today because of `rag.py:1007`.
2. RED: `test_hc_gc5_002_contradiction_fails_claim`. Use a fake cross-encoder returning "contradiction" for a claim the rules pass; with the flag on, `failed_claims == 1`.
3. `test_hc_gc5_003_offline_load_zero_sockets` (W-8's socket-guard pattern) and `test_hc_gc5_004_absent_model_falls_back_to_rules`.
4. Byte-identical proof with the flag off. Run before and after on the same tree base and save the outputs: `python scripts/legacy_eval_gate.py` (from #72), `python scripts/agent_eval_gate.py`, `pytest tests/test_phase4_ai_safety.py tests/test_hc_a1_agent_verification.py -q`. Then `diff` the saved outputs and record the exit codes (GATE-14: the agent gate may not exit on Windows).

**Acceptance:** 4 new tests pass; the flag-off diff is empty; `git diff origin/main -- src/backend/modules/faithfulness.py` is empty; the 0.6 grep (`rag.py:866`, `verifier_agent.py:85`) is unchanged; no weights in git.
**Rollback:** revert the PR. Flag off is today's path, and hunk 1 is value-identical.

## SAFE-CHAT-AGENT — owner ruling, then optional small PR

**Fact (re-read):** the agent guard's advice gate runs `classify_advice` on each draft sentence (`guard.py:103-104`). That classifier only matches question-shaped advice (`classifier.py:30-59`, `:73-89`). Drafts are templates, but they quote record text verbatim: `The note says: "<source_quote>"` (`nodes/draft.py:146-148`) and `"<quote>"` for medication changes (`:185-187`). A clinician note "Take 20 mg atorvastatin daily" is therefore shown. The legacy path's 11 patterns would catch it (`interpret_safety.py:49-71`, `take\s+\d+\s*(mg|…)`). PARA-R3-Q1 recorded that the agent path "emits no model prose", so the advice judge adds 0 recall there.

| Option | Change | Effect |
|---|---|---|
| **A (Recommended)** accept and close | none; owner row only | The patient keeps seeing their own clinician's quoted words. Consistent with PARA-R3-Q1. |
| B pattern floor in the guard | `guard.py` step 1 also tests each sentence against `InterpretationSafetyGuard.PROHIBITED_PATTERNS`, compiled once as `rag.py:178-181` already does (import only, no edit to `interpret_safety.py`); ~6 lines | Quoted notes that match a pattern ("Take 20 mg…", "discontinue…", "certainly") are replaced by `ESCALATE_TEMPLATE`. False positives on record text. |

If B: RED test `tests/agent/test_guard_prohibited_floor.py::test_hc_sca_001` (a draft sentence with a quoted dose escalates). Acceptance: `scripts/agent_eval_gate.py` golden set IDENTICAL; agent cache entries are in-process only, so a restart clears replays (`cache.py:21-23`). Rollback: revert.

## SAFE-CHAT-FALLBACK — owner ruling, no code recommended

**Fact:** the no-model knowledge fallback (`api/assistant.py:1311+`) returns seeded KB reference text, unscreened. Codex flagged a pattern match, "you have a cut" (`scripts/seed_knowledge_base.py:376`). The L1 measured 7 of 60 seeded KB fields matching a prohibited pattern (6 on "certain", 1 on "you have a cut"): false positives on curated reference text. The care-task and medication-change fallbacks (`:1175`, `:1239`) quote record text, the same class as SAFE-CHAT-AGENT.

| Option | Change |
|---|---|
| **A (Recommended)** accept: the fallback is curated reference text, not model output | owner row only |
| B screen the fallback with the 11 patterns | 7 of 60 analyte answers become `ESCALATE_TEMPLATE` (e.g. platelets) |
| C reword the 7 seed fields | `seed_knowledge_base.py` edit plus a re-seed path for existing installs |

**One decision with lane B's IBF-1.** Lane B's IBF-1 option (c) ("rewrite the 7 KB fields") is the same 7 seed fields as option C here. Lane B's open question "no lane owns BiomarkerKnowledge seed text" is answered here: **lane A owns the seed text.** The owner should answer SCF-RULING and IBF-1 together. If either answer chooses a seed rewrite, it is one lane-A PR (option C) that both items cite, and lane B writes no seed edit.

## SAFE-CHAT-HISTORY — owner ruling, no code recommended

**Fact:** turns persisted before SAFE-CHAT (PR #44, 2026-10-05) can hold prohibited text. One loader serves both replay (`get_session_history`, `api/assistant.py:421-444`) and prompt history (`chat`, `:771`): `_load_session_history` (`:262-273`). The prompt feed is not a trust boundary, because a client can already send arbitrary `history[]` (`:775-776`), and every new legacy answer is pattern-screened on output (`rag.py:838-843` → SAFE-CHAT branch `api/assistant.py:880-898`). The residual risk is replay display of old turns.

| Option | Change |
|---|---|
| **A (Recommended)** accept: new answers only | owner row only; same shape as the owner's PARA-R3-Q8 answer "No, new answers only" |
| B read-time mask | in `_load_session_history`, replace assistant turns that match a pattern with `ESCALATE_TEMPLATE`; no data rewrite; ~8 lines + 1 HTTP test via `route_client`; inherits SAFE-CHAT-FALLBACK's false positives on stored fallback turns |

## ASSIST-AGENT-DATES — agent path ignores chat date filters

**Fact (live impact):** `ExplainAssistant.tsx:176-177,320-321` shows date inputs and sends `from_date`/`to_date`. Agent mode is the default (`modules/agent/settings.py:19`), and `_serve_via_agent(question, profile_id, profile_db, db)` (`api/assistant.py:681-721`) takes no filters. So by default the dates are dropped; only the legacy call passes them (`:827-828`). #95 fixes parsing on the legacy path only. The semantic cache key has no filter fields (`cache.py:36-41`), so a filtered and an unfiltered ask of the same question share one entry. The agent also ignores `selected_analytes`, `selected_panel` and `document_category` (same class, recurring-failures #9), and the no-model fallback's `_fetch_latest_obs` (`api/assistant.py:1393`) ignores dates.

**Scope (owner AAD-ROW 2026-10-16, AAD-SEMANTICS 2026-10-17):** all four filters in the agent path plus the fallback's date window, one PR. `query_timeline`, `query_care_tasks`, `query_medication_changes` stay unfiltered (no legacy equivalent). AAD-SEMANTICS answer **ADD**: a selection adds to what the question asks about; it never hides it. Per filter:

| Filter | Legacy | Agent (this PR) |
|---|---|---|
| `from_date`/`to_date` | narrow `Observation.collected_at` (`rag.py:350-355`) and `Document.collection_date` (`:564-570`) | narrow the same 2 columns in `query_observations`, `compute_trend`, `retrieve_chunks` (both its text-match and its no-match fallback). NULL `collected_at` excluded when a bound is set (recurring-failures #7) |
| `selected_analytes` | **added** to the question's analytes for observation context (`rag.py:325-329`); **narrow** chunks to docs that have those analytes (`:572-579`) | `query_observations` with a planned `analyte`: rows of that analyte **OR** a selected analyte (case-insensitive), the asked analyte ordered first so the `limit` can never cut it. With no planned `analyte` the tool already returns every verified row, so "add" is a no-op there. `retrieve_chunks`: legacy narrowing |
| `selected_panel` | resolved by `NormalizeModule.get_panel_analytes` and merged into the analytes (`rag.py:1217-1223`) | the same resolution, then treated exactly as `selected_analytes`. An unknown panel resolves to nothing (no effect, no cache split) |
| `document_category` | narrows chunks via `DocumentCategory.category` (`rag.py:581-588`) | `retrieve_chunks`: the same narrowing. Nothing to add for observations |
| fallback `_fetch_latest_obs` | — | latest observation **within** the window (same `_parse_filter_date` bounds) |

Planner guard (`modules/agent/nodes/plan.py`, ~3 lines): the turn-2 `check_verification` follow-up fires when `query_observations` returned no row **of the asked analyte**, not "no rows at all". Without it, a selection would turn today's "value not yet verified" abstain for the asked analyte into an answer about a different analyte (the selection would hide what the question asks about). With no selection the two conditions are identical, so the golden set is unaffected.

**Not done, owner question AAD-TREND-ADD (PR body):** on a trend question the planner calls only `compute_trend` for the asked analyte. Adding the selected analytes there needs the planner (signature `(question, run_log)`) to see the selection and plan an extra `query_observations` call, which appends other analytes' values to a trend answer. That is a patient-visible change this plan does not justify, so trend answers get dates only. The asked analyte is never hidden.

`retrieve_chunks` is registered but today's deterministic planner never plans it, so its filters (dates, analytes, category) have no patient-visible effect yet; they are asserted at the tool.

**Design.** One frozen filter object instead of loose params (contracts I-18):

| File | Hunk |
|---|---|
| `src/backend/modules/agent/state.py` | `ChatFilters(BaseModel, frozen)`: `from_dt: datetime \| None`, `to_dt: datetime \| None` (naive UTC), `analytes: tuple[str, ...] = ()` (lowercased, deduplicated, sorted; selected ∪ panel), `category: str \| None`. All default empty |
| `src/backend/api/assistant.py` | `_chat_filters(request) -> ChatFilters` (parse once with `modules.rag._parse_filter_date`: malformed ⇒ ignored, no new 422s; panel via `get_panel_analytes`); `_serve_via_agent(question, profile_id, profile_db, db, filters: ChatFilters \| None = None)` passes it to `CacheKey` and `RunContext`; call site passes `_chat_filters(request)`; `_fetch_latest_obs` gets the window |
| `src/backend/modules/agent/graph.py` | `RunContext.filters: ChatFilters = field(default_factory=ChatFilters)` |
| `src/backend/modules/agent/cache.py` | `CacheKey.filters: ChatFilters = ChatFilters()` — an empty filter equals the default, so unfiltered keys are unchanged |
| `src/backend/modules/agent/tools/query_observations.py`, `compute_trend.py`, `retrieve_chunks.py` | read `getattr(ctx, "filters", None)` (ToolContext is a Protocol; test contexts may lack it) and apply the rows above |
| `src/backend/modules/agent/nodes/plan.py` | the planner guard above |

Rejected: routing filtered requests to legacy. It is 1 line, but it moves patients onto the model-prose path, needs a local model, and the no-model fallback ignores dates too.

**Test-first:** `src/backend/tests/test_assist_agent_dates_http.py`. Route tests go through `route_client` with the real `run_agent` against a real in-memory profile DB, asserting on the **cited observation ids**, so a filter that reached only the cache key and not the tool query still fails. Seed: verified glucose 2026-01-15 (`obs-g-jan`) and 2026-06-15 00:00 UTC (`obs-g-jun`), verified potassium and ferritin 2026-06, unverified `LDL`; two verified documents (2026-01 `lab`, 2026-06 `imaging`) with one chunk each. "RED" = fails on `aed9d50` with only the `ChatFilters` type added (no wiring).

| Id | Assertion | RED on main? |
|---|---|---|
| HC-AAD-001 | `from_date=2026-03-01`, "what is my glucose?" → cited == {`obs-g-jun`} | yes |
| HC-AAD-002 | same question unfiltered then with `from_date` → {jan, jun} then {jun} (cache split by dates) | yes |
| HC-AAD-003 ×4 | `+05:00` bounds: `from 04:30+05:00` → {jun}; `from 05:30+05:00` → {}; `to 04:30+05:00` → {jan}; malformed both → {jan, jun}, 200 | yes ×3; malformed case passes today (pins "ignored") |
| HC-AAD-004 | `retrieve_chunks` with `from_dt=2026-03-01` → only `doc-jun`, on the text-match path and on the no-match fallback | yes |
| HC-AAD-005 | trend question, `to_date=2026-03-01` → `compute_trend` cites {`obs-g-jan`} | yes |
| HC-AAD-006 | `selected_analytes=["Potassium"]` → cited == {g-jan, g-jun, k-jun} (added, glucose kept) | yes |
| HC-AAD-007 | `selected_panel="iron"` → cited == {g-jan, g-jun, fe-jun} | yes |
| HC-AAD-008 | "what is my ldl?" (LDL unverified) with `selected_analytes=["potassium"]` → same abstain text as without the selection, no citations | no: a guard for the planner change; fails against an ADD without it (break-it run in the PR body) |
| HC-AAD-009 | `retrieve_chunks` with `category="lab"` → only `doc-jan`, both paths | yes |
| HC-AAD-010 | `retrieve_chunks` with `analytes=("potassium",)` → only `doc-jun` | yes |
| HC-AAD-011 ×5 | cache key: for each of `from_date`, `to_date`, `selected_analytes`, `selected_panel`, `document_category`, a request differing only in that filter looks up a different `CacheKey` and does not return a sentinel planted under the unfiltered key | yes ×5 |
| HC-AAD-012 | no-model fallback (`ModelUnavailableError`), `to_date=2026-03-01` → the cited latest glucose is `obs-g-jan`, not `obs-g-jun` | yes |

**Expected collected delta: +19** (12 functions; 003 has 4 cases, 011 has 5).

**Acceptance:** 19 new tests pass; `scripts/agent_eval_gate.py` golden set IDENTICAL (empty filters ⇒ unchanged keys and queries); `scripts/legacy_eval_gate.py` unchanged; `tests/test_assistant_cache_version.py` and `tests/test_audit_order_guard.py` pass (add a `NAMED_DYNAMIC_EXCLUSIONS` row only if the new call in `_serve_via_agent` is unresolved). **Rollback:** revert. All new fields default to empty.

## RAG-RUNTIME-500 — inference failure on the grounded interpretation route

**Fact:** `POST /interpretations/observations/{id}/interpret-grounded` catches only `ModelUnavailableError` around `rag.query` (`api/interpretations.py:522-537`). An inference failure raises `RuntimeError` (`rag.py:1301-1303`, from `core/model_runner.py:159-212`) and escapes as an unhandled 500. The audit row was already written fail-closed (`:500-504`). Chat already maps any error to a fixed 500 detail (`api/assistant.py:955-962`).

**Design:** add after `:533-537`:
`except RuntimeError: logger.exception("Grounded interpretation inference failed", extra={"profile_id": session.profile_id}); raise HTTPException(503, detail=<fixed sentence>)`.
Never put `str(exc)` in the detail; it carries provider error text. About 6 lines.

**Test-first:** add `test_hc_rag_runtime_001_inference_failure_maps_to_503` to `src/backend/tests/test_safe_interp_grounded.py`. Reuse its `_rag` helper with `query.side_effect = RuntimeError("Failed to generate response: boom")` (same shape as `test_hc_safeinterp_006`, `:239`), through `route_client`. Assert 503, the detail equals the fixed sentence, `"boom"` is not in the body, and the grounded audit row exists. RED today: an unhandled exception, not 503.
**Acceptance:** `pytest tests/test_safe_interp_grounded.py -q` all pass; collected +1. **Rollback:** revert.
**Order:** `api/interpretations.py` and `tests/test_safe_interp_grounded.py` are shared with lane B's B-2 (HC-SIE-001), B-3 (audit reason `:591`, T4) and B-6 (question `:507-512`), and with B-5/W-7 (new route after `:603`).
- The hunks are disjoint: this item's `:533-537`, B-6's `:507-512` and B-3's `:591`. RAG-RUNTIME-500, B-2, B-3 and B-6 may land in any order; each later one rebases.
- RAG-RUNTIME-500 lands **before B-5 (W-7)**. W-7 is the large insertion, and it already maps runner `RuntimeError` to its template fallback (W07 plan HC-INT tests `:551`, `:1021`).
- W-8's 501 path is unaffected (W-8 point 5).

## Provides

1. `modules.agent.state.ChatFilters` (frozen: `from_dt`, `to_dt` naive UTC, `analytes: tuple[str, ...]`, `category`); `modules.agent.graph.RunContext.filters: ChatFilters`, read by agent tools via `getattr(ctx, "filters", None)` (ASSIST-AGENT-DATES).
2. `modules.agent.cache.CacheKey.filters: ChatFilters = ChatFilters()`; `api.assistant._serve_via_agent(question, profile_id, profile_db, db, filters: ChatFilters | None = None)` (ASSIST-AGENT-DATES).
3. `api.observations.TrendPoint.user_verified: bool = False`; frontend `TrendPoint.user_verified?: boolean` in `src/frontend/src/services/types.ts`; `UNVERIFIED_LABEL`, `TrendPointDot`, `UnverifiedTrendNote` in `src/frontend/src/components/TrendVerificationMarkers.tsx` (W-3 Tasks 1, 4).
4. Legacy RAG reads only `Observation.user_verified == True` (W-3 Task 2), and `Document.status == "verified"` chunks if O-5 is signed (Task 3).
5. `modules.embeddings.EmbeddingModelUnavailableError(RuntimeError)`, the offline local loader, `core.config.settings.embedding_model_path`, `download_models.py embedding`, `modules.rag.EMBEDDING_UNAVAILABLE_MESSAGE` (W-8). Also, from G-C5: `settings.use_llm_entailment` reaches `VerificationConfig` via `get_rag_module`, and `rag.py` calls `verify_all_claims(claims, self.verifier.config)`. The grounded route returns HTTP 503 with a fixed detail on `RuntimeError` (RAG-RUNTIME-500).

## Consumes

1. **#72 (W-4):** `api.assistant._legacy_serve_or_abstain(result: ValidatedResponse) -> ValidatedResponse`, `scripts/legacy_eval_gate.py`, the `legacy-evals` CI job. Merge waits on the owner's 20-question run (W4-20Q-HOST).
2. **#95 (ASSIST-UTC):** `modules.rag._parse_filter_date(value: str) -> Optional[datetime]` (naive UTC; `None` on `ValueError`/`TypeError`/`OverflowError`), and the `tests/test_assist_utc_http.py` real-`rag.query` HTTP fixture pattern.
3. **Lane E E-3 (W-11a PR-3)** (`ci.yml`, `ci-and-quality-gates.md`) before W-8; lane E's `ci.yml` order E-3 → #74 → #72 → W-8. **Lane B B-5 (W-7)** after RAG-RUNTIME-500 on `api/interpretations.py`. **#74 (lane E E-4)** before W-3 Task 5 on `TrendsDashboard.tsx`; #74 does not touch `InterpretedTrendChart.tsx` or `types.ts`.
4. **Lane B B-3 (PARA-1-R3 advice judge)** after `rag.py:1276`, plus `ValidatedResponse.prohibited_reason` and `api/assistant.py` audit reason `:932` (post-#72). Its hunks are disjoint from W-3 (`rag.py:325-334`, `:551-555`), W-8 (`:170`, the Task 5 wrap), G-C5 (`:1007`), ASSIST-AGENT-DATES (`api/assistant.py:681-721`, `:793`) and W-3 Task 7 (`:1367`).
   - Order on `modules/rag.py`: #95 → W-3 → W-8 → G-C5. B-3 has no fixed slot: it stays a parked draft until B-4 is signed, rebases on each landing, and lands when ready (reconciler ruling R-4, [contracts](contracts.md#e-rulings-on-peer-review-conflicts)). The later PR always rebases and re-greps its anchors.
   - At most one non-draft PR at a time on each of `rag.py` and `api/assistant.py`; a parked draft (B-3) does not hold the file (contracts §b rules 1–2, R-5).
   - Judge fake: see W-3 point 9.
5. `tests/support/routes.py::route_client`: lane C C-P7 adds only `profile_name: str = "T"`, and existing callers are unchanged. Lane-A tests keep overriding `get_profile_db_session` on `client.app.dependency_overrides`, which is the pattern C-P7 endorses. No lane-A test makes a cross-profile 403, so lane E's GATE-12 patch (`core.database.async_session_maker`) does not apply. Any later test that does make one adopts lane E's 403 pattern.
6. **Lane D D-0** merges #95 and measures the count chain before any lane-A branch is cut.

## Owner gates

| Gate | Item | Question (short) | State |
|---|---|---|---|
| O-5, O-1 (= VERIFIED-FALLBACK), O-2 veto | W-3 (+W-8 for O-1) | as in W03 §10 | unsigned |
| O-3 (= IUV-1, lane B B-6), O-4 (= MSG-UNVERIFIED, lane A if opened) | not W-3 blockers | as in W03 §10 | unsigned |
| Q-FC, Q-HASH | W-8 | as in W08 §Owner sign-offs | unsigned (Q-OFFLINE, EMB-REV answered 2026-10-08) |
| Q5a, Q5b, GC5-MODEL, GC5-PLAN | G-C5 | scaffold pack §3 | unsigned |
| **GC5-ASKFIRST** | G-C5 | approve the exact `verifier_agent.py:304-317` hunk (ask-first file, CLAUDE.md §1) | unsigned; `faithfulness.py` is not edited |
| SCA-RULING | SAFE-CHAT-AGENT | A accept / B pattern floor in `guard.py` | not asked |
| SCF-RULING | SAFE-CHAT-FALLBACK | A accept / B screen / C reword seed (ask together with lane B IBF-1; same 7 seed fields) | not asked |
| SCH-RULING | SAFE-CHAT-HISTORY | A new answers only / B read-time mask | not asked |
| AAD-ROW, AAD-SEMANTICS | ASSIST-AGENT-DATES | scope; narrow or add? | answered 2026-10-16 (all four filters) and 2026-10-17 (ADD). AAD-TREND-ADD open (trend answers) |
| RR500-MAP | RAG-RUNTIME-500 | 503 + fixed sentence (proposed: "The explanation could not be generated right now. Please try again.") | not asked |

Ask-first files touched by this lane: only `modules/verifier_agent.py` (G-C5). `interpret_safety.py`, `redaction.py`, `faithfulness.py`, `core/auth.py` and auth/encryption code stay read-only. SAFE-CHAT-AGENT option B only imports `PROHIBITED_PATTERNS`.

## Open questions

1. ~~Collected count baseline~~: resolved by L0. The baseline is 1574, re-measured per PR after its final rebase (ground rule 8).
2. ~~ASSIST-AGENT-DATES scope~~: resolved by owner AAD-ROW (all four filters plus the fallback window) and AAD-SEMANTICS (ADD).
3. ~~Tools without a legacy equivalent~~: resolved by AAD-ROW: they stay unfiltered.
4. G-C5: with the flag on and the model absent, fall back to rules (designed; never weaker than today) or fail closed (mark claims unverified, so every legacy answer abstains)? Should the faithfulness score also be fed in v1? Is a cross-encoder outside the ModelRunner rule (not an LLM, like embeddings)?
5. ~~W-3 vs #74~~: #74 is first (lane E E-4 is closer to merge). W-3 Task 5 rebases onto it and re-reads `chartData` and `Line`.

## Peer review (2026-10-15)

Each change was checked against the repo on `3b2236c` and on the open PR branches. No owner approval was added.

| # | Change in this doc | Peer source | Evidence |
|---|---|---|---|
| 1 | Baseline 1574, measured after the final rebase; D-0 runs first | L0 note 1; lane D D-0 | `CLAUDE.md:30`; `orchestration.md:47` (SLOT-RULE) |
| 2 | W-8 `ci.yml` order follows lane E (E-3 → #74 → #72 → W-8); #72 is a rebase trigger only | lane E §provides 1 | lane E doc `:137` |
| 3 | W-8 docs files listed; "W-8 → P4 F4" dropped | lane F F-5, F-9; lane E E-3 Task 9 | `W08:143`, `:170`, `:1307-1312`; P04 `:996` |
| 4 | W-3 O-3 → lane B B-6 (IUV-1); O-4 MSG-UNVERIFIED owned by lane A if opened; neither blocks W-3 | lane B B-6 | `W03:66`, `:1332-1333`; program `:460-461` |
| 5 | W-3 PR body meets the Variant-I contract | lane F §provides 2 | `W03:379` |
| 6 | W-3 judge fake vs B-3 | lane B B-3 | `rag.py:1270-1276`; `W03:534-563` |
| 7 | Seed text owned by lane A; SCF-RULING and IBF-1 asked together | lane B B-2 IBF-1 (c), lane B open question 7 | lane B doc `:46-55` |
| 8 | `api/interpretations.py` order: RAG-RUNTIME-500 / B-2 / B-3 / B-6 any order, all before B-5 | lane B | hunks `:507-512`, `:533-537`, `:591`; W07 `:551`, `:1021` |
| 9 | `rag.py` / `api/assistant.py` order with B-3 | lane B B-3 | lane B doc `:67-79` |
| 10 | `route_client` unchanged for lane A; GATE-12 not applicable | lane C C-P7, lane E Q-E3 | lane C doc `:85`, `:241` |

Checked with no conflict found:
- No lane-A migration.
- No new interface is consumed from lanes C, D or F.
- #82, #84, #97 and #99 do not touch lane-A files.
- #74 touches `TrendsDashboard.tsx` only.
- Wearables (#94) keeps out of `rag.py`, `api/observations.py` and `TrendsDashboard.tsx` (W-3 point 6).
