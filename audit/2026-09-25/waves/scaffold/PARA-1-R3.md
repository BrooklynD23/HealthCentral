**Verdict: PLAN, NOT APPROVED FOR EXECUTION.** Recommended: a local LLM answer check (option C) at the one seam every model-written answer passes through (`modules/rag.py:1276`). It is ORed with today's patterns, which stay as the floor. Every owner question in §9 is open. Codex review: REVISE (1 blocker, 4 major), all folded in; see §11.

# PARA-1-R3: prohibited-paraphrase recall outside `interpret_safety.py`

**Written:** 2026-10-09, worktree `hc-para-r3` (`docs/para-1-r3-plan`), base `origin/main` = `eb7de28`.
**Gate:** PARA-1-R3 "Stop using patterns" (`docs/capstone-report/owner-decisions-2026-09-27.md:87` in the `hc-l0-docs` worktree @`a08c427`; not yet on `origin/main`): "Keep today's list as a floor; a plan moves recall to another layer (agent draft path / PARA-2 or a classifier step)." `interpret_safety.py` stays unedited.
**Nothing implemented.** No file under `src/`, `scripts/` or `docs/` is edited by this plan's PR.
**Ask-first files:** none of `modules/interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py` is edited by any option here. Option C reads `InterpretationSafetyGuard.PROHIBITED_PATTERNS` only through the copy `rag.py` already compiles (`rag.py:178-181`).

## 1. Where we are (measured, not re-run here)

| Fact | Evidence |
|---|---|
| Live list (11 patterns) on the round-2 blind set: 29/180 caught, 11/200 safe sentences blocked | owner-decisions `:87` |
| `union_r2` (live 11 + 24 new, frozen `7991d96`): 0 lost of 215, 0.00 s, but 111/180 (61.7 %) and 23/200 blocked on that blind set | owner-decisions `:87`; `audit/2026-09-25/waves/wave-4-L0-notes.md:42` (both @`a08c427`); candidates on `test/para-round2-measure` @`7991d96` |
| 0 false positives is impossible while the live list is kept: it alone blocks 11/200 | `wave-4-L0-notes.md:42` |
| The blind set (180 must-block / 200 must-allow, sha256 `7e0830c0…`) lived only in L0's scratchpad and is gone | `wave-4-L0-notes.md:42` ("not committed") |
| Every other corpus has been read by someone who tuned patterns on it | `wave-4-L1-A.md` "How the out-of-sample claim was protected" |
| Real model output was never measured in any round | `wave-4-L1-A.md` finding 7 |

## 2. Where model-written text reaches a user (real flow, `origin/main@eb7de28`)

Verified by L1 (reads) and a Haiku sweep; every row below re-opened by L1.

| # | Surface | Path | Model prose? | Check today |
|---|---|---|---|---|
| 1 | Chat, agent on (default: `modules/agent/settings.py:19`) | `api/assistant.py:788` → `:793` `_serve_via_agent` → `modules/agent/graph.py:145` `run_agent` → `:169` `classify_advice(question)` → `nodes/draft.py:262` → `graph.py:225` → `guardrails/guard.py:103-129` | **No.** `draft` builds every sentence from tool rows (`draft.py:69`, `:83`, `:122`, `:161`, `:199`); no ModelRunner call in `modules/agent/` | question and draft regex (`guardrails/classifier.py:73`), groundedness, confidence; fixed templates (`templates.py:12`, `:20`) |
| 2 | Chat, agent off **or agent raised** | `api/assistant.py:814` → `rag.query` (`modules/rag.py:1179`) → `_generate_with_runner` `:1280` → `runner.generate_async` `:1296` → `validate_response` `:1276` (def `:795`, loop `:839-842`) → `assistant.py:879-892` | **Yes** | live 11 patterns → whole answer replaced by `ESCALATE_TEMPLATE`, audited |
| 3 | Grounded interpretation, `POST /observations/{id}/interpret-grounded` | `api/interpretations.py:422` → `:484` `rag.query` → same as row 2 → `:543-552` | **Yes**, on every call | same as row 2 |
| 4 | Template interpretation and panels | `api/interpretations.py:396`, `:448`, `:789` → `modules/interpret.py:139` → `:192` `_generate_interpretation` (`:555`, string parts joined at `:638`) | No | `validate_interpretation` `:209`; failure only sets flags (`:238`, `:266`) |
| 4b | Visit-note entity extraction, `POST /documents/{id}/reprocess?llm_assist=true` | `api/documents.py:1145` → `:983` `llm_assist_visit_entities` → `modules/extract_visit_notes.py:499` `generate_async`, parsed at `:512` | Model output, but **structured and quote-grounded** proposals the user verifies, not an answer | **excluded** from this plan (not answer prose) |
| 4c | Stored-answer replay: session history, feedback export | `api/assistant.py:436-439` `_load_session_history`; `api/feedback.py:375` `response_text` | Replays answers already persisted | a new check covers **new** answers only (owner Q8) |
| 5 | LLM lab interpretation | `modules/interpret.py:877` `interpret_with_model` → `:735` → `:761` `model_selector.run_inference` (direct llama, not ModelRunner) | Yes, but **no product caller** (`grep -rn interpret_with_model src/backend` outside tests: definition only) | out of scope; see R-6 |

