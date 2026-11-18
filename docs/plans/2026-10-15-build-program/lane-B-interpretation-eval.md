# Lane B — Interpretation and Eval

**Last Updated:** 2026-10-31 (CRIT-LOG-SCRUB answered "Scrub the log line first (Recommended)": new [delta 2026-10-31b](#delta-2026-10-31b-crit-log-scrub-scrub-the-critical-value-log-lines) plans row CRIT-LOG-SCRUB, merge-only gate CRIT-LOG-DIFF; INTERP-WITHHOLD-MSG Task 3 (#433) waits on it); 2026-10-31 (OQ-IWM-CRIT answered "Keep the flag (Recommended)": INTERP-WITHHOLD-MSG Tasks 1-2 done (#428, `e4246290`), Task 3 ready); 2026-10-31 (INTERP-ENFORCE-DIFF answered "Merge, then show message (Recommended)": new [delta 2026-10-31](#delta-2026-10-31-interp-withhold-msg-show-the-withheld-message) plans follow-up row INTERP-WITHHOLD-MSG, with open question OQ-IWM-CRIT drafted, not asked); 2026-10-31 (ISE-HGB-LOW-REWORD answered "Yes, to optional": INTERP-SAFETY-ENFORCE Task 1 gains a 12th field edit, Hemoglobin low "indicates anemia" becomes "can be a sign of anemia"); 2026-10-30 (ISE-SEED-HITS answered "Reword built-in text first (Recommended)": delta 2026-10-30b gains Task 1 (seed-text reword via `_TEXT_REVISIONS`, HC-ISE-005/006), the INTERP-ENFORCE-DIFF still-withheld list must be empty, row ready again); 2026-10-30 (ISE-DISC-SCOPE answered "Withhold on any failure": INTERP-SAFETY-ENFORCE [delta 2026-10-30b](#delta-2026-10-30b-ise-disc-scope-withhold-on-any-failure) on `143a969`: condition `not passed`, HC-ISE-002 inverted, newly withheld cases listed, seed-text hits found, new drafted gate ISE-SEED-HITS, row blocked on it); 2026-10-30 (INTERP-SAFETY-ENFORCE plan delta after #304 `64b92eb` on `144b5d4`: Facts 1-2, Design 1, tests and Files replaced; HC-ISV-003 licensed; new drafted question ISE-DISC-SCOPE); 2026-10-26 (post-merge batch on `0e8b2b2`: JUDGE-LAYA-RESEARCH done (#373); owner answered JUDGE-SWAP by free text; JUDGE-LAYA-FT and JUDGE-NLI-TUNE planned; new gates JUDGE-SWAP-ADOPT, LAYA-CKPT-HOST, Owner gates items 16-17); 2026-10-22 (owner prompts 38-39 on `d2843e8`: INTERP-SAFETY-ENFORCE and JUDGE-LAYA-RESEARCH planned; new gates INTERP-ENFORCE-DIFF, JUDGE-SWAP); 2026-10-22 (bug diagnosis on `5f7c67c`: JUDGE-THINK, EXTRACT-UNIT-MGL, EXTRACT-DOB-DATE, INTERP-GROUNDED-MD, INTERP-RENDER-2, INTERP-SAFETY-META, VERIFY-DOCS-STALE planned; new gates JUDGE-THINK, EXTRACT-DATE-PRIORITY, INTERP-DISC-ORDER, Owner gates items 11-13); 2026-10-21 (EXTRACT-NL-DIFF marked answered, prompt 28); 2026-10-21 (EXTRACT-REGEX-NEWLINES planned on `b9d285e`; new merge gate EXTRACT-NL-DIFF, Owner gates item 10, no option recommended; item 9 PATH-NL-DIFF marked answered to the wording in its owner-decisions row); 2026-10-17 (INTERP-RENDER, EXTRACT-FORMATS planned)
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

## JUDGE-LAYA-RESEARCH — a typed-decision encoder (Laya) or the local NLI cross-encoder as the B-3 advice judge (docs only)

**Source:** owner prompt 39 (2026-10-22, JUDGE-THINK re-asked with the owner's typed-decision proposal; owner row JUDGE-THINK, `owner-decisions-2026-09-27.md:389`, merged in #291 `df9ca7f`): **"Think off now + research Laya (Recommended)"**: "(a) as planned (judge-only think=false) so B-3 works now, plus a research row comparing a fine-tuned Laya and the repo's local NLI cross-encoder as the judge (accuracy, latency, dependency, training-data source); any swap comes back to you." The think-off half is #289's row JUDGE-THINK (option (a)); this row is the research half. Planned 2026-10-22 on `d2843e8`.

**Facts (`d2843e8`; Hugging Face API read 2026-10-22):**
1. The B-3 judge (§B-3 above, draft #264) asks the local generative model for one word, `ALLOW` or `BLOCK`, with `InferenceConfig(max_tokens=3, temperature=0.0, timeout_seconds=2)`, and fails closed on anything else (owner PARA-R3-Q2Q3). Owner bounds for sign-off (PARA-R3-Q4Q5, `owner-decisions-2026-09-27.md:125`): 2 s p95 / 90% recall / 5% / tier-2. B-4 measures it on the owner's sealed S5 (OW-3).
2. `convaiinnovations/laya` @ `7b928d828b7b`: card licence `apache-2.0`, library `transformers`, task `text-classification`; weights `model.safetensors` 843 MB (plus `typed-decisions/` and `multilingual/` variants; `convaiinnovations/laya-typed-decisions` @ `e929ae5cf69b`, 843 MB). The repo also ships Python files (`rl_agent_api.py`, `rl_common.py`, `email_utils.py`): any load that needs `trust_remote_code=True` is excluded unless that code is read and pinned. Per the owner's prompt-38 free text: ModernBERT-large encoder, about 421M parameters, typed decision head; per L0's prompt-39 question (from the card, secondary to this row): zero-shot 0.362 vs 0.318 random, so it needs fine-tuning.
3. The repo's local NLI cross-encoder: `cross-encoder/nli-deberta-v3-xsmall` @ `a15087641532`, `apache-2.0`, 283 MB safetensors, already bundled (`scripts/download_models.py nli`, pinned repo + revision + sha256; `modules/embeddings.py:52-105`, `local_files_only=True`). Used today only behind the HC-M11 flag (GC5-NLI-NEUTRAL: veto only).
4. `transformers 5.20.1`, `torch 2.14.1+cpu` are in the 3.11 venv (pulled by `sentence-transformers`, `requirements.txt:73`); ModernBERT support in that `transformers` is to be checked, not assumed.
5. Labelled advice text already in the repo (none of it is S5): `src/backend/tests/fixtures/prohibited_patterns/in_sample.json`, `held_out_dev.json` (175 allow), `held_out_final.json` (185 allow), `held_out_final2.json` (171 allow), each with `must_block` lists, and `must_not_regress.json` (215). `held_out_final*.json` are the regex filter's final held-out splits.

**Questions the research answers (primary sources: model cards, licence files, code; each with URL and read date):**
1. **Accuracy method, no contamination:** S5 is never read, copied, summarised or used for training or tuning; it stays the exam (B-4). Training and tuning data: `in_sample.json`, `must_not_regress.json` and a new labelled training set written by a separate agent session (the `held_out_*` author pattern); evaluation: `held_out_dev.json` only. `held_out_final.json` and `held_out_final2.json` are not touched (they keep their role for the regex filter). The research specifies the split, label balance, and the reporting metric (recall on `must_block`, false-block rate on `must_allow`, with Wilson 95% intervals) so a later build row can run it unchanged.
2. **Latency on this box:** p50/p95 per answer for Laya (zero-shot, and the fine-tuned size class), the NLI cross-encoder (as an entailment-to-a-"this is medical advice" hypothesis judge), and today's generative judge with think off (JUDGE-THINK), CPU and GPU, two concurrent requests (R-7); scratch scripts pasted, not committed.
3. **Zero-shot baseline on `held_out_dev.json`** for both encoders, pasted.
4. **A scratch fine-tune of Laya** (the owner asked to compare a *fine-tuned* Laya): on the GPU box, in a separate scratch venv (never the repo venv; any trainer package such as `accelerate` stays there), on the training split of Q1 only, evaluated on `held_out_dev.json`. The new agent-written training set is produced in this row by a separate agent session that has not seen `held_out_dev.json`, `held_out_final*.json` or S5, written into the scratch directory and not committed; it must bring the training split to at least 150 `must_allow` and 150 `must_block` items (today's in-repo sources give 215 block-only and 15 allow), or the fine-tune does not run and the row takes the "cannot run" path below; the weights stay in the scratch directory and are deleted after the run, never committed or bundled. Pasted: the command, the training-set size and label balance, the dev-split metrics with Wilson intervals and the run time. If it cannot run (dependency, VRAM, time), the row says so with the error, and JUDGE-SWAP then states that only zero-shot numbers exist (a narrowing of the owner's request, said in plain words). It also records what a real build would need: the trainer and its licence, where the weights live, how they are pinned and bundled.
5. **Dependency, licence, size, Python 3.11:** whether either loads with the existing packages and `local_files_only=True` (no new pip package, no `trust_remote_code`); disk size; bundling with the `cmd_nli` pattern; offline load with the network blocked.
6. **Fit with the frozen design:** what a swap reopens (B-3's `FROZEN_PROMPT`, parser and `InferenceConfig`; B-4's freeze sha, MM-2 and the owner's sign-off); how the encoder would sit behind `ModelRunner` (CLAUDE.md §3: all LLM calls go through `ModelRunner`; an encoder classifier may not, which is a design question the research states, not answers).

**Output:** `docs/research/2026-10-22-judge-laya/00-README.md` (new), ending with a filled-in draft of **JUDGE-SWAP** (below). No code under `src/`, no dependency, no model committed.
**Files:** `docs/research/2026-10-22-judge-laya/00-README.md` (new), `docs/INDEX.md`, `docs/_link_graph.json`. No slots. **Est:** 5 h (research 2 h, training set 1.5 h, scratch fine-tune and measurement 1.5 h). **Runtime:** claude on the GPU box (network for model cards and the scratch downloads only; scratch directory outside the repo). Never beside another model-host run (KV-PREFIX-MEASURE, DON-NER-MEASURE, MM-2).
**Acceptance:** the evidence states, with a command, that S5 (`~/asclexis-sealed/`) was not read (`ls` of the scratch dir and the scripts show no S5 path); every claim has a source and date; latency and zero-shot tables pasted with commands; `git diff --name-only origin/main...HEAD` lists only the three files; `git diff origin/main -- src/ requirements*.txt src/backend/requirements*.txt` empty; docs gates clean.
**Owner gates:** JUDGE-THINK answered "Think off now + research Laya (Recommended)" (`owner-decisions-2026-09-27.md:389`, prompt 39; #291 merged `df9ca7f`). **JUDGE-SWAP** (new, asked after the research; no recommendation until it lands). Draft: "The research compared Laya ([fine-tuned on the training split | zero-shot only, because: reason]), the local NLI model and today's judge with thinking off: [dev-split accuracy, latency, size, new dependency]. Your sealed S5 was not used. A swap reopens B-3's frozen design and B-4's sign-off. What next?" Options in plain words: "Keep today's judge", "Fine-tune Laya next", "Try the NLI judge", "Stop here". Tradeoffs: keeping today's judge costs nothing new and is what B-4 measures; a Laya fine-tune needs a labelled training set and a trainer dependency and restarts B-4; the NLI judge is already bundled but was built for entailment, not advice. Analogy: keep the referee you have with a "just the call" rule while a specialist referee trains; you decide later whether the specialist gets the job.
**Order:** ready (docs, no slot). Independent of JUDGE-THINK and B-3 (#264); touches no B-3 file. No ask-first file.
**Done 2026-10-26** (#373, `0e8b2b2`). JUDGE-SWAP was asked with the research's draft and answered by free text (below).

## JUDGE-LAYA-FT — fine-tune Laya with a calibration split and repeated runs (measurement; model host)

**Source:** owner JUDGE-SWAP, answered 2026-10-26 (L0 AskUserQuestion) by free text, verbatim: "Try both Layla fine tune and NLI judge" (owner-decisions row JUDGE-SWAP). L0 reading, not the owner's words: the answer combines option 2 ("Fine-tune Laya next") and option 3 ("Try the NLI judge"), and "Layla" is Laya (`convaiinnovations/laya`). This row is option 2's measurement; [JUDGE-NLI-TUNE](#judge-nli-tune--tune-the-bundled-nli-cross-encoders-hypothesis-and-threshold-as-the-advice-judge-measurement-model-host) is option 3's. Planned 2026-10-26 on `0e8b2b2`.

**Facts (from the [JUDGE-LAYA-RESEARCH note](../../research/2026-10-22-judge-laya/00-README.md), #373):** one pre-registered fine-tune of `convaiinnovations/laya` @ `7b928d828b7b` (embeddings and the bottom 14 of 28 encoder layers frozen; 3 epochs, batch 16, AdamW lr 2e-5; seed 0), trained on `in_sample.json` + `must_not_regress.json` + an agent-written `agent_train_v2.json` (42 + 215 + 130 must_block, 15 + 220 must_allow), caught 98.9% of advice on `held_out_dev.json` and wrongly blocked 15.4% of safe answers at a 0.5 threshold fixed in advance (owner bound 5%); dev AUROC 0.991. There was one run, no threshold tuning and no calibration split. CPU p95 372 ms on the 24-vCPU box. The dev split sits near the ceiling for the generative judges and does not predict S5.

**What the row measures (each step's command and raw output pasted):**
1. **Data, all written before the first training run, none of it S5.** S5 (`~/asclexis-sealed/`) is never read, copied, summarised or used. A separate agent session that has not seen `held_out_dev.json`, `held_out_final*.json` or S5 writes (a) a larger training set that brings the training split to at least 500 must_block and 500 must_allow items, and (b) a disjoint calibration split of at least 150 must_block and 150 must_allow items, used only to choose the threshold. Both stay in the scratch directory, are not committed, and are recorded by size, label balance and sha256. `held_out_final.json` and `held_out_final2.json` are not touched. `held_out_dev.json` is the report split only: nothing is tuned on it.
2. **Pre-registration.** Before the first run the README fixes the checkpoint and revision, freeze depth, epochs, batch, learning rate, the number of runs (at least 3, each with its own seed) and the threshold rule: the lowest threshold whose false-block rate on the calibration split is at most 5%. The pre-registration is committed before any dev result. A change after a dev score has been seen is a new pre-registration, reported beside the first.
3. **Repeated runs.** Per run: training time, the threshold chosen on calibration, and on dev the recall on must_block, the false-block rate on must_allow (both with Wilson 95% intervals) and AUROC. The summary lists every run and the range, not only the best.
4. **The 5% bound.** Per run, the README says whether the dev false-block rate is at most 5% and recall at least 90% (PARA-R3-Q4Q5, `owner-decisions-2026-09-27.md:125`; those bounds are for S5, so dev is a guide only), and whether the upper Wilson bound of the false-block rate is under 5%. It does not say the bound is met unless every run meets it.
5. **Latency.** p50/p95 per answer for the fine-tuned model, CPU and GPU, one and two concurrent requests (R-7), as in the research.
6. **What a build would need** (stated, not done): trainer packages and their licences, where the weights would live, how they would be pinned (revision + sha256, the `cmd_nli` pattern in `scripts/download_models.py`), the model-code question (`trust_remote_code` stays excluded; any Laya code needed is read and pinned), and that hosting or bundling our own fine-tuned checkpoint is owner gate **LAYA-CKPT-HOST**.

**Output and files:** `docs/research/<run date>-judge-laya-ft/00-README.md` (new), `docs/INDEX.md`, `docs/_link_graph.json`. Nothing under `src/`, no dependency, no model committed. No slots. **Est:** 8 h.
**Runtime:** claude on the GPU box (model host). Never beside another model-host run (DON-NER-MEASURE, QWEN3-4B-TIER, AUDIT-DB-LOCKED Task 1, KV-NUMCTX-VERIFY, MM-2, JUDGE-NLI-TUNE) and no pytest beside it: hold `hold_slots.sh` (locks 1–8) for the whole run. Any trainer package goes in a scratch venv outside the repo, never the repo venv (JUDGE-LAYA-RESEARCH Q4). The weights are deleted after the run.
**Acceptance:** a command shows S5 was not read (a listing of the scratch directory and the scripts shows no S5 path); the pre-registration commit comes before the first commit with a dev result (`git log --oneline` pasted); every run's table is pasted with its command; `git diff --name-only origin/main...HEAD` lists only the three files; `git diff origin/main -- src/ requirements*.txt src/backend/requirements*.txt` is empty; docs gates clean.
**Owner gates:** JUDGE-SWAP answered (above). New: **LAYA-CKPT-HOST** and **JUDGE-SWAP-ADOPT** (Owner gates items 16-17). This row makes no recommendation.
**Relation to B-3 and B-4.** Measurement only. B-3 (#264) stays a parked draft and is never agent-merged; no B-3 file is touched. B-3's frozen design (owner PARA-R3-Q2Q3, `owner-decisions-2026-09-27.md:118`: the generative judge's `FROZEN_PROMPT`, parser and `InferenceConfig`) and B-4's sign-off (PARA-R3-Q4Q5, `:125`) stand until the owner answers JUDGE-SWAP-ADOPT. If the owner adopts an encoder judge there, B-3 needs a design delta (a threshold becomes a frozen design value; contract I-15's `runner` argument; whether an encoder classifier may sit outside `ModelRunner`, CLAUDE.md §3, which the research left open), and B-4's freeze sha, MM-2 and sign-off restart on the new judge.

## JUDGE-NLI-TUNE — tune the bundled NLI cross-encoder's hypothesis and threshold as the advice judge (measurement; model host)

**Source:** owner JUDGE-SWAP, answered 2026-10-26 by free text (as in [JUDGE-LAYA-FT](#judge-laya-ft--fine-tune-laya-with-a-calibration-split-and-repeated-runs-measurement-model-host)); this row is option 3's measurement ("Plan a row that tunes the bundled NLI model's hypothesis and threshold on a new labelled split."). Planned 2026-10-26 on `0e8b2b2`.

**Facts (#373):** `cross-encoder/nli-deberta-v3-xsmall` @ `a15087641532` (283 MB, Apache-2.0) is already bundled (`scripts/download_models.py nli`, pinned revision and sha256; loaded with `local_files_only=True` in `modules/embeddings.py`). Zero-shot, with the one hypothesis "The text gives the patient a diagnosis, a medicine or dosing instruction, or emergency treatment advice." and an entailment threshold of 0.5 fixed in advance, it blocked 0 of 180 advice answers and 0 of 175 safe ones on `held_out_dev.json`, yet its scores ranked advice above safe text (AUROC 0.784). Latency p95 59 ms CPU, 61 ms GPU (one request).

**What the row measures (each step's command and raw output pasted):**
1. **Data, none of it S5.** S5 is never read. A new labelled tuning split of at least 150 must_block and 150 must_allow items, written by a separate agent session that has not seen `held_out_dev.json`, `held_out_final*.json` or S5, kept in the scratch directory, not committed, recorded by size, balance and sha256. If JUDGE-LAYA-FT has already written its calibration split, this row may reuse it when its sha256 matches the one recorded in that row's README; otherwise it writes its own. `held_out_dev.json` is the report split only.
2. **Pre-registration.** Before any score is seen the README fixes a list of at most 5 candidate hypotheses (the research's one included), the score (entailment probability, or entailment minus contradiction, named in advance), and the selection rule: on the tuning split, the hypothesis and the lowest threshold whose false-block rate is at most 5%, ties broken by recall. Committed before any dev result.
3. **Report.** For the selected pair, recall on must_block and false-block rate on must_allow on `held_out_dev.json` with Wilson 95% intervals, plus AUROC; the tuning-split table for every candidate. The model is deterministic, so one scoring pass suffices; the README also states how far the selected threshold sits from its neighbours (a threshold sweep on the tuning split).
4. **The 5% bound** is stated as in JUDGE-LAYA-FT step 4.
5. **Latency** p50/p95, CPU and GPU, one and two concurrent requests.

**Output and files:** `docs/research/<run date>-judge-nli-tune/00-README.md` (new), `docs/INDEX.md`, `docs/_link_graph.json`. Nothing under `src/`, no dependency (the model and `sentence-transformers` are already in the 3.11 venv). No slots. **Est:** 4 h.
**Runtime:** claude on the GPU box (model host); the same model-host rule as JUDGE-LAYA-FT (never beside JUDGE-LAYA-FT or another model-host run, no pytest beside it, `hold_slots.sh` locks 1–8).
**Acceptance:** as JUDGE-LAYA-FT (no S5 path; pre-registration before results; only the three files; no `src/` or requirements diff; docs gates clean).
**Owner gates:** JUDGE-SWAP answered; new **JUDGE-SWAP-ADOPT** (Owner gates item 16). No recommendation here.
**Relation to B-3 and B-4:** the same as JUDGE-LAYA-FT. The NLI model already loads outside `ModelRunner` (as the HC-M11 veto); whether a judge that blocks answers may do the same is part of the adoption question, not of this row.

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

## INTERP-SAFETY-ENFORCE — the template lab interpretation is saved and returned even when the prohibited-advice check fails

**Source:** bug diagnosis 2026-10-22 "Also found" (queue bullet INTERP-SAFETY-ENFORCE, added by #289); owner prompt 38 (2026-10-22, L0 AskUserQuestion; owner row INTERP-SAFETY-ENFORCE, `owner-decisions-2026-09-27.md:392`, merged in #291 `df9ca7f`): **"Plan an enforce fix"**: "Planner writes a row: on a failed prohibited check, the template path withholds/escalates like the chat path does. Touches interpretation code near ask-first safety logic; exact diff comes back to you." Planned 2026-10-22 on `d2843e8`.

**Superseded in part:** Facts 1-2, Design 1, the test list and Files below assume the pre-#304 order; [delta 2026-10-30](#delta-2026-10-30-after-304) replaces them.

**Facts (`d2843e8`):**
1. `InterpretModule.interpret_observation` (`src/backend/modules/interpret.py:139-290`) calls `self._safety_guard.validate_interpretation(...)` (`:209-213`), then adds disclaimers (`:228-231`), stores the safety JSON (`:237-242`), saves the `LabInterpretation` (`:278-279`) and returns `success=True` (`:286-290`) **whatever** `safety_result.passed` is.
2. `validate_interpretation` (`src/backend/modules/interpret_safety.py:101-150`, ask-first, read only) sets `passed=False` and appends `prohibited_<type>` to `checks_failed` on a prohibited-pattern hit (`:124-130`), and also sets `passed=False` with `missing_disclaimers` whenever fewer than 2 disclaimers are present (`:136-145`). Because the disclaimers are added only **after** the check (INTERP-DISC-ORDER, #289 row INTERP-SAFETY-META), `passed` is `False` on every template card today. So enforcement must key on a `prohibited_` entry in `checks_failed`, never on `passed`, or every card would be withheld.
3. The model path `interpret_with_model` (`:877-1044`) has the same shape (`:959` check, `:1042` `success=True`); no route calls it today (`grep -n interpret_with_model src/backend/api/*.py` is empty); B-5 (W-7) will.
4. The chat and grounded paths withhold a prohibited answer and serve `ESCALATE_TEMPLATE` as the answer content with a success status (`api/assistant.py:1004-1005`; `api/interpretations.py:597-601`, template at `:599` and `:601`, imported `:32` from `modules/agent/guardrails/templates.py`).
5. The routes turn `success=False` into HTTP 500 with `detail=interp_result.error_message` (`api/interpretations.py:433-437`, `:492-496`); the batch route records `error_message` per item (`:864-876`). `interpret_panel` calls `interpret_observation` per observation and silently skips one with no interpretation (`interpret.py:365-372`), so a withheld card would drop out of the panel summary without a notice. The lab page's grounded call has only an `onSuccess` handler (`src/frontend/src/pages/LabInterpreter.tsx:92-102`), so an error response shows the patient nothing. No template text is known to fail today (the template text is fixed).

**Design (`modules/interpret.py` only; `interpret_safety.py` is not edited):**
1. In `interpret_observation`, right after `validate_interpretation` (`:209-213`) and before any disclaimer, save or delete: if any entry of `safety_result.checks_failed` starts with `prohibited_`, log one WARNING with the violation types only (never the text), and return `InterpretationResult(success=False, error_message=ESCALATE_TEMPLATE, safety_validation=safety_result)`. Nothing is saved; under `force_regenerate` the existing interpretation is **not** deleted (the return comes before `:271-276`).
2. The same three lines in `interpret_with_model` after `:959`, so B-5 inherits the rule (in the diff the owner sees; the owner may answer "template path only").
3. Import `ESCALATE_TEMPLATE` from `modules.agent.guardrails.templates` (already imported the same way by `api/interpretations.py:32`).
4. **Not changed in this row:** the routes. So, unlike chat, a withheld card is **not** shown as an escalation: the route answers HTTP 500 with the escalation sentence in `detail`, the panel summary skips the card, and today's pages do not display that error. Serving the sentence as a visible card, as chat does, is a route edit in `api/interpretations.py` (ordered under contracts §b; #264 and #289's RUNNER-EXC-CHAIN also edit that file) and a frontend change; the owner chooses it in INTERP-ENFORCE-DIFF option "Merge, then show message", which becomes its own follow-up row. Also unchanged: stored cards from before the fix (the `existing_interp` early return at `:177-182` does not re-check them; none is known to fail); the disclaimer order (INTERP-SAFETY-META).

**Tests (test-first; new `src/backend/tests/test_interpret_safety_enforce.py`, HC-ISE-001…004; routes through `tests/support/routes.py::route_client`):**
- HC-ISE-001: `POST /observations/{id}/interpret` (`route_client(api.interpretations.router, "/interpretations")`; app path `/api/v1/interpretations/observations/{id}/interpret`) with `_generate_interpretation` patched to return a text holding a prohibited dosing phrase from `interpret_safety`'s own list → status 500, `detail == ESCALATE_TEMPLATE`, **no** `LabInterpretation` row for the observation, and the phrase appears in neither the response nor captured logs. RED on `main` (201, row saved).
- HC-ISE-002 (positive control): the real template text → 201 and one row saved, `safety_validation_json` still records `missing_disclaimers` (until INTERP-SAFETY-META lands). A scratch mutant that enforces on `not safety_result.passed` makes this test fail (pasted).
- HC-ISE-003: `force_regenerate=true` over an existing card with a failing new text → the old row is still there, unchanged.
- HC-ISE-004: `interpret_with_model` (called directly; no route exists) with a failing model text → `success=False`, `error_message == ESCALATE_TEMPLATE`, nothing saved.
- Re-run, not edited: `tests/test_interpret_safety_adversarial.py`, `tests/test_safe_interp_grounded.py`, `tests/test_interpret_history_units.py`, `tests/test_audit_order.py`, `tests/test_audit_order_guard.py`, `tests/test_prohibited_patterns_regression.py`.

**Files:** `src/backend/modules/interpret.py` (the two insertion points and one import only), `src/backend/tests/test_interpret_safety_enforce.py` (new), slots. **Expected collected delta:** +4. **Est:** 1 h. **Runtime:** claude (+ Opus review; safety-adjacent).
**Owner gates:** execution answered: INTERP-SAFETY-ENFORCE "Plan an enforce fix" (`owner-decisions-2026-09-27.md:392`, prompt 38; #291 merged `df9ca7f`); Task 0 quotes that row. **INTERP-ENFORCE-DIFF** (new, merge only; the owner asked that the exact diff comes back): asked with the draft PR's diff and the HC-ISE RED/GREEN output; no recommendation until the diff exists. Draft wording: "Here is the exact `modules/interpret.py` diff. If a lab-card explanation contains prohibited advice, the card is no longer saved or returned. Unlike chat, the patient does not see an escalation message yet: the request ends in an error the page does not show, and the card simply drops out of the panel summary. The disclaimer check is not part of the rule; `interpret_safety.py` is unchanged."

| Option (≤ 5 words) | Description |
|---|---|
| **Merge as shown** | Both paths (template and model) withhold; nothing shown yet. |
| **Template path only** | Drop the `interpret_with_model` hunk; B-5 handles the model path later. |
| **Merge, then show message** | Merge as shown, and plan a route + page row that shows the escalation sentence as chat does. |
| **Do not merge** | Keep today's behaviour (logged, not enforced). |

**Tradeoffs:** merging closes the gap that a future template edit could serve advice, but a withheld card fails quietly until a follow-up shows the message; template-only keeps the diff smallest and leaves the model path to B-5; the follow-up row touches a shared route file and the lab page; not merging leaves a check that records but never acts. **Analogy:** the smoke detector now cuts the power when it smells smoke; option 3 also makes it sound the alarm.
**Ask-first:** `modules/interpret_safety.py` is read only (CLAUDE.md §1); `interpret.py` is not on the §1 list but sits next to it, hence the diff gate.
**Order:** ready (build to draft; merge waits on INTERP-ENFORCE-DIFF). Never beside INTERP-SAFETY-META (#289 row; same function, `:209-245`) or B-5 (W-7, `interpret.py`); either order with INTERP-SAFETY-META, second lander merges `origin/main` and re-runs HC-ISE-002. Not beside another non-draft PR on `modules/interpret.py`.

### Delta 2026-10-30 (after #304)

INTERP-SAFETY-META merged as #304 (`64b92eb`, 2026-10-23). It moved `add_required_disclaimers` above `validate_interpretation` at both sites (owner answer INTERP-DISC-ORDER (a) "Check the final text", `owner-decisions-2026-09-27.md:390`). Facts 1-2, Design 1 and HC-ISE-002 above assumed the old order. This delta replaces them. Everything else above stands. Line numbers are on `origin/main` @ `144b5d4`. `interpret.py` changed after `64b92eb` (`b1162b6` RUNNER-EXC-INTERP, `9a92614`/`9072484` SAFETY-MODE-VERIFIED, `896aeba` SAFETY-MODE-STRICT, `6912931` INTERP-REGEN-500), so Task 0 re-reads the anchors. The item still matters: #304 changed only the order. Nothing on main acts on a failed prohibited check yet.

**Facts (re-derived on `144b5d4`):**

1. `InterpretModule.interpret_observation` (`src/backend/modules/interpret.py:139-291`) adds the disclaimers (`:208-212`), then calls `validate_interpretation` (`:214-219`). Next come the critical-value check (`:221-231`), the safety JSON (`:236-242`), the `force_regenerate` delete (`:272-277`) and the commit (`:279-280`). It returns `success=True` (`:287-291`) **whatever** `safety_result.passed` is. The model path `interpret_with_model` (`:878-1047`) has the same shape: disclaimers `:959-963`, check `:965-970`, delete `:1029-1033`, commit `:1036`, `success=True` `:1043-1047`. No route calls it yet (`grep -n interpret_with_model src/backend/api/*.py` is empty). The queue row's `:959`/`:965` is now `:960`/`:966`, one line lower.
2. `validate_interpretation` (`src/backend/modules/interpret_safety.py:101-158`; ask-first, read only, unchanged by #304) appends `prohibited_<type>` on a pattern hit (`:127`). It appends `missing_disclaimers` when fewer than 2 of the 3 disclaimer keyword groups are present (`:141-145`). `add_required_disclaimers` (`:247-291`) appends its sentence only when the interpretation text has **none** of the groups (`:262-274`). So on today's template text `passed` is `True`: HC-ISV-001 (`tests/test_interpret_safety_metadata.py:103-108`) pins this. `missing_disclaimers` can still occur when the text already has exactly one group (for example "ask your doctor") and no advice text. Probe 2026-10-30 (scratch, nothing committed): such a text gives `passed=False, ['missing_disclaimers']`, and a dosing text gives `passed=False, ['prohibited_dosing_recommendation']`. Keying on `prohibited_` therefore still matters. It is no longer what stops every card from being withheld. It is what keeps a disclaimer-only failure out of a rule the owner scoped to prohibited advice ("on a failed prohibited check", `owner-decisions-2026-09-27.md:392`).
3. **New: one existing test pins today's non-enforcement.** HC-ISV-003 (`tests/test_interpret_safety_metadata.py:129-140`, added by #304) posts a dosing text and asserts **201** and a stored row whose `checks_failed` holds a `prohibited_` entry. Its intent was "the reorder does not weaken the check". Probe 2026-10-30: Design 1 applied as a scratch patch (then reverted), against the 18 test files that reach `interpret_observation`/`interpret_with_model` or the guard. Command: `pytest -q tests/test_audit_order.py tests/test_audit_order_guard.py tests/test_biomarker_assistant.py tests/test_documents_api.py tests/test_embedding_fail_closed_paths.py tests/test_empty_answer.py tests/test_interpret_history_units.py tests/test_interpret_regenerate.py tests/test_interpret_safety_metadata.py tests/test_rag_timeout_answer.py tests/test_runner_exc_interp_logs.py tests/test_runner_exception_chain_logs.py tests/test_safe_interp_grounded.py tests/test_safety_mode_strict.py tests/test_safety_mode_verified.py tests/test_utc_sweep_http.py tests/test_interpret_safety_adversarial.py tests/test_prohibited_patterns_regression.py`. Output: `FAILED tests/test_interpret_safety_metadata.py::test_hc_isv_003_template_path_dosing_text_still_fails` / `1 failed, 305 passed`. HC-ISV-003 is the only failure. The row licenses it below.
4. The route facts moved. In the template route `generate_interpretation` (`api/interpretations.py:419-494`), `success=False` becomes HTTP 500 with `detail=interp_result.error_message` (`:481-485`). The SAFETY-MODE-VERIFIED refusal (`:460-462`) and the AUDIT-ORDER `started` audit (`:465-470`) come first. The `completed` audit (`:488-492`) is never reached on a 500. The grounded route `generate_grounded_interpretation` (`:501-688`) also calls `interpret_observation` first (`:539-543`) and returns 500 on failure (`:545-549`). So a withheld card fails the lab page's "Generate" call too, and that call has only an `onSuccess` handler (`src/frontend/src/pages/LabInterpreter.tsx:91-104`). The batch route records `error_message` per item (`:991-1003`). `interpret_panel` skips an observation that has no interpretation (`interpret.py:366-373`). Chat and grounded serve `ESCALATE_TEMPLATE` as content (`api/assistant.py:1252-1254`, `api/interpretations.py:653-656`; template `modules/agent/guardrails/templates.py:12`). The panel summary (`interpret.py:1049`) is fixed text built from analyte names, values and severities. It is never validated and is out of scope.

**Ordering question: disclaimer insertion vs validation vs enforcement.** Three orders are possible.

- **(a) Chosen.** Disclaimers, then the one existing `validate_interpretation` call, then the new prohibited check. Nothing is stored or deleted before the check.
- (b) Enforce on the raw text, before disclaimers, with a second `validate_interpretation` call.
- (c) Enforce after the critical-value check or after the save.

(a) is the conservative order, for four reasons:

1. It checks exactly the text that would be stored and served, which is the owner's INTERP-DISC-ORDER answer.
2. `add_required_disclaimers` only appends (`interpret_safety.py:274`, `:289`), so any prohibited match in the raw text is still a match in the final text. A match that spans the join (raw text ending "stop taking" + "\n\nThis information…") is caught only on the final text. So (a) is at least as strict as (b).
3. (b) adds a second guard call, which logs twice, and reopens the order #304 just settled.
4. (c) can delete the old card under `force_regenerate` (`:272-277`) or commit advice before refusing it.

The disclaimer sentences themselves match no prohibited pattern: HC-ISE-002 and HC-ISV-001 run them through the real guard.

**Design 1 (replaces Design 1 above).** In `interpret_observation`, put the check directly after the `validate_interpretation` call (`:215-219`, before `# Check for critical values` at `:221`). If any `safety_result.checks_failed` entry starts with `prohibited_`, do three things:

- log one WARNING naming the observation id and the violation types only, never the text;
- return `InterpretationResult(success=False, error_message=ESCALATE_TEMPLATE, safety_validation=safety_result)`;
- leave the database alone: no save, no delete, no commit.

Do not key on `passed` (Fact 2). Design 2 is unchanged: the same lines in `interpret_with_model` directly after `:966-970`, before `:972`. Design 3 is unchanged: one module-level import of `ESCALATE_TEMPLATE` from `modules.agent.guardrails.templates`. That module imports nothing else (`templates.py:8`), so there is no import cycle. Design 4 is unchanged: no route, frontend or `interpret_safety.py` edit. A withheld card writes no `completed` audit row; it is a 500, like any failed generation today. The route's `started` row (`:465-470`) already records an irreversible regenerate attempt.

**Tests (replace the list above; still test-first, new `src/backend/tests/test_interpret_safety_enforce.py`).** HC-ISE-001…003 go through HTTP: `route_client(interpretations_router, "/interpretations", profile_id=..., master_db=...)` with the `get_profile_db_session` override. Prior art is `_post_interpret` in `tests/test_interpret_safety_metadata.py:78-87`, which may be copied but not imported across test modules.

| Id | Assertion | On `main` |
|---|---|---|
| HC-ISE-001 | `_generate_interpretation` patched to a text holding a dosing phrase from `interpret_safety`'s own list (e.g. #304's `DOSING_TEXT`). Expect 500, `detail == ESCALATE_TEMPLATE`, **zero** `LabInterpretation` rows, and the drug name in neither the response nor `caplog.text`. Call `caplog.set_level(logging.DEBUG)` first, or the log assertion cannot fail (recurring-failures §1). | RED (201, row saved) |
| HC-ISE-002 (control) | `_generate_interpretation` patched to a cited text with exactly one disclaimer keyword group and no advice (e.g. "...[KB:ldl]. Ask your doctor what it means for you."). Expect 201, one row, stored `checks_failed == ["missing_disclaimers"]`. The test asserts that exact list, so it fails loudly if the text or the guard ever stops producing a disclaimer-only failure. **Mutant control:** a scratch patch that keys on `not safety_result.passed` makes this test fail (paste the output). Probe 2026-10-30 through `route_client`: prefix rule → `201 [['missing_disclaimers']]`; `not passed` mutant → `500 []`. | GREEN |
| HC-ISE-003 | Seed a card, then `POST ...?force_regenerate=true` with a failing new text. Expect 500, the old row still there with the same id, `interpretation_text` and `regeneration_count`. **Mutant control:** moving the check below `:272-277` makes it fail (paste). | RED (old row replaced) |
| HC-ISE-004 | `interpret_with_model` called directly (no route exists), with a stub selector like HC-ISV-002 (`tests/test_interpret_safety_metadata.py:111-126`) returning a cited dosing text. The citation keeps `_validate_llm_citations` (`interpret.py:773-777`) from falling back to the template. Expect `selector.run_inference.assert_awaited()`, `success is False`, `error_message == ESCALATE_TEMPLATE`, zero rows. | RED (success, row saved) |

**Licensed edit: HC-ISV-003 only (`tests/test_interpret_safety_metadata.py:129-140`).** Fact 3 shows the fix breaks it by design. The owner's "Plan an enforce fix" replaces the behaviour it pins, so this is a spec change. It is not a weakening (CLAUDE.md §3): the new assertions are stricter. Keep the name, the `DOSING_TEXT` constant and the HTTP call. Replace `status_code == 201` and the `_stored_safety` assertions with three: status 500, `detail == ESCALATE_TEMPLATE`, zero `LabInterpretation` rows. The check can withhold only on a `prohibited_` entry, so the test still fails if the reorder ever hides the dosing hit, which was its original intent. Edit it in the RED commit, with HC-ISE-001…004. No other line in that file changes. HC-ISV-001/002 must stay GREEN unedited.

**Re-run, not edited:** the 18 files of Fact 3 (this includes the old list: `test_interpret_safety_adversarial.py`, `test_safe_interp_grounded.py`, `test_interpret_history_units.py`, `test_audit_order.py`, `test_audit_order_guard.py`, `test_prohibited_patterns_regression.py`), then the full suite.

**Files (replaces Files above):**

- `src/backend/modules/interpret.py`: the two insertion points and one import only;
- `src/backend/tests/test_interpret_safety_enforce.py`: new;
- `src/backend/tests/test_interpret_safety_metadata.py`: HC-ISV-003 only;
- slots.

**Expected collected delta:** +4 (HC-ISV-003 is rewritten, not added). **Est:** 1.25 h. **Acceptance:** RED for HC-ISE-001, 003, 004 and the rewritten HC-ISV-003; HC-ISE-002 GREEN before and after; both mutant outputs pasted; 0 failed across the re-run set; `git diff origin/main --stat -- src/backend/modules/interpret_safety.py` empty; full suite. **Rollback:** revert the PR.

**Owner gate INTERP-ENFORCE-DIFF (merge only): unchanged.** The draft wording above stands, with two additions. After "the request ends in an error the page does not show", add: "(this includes the lab page's Generate button, whose call runs the same step first)". After "`interpret_safety.py` is unchanged", add: "One existing test (HC-ISV-003), which expected such a card to be saved, now expects it to be withheld." Options, tradeoffs and analogy are unchanged.

**Open question (answered 2026-10-30: "Withhold on any failure", owner-decisions row ISE-DISC-SCOPE; see [delta 2026-10-30b](#delta-2026-10-30b-ise-disc-scope-withhold-on-any-failure)).** ISE-DISC-SCOPE: "A lab-card explanation whose text names a doctor but has no other disclaimer word fails the disclaimer check. No current template does this. Under this fix, such a card is still saved and shown, because you scoped the rule to prohibited advice. Should a disclaimer-only failure also withhold the card?" Options: "Keep scope (plan default)" / "Withhold on any failure". Analogy: the smoke detector now cuts the power for smoke. Should it also cut the power for a missing label on the fuse box? The plan default keeps the owner's wording and does not widen it silently. "Withhold on any failure" is a one-line change to the condition, and HC-ISE-002 would then be inverted.

**Order:** ready. INTERP-SAFETY-META is done (#304), so the "either order" note above no longer applies. Never beside B-5 (W-7) or another non-draft PR on `modules/interpret.py` or `tests/test_interpret_safety_metadata.py`. Today no open PR touches either file (`gh pr list --state open --json number,files`, 2026-10-30).

### Delta 2026-10-30b (ISE-DISC-SCOPE: withhold on any failure)

**Owner answer.** ISE-DISC-SCOPE was answered on 2026-10-30 in the owner's chat reply to L0: "2. Yes." L0 reads this as **"Withhold on any failure"** (owner-decisions row ISE-DISC-SCOPE; L0 reading, not the owner's words). This delta replaces, in [delta 2026-10-30](#delta-2026-10-30-after-304), the condition in Design 1, HC-ISE-002 and its mutant control, the last two sentences of Fact 2, and the INTERP-ENFORCE-DIFF draft wording. Everything else in that delta stands: order (a), Designs 2-4, HC-ISE-001, 003 and 004, the HC-ISV-003 licence, and the re-run set. `interpret_safety.py` stays read only. Code anchors were re-checked on `143a969`. `interpret.py`, `api/interpretations.py`, `interpret_safety.py`, `recommend.py` and `scripts/seed_knowledge_base.py` are unchanged since `144b5d4`, so the line numbers of delta 2026-10-30 still hold.

**Design 1 condition (replaces "any entry starts with `prohibited_`").** The check is `if not safety_result.passed:`. It sits at the same place: directly after `validate_interpretation` (`interpret.py:215-219`, and `:966-970` for Design 2), before the critical-value check. The rest is unchanged: one WARNING naming the observation id and the `checks_failed` entries (types only, never the text), then `InterpretationResult(success=False, error_message=ESCALATE_TEMPLATE, safety_validation=safety_result)`, and no save, delete or commit. `passed` turns `False` in only two places: a prohibited-pattern hit (`interpret_safety.py:124-127`) and `missing_disclaimers` (`:141-145`). A missing citation only warns (`:148-155`). A critical value sets `requires_physician_review` (`interpret.py:221-231`), not `passed`. So under the new rule the only newly withheld failure type is `missing_disclaimers`.

**Tests (replace HC-ISE-002 and its mutant).**

| Id | Assertion | On `main` |
|---|---|---|
| HC-ISE-002 (now withheld) | Same patched text as before: cited, exactly one disclaimer keyword group, no advice (for example "...[KB:ldl]. Ask your doctor what it means for you."). Precondition, asserted in the test: the real guard on that text after `add_required_disclaimers` gives `checks_failed == ["missing_disclaimers"]`, so the test fails loudly if the text ever stops being a disclaimer-only failure. Expect what the prohibited case gets (HC-ISE-001): 500, `detail == ESCALATE_TEMPLATE`, **zero** `LabInterpretation` rows, and the text in neither the response nor `caplog.text` (after `caplog.set_level(logging.DEBUG)`). | RED (201, row saved) |
| Mutant control | A scratch patch that withholds only on a `prohibited_` entry (the rule from delta 2026-10-30) must make HC-ISE-002 fail. Paste the output. #414's probe through `route_client` already showed that rule giving `201 [['missing_disclaimers']]`. | — |

HC-ISE-001, 003 and 004 stay as written. They use dosing texts, which fail under either rule. Their mutant controls (HC-ISE-003: moving the check below `:272-277`) are unchanged. **Acceptance** gains: HC-ISE-002 RED on `main` and GREEN after; the `prohibited_`-only mutant output pasted.

**Newly withheld cases.** The INTERP-ENFORCE-DIFF draft must name every one of these. Re-check 2026-10-30 on `143a969`. Scratch probes only: nothing was committed and `git status` was clean after.

1. **The mechanism.** A card is newly withheld when its `checks_failed` is exactly `["missing_disclaimers"]`. That happens when the final interpretation text names exactly **one** of the three keyword groups (`interpret_safety.py:71-75`: "consult" / "healthcare provider|doctor|physician" / "educational|informational|general information") and there is no advice text. `add_required_disclaimers` appends its two-group sentence only when the text names **none** (`:262-274`). Any advice text ends with `RECOMMENDATION_DISCLAIMER` (`recommend.py:73-77`, all three groups), so a card with recommendations always passes this check.
2. **Shipped template cards.** The knowledge base is seeded from `scripts/seed_knowledge_base.py` at startup (`main.py:53-54`). For a result flagged high with no recommendations, the template text (`interpret.py:556-650`) names only "healthcare provider", so the card is withheld for: **Total Cholesterol** (`seed_knowledge_base.py:67`), **Fasting Glucose** (`:222`), **Hemoglobin** (`:300`) and **Creatinine** (`:458`). **LDL Cholesterol** (`:105`) is also withheld whenever the recommendation engine returns nothing for the value. The seed has an LDL-high intervention, but the engine classifies by value against the range (`recommend.py:115`), not by the flag. Probe: `_generate_interpretation` on each seeded row × flag H / L / none / other, with the seed's interventions, then the real guard.
3. **One existing test breaks.** The `not passed` rule was applied as a scratch patch at both sites and run over the 18-file re-run set of delta 2026-10-30. Result: `FAILED tests/test_biomarker_assistant.py::TestInterpretRouteAdviceWording::test_hc_iaw_004_high_ldl_interpretation_has_no_medication` / `FAILED tests/test_interpret_safety_metadata.py::test_hc_isv_003_template_path_dosing_text_still_fails` / `2 failed, 304 passed`. HC-IAW-004 (`test_biomarker_assistant.py:296`) posts a seeded LDL-high card with no interventions seeded, and it now gets 500. **This delta does not license editing HC-IAW-004.** That test's purpose (no medication wording on the shipped LDL card) is not replaced by the owner's answer. See ISE-SEED-HITS below.
4. **The model path** (`interpret_with_model`; no route calls it yet, B-5 will): any model text whose interpretation names exactly one group (for example only "talk to your doctor") and has no advice section. Today this is probably the most common shape of a model answer that fails.
5. **Where a withheld card shows up.** The cases are the same as for the prohibited rule, now including the above. The template route returns 500 (`api/interpretations.py:481-485`). The grounded route returns 500 because it calls `interpret_observation` first (`:539-549`). The lab page shows nothing for either, because it has only `onSuccess` handlers. The batch route records the escalation sentence as that item's error (`:991-1003`). The panel drops the card without any notice (`interpret.py:366-373`). Cards stored before the fix are still served without a re-check (`:177-182`). Regenerating one of them gives 500 and keeps the old card (HC-ISE-003).
6. **Not withheld:** missing citations (warning only), critical values, and the panel summary (never validated).

**Found on the way, already inside the prohibited scope (it contradicts "No template text is known to fail today", Fact 5 above).** The same probe shows that the shipped seed text trips prohibited patterns. Under either rule, these cards are withheld once the fix merges:

- `certain(ly)?` (`interpret_safety.py:63`, certainty_claims) matches the ordinary phrase "certain conditions/medications/foods". Affected: **Total Cholesterol low** (`seed_knowledge_base.py:68`), **Fasting Glucose low** (`:223`), **WBC low** (`:341`), **Platelets low** (`:379`), and the **Vitamin D** description (`:495`). The description is appended to every card (`interpret.py:636-637`), so Vitamin D is withheld at **every** status.
- `you have\s+\w+` (`:51`, diagnostic_language) matches the **Platelets** description ("when you have a cut", `:375`), so Platelets is withheld at **every** status.

Over 12 seeded analytes × 4 flag states, 15 combinations fail: 4 are disclaimer-only (5 counting LDL-high without recommendations) and 11 are prohibited. No current test covers the prohibited 11, which is why #414's probe saw only HC-ISV-003.

**Drafted owner question ISE-SEED-HITS (execution gate; answered 2026-10-30 "Reword built-in text first (Recommended)", see Task 1 below).** The ISE-DISC-SCOPE question told the owner "No current template does this", and the INTERP-SAFETY-ENFORCE prompt said "no failure is known today". Both premises are false for the shipped text. The answers stand as recorded, but the owner decides before patient-visible cards disappear. Draft: "When you chose 'withhold on any failure', we said no built-in explanation fails the checks. A re-check found that several do. Once the fix is in, these lab cards would no longer appear for new or regenerated results: Platelets and Vitamin D at every result (the safety check misreads 'certain foods' and 'when you have a cut' as medical claims); Total Cholesterol, Fasting Glucose and WBC when low (the same word 'certain'); Total Cholesterol, Fasting Glucose, Hemoglobin and Creatinine when high (they name a doctor only once, so the disclaimer check fails), and LDL when high without suggestions. Cards already saved keep showing. One existing test fails as a result. What now?"

| Option (≤ 5 words) | Description |
|---|---|
| **Reword built-in text first (Recommended)** | A small row rewords those seed sentences in `scripts/seed_knowledge_base.py` (not ask-first; existing installs are updated through its `_TEXT_REVISIONS` list, `:835-841`) so every built-in card passes both checks. The enforce fix merges after it, HC-IAW-004 stays green and unedited, and no card disappears. |
| **Withhold them anyway** | Build as planned; those cards stop appearing. HC-IAW-004 would need a licensed rewrite. |
| **Back to prohibited only** | Reverse ISE-DISC-SCOPE: the four or five high cards stay, but Platelets, Vitamin D and the three low cards are still withheld. |
| **Pause the enforce fix** | Keep today's behaviour (logged, not enforced) for now. |

**Tradeoffs:** rewording first is one more small row (seed text and its revision entries, plus a test that runs every seeded row through the guard), but no patient loses a card and the check is not weakened. Withholding anyway hides correct, harmless explanations. Prohibited-only does not fix the main loss. Pausing leaves advice unenforced. **Analogy:** the new smoke detector cuts the power, but the kitchen's own toaster sets it off. Clean the toaster first, or live without toast. The planner recommends the reword because it is the conservative option: it loses no safety check and no correct card. `interpret_safety.py`'s false matches on "certain" and "you have a" are an ask-first edit, so they are not proposed here.

**INTERP-ENFORCE-DIFF draft wording (replaces the 2026-10-30 additions).** "Here is the exact `modules/interpret.py` diff. If a lab-card explanation fails **any** safety check (prohibited advice, or fewer than two of the required disclaimer phrases), the card is no longer saved or returned. Unlike chat, the patient does not see an escalation message yet: the request ends in an error the page does not show (this includes the lab page's Generate button, whose call runs the same step first), and the card simply drops out of the panel summary. Cards saved before the fix still show. `interpret_safety.py` is unchanged. One existing test (HC-ISV-003), which expected such a card to be saved, now expects it to be withheld." The draft then lists, as measured on the PR's own base, every seeded analyte and status from the list above that is still withheld. If ISE-SEED-HITS is answered "Reword built-in text first", that list must be empty, and a test must show it is. Options, tradeoffs and analogy are unchanged.

**ISE-SEED-HITS answered 2026-10-30** (L0 AskUserQuestion; owner-decisions row ISE-SEED-HITS): **"Reword built-in text first (Recommended)"**. Before the owner was asked, L0 corrected the premise ("No current template does this") that it had relayed with ISE-DISC-SCOPE. The reword is **Task 1 of this row**, not a separate row. It lands in the same PR, before the enforce change.

**Task 1: reword the seed text (before Tasks 2+, the enforce change).** Only `src/backend/scripts/seed_knowledge_base.py` changes. It is not on the CLAUDE.md §1 list. `interpret_safety.py` stays read only, and its patterns are **not** changed, so the reworded text has to pass the unchanged guard.

- **12 field edits in `BIOMARKER_DATA`**, all wording only:
  - **Prohibited hits:** "certain" becomes "some" in Total Cholesterol low ("some health conditions"), Fasting Glucose low, WBC low, Platelets low and the Vitamin D description. In the Platelets description, "when you have a cut or injury" becomes "after a cut or injury".
  - **One-group disclaimers:** Total Cholesterol high and low, LDL high, Fasting Glucose high, Hemoglobin high and Creatinine high each change "Your healthcare provider can/will/may …" to "Consult your healthcare provider, who can/will/may …".
  - **Owner addition 2026-10-31 (ISE-HGB-LOW-REWORD):** Hemoglobin low "indicates anemia" becomes "can be a sign of anemia". It is not a guard failure today, but it is a diagnostic-sounding statement.
  - **Every reworded card ends up with a full disclaimer.** A "Consult" sentence names two groups. The other cards name none, so `add_required_disclaimers` appends its two-group sentence.
  - **The text stays educational:** no diagnosis, dosing or new advice is added. The LDL text keeps no "medication", so HC-IAW-001 and HC-IAW-004 stay green. The implementer may improve wording, but each final text must pass HC-ISE-005 below.
  - **Probe 2026-10-30** (scratch, this wording): over every seeded analyte × flag (H / L / none / other), with and without the seed's recommendations, 52 cases. Original text: `17 failing`. Reworded: `0 failing`. No new text matches any prohibited pattern.
- **One `_TEXT_REVISIONS` entry per edited field** (`seed_knowledge_base.py:802-819`). Each entry is `(analyte, field, old_exact_text, new_text)`, and `old_text` is the text on `143a969`.
  - LDL high and Fasting Glucose high already have an entry, from INTERP-ADVICE-WORDING. Their new entries go **after** the existing ones, and the existing tuples are not edited. The loop (`:836-842`) re-reads the field on every iteration, so an install that still has the pre-IAW text is revised twice in one pass and ends on the new text. HC-IAW-002 relies on this and must stay green.
  - The `description` field works the same way, because `setattr` is generic.
- **How existing installs pick it up.** The knowledge base is a **master-DB** table (`models/knowledge_base.py:20`, `core.database.Base`), not a per-profile one. So there is one copy per install, and no per-profile migration is needed.
  - At every startup, the app lifespan calls `seed_all(skip_db_init=True)` (`main.py:51-54`). That calls `seed_biomarker_knowledge`, which loops over `_TEXT_REVISIONS` for each row that already exists (`:835-843`). It rewrites a field only when the stored text **exactly** equals `old_text`, then commits (`:854`). A row someone edited is left alone (HC-IAW-003).
  - Seeding runs in the lifespan, before requests. The knowledge loader's cache is per process, so a restart serves the new text.
  - Lab cards already saved in a profile DB keep their old text. They are served without a re-check (`interpret.py:177-182`). Regenerating one builds it from the revised text.
  - **Residual case for INTERP-ENFORCE-DIFF:** an install whose knowledge-base row was edited by hand keeps its text. If that text fails the guard, it is withheld once Task 2 lands.
- **Tests (new, in `test_interpret_safety_enforce.py`, RED on `main`):**
  - **HC-ISE-005.** Seed a real master DB with `seed_all(skip_db_init=True)`, as HC-IAW-002 does (copy the `real_master_session` fixture from `test_biomarker_assistant.py:199`; do not import it). For every `BIOMARKER_DATA` analyte × flag H / L / none / other, add an in-memory profile observation. Call the real `InterpretModule.interpret_observation`, which runs `_assemble_context`, `_generate_interpretation`, `add_required_disclaimers` and `validate_interpretation`. Assert `safety_validation.passed` for each case, and fail with a list of every failing (analyte, flag, `checks_failed`). Run once with the seeded interventions and once with the `InterventionMapping` rows deleted; disclaimer-only failures arise only without recommendations. Assert the case count, 48 per pass, so a shrinking loop cannot pass. RED on `main` (15 failing without recommendations).
    - **Mutant controls**, paste both outputs: (1) restore the original Vitamin D description (the "certain foods" text) as a scratch edit, and HC-ISE-005 must fail with `prohibited_certainty_claims`; (2) restore the original Hemoglobin high text, and it must fail with `missing_disclaimers`.
  - **HC-ISE-006.** For each new `_TEXT_REVISIONS` entry, insert a row holding the old exact text, hard-coded in the test as the `test_biomarker_assistant.py:184` comment requires, then run `seed_all`. The stored field must equal the current `BIOMARKER_DATA` text. Include the pre-IAW LDL and glucose texts (`_OLD_LDL_HIGH`, `_OLD_GLUCOSE_HIGH` shapes) so the chain is covered. RED on `main`.
  - Re-run unedited: `test_biomarker_assistant.py`, which includes HC-IAW-001…004. HC-IAW-004 must be green after Task 1 **and** after Task 2.
- **Commit order:** the Task 1 RED commit, then the reword. Then the enforce RED commit, with HC-ISE-001…004 and HC-ISV-003, then the enforce change. HC-ISE-005 stays green across the enforce change. With Task 1 in, the scratch `not passed` probe of Fact 3 should fail **only** HC-ISV-003, the licensed one. Task 0 re-runs that probe after Task 1 and pastes it.

**INTERP-ENFORCE-DIFF draft, still-withheld seed cards (now required to be empty).** The draft's list of seeded analytes and statuses still withheld, as measured on the PR's own base, must be **empty**. HC-ISE-005's green output is the evidence and is pasted with the diff. The draft adds one sentence: "The app's built-in explanation text was reworded first, so that none of its own cards is withheld. Lab cards you already have keep their old text until you regenerate them, and an explanation row someone edited by hand is not changed." The rest of the draft wording above stands.

**Files (replaces the Files list of delta 2026-10-30):**

- `src/backend/scripts/seed_knowledge_base.py`: Task 1, the 12 `BIOMARKER_DATA` fields and their `_TEXT_REVISIONS` entries only;
- `src/backend/modules/interpret.py`: the two insertion points and one import only;
- `src/backend/tests/test_interpret_safety_enforce.py`: new, HC-ISE-001…006;
- `src/backend/tests/test_interpret_safety_metadata.py`: HC-ISV-003 only;
- slots.

**Expected collected delta:** +6. **Est:** 2.5 h.

**Order (replaces the paragraph below).** **Ready.** Task 1 (the reword) comes first, then the enforce change, in one PR. The merge still waits on INTERP-ENFORCE-DIFF. The "never beside" rules are unchanged. Add one: never beside another PR on `scripts/seed_knowledge_base.py` or `tests/test_biomarker_assistant.py`.

**Order before the ISE-SEED-HITS answer (superseded by the paragraph above).** Blocked on ISE-SEED-HITS. With "Reword built-in text first", the reword row lands first and this row then builds as above. With "Withhold them anyway", HC-IAW-004's rewrite is licensed by that answer, and the row builds. With "Back to prohibited only", delta 2026-10-30 applies again, and the 11 prohibited combinations still go in the merge-gate list. With "Pause", the row is parked. The other "never beside" rules are unchanged.

### Delta 2026-10-31 (INTERP-WITHHOLD-MSG: show the withheld message)

**Owner answer.** INTERP-ENFORCE-DIFF was answered on 2026-10-31 (L0 AskUserQuestion; owner-decisions row INTERP-ENFORCE-DIFF): **"Merge, then show message (Recommended)"**. L0 marks #423 ready and merges it as shown. This delta plans the follow-up the option names: "plan a route + page row that shows the escalation sentence as chat does". It is a new queue row, **INTERP-WITHHOLD-MSG**, not a change to #423. Planned 2026-10-31 on `origin/main` @ `1a85ad67`, with `modules/interpret.py` read on #423's head `15476c76` (the row builds only after #423 merges, so Task 0 re-reads every anchor on the merged main).

**Facts (`1a85ad67`; `interpret.py` on `15476c76`):**

1. **The withhold result.** At both withhold sites (`interpret.py:225-235` in `interpret_observation`, `:990-1000` in `interpret_with_model`) the module returns `InterpretationResult(success=False, error_message=ESCALATE_TEMPLATE, safety_validation=safety_result)`. The dataclass (`:84-89`) has no field that tells a withhold apart from any other failure; only the `error_message` string does.
2. **Plain route** `POST /interpretations/observations/{id}/interpret` (`api/interpretations.py:419-493`): any `success=False` becomes HTTP 500 with `detail=error_message` (`:481-485`), so a withheld card is a 500 whose `detail` is the escalation sentence (HC-ISE-001…003 pin this). No audit row is written on that path. Under `force_regenerate` over an existing card, the `started` intent row is written first (`:465-470`) and nothing closes it, so the audit trail shows an irreversible change that started and never completed, although the old card is kept (HC-ISE-003).
3. **Grounded route** `POST …/interpret-grounded` (`:496-689`): same mapping (`:545-549`, 500 with the sentence in `detail`); the `started` row (`:531-537`) is likewise left open on a withheld regenerate. Its existing withhold patterns are the model: on `rag_result.prohibited_advice` it answers 201 with one `uncertainty` segment holding `ESCALATE_TEMPLATE`, `full_response = ESCALATE_TEMPLATE`, an empty verification, and one `interpretation.prohibited_blocked` audit row with `details={"reason": "prohibited_pattern", "decision": "escalate"}` (`:652-662`). `GroundedInterpretationResponse.interpretation` is required (`:245-247`), so the route cannot answer 201 without a card today.
4. **Batch route** (`:902-1025`): a withheld id lands in `failed` with the escalation sentence as its `error` (`:998-1003`), and the closing `batch_generate` row counts it in `skipped_count` (`:1016-1024`). Nothing is silent there. No change.
5. **The lab page uses only the grounded route.** `pages/LabInterpreter.tsx:88` takes `useGenerateGroundedInterpretation`; both the "Generate Interpretation" button (`:271-282`) and the card's Regenerate (`:254`) call `handleGenerateInterpretation` (`:91-105`), which has an `onSuccess` and no `onError`. A 500 therefore shows nothing: the "No interpretation yet" card (`:257-285`) simply stays. The hook (`services/interpretations.ts:120-136`) writes `data.interpretation` into the query cache on success. `useGenerateInterpretation` (plain route, `:102-118`) has no caller in `src/`. Types: `services/types.ts:345-354`.
6. **Audit allowlist.** `core/audit.py::_scrub_details` keeps only allowlisted keys. There is no key for check names: `checks_failed` would be dropped. Every `checks_failed` entry is enum-shaped (`prohibited_<type>`, `missing_disclaimers`) and passes `_ENUM_VALUE_RE` (`:113`). `ID_LIST_DETAIL_KEYS` (`:80-83`) is the list-of-enums home. `core/audit.py` is not on the CLAUDE.md §1 ask-first list; it is a contracts §b shared file (`contracts.md:81`).
7. **Critical value.** At both sites the withhold return sits above the `check_critical_value` block (`:237-246`, `:1002-1011`), so a withheld card computes no physician-review flag (#423 body, "Critical value"). `check_critical_value` (`interpret_safety.py:160-205`, ask-first, read only) is a pure function: it reads thresholds and returns a `SafetyValidationResult`; it writes nothing. Its `physician_review_reason` string contains the value.

**Found on the way (out of scope, not fixed here):** the page's Regenerate never regenerates. `handleGenerateInterpretation` sends no `forceRegenerate`, so the route returns the stored card from the `existing_interp` shortcut (`interpret.py:172-183`). A withhold is therefore reachable on the page only on a first generate. Other 500s on the page (for example 501 / 503 from `rag.query`) are also silent; this row shows the withhold only. The panel summary still drops a withheld card without notice (`interpret.py:387-398` on `15476c76`). Candidate queue bullets for L0.

**L0 note 2026-10-31: Tasks 1-2 are done (#428, merged as `e4246290`). OQ-IWM-CRIT was asked and answered 2026-10-31: "Keep the flag (Recommended)" (owner-decisions row OQ-IWM-CRIT, `owner-decisions-2026-09-27.md:450`), so Task 3 is ready (HC-IWM-007, HC-IWM-FE-004). The Design and question text below are the planner's original, kept for the record.**

**L0 note 2026-10-31 (later): Task 3 (draft #433) stopped because `check_critical_value` logs the value (`interpret_safety.py:194-196`, `:204-206`). Owner row CRIT-LOG-SCRUB answered "Scrub the log line first (Recommended)": Task 3 now waits on row CRIT-LOG-SCRUB ([delta 2026-10-31b](#delta-2026-10-31b-crit-log-scrub-scrub-the-critical-value-log-lines)) merging, then resumes unchanged.**

**Design (Tasks 1-2 ready; Task 3 waits on OQ-IWM-CRIT):**

- **Task 1, backend: withheld response + audit.**
  1. `modules/interpret.py`: add `withheld: bool = False` to `InterpretationResult` (`:84-89`) and pass `withheld=True` in the two withhold returns. Nothing else in that file changes in Task 1. The route keys on this flag, never on the `error_message` string.
  2. `core/audit.py`: add `"checks_failed"` to `ID_LIST_DETAIL_KEYS` (one token). Values still pass the enum regex and the 50-entry cap, so prose cannot pass.
  3. `api/interpretations.py`, both single-observation routes, on `interp_result.withheld` (before the existing `success=False` raise): write one audit row, event `withheld` (so `interpretation.withheld`), `entity_type="observation"`, `entity_id=observation_id`, `details={"reason": "safety_check_failed", "decision": "escalate", "checks_failed": list(interp_result.safety_validation.checks_failed)}`, and `intent="completed" if started else None`, which closes the open `started` row of a regenerate. Ids and check type names only, never the text, the analyte or the value.
  4. **Grounded route** (the one the page calls): after the audit row, return **201** `GroundedInterpretationResponse(interpretation=None, withheld=True, grounded_segments=[uncertainty segment with ESCALATE_TEMPLATE], full_response=ESCALATE_TEMPLATE, verification=GroundedVerificationResponse(), is_valid=False)`, the same shape as the SAFE-INTERP-GROUNDED branch (`:652-656`). `rag.query` is **not** called for a withheld card. Schema: `interpretation: Optional[InterpretationResponse] = None`, new `withheld: bool = False`.
  5. **Plain route:** status and body are unchanged (500, `detail == ESCALATE_TEMPLATE`), so HC-ISE-001…003 stay green and unedited. It has no frontend caller, and its `detail` already carries the sentence. Only the audit row is added. Planner choice, conservative: a status change here would rewrite #423's tests for no visible gain; if L0 or the owner wants a non-500 status, that is a new row.
  6. Every other `success=False` keeps today's mapping (500).
- **Task 2, frontend: show the message.**
  1. `services/types.ts`: `GroundedInterpretationResponse.interpretation: InterpretationResponse | null`, `withheld?: boolean`.
  2. `services/interpretations.ts` hook (`:131-134`): write the cache only when `data.interpretation` is not null (a withheld answer must not overwrite a stored card with null).
  3. `pages/LabInterpreter.tsx`: in `handleGenerateInterpretation`'s `onSuccess`, if `data.withheld`, store a notice `{ observationId, message: data.full_response }`, clear `groundedSummary` and `groundedValidation`, and render one card (`role="status"`) for the selected observation only, in place of the "Grounded explanation" card: a fixed lead line, planner draft "Asclexis could not produce a safe explanation for this result.", then `message` as plain text (React text node, no markup; HC-LAB-001b's rule). No faithfulness badge. The notice is hidden when another observation is selected. No new component file.
- **Task 3, gated on OQ-IWM-CRIT (do not build until answered).** With "Keep the flag (Recommended)": at both sites, move the existing `check_critical_value` block above the withhold return (a pure reorder of a pure computation; no write moves, and #423's "nothing saved before the return" stays true). The grounded withheld response gains `withheld_physician_review: bool = False`, set from `safety_validation.requires_physician_review`; the reason string (it holds the value) is not sent and not audited. The page notice adds one fixed line when it is true, planner draft "This value is outside the range where a clinician should review it promptly. Please contact your clinician." With "Skip it (as merged)", Task 3 is dropped.

**Open question OQ-IWM-CRIT (drafted; asked and answered 2026-10-31, "Keep the flag (Recommended)").** "When a lab-card explanation is withheld, should Asclexis still check whether the value is critical, and tell the patient a clinician should review it? Today a withheld card skips that check, so a critical value shows only the 'not shown' message."

| Option (≤ 5 words) | Description |
|---|---|
| **Keep the flag (Recommended)** | The critical-value check runs before the withhold, as a pure reorder at both sites in `interpret.py`; the withheld message adds a fixed "please contact your clinician" line. `interpret_safety.py` stays unedited. |
| **Skip it (as merged)** | Keep #423's order; a withheld card shows only the escalation sentence. |

**Tradeoffs:** keeping the flag never shows advice text (the line is fixed, and it already appears on saved cards via `requires_physician_review`), so it loses no safety check and restores a safety signal the withhold removed; it moves 10 lines in a file the owner saw as a diff, which is why it is asked. Skipping keeps the merged diff untouched, but a critical result whose explanation fails a wording check then shows less urgency than a normal one. **Planner recommendation:** keep the flag; it is the conservative choice for a patient with a critical value. **Analogy:** the smoke detector cut the power; the follow-up sounds the alarm, and this question is whether it should still also say "the oven is very hot".

**Tests (test-first; new `src/backend/tests/test_interpret_withhold_msg.py`, HC-IWM-001…008; every route test goes through `tests/support/routes.py::route_client` with a real master session, copying the `dbs` / `_call` / `_audit_rows` pattern of `test_safe_interp_grounded.py:52-125`, not importing it):**

| Id | Assertion | On `main` after #423 |
|---|---|---|
| HC-IWM-001 | Grounded route, `_generate_interpretation` patched to a dosing text: **201**, `withheld is True`, `interpretation is None`, `full_response == ESCALATE_TEMPLATE`, exactly one `uncertainty` segment; `rag.query` (patched module) not awaited; zero `LabInterpretation` rows; the patched text in neither the response nor `caplog.text`. | RED (500) |
| HC-IWM-002 | Grounded route, the disclaimer-only text of HC-ISE-002 (same precondition asserted): same as 001. | RED |
| HC-IWM-003 | Plain route, dosing text: status **500** and `detail == ESCALATE_TEMPLATE` (pin, unchanged), and exactly one audit row, `event_type == "interpretation.withheld"`, details `reason`, `decision` and `checks_failed` equal to the guard's own list (`prohibited_…` names). The patched text, the analyte and the value appear in no audit row (`_row_blob` over every row). | RED (no row) |
| HC-IWM-004 | Plain route, `force_regenerate=true` over a stored card, failing text: rows are `[interpretation.generate status=started, interpretation.withheld status=completed]`; the old card is unchanged. | RED (started only) |
| HC-IWM-005 | Grounded route, same as 004: `[interpretation.grounded started, interpretation.withheld completed]`, and the response is 201 withheld. | RED |
| HC-IWM-006 | `_scrub_details({"checks_failed": ["prohibited_dosing_recommendation", "missing_disclaimers"]})` keeps the list; `{"checks_failed": ["take 500 mg daily"]}` is dropped (`_scrubbed == 1`). | RED (key dropped) |
| HC-IWM-007 | **Task 3 only.** Observation above its critical threshold plus a failing text, grounded route: 201 withheld and `withheld_physician_review is True`; below the threshold it is `False`; the reason string is in neither the response nor any audit row. | RED |
| HC-IWM-008 | Positive control: `interpret_observation` patched to `InterpretationResult(success=False, error_message="boom")` (no `withheld`): grounded route still 500, no `interpretation.withheld` row. | green (pin) |

**Mutant controls** (scratch, paste output): (m1) the grounded branch keys on `error_message == ESCALATE_TEMPLATE` and the 008 patch uses that string → 008 fails; (m2) the audit row drops `intent` → 004 and 005 fail; (m3) the grounded branch still calls `rag.query` → 001 fails; (m4) `details` carries `interpretation_text` → 003 fails.

**Frontend (vitest, extend `src/frontend/src/__tests__/LabInterpreter.test.tsx`, its existing `@/services/api` mock):**

- HC-IWM-FE-001: `apiPost` for `interpret-grounded` resolves with `withheld: true, interpretation: null, full_response: <ESCALATE text>` → after clicking "Generate Interpretation", a `role="status"` region shows the lead line and the escalation sentence; no "Grounded faithfulness" badge, no "Grounded explanation" heading. RED on main.
- HC-IWM-FE-002: selecting another observation hides the notice. RED.
- HC-IWM-FE-003: a normal (non-withheld) answer still renders the grounded card (HC-LAB-001 unchanged and green); the hook does not write `null` to the cache (the stored card query keeps its data). RED for the cache half.
- HC-IWM-FE-004: **Task 3 only**, `withheld_physician_review: true` shows the clinician line.

**Re-run, not edited:** `test_interpret_safety_enforce.py` (HC-ISE-001…006), `test_safe_interp_grounded.py`, `test_interpret_regenerate.py`, `test_audit_order.py`, `test_audit_order_guard.py`, `test_rag_timeout_answer.py`, `test_safety_mode_strict.py`, `test_safety_mode_verified.py`, `test_interpret_safety_metadata.py`; frontend `InterpretedResultCard.test.tsx`, `a11y-crit-labels.test.tsx`, then `npx tsc --noEmit` and the full `npx vitest run`.

**Files:**

- `src/backend/modules/interpret.py`: the `withheld` field and the two `withheld=True` arguments (Task 1); the critical-value reorder at both sites (Task 3 only);
- `src/backend/api/interpretations.py`: the withhold branch in the plain and grounded routes, `GroundedInterpretationResponse` (`interpretation` optional, `withheld`; `withheld_physician_review` in Task 3);
- `src/backend/core/audit.py`: `"checks_failed"` in `ID_LIST_DETAIL_KEYS` only;
- `src/backend/tests/test_interpret_withhold_msg.py`: new, HC-IWM-001…008;
- `src/frontend/src/services/types.ts` (`GroundedInterpretationResponse` only), `src/frontend/src/services/interpretations.ts` (the grounded hook's `onSuccess` only), `src/frontend/src/pages/LabInterpreter.tsx`, `src/frontend/src/__tests__/LabInterpreter.test.tsx` (new describe HC-IWM-FE);
- slots.

`interpret_safety.py` is read only (`check_critical_value` and `validate_interpretation` are called, never edited). No `redaction.py`, `faithfulness.py`, `verifier_agent.py` or auth file is touched. **Expected collected delta:** +7 backend (+8 with Task 3). **Est:** 3 h (backend 1.5, frontend 1, review 0.5); +0.5 h for Task 3.

**Order.** **Ready** for Tasks 1-2 once #423 (INTERP-SAFETY-ENFORCE) is merged (Task 0 check 2: its PR title ends `(INTERP-SAFETY-ENFORCE)`). Task 3 waits on OQ-IWM-CRIT. **Never beside:**

- `modules/interpret.py`: B-5 (W-7) or any other non-draft PR on that file; never before #423 merges.
- `api/interpretations.py`: the lane B file queue (contracts §b `:64`, R-3): one non-draft at a time, so never beside B-3 (#264) once it leaves draft, and before B-5; `test_safe_interp_grounded.py` is re-run here, not edited.
- `core/audit.py`: contracts §b `:81`; never beside another non-draft PR on that file (second lander re-anchors without changing content).
- `pages/LabInterpreter.tsx`, `__tests__/LabInterpreter.test.tsx`, `services/interpretations.ts`, `services/types.ts`: never beside another non-draft PR on any of them.

**Runtime:** claude (+ Opus review, security reviewer included: audit details and a safety-message path).

### Delta 2026-10-31b (CRIT-LOG-SCRUB: scrub the critical-value log lines)

**Owner answer.** Owner row CRIT-LOG-SCRUB was answered on 2026-10-31 (L0 AskUserQuestion): **"Scrub the log line first (Recommended)"**. Option text: "A small ask-first row: change those 2 log lines to analyte + direction only ('Critical value detected: potassium above critical threshold'), with no value and no threshold, plus a caplog test. The exact diff comes back to you before merge. Task 3 then resumes unchanged." Planned 2026-10-31 on `origin/main` @ `5b18f7bc` by the Opus planner.

**Facts (`5b18f7bc`):**

1. `InterpretationSafetyGuard.check_critical_value` (`src/backend/modules/interpret_safety.py:160-210`) logs the patient's value and the threshold at WARNING: `:194-196` `logger.warning(f"Critical value detected: {analyte_canonical}={value} < {c_low}")` and `:204-206`, the `>` twin with `c_high`. Both callers (`modules/interpret.py:241`, `:1007`) run it for every card with a value, so this happens today for every critical non-withheld card. INTERP-WITHHOLD-MSG Task 3 (draft #433) would also run it for withheld cards, and its brief forbids the value in any log line, so Task 3 stopped.
2. `physician_review_reason` (`interpret_safety.py:190-192`, `:200-202`, "Critical low value: {value} is below critical threshold of {c_low}") is **returned, not logged**. Grep over `src/backend` (tests excluded): it is copied into `safety_result` (`interpret.py:249`, `:1015`), stored on the per-profile `LabInterpretation` row (`interpret.py:285`, `:1057`; `models/interpretation.py:96`; profile migration `001_initial_schema.py:157`) and returned by `GET` interpretation responses (`api/interpretations.py:198`, `:234`). No `logger` call, no audit `details` and no export module names it; `_audit_withheld` (`api/interpretations.py:94-117`) writes ids and check names only. It is the patient's own data in their encrypted profile DB, so it is **not** in scope here.
3. No test pins the old log text: `grep -rn "Critical value detected" src/backend/tests` is empty, and the `caplog` assertions in `test_interpret_safety_enforce.py:386-464` check advice text only.

**Findings (not scope, no change):** no other log line in `interpret_safety.py` or `interpret.py` carries a value. `interpret_safety.py:128` logs the violation type name, `:146` and `:156` are constant strings. `interpret.py:228` and `:994` log the observation id and check names; `:300` the observation id, severity and the review flag; `:466` the panel name, status and abnormal count; `:792` a constant; `:803` the exception type name; `:929`, `:937` and `:1071` the observation id, tier and severity. None carries `value`, a threshold or `physician_review_reason`.

**Design (one task; ask-first, signed by CRIT-LOG-SCRUB):**

- `interpret_safety.py:194-196` becomes `logger.warning("Critical value detected: %s below critical threshold", analyte_canonical)`, and `:204-206` becomes the same call with `above`. Nothing else in the file changes: not `physician_review_reason`, not `warnings`, not the thresholds, not a prohibited pattern or any check. Lazy `%s` formatting, so the record carries only the analyte as an argument.
- No change to `interpret.py`, the routes or the audit. INTERP-WITHHOLD-MSG Task 3 then resumes unchanged.

**Tests (test-first; new `src/backend/tests/test_interpret_safety_log_scrub.py`, HC-CLS-001…003; `caplog.set_level(logging.DEBUG, logger="modules.interpret_safety")`, or the absence assertions cannot fail):**

| Id | Assertion | On `main` |
|---|---|---|
| HC-CLS-001 | Critical low: `check_critical_value("potassium", 1.937, critical_low=2.513)`. Over every record's `getMessage()` and `args`, `"1.937"` and `"2.513"` are absent; one WARNING contains `potassium` and `below critical threshold`. Pin: `requires_physician_review is True` and `physician_review_reason` equals today's string exactly (it is returned, so it keeps the value). | RED (value logged) |
| HC-CLS-002 | Critical high: `("potassium", 7.193, critical_high=6.487)`, same assertions with `above critical threshold`. | RED |
| HC-CLS-003 | Non-critical: `("potassium", 4.2)` with the default thresholds: no record from `modules.interpret_safety`, `"value_not_critical"` in `checks_passed`. | green (pin) |

Values are chosen so their strings cannot occur in the analyte or the fixed text. **Mutant controls** (scratch, paste output): (m1) restore the old f-string at `:194-196` → 001 fails; (m2) at `:204-206` → 002 fails; (m3) drop the direction word → 001 or 002 fails.

**Re-run, not edited:** `test_interpret_safety_adversarial.py`, `test_interpret_safety_enforce.py`, `test_interpret_safety_metadata.py` (`pytest tests/test_interpret_safety*.py`), then the full backend suite with `--collect-only` for the count.

**Files:** `src/backend/modules/interpret_safety.py` (the two `logger.warning` calls only; ask-first, CRIT-LOG-SCRUB), `src/backend/tests/test_interpret_safety_log_scrub.py` (new, HC-CLS-001…003), slots. No `interpret.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py` or auth file. **Expected collected delta:** +3. **Est:** 0.75 h.

**Gates.** CRIT-LOG-SCRUB approves the build only. **Merge waits on merge-only gate CRIT-LOG-DIFF**: the PR stays draft until L0 shows the owner the exact `interpret_safety.py` diff and the owner answers. Every prohibited pattern and check is unchanged, and the `interpret_safety` tests keep passing unedited; if either cannot hold, stop and ask.

**Order.** Ready now. Merges **before** INTERP-WITHHOLD-MSG Task 3 (#433) resumes. **Never beside** another non-draft PR on `modules/interpret_safety.py` or `modules/interpret.py` (#433 is a draft, so it may sit beside it).

**Runtime:** claude (+ Opus review; ask-first file, privacy).

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
| HC-EXF-006 | after EXTRACT-PAGE-MERGE (#336): table yields 2 observations and page text repeats those rows → still 2 observations, table methods only, no text duplicates (`test_hc_exf_006_no_duplicate_when_text_repeats_table`; rewrites the pre-#336 pin that skipped the text pass entirely) | no (pin) |
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

## EXTRACT-REGEX-NEWLINES — the imaging and visit-note section patterns are quadratic on newline runs

**Source:** #254 (PATH-REGEX-NEWLINES) review round 1, MINOR "out of scope, new row" (comment 6312199407): "`src/backend/modules/extract_imaging.py:22-23` (`FINDINGS_PATTERN`, `IMPRESSION_PATTERN`) and `src/backend/modules/extract_visit_notes.py:52,57,77` (`ASSESSMENT`, `PLAN`, `VITALS`) use the same `(.+?)(?=\n\s*[A-Z]{2,}|\Z)` + DOTALL shape. Measured at 20,000 newlines: `"FINDINGS:x"` took 4.6 s and `"PLAN:x"` took 4.75 s." Recurring-failures #9 (the shape PATH-REGEX-NEWLINES removed from one module is left in two siblings; the GRADE plan above timed only `extract_pathology.py`, and no plan timed the sibling extractors). Planned 2026-10-21 on `origin/main` @ `b9d285e`.

**Facts (`b9d285e`):**
1. Five patterns share the body `(.+?)(?=\n\s*[A-Z]{2,}|\Z)` under `re.DOTALL | re.IGNORECASE`, each after a label and `:?\s*`: `FINDINGS_PATTERN` (`src/backend/modules/extract_imaging.py:22`, label `FINDINGS?`), `IMPRESSION_PATTERN` (`:23`), `ASSESSMENT_PATTERN` (`src/backend/modules/extract_visit_notes.py:51-54`, labels `ASSESSMENT|A/P|ASSESSMENT\s+AND\s+PLAN`, stop `(?=\n\s*(?:PLAN|[A-Z]{2,})|\Z)`; `PLAN` is already covered by `[A-Z]{2,}` under `re.IGNORECASE`), `PLAN_PATTERN` (`:56-59`) and `VITALS_PATTERN` (`:76-79`, labels `VITAL\s+SIGNS?|VITALS?`). As in pathology, the lookahead's `\s*` re-scans the rest of a whitespace run at each step of the lazy body, so n newlines cost O(n²).
2. Each runs once per document (`extract_imaging.py:56`, `:65`; `extract_visit_notes.py:315`, `:324`, `:360`) through `_CATEGORY_EXTRACTORS` (`src/backend/api/documents.py:924-928`), on uploaded text. Values are `group(1).strip()[:500]` (`[:300]` for vitals, `:364`); spans come from `with_span` (`src/backend/modules/extract_spans.py:27-34`).
3. Consumers of the values beyond the entity list: `finding` and `impression` go into the FHIR export (`src/backend/modules/fhir_export.py:46`, `src/backend/api/export.py:55`). Visit-note care-task candidates use other entity types (follow-up, test ordered, referral), not these.
4. Tests: `tests/test_extract_imaging.py` (7 tests) and `tests/test_extract_visit_notes.py` (5 tests) check one simple value each; none times a pattern or checks an empty label. `tests/test_visit_note_extraction.py` scores a 12-file golden set (`tests/fixtures/visit_notes_golden/`); `tests/test_source_spans.py` checks spans on fixed texts.

**Measured on `b9d285e`** (scratch scripts under the session scratchpad, `~/venvs/asclexis-311/bin/python -I`, run from `src/backend`; not committed; this container is slower than the #254 reviewer's machine, which measured 4.6 s and 4.75 s):

| Input | `main` `Pattern.search` | candidate (design) |
|---|---|---|
| `"FINDINGS:x" + "\n" * n` | 0.015 s (1,000), 0.295 s (4,000), **6.72 s (20,000)** | 0.0002 s (50,000) |
| `"IMPRESSION:x" + "\n" * 20000` | **8.42 s** | 0.0003 s (50,000) |
| `"ASSESSMENT:x" + "\n" * 20000` | **11.90 s** | 0.0001 s (50,000) |
| `"PLAN:x" + "\n" * 20000` | **7.19 s** | 0.0001 s (50,000) |
| `"VITALS:x" + "\n" * 20000` | **8.56 s** | 0.0002 s (50,000) |
| the same five with `" \n" * 20000` | 13.5-22.5 s | 0.0003-0.0005 s (50,000) |
| whitespace only after a bare label (`" \n"` ×16,000, `"\n"` ×50,000, `"\t\n "` ×20,000), all five | 0.004-0.044 s (whole extractor; `\s*` takes the run, the body reaches `\Z`) | 0.0005-0.0043 s |
| `(label + " ") * 20000` | 0.011 s (ASSESSMENT) | 0.018-0.340 s; ASSESSMENT 0.154 / 0.379 / 0.889 s at 20,000 / 40,000 / 80,000 labels (`main` 0.011 / 0.026 / 0.053 s) |

Whole extractor on `main`: `extract_imaging_entities("FINDINGS:x" + "\n" * 20000)` 7.37 s, `IMPRESSION` 6.85 s; `extract_visit_note_entities` with `PLAN` 6.64 s, `ASSESSMENT` 10.92 s, `VITALS` 8.16 s. The candidate is slower than `main` on long runs of repeated labels (last row), but stays under 1 s at 80,000 labels (about 1 MB of text); it is linear on every newline input.

**Design (one candidate, measured; the implementer may choose another that passes the same tests):** the #254 shape, merged on PATH-NL-DIFF (a) (below), applied to each of the five: label atomic, separator possessive, the same body and stop.
- `FINDINGS_PATTERN`: `(?>FINDINGS?):?+\s*+` + body + stop; `IMPRESSION_PATTERN`: `(?>IMPRESSION):?+\s*+` …; `ASSESSMENT_PATTERN`: `(?>ASSESSMENT|A/P|ASSESSMENT\s+AND\s+PLAN):?+\s*+` …; `PLAN_PATTERN`: `(?>PLAN):?+\s*+` …; `VITALS_PATTERN`: `(?>VITAL\s+SIGNS?|VITALS?):?+\s*+` ….
- Body: `((?:\S|[^\S\n]+(?![^\S\n]|\n\s*[A-Z]{2,}|\s*\Z)|(?>[^\S\n]*\n\s*)(?![A-Z]{2,}|\Z))+?)`; stop: `(?=\s*\Z|[^\S\n]*\n\s*[A-Z]{2,})` (as `extract_pathology.py` on #254's head `ccd9425`). `ASSESSMENT_PATTERN`'s `(?:PLAN|[A-Z]{2,})` becomes the shared stop; the differential below shows no non-empty value changes. Flags unchanged (`re.DOTALL | re.IGNORECASE`); atomic groups and possessive quantifiers need Python 3.11+, the project floor.
- **Differential** (200,000 seeded random strings of 1-12 tokens from {`FINDINGS`, `Findings`, `finding`, `IMPRESSION`, `Impression`, `ASSESSMENT`, `A/P`, `Assessment and Plan`, `PLAN`, `plan`, `explanation`, `VITALS`, `Vital signs`, `:`, space, tab, `\n`, `\n\n`, `\r`, `AB`, `Ab`, `x`, `a`, `.`, `1`}; observable `(trimmed start, trimmed end, value)` as `with_span` trims). Seed 0: FINDINGS differs on 12,520 strings (`main` value `s` 4,423, `S` 4,412, `""` 3,179, `":"` 506), IMPRESSION 2,909 (`""` 2,540, `":"` 369), ASSESSMENT 2,641 (`""` 2,308, `":"` 333), PLAN 3,105 (`""` 2,660, `":"` 445), VITALS 13,548 (`S` 5,307, `s` 5,258, `""` 2,572, `":"` 411). In **every** difference `main`'s value is `""`, `":"`, `"s"` or `"S"` (the label's own last letter: `Findings`, `Vitals` with nothing after) and the candidate returns no match. Seeds 1, 2 and 42: the same property (per-pattern counts 2,307-13,597). It never returns a different non-empty value and never moves to a later label.
- **Golden set:** the 13 `.txt` files in `tests/fixtures/visit_notes_golden/` give identical entities from both extractors on `main` and with the candidate (0 of 13 differ).
- **Pins** (identical on `main` and the candidate, value and trimmed span): `"FINDINGS: No acute fracture.\nIMPRESSION: Normal study."` → finding `No acute fracture.` (0-28) and impression `Normal study.` (29-54); `"Findings:\n  Mild degenerative change.\n  1. small effusion\nIMPRESSION: ok"` → `Mild degenerative change.\n  1. small effusion` (0-57); `"FINDINGS:  Lungs clear.  \n\nIMPRESSION: none"` → `Lungs clear.` (0-23); `"ASSESSMENT: Type 2 diabetes, stable.\nPLAN: Continue metformin."` → assessment `Type 2 diabetes, stable.` (0-36); the same text plus `"\nFOLLOW-UP: 3 months"` → plan `Continue metformin.` (37-62); `"A/P: Hypertension\n  - continue lisinopril\nVITALS: BP 130/80"` → assessment `Hypertension\n  - continue lisinopril` (0-41); `"VITAL SIGNS: BP 120/80, HR 72\nASSESSMENT: well"` → vitals `BP 120/80, HR 72` (0-29); `"Vitals: BP 118/76  \n HR 70\nPLAN: none"` → vitals `BP 118/76` (0-17).

**Behaviour change, gated.** Like PATH-REGEX-NEWLINES, this changes what is extracted from a patient's document: a section label with no real value no longer yields an entity whose value is `""`, `":"` or `s`/`S`, so such an empty finding or impression also no longer reaches the FHIR export. That needs the owner's yes on the exact diff: merge-only gate **EXTRACT-NL-DIFF**, item 10 of [Owner gates](#owner-gates). The build is allowed now; the PR stays draft until EXTRACT-NL-DIFF. Related: PATH-NL-DIFF was answered (a) "Yes, merge this diff" for #254's `extract_pathology.py` diff (owner-decisions row PATH-NL-DIFF; its question said "Differential: 0 violations vs main" and did not describe the empty-value change). That answer licenses `extract_pathology.py` only; it is not an approval of this diff and is not cited to the owner as a reason.

**Test-first** (new file `src/backend/tests/test_extract_newline_runs.py`, the HC-PATH-004 child-process timing style of #254: `subprocess.run([sys.executable, "-c", …], input=text, cwd=src/backend, timeout=10)`, bound 1.0 s):

| Id | Assertion | RED today? |
|---|---|---|
| HC-ENL-001 ×10 (parametrised) | the extractor (`extract_imaging_entities` for FINDINGS, IMPRESSION; `extract_visit_note_entities` for ASSESSMENT, PLAN, VITALS) finishes in a child process in under 1.0 s on `label + "x" + "\n" * 50000` and `label + "x" + " \n" * 50000`, for the labels `FINDINGS:`, `IMPRESSION:`, `ASSESSMENT:`, `PLAN:`, `VITALS:` | yes ×10 (6.6-11.9 s already at 20,000; 10 s timeout at 50,000) |
| HC-ENL-002 ×6 (parametrised) | same child process, under 1.0 s: `"FINDINGS:" + " \n" * 16000`, `"IMPRESSION:" + "\n" * 50000`, `"ASSESSMENT:" + " \n" * 16000`, `"PLAN:" + "\t\n " * 20000`, `"VITALS:" + " \n" * 16000`, `"ASSESSMENT: " * 20000` | no (guards; `main` 0.004-0.197 s through the extractor, measured for all six; the last is the slowest). Mutant `:?\s*` instead of `:?+\s*+` (the shape of #254's first pathology candidate): `"ASSESSMENT:" + " \n" * 16000` takes **12.8 s**, so it fails |
| HC-ENL-003 ×8 (parametrised) | no entity of the label's type for `"FINDINGS:   \n\n"`, `"Findings"`, `"IMPRESSION:"`, `"ASSESSMENT:" + " \n" * 1000`, `"A/P:"`, `"PLAN:   \n\n"`, `"Vitals"`, `"VITAL SIGNS: \t\n"` | yes ×8 (`main` gives `""`, `"s"`, `":"`, `""`, `":"`, `""`, `"s"`, `""`, measured) |
| HC-ENL-004 ×5 (parametrised by pattern) | differential: an inline copy of today's pattern against the new one on 20,000 seeded random strings over the token set above: the same observable triple, **or** today's value is in {`""`, `":"`, `"s"`, `"S"`} **and** the new pattern returns no match | no (pin; the design gives 0 violations on seed 5, measured). Mutants, measured on seed 5: dropping the `\n\s*[A-Z]{2,}` stop → 1,285 violations (ASSESSMENT); a non-atomic label `(?:FINDINGS?)` → 229 violations (FINDINGS; the ASSESSMENT labels have no optional last letter, so 0 there); the non-possessive separator above → 9 (ASSESSMENT) |
| HC-ENL-005 ×9 (parametrised) | the 9 pins above: exact `entity_value`, `char_start`, `char_end` through the extractor | no (pins; measured identical) |

**Files:** `src/backend/modules/extract_imaging.py` (`:22-23` only), `src/backend/modules/extract_visit_notes.py` (`:51-59`, `:76-79` only), `src/backend/tests/test_extract_newline_runs.py` (new), slots. **Re-run, not edited:** `tests/test_extract_imaging.py`, `tests/test_extract_visit_notes.py`, `tests/test_visit_note_extraction.py`, `tests/test_source_spans.py`, `tests/test_documents_api.py`, `tests/test_fhir_export.py`.
**Expected collected delta:** +38 (10 + 6 + 8 + 5 + 9). **Est:** 2 h.
**Acceptance:** `pyt tests/test_extract_newline_runs.py tests/test_extract_imaging.py tests/test_extract_visit_notes.py tests/test_visit_note_extraction.py tests/test_source_spans.py tests/test_documents_api.py tests/test_fhir_export.py -q -rfE`: 0 failed; RED output for HC-ENL-001 ×10 and HC-ENL-003 ×8; the mutant outputs for HC-ENL-002 and HC-ENL-004; the differential counts per pattern pasted in the PR body (run HC-ENL-004 with `-s`, or a scratch script, so the counts are seen); full suite per RUNBOOK §6. **Rollback:** revert. Documents already extracted keep their stored entities until re-processed.
**Owner gate:** **EXTRACT-NL-DIFF** (merge only, answered 2026-10-21, prompt 28: "Yes, merge #277's diff"), Owner gates item 10 below.
**Order:** build allowed now; merge blocked on EXTRACT-NL-DIFF (PR stays draft). Not a dependency of #254 or on it: no shared file (#254 edits `extract_pathology.py` and its test). No open PR touches these files on `b9d285e`. No ask-first file. **Not in scope (found while planning, bullet EXTRACT-LABEL-BOUNDARY):** none of these labels has a word boundary, so `PLAN` matches inside `explanation` (`"Explanation of plan: rest\nVITALS: ok"` → plan `ation of plan: rest` on `main` and with the candidate alike); the other patterns in both modules were not timed.

## Bug diagnosis 2026-10-22 (planned 2026-10-22 on `origin/main` @ `5f7c67c`)

**Source:** the 2026-10-22 GPU-box runs, MM-4 run and F-9 dry run (evidence on the GPU box only: `/tmp/claude-1000/gpu-1022/`, `/tmp/claude-1000/mm4-1022/`, `/tmp/claude-1000/f9-dryrun/record.md`). Diagnosis table: `/tmp/claude-1000/bug-diagnosis-1022.md`; Codex proposals (read-only, `gpt-5.6-sol`): `codex-diag-judge.txt`, `codex-diag-extract.txt`, `codex-diag-fe-ui.txt`, `codex-diag-interp-meta.txt` in `/tmp/claude-1000/`. Every `file:line` was re-read on `5f7c67c` (`48a50b5` for the B-3 branch). **No owner approval is recorded here.** **Ask-first files (CLAUDE.md §1):** none edited by any row below; `modules/interpret_safety.py` is read only. Three new gates: JUDGE-THINK (blocks JUDGE-THINK), INTERP-DISC-ORDER (blocks INTERP-SAFETY-META), EXTRACT-DATE-PRIORITY (non-blocking). All three were answered in owner prompts 38-39 (2026-10-22; see each row); the owner-decisions rows land in L0's PR from `docs/owner-rows-prompts38-39`, not here.

### JUDGE-THINK — with Ollama thinking models the B-3 judge never answers ALLOW, so every answer is withheld

**Facts:**
1. B-3 (draft #264, `48a50b5`, parked until B-4): `src/backend/modules/agent/guardrails/advice_judge.py:45-47` `_CONFIG = InferenceConfig(max_tokens=3, temperature=0.0, timeout_seconds=JUDGE_TIMEOUT_S)` with `JUDGE_TIMEOUT_S = 2`; `:105-116` whole-response exact match `ALLOW` / `BLOCK`, anything else `UNAVAILABLE`; `modules/rag.py:1371-1381` (branch) withholds every non-`ALLOW` answer. The exact match and fail-closed rule are owner-approved (this lane §B-3 rule 1; `owner-decisions-2026-09-27.md:118`) and are **not** changed.
2. Main: `src/backend/core/llm/ollama_provider.py:130-146` (`_build_request_body`) sends `model`, `messages`, `stream`, `options` (`num_predict` = `max_tokens`) and `format`; no `think` key. The reply text is `message.content` only (`:213`, `:262`). `core/model_runner.py:32-41` `InferenceConfig` has no thinking field.
3. Measured on the GPU box (2026-10-22, `gpu-1022/judge_preview.py`, 40 texts): Ollama `gemma4:e4b` at the production 2 s: `verdicts {'UNAVAILABLE': 40}`, p50 2.01 s (`s2-preview-ollama.txt`); at a 60 s override: `{'UNAVAILABLE': 39, 'ALLOW': 1}`, p50 0.28 s, warm-up 13.16 s (`s2-preview-ollama-raw.txt`), so the failure is the 3-token reply, not the clock. llama.cpp Phi-4-mini: `{'ALLOW': 37, 'BLOCK': 3}` (`s2-preview-cpu-seq.txt`). The raw judge replies were not logged; "reasoning tokens use the budget" is the reading consistent with these numbers, not a capture.
4. Second finding for B-4 (not fixed here): at 2 s the first call never completes the 13 s cold load, and each later call timed out too (40/40 at about 2 s). Whether a warm-up belongs anywhere is a B-4 measurement question; the 2 s number is the owner's (Q4) and is not changed.

**Design (two parts, one row):**
- Main PR: `InferenceConfig.think: Optional[bool] = None` (`core/model_runner.py`, dataclass field only); `OllamaProvider._build_request_body` adds top-level `body["think"] = think` only when it is not `None`. Every existing call is byte-identical. No `<think>` stripping and no reading of `message.thinking`: either would loosen what reaches the exact match.
- B-3 plan delta (applied on #264 by whoever resumes B-3, after the gate): `_CONFIG` gains `think=False`; tests HC-PARA-110 and HC-PARA-101c below go into `tests/test_advice_judge.py` on that branch.
- Unknown-daemon behaviour is not assumed: a daemon that rejects the key gives an error -> `UNAVAILABLE` (fail closed); one that ignores it leaves today's failure. Ollama 0.40.5 on the box advertises `--think false` (Codex read of the binary; not run).

**Test-first:**

| Id | File | Assertion | RED today? |
|---|---|---|---|
| HC-OTK-001 | `src/backend/tests/test_ollama_think.py` (new, main) | `_build_request_body(msgs, InferenceConfig(think=False))["think"] is False` | yes (no field) |
| HC-OTK-002 | same | `"think" not in _build_request_body(msgs, InferenceConfig())` | GREEN today (pin: default unchanged) |
| HC-PARA-110 | `tests/test_advice_judge.py` (#264) | `httpx.MockTransport` behind a real `OllamaProvider`: the judge request body has `think: false`; an ordinary `generate_async` body has no `think` | yes on #264 |
| HC-PARA-101c | same | a provider reply `"<think>x</think>ALLOW"` gives `UNAVAILABLE` | GREEN (pin: the parse is not loosened) |

**Files (main PR):** `src/backend/core/model_runner.py` (`InferenceConfig` only), `src/backend/core/llm/ollama_provider.py` (`_build_request_body` only), `src/backend/tests/test_ollama_think.py` (new), slots. **Re-run, not edited:** `tests/test_llm_provider_layer.py`, `tests/test_llm_structured_output.py`, `tests/test_model_runner_exc_log.py`. **#264 (later):** `advice_judge.py` `_CONFIG` only, `tests/test_advice_judge.py` (two tests).
**Expected collected delta:** main +2; #264 +2 when it lands. **Est:** 1 h.
**Acceptance:** RED for HC-OTK-001; pytest set 0 failed; full suite. **Model-host check (L0, after #264 is resumed):** `judge_preview.py` against Ollama `gemma4:e4b` with the 60 s override gives ALLOW/BLOCK verdicts, not UNAVAILABLE; the 2 s production number is reported, not changed. **Rollback:** revert.
**Owner gates:** **JUDGE-THINK answered (a) "Judge only, think off"** in substance: Owner prompts 38-39 (2026-10-22, L0 AskUserQuestion; record `/tmp/claude-1000/prompts-38-39.json`; rows land in L0's owner-rows PR from branch `docs/owner-rows-prompts38-39`). Prompt 38 got a proposal instead of an option (a typed decision model, Jev / Laya); L0 re-asked in prompt 39 and the owner chose "Think off now + research Laya (Recommended)". The Laya research is a separate row, JUDGE-LAYA-RESEARCH, planned by another planner; it does not change this row. No answer is recorded in this file; the owner-decisions row comes from L0's PR.
**Order:** ready (owner rows on main via #291 `df9ca7f`). Never beside OLLAMA-NUM-CTX (lane A, also `_build_request_body`); whichever lands second merges `origin/main` and re-runs both test files.

### EXTRACT-UNIT-MGL — `mg/L` is not a known unit, so CRP lines are dropped silently

**Facts (`5f7c67c`):**
1. `src/backend/modules/extract.py:67-70` `_UNIT_ALT` lists `mg/dL` but not `mg/L`. The three text-line patterns use it (`:347-381`); `LINE_PATTERN`'s unit is optional but its `$` anchor rejects an unknown unit suffix; `ALT_LINE_PATTERN` and `COLUMN_LINE_PATTERN` require it. `_parse_text_line` returns `None` (`:417-427`).
2. Codex ran the patterns on `5f7c67c`: `CRP: 4.2 mg/L (0.0-5.0) => []`, `CRP 4.2 mg/L 0.0-5.0 => []`, `CRP: 4.2 mg/dL (0.0-5.0) => [('CRP', 4.2, 'mg/dL', 0.0, 5.0)]`.
3. Observed: MM-4 smoke and F-9 layouts 0, B and C lost CRP (record.md "PDF layout used"); only the ruled table (pdfplumber table path, no unit list) kept it.
4. EXTRACT-FORMATS (done, #164) added `mIU/L` and others; `mg/L` was not in its list (§EXTRACT-FORMATS). Storage needs nothing else: `api/documents.py:636-647` copies value and unit; `modules/normalize.py` `UNIT_CONVERSIONS` only matters for cross-unit trends (no CRP entry; none added).

**Design:** insert `mg/L|` right after `mg/dL|` in `_UNIT_ALT` (the order does not matter: `mg/L` and `mg/dL` are not prefixes of each other, review round 1; next to `mg/dL` only for readability). Nothing else.

**Test-first** (`src/backend/tests/test_extraction_pipeline.py`, new tests only):

| Id | Assertion | RED today? |
|---|---|---|
| HC-EXU-001 (×3) | `CRP: 4.2 mg/L (0.0-5.0)`, `CRP 4.2 mg/L 0.0-5.0`, and a column line `CRP   4.2   mg/L   0.0-5.0` each give one observation: value 4.2, unit `mg/L`, range 0.0-5.0 | yes (all three) |
| HC-EXU-002 | `LDL: 128 mg/dL (0-100)` still gives unit `mg/dL` (prefix order) | GREEN (pin) |

**Files:** `src/backend/modules/extract.py` (`:69` only), `src/backend/tests/test_extraction_pipeline.py` (new tests only), slots. **Re-run, not edited:** `tests/test_date_extraction.py`, `tests/test_extraction_golden.py`, `tests/test_unit_conversion.py`, `tests/test_documents_api.py`, `tests/test_source_spans.py`.
**Expected collected delta:** +4. **Est:** 0.5 h.
**Acceptance:** RED for HC-EXU-001; pytest set 0 failed; full suite. **Rollback:** revert.
**Owner gates:** none.
**Order:** ready; built in bundle 2 with EXTRACT-UNIT-MGL and EXTRACT-DOB-DATE (L0 ruling, #289 review round 1); the same-file order is inside that one PR.

### EXTRACT-DOB-DATE — a date of birth becomes the document's collection date

**Facts (`5f7c67c`):**
1. `src/backend/modules/extract.py:759-814` `_extract_dates`: stage 1 takes dates after collection labels (`_COLLECTION_LABEL_RE`, `:699-703`); stage 2 takes every generic date-shaped string with no exclusion; `_date_is_plausible` (`:713-715`) accepts 1950 onwards. Codex ran it on text with `DOB: 1970-01-01` and `Collection Date: 2026-03-02`: `['2026-03-02', '1970-01-01']`.
2. `src/backend/api/documents.py:662-667`: `document.collection_date = min(valid_dates)`, so the DOB wins. Then the same-date duplicate check (`:339-383`, called after extraction at `:518-524`) flags a second document with the same DOB: F-9 layout A showed "Possible duplicate upload" and Export listed both files as "1/1/1970" (record.md "PDF layout used", attempt A). Writing the DOB as `1 January 1970` avoided it only because that spelling is not a generic pattern.
3. The structured-import path (`:799-807`) takes `min()` over observation dates; it is not affected (observations take the page's first date, which is label-first).
4. No test covers a DOB (`git grep -n -i "dob\|birth" -- src/backend/tests/test_date_extraction.py`: no hit). `modules/redaction.py` has DOB patterns; it is ask-first and not reused here.

**Design (a), the row's scope:** in `_extract_dates`, skip a candidate (both stages) when the 32 characters before it end with a birth label: a module constant `_BIRTH_LABEL_TAIL_RE = re.compile(r"(?:\bd\.?\s?o\.?\s?b\.?|\bdate\s+of\s+birth|\bbirth\s*date|\bborn(?:\s+on)?)\s{0,3}[:\-]?\s{0,3}$", re.IGNORECASE)` run with `.search(text[max(0, start - 32):start])`. The window is fixed, so the check is linear in the text (Codex's prefix-wide `\s*[:\-]?\s*$` search is the REDACT-WS-REDOS shape, quadratic on whitespace runs; review correction). `min()` in `documents.py` is unchanged; with the DOB gone it picks the real date. Never invent a date: a document whose only date is a DOB is undated.

**Test-first** (`src/backend/tests/test_date_extraction.py` new tests; HTTP via `route_client` in `tests/test_documents_api.py`):

| Id | Assertion | RED today? |
|---|---|---|
| HC-DATE-007 (×5) | `DOB:`, `D.O.B.`, `Date of Birth:`, `Birth Date:`, `Born on` + `1970-01-01`, with `Collection Date: 2026-03-02`: result is `['2026-03-02']` | yes |
| HC-DATE-008 | text with only `DOB: 1970-01-01` and a lab line: `collection_dates == []` | yes |
| HC-DATE-009 | `"DOB" + " " * 50000 + "x 1970-01-01"` returns within 1 s | GREEN (pin against a prefix-wide look-behind: the non-space `x` before the date makes the rejected `\s*[:\-]?\s*$` search over `text[:start]` backtrack, quadratic, about 13 s at 50,000 per the round-1 timing; an all-space tail would match at once and could not fail) |
| HC-DATE-010 | upload of two text PDFs (same DOB, collection dates 2026-03-02 and 2026-06-01) through `route_client`: stored `collection_date` 2026-03-02 / 2026-06-01, and the second upload has no `same_date` duplicate warning | yes |

**Files:** `src/backend/modules/extract.py` (one constant + `_extract_dates` only), `src/backend/tests/test_date_extraction.py` (new tests only), `src/backend/tests/test_documents_api.py` (HC-DATE-010 only), slots. **Re-run, not edited:** `tests/test_extraction_pipeline.py`, `tests/test_source_spans.py`, `tests/test_fhir_export.py`.
**Expected collected delta:** +8 (007 ×5, 008, 009, 010). **Est:** 1.5 h.
**Acceptance:** RED for 007, 008, 010; pytest set 0 failed; full suite. **Rollback:** revert.
**Owner gates:** none for (a). **EXTRACT-DATE-PRIORITY answered (a) "Keep earliest date"** (Owner prompts 38-39 (2026-10-22, L0 AskUserQuestion; record `/tmp/claude-1000/prompts-38-39.json`; rows land in L0's owner-rows PR from branch `docs/owner-rows-prompts38-39`), prompt 38): `min()` stays, no follow-up row.
**Order:** ready; built in bundle 2 with EXTRACT-UNIT-MGL and EXTRACT-DOB-DATE (L0 ruling, #289 review round 1); the same-file order is inside that one PR.

### INTERP-GROUNDED-MD — the "Grounded explanation" panel shows raw `**UNCERTAINTY**`

**Facts (`5f7c67c`):** `src/frontend/src/pages/LabInterpreter.tsx:96` stores `data.full_response`; `:294-300` renders it in one `<p className="... whitespace-pre-wrap">`. The backend joins segments as `**SEGMENT TYPE**\n<content>` (`src/backend/api/interpretations.py:575-578`), which the claim extractor parses (`modules/claim_extractor.py:171`, `:181-182`), so the backend string stays. The formatter `components/lab-interpreter/formatInterpretationText.ts` (bold runs, no HTML) is used by `InterpretedResultCard.tsx` and `AdviceSection.tsx:3`. INTERP-RENDER (done, #161) did not list `LabInterpreter.tsx`.

**Design:** render `formatInterpretationText(groundedSummary).paragraphs` as `<p>` runs with `<strong>` for bold, as `InterpretedResultCard.tsx` does. Each `<p>` keeps `whitespace-pre-wrap`: the formatter splits paragraphs only on blank lines, so `**UNCERTAINTY**\n<content>` is one paragraph with a single `\n`, and without pre-wrap the header runs into the body (review round 1). No `dangerouslySetInnerHTML`, no Markdown library.

**Test-first** (`src/frontend/src/__tests__/LabInterpreter.test.tsx`):

| Id | Assertion | RED today? |
|---|---|---|
| HC-LAB-001 | `full_response: '**UNCERTAINTY**\nMore context is needed.'` -> `UNCERTAINTY` is in a `STRONG` element and the panel text has no `**` | yes |

**Files:** `src/frontend/src/pages/LabInterpreter.tsx` (`:294-300` + one import), `src/frontend/src/__tests__/LabInterpreter.test.tsx` (new test only). **Expected collected delta:** 0 backend; +1 Vitest. **Est:** 0.5 h.
**Acceptance:** RED for HC-LAB-001; `npx tsc --noEmit`; `npx vitest run`. **Owner gates:** none. **Order:** ready; built in bundle 3, the frontend PR with INTERP-GROUNDED-MD, CHAT-MODEL-BADGE, INTERP-RENDER-2 and VERIFY-DOCS-STALE (L0 ruling, #289 review round 1).

### INTERP-RENDER-2 — the gauge axis can exclude the value, and citation keys collide

**Facts (`5f7c67c`):**
1. `src/frontend/src/components/lab-interpreter/ReferenceRangeComparison.tsx:20-29`: axis = reference range ± 30 %, `valuePct` clamped to 0-100. The value is never in the min/max. MM-4: glucose 118 with range 70-99 -> axis 61.3-107.7; LDL 162 with range 0-100 -> axis 0-130 (`mm4-1022/out-interpret-grounded.json`: "The reference range is 0.0-100.0 mg/dL"). The marker sits at the edge, which understates how far out of range the value is.
2. `InterpretedResultCard.tsx:123` and `PanelInterpretationDashboard.tsx:110` key citations by `citation.id`. Backend source citations default `id` to `""` (`src/backend/modules/interpret.py:697`); MM-4's LDL card had two `{'type': 'source', 'id': ''}` -> React "two children with the same key".
3. INTERP-RENDER (done) fixed only the negative axis (non-negative floor); its tests stay.

**Design:** `paddedMin = Math.min(refLow, value) - padding`, `displayMin` keeps the non-negative floor rule on `paddedMin`, `displayMax = Math.max(refHigh, value) + padding`. Keys become `` `${citation.type}:${citation.id}:${i}` `` in both components. The backend empty id is left (display fix only).

**Test-first** (`src/frontend/src/__tests__/InterpretedResultCard.test.tsx`):

| Id | Assertion | RED today? |
|---|---|---|
| HC-IRC-007 | value 118, range 70-99: axis max label 126.7 (not 107.7); the marker's `left` is below 100 % | yes |
| HC-IRC-008 | value 162, range 0-100: axis max 192; axis min 0 (floor kept) | yes |
| HC-IRC-009 | two citations `{type:'source', id:''}` in both components: no `console.error` containing `same key` | yes |

**Files:** `ReferenceRangeComparison.tsx` (`:20-24` only), `InterpretedResultCard.tsx` (`:123` only), `PanelInterpretationDashboard.tsx` (`:110` only), `src/frontend/src/__tests__/InterpretedResultCard.test.tsx` (new tests only). **Re-run, not edited:** the INTERP-RENDER tests HC-IRC-004…006. **Expected collected delta:** 0 backend; +3 Vitest. **Est:** 0.75 h.
**Acceptance:** RED for each; `npx tsc --noEmit`; `npx vitest run`. **Owner gates:** none (no copy change). **Order:** ready; built in bundle 3, the frontend PR with INTERP-GROUNDED-MD, CHAT-MODEL-BADGE, INTERP-RENDER-2 and VERIFY-DOCS-STALE (L0 ruling, #289 review round 1).

### INTERP-SAFETY-META — template interpretations store "missing disclaimers" for text that ships with them

**Facts (`5f7c67c`, `src/backend/modules/interpret.py`):**
1. `:209` validates the text, then `:228` appends the disclaimers; same order at `:959` / `:978`. The stored safety metadata (`:236-240`, `:986-990`) therefore reads `passed: False`, `checks_failed: ['missing_disclaimers']`, and `interpret_safety.py:146` logs `Safety violation: Missing required disclaimers` (`mm4-1022/backend.log:115`) for a text the patient receives with disclaimers.
2. Codex probe (no writes): before `passed=False, ['missing_disclaimers']`; append-then-validate `passed=True, []`; prohibited text still `passed=False` with the prohibited checks.
3. Not the reason interpret-grounded abstains: the grounded route (`api/interpretations.py:449-611`) never calls `validate_interpretation`; its MM-4 abstain came from verification (`"Low faithfulness score: 0.00"`, 2 claims unverified).
4. No runtime reader of `checks_failed` / `safety_validation_json` (Codex grep); the API response omits it (`api/interpretations.py:116`).

**Design (if INTERP-DISC-ORDER (a)):** move the `add_required_disclaimers` block above `validate_interpretation` at both sites. `add_required_disclaimers` only appends, so the prohibited-pattern checks still see every original word. `interpret_safety.py` is not edited.

**Test-first** (new `src/backend/tests/test_interpret_safety_metadata.py`; HTTP via `route_client` for 001):

| Id | Assertion | RED today? |
|---|---|---|
| HC-ISV-001 | `POST /api/v1/interpretations/observations/{id}/interpret` on a seeded observation: stored metadata `passed` true, `has_required_disclaimers` in `checks_passed`, no `missing_disclaimers` | yes |
| HC-ISV-002 | the model path (`interpret_with_model` with a stub runner, benign cited text): same | yes |
| HC-ISV-003 | template path with a dosing sentence injected: `checks_failed` still contains the prohibited check and `passed` is false | GREEN (pin: no weakening) |

**Files:** `src/backend/modules/interpret.py` (the two blocks only), `src/backend/tests/test_interpret_safety_metadata.py` (new), slots. **Re-run, not edited:** `tests/test_interpret*.py`, `tests/test_safe_interp_grounded.py`, `tests/test_interpret_safety*.py`. **Expected collected delta:** +3. **Est:** 0.75 h.
**Acceptance:** RED for 001-002; pytest set 0 failed; `git diff origin/main --stat -- src/backend/modules/interpret_safety.py` empty; full suite. **Rollback:** revert.
**Owner gates:** **INTERP-DISC-ORDER answered (a) "Check the final text"** (Owner prompts 38-39 (2026-10-22, L0 AskUserQuestion; record `/tmp/claude-1000/prompts-38-39.json`; rows land in L0's owner-rows PR from branch `docs/owner-rows-prompts38-39`), prompt 38). Not an ask-first file, but the change moves when a safety check runs, so the owner decides (CLAUDE.md §3: never weaken a check without asking).
**Order:** ready (owner rows on main via #291 `df9ca7f`). Never beside B-5 (W-7), which edits `interpret.py`, or INTERP-SAFETY-ENFORCE (same function).

### VERIFY-DOCS-STALE — after "Mark All Verified" the "Documents needing attention" panel stays until reload

**Facts (`5f7c67c`):** `src/frontend/src/pages/VerificationWorkbench.tsx:136-150` (`handleMarkAllVerifiedClick`) with no selected document calls `useVerifyObservation().mutateAsync` per observation; `src/frontend/src/services/observations.ts:82-97` invalidates only `['observations']`. The panel reads `useDocuments` (`VerificationWorkbench.tsx:101`, key `['documents', filters]`). The backend flips the document once its last observation is verified (`src/backend/api/observations.py:480`); F-9 step 4: the panel listed both files as `parsed` until a reload showed "All observations verified".

**Design:** `useVerifyObservation.onSuccess` also invalidates `['documents']`.

**Test-first** (`src/frontend/src/__tests__/VerificationWorkbench.test.tsx`):

| Id | Assertion | RED today? |
|---|---|---|
| HC-VFY-001 | mocked API flips the document to `verified` when the last observation is verified; after "Mark All Verified" the panel text is gone without a reload and `/documents` was fetched again | yes |

**Files:** `src/frontend/src/services/observations.ts` (`onSuccess` only), `src/frontend/src/__tests__/VerificationWorkbench.test.tsx` (new test only). **Expected collected delta:** 0 backend; +1 Vitest. **Est:** 0.3 h.
**Acceptance:** RED; `npx tsc --noEmit`; `npx vitest run`. **Owner gates:** none. **Order:** ready; built in bundle 3, the frontend PR with INTERP-GROUNDED-MD, CHAT-MODEL-BADGE, INTERP-RENDER-2 and VERIFY-DOCS-STALE (L0 ruling, #289 review round 1).

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

Unless an item says it was answered, none of these is answered. Ask with the wording below; record answers in owner-decisions only when given.

1. **BGS-1 (B-1).** "When the app cannot confirm whether the privacy override is on, should the page say so? (a) yes, a neutral notice, copy: 'Could not confirm this installation's privacy settings. If the privacy protection override is on, external AI requests may leave this device with reduced redaction.' (b) also block external sends until confirmed (larger) (c) close the item as accepted." Recommended (a).
2. **IBF-1 (B-2 + W-7).** Options in §B-2. Recommended (a).
3. **PR3-TIER (B-3).** "Your Q4/Q5 'tier-2' minimum: the app cannot tell which tier a loaded model belongs to, except the `low` file. (a) enforce at measurement only, and block at runtime only when the loaded file is the `low` tier's (b) block unless the loaded file is a pinned mid-or-higher file (fails closed for everyone today) (c) other." Recommended (a).
4. **PR3-S5N (B-3/B-4).** "S5 size: the plan asks 180 + 200 items; your Q6 note says 40-60. Which?" Recommended: the plan's size, or accept ±8 points at 50.
5. **IUV-1 (B-6)**, **W7-SPILL (B-5)**, **S-C3-2** and **GC3A-LEDGER (B-8)**: wording in §B-6, the [W-7 pack](../../../audit/2026-09-25/waves/scaffold/W-7.md) Q3, and the [G-C3a pack](../../../audit/2026-09-25/waves/scaffold/G-C3a.md) §3.
6. **IR-FOOTER (INTERP-RENDER, planned 2026-10-17).** "The lab card footer says `Model: template` even when a local model wrote the separate grounded summary. What should it say? (a) plain source labels: 'Source: knowledge-base template' / 'Source: local model (<tier>)' (b) hide the tier (c) keep as is." Recommended (a).
7. **EXF-SAMPLE (EXTRACT-FORMATS, optional, planned 2026-10-17).** "Can you share the `extract_text()` output of one de-identified page of the column-layout report from MM-4? It becomes a regression row; the fix does not wait for it."
8. **GRADE-REDOS-DIFF (GRADE-PATTERN-REDOS, merge only, added 2026-10-20; asked after the draft PR exists).** "GRADE-REDOS-DIFF: here is the exact `modules/extract_pathology.py` diff for GRADE-PATTERN-REDOS, with RED/GREEN, timing, mutant output and the differential against today's pattern. It changes what is extracted from a pathology report in one shape: a grade label followed only by spaces and then `,` `;` `.` or a newline. Today that gives a grade entity with an empty value. With the diff, no empty grade is emitted; the search goes on, and in some strings (76 of 200,000 in the planning differential) it returns a later, non-empty value, for example `Tumor grade: ;\nMargins: clear, grade 3 elsewhere.` gives `3 elsewhere` instead of an empty grade. Which do you want? (a) Merge this diff: no empty grade, the search goes on to a later label. (b) Keep today's empty match at the first label: the implementer redrafts the pattern to keep it and asks again on that diff (more work; not yet designed). (c) Do not merge; leave the pattern as it is (the slow inputs stay slow)." No option is recommended: the choice is what a patient's report should show.
9. **PATH-NL-DIFF (PATH-REGEX-NEWLINES, merge only, added 2026-10-20; asked after the draft PR exists).** "PATH-NL-DIFF: here is the exact `modules/extract_pathology.py` diff for PATH-REGEX-NEWLINES (`DIAGNOSIS_PATTERN`, `SPECIAL_STAINS_PATTERN`), with RED/GREEN, timing and the differential. Every difference from `main` is a label with no real value, where `main` returns an empty diagnosis or stains value, a bare `:`, or `s` (the last letter of `Special stains`); the new pattern returns no entity there. No non-empty value changes, and no value moves to a later label. (a) merge this diff, as you chose for grades (GRADE-REDOS-DIFF (a)) (Recommended: same class of change, same reasoning) (b) redraft so empty values are kept exactly (zero differences), then ask again (c) leave both patterns as they are." This planned wording is **not** what the owner was asked. **Answered (a) "Yes, merge this diff"** 2026-10-21 (L0 AskUserQuestion, prompt 23) to the question recorded in owner-decisions row PATH-NL-DIFF: "Approve merging this `extract_pathology.py` diff? It rewrites the DIAGNOSIS and SPECIAL_STAINS patterns with atomic groups and possessive quantifiers (Python 3.11+) so newline runs are linear. Differential: 0 violations vs main." (PR #254 head `c550e24`; no option marked recommended).
10. **EXTRACT-NL-DIFF (EXTRACT-REGEX-NEWLINES, merge only, added 2026-10-21; asked after the draft PR exists).** "EXTRACT-NL-DIFF: here is the exact diff to `modules/extract_imaging.py` (`FINDINGS_PATTERN`, `IMPRESSION_PATTERN`) and `modules/extract_visit_notes.py` (`ASSESSMENT_PATTERN`, `PLAN_PATTERN`, `VITALS_PATTERN`) for EXTRACT-REGEX-NEWLINES, with RED/GREEN, timing and the differential. Timing: on `main` each of these patterns takes 6.7-11.9 s on a document with a 20,000-newline run (measured on `b9d285e`); with the diff, under 0.005 s at 50,000. What it changes: in a 200,000-string differential, every difference from `main` is a section label with no real value. There `main` returns an entity whose value is empty (`""`), a bare `:`, or `s`/`S` (the last letter of `Findings` or `Vitals`); with the diff no entity is returned, so such an empty finding or impression also no longer reaches the FHIR export. No non-empty value changes, and no value moves to a later label. Which do you want? (a) Merge this diff: no entity for an empty section label. (b) Redraft so empty values are kept exactly (zero differences), then ask again on that diff. (c) Do not merge; leave the five patterns as they are (the slow inputs stay slow)." No option is recommended: like GRADE-REDOS-DIFF (item 8), the choice is what a patient's document should show. **Answered 2026-10-21, prompt 28: "Yes, merge #277's diff"** (owner-decisions row EXTRACT-NL-DIFF; #277 merged `35cdb10`). This planned wording is **not** what the owner was asked: the owner saw a two-option question with corrected wording, quoted verbatim in owner-decisions row EXTRACT-NL-DIFF.

11. **JUDGE-THINK (JUDGE-THINK, new 2026-10-22; answered prompt 39: "Think off now + research Laya (Recommended)" = (a) plus row JUDGE-LAYA-RESEARCH; prompt 38 got a proposal, not an option; record `/tmp/claude-1000/prompts-38-39.json`, rows via L0's PR `docs/owner-rows-prompts38-39`). Wording as asked in prompt 38:** "The advice judge (B-3) asks the local model for one word, ALLOW or BLOCK, within 3 tokens. Ollama thinking models (gemma4:e4b, qwen3:8b) spend those tokens reasoning, so the judge fails closed every time and once B-3 lands every answer is withheld (measured 40/40 and 39/40 UNAVAILABLE). What should the judge do? (a) Judge only, thinking off (Recommended): only the judge request tells Ollama not to think; every other call and the exact ALLOW/BLOCK rule stay as they are. Tradeoff: B-4 must measure the judge with thinking off, and a model may judge a little worse without reasoning. (b) Thinking off everywhere: every Ollama call, chat answers included, stops thinking. Tradeoff: changes chat answers that nobody has measured. (c) Leave as is: thinking models cannot serve answers once B-3 lands; only non-thinking models (llama.cpp Phi-4-mini measured 37 ALLOW / 3 BLOCK) work." Options as asked: "Judge only, thinking off" / "Thinking off everywhere" / "Leave as is". Exact diff for (a): `core/model_runner.py` `InferenceConfig` gains `think: Optional[bool] = None`; `core/llm/ollama_provider.py` `_build_request_body` adds `think = getattr(config, "think", None)` / `if think is not None: body["think"] = think`; `advice_judge.py` `_CONFIG = InferenceConfig(max_tokens=3, temperature=0.0, timeout_seconds=JUDGE_TIMEOUT_S, think=False)` (plan: [JUDGE-THINK](#judge-think--with-ollama-thinking-models-the-b-3-judge-never-answers-allow-so-every-answer-is-withheld)).
12. **EXTRACT-DATE-PRIORITY (EXTRACT-DOB-DATE follow-up, new 2026-10-22; non-blocking; answered prompt 38: (a) "Keep earliest date").** "When a lab report has a labelled collection date and other dates (a printed-on date, say), the app uses the earliest date of all as the document date. Should a labelled collection date win instead? (a) Keep earliest date (Recommended): today's rule; the date-of-birth fix alone solves the reported bug. (b) Labelled date wins: closer to what the report means; documents re-processed later may change date, and a report with two labelled draws would use the first one printed, not the earliest." Options as asked: "Keep earliest date" / "Labelled date wins". A (b) answer becomes its own row (Codex sketch: `api/documents.py:665` `valid_dates[0]` + whole-document label order).
13. **INTERP-DISC-ORDER (INTERP-SAFETY-META, new 2026-10-22; answered prompt 38: (a) "Check the final text").** "Lab-card explanations are checked for disclaimers before the app adds them, so every saved card records 'missing disclaimers' and the log says 'Safety violation', although the patient sees the disclaimers. (a) Check the final text (Recommended): add the disclaimers first, then run every check; the advice and dosing checks still read every original word. Tradeoff: the disclaimer check then confirms the app's own appended sentence rather than catching a model that left it out. (b) Leave as is: no behaviour change; the stored result and the log stay misleading." Options as asked: "Check the final text" / "Leave as is". Exact diff for (a): in `modules/interpret.py`, move the `# Ensure disclaimers` block (`:227-231` and `:977-981`) above `# Validate safety` (`:208` and `:958`); nothing else; `interpret_safety.py` unchanged.
14. **INTERP-ENFORCE-DIFF (INTERP-SAFETY-ENFORCE, merge only, new 2026-10-22; open, asked with the draft PR's diff; no recommendation until it exists).** Wording, the four options ("Merge as shown", "Template path only", "Merge, then show message", "Do not merge"), tradeoffs and analogy: [INTERP-SAFETY-ENFORCE](#interp-safety-enforce--the-template-lab-interpretation-is-saved-and-returned-even-when-the-prohibited-advice-check-fails) Owner gates.
15. **JUDGE-SWAP (JUDGE-LAYA-RESEARCH, new 2026-10-22; answered 2026-10-26 by free text: "Try both Layla fine tune and NLI judge"; owner-decisions row JUDGE-SWAP; L0 reading: options 2 and 3, "Layla" is Laya; rows JUDGE-LAYA-FT, JUDGE-NLI-TUNE).** Wording, options ("Keep today's judge", "Fine-tune Laya next", "Try the NLI judge", "Stop here"), tradeoffs and analogy: [JUDGE-LAYA-RESEARCH](#judge-laya-research--a-typed-decision-encoder-laya-or-the-local-nli-cross-encoder-as-the-b-3-advice-judge-docs-only) Owner gates.
16. **JUDGE-SWAP-ADOPT (JUDGE-LAYA-FT, JUDGE-NLI-TUNE; new 2026-10-26; open, asked after both rows report; no recommendation until then).** Draft, filled in from both READMEs: "The two follow-up measurements are done (your sealed S5 was not used): fine-tuned Laya [runs, dev recall and false-block range with intervals, latency, size, what hosting needs]; the tuned NLI judge [dev recall and false-block with intervals, latency]; today's judge with thinking off [the research's numbers]. Adopting either encoder changes B-3's frozen design and restarts B-4's freeze, measurement and your sign-off. What next?" Options in plain words: "Keep today's judge", "Adopt fine-tuned Laya", "Adopt the NLI judge", "Measure more" (each with its tradeoff from the READMEs). An adoption answer becomes a B-3 design delta and a B-4 restart, planned then; it may also need an L0 ruling on contract I-15 and an owner answer on `ModelRunner` (CLAUDE.md §3).
17. **LAYA-CKPT-HOST (JUDGE-LAYA-FT; new 2026-10-26; asked only if JUDGE-SWAP-ADOPT chooses Laya).** "Where should our own fine-tuned Laya checkpoint live, and how does the app get it?" Options are drafted from JUDGE-LAYA-FT step 6 (for example a pinned download with revision and sha256 in the `cmd_nli` pattern, or a bundle), with size and licence. No recommendation here.

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
