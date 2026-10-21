# Lane A — RAG + assistant: build-program design

**Last Updated:** 2026-10-20 (PR #202 review round 2: verifier-on column for LCP-HEADERLESS, two shapes served today; (b) rule narrowed; CFR-CACHE-TZ in progress #204); 2026-10-20 (PR #202 review round 1: LCP-HEADERLESS re-measured on `5750a97`, HC-LCPH-003 RED ×3, labels split into LCP-HL-LABELS; #185 merged, so W-8-FC-NOTICE and LLM-PATH-LOG are ready); 2026-10-19 (follow-ups planned: LCP-HEADERLESS, EMB-LOAD-LOG-PATH, LLM-PATH-LOG); 2026-10-19 (review round 2 fixes: HC-EMB-005b, HC-EMB-009a; G-C5 OL-1..3 answered); 2026-10-18 (G-C5 plan linked, PR #183); 2026-10-17 (CHAT-FACT-ROUTING, LOCAL-HF-HUB, INTERP-ADVICE-WORDING planned)
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
| G-C5-PLAN | DOCS | program row `:411`, `:450`; [scaffold pack](../../../audit/2026-09-25/waves/scaffold/G-C5.md) | [GC5](../2026-10-18-GC5-hc-m11-nli-flag-off.md) (PROPOSED) | PR #183 (draft) | Q5b and GC5-PLAN signed 2026-10-17; W-8 merged |
| G-C5 | PRODUCT | same | [GC5](../2026-10-18-GC5-hc-m11-nli-flag-off.md) (PROPOSED) | blocked-on-item | G-C5-PLAN merge; plan OL-1..3 answered 2026-10-19 (`owner-decisions-2026-09-27.md:269-271`: confirm the pin; B, fail closed; A, load directly). W-8 and W-4 merged |
| SAFE-CHAT-AGENT | OWNER (→ PRODUCT if B) | program owner item `:498` (a); [wave-3-L1-A](../../../audit/2026-09-25/waves/wave-3-L1-A.md) "Other paths" 2 | none | blocked-on-owner | SCA-RULING |
| SAFE-CHAT-FALLBACK | OWNER | `:498` (b); wave-3-L1-A Codex diff row | none | blocked-on-owner | SCF-RULING |
| SAFE-CHAT-HISTORY | OWNER | `:498` (c); wave-3-L1-A "Other paths" 5 | none | blocked-on-owner | SCH-RULING |
| ASSIST-AGENT-DATES | PRODUCT | #95 body "Scope note"; `docs/reviews/2026-10-14/ASSIST-UTC-diff-codereview.md` (on `fix/assistant-utc`) MEDIUM row | none | ready | AAD-ROW + AAD-SEMANTICS answered; #95 merged (provides the parser) |
| RAG-RUNTIME-500 | PRODUCT | program owner item `:495`; wave-3-L1-A Phase 4 owner item 4 | none | blocked-on-owner | RR500-MAP; serial with W-7 on `api/interpretations.py` |
| CHAT-FACT-ROUTING | PRODUCT | queue status 2026-10-16 third batch (MM-4) | [below](#chat-fact-routing--the-agent-cannot-find-real-lab-rows-by-name-open-questions-dump-raw-facts) | done (#162) | CFR-FORMAT (a), answered 2026-10-18 |
| LOCAL-HF-HUB | PRODUCT (or folds into W-8) | queue status 2026-10-16 third batch (MM-4); LOCAL-01 | [below](#local-hf-hub--embeddings-may-fetch-from-the-hugging-face-hub-at-runtime-local-first) | blocked-on-owner | LHH-SCOPE; (a) = W-8's blockers |
| INTERP-ADVICE-WORDING | PRODUCT (seed text) | queue status 2026-10-16 third batch (MM-4); no-medical-advice invariant | [below](#interp-advice-wording--a-seeded-kb-sentence-suggests-medication) | done (#156) | IAW-WORDING (b), answered 2026-10-18 |
| W-8-FC-NOTICE | PRODUCT | PR #168 Codex [high] 1 + L0 ruling | [below](#w-8-fc-notice--a-hash-only-vault-with-no-embedding-model-abstains-silently-instead-of-returning-the-q-fc-notice) | in progress (#203) | LEGACY-CITE-PROMPT (#185) merged 2026-10-20 (`5750a97`), so `rag.py` is free; re-grep the `rag.py` anchors in Task 0 |
| REPROCESS-ATOMIC | PRODUCT | PR #168 Codex [high] 2 + L0 ruling | [below](#reprocess-atomic--reprocess-commits-the-chunk-delete-when-the-replacement-row-build-fails) | ready | — |
| W-8-HARDEN | PRODUCT | PR #168 Codex mediums + L0 ruling | [below](#w-8-harden--model-path-in-logs-weights-only-checksum-partial-left-after-an-exception) | blocked-on-item | REPROCESS-ATOMIC (shared test file, reused harness) |
| CFR-CACHE-TZ | PRODUCT | PR #162 follow-ups 1-2 | [below](#cfr-cache-tz--the-agent-cache-key-ignores-the-profile-time-zone-abbreviation-analytes-get-title-case-names) | in progress (#204) | — (#185 merged 2026-10-20) |
| LCP-HEADERLESS | PRODUCT | owner LCP-HEADERLESS (a), `owner-decisions-2026-09-27.md:275`; #185 open MINOR 1 and comment 6270643786 | [below](#lcp-headerless--the-legacy-parser-finds-headers-anywhere-drops-text-before-them-and-never-checks-headerless-text-for-citations) | blocked-on-owner | #185 merged (`5750a97`); owner LCP-HL-SCOPE and LCP-HL-LABELS (then LCP-HL-DIFF, merge) |
| EMB-LOAD-LOG-PATH | PRODUCT | #196 L0 ruling (comment 6267273354); #196 and #192 review MINORs | [below](#emb-load-log-path--sentence-transformers-logs-the-model-path-at-info-the-path-leak-tests-look-only-at-warning-takes-emb-harden-minors-and-reprocess-007c-reach) | ready | — |
| LLM-PATH-LOG | PRODUCT | #196 reviews (LLM model paths at INFO) | [below](#llm-path-log--the-two-llm-loaders-log-the-model-path-at-info) | ready | #185 merged (`5750a97`); never beside B-5 |
| EMB-LOG-M7 | PRODUCT (test only) | PR #214 review MINOR (mutant M7) | [below](#emb-log-m7--the-logger-restore-tests-never-start-at-notset-so-mutant-m7-survives) | ready | — |
| LLM-PATH-LOG-M2M3 | PRODUCT | PR #208 review M2/M3; L0 handoff 2026-10-20 §3 item 4 | [below](#llm-path-log-m2m3--six-more-loader-log-lines-can-carry-the-model-path) | ready | never beside B-5 |

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
10. **Plan delta (2026-10-17, PR #136 Task 0 block): `tests/test_assist_utc_http.py` joins the file list.** Run 1 stopped because Task 2's filter (O-5, signed: "Yes, verified only") hides the one observation HC-ASSIST-UTC-001 seeds: its fixture `Observation(...)` (`tests/test_assist_utc_http.py:88-92`) leaves `user_verified` at the model default `False` (`models/observation.py:80`), while its `Document` is already `status="verified"` (`:83`). Measured on the PR head `a4d71af`: `scripts/pyslot.sh env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/ -q -p no:cacheprovider` → `10 failed, 1716 passed`; all 10 are the `*_includes` / `*_ignored` cases of HC-ASSIST-UTC-001, each `AssertionError: <case>: observation filtered out`. The four `*_excludes` cases pass. The only change licensed: add `user_verified=True` to that one `Observation(...)` in the fixture. HC-ASSIST-UTC-001 tests date filtering, not verification, so the fixture now seeds a row that the signed D4 scope lets chat read. The 14 cases, their ids, and every assertion stay as they are. Unverified rows staying out is HC-VER-001…003's job, not this test's. No new test ids. Expected delta: backend collected **+5** for W-3 overall (1721 → 1726, measured as 1716 + 10 above), and **0** from this change. Vitest unchanged (+8 for W-3). Contracts: §b already gives W-3 ownership of this file; I-13 gains one sentence on the fixture consequence.

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

> Plan: [2026-10-18-GC5-hc-m11-nli-flag-off.md](../2026-10-18-GC5-hc-m11-nli-flag-off.md) (PROPOSED, PR #183). Its line numbers and the absent-model decision (OL-2) supersede the design text below.

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
| 3 | `src/backend/modules/verifier_agent.py:304-317` | body of `_check_entailment_llm` only: score `(source.text, claim)` with the cross-encoder, then map contradiction/entailment/neutral to `EntailmentResult`; model absent: see the [plan](../2026-10-18-GC5-hc-m11-nli-flag-off.md) OL-2 (answered B, fail closed, `owner-decisions-2026-09-27.md:270`) | **yes (GC5-ASKFIRST)** |
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

Asked-analyte rule (in `query_observations`, not the planner): when a selection is present but the result holds **no row of the asked analyte**, the tool returns no rows, exactly as without a selection. Reason: `reflect` drafts as soon as any act returned rows (`nodes/reflect.py::_has_grounding`), so selected-analyte rows alone would skip the planner's `check_verification` follow-up and turn today's "value not yet verified" abstain for the asked analyte into an answer about a different analyte. A planner-only guard is dead code for that reason (found by HC-AAD-008 during build). Cost: when the asked analyte has no verified in-window row, the selection adds nothing, which is today's behaviour; the conservative choice for a safety signal. Owner question AAD-ABSENT-ADD (PR body) asks whether to go further.

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

Rejected: routing filtered requests to legacy. It is 1 line, but it moves patients onto the model-prose path, needs a local model, and the no-model fallback ignores dates too.

**Test-first:** `src/backend/tests/test_assist_agent_dates_http.py`. Route tests go through `route_client` with the real `run_agent` against a real in-memory profile DB, asserting on the **cited observation ids**, so a filter that reached only the cache key and not the tool query still fails. Seed: verified glucose 2026-01-15 (`obs-g-jan`) and 2026-06-15 00:00 UTC (`obs-g-jun`), verified potassium and ferritin 2026-06, unverified `LDL`; two verified documents (2026-01 `lab`, 2026-06 `imaging`) with one chunk each. "RED" = fails on `aed9d50` with only the `ChatFilters` type added (no wiring).

| Id | Assertion | RED on main? |
|---|---|---|
| HC-AAD-001 | `from_date=2026-03-01`, "what is my glucose?" → cited == {`obs-g-jun`} | yes |
| HC-AAD-002 | same question unfiltered then with `from_date` → {jan, jun} then {jun} (cache split by dates) | yes |
| HC-AAD-003 ×6 | `+05:00` bounds: `from 04:30+05:00` → {jun}; `from 05:30+05:00` → {}; `to 04:30+05:00` → {jan}; malformed both → {jan, jun}, 200; bound equal to the stored instant is inclusive (`from` → {jun}, `to` → {jan, jun}) | yes ×4; malformed and `to`-equal pass today (pin "ignored" / inclusive) |
| HC-AAD-004 | `retrieve_chunks` with `from_dt=2026-03-01` → only `doc-jun`, and `to_dt=2026-03-01` → only `doc-jan`, on the text-match path and on the no-match fallback | yes |
| HC-AAD-005 ×2 | trend question: `to_date=2026-03-01` → `compute_trend` cites {`obs-g-jan`}; `from_date=2026-03-01` → {`obs-g-jun`} | yes ×2 |
| HC-AAD-006 | `selected_analytes=["Potassium"]` → cited == {g-jan, g-jun, k-jun} (added, glucose kept) | yes |
| HC-AAD-007 | `selected_panel="iron"` → cited == {g-jan, g-jun, fe-jun} | yes |
| HC-AAD-008 | "what is my ldl?" (LDL unverified) with `selected_analytes=["potassium"]` → same abstain text as without the selection, no citations | no: a guard for the asked-analyte rule; fails against an ADD without it (break-it run in the PR body) |
| HC-AAD-009 | `retrieve_chunks` with `category="lab"` → only `doc-jan`, both paths | yes |
| HC-AAD-010 | `retrieve_chunks` with `analytes=("potassium",)` → only `doc-jun` | yes |
| HC-AAD-011 ×5 | cache key: for each of `from_date`, `to_date`, `selected_analytes`, `selected_panel`, `document_category`, a request differing only in that filter looks up a different `CacheKey` and does not return a sentinel planted under the unfiltered key | yes ×5 |
| HC-AAD-012 | no-model fallback (`ModelUnavailableError`), `to_date=2026-03-01` → the cited latest glucose is `obs-g-jan`, not `obs-g-jun`; `from_date=2026-07-01` → none cited | yes |
| HC-AAD-013 | `query_observations(analyte="potassium", limit=1)` with glucose selected → returns `obs-k-jun` (asked rows ordered first; natural order puts glucose first) | yes (no filters on main) |
| HC-AAD-014 | a verified selected potassium row with NULL `collected_at` → the request stays on the agent path (`agent:` summary) and cites {g-jan, g-jun, k-jun} | yes |

**Expected collected delta: +24** (14 functions; 003 has 6 cases, 005 has 2, 011 has 5). Raised from +19 after review round 1 (untested predicates, limit ordering, NULL `collected_at` on a selected row).

**Acceptance:** 24 new tests pass; `scripts/agent_eval_gate.py` golden set IDENTICAL (empty filters ⇒ unchanged keys and queries); `scripts/legacy_eval_gate.py` unchanged; `tests/test_assistant_cache_version.py` and `tests/test_audit_order_guard.py` pass; `tests/test_audit_order.py::_agent_stub` (a stand-in for `_serve_via_agent`) gains `filters=None` (add a `NAMED_DYNAMIC_EXCLUSIONS` row only if the new call in `_serve_via_agent` is unresolved). **Rollback:** revert. All new fields default to empty.

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

## CHAT-FACT-ROUTING — the agent cannot find real lab rows by name; open questions dump raw facts

**Source:** queue status 2026-10-16 (third batch, MM-4). Planned on `origin/main` @ `b54f105`.

**Root cause (verified on `b54f105`; not the model):** the agent path is deterministic by design (S1/S2: `nodes/plan.py:188` "Deterministic plan", `nodes/draft.py:262`), so "answers without the model" is expected there. The patient-visible bug is a **name mismatch**. `_ANALYTE_KEYWORDS` (`modules/agent/nodes/plan.py:28-45`) maps question words to labels: `ldl` → `"LDL"`, `hdl` → `"HDL"`, `cholesterol` → `"Cholesterol"`, `a1c` → `"HbA1c"`, `vitamin d` → `"Vitamin D"`. The tools match those labels with `analyte_canonical ILIKE <label>`: `query_observations.py:60`, `compute_trend.py:59`, `check_verification.py:74`. Ingest stores the `NormalizeModule.ANALYTE_SYNONYMS` keys instead (`modules/normalize.py:165-195`): `ldl_cholesterol`, `hdl_cholesterol`, `total_cholesterol`, `hba1c`, `vitamin_d`. So with a real vault:
- "Is my LDL cholesterol high?" finds 0 rows, then runs `check_verification("LDL")`, finds 0 rows, and abstains, even though `ldl_cholesterol` is verified.
- "Explain my cholesterol results." finds `"Cholesterol"` ≠ `total_cholesterol` and gets the same result.
- The agent goldens (`tests/agent/golden/*.json`, seeded by `tests/agent/conftest.py:127` with `analyte_canonical=<label>`) store the labels, so the eval gate never saw it.
- With no analyte in the question, `query_observations` runs unfiltered, and `draft()` writes one sentence per row (`draft.py:69-80`): `Your verified {analyte_canonical} result was … (collected {collected_at})`. The result is raw keys such as `ldl_cholesterol` and a raw `datetime` string.

**Design.**
1. **Task 1–2 (no gate; a bug).** Add `NormalizeModule.canonical_keys_for(term: str) -> tuple[str, ...]` to `modules/normalize.py`, which already owns canonicalisation. It returns every key whose key, its space form, or a synonym equals `term.lower()`. The 3 tools match `func.lower(Observation.analyte_canonical).in_({label.lower(), *canonical_keys_for(label)})`. Labels keep matching, so the 74 goldens are unchanged, and real keys match too. Leave the `_ANALYTE_KEYWORDS` labels as they are.
2. **Task 3 (gate CFR-FORMAT; what patients read).** Recommended option (a): a sentence names the analyte by `NormalizeModule.DISPLAY_NAMES` (`normalize.py:222`, else key → title case, as `:273`). It dates the result by the profile-local date (`%b %d, %Y`; D lane `to_local` + `profile_timezone_name`). An open question with no analyte drafts the **latest** verified value per analyte, at most 10 analytes, most recent first, each sentence cited.

**Owner gate CFR-FORMAT** (Task 3 only; Tasks 1–2 do not wait):
- **(a) Recommended:** display names, local dates, latest value per analyte, cap 10.
- (b) Display names and local dates only; keep one sentence per verified row.
- (c) No format change; ship Tasks 1–2 only.
- Model-written agent answers stay out of scope. They need an LLM drafting node behind B-3's advice judge, which is a separate plan.

**Test-first** (`src/backend/tests/agent/test_agentic_queries.py`, `HC-CFR-NNN`; real `run_agent` on the in-memory profile DB of `tests/agent/conftest.py`, seeding **ingest keys**; RED on `b54f105`):

| Id | Assertion | RED? |
|---|---|---|
| HC-CFR-001 | verified `ldl_cholesterol` 138 → "Is my LDL cholesterol high?" ends `answer` and cites that observation id | yes (abstains) |
| HC-CFR-002 | verified `total_cholesterol` → "Explain my cholesterol results." cites it | yes |
| HC-CFR-003 | two verified `ldl_cholesterol` rows → "How has my LDL changed over time?" → `compute_trend` cites both | yes |
| HC-CFR-004 | **unverified** `ldl_cholesterol` → still abstains with the "not yet verified" reason (the `check_verification` path now finds the row) | yes (today: the no-data reason) |
| HC-CFR-005 | guard: every `_ANALYTE_KEYWORDS` value has `canonical_keys_for(value) != ()` | yes (no helper) |
| HC-CFR-006 (Task 3) | the sentence for `ldl_cholesterol` says `LDL Cholesterol`, not `ldl_cholesterol` | yes |
| HC-CFR-007 (Task 3) | `collected_at` `2026-01-16 01:00` (naive UTC), profile LA → the sentence says `Jan 15, 2026`, no `:` time | yes |
| HC-CFR-008 (Task 3, a) | 15 verified analytes, 2 rows each → an open question drafts 10 sentences, one per analyte, the latest of each | yes |

**Files:** `src/backend/modules/normalize.py`, `src/backend/modules/agent/tools/query_observations.py`, `src/backend/modules/agent/tools/compute_trend.py`, `src/backend/modules/agent/tools/check_verification.py`, `src/backend/modules/agent/nodes/draft.py` (Task 3), `src/backend/tests/agent/test_agentic_queries.py`.

**Expected collected delta:** +5 (Tasks 1–2); +8 with Task 3 (a); +7 with (b).

**Acceptance:** the new tests; `~/venvs/asclexis-311/bin/python ../../scripts/agent_eval_gate.py` (from `src/backend`) PASS on all 74 golden cases (the gate is never edited); `pyt tests/agent/ tests/test_assist_agent_dates_http.py tests/test_biomarker_assistant.py -q` 0 failed; HC-AAD-* unchanged. Full suite per RUNBOOK §6. **Rollback:** revert.

**Order:** none of B-3, W-3, W-8, G-C5 or LEGACY-CITE-PROMPT edits these files. ASSIST-AGENT-DATES (#119) is merged, so rebase on its `query_observations` hunk.

## LOCAL-HF-HUB — embeddings may fetch from the Hugging Face Hub at runtime (local-first)

**Source:** queue status 2026-10-16 (third batch, MM-4). `docs/features/TASK_LIST.md:91` has the same log line.

**Fact (`b54f105`):** `EmbeddingsModule._ensure_initialized` calls `SentenceTransformer(self.config.model_name)` with the bare name `all-MiniLM-L6-v2` (`modules/embeddings.py:55-56`). With no local copy, `huggingface_hub` resolves the name online. That is the "unauthenticated requests" warning and a local-first violation, recorded since 2026-09-27 as LOCAL-01 (`docs/capstone-report/specs-compliance-matrix.md:41`). No product code sets `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE` or `local_files_only`. **Not verified:** that the request happens at *startup*. `main.py:31-70` lifespan does not build `EmbeddingsModule`; the call sites are lazy (`modules/rag.py:184` via `get_rag_module`, `api/documents.py:852`). The likely trigger is the first chat, interpret or index request.

**This is W-8's scope.** The W-8 plan (`docs/plans/2026-09-27-W08-bundled-embedding-model.md`) loads one local directory with `local_files_only=True`, fails closed, and never sets `HF_HUB_OFFLINE` in product code. That last rule implements owner Q-OFFLINE "per call" (`owner-decisions:87`), because a process-wide flag would also break the sanctioned GGUF download (`api/model_settings.py:902-937`). W-8 is blocked on W-3 and on owner Q-FC and Q-HASH (lane A §W-8).

**Owner gate LHH-SCOPE:**
- **(a) Recommended:** no separate PR. Fold the row into W-8 and add one startup check to W-8's tests (HC-LHH-001 below). The interim leak stays, and is recorded, until W-8 merges.
- (b) Interim PR now: `SentenceTransformer(name, local_files_only=True)`, loading from the local HF cache only. On a cache miss the module takes today's `except Exception` branch (`embeddings.py:66-69`), which means hash-vector fallback, so retrieval quality silently drops on a fresh install. That pre-empts Q-FC (fail closed), which is unsigned.
- (c) Interim PR that fails closed on a cache miss. This is W-8 Task 2 without the bundling, and it needs Q-FC.

**Test-first (both options):**

| Id | File | Assertion | RED? |
|---|---|---|---|
| HC-LHH-001 | `src/backend/tests/test_embedding_no_network.py` (new) | with `socket.socket.connect` patched to record and refuse non-loopback addresses, and `HF_HOME` set to an empty `tmp_path`, `EmbeddingsModule()._ensure_initialized()` makes **no** non-loopback connect attempt (`sentence_transformers` absent → `pytest.importorskip`) | yes (it tries the hub) |
| HC-LHH-002 | same | `TestClient(main.app)` startup with the same guard (lifespan only, no request) → no non-loopback connect attempt | Task 0 finds out; if it passes on `main`, the row's "startup" wording is corrected in the PR body, and the guard stays |

**Files:** (a) W-8's list plus `src/backend/tests/test_embedding_no_network.py`; (b)/(c) `src/backend/modules/embeddings.py` and the new test. **Expected collected delta:** +2. **Acceptance:** HC-LHH-001/002; `pyt tests/test_rag_pipeline.py -q` same pass/fail as Task 0 (`test_api_rag_index_002b` is the environmental one; its 0.7 bar is never lowered); `grep -rn "HF_HUB_OFFLINE" src/backend --include=*.py | grep -v tests/` prints nothing. **Rollback:** revert.

## INTERP-ADVICE-WORDING — a seeded KB sentence suggests medication

**Source:** queue status 2026-10-16 (third batch, MM-4), flagged for owner review against the no-medical-advice invariant. Lane A owns the KB seed text (§SAFE-CHAT-FALLBACK).

**Fact (`b54f105`):** `src/backend/scripts/seed_knowledge_base.py:106`, LDL `high_interpretation`: "Elevated LDL cholesterol increases your risk of plaque buildup in arteries. **Lifestyle changes and possibly medication may help reduce this risk.**" The template path appends it to every high-LDL card (`modules/interpret.py:600`). It also goes into the LLM prompt (`:799`), the RAG context (`modules/rag.py:502`) and the chat fallback (`api/assistant.py:1510`). `interpret_safety` does not catch it: its medication patterns are `prescribe`, `should take`, `must take`, `start taking`, `stop taking` and dosing (`interpret_safety.py:54-59`). The owner's IBF-1 + SCF-RULING "Accept" (`owner-decisions:187`) covered the 7 fields that **match** a pattern. This sentence matches none, so that answer does not cover it. Similar fields: glucose `high_interpretation` "…lifestyle modifications may be recommended." (`:223`), and the `intervention_text` rows (`:541-595`, "Consider …"), which recommendation cards show as lifestyle suggestions.

**Existing installs keep the old text:** `seed_biomarker_knowledge` skips rows that already exist (`seed_knowledge_base.py:799-812`). A seed edit alone reaches only new installs.

**Owner gate IAW-WORDING** (text patients read):
- **(a) Recommended:** replace the second sentence with an educational one: "Elevated LDL cholesterol increases your risk of plaque buildup in arteries. Your healthcare provider can explain what this result means for you." Also rewrite rows in existing installs whose text still **equals** the old default; a row someone edited is left alone.
- (b) Option (a), plus the glucose sentence `:223` → "Elevated fasting glucose may indicate prediabetes or diabetes. Your healthcare provider can explain whether further testing is needed."
- (c) Keep the wording (educational enough); close the row.
- Out of scope either way: the `intervention_text` rows and any new `interpret_safety` pattern (ask-first file).

**Design (a/b):** edit the seed dict. Add `_TEXT_REVISIONS: tuple[tuple[str, str, str, str], ...]`, holding (`analyte_canonical`, field, old exact text, new text). `seed_biomarker_knowledge` applies a revision only where the stored field equals the old text: idempotent, no migration, master DB only. It returns the count, logged with the existing seed log line.

**Test-first** (`src/backend/tests/test_biomarker_assistant.py`, next to the seed tests `:85-151`; RED on `b54f105`):

| Id | Assertion | RED? |
|---|---|---|
| HC-IAW-001 | the seed data's `ldl_cholesterol.high_interpretation` contains no `medication` (and, under b, glucose's contains no `lifestyle modifications may be recommended`) | yes |
| HC-IAW-002 | a master DB holding the **old** LDL row → after `seed_all(skip_db_init=True)` the row has the new text | yes |
| HC-IAW-003 | a row whose text was edited (≠ old default) → unchanged after `seed_all` | no (pin) |
| HC-IAW-004 | over HTTP (`route_client`), the template interpretation of a verified high LDL observation → `interpretation_text` contains no `medication` | yes |

**Files:** `src/backend/scripts/seed_knowledge_base.py`, `src/backend/tests/test_biomarker_assistant.py`. **Expected collected delta:** +4. **Acceptance:** the 4 tests; `pyt tests/test_biomarker_assistant.py tests/test_safe_interp_grounded.py tests/test_interpret_safety_adversarial.py tests/test_phase4_ai_safety.py -q` 0 failed; `~/venvs/asclexis-311/bin/python scripts/measure_prohibited_patterns.py` count does not rise. **Rollback:** revert, plus a reverse revision tuple if any install already took the new text.

## Follow-ups found 2026-10-18 (planned 2026-10-19 on `origin/main` @ `a9978e8`)

Four rows from the W-8 (#168) Codex review and the CHAT-FACT-ROUTING (#162) notes. Each fact below was re-checked on `a9978e8`. The repros ran through `scripts/pyslot.sh` from a scratchpad test file (not committed). `pyt` = `scripts/pyslot.sh env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest`, run from `src/backend`.

**Shared test file.** W-8-FC-NOTICE, REPROCESS-ATOMIC and W-8-HARDEN all add tests to `src/backend/tests/test_embedding_fail_closed_paths.py`, so no two of them run at once. Order: REPROCESS-ATOMIC → W-8-HARDEN (it reuses REPROCESS-ATOMIC's HTTP reprocess harness). W-8-FC-NOTICE goes whenever `rag.py` is free, but never beside either of the other two.

### W-8-FC-NOTICE — a hash-only vault with no embedding model abstains silently instead of returning the Q-FC notice

**Source:** PR #168 Codex adversarial review, [high] 1, and the L0 ruling on that PR: "return the Q-FC unavailable error before the hash-only early return, with a route test. Not a merge blocker."

**Fact (`a9978e8`):** `RAGModule._search_vectors_async` filters on `Embedding.model_name == self._embedder.config.model_name` (`src/backend/modules/rag.py:570-572`, Q-HASH). It returns `[]` at `:605-606` when no row is left. It reaches `embed_text` (`:611`) only when rows remain, and that call is what raises `ModelUnavailableError(EMBEDDING_UNAVAILABLE_MESSAGE)` (`:612-614`). So a pre-W-8 vault that holds only `hash-fallback` rows never asks whether the model is installed. With the model absent, document search is skipped **silently**: `rag.query` carries on with observation and KB context only, and **the LLM is still called** with that context. The patient gets a generated answer with no document context and never sees the signed Q-FC notice (`api/interpretations.py:539-543` would map the error to a 501). On `/assistant/chat`, when observation context exists, the same vault yields an LLM answer instead of the knowledge fallback that HC-EMB-005 pins for a vault with real vectors. (With no observation and `include_references: false` the chunk list is empty and `RAGModule.query` abstains before the runner, `modules/rag.py:1261-1271`, review round 2.)
**Repro:** a verified document with one chunk whose embedding is `model_name="hash-fallback"`, model path pointing at an empty directory (the `absent_model` fixture). `await rag._search_vectors_async(query="LDL", ...)` returned `[]` and raised nothing. Review round 1 on PR #189 (comment 6264375489) re-ran the HC-EMB-006c harness with only the embedding row changed to `hash-fallback`: `rag.query` ran, the sentinel runner was called once (`runner.calls == 1`), and the 006c stub then crashed in `InterpretationResponse.from_model` (`api/interpretations.py:139`, no `citations_json`), because that stub is only safe when retrieval raises first.

**Scope of the harm.** No unverified or placeholder vector reaches an answer (L0 ruling on #168). The defect is that the model-absent state is invisible: the LLM answers from observation and KB context alone, and the patient is not told that document search is unavailable.

**Design (one hunk in `_search_vectors_async`, no new layer):**
1. Keep the base statement (joins, `Document.status == "verified"`, date / analyte / category filters) in one variable. Apply the `model_name` filter to a copy of it, and run that copy as today.
2. If that returns no rows, run the base statement once more as `select(Chunk.id)` with the same joins and filters, `limit(1)`. If it finds a row, eligible chunks exist but none has a comparable vector. Call `self._embedder.embed_text(query)` inside the same `try` as `:610-614`. With the model absent, that raises the Q-FC error. With the model present, the result is discarded and the method returns `[]` (Q-HASH unchanged: hash vectors are still never compared).
3. If the base statement finds nothing, return `[]` without embedding (HC-EMB-006b unchanged: an empty profile needs no model).

**Test-first** (`src/backend/tests/test_embedding_fail_closed_paths.py`; "RED" = fails on `a9978e8`):

| Id | Assertion | RED today? |
|---|---|---|
| HC-EMB-006d | `POST /interpretations/observations/{id}/interpret-grounded` through `route_client`, as HC-EMB-006c but the only embedding row has `model_name="hash-fallback"`, model absent. The interpret stub returns a **complete** interpretation object (a `LabInterpretation` with `citations_json`, `context_json` and every field `InterpretationResponse.from_model` reads, `api/interpretations.py:135-160`), so the request finishes instead of crashing → 501, `detail == QFC_APPROVED_DETAIL`, `str(absent_model)` not in it, `runner.calls == 0`, one audit row with `entity_id == obs_id` (`master_db.add` is a `MagicMock`) | yes: today 200 and `runner.calls == 1` (the LLM answered without document context) |
| HC-EMB-005b | `POST /assistant/chat` through `route_client`, as HC-EMB-005 (`"What is my LDL?"`, `include_references: false`) but the only embedding row is `hash-fallback`, model absent, **and a verified observation for the asked analyte is seeded** (`analyte_canonical="ldl_cholesterol"`, `user_verified=True`; not 006c's `"ldl"`: on `/assistant/chat` `selected_analytes` is None, so `_get_observation_chunks` takes the analyte from the question text, `modules/rag.py:327-332`, and "What is my LDL?" resolves to `ldl_cholesterol`), so observation context exists → 200, `runner.calls == 0`, `ANSWER-SENTINEL` not in `full_response`, `verification.enabled is False`, and `"based on the knowledge base only"` in `full_response` (the note only `_build_knowledge_fallback` emits, `api/assistant.py:1592`; the route reaches it via `except ModelUnavailableError` at `:1047`), so the test cannot pass on the insufficient-context abstain shape | yes: today `runner.calls == 1` and the LLM answer is returned without the fallback note |
| HC-EMB-006e | `_search_vectors_async` on the same hash-only vault, model absent → raises `ModelUnavailableError` | yes (repro above) |
| HC-EMB-006f | hash-only vault, model present (`_FixedEmbedder` as in HC-EMB-008) → returns `[]` | no. Guard against over-correction; the mutant "raise whenever the filtered query is empty" must fail it |

**Files:** `src/backend/modules/rag.py` (`_search_vectors_async` only), `src/backend/tests/test_embedding_fail_closed_paths.py`, slots. **Re-run, not edited:** `tests/test_embedding_bundle.py`, `tests/test_rag_pipeline.py`, `tests/test_safe_interp_grounded.py`, `tests/test_assist_utc_http.py`, `tests/test_verified_only_consumers.py`.
**Expected collected delta:** +4. **Est:** 1.5 h.
**Acceptance:** `pyt tests/test_embedding_fail_closed_paths.py tests/test_embedding_bundle.py tests/test_rag_pipeline.py tests/test_safe_interp_grounded.py tests/test_verified_only_consumers.py -q -rfE`: 0 failed except the documented model-absent set when the bundle is not fetched. Full suite per RUNBOOK §6, with the embedding model present. **Rollback:** revert; no data.
**Order:** LEGACY-CITE-PROMPT (#185) merged on 2026-10-20 (`5750a97`), so `rag.py` is free; the row is in progress (#203, claimed 2026-10-20) and Task 0 re-greps every `rag.py` anchor above (#185 shifted them). Never beside LCP-HEADERLESS (`rag.py`). Never beside G-C5 or B-3 (both edit `rag.py`), REPROCESS-ATOMIC or W-8-HARDEN (shared test file). No ask-first file.

### REPROCESS-ATOMIC — reprocess commits the chunk delete when the replacement row build fails

**Source:** PR #168 Codex adversarial review, [high] 2; L0 ruling on #168 ("pre-existing, narrowed by W-8; follow-up row").

**Fact (`a9978e8`):** `_create_chunks_and_embeddings` embeds first (`src/backend/api/documents.py:869-871`, W-8). Then, with `refresh_existing`, it runs `delete(Chunk).where(Chunk.doc_id == doc_id)` (`:873-874`) and builds the replacement rows one pair at a time (`:877-897`): each `Chunk` is added before its `Embedding`, and `embedder.vector_to_blob(...)` runs inside the `Embedding(...)` constructor (`:894`). If that raises, the caller `_run_extraction_pipeline` swallows the error (`:686-687`) and commits (`:689`).
**Repro (worse than the review says):** one chunk `chunk-1` with its embedding; `EmbeddingsModule.embed_chunks` stubbed, `vector_to_blob` raising `ValueError`; call with `refresh_existing=True`, then commit as the caller does. The committed chunk ids for the document are `['<new uuid>']`: `chunk-1` is gone and **one new chunk with no embedding row** replaced it. The document's index is silently emptied.

**Design (smallest correct version):** build every replacement `Chunk` and `Embedding` object, including every `vector_to_blob` call and every `emb_data[...]` lookup, into a list **before** the delete. Then run the delete and `profile_db.add_all(rows)`, and commit as today. A failure in the build then happens before any row is touched. A flush failure at the `:899` commit already rolls back the whole transaction, delete included, so no savepoint is needed. Do not change the swallow-and-commit in the caller: it is what keeps a document's new observations when embedding is unavailable (HC-EMB-007).

**Not in scope (noted only):** the core `delete(Chunk)` relies on `Embedding.chunk_id` `ondelete="CASCADE"` (`models/embedding.py:44`), which works only with SQLite FK enforcement on. That is C-P6's FK work (recurring-failures #9 already records it).

**Test-first** (`src/backend/tests/test_embedding_fail_closed_paths.py`):

| Id | Assertion | RED today? |
|---|---|---|
| HC-EMB-007b | as HC-EMB-007 (direct `_create_chunks_and_embeddings`, `refresh_existing=True`), but `embed_chunks` returns valid dicts and `EmbeddingsModule.vector_to_blob` raises → the call raises; after `commit()` + `expunge_all()`, the committed chunk ids are `["chunk-1"]` and `chunk-1` still has its embedding row | yes (repro: one new chunk id, no embedding) |
| HC-EMB-007c | `POST /documents/{id}/reprocess` through `route_client`: a verified `lab_pdf` document with `chunk-1` and its embedding; `documents_api.get_decrypted_document`, `documents_api.ExtractModule` (one result with `observations=[]`, `extracted_text="LDL 128 mg/dL"`, `ocr_unavailable=False`, `collection_dates=[]`), `documents_api._classify_and_extract_entities` (as the `reprocess` fixture in `tests/test_audit_order.py:373-394`), `EmbeddingsModule.embed_chunks` and a raising `vector_to_blob` stubbed → 200; committed chunk ids `["chunk-1"]` | yes (same defect, through the caller's commit) |

**Files:** `src/backend/api/documents.py` (`_create_chunks_and_embeddings` only), `src/backend/tests/test_embedding_fail_closed_paths.py`, slots. **Re-run, not edited:** `tests/test_audit_order.py` (reprocess Cases), `tests/test_documents_api.py`, `tests/test_care_tasks.py`, `tests/test_audit_order_guard.py`.
**Expected collected delta:** +2. **Est:** 1.5 h.
**Acceptance:** `pyt tests/test_embedding_fail_closed_paths.py tests/test_audit_order.py tests/test_documents_api.py tests/test_audit_order_guard.py -q -rfE`: 0 failed (model-absent set aside); HC-EMB-007 still green. Full suite per RUNBOOK §6. **Rollback:** revert; no data.
**Order:** ready now. Never beside W-8-FC-NOTICE or W-8-HARDEN (shared test file), or any open PR on `api/documents.py` (none open or ready on `a9978e8`). No ask-first file.

### W-8-HARDEN — model path in logs, weights-only checksum, `.partial` left after an exception

**Source:** PR #168 Codex adversarial review, the three [medium] findings; L0 ruling on #168 ("go into one follow-up row, W-8-HARDEN").

**Facts (`a9978e8`):**
1. **Path in logs.** `EmbeddingsModule._load_local_model` puts the absolute model directory in both error messages (`src/backend/modules/embeddings.py:102-105` "not installed at {model_dir}", `:114-116` "at {model_dir} failed to load"). Two sinks log the message verbatim: `rag.py:613` (`"...failed closed: %s", exc`) and `api/documents.py:687` (`f"Chunking failed ...: {chunk_error}"`). Measured: with `settings.embedding_model_path` set to `/tmp/.../home-jane-doe/model`, the message reads `Embedding model not installed at /tmp/.../home-jane-doe/model (11 of 11 files missing). ...`. The 501 detail is already path-free (HC-EMB-006a/c).
2. **Weights-only checksum.** `_embedding_complete` checks that the 11 `EMBEDDING_FILES` exist and that only `model.safetensors` matches `EMBEDDING_WEIGHTS_SHA256` (`src/backend/scripts/download_models.py:319-324`). A changed tokenizer or config file is accepted, both on a fresh fetch and when an existing target is re-checked (`:344-347`).
3. **`.partial` left behind.** Cleanup covers an exception from `snapshot_download` (`:361-372`) and a `False` verification (`:374-378`). It does not cover an exception raised by `_embedding_complete` itself (for example `OSError` while hashing) or by `partial.rename(target)` (`:380`). The next run then stops at `:356-359` ("already exists") and needs manual cleanup.

**Design:**
1. **Messages without the path** (`embeddings.py:102-105`, `:114-116`): "Embedding model not installed ({n} of {m} files missing). Fetch it once with: cd src/backend && python scripts/download_models.py embedding" and "Embedding model failed to load: {type(exc).__name__}". No log line elsewhere changes; both sinks then log a path-free message. The fetch script prints its own target path, so a developer still sees where the model goes.
2. **Full digest manifest** (`embeddings.py`): replace `EMBEDDING_WEIGHTS_SHA256` with `EMBEDDING_FILE_SHA256: dict[str, str]`, one entry per name in `EMBEDDING_FILES`, keep `EMBEDDING_FILES = tuple(EMBEDDING_FILE_SHA256)` order-stable, and make `_embedding_complete` require every file to exist and match. The values, measured on 2026-10-19 with `sha256sum` over a bundle fetched by the W-8 script (`hc-f-5` worktree; its `model.safetensors` digest equals today's pinned `EMBEDDING_WEIGHTS_SHA256`, so it is the pinned revision `1110a243…`):

   | File | sha256 |
   |---|---|
   | `1_Pooling/config.json` | `4be450dde3b0273bb9787637cfbd28fe04a7ba6ab9d36ac48e92b11e350ffc23` |
   | `README.md` | `dcd602d2fd35c203a247304a06fec6654a12f7941b739f9221a064fe8dc3b7f0` |
   | `config.json` | `953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41` |
   | `config_sentence_transformers.json` | `061ca9d39661d6c6d6de5ba27f79a1cd5770ea247f8d46412a68a498dc5ac9f3` |
   | `model.safetensors` | `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db` |
   | `modules.json` | `84e40c8e006c9b1d6c122e02cba9b02458120b5fb0c87b746c41e0207cf642cf` |
   | `sentence_bert_config.json` | `fc1993fde0a95c24ec6c022539d41cf6e2f7c9721e5415d6fb6897472a9cd4b7` |
   | `special_tokens_map.json` | `303df45a03609e4ead04bc3dc1536d0ab19b5358db685b6f3da123d05ec200e3` |
   | `tokenizer.json` | `be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037` |
   | `tokenizer_config.json` | `acb92769e8195aabd29b7b2137a9e6d6e25c476a4f15aa4355c233426c61576b` |
   | `vocab.txt` | `07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3` |

   Task 0 re-measures these on a fresh fetch (owner host or CI fetch step) and stops if any differs. The revision pin (EMB-REV) does not change, so no owner gate is needed. The runtime load path does not hash files; only the fetch script does, as today.
3. **One ownership-aware cleanup** (`download_models.py:361-381`): `snapshot_download`, `_embedding_complete(partial)` and `partial.rename(target)` sit in one `try`. On any `BaseException`, remove `partial` (created by this run's exclusive `mkdir`, `:355`) and re-raise. On a `False` check, remove it and exit 1 as today. Never touch `target` or a `.partial` this run did not create (HC-EMB-004c/d unchanged).

**Test-first:**

| Id | File | Assertion | RED today? |
|---|---|---|---|
| HC-EMB-009a | `tests/test_embedding_fail_closed_paths.py` | with `absent_model`, and with a model directory holding all 11 files and `monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=_raiser))` (not `monkeypatch.setattr("sentence_transformers.SentenceTransformer", ...)`, which imports the package first; the function-local `from sentence_transformers import SentenceTransformer` at `modules/embeddings.py:108` picks the stub up whether or not the package is installed, so the `:114-116` branch always runs), `str(EmbeddingModelUnavailableError)` does not contain the directory path | yes (path in both messages) |
| HC-EMB-009b | same | `caplog` at WARNING: `_search_vectors_async` with one chunk and `absent_model` → `str(absent_model)` not in `caplog.text` (the `rag.py:613` sink) | yes |
| HC-EMB-009c | same | `caplog` at WARNING: the HC-EMB-007c HTTP reprocess harness with `absent_model` and the real `embed_chunks` → `str(absent_model)` not in `caplog.text` (the `api/documents.py:687` sink) | yes |
| HC-EMB-004f | `tests/test_embedding_bundle.py` | the fake snapshot succeeds, `download_models._sha256` raises `OSError` → `OSError` propagates; no `.partial`, no target | yes (`.partial` left) |
| HC-EMB-004g | same | `download_models._embedding_complete` monkeypatched to return `True` (so the test does not depend on the new manifest), `Path.rename` raises `PermissionError` for the `.partial` → error propagates; no `.partial`, no target | yes: today the rename sits outside the cleanup `try` and the `.partial` is left |
| HC-EMB-004h | same | manifest monkeypatched to the fake payload digests, then the fake snapshot writes a different `tokenizer.json` → exit 1, nothing installed, no `.partial` | yes (today only the weights are checked; before the edit the monkeypatch target does not exist either, so also prove RED with the mutant "check `model.safetensors` only" in Task 3) |
| HC-EMB-004i | same | an existing complete target whose `config.json` differs from the manifest → exit 1, target not deleted, `snapshot_download` not called | today the monkeypatch of `emb.EMBEDDING_FILE_SHA256` fails at setup (`AttributeError`), which proves nothing (recurring-failures #1). The behavioural RED is the Task 3 mutant "check `model.safetensors` only": it accepts the altered target and fails this test; paste its output, as for 004h |

**Tests that pin changed behaviour (edited):** HC-EMB-004b (`tests/test_embedding_bundle.py:157-170`) monkeypatches `emb.EMBEDDING_WEIGHTS_SHA256`; it now monkeypatches `emb.EMBEDDING_FILE_SHA256` to the digests of the fake payloads (`b"pinned-weights-stand-in"` for the weights, `b"{}"` for the rest). HC-EMB-004a stays as is (wrong weights still fail).

**Files:** `src/backend/modules/embeddings.py`, `src/backend/scripts/download_models.py`, `src/backend/tests/test_embedding_bundle.py`, `src/backend/tests/test_embedding_fail_closed_paths.py`, slots. **Re-run, not edited:** `tests/test_embedding_no_network.py`, `tests/test_model_integrity.py`, `tests/test_verify_model_repos.py`, `tests/test_rag_pipeline.py`.
**Expected collected delta:** +7. **Est:** 2.5 h.
**Acceptance:** `pyt tests/test_embedding_bundle.py tests/test_embedding_fail_closed_paths.py tests/test_embedding_no_network.py tests/test_model_integrity.py tests/test_verify_model_repos.py -q -rfE`: 0 failed with the model present. `cd src/backend && python scripts/download_models.py embedding` against the installed bundle prints "already installed" (the real bundle passes the full manifest). Full suite per RUNBOOK §6. **Recurring-failures #12 recheck:** after this merges, L0 runs the new gate (the stricter `_embedding_complete`: CI's fetch step and any open PR that installs or fakes a bundle) on `origin/main` and on every open PR built before it, and rebases or fixes those PRs before merging the rest of the group. **Rollback:** revert; an install that the stricter check now rejects is re-fetched by deleting it by hand (the script never deletes it).
**Order:** blocked until REPROCESS-ATOMIC merges (shared test file; HC-EMB-009c reuses its harness). Never beside W-8-FC-NOTICE (shared test file) or G-C5 (edits `embeddings.py` and `download_models.py`). No ask-first file.

### CFR-CACHE-TZ — the agent cache key ignores the profile time zone; abbreviation analytes get title-case names

**Source:** PR #162 (CHAT-FACT-ROUTING) "Follow-ups (MINOR, outside this row's files)" items 1 and 2.

**Facts (`a9978e8`):**
1. **Cache key.** `CacheKey` holds `normalized_question`, `profile_version`, `profile_id`, `filters` (`src/backend/modules/agent/cache.py:37-43`). `_serve_via_agent` builds it at `src/backend/api/assistant.py:803-808`, and `_profile_version` (`:638`) fingerprints only verified observations and documents. Since CFR-FORMAT (a), the agent's fact sentences print profile-local dates: `draft.py` reads the zone at answer time (`modules/agent/nodes/draft.py:102-110`, `:334`). A cache hit skips `draft`, so after the patient changes their time zone a cached answer keeps the old zone's dates until the evidence changes.
2. **Display names.** `_display_name` (`draft.py:83-90`) falls back to `key.replace("_", " ").title()`. 17 of the 39 `ANALYTE_SYNONYMS` keys have no `DISPLAY_NAMES` entry (`modules/normalize.py:221-244`). For most the fallback reads fine (`Calcium`, `Total Protein`). It is wrong for the 8 abbreviation keys `mcv`, `mch`, `mchc`, `rdw`, `ast`, `alt`, `tibc`, `esr` (`Mcv`, `Alt`, ...), and for `egfr` (`Egfr`), which is not a synonyms key but is stored as-is when a report prints it.

**Design:**
1. **Cache key.** Add a **required** field `tz_name: str` to `CacheKey`. At `api/assistant.py:803-808`, pass `tz_name=await profile_timezone_name(profile_db, profile_id)` (`core.time`, already the zone source for `draft`). Required, not defaulted to `"UTC"`: a default would let a future construction site recreate this bug without failing. Update the module docstring (`cache.py:1-23`) with one sentence: the zone is in the key because answers print local dates.
2. **Display names.** Add 9 entries to `NormalizeModule.DISPLAY_NAMES`, in the existing "ABBR (Expansion)" style of `BUN (Blood Urea Nitrogen)`: `mcv` "MCV (Mean Corpuscular Volume)", `mch` "MCH (Mean Corpuscular Hemoglobin)", `mchc` "MCHC (Mean Corpuscular Hemoglobin Concentration)", `rdw` "RDW (Red Cell Distribution Width)", `ast` "AST (Aspartate Aminotransferase)", `alt` "ALT (Alanine Aminotransferase)", `tibc` "TIBC (Total Iron-Binding Capacity)", `esr` "ESR (Erythrocyte Sedimentation Rate)", `egfr` "eGFR (Estimated Glomerular Filtration Rate)". These are names, not advice; CFR-FORMAT (a) already approved display names. `DISPLAY_NAMES` is also read by `modules/rag.py:372` and `modules/normalize.py:286`; neither file's code changes, and no test pins the old title-case strings (grep on `a9978e8`). The `rag.py:372` reader means the legacy RAG "YOUR RESULTS" context text changes too (for example `Alt` becomes `ALT (Alanine Aminotransferase)`). CFR-FORMAT (a) was answered for the agent's fact answers; applying it to the legacy context is **L0's reading, not an owner answer**. L0 ruling (2026-10-19, PR #189 review round 1): allowed, because display names are presentation only.

**Test-first:**

| Id | File | Assertion | RED today? |
|---|---|---|---|
| HC-CFR-009 | `tests/test_assist_agent_dates_http.py` (its `_post` harness, real `run_agent`, `route_client`) | profile zone `America/Los_Angeles` (a `UserModelSettings` row), one verified LDL row collected `2026-01-16 03:00` (naive UTC). Ask "Is my LDL cholesterol high?" → the answer contains `Jan 15, 2026`. Set the row's zone to `Asia/Tokyo`, commit, ask the same question → the answer contains `Jan 16, 2026` and not `Jan 15, 2026` | yes (cache hit replays `Jan 15`) |
| HC-CFR-010 | `tests/agent/test_agentic_queries.py` | parametrised over the 9 keys: `draft._display_name(key)` equals the name above | yes ×9 |

**Tests that pin changed behaviour (edited, one kwarg each):** every direct `CacheKey(...)` with all three old fields gains `tz_name="UTC"`: `tests/test_agent_cache_isolation.py:127-128`, `tests/test_hc_a1_agent_verification.py:75` (`_seed_cache`; the route computes `"UTC"` for a profile with no settings row, so the seeded key still matches), `tests/agent/test_s5_cutover_cache.py:24-25`, `:132`, `:147`. `test_s5_cutover_cache.py:15` and `:20` assert that a missing field raises; they stay as they are and still pass.

**Files:** `src/backend/modules/agent/cache.py`, `src/backend/api/assistant.py` (the `CacheKey(...)` call and the `core.time` import only), `src/backend/modules/normalize.py` (`DISPLAY_NAMES` only), `src/backend/tests/test_assist_agent_dates_http.py`, `src/backend/tests/agent/test_agentic_queries.py`, `src/backend/tests/test_agent_cache_isolation.py`, `src/backend/tests/test_hc_a1_agent_verification.py`, `src/backend/tests/agent/test_s5_cutover_cache.py`, slots. **Re-run, not edited:** `tests/test_assist_utc_http.py`, `tests/test_chat_sessions.py`, `tests/test_rag_trend_units.py`, `tests/test_export_trend_units.py`, `tests/test_audit_order.py`.
**Expected collected delta:** +10. **Est:** 2 h.
**Acceptance:** `pyt tests/agent/ tests/test_assist_agent_dates_http.py tests/test_agent_cache_isolation.py tests/test_hc_a1_agent_verification.py tests/test_assist_utc_http.py tests/test_chat_sessions.py tests/test_rag_trend_units.py -q -rfE`: 0 failed. `cd src/backend && python -c "from main import app"`. Full suite per RUNBOOK §6. **Rollback:** revert; the cache is in-process only.
**Order:** in progress (#204, claimed 2026-10-20). Never beside B-3 or G-C5 (both edit `api/assistant.py`). The earlier wait on LEGACY-CITE-PROMPT (#185; `DISPLAY_NAMES` feeds the legacy context at `rag.py:372`) is over: #185 merged on 2026-10-20 (`5750a97`). No ask-first file. **Recurring-failures #12 recheck:** after this merges, L0 runs the new gate (the required `CacheKey.tz_name`: `tests/agent/`, `tests/test_agent_cache_isolation.py`, `tests/test_hc_a1_agent_verification.py`) on `origin/main` and on every open PR built before it, and rebases or fixes those PRs before merging the rest of the group. An open PR that builds a `CacheKey` without `tz_name` fails it.

## Follow-ups found 2026-10-19 (planned 2026-10-19 on `origin/main` @ `d42dba9`)

Three rows: LCP-HEADERLESS (owner LCP-HEADERLESS (a), `docs/capstone-report/owner-decisions-2026-09-27.md:275`), EMB-LOAD-LOG-PATH (L0 ruling on #196, comment 6267273354; it also takes EMB-HARDEN-MINORS and REPROCESS-007C-REACH, because all three edit `tests/test_embedding_fail_closed_paths.py`) and LLM-PATH-LOG (the LLM half of EMB-LOAD-LOG-PATH, split off because `model_selector.py` is held by B-5). Every "measured" fact below ran in a scratch copy of `d42dba9` under `/tmp/claude-1000/` through `scripts/pyslot.sh`; nothing was committed. `pyt` = `scripts/pyslot.sh env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest`, run from `src/backend`.

### LCP-HEADERLESS — the legacy parser finds headers anywhere, drops text before them, and never checks headerless text for citations

**Source:** owner LCP-HEADERLESS (a) "Own row", `owner-decisions-2026-09-27.md:275`: "Plan it as its own item; it takes #185's open headerless-malformed MINOR." The [LEGACY-CITE-PROMPT plan](../2026-10-17-legacy-cite-prompt-constrained-decoding-plan.md) `:164` raised it. #185's open MINOR 1 (PR body, "Open MINORs"; review comment 6263486895): Python-repr dicts, curly-quoted keys, multi-item arrays and JSON strings "can be served as a JSON fragment with `is_valid: true`", root cause `_parse_response_segments`. #185 comment 6270643786 (LCP Task 5 quiet re-run): "the served text shows `[USER_OBSERVATION:N]` labels to the patient (cosmetic, D11 context label leaked into output)". #185 merged on 2026-10-20 (`5750a97`), so its renderer (`_render_structured_answer`, `rag.py:1346`) and its withhold of JSON-shaped text (`_STRUCTURED_WITHHELD`, `:1401`; `_contains_json_object`, `:1407`) are on `main`.

**Facts (`5750a97`):**
1. `_parse_response_segments` (`src/backend/modules/rag.py:1101-1127`) runs `re.search` for `REPORT FACTS:?`, `GENERAL INFO:?` and `UNCERTAINTIES:?` anywhere in the text, case-insensitively (`:1107-1109`, `:1113`). Text before the first match is in no segment. If nothing matches, the whole text becomes one `general_info` segment (`:1120-1125`).
2. `validate_response` checks for citations only in `report_facts` segments (`:891-896`). The served text is the segments joined (`api/assistant.py:952`).
3. Context labels come from `_compose_prompt`: `[YOUR_RESULTS:N]` for observation summaries and `[{source_type.upper()}:N]` for other chunks (`rag.py:696-703`), so the model can echo `[USER_DOCUMENT:N]`, `[REFERENCE:N]` and `[USER_OBSERVATION:N]`. Nothing removes them from the served text.

**Measured on `5750a97`** (`RAGModule(enable_verification=…).validate_response(text, build_chunks("glucose"))`; scratch tests, not committed). "Verifier off" isolates the parser's own check. "Verifier on" is the default that `/assistant/chat` uses, and on the legacy path a response with `is_valid` True is served.

| Input | Segments today (identical with the verifier off and on) | Verifier off: `is_valid` | Verifier on (default): `is_valid`, errors |
|---|---|---|---|
| `Your LDL is 128 mg/dL, above the range.` (headerless, uncited) | one `general_info`, no "missing citations" error | True | False: "1 claim(s) could not be verified", "Low faithfulness score: 0.06" |
| `REPORT FACTS:\nYour LDL is 128 mg/dL, above the range.` (same text with a header) | `report_facts`, error "Report facts section missing citations" | False | False (also the two verifier errors) |
| `LDL Cholesterol is 128 mg/dL [cite:1]. There are uncertainties about lab ranges.` | one `uncertainty` segment, `about lab ranges.`; the cited fact is dropped | True | False: "2 claim(s) could not be verified", faithfulness 0.02 |
| Python-repr dict `{'report_facts': [{'text': 'Glucose: 95 mg/dL [cite:1]', 'cites': [1]}], 'uncertainties': ['Reference ranges can vary between laboratories.']}` | **fragment**: `uncertainty`, `': ['Reference ranges can vary between laboratories.']}` | True | False: "Low faithfulness score: 0.58" |
| curly-quoted keys `{“report_facts”: [{“text”: “Glucose: 95 mg/dL [cite:1]”}], “uncertainties”: ["Reference ranges can vary between laboratories."]}` | **fragment**: `uncertainty`, `”: ["Reference ranges can vary between laboratories."]}` | True | False: "Low faithfulness score: 0.59" (just under the 0.6 cut) |
| JSON string `"REPORT FACTS:\n- Glucose: 95 mg/dL [cite:1]"` (with the literal backslash-n) | **fragment**: `report_facts`, `\n- Glucose: 95 mg/dL [cite:1]"` | True | **True, no errors: the fragment is served today** |
| 2-item array `[{"text": "Glucose: 95 mg/dL [cite:1]", "cites": [1]}, {"text": "Reference ranges can vary.", "cites": []}]` | the **whole input**, one `general_info` segment (not a fragment) | True | **True, no errors: raw JSON is served today** |
| `**UNCERTAINTY**\n- Reference ranges can vary.` (the singular form #185's renderer emits) | one `general_info` segment (the pattern needs `UNCERTAINTIES`) | True | False: "1 claim(s) could not be verified", faithfulness 0.03 |

So with the default verifier on, the parser's defects already reach a patient for two shapes: the JSON string is served as a fragment, and the 2-item array is served as raw JSON. #185's `_contains_json_object` does not withhold either shape (PR #202 review round 2, re-checked on `5750a97`). The repr dict and curly-quoted keys are withheld only by the faithfulness score, at 0.58 and 0.59 against a 0.6 cut. **Label leak over HTTP** (`legacy_chat_client`, glucose chunks, verifier on): the model output `REPORT FACTS:\n- Glucose: 95 mg/dL (reference range 70-100 mg/dL) [USER_OBSERVATION:1] [cite:1]` returns 200 with `is_valid: true`, and `full_response` keeps `[USER_OBSERVATION:1]`.

**Owner gate LCP-HL-SCOPE** (execution; open). Exact wording to ask:

> "LCP-HL-SCOPE (LCP-HEADERLESS edits the legacy citation check in `modules/rag.py`, `_parse_response_segments`. No threshold changes, and `faithfulness.py`, `verifier_agent.py` and `interpret_safety.py` are untouched.) Today the parser finds section headers anywhere in the text and drops everything before the first one. Measured on `main`:
> - **Served today with the verifier on (the default):** a JSON string `"REPORT FACTS:\n- Glucose: 95 mg/dL [cite:1]"` is served as the fragment `\n- Glucose: 95 mg/dL [cite:1]"`, and a cited JSON array is served whole as raw JSON.
> - **Withheld today only by the verifier:** a Python-repr dict and curly-quoted JSON are cut into fragments such as `': [...]}` and fail only on faithfulness (0.58 and 0.59, against a 0.6 cut). `LDL Cholesterol is 128 mg/dL [cite:1]. There are uncertainties about lab ranges.` keeps only `about lab ranges.` A headerless answer is one GENERAL INFO segment, so the 'Report facts section missing citations' check never runs on it.
> Which fix?
> **(a)** A header counts only at the start of a line (optionally inside `**…**` or after `#`), and `UNCERTAINTY` counts like `UNCERTAINTIES`. Any text outside a recognised section is treated as REPORT FACTS, so it must carry a `[cite:N]`. A headerless or prefixed uncited answer then abstains, and no input is cut into a fragment. **But any of the four structured shapes above (repr dict, curly-quoted JSON, JSON string, JSON array) becomes one whole REPORT FACTS segment that carries `[cite:1]`, so it is served as raw text whenever the verifier passes.** The JSON string and the cited JSON array are served today (as a fragment and as raw JSON), and both stay served, now as whole raw text. Recommended: stricter than today, no threshold changes.
> **(b)** (a), plus withhold structured output the renderer did not turn into sections: text that starts with `{`; text that starts with `[` followed by `{`, `[` or a quote; or text wrapped whole in one pair of quotes. This withholds all four shapes, including the JSON string and the JSON array that are served today. Prose that only opens with `[cite:1]`, an echoed `[YOUR_RESULTS:1]` or a quoted word is not withheld. The cost: a prose answer wrapped entirely in quotes is withheld. It flips #185's pinned `{oops` pass-through (HC-LCP-007, now on `main`) to withheld.
> **(c)** Line-start headers only. Headerless text stays GENERAL INFO, so the citation check still does not run on it, and the JSON string and the cited JSON array stay served as whole raw text."

**Owner gate LCP-HL-LABELS** (execution; open; asked as its own yes/no). Removing labels changes served output, and the owner's LCP-HEADERLESS answer (`:275`) does not cover it. D11 makes labels "not citations" but does not require removing them. Exact wording to ask: "LCP-HL-LABELS: the model sometimes copies context labels such as `[USER_OBSERVATION:1]` or `[YOUR_RESULTS:2]` into its answer, and the patient sees them (measured over HTTP on `main`). Should LCP-HEADERLESS also remove `[YOUR_RESULTS:N]`, `[REFERENCE:N]`, `[USER_DOCUMENT:N]` and `[USER_OBSERVATION:N]` from the served text? Validation would still read the raw text, and `[cite:N]` stays. (a) Yes, remove them from served text (Recommended: they mean nothing to a patient). (b) No, leave served text as it is (parser fix only)."

**Owner gate LCP-HL-DIFF** (merge only; open; asked after the draft PR exists): "LCP-HL-DIFF: here is the exact `modules/rag.py` diff for LCP-HEADERLESS under option (x) [and LCP-HL-LABELS (y)], with RED/GREEN output, the mutant table and `scripts/legacy_eval_gate.py` on the branch. Validation still runs on the raw model text; thresholds, `faithfulness.py`, `verifier_agent.py` and `interpret_safety.py` are unchanged. Merge?" `modules/rag.py` is not a CLAUDE.md §1 file, but this edits the citation check that the LEGACY-CITE-PROMPT plan says to stop and ask about ("If any task seems to need an edit to `validate_response` … STOP and ask"), so the diff gets its own owner yes.

**Design (LCP-HL-SCOPE (a); the implementer drafts the exact pattern for LCP-HL-DIFF):**
1. `_parse_response_segments`: match headers with `re.MULTILINE` at the start of a line: optional spaces, optional `**` or `#`s, then `REPORT FACTS`, `GENERAL INFO`, `UNCERTAINTIES` or `UNCERTAINTY`, an optional closing `**`, an optional `:`. The rest of that line belongs to the section, as today. Split the text at those header lines, in order. A header type may appear more than once; keep each occurrence as its own segment.
2. Text before the first header, and headerless text, becomes a `report_facts` segment, so the existing check at `:891-896` applies. Empty text gives no segment.
3. Only if LCP-HL-LABELS = (a): after verification and before `ValidatedResponse` is built, remove `\[(?:YOUR_RESULTS|REFERENCE|USER_DOCUMENT|USER_OBSERVATION):\d+\]` (and the space before it) from each returned segment's `content`. The citation regex, the verifier and faithfulness keep reading the raw `response`, so validation is unchanged.
4. Only under (b): in `validate_response`, append the error `"Unrendered structured answer"` when the stripped response starts with `{`, or starts with `[` and its next non-space character is `{`, `[`, `"`, `'`, `“` or `‘`, or is wrapped whole in one pair of `"…"`, `“…”`, `'…'` or `‘…’`. A response that only opens with `[cite:N]`, a context label or a quoted word does not match.

**Test-first** (new file `src/backend/tests/test_rag_headerless.py`; "RED" means it fails on `main`, measured above):

| Id | Assertion | RED today? |
|---|---|---|
| HC-LCPH-001 | (a)/(b) only: `RAGModule(enable_verification=False).validate_response("Your LDL is 128 mg/dL, above the range.", chunks)` → `"Report facts section missing citations"` in `validation_errors`, `is_valid is False` | yes (no error, `is_valid` True) |
| HC-LCPH-002 | `"LDL Cholesterol is 128 mg/dL [cite:1]. There are uncertainties about lab ranges."` → the joined segment content equals the whole input (nothing dropped, no `uncertainty` segment) | yes (only `about lab ranges.` survives) |
| HC-LCPH-003 ×4 | the four shapes in the table above → no returned segment's content is a fragment that starts inside the input. Under (a) each is the whole input in one `report_facts` segment; under (b) each gives `is_valid` False with `"Unrendered structured answer"` | yes ×3 (repr dict, curly-quoted keys, JSON string: fragments, measured on `5750a97`). The 2-item array is a **pin** under (a) (whole input today; it moves from `general_info` to `report_facts`) and RED only under (b) |
| HC-LCPH-004 | line-start headers still split: `REPORT FACTS:\n- X [cite:1]\n\nGENERAL INFO:\n- Y\n\nUNCERTAINTIES:\n- Z` → three segments with today's types and contents; `**UNCERTAINTY**\n- Z` → one `uncertainty` segment | the first half no (pin); the `**UNCERTAINTY**` half yes (`general_info` today) |
| HC-LCPH-005 | LCP-HL-LABELS (a) only, over HTTP: `legacy_chat_client(build_chunks("glucose"), "REPORT FACTS:\n- Glucose: 95 mg/dL (reference range 70-100 mg/dL) [USER_OBSERVATION:1] [cite:1]")` → 200, `is_valid` True, `full_response` contains `[cite:1]` and no `[USER_OBSERVATION:` | yes (measured: the label is served) |
| HC-LCPH-006 | (b) only: `{oops`, `[{"text": "x"}]` and `"REPORT FACTS: x"` (wrapped in quotes) → `"Unrendered structured answer"`; `[cite:1] Glucose is 95 mg/dL.`, `[YOUR_RESULTS:1] Glucose is 95 mg/dL [cite:1]` and `"Normal" means within the range [cite:1].` → no such error | the first three yes; the last three no (pins against over-withholding) |

**Mutants (Task 3, output in the PR body):**
- Drop the line-start anchor → HC-LCPH-002 fails.
- Map prefix text to `general_info` → HC-LCPH-001 fails.
- Drop `UNCERTAINTY` → HC-LCPH-004 fails.
- Under LCP-HL-LABELS (a), strip labels before validation instead of after → a scratch check shows the verifier mock receives changed text.

**Files:** `src/backend/modules/rag.py` (`_parse_response_segments`; the end of `validate_response`), `src/backend/tests/test_rag_headerless.py` (new), slots. **Re-run, not edited:** `tests/test_rag_pipeline.py`, `tests/test_legacy_abstain.py`, `tests/test_safe_chat_prohibited.py`, `tests/test_rag_citation_prompt.py` (calls `validate_response` on text with headers, `:143`, `:157`, the D11 label-only pin), `tests/test_biomarker_assistant.py` (`:699-743`), `tests/test_rag_structured_cite.py`, `tests/legacy_eval/`, and `python3 scripts/legacy_eval_gate.py`. The only headerless golden case, `abstain-generation-timeout`, has empty output and expects abstain (measured).
**Expected collected delta:** under (a): +7, plus 1 if LCP-HL-LABELS (a); under (b): +8, plus 1; under (c): +6, plus 1 (no HC-LCPH-001).
**Est:** 3 h after LCP-HL-SCOPE and LCP-HL-LABELS.
**Acceptance:**
- `pyt tests/test_rag_headerless.py tests/test_rag_pipeline.py tests/test_legacy_abstain.py tests/test_rag_citation_prompt.py tests/test_biomarker_assistant.py tests/test_rag_structured_cite.py tests/legacy_eval -q -rfE`: 0 failed.
- `python3 scripts/legacy_eval_gate.py` passes (run from the repo root, as the `legacy-evals` CI job runs it).
- `git diff origin/main -- src/backend/modules/faithfulness.py src/backend/modules/verifier_agent.py src/backend/modules/interpret_safety.py src/backend/modules/redaction.py` is empty.
- Full suite per RUNBOOK §6.
**Rollback:** revert.
**Order:**
- #185 is merged (`5750a97`), so `rag.py` is free. Task 0 re-measures the table above on the current `main`.
- Blocked on owner LCP-HL-SCOPE and LCP-HL-LABELS.
- Never beside W-8-FC-NOTICE, G-C5 or B-3 (all edit `rag.py`).
- The PR stays draft until LCP-HL-DIFF.
- **Recurring-failures #12 recheck:** after this merges, L0 runs `tests/test_legacy_abstain.py`, `tests/test_rag_headerless.py` and `scripts/legacy_eval_gate.py` on `origin/main` and on every open PR built before it. An open PR whose fake model output has no line-start header now abstains.

### EMB-LOAD-LOG-PATH — sentence-transformers logs the model path at INFO; the path-leak tests look only at WARNING (takes EMB-HARDEN-MINORS and REPROCESS-007C-REACH)

**Source:** L0 ruling on #196 (comment 6267273354): "EMB-LOAD-LOG-PATH (silence or redact the sentence_transformers logger during load, a real-package INFO test, `from None`; …)". #196 review MINORs (EMB-HARDEN-MINORS): HC-EMB-009a/b/c "miss a leak through `exc_info`, stdout, or a log level below WARNING". #192 review MINOR (REPROCESS-007C-REACH): HC-EMB-007c "does not assert the blob failure was reached".

**Facts (`d42dba9`):**
1. `_load_local_model` passes the absolute directory to `SentenceTransformer(str(model_dir), local_files_only=True)` (`src/backend/modules/embeddings.py:114`) and re-raises with `from exc` (`:112`, `:118`).
2. Nothing in the backend sets the root logger level: `alembic.ini`'s `[logger_root]` is `WARN`, and `core/config.py:134` `log_level` is never applied (L1 triage on #196). So INFO lines are dropped by default; this is a latent leak, reachable once anyone enables INFO.
3. HC-EMB-009b and 009c capture at `logging.WARNING` only (`tests/test_embedding_fail_closed_paths.py:373`, `:386`); 009a uses a stub `SentenceTransformer` (`:352-356`), so it cannot see the real package log.
4. HC-EMB-007c (`:299-307`) asserts status 200 and that `chunk-1` and its embedding survive. It never checks that the stubbed `vector_to_blob` raised.

**Measured** (scratch tests):
- Real package, stub bundle (the 11 files of `EMBEDDING_FILES` written as `b"{}"` under `<tmp>/jane-doe-home/model`): with `caplog` at DEBUG, `EmbeddingsModule()._load_local_model()` raises `EmbeddingModelUnavailableError`, and logger `sentence_transformers.base.model` has already logged the full path at INFO. Stdout and stderr hold no path. `__cause__` is a `ValueError` whose text holds no path here (it depends on the dependency's message).
- Real bundle (`/home/danny/asclexis-models/embeddings/all-MiniLM-L6-v2`): the INFO record reads `Loading SentenceTransformer model from /home/danny/asclexis-models/embeddings/all-MiniLM-L…`.
- HC-EMB-007c mutant: `api.documents._create_chunks_and_embeddings` replaced by a function that raises before building any row → the route still returns 200 and `chunk-1` and its embedding survive, so all three 007c assertions pass. The test passes without reaching the blob failure.

**Design:**
1. `embeddings.py`: around the `SentenceTransformer(...)` call only, raise the `sentence_transformers` logger to `WARNING` and restore its previous level in a `finally`. Child loggers such as `sentence_transformers.base.model` inherit it while their own level is unset; Task 0 checks that, and HC-EMB-010a fails if it stops being true. Raise both `EmbeddingModelUnavailableError`s `from None`. The messages stay as W-8-HARDEN left them.
2. Tests only: 009b and 009c capture at `logging.DEBUG`, also check `capsys` output, and check each record's `exc_text` / formatted traceback, not only `caplog.text`. 007c counts calls in the raising `vector_to_blob` stub (`_stub_embedding_blob_failure` returns the counter) and asserts at least one call.

**Test-first** (`src/backend/tests/test_embedding_fail_closed_paths.py`):

| Id | Assertion | RED today? |
|---|---|---|
| HC-EMB-010a | stub bundle under a directory named `jane-doe-home`, real `sentence_transformers`, `caplog` at DEBUG → no record from any logger contains the directory path; `EmbeddingModelUnavailableError.__cause__ is None` | yes (measured INFO record; `__cause__` set). Needs `sentence-transformers` installed, not the model bundle, so it adds no environment failure |
| HC-EMB-010b | after HC-EMB-010a's call, `logging.getLogger("sentence_transformers").level` equals its level before the call | no (pin; mutant "no `finally`" fails it) |
| HC-EMB-009b, 009c (edited) | capture at DEBUG + `capsys` + formatted tracebacks | no (pins; mutant: add `logger.debug("model at %s", model_dir)` to `_load_local_model` → both now fail, the WARNING-only versions stay green; paste both) |
| HC-EMB-007c (edited) | as today, plus the blob stub was called at least once | no (pin; the mutant above now fails it) |

**Files:** `src/backend/modules/embeddings.py`, `src/backend/tests/test_embedding_fail_closed_paths.py`, slots. **Re-run, not edited:** `tests/test_embedding_bundle.py`, `tests/test_embedding_no_network.py`, `tests/test_rag_pipeline.py`.
**Expected collected delta:** +2. **Est:** 1.5 h.
**Acceptance:** `pyt tests/test_embedding_fail_closed_paths.py tests/test_embedding_bundle.py tests/test_embedding_no_network.py -q -rfE`: 0 failed (the bundle tests that need the fetched model are the known environment failures if it is absent); the two mutant outputs in the PR body; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** ready now. Never beside W-8-FC-NOTICE (shared test file) or G-C5 (`embeddings.py`). No ask-first file.

### LLM-PATH-LOG — the two LLM loaders log the model path at INFO

**Source:** the "LLM model paths at INFO" follow-up that #196's reviews raised and the L0 ruling (comment 6267273354) folded into EMB-LOAD-LOG-PATH. Split into its own row here: `modules/model_selector.py` is in B-5's file list (and `core/llm/llama_cpp_provider.py` was in #185's until it merged), so keeping them in EMB-LOAD-LOG-PATH would tie that row to B-5.

**Facts (`d42dba9`):** `logger.info("LlamaCppProvider: loading model from %s", model_path)` (`src/backend/core/llm/llama_cpp_provider.py:130`) and `logger.info(f"Loading model from {model_path}")` (`src/backend/modules/model_selector.py:462`) log the absolute GGUF path. Like fact 2 above, INFO is dropped by default.

**Design:** log `model_path.name` (the GGUF file name) instead of the path at both sites. No other change.

| Id | File | Assertion | RED today? |
|---|---|---|---|
| HC-MPATH-001 | `src/backend/tests/test_model_path_logs.py` (new) | `LlamaCppProvider._ensure_initialized()` with `_find_model_path` returning `<tmp>/jane-doe-home/x.gguf`, and `_load_llama_class` and `modules.model_integrity.verify_and_log` stubbed, `caplog` at DEBUG → the GGUF file name appears, the directory does not | yes (path logged at `:130`) |
| HC-MPATH-002 | same | `ModelSelector.load_model(tier)` with `get_model_path` returning the same path and `llama_cpp` stubbed in `sys.modules`, same assertion | yes (`:462`) |

**Files:** `src/backend/core/llm/llama_cpp_provider.py`, `src/backend/modules/model_selector.py`, `src/backend/tests/test_model_path_logs.py` (new), slots. **Re-run, not edited:** `tests/test_llm_provider_layer.py`, `tests/test_model_integrity.py` (corrected 2026-10-20, PLANNER bullet: this line first named `tests/test_llm_import_boundary.py`, which does not exist on `main`; only the W07 plan lists it, as a file B-5 will create). The new test stubs `llama_cpp`; it never imports it for real (CLAUDE.md §3 import boundary).
**Expected collected delta:** +2. **Est:** 1 h.
**Acceptance:** `pyt tests/test_model_path_logs.py tests/test_llm_provider_layer.py tests/test_model_integrity.py -q -rfE`: 0 failed; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** ready now: LEGACY-CITE-PROMPT (#185), which also edited `llama_cpp_provider.py`, merged on 2026-10-20 (`5750a97`); `:130` is unchanged. Never beside B-5 (`model_selector.py`). No ask-first file.

## Follow-ups found 2026-10-20 (planned 2026-10-20 on `origin/main` @ `b2b3f4e`)

Two rows from the reviews of #208 (LLM-PATH-LOG) and #214 (EMB-LOAD-LOG-PATH), plus one correction: the LLM-PATH-LOG section above cited `tests/test_llm_import_boundary.py`, which does not exist on `main` (PLANNER bullet; recurring-failures #6), and now cites `tests/test_llm_provider_layer.py`, as the L0 correction on #208 did. CFR-009-AGENT-PATH (#204 review MINOR) is **not** a row: measured on `b2b3f4e`, with `api.assistant._serve_via_agent` monkeypatched to raise, HC-CFR-009 already fails (the legacy path answers "I don't have enough information to answer this question…", so `"Jan 15, 2026" in first` is false), and so does HC-AAD-014 (`'Knowledge base response (no LLM)'.startswith("agent:")` is false). The extra `startswith("agent:")` line only guards a future legacy path that prints local dates; the next row that edits `tests/test_assist_agent_dates_http.py` adds it (queue bullet). Measured facts below ran as scratch tests in the planning worktree through `bash scripts/pyslot.sh` (removed afterwards; `git status --short` empty). `pyt` = `bash "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest`, run from `src/backend` (absolute path: there is no `scripts/` under `src/backend`; see lane E §2.18).

### EMB-LOG-M7 — the logger-restore tests never start at NOTSET, so mutant M7 survives

**Source:** PR #214 review MINOR: mutant M7 ("save the effective level instead of `.level`") survives; no test starts the logger at NOTSET.

**Facts (`b2b3f4e`):** `_load_local_model` saves `prev_levels = [lg.level for lg in quiet]` (`src/backend/modules/embeddings.py:117`), raises each logger to `max(getEffectiveLevel(), WARNING)` (`:119`) and restores the saved levels in `finally` (`:127-128`). HC-EMB-010b (`tests/test_embedding_fail_closed_paths.py:583-595`) and HC-EMB-010c (`:598-623`) set the loggers to INFO first. At INFO, `.level` and `getEffectiveLevel()` are both 20, so M7 restores the same value. A logger nobody configured has `.level == NOTSET` (0) and inherits root's WARNING (30); under M7 it would come back pinned at 30, and later `setLevel` calls on the parent would stop reaching it.

**Measured (scratch test, then M7 applied to a working copy of `embeddings.py`, reverted with `git checkout`):** the proposed HC-EMB-010d passes on `b2b3f4e` (`1 passed`) and fails under M7 (`assert 30 == 0`, `<Logger sentence_transformers (WARNING)>.level`).

**Design:** test only. No product change.

| Id | Assertion | RED today? |
|---|---|---|
| HC-EMB-010d | `sys.modules["sentence_transformers"]` monkeypatched to a module whose `SentenceTransformer` returns `"model"` (so the real package is not needed), `_install_stub_bundle`, `logging.getLogger("sentence_transformers").setLevel(logging.NOTSET)`; assert `getEffectiveLevel() != NOTSET` first (otherwise M7 restores the same value and the test is vacuous); `EmbeddingsModule()._load_local_model() == "model"`; then `.level == logging.NOTSET`; restore the old level in `finally` | no (pin). Mutant M7 (`:117` saves `lg.getEffectiveLevel()`) fails it: measured above |

**Files:** `src/backend/tests/test_embedding_fail_closed_paths.py`, slots. **Re-run, not edited:** `tests/test_embedding_bundle.py`, `tests/test_embedding_no_network.py`. `src/backend/modules/embeddings.py` shows an empty diff (the mutant is applied only in the RED step and reverted).
**Expected collected delta:** +1. **Est:** 0.5 h.
**Acceptance:** `pyt tests/test_embedding_fail_closed_paths.py tests/test_embedding_no_network.py -q -rfE`: 0 failed apart from the known environment failures named in CLAUDE.md §4 when the model bundle is absent; the M7 RED output pasted; `git diff origin/main -- src/backend/modules` empty; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** ready now. Never beside another PR on `tests/test_embedding_fail_closed_paths.py` (none open on `b2b3f4e`). G-C5 edits `embeddings.py`, not this test file, so the two may run together. No ask-first file.

### LLM-PATH-LOG-M2M3 — six more loader log lines can carry the model path

**Source:** PR #208 (LLM-PATH-LOG) review M2/M3, L0 handoff 2026-10-20 §3 item 4: model paths are still logged at ERROR and at INFO/WARNING. Never beside B-5.

**Facts (`b2b3f4e`; #208 already fixed `llama_cpp_provider.py:130` and `model_selector.py:462`, pinned by HC-MPATH-001/002 in `src/backend/tests/test_model_path_logs.py`):**

| Site | Level | What it logs |
|---|---|---|
| `src/backend/core/llm/llama_cpp_provider.py:110-113` | WARNING | `"no GGUF model found in %s", self._settings.models_path`: the models directory |
| `src/backend/core/llm/llama_cpp_provider.py:152` | ERROR | `"failed to load model: %s", exc`: llama-cpp-python's load errors carry the path (`ValueError(f"Model path does not exist: {model_path}")`, `llama_cpp/llama.py:384`; `ValueError(f"Failed to load model from file: {path_model}")`, `llama_cpp/_internals.py:62`; read in the pinned 0.3.35 sdist) |
| `src/backend/modules/model_selector.py:477` | ERROR | `f"Failed to load model for tier {tier}: {e}"`: same exception text |
| `src/backend/modules/model_selector.py:660` | INFO | `f"Model downloaded to {result_path}"`: full path |
| `src/backend/modules/model_selector.py:671` | ERROR | `f"Failed to download model for tier {tier}: {e}"`: an `OSError` from `hf_hub_download` names the local file. Not in the review's list; added here because it is the same mechanism in the same function as `:660` |
| `src/backend/modules/model_selector.py:740` | INFO | `f"Found existing model for tier {check_tier}: {path}"`: full path |

`:152` and `:477` log only `exc`; they leak when the exception text holds a path, which llama.cpp's does. Out of scope and left as is: `llama_cpp_provider.py:227` puts `models_path` into a `ProviderUnavailableError` message (an exception, not a log call), and `download_model_async` stores `str(e)` and `str(result)` in the progress row (a DB field, not a log).

**Measured on `b2b3f4e`** (scratch copies of HC-MPATH-003…008 below, run through `bash scripts/pyslot.sh`): **6 failed**, each on a log message that contains `jane-doe-home`, for example `LlamaCppProvider: failed to load model: Failed to load model from file: /tmp/pytest-of-root/…/jane-doe-home/x.gguf` and `Failed to download model for tier low: [Errno 13] Permission denied: '…/jane-doe-home/models/x.gguf'`.

**Design (log text only; return values and control flow unchanged):**
1. `:110-113`: log `Path(self._settings.models_path).name` instead of the directory.
2. `:152`, `:477`, `:671`: log `type(exc).__name__` instead of the exception text (prior art: `modules/embeddings.py:123-125`, "Embedding model failed to load: {type(exc).__name__}").
3. `:660`: `result_path.name`. `:740`: `path.name`.

**Test-first** (`src/backend/tests/test_model_path_logs.py`; same stubs as HC-MPATH-001/002, `caplog` at DEBUG on the module logger; the directory is `<tmp>/jane-doe-home`; each test also asserts that a record at the named level exists, so it is not vacuous):

| Id | Call | Assertion | RED today? |
|---|---|---|---|
| HC-MPATH-003 | `LlamaCppProvider._ensure_initialized()` with `_find_model_path` → `None` and `settings.models_path` monkeypatched to `<tmp>/jane-doe-home/models` | a WARNING record exists; no record contains `jane-doe-home` or `str(tmp_path)` | yes (measured) |
| HC-MPATH-004 | same provider, `_load_llama_class` → a callable raising `ValueError(f"Failed to load model from file: {model_path}")` | returns `False`; an ERROR record exists and names `ValueError`; no path | yes (measured) |
| HC-MPATH-005 | `ModelSelector.load_model(tier)` with a stub `llama_cpp` whose `Llama` raises the same `ValueError` | returns `None`; ERROR record names `ValueError`; no path | yes (measured) |
| HC-MPATH-006 | `ModelSelector(models_path=<tmp>/jane-doe-home/models).download_model(tier)` with a stub `huggingface_hub` module in `sys.modules` (`list_repo_files` → `["x.gguf"]`, `hf_hub_download` → `<local_dir>/x.gguf`) | returns the path; an INFO record contains `x.gguf`; no path | yes (measured) |
| HC-MPATH-007 | `ensure_model_available()` with `get_model_path` → `<tmp>/jane-doe-home/x.gguf` | returns the path; an INFO record contains `x.gguf`; no path | yes (measured) |
| HC-MPATH-008 | as HC-MPATH-006, `hf_hub_download` raising `PermissionError(13, "Permission denied", <local_dir>/x.gguf)` | returns `None`; ERROR record names `PermissionError`; no path | yes (measured) |

No test imports the real `llama_cpp` or reaches the network: both libraries are stubbed in `sys.modules` (CLAUDE.md §3 import boundary; local-first).

**Files:** `src/backend/core/llm/llama_cpp_provider.py` (`:110-113`, `:152` only), `src/backend/modules/model_selector.py` (`:477`, `:660`, `:671`, `:740` only), `src/backend/tests/test_model_path_logs.py`, slots. **Re-run, not edited:** `tests/test_llm_provider_layer.py`, `tests/test_model_integrity.py`, `tests/test_tier_capabilities.py`, `tests/test_llm_structured_output.py`.
**Expected collected delta:** +6. **Est:** 1 h.
**Acceptance:** `pyt tests/test_model_path_logs.py tests/test_llm_provider_layer.py tests/test_model_integrity.py tests/test_tier_capabilities.py tests/test_llm_structured_output.py -q -rfE`: 0 failed; RED output for the 6 new ids; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** ready now. Never beside B-5 (`model_selector.py`; B-5 is blocked on B-3). No ask-first file; `core/model_runner.py` and `core/external_runner.py` are not touched.

## Follow-ups found 2026-10-20, second batch (planned 2026-10-20 on `origin/main` @ `699eb18`)

Five rows: UNCERTAINTY-VERIFY (owner LCP-HL-DIFF follow-up, `owner-decisions-2026-09-27.md:319`), NLI-LOG-M7 (#240 review), and three RRSI app rows from owner rows RRSI-OQ-9, RRSI-OQ-14 and RRSI-OQ-21 (`owner-decisions-2026-09-27.md:330`, `:335`, `:342`). None of them edits a CLAUDE.md §1 ask-first file. Measured facts ran as scratch tests in the planning worktree through `bash scripts/pyslot.sh` (removed afterwards; `git status --short` empty). `pyt` is as defined in the 2026-10-20 batch above.

### UNCERTAINTY-VERIFY — uncertainty sections are never verified, so a false cited value there is served

**Source:** owner LCP-HL-DIFF (`owner-decisions-2026-09-27.md:319`): "Merge as shown. The UNCERTAINTY gap becomes a follow-up row 'uncertainty sections are never verified'." Disclosure (5) of #215.

**Facts (`699eb18`):**
1. `ClaimExtractor.extract_claims` skips every uncertainty section before claims are extracted (`src/backend/modules/claim_extractor.py:130-132`, `if segment_type == "uncertainty": continue`). So the bullet's pointer is half right: `filter_unverifiable_claims` also marks uncertainty claims unverifiable (`:347-349`), but no uncertainty claim ever reaches it. A fix must change both sites.
2. `RAGModule._run_verification_pipeline` (`src/backend/modules/rag.py:1015`) calls `extract_claims` then `filter_unverifiable_claims` (`:1031-1034`); with no verifiable claims it returns `faithfulness_score=1.0` (`:1036-1044`).
3. HC-LCPH-013 (`src/backend/tests/test_rag_headerless.py:241-252`) pins the gap: `FACTS_LINE + "\nUNCERTAINTY:\nYour glucose is 300 mg/dL [cite:1]"` is served with `is_valid True` and `300 mg/dL` in `full_response`. **Measured:** it passes on `699eb18` (`1 passed`, run together with the NLI scratch test below). Its docstring says it is expected to change when this row lands.
4. The app's own uncertainty texts carry no digit and no `[cite:N]` (`rag.py:858-859`, `:1409-1412`, `:1453-1454`); the structured renderer's `UNCERTAINTIES:` list (`:1406`) is model text and is the case this row is about.

**Design (under UNC-VERIFY-SCOPE (a), recommended):** `extract_claims` no longer skips uncertainty sections; `filter_unverifiable_claims` treats an uncertainty claim like a meta claim: unverifiable **unless** it carries a citation or a digit (the existing `carries_fact` test, `:354`). A hedge such as "Reference ranges can vary between laboratories." stays unverified; "Your glucose is 300 mg/dL [cite:1]" is verified against source 1 and withheld when it fails, exactly as in REPORT FACTS. No threshold, `faithfulness.py`, `verifier_agent.py` or `interpret_safety.py` change.

**Test-first** (`src/backend/tests/test_rag_headerless.py`, via `legacy_chat_client` as HC-LCPH-013):

| Id | Assertion | RED today? |
|---|---|---|
| HC-LCPH-013 (changed, docstring says so) | the same answer is now withheld: `"300 mg/dL"` in neither `full_response` nor any segment | yes (measured: served today) |
| HC-LCPH-016 | `UNCERTAINTIES:\n- Reference ranges can vary between laboratories.` after `FACTS_LINE` is still served unchanged, `is_valid True` | no (pin) |
| HC-LCPH-017 | `UNCERTAINTIES:\n- Your glucose is 300 mg/dL` (digit, no cite) is withheld | yes |
| HC-LCPH-018 | unit: `filter_unverifiable_claims` on an uncertainty claim with `[cite:1]` puts it in `verifiable`; one with no digit and no cite in `unverifiable` | yes (the claim is never extracted today) |

Under (b) (cite only), HC-LCPH-017 flips to "served" and is kept as a pin of the remaining gap.

**Files:** `src/backend/modules/claim_extractor.py` (`:130-132`, `:347-349` only), `src/backend/tests/test_rag_headerless.py`, slots. **Re-run, not edited:** `tests/test_phase4_ai_safety.py`, `tests/test_rag_pipeline.py`, `tests/test_legacy_abstain.py`, `tests/test_legacy_cite_eval.py`, `tests/test_rag_structured_cite.py`, and the legacy eval gate (`scripts/legacy_eval_gate.py`, same result as on `main`).
**Expected collected delta:** +3. **Est:** 1.5 h (+ Opus review).
**Acceptance:** `pyt tests/test_rag_headerless.py tests/test_phase4_ai_safety.py tests/test_rag_pipeline.py tests/test_legacy_abstain.py tests/test_legacy_cite_eval.py tests/test_rag_structured_cite.py -q -rfE`: 0 failed apart from the CLAUDE.md §4 environment failures; RED output for HC-LCPH-013 (changed), 017 and 018; legacy eval gate output before and after, identical; full suite per RUNBOOK §6. **Rollback:** revert.
**Owner gates:** **UNC-VERIFY-SCOPE** (execution; **answered 2026-10-20: (a)**, owner-decisions row UNC-VERIFY-SCOPE: "lines that carry a `[cite:N]` or a number; hedges without either stay unchecked"). Wording as asked: "Uncertainty sections are never verified today (`claim_extractor.py:130-132`), so `UNCERTAINTY:\nYour glucose is 300 mg/dL [cite:1]` is served even when source 1 says otherwise (pinned by HC-LCPH-013). Which uncertainty lines should be checked like report facts? (a) lines that carry a `[cite:N]` or a number; hedges without either stay unchecked (Recommended: closes the measured leak; the app's own uncertainty texts have neither, so they are unaffected) (b) only lines that carry a `[cite:N]`; an uncited number stays unchecked (c) none; keep the gap and the pin." **UNC-VERIFY-DIFF** (merge only, open; asked after the draft PR exists), as LCP-HL-DIFF: owner yes on the exact `claim_extractor.py` diff with the eval-gate output.
**Order:** ready (build on a draft; UNC-VERIFY-SCOPE answered (a)); merge blocked on UNC-VERIFY-DIFF. Never beside B-3 (B-3 rebases on what the verifier withholds; queue bullet). No open PR touches `claim_extractor.py` or `test_rag_headerless.py` (checked against #210, #230, #239, #245, #246). No ask-first file.

### NLI-LOG-M7 — the NLI loader's logger-restore test starts at INFO, so mutant M7 survives

**Source:** #240 review (EMB-LOG-M7's twin in the NLI loader). Never run beside G-C5 (queue bullet; G-C5 is done, its real-model steps are pending).

**Facts (`699eb18`):** `load_local_cross_encoder` (`src/backend/modules/embeddings.py:72`) saves `prev_levels = [lg.level for lg in quiet]` (`:101`), raises each logger to `max(getEffectiveLevel(), WARNING)` (`:103`) and restores in `finally` (`:111-112`). Its only restore test, HC-GC5-004c (`src/backend/tests/test_gc5_nli_flag.py:443-461`), sets both loggers to INFO first, where `.level == getEffectiveLevel()`.

**Measured (scratch test, then M7 applied with `sed` to a working copy of `embeddings.py`, reverted with `git checkout`):** a NOTSET-start test passes on `699eb18`; under M7 (`prev_levels = [lg.getEffectiveLevel() …]`) it fails with `assert 30 == 0`, while HC-GC5-004c still passes (`1 failed, 1 passed`).

**Design:** test only, as EMB-LOG-M7 (#240).

| Id | Assertion | RED today? |
|---|---|---|
| HC-GC5-004d | same setup as HC-GC5-004c (corrupt bundle, `verify_model_file` → VERIFIED, `CrossEncoder` stub raising); `logging.getLogger("sentence_transformers").setLevel(NOTSET)`; assert `getEffectiveLevel() != NOTSET` first (non-vacuous); `load_local_cross_encoder()` raises `EmbeddingModelUnavailableError`; then `.level == NOTSET`; restore in `finally` | no (pin). M7 fails it (measured above) |

**Files:** `src/backend/tests/test_gc5_nli_flag.py`, slots. `src/backend/modules/embeddings.py` shows an empty diff.
**Expected collected delta:** +1. **Est:** 0.25 h.
**Acceptance:** `pyt tests/test_gc5_nli_flag.py tests/test_embedding_fail_closed_paths.py -q -rfE`: 0 failed; the M7 RED output pasted; `git diff origin/main -- src/backend/modules` empty. **Rollback:** revert.
**Order:** ready now. No open PR touches `test_gc5_nli_flag.py`. No ask-first file.

### AGENT-ENABLED-TOGGLE — no Settings switch for the agent, and care-task text is not labelled unverified

**Source:** owner RRSI-OQ-9 (`owner-decisions-2026-09-27.md:330`): "Keep T0 on by default; add a Settings toggle for `agent_enabled`; label care-task text as unverified in answers."

**Facts (`699eb18`):**
1. The backend already has the flag: `PATCH /settings/model/agent` (`src/backend/api/model_settings.py:1201-1229`, audited as `settings.agent.update`), and `GET /settings/model` returns `agent_enabled` (`:465`). `git grep -n agent_enabled -- src/frontend/src` prints nothing: no type field, hook or switch.
2. `_care_task_sentences` (`src/backend/modules/agent/nodes/draft.py:184-219`) writes `Open follow-up: {title}{due}. The note says: "{quote}"` with no label, although `query_care_tasks` returns document-extracted free text (`modules/agent/tools/query_care_tasks.py:5`, `:81`). Prior art for a label: unverified timeline events are rolled into a "pending your verification" sentence (`draft.py:262-300`, HC-AGQ-052b).

**Design:**
1. Frontend: `agent_enabled: boolean` on `ModelSettings` and `useSaveAgentSettings()` (`apiPatch('/settings/model/agent', …)`, invalidating the model-settings query) in `src/frontend/src/services/modelSettings.ts`, exported through the `src/frontend/src/services/index.ts` barrel (AGENT.md:18; it lists `modelSettings` hooks by name, `:164`, `:177`, `:324`), and the card imports it from `@/services`; a small `AgentSettingsCard.tsx` in `src/frontend/src/components/settings/` (one switch, on by default, copy: "Use the step-by-step assistant. When off, answers come from the simpler search path."); one import and render line in `SettingsPage.tsx`.
2. Backend: each care-task sentence gets the AET-LABEL wording (recommended: `Open follow-up (from your documents, not verified by you): …`). Summary sentence and citations unchanged.

**Test-first:**

| Id | Where | Assertion | RED today? |
|---|---|---|---|
| HC-AGQ-050 (changed) | `src/backend/tests/agent/test_agentic_queries.py` | each care-task sentence contains the AET-LABEL text; citations and groundedness mapping unchanged (`mapping.dropped == []`) | yes |
| HC-AET-001 | `src/backend/tests/test_model_settings_api.py` via `route_client` | `PATCH /settings/model/agent {"agent_enabled": false}` → 200, then `GET /settings/model` shows `false`; one `settings.agent.update` audit row | no (pin of the route the card calls) |
| HC-AET-FE-001…002 | `src/frontend/src/__tests__/AgentSettingsCard.test.tsx` | the switch reflects `agent_enabled`; toggling calls PATCH with the new value | yes (no card) |

**Files:** `src/backend/modules/agent/nodes/draft.py` (`_care_task_sentences` only), `src/backend/tests/agent/test_agentic_queries.py` (HC-AGQ-050 only), `src/backend/tests/test_model_settings_api.py` (HC-AET-001 only), `src/frontend/src/services/modelSettings.ts`, `src/frontend/src/services/index.ts` (export `useSaveAgentSettings` through the barrel, AGENT.md:18), `src/frontend/src/components/settings/AgentSettingsCard.tsx`, `src/frontend/src/pages/SettingsPage.tsx` (one import + render line), `src/frontend/src/__tests__/AgentSettingsCard.test.tsx`, slots.
**Expected collected delta:** +1 backend. **Est:** 2 h.
**Acceptance:** `pyt tests/agent/test_agentic_queries.py tests/test_model_settings_api.py -q -rfE`: 0 failed; `cd src/frontend && npx tsc --noEmit && npx vitest run src/__tests__/AgentSettingsCard.test.tsx` (on WSL `/mnt/c` vitest stalls: SKIPPED with that reason, CI runs it); full suite per RUNBOOK §6. **Rollback:** revert.
**Owner gates:** RRSI-OQ-9 answered (`:330`). **AET-LABEL** (wording; **answered 2026-10-20: (a)** "`Open follow-up (from your documents, not verified by you): …`", owner-decisions row AET-LABEL). Wording as asked: "Care-task sentences in agent answers come from text extracted from your documents and are not verified. Which label? (a) `Open follow-up (from your documents, not verified by you): …` (Recommended: says where it came from and that nobody checked it) (b) `Unverified follow-up: …` (c) a separate line after the list: `These follow-ups come from your documents and are not verified.`"
**Order:** ready (AET-LABEL answered (a)). `SettingsPage.tsx` is a shared file (contracts §b) and #239 (RSI1-DONATE PR-2) edits it, but #239 is parked as a draft by owner DON-RECALL-R2 (donation stays off until after 2026-10-24), so it is not running: L0 rules whether this row builds now and #239 rebases its one `SettingsPage.tsx` line later (recommended), or waits. Never beside MSET-EXT-AUDIT-CT's successors on `test_model_settings_api.py` (none open). No ask-first file.

### RUNSTEP-CONTRACT — the RunStep comment says handles, but `act` stores full tool outputs

**Source:** owner RRSI-OQ-14 (`owner-decisions-2026-09-27.md:335`): "Correct the comment; add a test that RunLog never reaches audit, cache, persistence or donation."

**Facts (`699eb18`):** `RunStep.payload` is commented `# handles, never raw PHI` (`src/backend/modules/agent/state.py:64`), but `act` stores `{"tool_name": …, "output": output.model_dump(mode="json")}` (`src/backend/modules/agent/nodes/act.py:50-59`, payload at `:56`), i.e. full tool output, values included. `graph.replay` relies on that, while its docstring repeats the wrong claim: "handles only, never raw PHI — state.py's `RunStep` contract" (`graph.py:240-244`). The RunLog is built in `graph.py:176` and lives only in memory; no `RunLog` reference exists outside `modules/agent/` except the eval scorer (`modules/agent/eval/scorer.py:293-328`).

**Design:** comments only: `state.py:64` (e.g. `# full tool output (values included); in memory only, never persisted, audited, cached or donated (RRSI-OQ-14)`) and the `replay` docstring at `graph.py:240-244` (same correction; #248 Codex review MINOR 6), plus the isolation test. No product change.

| Id | Assertion | RED today? |
|---|---|---|
| HC-RUNLOG-001 | one `POST /assistant/chat` through `route_client` on the agent path, with a stub tool whose output carries a canary in a field `draft` never renders (the implementer picks it from `draft.py` and asserts the canary is in `run_log.steps`, so the test is not vacuous); the canary is absent from every `create_audit_log` call's arguments, from the agent cache entry (`modules/agent/cache.py` `put_cached`), from the stored `ChatTurn` rows, and from `caplog` | no (pin). Mutant: `put_cached` storing `run_log.model_dump()` beside the terminal fails it |

**Donation leg: moved out of this row (#248 Codex review MAJOR 4, and owner DON-RECALL-R2).** As first planned, HC-RUNLOG-002 could pass on an empty collection, so it proved nothing. And there is nothing to test on `main`: no code collects donations (`collect` exists only in #239), RRSI-OQ-24 (`owner-decisions-2026-09-27.md:345`) bars any `agent_traces` collection until a new owner row, and owner DON-RECALL-R2 (2026-10-20) parked #239: "donation stays off" until a stronger local detector, as its own row and gate, after 2026-10-24. The donation leg is now a requirement on whichever row turns donation collection on (written into the [RSI1-DONATE plan](../2026-10-17-rsi1-opt-in-donation-pipeline-plan.md#delta-2026-10-20-second-planner-211-review-notes-for-pr-2-and-rrsi-oq-25)): grant `fine_tune` consent on the current copy version, run one agent chat with the canary, rate that turn so a `ResponseFeedback` row exists, run `collect`, and require a **positive control** (the rated turn's redacted question and answer are donated, count ≥ 1) and the canary absent from every donated row; a scratch mutant that copies `run_log` payloads into the donated record must fail it.

**Files:** `src/backend/modules/agent/state.py` (`:64` comment only), `src/backend/modules/agent/graph.py` (`replay` docstring `:240-244` only), `src/backend/tests/agent/test_runlog_isolation.py` (new), slots.
**Expected collected delta:** +1. **Est:** 1.5 h.
**Acceptance:** `pyt tests/agent/test_runlog_isolation.py tests/agent/ -q -rfE`: 0 failed; the mutant output pasted; full suite per RUNBOOK §6. **Rollback:** revert.
**Owner gates:** RRSI-OQ-14 answered (`:335`); none open.
**Order:** ready now (no dependency on #239). No ask-first file.

### CHAT-TREND-DEF — the chat trend uses first-vs-last with strict equality; the owner wants the Trends-page definition

**Source:** owner RRSI-OQ-21 (`owner-decisions-2026-09-27.md:342`): "Adopt the Trends page's latest-vs-prior comparison with a 5% stable band."

**Facts (`699eb18`) — the owner row's premise does not hold:**
1. Agent chat: `compute_trend` compares first and last point with strict equality (`src/backend/modules/agent/tools/compute_trend.py:83-89`); `draft` turns that into "increased / decreased / stayed about the same" (`modules/agent/nodes/draft.py:176-179`).
2. The Trends page shows `trendData.summary` (`src/frontend/src/pages/TrendsDashboard.tsx:403`, `:528-530`) from `GET /observations/trends/{analyte}` (`src/frontend/src/services/observations.ts:51`), which computes **first-vs-last** with a 5% band (`src/backend/api/observations.py:660-671`). The doctor export does the same (`src/backend/api/export.py:355-368`).
3. The **latest-vs-prior** 5% definition the research cited (`02-verdicts.md:183`) is `AnalyticsModule.calculate_trend` (`src/backend/modules/analytics.py:96-112`), and nothing calls it: `git grep -n "AnalyticsModule\|calculate_trend" -- src/backend` finds only its definition and the `modules/__init__.py` export. The Trends page icon (`TrendsDashboard.tsx:216-221`) is called with `previous = undefined` (`:595`), so it always shows the flat icon.
4. Other trend texts: the legacy chat chunk uses 3% over the recent rows (`modules/rag.py:465-473`); the lab interpretation uses latest-vs-prior 5% (`modules/interpret.py:531-541`).

So "the Trends page's definition" and "latest-vs-prior" name different rules. Which one the owner meant is a new gate (CTD-DEF); this plan does not choose.

**Design (agent path only unless CTD-SCOPE says otherwise):** `compute_trend` takes the CTD-DEF rule with a 5% band and no division by zero (a zero base gives "flat", as `api/observations.py:664` does). `draft` wording unchanged.

| Id | Assertion | RED today? |
|---|---|---|
| HC-CTD-001 ×3 | `compute_trend` on points 100 → 103 gives `flat`; 100 → 110 gives `up`; 100 → 90 gives `down` | 100 → 103 yes (strict equality gives `up`) |
| HC-CTD-002 | under CTD-DEF (a): points 100, 150, 104 give `flat` (first-vs-last 4%); under (b): `down` (latest-vs-prior −31%) | yes under (b); under (a) yes (strict gives `up`) |
| HC-CTD-003 | parity: for the same verified series, `compute_trend`'s direction agrees with the word in `GET /observations/trends/{analyte}`'s summary (under (a) only) | yes |

**Files:** `src/backend/modules/agent/tools/compute_trend.py` (`:83-89` only), `src/backend/tests/agent/test_s2_loop.py` or a new `src/backend/tests/agent/test_chat_trend_def.py` (the implementer picks one; the file list names the one used), slots. Under CTD-SCOPE (b) also `src/backend/modules/rag.py` (`:465-473` only) and `src/backend/tests/test_biomarker_assistant.py`.
**Expected collected delta:** +5. **Est:** 1 h (+1 h under CTD-SCOPE (b)).
**Acceptance:** `pyt tests/agent/ tests/test_assist_agent_dates_http.py tests/test_export_trend_units.py -q -rfE`: 0 failed; RED output; full suite per RUNBOOK §6. **Rollback:** revert.
**Owner gates:** RRSI-OQ-21 answered (`:342`), but on a premise that does not match the code (facts 2-3). **CTD-DEF answered 2026-10-20: (a)** "first-vs-last with a 5% band, the rule the Trends page and export show"; **CTD-SCOPE answered 2026-10-20: (a)** "no, agent path only" (owner-decisions rows CTD-DEF, CTD-SCOPE). Wording as asked: **CTD-DEF**: "You chose 'the Trends page's latest-vs-prior comparison with a 5% stable band' for chat trends. The Trends page actually compares the **first and last** result with a 5% band (`api/observations.py:660-671`, the doctor export does the same); the latest-vs-prior rule exists only in an unused module (`modules/analytics.py`). Which rule should chat use? (a) first-vs-last with a 5% band, the rule the Trends page and export show (Recommended: one definition across the app, as your answer intended, and the smallest change) (b) latest-vs-prior with a 5% band, as worded; chat and the Trends page summary would then disagree (c) latest-vs-prior with a 5% band for chat **and** the Trends page summary (changes the Trends page text too; a separate row)." **CTD-SCOPE** (open): "Should the legacy chat path's trend line (3% over recent rows, `modules/rag.py:465-473`) change too? (a) no, agent path only (Recommended: the legacy text is model context, and `rag.py` is shared with B-3) (b) yes, same rule."
**Order:** ready (CTD-DEF (a), CTD-SCOPE (a): agent path only, so `rag.py` is not touched). No open PR touches `compute_trend.py`. No ask-first file.

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
| Q5a, Q5b, GC5-MODEL, GC5-PLAN | G-C5 | scaffold pack §3 | answered 2026-10-17 (`owner-decisions-2026-09-27.md:225-228`); follow-ups OL-1, OL-2 and OL-3 in the [plan](../2026-10-18-GC5-hc-m11-nli-flag-off.md) answered 2026-10-19 (`:269-271`) |
| **GC5-ASKFIRST** | G-C5 | approve the exact `verifier_agent.py:304-317` hunk (ask-first file, CLAUDE.md §1) | answered 2026-10-17 (`:238`: approved in advance, Opus review still runs, owner merges); `faithfulness.py` is not edited |
| SCA-RULING | SAFE-CHAT-AGENT | A accept / B pattern floor in `guard.py` | not asked |
| SCF-RULING | SAFE-CHAT-FALLBACK | A accept / B screen / C reword seed (ask together with lane B IBF-1; same 7 seed fields) | not asked |
| SCH-RULING | SAFE-CHAT-HISTORY | A new answers only / B read-time mask | not asked |
| AAD-ROW, AAD-SEMANTICS | ASSIST-AGENT-DATES | scope; narrow or add? | answered 2026-10-16 (all four filters) and 2026-10-17 (ADD). AAD-TREND-ADD open (trend answers) |
| RR500-MAP | RAG-RUNTIME-500 | 503 + fixed sentence (proposed: "The explanation could not be generated right now. Please try again.") | not asked |
| CFR-FORMAT | CHAT-FACT-ROUTING Task 3 | how agent fact answers read: (a) display names + local dates + latest per analyte, cap 10 / (b) names + dates only / (c) no change | **(a)**, answered 2026-10-18 |
| LHH-SCOPE | LOCAL-HF-HUB | (a) fold into W-8 / (b) interim `local_files_only` with today's hash fallback / (c) interim fail-closed (needs Q-FC) | not asked (planned 2026-10-17) |
| IAW-WORDING | INTERP-ADVICE-WORDING | (a) educational LDL sentence + rewrite untouched installed rows / (b) (a) + the glucose sentence / (c) keep | **(b)**, answered 2026-10-18 |
| **LCP-HL-SCOPE** | LCP-HEADERLESS | (a) line-start headers, text outside a section counts as REPORT FACTS (cited unrendered JSON still served raw) / (b) (a) + withhold unrendered structured text / (c) line-start headers only (exact wording in [LCP-HEADERLESS](#lcp-headerless--the-legacy-parser-finds-headers-anywhere-drops-text-before-them-and-never-checks-headerless-text-for-citations)) | **open** (planned 2026-10-19; recommended (a)) |
| **LCP-HL-LABELS** | LCP-HEADERLESS | yes/no: remove `[YOUR_RESULTS:N]`, `[REFERENCE:N]`, `[USER_DOCUMENT:N]`, `[USER_OBSERVATION:N]` from served text | **open** (split out in PR #202 review round 1; recommended (a) yes) |
| **LCP-HL-DIFF** | LCP-HEADERLESS | merge only: owner yes on the exact `rag.py` diff (citation check) | **open**; asked after the draft PR exists |
| **UNC-VERIFY-SCOPE** | UNCERTAINTY-VERIFY | (a) verify uncertainty lines carrying `[cite:N]` or a number / (b) `[cite:N]` only / (c) keep the gap (exact wording in [UNCERTAINTY-VERIFY](#uncertainty-verify--uncertainty-sections-are-never-verified-so-a-false-cited-value-there-is-served)) | **(a)**, answered 2026-10-20 (owner-decisions row UNC-VERIFY-SCOPE) |
| **UNC-VERIFY-DIFF** | UNCERTAINTY-VERIFY | merge only: owner yes on the exact `claim_extractor.py` diff with the eval-gate output | **open**; asked after the draft PR exists |
| **AET-LABEL** | AGENT-ENABLED-TOGGLE | care-task label wording: (a) `Open follow-up (from your documents, not verified by you): …` / (b) `Unverified follow-up: …` / (c) one trailing sentence | **(a)**, answered 2026-10-20 (owner-decisions row AET-LABEL); RRSI-OQ-9 answered (`owner-decisions-2026-09-27.md:330`) |
| **CTD-DEF** | CHAT-TREND-DEF | RRSI-OQ-21's "Trends page's latest-vs-prior" names two different rules: (a) first-vs-last 5% (what the Trends page and export show) / (b) latest-vs-prior 5% as worded / (c) latest-vs-prior for chat and the Trends page | **(a)**, answered 2026-10-20 (owner-decisions row CTD-DEF; refines RRSI-OQ-21) |
| **CTD-SCOPE** | CHAT-TREND-DEF | (a) agent path only / (b) also the legacy chunk's 3% line in `rag.py` | **(a)**, answered 2026-10-20 (owner-decisions row CTD-SCOPE) |

Ask-first files touched by this lane: only `modules/verifier_agent.py` (G-C5). LCP-HEADERLESS edits the citation check in `modules/rag.py` (not a CLAUDE.md §1 file), so its diff has the named merge gate LCP-HL-DIFF. `interpret_safety.py`, `redaction.py`, `faithfulness.py`, `core/auth.py` and auth/encryption code stay read-only. SAFE-CHAT-AGENT option B only imports `PROHIBITED_PATTERNS`.

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