**Consequence:** rows 2 and 3 are the only live paths where model paraphrase can reach a user, and both pass through one line: `validated = self.validate_response(response, chunks)` at `modules/rag.py:1276`. Both callers already turn `prohibited_advice=True` into the fixed escalation answer plus an audit row. A new check that sets the same flag needs no route change.

`runner` in row 2/3 may be an **external** API runner (`core/external_runner.py:408`, `:433`; picked at `api/assistant.py:755-758`, `api/interpretations.py:475-481`). Any check that sends the answer to "the request's runner" would send patient text off the device. The check must use the local `core.model_runner.get_model_runner()` (`core/model_runner.py:239`) only.

## 3. Candidate layers

### A. PARA-2: apply a check to the agent draft path

- **Recall gain on model paraphrase: 0 by construction.** The agent never emits model prose (table row 1). Its sentences are fixed templates filled with record values, trends, dates, counts and medication entities (`draft.py:80`, `:116`, `:187`), plus sanitized quoted record text ("The note says: …", docstring `:27-30`). Any risky wording there is template copy (a code change with a test) or the patient's own clinician's text, not paraphrase by the model. (Corrected after Codex finding 3.)
- **Cost:** the live list already flags 3 of the product's own draft sentences (`draft.py:155`, `:193`, `:249`; `wave-4-L1-A.md` finding 2). Wiring it in would escalate correct record answers.
- **Verdict:** not a recall layer. It answers scaffold Q4 (`PROHIBITED-PARAPHRASE.md` §3): PARA-2 is not needed for model output.

### B. Remove the free-text surface

Serve rows 2 and 3 from deterministic composition (the agent, or templates), so no model prose reaches the user and recall stops being a measured quantity.
- **For:** strongest guarantee; testable by construction (no route returns `generate_async` text).
- **Against:** removes the LLM explanation, the product's stated core ("chat with a local-LLM assistant that explains results", `AGENT.md:7`); drops the one-release chat fallback (`api/assistant.py:804`), so an agent exception has to become a fixed abstain; the grounded-interpretation route needs a new agent-shaped composition. Largest change of the four.

### C. Local LLM answer check at the `rag.py` seam (recommended)

After `validate_response` at `rag.py:1276`, when the live floor did not fire, make one extra local call through the ModelRunner facade asking for a single label, and OR the result into `prohibited_advice`.

```
validated = self.validate_response(response, chunks)          # rag.py:1276, unchanged
if not validated.prohibited_advice:
    outcome = await advice_judge(response, runner=judge_runner)    # "ALLOW" | "BLOCK" | "UNAVAILABLE"
    if outcome != "ALLOW":
        validated = dataclasses.replace(                            # ValidatedResponse is a dataclass, rag.py:103
            validated, prohibited_advice=True,
            prohibited_reason="advice_judge" if outcome == "BLOCK" else "advice_judge_unavailable")
```

