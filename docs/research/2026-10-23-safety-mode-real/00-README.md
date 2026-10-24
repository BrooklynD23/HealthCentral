# Safety Mode research: what can the top-bar toggle really do (2026-10-23)

**Last Updated:** 2026-10-23
**Owner:** repository owner
**Status:** research complete, owner question SAFETY-MODE-BEHAVIOUR drafted and not yet asked
**Refresh Trigger:** an owner answer to SAFETY-MODE-BEHAVIOUR or SAFETY-MODE-DIFF; PR #264 (B-3 advice judge) merging or closing; a change to any `file:line` cited below (re-read before the build row starts); a new migration in `src/backend/migrations/profile/versions/`.

> **Point-in-time research (2026-10-23).** Planning and documentation only. No product code changed and no owner gate is answered here. Read at `origin/main` `fe9581f` (rebased from `035637e` after review round 1; the claim commit touches only queue text). The ExplainAssistant cite moved from `:571` to `:573` with BADGE-TICK (#332) and was re-read. Every `file:line` below was re-read on that tree. Medical-safety files named here (`interpret_safety.py`, `faithfulness.py`, `verifier_agent.py`) were read only.

## Where this comes from

Owner answer **UI-SAFETY-TOGGLE = "Make it real"** ([owner-decisions-2026-09-27.md](../../capstone-report/owner-decisions-2026-09-27.md), line 410) keeps a toggle and wires it to real behaviour. The plan ([frontend revamp plan](../../plans/2026-10-23-frontend-revamp-plan.md) section 7.2, row SAFETY-MODE-REAL) asks for concrete options, each with the files it touches, before any build. Until the owner answers, the toggle stays relabelled as inert (plan sections 3.6 and 8.1).

**The constraint (L0 reading in the plan, not an owner quote):** OFF must be exactly today's behaviour; ON may only be stricter. No option may weaken any check below today's default. Every option below was tested against that sentence; the ones that failed are in [Dropped](#dropped-options).

## What the toggle is today

- `src/frontend/src/components/layout/TopBar.tsx:9` holds `const [safeMode, setSafeMode] = useState(true);` and nothing reads it outside that component. It resets on every reload.
- It starts **ON**. So today's behaviour is displayed as "Safety Mode ON". Under the constraint, OFF is today's behaviour, so the label must change. Plan section 3.6 already sets "Stricter safety mode" (disabled, off, with the note that the standard checks always run), and the open non-blocking question SAFETY-LABEL-WORDING holds the alternatives. This research coins no label; the build row wires the switch under whichever wording is in force.

## What the pipeline does today (what an option can and cannot change)

| Path | What runs | Evidence |
|---|---|---|
| Chat, default (agent on) | No model writes the answer. The draft is built from database rows, then a fixed guard runs: advice gate, groundedness gate, confidence gate. The confidence signal is `1.0` or `0.0` only. | `src/backend/modules/agent/nodes/draft.py:342` (`async def draft(`), `src/backend/modules/agent/guardrails/guard.py:44` (`def groundedness_confidence(`), `src/backend/modules/agent/guardrails/guard.py:34` (`CONFIDENCE_THRESHOLD = FaithfulnessConfig().min_overall_score  # 0.6`) |
| Chat, legacy fallback (agent flag off, or any agent exception) | `rag.query` with a model, then `_legacy_serve_or_abstain` replaces any invalid answer with the fixed abstention. | `src/backend/api/assistant.py:1055` (`result = await rag.query(`), `src/backend/api/assistant.py:1072` (`result = _legacy_serve_or_abstain(result)`) |
| Interpretation, `POST /observations/{id}/interpret` | Template text only, then `interpret_safety` validates it. | `src/backend/api/interpretations.py:426` (`interp_result = await interpret_module.interpret_observation(`), `src/backend/modules/interpret.py:215` (`safety_result = self._safety_guard.validate_interpretation(`) |
| Interpretation, `POST /observations/{id}/interpret-grounded` | Template interpretation plus `rag.query` (a model writes the grounded segments). | `src/backend/api/interpretations.py:529` (`rag_result = await rag.query(`) |
| Model-written interpretation (`interpret_with_model`) | Defined but no route calls it. | `src/backend/modules/interpret.py:878` (`async def interpret_with_model(`) |
| Verified-only data | Already on for chat: the agent tools and the legacy retrieval both filter to verified rows. | `src/backend/modules/rag.py:390` (`Observation.user_verified == True,  # noqa: E712`), `src/backend/modules/rag.py:609` (`.where(Document.status == "verified")`) |

Three consequences the options below depend on:

1. **The default chat path has no graded score to tighten.** The agent guard's confidence is 0 or 1 (`guard.py:44` onward), so raising a threshold does nothing there. Threshold options reach the legacy fallback and `interpret-grounded` only. On the fallback a failed score becomes the fixed abstention. On `interpret-grounded` it only flips `is_valid` (see Option A).
2. **Template-only is mostly today's behaviour already.** The default chat and `/interpret` are template-driven. Only `interpret-grounded` and the legacy fallback use a model for prose.
3. **Verified-only is mostly today's behaviour already** for chat and retrieval (D4). The remaining gap is the interpretation API: every generate path calls `interpret_observation` or `interpret_panel` with no `user_verified` gate (`src/backend/api/interpretations.py:426`, `:486`, `:715`, `:865` on `origin/main`), and the GET routes return stored rows regardless (`:626`, `:743`). The only `user_verified` use today is `:511`, which keeps an unverified value out of the grounded question text, not out of generation.

## Shared plumbing (needed by any option, counted once)

**Where the setting lives.** There is already a per-profile settings table, so no new table is needed (CLAUDE.md section 2: extend what exists). `UserModelSettings` (`src/backend/models/model_settings.py:18`) already carries boolean per-profile preferences added one column per migration; the latest precedent is `streaks_hidden` (`src/backend/models/model_settings.py:141`, migration `014_streaks_hidden`). The next free revision is after `015_data_donation` (`src/backend/migrations/profile/versions/015_data_donation.py:17`, `revision: str = "015_data_donation"`).

| Storage | How | Survives lock and unlock | Fits which options | Cost |
|---|---|---|---|---|
| **Per-profile setting** (L1/L2 reading: preferred for A, B, D) | One new boolean column on `user_model_settings` (new profile migration 016, `server_default="0"` so every existing profile stays OFF), `GET`/`PATCH` pair modelled on `/assistant/memory-settings` (`src/backend/api/assistant.py:548` and `:570`) including the audit row | Yes. Lock closes the profile database and clears keys (`src/backend/api/profiles.py:992`, `lock_profile`; `src/backend/core/auth.py:428`) but does not delete rows. The value is read again after unlock. | all | 4 to 5 h (migration, model, route, audit, toggle wiring, tests) |
| **Request flag** (header or query parameter) | Frontend keeps the state and sends it on each call | Only as well as the browser stores it. The auth store persists only the token (`src/frontend/src/stores/authStore.ts:74`, `partialize`), so a flag needs its own storage, and a client that forgets to send it silently runs OFF. | C only (display) | 1 to 2 h |

**Cache trap.** The agent answer cache key is `normalized_question, profile_version, profile_id, tz_name, filters` (`src/backend/modules/agent/cache.py:43` to `:50`). It has no mode field. None of the four options below changes agent output, so no change is needed now. Any later option that does change agent output must add the mode to this key, or a stricter answer can replay under OFF and the reverse.

**Test pattern (all options).** Through HTTP with `route_client` (`src/backend/tests/support/routes.py:27`, `def route_client(`), using a real in-memory profile database and stubs below `rag.query`, as `src/backend/tests/test_safe_interp_grounded.py:83-101` does (it stubs `retrieve_context`, `_generate_with_runner` and `_run_verification_pipeline`, not `rag.query`; the `from tests.support.routes import route_client` import is at `:37`). A stub on `rag.query` itself would decide `is_valid` and hide whether a threshold was wired (recurring-failures #1). Every option needs the same two proofs: **OFF equals today** (same request with the setting absent, `false` and a pre-migration profile returns an identical body) and **ON is stricter** (a fixture that passes today is withheld, never the reverse). A route test that calls the handler directly would not see a broken `Depends(...)` (recurring-failures list), so none is proposed.

## The options

### Option A: Stricter checks

**Patient sees.** OFF: today. ON: an answer needs a higher verified share (the proposal uses 0.75 against today's 0.6; the number is for the owner to confirm and must stay above 0.6). On the legacy chat fallback, more questions get the fixed "There isn't enough verified information" abstention. On `interpret-grounded` the route today never abstains on `is_valid` false: it returns the segments with `is_valid` and `validation_errors`, and the page only turns a badge from verified to caution (`src/frontend/src/pages/LabInterpreter.tsx:189`, `<Badge variant={groundedValidation.isValid ? 'verified' : 'caution'}>`). So the threshold alone changes that badge, not the answer. The extra route row below makes ON withhold the answer there too. The default chat path is unchanged because its score is 0 or 1.

**Constraint check.** Passes: ON only raises thresholds; OFF keeps the 0.6 objects. No check is lowered.

**Design.** Build a second `RAGModule` (or per-call override) with `FaithfulnessConfig(min_overall_score=0.75)` and `VerificationConfig(min_faithfulness_score=0.75)`, selected when the profile setting is on. Both are plain dataclass arguments (`src/backend/modules/faithfulness.py:55`, `min_overall_score: float = 0.6  # Below this, flag as unfaithful`; `src/backend/modules/verifier_agent.py:85`, `min_faithfulness_score: float = 0.6`), so the ask-first files are **constructed differently, not edited**. The one hard-coded copy of the number is in `rag.py` and is not ask-first: it must read the scorer config instead of the literal, with the default staying 0.6.

| File | Change | Ask-first |
|---|---|---|
| `src/backend/modules/rag.py:940` (`if verification_metadata.faithfulness_score < 0.6:`) | use `self.faithfulness_scorer.config.min_overall_score`; default identical | no |
| `src/backend/api/assistant.py:217` (`def get_rag_module() -> RAGModule:`) and `:225`, `:230` (the two `0.6` literals) | choose the strict module when the profile setting is on | no |
| `src/backend/api/assistant.py:1055` (`result = await rag.query(`) | pass the chosen module; `_legacy_serve_or_abstain` (`:236`) already turns an invalid result into the abstention | no |
| `src/backend/api/interpretations.py:529` (`rag_result = await rag.query(`) | pass the chosen module | no |
| `src/backend/api/interpretations.py:598` (`if rag_result.prohibited_advice:`, the existing swap-to-template block; the new branch is its `else`) | `elif ON and not rag_result.is_valid:` (so it never runs when `prohibited_advice` is true; a prohibited match always makes `is_valid` false, `rag.py:915-916` and `:958`, and its `ESCALATE_TEMPLATE` clinician referral, owner decision SAFE-INTERP-GROUNDED, must win with exactly one `prohibited_blocked` audit row). In it: replace the segments with `ABSTAIN_TEMPLATE` (`src/backend/modules/agent/guardrails/templates.py:20`), set `full_response = ABSTAIN_TEMPLATE` (otherwise the withheld model text still ships in `full_response`, recurring-failures #2), clear `verification` as the block above does, and write an audit row through `_audit_interpretation` (`:38`) with no answer or question text. Without this branch, ON only changes the badge. | no |
| `src/backend/core/config.py:165` (`min_faithfulness_score: float = 0.6  # Minimum score for verified claims`) | read only; not changed (it is the global default) | no |
| `src/backend/api/assistant.py:1400` (`"min_faithfulness_score": 0.6,`) | status route reports the active value | no |
| `src/backend/modules/faithfulness.py:55`, `:149`, `:431` | **read only** | **yes**, not edited |
| `src/backend/modules/verifier_agent.py:85`, `:446`, `:480` | **read only** | **yes**, not edited |

**Conditional on PR #264** (B-3 advice judge, still an open draft; not main). #264 touches `assistant.py`, `interpretations.py`, `rag.py` and adds `modules/agent/guardrails/advice_judge.py`. If it merges first, the judge's threshold could join this option and the build row must be rebased on it; if the judge threshold lives in an ask-first file the SAFETY-MODE-DIFF wording below is needed for that file. Not designed here because the diff is not on main.

**Storage.** Per-profile setting. Survives lock/unlock: yes.
**HTTP test.** Stub at the `test_safe_interp_grounded.py:83-101` layer, with `_run_verification_pipeline` returning `faithfulness_score=0.70`, so the real `rag.py:940` comparison runs against the selected module's config. `POST /assistant/chat` with the agent disabled: OFF serves the answer, ON returns `ABSTAIN_TEMPLATE`. `interpret-grounded`, same stub: with no failed claims in the stub, OFF returns the segments with `is_valid` true; ON returns `ABSTAIN_TEMPLATE` as segment and as `full_response`, empty verification, and writes one audit row. Extra proofs: (1) a score of 0.50 on the chat fallback is withheld in both modes (interpret-grounded under OFF still serves segments with `is_valid` false); (2) a prohibited answer under ON still returns `ESCALATE_TEMPLATE` with exactly one `prohibited_blocked` audit row. Limit: the stubbed pipeline test would not notice if the build wired a strict `FaithfulnessConfig` but left `VerificationConfig` at 0.6, or the reverse. Add one test following `_real_verifying_rag` (`test_safe_interp_grounded.py:368`, real `_run_verification_pipeline`, stubbed retrieval and generation only) with `get_rag_module` returning a module built with **both** `FaithfulnessConfig(min_overall_score=0.75)` and `VerificationConfig(min_faithfulness_score=0.75)`.
**Cost.** 6 to 8 h plus the shared 4 to 5 h (the extra route branch, its audit and HTTP test add about 1 h).
**Honest limit.** Reach is the legacy fallback and `interpret-grounded`. A patient on the default agent path sees no change.

### Option B: Template-only explanations

**Patient sees.** OFF: today. ON: `interpret-grounded` returns the template interpretation plus a plain list of the cited facts (quoted from the patient's records and the reference corpus) and no model-written prose; the legacy chat fallback returns the fixed abstention instead of a model answer.

**Constraint check.** Passes, with one condition: the fact list is text that was never model-written, so it still has to go through the existing prohibited-pattern check (call `interpret_safety` as is). Removing model prose removes the most variable text; no check is lowered.

**Confirmed (the plan said "confirm").** `interpret_safety.py` still runs on template text: `src/backend/modules/interpret.py:215` validates the template output, and `:209` adds the required disclaimers. It is a pure rules module and needs no edit to be called on a fact list.

| File | Change | Ask-first |
|---|---|---|
| `src/backend/api/interpretations.py:529` (`rag_result = await rag.query(`) | when on, use retrieval only (`rag.retrieve_context`) and return the facts as segments | no |
| `src/backend/api/assistant.py:1055` (`result = await rag.query(`) | when on and the agent path failed or is off, return the abstention. ON makes the fallback always abstain, so a profile whose agent flag is off (`is_agent_enabled`, `assistant.py:1020`) gets a refusal for every chat question. | no |
| `src/backend/modules/interpret.py:209` and `:215` | read only; existing calls reused | no |
| `src/backend/modules/agent/nodes/draft.py:342` | none; already deterministic | no |
| `src/backend/modules/interpret_safety.py` | **read only**, called on the fact list | **yes**, not edited |

**Storage.** Per-profile setting. Survives lock/unlock: yes.
**HTTP test.** Same stub layer as `:49`: stub `retrieve_context` to return a chunk whose text contains a prohibited phrase, stub `_generate_with_runner` to return model prose, and leave `_run_verification_pipeline` stubbed or real as needed. `interpret-grounded` with ON: assert `_generate_with_runner` was never awaited, the body has no model-written prose (facts only), and OFF is unchanged. Chat fallback: ON abstains. Fact-list screening: assert `interpret_safety` withholds a prohibited fact from the list.
**Cost.** 6 to 8 h plus the shared 4 to 5 h.
**Honest limit.** Mostly today's behaviour already (see consequence 2). The visible change is on one route and the fallback. The `interpret-grounded` payload shape (`GroundedInterpretationResponse`, `interpretations.py:202`) must stay valid for the frontend.

### Option C: Always-on citations view

**Patient sees.** OFF: today (source chips under an answer, hover tooltips on interpretations). ON: each source is shown expanded inline under the answer or interpretation, with its document name, page and the quoted text.

**Constraint check.** Passes trivially: it changes display only, no backend check moves in either direction. It is not a safety *check*, and the owner should know this option does not make the system safer, it makes the grounding visible.

**Data gap.** The chat chip carries no quote (`src/frontend/src/pages/ExplainAssistant.tsx:51`, `interface CitationChip {` has `source, page, docId, observationId, entityId`). On the default agent path the API's `text_snippet` is a locator or id, not a quote (`src/backend/api/assistant.py:853`, `text_snippet=c.locator or c.source_id,`). So "quoted text" is real on the legacy and interpretation paths and would show a locator on the default path unless the agent citation also carries a quote; adding that is a backend change this option does not include.

| File | Change | Ask-first |
|---|---|---|
| `src/frontend/src/pages/ExplainAssistant.tsx:573` (`{message.citations && message.citations.length > 0 && (`) | render expanded when on | no |
| `src/frontend/src/components/lab-interpreter/InterpretedResultCard.tsx:119` (`{interpretation.citations.length > 0 && (`) | same | no |
| `src/frontend/src/components/lab-interpreter/CitationTooltip.tsx` | reuse content inline | no |
| `src/frontend/src/components/layout/TopBar.tsx:9` | wire the toggle | no |

**Storage.** Display preference only. Either the shared per-profile setting (survives lock: yes) or the request-free browser route: `localStorage`, keyed by profile id and wrapped in try/catch (survives lock only if the browser keeps it; the next profile on a shared machine must not inherit it, hence the key).
**Test.** No backend behaviour to put through `route_client`, so none is invented. If stored per-profile, `GET`/`PATCH` of the setting goes through `route_client`; the render is a vitest test. Both written at build time and **NOT RUN** here.
**Cost.** 4 to 5 h plus the shared 1 to 2 h (browser storage) or 4 to 5 h (per-profile).

### Option D: Verified-only data

**Patient sees.** OFF: today. ON: any request that would **generate** an interpretation for an unchecked lab value is refused with "verify this result first" (single observation, grounded, panel, and batch). Stored interpretations for unchecked values are **not returned** on the GET routes while ON (even if they were created while OFF). Unchecked values on the trends page are listed but not plotted.

**Constraint check.** Passes: ON refuses more, never less.

**Confirmed (the plan said "confirm").** `verifier_agent.py` stays read only. It imports only `typing`, `dataclasses`, `enum` and `re` (`src/backend/modules/verifier_agent.py:16` to `:19`) and has no database or file write; the option never calls it differently.

**Finding (recurring-failures #9).** Chat is already verified-only (`rag.py:390`, `rag.py:609`, and the agent tools). Refusing only at the two observation `POST` handlers would leave four other interpretation routes on `origin/main` unchanged: panel generate (`interpretations.py:689`, `interpret_panel` at `:715`), batch (`:806`, `interpret_observation` at `:865` with no check), stored GET (`:626`), and recent list (`:743`). Today the only `user_verified` branch in this file is `:511` (question text for grounded RAG, not a refusal). The plan's list names `ResultsPage.tsx`; that file does not exist. The real surfaces are `src/frontend/src/pages/TrendsDashboard.tsx` and `src/frontend/src/pages/LabInterpreter.tsx`.

| File | Change | Ask-first |
|---|---|---|
| `src/backend/api/interpretations.py:380` (`async def generate_interpretation(`) | when on, refuse before `:426` if `user_verified` is false | no |
| `src/backend/api/interpretations.py:453` (`async def generate_grounded_interpretation(`) | when on, refuse before `:486` if `user_verified` is false (not only `:511`) | no |
| `src/backend/api/interpretations.py:689` (`async def generate_panel_interpretation(`) | when on, refuse before `:715` if any observation in the panel at `collected_at` is unverified | no |
| `src/backend/api/interpretations.py:806` (`async def batch_generate_interpretations(`) | when on, refuse or skip each unverified id in the loop before `:865` | no |
| `src/backend/api/interpretations.py:626` (`async def get_interpretation(`) | when on, refuse if the linked observation is unverified (stored-under-OFF rows must not leak) | no |
| `src/backend/api/interpretations.py:743` (`async def get_recent_interpretations(`) | when on, omit interpretations whose observation is unverified | no |
| `src/backend/modules/interpret.py:139` (`async def interpret_observation(`) | none; refusal stays in the routes | no |
| `src/frontend/src/pages/TrendsDashboard.tsx:499` (`<TrendPointDot`) and `:533` (`<UnverifiedTrendNote`) | hide unverified points when on | no |
| `src/frontend/src/pages/LabInterpreter.tsx` | show the "verify first" state | no |
| `src/backend/modules/verifier_agent.py` | **read only** | **yes**, not edited |

**Storage.** Per-profile setting (the refusal is server-side). Survives lock/unlock: yes.
**HTTP test.** Seed one verified and one unverified observation. With OFF: `POST .../interpret` and `.../interpret-grounded` succeed for both (today); `GET .../interpretation` returns the stored row for the unverified one. With ON: both `POST` routes refuse the unverified id with a stable status; `GET .../interpretation` for that id refuses even when the row exists; `GET /recent` lists only the verified interpretation; `POST /batch` leaves the unverified id in `failed` (or equivalent) and succeeds for the verified id; panel route gets a fixture with one unverified member and is refused. Audit rows on refusals as today.
**Cost.** 7 to 10 h plus the shared 4 to 5 h (four extra routes, shared `user_verified` helper, and GET/stored-OFF proofs).
**Honest limit.** Chat sees no change. Does not retroactively delete interpretations created under OFF; ON hides or refuses them until the observation is verified. Interacts with W-3 (invariant I-13 in `docs/plans/2026-10-15-build-program/contracts.md`, line 33), which already marks unverified trend points; re-read the trends file before building.

## Dropped options

| Candidate | Why dropped |
|---|---|
| "OFF skips the checks" (the toggle's literal reading) | Fails the constraint: it weakens a check below today's default. The owner decision for chat (G-B5) and the claim that the checks are always on forbid it. |
| Turn on `use_llm_entailment` when strict | Not shown to be stricter: a model-based entailment can pass a claim the rule-based check fails. Cannot be shown to meet "only stricter" without an eval. Not pursued. |
| Raise the agent guard confidence threshold | No effect: the signal is only 0 or 1 (`guard.py:44`). Making it effective needs a new graded signal, which is a design change to a safety path, out of scope. |
| Lower the embedding threshold (0.7) or any current threshold | Forbidden by CLAUDE.md. |

## Owner question SAFETY-MODE-BEHAVIOUR (draft; not asked)

**Question.** "You asked to keep the top-bar toggle and wire it to real behaviour. Today every safety check always runs, and the toggle changes nothing. The constraint I am working to is: with the toggle OFF the app behaves exactly as it does now, and ON is only ever stricter, never looser. Which behaviour should ON mean? You may pick more than one; each is separate work."

| Option (5 words or fewer) | What changes for the patient |
|---|---|
| **Stricter checks** | Answers need a higher verified share (0.75, not 0.6); more questions get "there isn't enough verified information" on the older chat fallback, and a lab result's grounded explanation is replaced by the same message instead of only showing a caution badge. Not on normal chat. |
| **Template-only explanations** | No model-written sentences: a lab result's grounded explanation becomes the template text plus a list of the cited facts. Normal chat already works this way, but ON also makes the older chat fallback always refuse, so a profile with the assistant's agent mode switched off would get a refusal for every chat question. |
| **Always-on citations view** | Every answer and interpretation shows its sources expanded with name, page and quote, instead of small chips. No check changes; the grounding is just visible. |
| **Verified-only data** | Unchecked values cannot get new interpretations (single, grounded, panel, or batch) until you verify them; stored interpretations for unchecked values are not shown while ON; unchecked points are hidden from trend charts. Chat already uses verified values only. |

**Tradeoffs.**
- Stricter checks is the only option that visibly changes answers, at the price of more refusals. Its reach is the fallback and the grounded explanation (which needs the extra route branch, or only the badge changes), so most patients on the default path see little. The number 0.75 is a proposal, to be set or measured before the build.
- Template-only is safe and cheap to reason about but mostly describes today's default; the change is felt on one screen and the fallback. Its cost: ON makes the fallback always abstain, so a profile with the agent flag off gets a refusal for every chat question.
- Always-on citations is the cheapest and carries no safety risk, but it does not make anything safer; on the default chat path the "quote" is a locator until a backend change adds real quotes.
- Verified-only is easy to explain ("only what you checked") and refuses more, but chat already behaves this way; the build must gate every interpretation route (six handlers in `interpretations.py`, not two), including stored GET responses, or the toggle overclaims (recurring-failures #9).
- All four share one setting per profile (one new profile migration) except Always-on citations, which can live in the browser. All four need the label to change (plan section 3.6 already sets it; SAFETY-LABEL-WORDING holds the alternatives), because today's behaviour is shown as "Safety Mode ON" and must become the OFF state.

**Analogy.** A car with checks that always run (seat belt chime, brake assist). The toggle cannot switch those off. It can add an "extra careful" mode: slower to answer (stricter checks), a script instead of free speech (template-only), the dashboard showing every gauge (citations view), or refusing to drive on a part nobody has inspected (verified-only).

**Reading, not the owner's words (L1/L2).** The research supports one statement: template-only and verified-only mostly restate today's behaviour for chat, so choosing only those would give a toggle patients rarely feel. If the owner wants a toggle with visible effect and low risk, stricter checks (reach: fallback and grounded explanation, with the extra route branch so the answer, not only a badge, changes) plus the always-on citations view is the lowest-cost pair; the research does not support ranking beyond that, and the choice is the owner's.

## SAFETY-MODE-DIFF: draft wording (ask-first files)

**As designed, no option edits an ask-first file.** All four read `faithfulness.py`, `verifier_agent.py` and `interpret_safety.py` unchanged and pass different configuration into them from files that are not ask-first. If the build row finds it cannot, it must stop and use the wording below. Each sentence names the exact edit that would need an ask-first yes; none is requested now.

- **Option A, `src/backend/modules/faithfulness.py`** (only if constructing `FaithfulnessConfig(min_overall_score=...)` from `assistant.py` proves insufficient): "May I add a module-level constant `STRICT_MIN_OVERALL_SCORE` (value to be agreed, greater than 0.6) next to `min_overall_score` at `faithfulness.py:55`, leaving the default `0.6` and the comparisons at `:149` and `:431` untouched?"
- **Option A, `src/backend/modules/verifier_agent.py`** (same condition): "May I add `STRICT_MIN_FAITHFULNESS_SCORE` next to `min_faithfulness_score` at `verifier_agent.py:85`, leaving the default `0.6` and the comparisons at `:446` and `:480` untouched?"
- **Option B, `src/backend/modules/interpret_safety.py`** (only if the existing `validate_interpretation` cannot screen a fact list): "May I add one new method that applies the existing `PROHIBITED_PATTERNS` list to a list of strings, without changing the list or `validate_interpretation`?"
- **Option D, `src/backend/modules/verifier_agent.py`:** no edit proposed; none to ask.
- **Option C:** no ask-first file.

Each yes must name the file and the diff, and an unrelated edit to the same file is not covered.

## Summary table

| Option | Ask-first files edited | Ask-first files read only | New migration | Cost (option + shared) |
|---|---|---|---|---|
| A Stricter checks | none as designed (2 conditional) | `faithfulness.py`, `verifier_agent.py` | 016 (shared) | 6 to 8 h + 4 to 5 h |
| B Template-only | none as designed (1 conditional) | `interpret_safety.py` | 016 (shared) | 6 to 8 h + 4 to 5 h |
| C Always-on citations | none | none | none if browser storage | 4 to 5 h + 1 to 2 h |
| D Verified-only | none | `verifier_agent.py` | 016 (shared) | 7 to 10 h + 4 to 5 h |

The shared cost is paid once however many options are picked.

## What was not done

- No threshold, code, test or count slot was changed, and no gate was signed.
- PR #264's diff was not read as main; its file list was read from the PR page only.
- The 0.75 value, the hour ranges and the fact-list design are estimates from reading, not measurements.
