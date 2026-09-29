# 13 — Consultation: what to integrate, in what order, and what to drop

Written 2026-09-09 against the ten tracks (`01`-`08`, `10`, `11`), the
synthesis in [`09-roadmap.md`](09-roadmap.md), and [`STATUS.md`](STATUS.md).
Every repo claim below was re-verified in this session with `grep`/`sed` on
branch `claude/healthcentral-agentic-research-r1n54x`; where a claim could not
be verified from this checkout it is marked **[unverified]** and treated as a
lead, not a finding. Nothing here was executed against a model: `llama_cpp` is
not importable in this environment (`ModuleNotFoundError`), so every inference
number in every track — and in this document — remains unmeasured on this
codebase.

This is a consultation, not a summary. Of the 113 table rows the ten tracks
produced (106 recommendation rows plus Track 7's seven specification-surface
rows; the roadmap's 128 also counted its "do not build" list), **19 survive**,
grouped into five phases. The rest are dropped with reasons, or were already
shipped, or were already rejected.

---

## 0. The recommendation, in plain sentences

Do not start with the LLM planner. Start with the four things that are
currently *wrong* and cost hours, not weeks: make the security gate fail
closed, wire `repo_hygiene_check.py` into CI, stop the agent path from
reporting a fabricated `faithfulness_score=1.0`, and delete the `harness.md`
claims about subagents and hooks that do not exist. Then build the one
backend change three tracks independently asked for — return `run_id`,
`terminal`, and per-sentence citations on `ChatResponse` — and the audit-log
read route, because those two are what let a patient *see* what the agent did.
Then add the trajectory-scoring axis to the eval harness, and write the eval
card for the gate that already exists.

Only after that, open the generative seam — and open it differently from
the roadmap. The roadmap's Wave 2 is an LLM *planner*. Verified today, that
buys a patient nothing they can see: `draft()` can only render five tool
outputs and explicitly leaves `retrieve_chunks`/`lookup_reference` "for later
stories" (`nodes/draft.py:12-19`), and `_default_planner` never calls either
tool (`grep retrieve_chunks\|lookup_reference nodes/plan.py` → no hits). A
smarter planner that reaches a tool the drafter cannot render produces the
same templated sentence — or an abstain. The cheaper, LLM-free move is to
extend the deterministic planner and drafter to those two tools first
(Track 1 row 8), measure how often the keyword planner still misses (the new
trajectory axis gives you that number), and let the measurement decide
whether an LLM planner is needed at all.

Drop MCP, the voice stack, the embedding swap, two-model routing, KV-state
caching, and every cosmetic frontend migration this year. Individually each
is defensible. Collectively they are two to three years of one person's time,
they compete with each other for the same quarter, and none can be evidenced
on this repo today.

---

## 1. Method, and what this document could and could not verify

**Read.** `STATUS.md`, `00-brief.md`, `09-roadmap.md`, all ten tracks (via ten
parallel readers, each returning the full recommendation table with row ids
and verbatim cost claims), `CLAUDE.md`, `AGENT.md`,
`docs/agentic/recurring-failures.md`.

**Verified in this session** (tool output seen, not inferred):

| Claim | Evidence |
|---|---|
| Agent graph is LLM-free | `grep -rn "ModelRunner\|model_runner\|generate_async" modules/agent/` → one docstring, `guardrails/redaction_gate.py:16` |
| Planner seam has no caller | `Planner = Callable[...]` at `nodes/plan.py:311`; `plan(..., planner=_default_planner)` :319; `grep -rn "planner=" --include=*.py` outside defs/tests → zero |
| `draft()` has no injection seam | `nodes/draft.py:262` signature `(question, run_log, ctx)`; `graph.py:219` calls it directly |
| Groundedness is positional | `guardrails/groundedness.py:51-52` — `citations[index] if index < len(citations)` |
| `draft` cannot render `retrieve_chunks`/`lookup_reference` | `nodes/draft.py:17-19` docstring; no `chunks`/`reference` handling in the body |
| Planner never reaches those two tools | `grep -n "retrieve_chunks\|lookup_reference" nodes/plan.py` → nothing |
| `reflect` already accepts chunks as grounding | `nodes/reflect.py:36` `output.get("chunks")` |
| Agent path fabricates verification | `api/assistant.py:641-648` — `verified_claims=len(citations)`, `failed_claims=0`, `faithfulness_score=1.0 if is_answer` |
| Agent exceptions fall back silently to legacy RAG | `api/assistant.py:774-780` `except Exception` |
| No constrained decoding anywhere | `grep -rn "grammar\|json_schema\|response_format" core modules` (non-comment) → zero |
| llama.cpp streaming is fake | `core/llm/llama_cpp_provider.py:297-302` yields the whole response as one chunk |
| `interpret.py` bypasses `ModelRunner` | `modules/interpret.py:761` → `self._model_selector.run_inference(...)`; `model_selector.py:538` calls the raw `Llama` object |
| Security gate fails open | `scripts/security_gate.py:44-51, 71-78` `return []` on missing/malformed report; `.github/workflows/ci.yml:92,95` `\|\| true`; no `test_security_gate.py` anywhere |
| `repo_hygiene_check.py` never runs in CI | `grep repo_hygiene .github/workflows/*.yml` → nothing; `CONTRIBUTING.md:75,187,196` say it does |
| `harness.md` describes a directory that does not exist | `docs/agentic/harness.md:25-30` names five subagents in `.claude/agents/`; `ls .claude/agents` → No such file; no `.claude/settings.json` anywhere |
| Memory audit logging **has** shipped | `api/memory.py:21` imports `audit_and_commit`; five call sites :129,159,196,243,288 (commit `2c98ae6`) |
| Answer-cache fix **has** shipped | `api/assistant.py:553-556` docstring, fingerprint of verified observations and documents |
| Pin and mid tier **have** shipped | `requirements.txt:72` `llama-cpp-python==0.3.35`; `model_selector.py:101-110` Phi-4-mini, 16384 ctx |
| Golden set is 74 cases with only `terminal`/`min_citations`/`advice_leakage` expectations | `ls tests/agent/golden/*.json \| wc -l` → 74; `expect` field census shows no `tool_sequence` |
| No audit read route | `grep AuditLog api/*.py` → only `api/profiles.py:909` (delete on profile purge) |
| `get_correlation_id` unused outside `monitoring/` | `grep -rn get_correlation_id` → `monitoring/correlation.py:19`, `monitoring/__init__.py` only |
| Dictation uses the browser's cloud speech service | `hooks/useSpeechRecognition.ts:2,23` wraps `window.SpeechRecognition` |
| `CitationTooltip` exists but only in `lab-interpreter/` | `grep -rln CitationTooltip src/frontend/src` → 4 files, none under `pages/ExplainAssistant.tsx` |
| Two drifted trend charts, same bare `800` | `TrendsDashboard.tsx:486`, `InterpretedTrendChart.tsx:165` |
| Exports are in-process dicts | `api/export.py:43-49` `_summary_store`, `_packet_store`, `_fhir_store` |
| Observations have page-level provenance only | `models/observation.py:92` `source_bbox_json`; `char_start`/`char_end` exist only on `models/document_category.py:46-47` |
| `test_backup_api.py` never uses `route_client` | `grep -c route_client` → 0 there, 8 in `test_backup_routes.py` |
| Tier capability disclosure shipped | `model_selector.py:827 get_tier_capabilities`; `components/settings/TierCapabilities.tsx` |

**Could not verify here:** any tok/s, latency or RAM figure; whether
`llama-cpp-python==0.3.35`'s `response_format` schema path actually constrains
on the Phi-4-mini GGUF (STATUS says it was checked against the tag, not run);
the Track 8 brand-guideline line "Smooth number transitions" (`grep` of
`docs/brand/brand-guidelines.md` finds no such phrase — **[unverified]**, the
phrase may have been paraphrased); every post-May-2026 external release claim.

---

## 2. The candidate matrix

| Track | Rows | Shipped/rejected since | Kept | Dropped | Notes |
|---|---|---|---|---|---|
| T1 audit | 8 | — | 3 (R7 audit route, R8 planner reach, and R2's *constraint* not its proposal) | 5 | R1/R3/R5/R6 are designs for a model call that does not exist |
| T2 serving | 13 | R3 pin shipped | 3 (R2 fallback, R6 prohibition, R9 non-change) | 10 | R1/R4/R5/R7/R8 all wait on a generative node; R10-R13 are "don't"s I agree with |
| T3 loops | 14 | R8 shipped, R9 **rejected** | 5 (R1, R5, R11, R12, R13) | 9 | R2/R4/R14 deferred behind measurement |
| T4 MCP | 8 | — | 1 (R7, the documented "don't") | 7 | R1-R5 drop as a bundle; R6 deferred |
| T5 models | 12 | R3 and R6 shipped | 3 (R1, R9, R12 as "don't"s; R4 as policy) | 8 | R7 replaced by a disclosure fix; R5/R8/R10 dropped |
| T6 landscape | 6 | — | 2 (R1 merges into abstain cards; R5 "don't") | 4 | R3 partially shipped as capability disclosure |
| T7 data control | 14 + 7 | R2, R3 shipped | 3 (R1, R7, R6-after-T10-R6) | 11 + 7 | R10/R11 kept only as doc lines; R12 is counsel, not code |
| T8 frontend | 13 | — | 4 (R1, R2, R4, R9) | 9 | R5 cost understated; R3 deferred; R6/R10-R13 cosmetic |
| T10 artifact | 7 | — | 2 (R2 correction, R6 eval card) | 5 | R3/R4/R7 are high-rot prose |
| T11 harness | 11 | — | 4 (R1, R3, R4, R11) | 7 | R2 optional; R5-R7 build nothing |
| **Total** | **113** | 8 | **19 distinct survivors** (after merging duplicates) | | |

Survivors are fewer than "kept" rows because several rows are the same item
in different words (§3.1).

---

## 3. What the isolated tracks could not see

### 3.1 Same thing, different words (merged)

| Item | Proposed by | Merged as |
|---|---|---|
| Audit-log read route | T1-R7, T7-R1, T7 spec "audit timeline", roadmap 1.3 | **C4** |
| Return `run_id`/`terminal`/per-sentence citations | T1 (§summary), T3 (§5), T8-R1/R2, roadmap 1.4 | **C3** |
| Make abstention legible | T6-R1, T8-R1 abstain/escalate cards, roadmap 3.1 | **C3b** (same PR as C3) |
| LLM planner behind constrained decoding with deterministic fallback | T1-R1, T2-R1/R2, T3-R1/R2/R4, T5-R4, roadmap 2.1-2.5 | **C11** (deferred, and reshaped — §3.4) |
| Constrained decoding in both providers | T1-R3, T2-R1/R4, T3-R4 | folded into C11 |
| KV/prefix reuse | T1-R6, T2-R5/R7, roadmap 2.7 | dropped (§5) |
| Per-node model routing | T1-R5, T2-R8 | dropped (§5) |
| Correct the CS4610 claims the repo cannot evidence | T10-R2, T11-R1 | **C2** |
| Eval card | T7-R6 (HC-M06 extraction card), T10-R6 (card for the *existing* agent gate) | **C7** does T10-R6 first; HC-M06 follows as **C13** |
| Provenance "where did this number come from" | T7-R4 (backend span columns), T8-R8 (UI panel over page images) | T8-R8 kept as **C10**; T7-R4 deferred |
| Show tier reasoning | T6-R3 | already half-shipped as `get_tier_capabilities` (`13b1466`); remainder folded into C10's settings work, not a separate item |
| Memory-route hardening | T3-R8/R9, T7-R3 | shipped / rejected — nothing left |

### 3.2 Opposite things

**Constrained-decoding cost (T2 vs T3).** T2: "roughly 60-78% fewer tok/s"
but "the payload is ~20-80 tokens, so the absolute cost is small." T3:
"3.6x-8.2x slower" and "budget it explicitly." They are not actually
contradictory — one is a per-token multiplier, the other is the same
multiplier applied to a short span — but *both* are wrong about what matters
here. On a CPU-only tier decoding at tens of tok/s (T2's own figure), an
8x multiplier on a 60-token `PlanDecision` is ~15 s per plan turn, and the
loop is bounded at `MAX_STEPS = 5` (`state.py:19`). A grammar-constrained LLM
planner could add a minute to a question. That is not "negligible" and it is
not "a budget item"; it is a reason the planner must be turn-1-only (T3's
own gate) and a reason to measure before committing. Neither track measured
on this codebase, and this environment cannot either. **Resolution:** the
measurement is a deliverable (C11a), not a footnote.

**"Build the harness claims" vs "delete them" (T10-R2 vs T11-R1/R5/R7).**
T10 offers "build for real or correct"; T11 leans toward building one
subagent and a dev-time PHI hook. Given `recurring-failures.md` #8 and one
maintainer, **delete the claims**. A hook is "not a security boundary" by
Anthropic's own docs (T11's finding) and the product already has the real
guarantee in `core/llm/ollama_provider.py:40` and `modules/redaction.py`.
Building the thing the report falsely described, to make the report true
retroactively, is narrative-ahead-of-evidence in reverse.

**MCP "Now" (T4-R1 phase) vs local-first.** T4 marks the MCP router as
"Now — closes brief gap #6." The brief lists gap #6, but `CLAUDE.md` lists
"no network calls in product code paths" as a hard invariant. T4 itself
concedes MCP is "the only new PHI egress path this cycle" and bundles a new
token type in `core/auth.py` (ask-first territory). No patient asked for it;
no client exists to consume it. **Dropped**, not deferred (§5).

**SMART Health Links (T4-R6) — "first outbound network call from product
code."** T4 is honest that this breaks the invariant and asks for sign-off.
Roadmap 4.3 accepted it. I would not accept it this year: it is the one item
that turns "no network calls" from a grep-verifiable property
(`_assert_localhost`) into a policy with a carve-out. Defer until a patient
actually presents an SHL; the import path (`import_structured.py:338
parse_fhir_bundle`) already accepts the decrypted bundle as a file.

**Voice: PRD vs invariant (T5-R7).** The shipped dictation feature sends
audio to the browser vendor's cloud (`useSpeechRecognition.ts:2`). The PRD
listed offline recognition as a non-goal; `CLAUDE.md` says no network in
product paths. T5's answer is whisper.cpp at "High" cost with Windows
packaging. The conservative answer is cheaper and lands this month: label it
honestly and default it off (**C9**). whisper.cpp is dropped for the cycle.

**Live step tray (T8-R5 vs roadmap 3.3).** T8 rates it "Medium-High: real
backend work to expose in-flight state." Roadmap 3.3 lists it as a Wave 3
UI item gated only on 1.4. 1.4 returns a *finished* `RunLog`; in-flight state
needs a streaming or polling surface that does not exist, and the default
provider's `generate_stream` is fake (`llama_cpp_provider.py:297-302`).
Render the **post-hoc** trace (C3 gives you the data) and drop the live one.

### 3.3 Cheap only if something else lands first

| Item | Cheap after | Why |
|---|---|---|
| Distinct abstain/escalate cards (T8-R1, T6-R1) | C3 (`terminal` on the wire) | Today the frontend infers "uncertainty" by string-matching `'knowledge base only'` (`ExplainAssistant.tsx:332`) |
| Inline `CitationTooltip` (T8-R2) | C3 (`sentences[]` parallel to `citations[]`) | The pairing exists in `Draft` (`draft.py:271-301`) and dies at `assistant.py:637` |
| Historical run view (T8-R7, roadmap 3.4) | C4 audit route **and** C3 | Needs both the rows and a `run_id` to group them |
| Tool-selection scorer axis (T3-R11) | nothing — but **everything generative is cheap only after it** | It is the only instrument that can tell you an LLM planner improved trajectories rather than terminals |
| HC-M06 extraction eval card (T7-R6) | C7 (card for the existing gate) | T10's argument: get the card format right on the gate that already computes its numbers before building a new gate |
| Any LLM planner (C11) | C8 (deterministic reach to `retrieve_chunks`/`lookup_reference`) and C6 (trajectory axis) | Otherwise the planner's new decisions land on a drafter that cannot render them |
| Constrained decoding (T2-R1) | a generative node existing | T2's own "blocked by" column says so |
| KV prefix reuse (T2-R5) | a generative node with a stable prefix | same |

### 3.4 The generative seam: where the roadmap has the order backwards

The roadmap calls Wave 2 "the actual thesis." Reading the code rather than
the tracks, the planner is the wrong first generative node, for three
verified reasons:

1. **A better planner cannot be seen.** `draft()` renders exactly five
   output shapes — trend, observation row, care task, med change, timeline
   (`draft.py:271-301`) — and its own docstring defers `retrieve_chunks` and
   `lookup_reference` "for later stories" (`draft.py:17-19`). The keyword
   planner never selects either tool. So the only questions an LLM planner
   would newly route are exactly the ones the drafter cannot answer. The
   patient sees a templated sentence or an abstain either way.
2. **Groundedness is positional.** `groundedness.py:51-52` pairs sentence
   *i* with citation *i*. That contract is why the guard is trustworthy and
   why an LLM *drafter* emitting free prose would fail every sentence. Any
   generative drafter has to be sentence-at-a-time, each output bound to
   one input citation, with the deterministic sentence as fallback when a
   lexical check (value, unit, date verbatim) fails. That is a design the
   tracks did not write, and it is the one that changes what a patient reads.
3. **The instrument to justify the planner does not exist yet.** The
   golden set expects only `terminal`, `min_citations`, `advice_leakage`
   (census of all 74 `expect` blocks). Nothing scores which tool was chosen.
   Ship T3-R11 first and you get the keyword planner's miss rate for free —
   if it is low, the LLM planner is a cost with no benefit.

So the order inside the seam becomes: **C8** (deterministic reach, no LLM)
→ **C6** (trajectory axis) → measure → **C11** (constrained LLM planner,
turn-1, mid/high only, *if* the miss rate justifies it) → **C12** (per-sentence
LLM explainer, the node that actually changes the answer text). The roadmap
has C11 before C8 and does not have C12 or the measurement at all.

### 3.5 Individually sensible, collectively unaffordable

Roadmap Wave 4 says "sequence by appetite." Using the tracks' own effort
labels: whisper.cpp **High**; Qwen3-Embedding **Medium-High** plus a
re-embed migration; MCP router+tokens+allowlist+budget **M+M+S+S** plus a
`core/auth.py` change; SHL resolver **M**; Kokoro **M**; HC-M06 **L**;
`TrendChart` consolidation **M**; motion tokens **M**; live step tray
**M-H**; Tailwind v4 "one to two days"; React 19 **High**. Add Wave 2's
seven items. That is well over a year of one maintainer's evenings, before
maintenance — and the embedding swap, the voice stack and MCP each add a
native or network dependency the repo must then keep working on Windows.
Only the items in §4 survive that arithmetic.

---

## 4. Recommended integrations, in order

Each survivor is judged on the four things asked: **patient** (what changes
for a patient), **cost** (build and keep), **blast** (what breaks if wrong),
**evidence** (whether this repo can demonstrate it working). Effort labels
are mine, calibrated against each other, not against any track's scale.

### Phase A — Things that are wrong today (days)

| # | Item | Source | Patient | Cost | Blast | Evidence |
|---|---|---|---|---|---|---|
| **C1** | Security gate fails closed: missing/malformed report → exit 2 (already documented at `security_gate.py:11`, never returned); drop `\|\| true` at `ci.yml:92,95` or capture exit codes; wire `repo_hygiene_check.py` into the docs-lint job; add `tests/test_security_gate.py` that deletes the report and asserts RED | T11-R3, R4; STATUS | Indirect — a scanner that crashes no longer ships green | XS | If wrong, CI goes red on a scanner hiccup — the correct failure direction | Yes: the test *is* the recheck in `recurring-failures.md` #1 |
| **C2** | Delete or correct claims the repo cannot evidence: `harness.md:25-30` subagent list, the PreToolUse-hook description in `docs/agentic/`, the `AGILE_PLAN.md:50,53` links, the OpenWiki present tense in `CLAUDE.md`; add `CS4610_Report_Demo/README.md` stating which report claims are aspirational; gitignore and delete the two lock files | T10-R1, R2; T11-R1 | None directly; prevents the next agent from "implementing" a fiction | S (docs) | None | Yes: `ls .claude/agents` after; `docs_lint.py` |
| **C2b** | Optional: `scripts/harness_drift_check.py` — for each path/script/CI-step a `docs/agentic/*.md` file names, assert it exists | T11-R2 | None | S | A false positive blocks docs-lint until the doc is fixed — acceptable | Yes: it would have caught both T11 gaps on the first run |

Reasoning: these are `recurring-failures.md` #1 and #8 instances found *after*
the roadmap was written, so the roadmap's Wave 0 is incomplete. They cost
hours and remove two ways the project can currently lie to itself.

### Phase B — Let the patient see what the agent did (weeks)

| # | Item | Source | Patient | Cost | Blast | Evidence |
|---|---|---|---|---|---|---|
| **C3** | `ChatResponse` gains `run_id`, `terminal`, `sentences: list[str]`, `citations` parallel to sentences — and **`VerificationInfo` on the agent path stops being fabricated**: replace `faithfulness_score=1.0 / failed_claims=0` (`assistant.py:641-648`) with fields derived from the guard's `MappingResult` (`surviving`/`dropped` counts) and a `summary` that says `agent:groundedness` rather than implying `faithfulness.py` ran | T1, T3, T8-R1/R2; roadmap 1.4; **new: the fabricated score** | Sees *which* sentence came from *which* result; sees an honest "N of M sentences kept" instead of a made-up 1.0 | S backend, S-M frontend | Wire-format change; frontend must tolerate absent fields for the legacy path | Yes: golden cases already exercise `Draft`; a route test through `route_client` asserting the new fields |
| **C3b** | Distinct abstain / escalate cards, rendered as trustworthy outcomes with "what I checked" (the `RunLog` tool names from C3) and one next step; wire the existing `CitationTooltip` inline per sentence | T8-R1/R2, T6-R1; roadmap 3.1/3.2 | The single biggest legibility change available: abstention stops looking like failure | S-M frontend | Cosmetic if wrong | Yes: vitest on the two card branches; e2e `assistant.spec.ts` category grep already exists (`CONTRIBUTING.md:196`) |
| **C4** | `GET /audit-log` — paginated, filterable by date/event_type/entity_type/`run_id`, reads only `ALLOWED_DETAIL_KEYS` (`core/audit.py:86-106`), with a phrase-table translator | T1-R7, T7-R1; roadmap 1.3 | "What did this app do with my data?" becomes answerable in-product | S backend, S frontend | If the allowlist is not re-applied on read, PHI-adjacent details leak to the UI — apply the same allowlist | Yes: route test via `route_client` including cross-profile 404 (pattern from `aec2a56`) |
| **C5** | Wire `get_correlation_id()` into the log formatter and `create_audit_log` | T7-R7; roadmap 1.5 | None visible; makes C4 rows joinable to logs | XS | None | Yes: one unit test on the formatter |

### Phase C — Instrument before generating (weeks)

| # | Item | Source | Patient | Cost | Blast | Evidence |
|---|---|---|---|---|---|---|
| **C6** | `expect.tool_sequence` (or `first_tool`) on golden cases + a **tool-selection** scorer axis; step-count and per-node timing aggregation in `ScoreReport` (timing already recorded at `graph.py:64-74`) | T3-R11, R12; roadmap 1.1/1.2 | None directly; it is the instrument every later item is judged by | M (74 cases to backfill) | A wrong expectation fails CI until corrected — good | Yes by construction |
| **C7** | `docs/agentic/eval-cards/agent-gate.md` — numbers generated from `agent_eval_gate.py` output, human-written "not covered" section (extraction, retrieval, trajectory until C6) | T10-R6 | None; but it is the first repo artifact where narrative cannot outrun evidence | S-M | Rots if numbers are hand-typed — generate them | Yes: the generator is the test |

### Phase D — The generative seam, reshaped (a quarter)

| # | Item | Source | Patient | Cost | Blast | Evidence |
|---|---|---|---|---|---|---|
| **C8** | **Deterministic** planner reach to `lookup_reference` (analyte questions with no verified rows) and `retrieve_chunks` (free-text questions), plus the two missing `draft` branches; `reflect` already treats `chunks` as grounding (`reflect.py:36`) | T1-R8 | General questions ("what is TSH?") get a cited reference sentence instead of an abstain; document questions get a cited excerpt | M | `retrieve_chunks` is the highest-injection-risk tool (T4's finding); the guard's positional mapping still applies, and `injection_resistance` golden cases must be extended | Yes: new golden cases with `tool_sequence` (C6) |
| **C9** | Dictation disclosure: default `voice_logging_enabled`-style flag off, a one-line "audio is processed by your browser's speech service, which may be cloud-based" in the modal that already exists (`VoiceSettingsResponse.voice_modal_seen`) | replaces T5-R7 | Honest about the one path where data leaves the device | XS | None | Yes: vitest on the modal copy and default |
| **C10** | Reuse `PageImageOverlay` as a provenance panel from trend points and interpreted-result cards; accessible `<details>` table under the trends chart | T8-R8, R4; roadmap 3.5/3.7 | "Where did this number come from" from every place a number appears; screen-reader parity | S-M | Cosmetic | Yes: vitest; existing `ResponsiveLayout`/a11y test patterns |
| **C11a** | **Measure** constrained decoding on the owner's Windows machine: one script, one tier, one `PlanDecision` schema, unconstrained vs `response_format` schema, tok/s and wall-clock per plan turn. Record in the eval card | T2 §2 vs T3 — the unresolved order-of-magnitude disagreement | None; it decides C11 | S | None | This *is* the evidence |
| **C11** | LLM planner — *only if* C6 shows the keyword planner's miss rate is material and C11a shows a plan turn under ~3 s: async `Planner` (T3-R1), compressed tool menu from `registry` (T3-R3), schema-constrained decoding with post-hoc `model_validate_json` and fallback to `_default_planner` on any failure (T2-R2), turn-1 only, mid/high only (T5-R4), tool outputs sanitized before entering planner context (T3-R14) | T1-R1, T2-R1/R2, T3-R1/R2/R3/R4/R14, T5-R4; roadmap 2.1-2.6 | Questions the keyword planner misses reach the right tool | M-L | New untrusted-output source; mitigated by `registry.validate_args` and the fallback | Yes, *if* C6 exists: the trajectory axis is the acceptance test |
| **C12** | Per-sentence LLM explainer between `draft` and `guard`: for each grounded sentence, ask the model to restate it in plain language *without changing* value/unit/date/analyte; accept only if those tokens survive verbatim, else keep the template sentence; citations list unchanged so `map_sentences` still pairs positionally | new — the node no track designed but T1-R2's "1:1 alignment" constraint demands | The first change a patient can *read*: "Your LDL was 160 mg/dL on 2026-03-01" becomes a sentence a person would say — with the same citation | L | A paraphrase that alters meaning while preserving tokens; mitigate with `advice_leakage` and `classifier` on the paraphrase, and keep the template as the audit-replayable form | Partially: golden cases can assert token preservation and terminal; wording quality needs the user study (C14) |

**Sequencing rule inside Phase D:** C8 → C6 already done → C11a → decide C11
→ C12. C11 may legitimately be skipped; C12 may not, if the product is ever to
stop being a template engine.

### Phase E — Reach, with a ceiling of two (next quarter)

| # | Item | Source | Patient | Cost | Blast | Evidence |
|---|---|---|---|---|---|---|
| **C13** | HC-M06 extraction eval card, in the C7 format, synthetic golden PDFs, CI gate on the two easy tiers only | T7-R6; roadmap 4.1; `feature_list.json` HC-M06 pending | Extraction accuracy becomes a number, not a claim | L | None | Yes by construction |
| **C14** | Abstention-tolerance user study with the PRD's health-anxiety persona, using C3b's cards | T6-R2 | Tells you whether the core safety bet survives contact with a person | S (not engineering) | None | Outside the repo; record results in `docs/plans/` |
| **C15** | Compliance doc lines for FTC HBNR, EU AI Act Art. 50, MHMDA — and the FDA patient-facing CDS carve-out routed to counsel before any "not a device" copy | T7-R10/R11/R12; roadmap 4.8 | Honest docs | S (docs) | Asserting non-device status wrongly is the one real regulatory exposure — counsel, not code | Docs only |
| **C16** | Route `interpret.py:761` through `ModelRunner`; retire `model_selector.run_inference` as a public call shape | new — a `CLAUDE.md` hard-invariant violation the tracks did not flag | None visible; one call shape before any generative node multiplies them | S-M | Interpret path regresses — covered by existing interpret tests | Yes: existing tests plus a grep-based test that no module imports `Llama` outside `core/llm/` |

Explicitly **not** in Phase E, even though the roadmap put them there: SHL
resolver, MCP, whisper, Kokoro, embedding swap, `TrendChart` consolidation.
Reasons in §5.

---

## 5. Dropped, and why

Grouped by reason. "Competes with X" means the same maintainer-month.

### 5.1 Designs for a model call that does not exist (defer until C11/C12 exist; do not schedule)

| Item | Source | Why |
|---|---|---|
| Native JSON-schema grammar per tool at startup | T1-R3, T2-R1; roadmap 2.3 | Folded into C11 if C11 happens; nothing to constrain before then. STATUS's "0.3.2 exposes the hook" was checked against a tag, never executed — **[unverified]** on this repo |
| Ollama `format` mirror | T2-R4; roadmap 2.6 | Same; and Ollama is the non-default provider |
| Stable-prefix prompt construction | T2-R5; roadmap 2.7 | No prompt exists on the agent path to structure |
| In-RAM `LlamaState` cache | T2-R7 | T2's own "quantify the realistic win" says the win is modest at `MAX_STEPS=5`; adds PHI-derived state in a second in-process store |
| Two-model routing | T1-R5, T2-R8 | Needs a second resident provider slot (`factory.py`), ~350 MB-1.5 GB more RAM on tiers already at floor; nothing to route |
| Per-request tier routing | T1-R5 | Same |
| Real llama.cpp streaming | T1-R4 | Only matters once there is a generative node worth streaming; and C3b's post-hoc trace covers the "is it doing anything" anxiety |
| Sanitize tool output into planner context | T3-R14 | Correct, and part of C11's definition — not separately schedulable |
| `_has_grounding` row-count/topic signal | T3-R6 | Guard-adjacent, small benefit, no failing case motivates it. Revisit if C6 shows unnecessary loops |

### 5.2 New egress, new dependency, or both

| Item | Source | Why |
|---|---|---|
| MCP HTTP router + scoped tokens + Origin allowlist + call budget + `retrieve_chunks` opt-in | T4-R1-R5, R8; roadmap 4.4 | Five rows that are one feature. New PHI egress, a new token type in `core/auth.py` (ask-first), a spec-version bet, and no consumer. T4 rated it "Now"; nothing in the patient's workflow needs it. Keep T4-R7's *documented decision* pattern: record "no MCP until a concrete client exists" in `docs/plans/` |
| SMART Health Link resolver | T4-R6; roadmap 4.3 | The first outbound network call from product code. Defer until a patient presents one; the file-import path already exists |
| whisper.cpp ASR | T5-R7; roadmap 4.5 | "High" with a native binary and Windows model packaging; T5's own WER figures show generic Whisper is poor on drug/analyte vocabulary (25.3% vs 4.6% reported). C9 closes the honesty gap for XS |
| Kokoro TTS | T5-R8; roadmap 4.6 | Real accessibility motivation, but a ~327 MB dependency for a feature no eval can score and no patient has asked for. Competes with C12 for the quarter |
| Qwen3-Embedding-0.6B | T5-R5; roadmap 4.7 | Re-embed migration for every profile vault, ~1.2-1.5 GB more on disk, and it collides head-on with `test_api_rag_index_002b`'s 0.7 threshold, which must not move. The retrieval quality problem is unmeasured; C13's sibling (a retrieval eval) should exist before the model changes |
| BioMistral high-tier swap | T5-R10 | Agree it is stale; but the high tier has never been evidenced loading at all (STATUS). Swap after a first local run of each tier, not before |
| Unsloth dynamic quant check | T2-R13 | Fine as a checklist line in `docs/model_tiers/`; not a work item |
| Bug-report bundler | T7-R9 | New export-shaped path through `RedactionEngine(strict)` — every export path is an invariant surface. No support channel exists to send it to |

### 5.3 Cosmetic, or cost without patient-visible change

| Item | Source | Why |
|---|---|---|
| Motion token table across 23 files | T8-R6 | Touches every animated component for consistency no patient will notice |
| `motion/react` rename | T8-R11 | Mechanical churn |
| CSS View Transitions spike | T8-R10 | A spike to remove a dependency that is not causing a problem |
| Tailwind v4, React 19 | T8-R12/R13; roadmap "don't" list | Agree with the roadmap: ~92 files, zero product payoff on a localhost build |
| `TrendChart` consolidation | T8-R3; roadmap 3.6 | Real drift (both hardcode `800`), but a careful M-sized refactor of the two most-tested pages for a shaded band. Do it when one of them next needs a real change |
| Live in-flight step tray | T8-R5; roadmap 3.3 | Cost understated (§3.2); post-hoc trace in C3b covers the need |
| Historical run view reusing the step tray | T8-R7; roadmap 3.4 | Cheap *after* C3 and C4; not worth its own line until both exist and a patient opens the audit page |
| Durable export stores | T7-R5 | Correct observation (`api/export.py:43-49`), but exports are regenerable and the fix belongs in the vault, a profile migration — schedule with the next profile-schema change, not alone |
| `char_start`/`char_end` on `Observation` | T7-R4; roadmap 4.2 | Requires a profile migration plus re-extraction to populate; C10 gives the page-level "where from" today |
| Granular deletion, data inventory, audit export | T7 spec rows | Data inventory is C4 plus a count query; the others are follow-ons once C4 has users |
| Diagnostics settings panel | T7-R8; roadmap 3.8 | The endpoint exists (`main.py:154` mounts `/api/v1/monitoring/metrics`; agent nodes already report into it, `modules/agent/metrics.py:3-4`), so this is buildable and cheap — but it shows p50/p95 latencies to a patient who has no action to take on them. Fold a one-line "last answer took N s" into C3b's trace instead of a panel |
| Doctor-export "share with care team" | T6-R6 | Scope-creep magnet by T6's own admission |
| Sharpen cross-silo positioning | T6-R4 | Messaging, not code; agree, no work item |

### 5.4 Documentation that will rot

| Item | Source | Why |
|---|---|---|
| Retroactive `docs/adr/` | T10-R3 | T10 itself rates it "high rot risk if treated as one-time backfill"; the domain-modeling skill has existed eight months unused |
| `harness-history.md` | T10-R4 | Same shape; C2 records what is false today, which is the part that matters |
| "How this was built" narrative | T10-R7 | T10 says build last, after R4/R6. R4 is dropped; write it never, or when someone asks |
| Self-maintaining `progress.md` template | T10-R5 | Reasonable, but the honest fix is C7's generated numbers; a second prose log will go silent the way the first did (48 commits, STATUS) |
| RED/GREEN fields in `feature_list.json` | T11-R8 | Metric with no consumer; T11-R9 (measure passively first) is the better version of the same idea and needs no code |
| One real subagent, dev-time PHI hook | T11-R5, R7 | Build nothing to make a report true. If a cheap-model scanner earns its keep in practice, add the file then |
| Branch-protection check | T11-R11 | Do it — it is a settings page, not a repo change. Not a work item |

### 5.5 Already done or already rejected (tracks are stale here)

Memory audit (T3-R8, T7-R3), cache staleness (T7-R2), pin (T2-R3), mid tier
(T5-R3), dead embeddings config (T5-R6), Gemma repo verification (T5-R2 →
`download_models.py verify`) — all shipped per STATUS and re-verified above.
T3-R9 (sanitize memory on write) is **rejected** and must stay rejected: the
reasoning in STATUS is correct and was re-checked (`rag.py::_retrieve_memory_context`
filters at compose time; strict redaction on write is irreversible).

### 5.6 "Don't"s I am keeping as documented decisions

T2-R6 (never `LlamaDiskCache` — add the comment at the provider constructor),
T2-R9/T3-R5 (guard and reflect stay non-LLM), T3-R13 (no LLM judge on the
safety axes), T2-R10/R11/R12, T5-R1/R9/R12, T6-R5, T7-R13/R14, T4-R7,
T11-R6/R10. These cost nothing and the roadmap's §4 table already holds most
of them. Two additions: **no on-disk KV state** should become a grep-shaped
CI rule (one line in `docs_lint.py` or C2b), and **no MCP until a client
exists** joins the list.

---

## 6. Where `09-roadmap.md` has it wrong

1. **Wave 0 is incomplete.** It predates T10/T11. The fail-open security gate
   and the never-run hygiene check are defects of the same class as the
   memory audit gap, and cheaper. They belong at the top, not in a status note.
2. **Wave 1.4 ships a fabricated number to a new UI.** "Stop discarding
   computed data" is right, but `_agent_terminal_to_response_parts` also
   *invents* `faithfulness_score=1.0` and `failed_claims=0`
   (`assistant.py:641-648`). Any UI built on 1.4 renders that as a trust
   signal. C3 fixes both in one change; the roadmap fixes only the first.
3. **Wave 2 is in the wrong order and missing its instrument.** The LLM
   planner (2.1-2.6) precedes any way to see a trajectory improve (1.1 is
   listed in Wave 1 but nothing gates 2.5 on its result) and precedes the
   deterministic reach that would make a planner's new choices renderable
   (T1-R8 does not appear in the roadmap at all). See §3.4.
4. **The node that changes the answer is not in the roadmap.** No wave
   contains an LLM drafter or explainer. The roadmap's own §1 quotes
   `draft.py:44-46`'s parallel `sentences`/`citations`, which is exactly the
   contract a per-sentence explainer (C12) can honor. Without it, every wave
   leaves the patient reading f-strings.
5. **Wave 3.3 is mispriced** (§3.2): "live step tray" requires an in-flight
   surface and real streaming; neither exists.
6. **Wave 4.1 should be preceded by an eval card for the gate that already
   exists** (T10-R6, written after the roadmap). Get the format right where
   the numbers are already computed.
7. **"Sequence Wave 4 by appetite" is the collectively-unaffordable trap.**
   Eight independent M-to-High items for one maintainer is not a wave; it is
   a backlog. Cap it at two per quarter and name them (C13, C14).
8. **Wave 4.3 (SHL) and 4.4 (MCP) each convert a grep-verifiable invariant
   into a policy.** The roadmap accepts 4.3 with T4's carve-out language and
   4.4 as "off by default." Off-by-default network paths are still network
   paths in product code. Both should be documented decisions *not* to build
   until a concrete patient need appears.
9. **Two invariant violations the tracks missed are absent:** `interpret.py:761`
   calls the raw `Llama` object via `model_selector.run_inference`, bypassing
   `ModelRunner` (`CLAUDE.md` §3 says every LLM call goes through it) — C16;
   and the legacy RAG path's citation dialects disagree with each other
   (`rag.py:126` asks for `[cite:N]`, :128/:133-134 also ask for
   `[YOUR_RESULTS:N]`/`[REFERENCE:N]`, `validate_response` :819 parses only
   `[cite:N]`, and `is_valid` reaches the client at :873 without blocking
   anything). The roadmap keeps the legacy path as a one-release fallback;
   the fallback is also the thing every agent exception lands on
   (`assistant.py:774`). Either fix its validator or make the fallback a
   templated abstain — do not leave the silent path as the least-checked one.
10. **§6 is right that no effort estimate is calibrated**, and the roadmap
    then sequences by them anyway. Phase labels in §4 above are calibrated
    against each other by one reader; treat them the same way.

---

## 7. Decisions only the owner can make

- **C11 vs skipping it.** If C6 shows the keyword planner misses under
  ~10% of golden and real questions, do not build the LLM planner this year;
  spend the quarter on C12.
- **C12's paraphrase policy.** A per-sentence explainer is the first place
  the product's voice stops being fixed strings. It must pass `classifier`
  and `advice_leakage`; the question of whether the *template* or the
  *paraphrase* is the audit-replayable form (`graph.py:235-304 replay`)
  needs an answer before code.
- **C9's default.** Turning dictation off by default is a product change to
  a shipped feature; the alternative is disclosure-only.
- **FDA posture (C15).** Counsel, before any "not a medical device" copy.
- **Ask-first files.** Nothing in §4 touches `interpret_safety.py`,
  `redaction.py`, `faithfulness.py`, `verifier_agent.py`, or auth/encryption.
  C3 *stops implying* `faithfulness.py` ran on the agent path; it does not
  call it. C16 touches `interpret.py`, which is adjacent to
  `interpret_safety.py` — flagging, not asking, since the safety module is
  untouched.

---

## 8. What this consultation cannot tell you

- Any latency, RAM or throughput figure. `llama_cpp` does not import here;
  C11a exists because of that.
- Whether `response_format` with a schema constrains on Phi-4-mini under
  0.3.35. STATUS checked source at a tag; nobody has run it.
- Whether Track 8's brand-guideline quotation exists verbatim.
- How a patient reacts to an abstain card. That is C14, and it is the
  cheapest item on this list with the largest unknown behind it.