- **Home:** one new file `modules/agent/guardrails/advice_judge.py` (about 60 lines: frozen prompt constant, `advice_judge(text, runner) -> "ALLOW" | "BLOCK" | "UNAVAILABLE"`, strict parser). A tri-state result, not a bool, so a block and a failure audit differently (Codex finding 2). Not `guardrails/classifier.py`: that module's contract is "Deterministic … NO LLM" (`classifier.py:22-29`) and both agent call sites rely on it.
- **Runner:** `judge_runner` defaults to `get_model_runner()` (`core/model_runner.py:239`, the local singleton), never the request runner; it is a parameter of `rag.query` so tests inject a fake (existing tests patch `_generate_with_runner`, `tests/test_rag_pipeline.py:1117`, and would not fake a separate call otherwise). Local-first holds: llama.cpp in-process or Ollama on localhost (`core/llm/factory.py`).
- **Call:** `InferenceConfig(max_tokens=3, temperature=0.0, timeout_seconds=<owner Q4>)`. The answer goes in a delimited block; the prompt carries the five category definitions from the PROHIBITED-PARAPHRASE plan and nothing from any corpus. No question, no retrieved context, no history (smaller injection surface, shorter prompt).
- **Parse:** the whole response, stripped of surrounding whitespace, must equal exactly `ALLOW` or `BLOCK` (case-sensitive), and `finish_reason` must be `stop` or `length`. Anything else, including `ALLOW please` or `ALLOW\nBLOCK`, is `UNAVAILABLE` (§5). (First-token parsing was wrong: Codex finding 1.)
- **Timeout and serialization:** the judge runs after generation, in the same request, so one request never overlaps its own two calls. `LlamaCppProvider.generate_async` wraps a thread in `asyncio.wait_for` (`core/llm/llama_cpp_provider.py:277-280`); on timeout the thread keeps running and the request fails closed. Concurrent requests already share the singleton with no lock today (`grep -n Lock core/llm/llama_cpp_provider.py` → 0); the judge doubles that exposure (R-7).
- **Audit:** reuse the existing rows (`assistant.py:883-892`, `interpretations.py:550-552`). Both hard-code `"reason": "prohibited_pattern"` today (`assistant.py:891`, `interpretations.py:552`); execution adds a `prohibited_reason` field to `ValidatedResponse` (default `"prohibited_pattern"`) and both routes read it, so the audit says `prohibited_pattern`, `advice_judge` or `advice_judge_unavailable`. No answer or question text, as today. The block itself is already safe: chat swaps the answer before the turn is persisted (`assistant.py:879` before `:899`), grounded interpretation before it returns (`interpretations.py:543` before `:558`).
- **For:** one seam covers both live surfaces; no new dependency, no new model file; generalises to paraphrase where patterns cannot; the floor keeps every live catch (0 lost by construction, the round-2 condition).
- **Against:** latency (a second prompt evaluation of up to 1,024 answer tokens on CPU; UNMEASURED); the model judging its own output shares its blind spots; quality depends on the tier the user downloaded; the answer text can carry injected instructions from the patient's documents; needs a local model even for external-runner users (Q3).

### D. Embedding classifier

Use `all-MiniLM-L6-v2` through `sentence-transformers`, which the RAG module already loads lazily by name (`modules/embeddings.py:17`, `:55`; the model file may be absent) with exemplar nearest-neighbour or a small trained head.
- **For:** milliseconds, deterministic, no LLM call.
- **Against:** sentence embeddings encode topic more than stance, so "You have diabetes." sits next to "This test helps check for diabetes."; the module silently falls back to hash embeddings when the model is absent (`embeddings.py:138`), which turns the classifier into noise without an error (recurring-failures §4; the repo already has one test that fails without the model, `CLAUDE.md` baseline note); exemplars drawn from the burned corpora risk overfitting (testable on S5 and R if D is frozen first, not an inherent defect); shipping a trained head is a new reviewed artifact.

### E. Prompt-side instruction

Not a recall layer (it changes the base rate, not detection). Out of scope; may sit beside any option.

### Recommendation

**C, conditional on its numbers.** Of the options that keep the product's explanations, it is the one whose known weakness (shared blind spots, latency) is measurable on S5 and R, while D's (stance blindness, silent hash fallback) is structural. The floor guarantees it loses nothing today's list catches. C ships only if it meets targets the owner fixes **before** S5 is written (Q5). If the measured latency (§6) breaks the owner's bound, fall back to **B** for the grounded-interpretation route only and keep C on legacy chat, which is reached only when the agent is off or failed.

## 4. Local-first constraint

| Rule | How C meets it | Test |
|---|---|---|
| No network in product paths | local `get_model_runner()` only; Ollama provider is localhost-only | T2 below asserts an external fake runner never receives the answer |
| All LLM calls via the facade | `generate_async` on `ModelRunner` (`core/model_runner.py:174`); no `llama_cpp` import | `grep -n "llama_cpp" modules/agent/guardrails/advice_judge.py` → 0 |
| Redaction before anything leaves | nothing leaves; the answer never goes to an external runner | T2 |

## 5. Failure mode: fail closed, or fall back to the floor

| Event | Proposed | Alternative (owner Q2) |
|---|---|---|
| Judge says `BLOCK` | escalate: `ESCALATE_TEMPLATE`, as SAFE-CHAT does today | — |
| Judge times out, raises, or returns anything but `ALLOW`/`BLOCK` | **fail closed**: block the answer, audit `advice_judge_unavailable` | floor only: return the answer if the live patterns passed, audit the miss |
| No local model, request used an external runner | **fail closed** (consequence: external-runner users get no model answers) | floor only for external-runner requests; or refuse to enable external runners without a local model |

"Abstain" (`ABSTAIN_TEMPLATE`, `templates.py:20`) is the wrong copy for any of these: it tells the user their record lacks verified data. Blocking reuses `ESCALATE_TEMPLATE`, which the owner already signed for this purpose (SAFE-CHAT-TPL). A dedicated "could not check this answer" template is owner Q7; copy changes are code changes with a test (`templates.py:3-5`).

Conservative default, per `CLAUDE.md` §1: fail closed.

## 6. Measuring recall and precision without overfitting

**Every corpus in the repo is now dev data.** `in_sample`, `must_not_regress`, `held_out_dev`, `held_out_final`, `held_out_final2` (`src/backend/tests/fixtures/prohibited_patterns/`) have all been read by someone who tuned on them. Prompt iteration may use them freely; no number from them counts as evidence.

**Sealed set S5 (replaces the lost blind set):**
1. Freeze first: commit the judge prompt, parser and the list of model tiers to be measured. Record the sha. No change after this point without a new sealed set.
2. Author: someone with no repo access, given only the five category definitions and the must-allow genres: lab education, numbers with units (`mg/dL`), app instructions, refusals ("I won't advise you to …"), quoted clinician notes, negations. At least 180 must-block and 200 must-allow (round-2 size; a Wilson 95 % interval at 85 % on 180 is about ±5 points). Who writes it: owner Q6.
3. Custody: the file goes to the owner and lives outside every worktree and scratchpad (set 4 was lost because it lived in a scratchpad). Its sha256 and item counts are committed before the run.
4. One session: the holder runs one command (two passes, for agreement) against the frozen sha and reports aggregate counts, per-category counts and the failing items. Then the set is burned: committed as dev data. A second attempt needs S6.

**Real-output set R (never measured before):** a fixed question bank (bait questions written to draw out diagnosis or dosing, plus ordinary questions) run through the legacy RAG path offline on each measured tier; **raw generations captured before the judge** (the harness calls the pipeline's generation step and records the floor decision and the judge outcome separately; capturing route output would hide what was blocked), stored in a file outside the repo (they can contain synthetic-profile text only: use the synthetic vault states from `asclexis-evals`, never a real profile). Two labelers label each answer independently; the owner settles disagreements. Recall and added false positives on R are reported separately from S5.

**What is reported (per tier, per set):**

| Metric | Definition |
|---|---|
| System recall | must-block caught by floor OR judge |
| Judge-added recall | caught by judge, missed by floor |
| Added false positives | must-allow blocked by judge, passed by floor (the floor's own 11/200 are a known cost and not the judge's) |
| False-positive rate | added false positives ÷ must-allow items, per set (class-specific; no precision figure without an assumed prevalence of must-block answers, which R gives only for its own question bank) |
| Unavailable rate | share of calls that returned `UNAVAILABLE` |
| Agreement | same verdict on two full passes of the same set (S5 is run twice in its one session) |
| Latency | added seconds per answer, p50 and p95, on the owner's machine, for 200- and 1,000-token answers |

Targets are the owner's (Q5); the previous bar was 85 % recall.

Harness: a `--judge` mode on `src/backend/scripts/measure_prohibited_patterns.py` (or a sibling script), run with `HF_HUB_OFFLINE=1` and a real GGUF. Not a pytest test: it needs a model, so it is a recorded measurement with the tier, model file sha256 and commit sha (recurring-failures §4).

## 7. Test plan (pytest, `HC-PARA-1xx`; fake provider via `ModelRunner(_provider=...)`)

| ID | Asserts | Fails if |
|---|---|---|
| T1 parser | `ALLOW` and `" ALLOW\n"` → `ALLOW`; `BLOCK` → `BLOCK`; `""`, `"allow"`, `"ALLOW please"`, `"ALLOW\nBLOCK"`, `finish_reason="timeout"`, exception → `UNAVAILABLE` | parser loosened, or a failure fails open |
| T2 local only | request with an external fake runner: the external fake receives the generation prompt and **never** the judge prompt; the local fake receives the judge prompt | judge uses the request runner (privacy) |
| T3 chat route (HTTP, `tests/support/routes.py::route_client`, agent disabled) | judge `BLOCK` → `full_response == ESCALATE_TEMPLATE`, audit `details.reason == "advice_judge"`, persisted turn holds the template, not the answer | flag not honoured, answer persisted |
| T4 grounded route (HTTP) | same for `POST /observations/{id}/interpret-grounded` | second caller missed (recurring-failures §9) |
| T5 floor | live pattern fires and judge says `ALLOW` → still escalates; judge not called when the floor fired | OR became AND; break-it: change it and show T5 FAIL, restore, PASS |
| T6 unavailable | judge raises → blocked, audit `advice_judge_unavailable` | fail-open slips in |
| T7 agent untouched | `scripts/agent_eval_gate.py` → `All 74 golden cases passed.` with `timeout 600`, rc recorded (GATE-14) | agent path changed |

Stay green: `test_safe_chat_prohibited.py`, `test_safe_interp_grounded.py`, `test_prohibited_patterns_regression.py`, `test_interpret_safety_adversarial.py`, `test_rag_pipeline.py`, `test_biomarker_assistant.py`. Existing RAG tests that mock the runner will now see a second call; each needs the fake to answer `ALLOW` explicitly, never a blanket bypass flag. Collected count updated per SLOT-RULE.

**What these tests cannot see:** real-model recall, real injection resistance, real latency. Those come only from §6, which is why §6 is part of acceptance and not optional.

## 8. Residual risks

| # | Risk | Severity | Note |
|---|---|---|---|
| R-1 | Same model writes and judges; shared blind spots | HIGH | measured on R, not removable within C; B removes it |
| R-2 | Injected text in the patient's own documents reaches the answer and steers the judge to `ALLOW` | MEDIUM | strict parse and no context in the judge prompt narrow it; floor still applies |
| R-3 | Small tiers judge badly | MEDIUM | per-tier numbers; owner Q5 decides a minimum tier |
| R-4 | Latency makes chat or grounded interpretation unusable on CPU | MEDIUM | UNMEASURED; owner Q4 bound; B is the fallback for the grounded route |
| R-5 | `is_valid=False` answers are still returned with metadata only (`api/assistant.py:871`, `:921-922`) | LOW | pre-existing, out of scope |
| R-6 | Dead LLM path `interpret_with_model` (`interpret.py:877`) calls llama directly (`:761`), bypassing the facade and any judge; template-interpretation safety failures only set flags (`interpret.py:238`, `:266`) | LOW | no product caller today (recurring-failures §10 in reverse: if anyone wires it, it ships unguarded); separate owner item |
| R-7 | A timed-out llama.cpp thread keeps running (`llama_cpp_provider.py:277-280`); concurrent requests share one unlocked model instance; the judge adds a second call per answer | MEDIUM | pre-existing; latency measurement (§6) on the owner's machine must include two concurrent requests |

## 9. Owner questions (not decided here)

1. **Q1. Which layer?** A. C, local answer check, floor kept, ships only if it meets Q5 (recommended). B. Remove model prose (option B). C. Embedding classifier (D). D. Build both C and D and pick by S5 and R numbers (about twice the work).
2. **Q2. When the check cannot run** (timeout, error, bad label): fail closed (recommended) or floor only?
3. **Q3. External-runner users** with no local model: fail closed, floor only, or require a local model to enable external runners?
4. **Q4. Latency bound** for the added check (seconds, p95, on your machine), and the timeout value.
5. **Q5. Targets:** system recall (85 % again?), how many added false positives on S5 must-allow, and the minimum tier the check must pass on.
6. **Q6. Sealed set S5 and labels for R:** who writes S5 (you; an agent with no repo access, as round 2; Codex read-only) and who labels R. Recommended: an agent with no repo access writes S5, you hold it outside the repo; you settle R label disagreements.
7. **Q7. Block copy:** reuse `ESCALATE_TEMPLATE` for judge blocks and failures (recommended), or a new fixed "could not check this answer" template?
8. **Q8. Answers already stored** before the check ships (session history `api/assistant.py:436-439`, feedback export `api/feedback.py:375`): leave as they are, re-screen on read, or re-screen once at upgrade?

## 10. Execution outline (only after Q1-Q8)

1. Plan file under `docs/plans/` with the owner's answers verbatim; Codex plan review.
2. T1-T6 written and seen failing; `advice_judge.py`, the `rag.py` hook and `prohibited_reason` field, and the audit `reason` read in `api/assistant.py:891` and `api/interpretations.py:552`; T1-T7 green; full suite under flock.
3. Freeze commit (§6 step 1); S5 written and held; one measurement run per tier; R captured and labelled.
4. Numbers to the owner. Nothing ships to users until the owner signs the numbers.

Codex review of this plan: [`../../swarm-2026-09-27/reviews/PARA-1-R3-codex.txt`](../../swarm-2026-09-27/reviews/PARA-1-R3-codex.txt); dispositions in §11.

## 11. Codex review dispositions

Review: `codex exec -s read-only`, prompt [`PARA-1-R3-prompt.md`](../../swarm-2026-09-27/reviews/PARA-1-R3-prompt.md), verdict **REVISE**, 1 BLOCKER, 4 MAJOR. L1 re-opened every cited line before deciding.

| # | Finding | Disposition |
|---|---|---|
| 1 | BLOCKER: first-token parse accepts `ALLOW please`, contradicting T1 | **Accepted.** Whole-response exact match plus `finish_reason` check (§3 C "Parse") |
| 2 | MAJOR: bool result cannot audit block vs failure; routes hard-code `prohibited_pattern`; no runner injection, timeout or serialization policy | **Accepted.** Tri-state outcome, `prohibited_reason` field, `judge_runner` parameter, timeout and serialization text, R-7 |
| 3 | MAJOR: inventory misses visit-note LLM extraction and stored-answer replay; agent "quote-only" claim wrong | **Accepted.** §2 rows 4b, 4c; option A corrected; Q8 added |
| 4 | MAJOR: R captured after the judge hides blocked answers; no FP-rate denominator; agreement needs two passes | **Accepted.** Raw pre-judge capture, FP-rate row, two passes |
| 5a | MAJOR: Q1 offered "stop", against PARA-1-R3 | **Accepted.** Replaced by "build C and D, pick by numbers" |
| 5b | "already-installed" embedding claim; D overfitting is testable, not inherent | **Accepted.** §3 D reworded |
| 5c | Recommendation precedes measurement; compare C with D | **Partly accepted.** C is now conditional on targets fixed before S5. Building D only to compare is **rejected** as the default (about twice the work for an option with a structural stance problem); it stays available as Q1 option D |
| 5d | Pin SHAs for `hc-l0-docs` evidence | **Accepted.** `a08c427` and `7991d96` cited in the header and §1 |

No finding rejected outright.

Next action: owner answers Q1.
