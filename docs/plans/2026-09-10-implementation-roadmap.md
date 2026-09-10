# Implementation roadmap — accepted 2026-09-10

Derived from the Fable 5.1 consultation
([`docs/research/2026-09-08/13-consultation.md`](../research/2026-09-08/13-consultation.md)),
which worked the ~113 candidate rows the ten Sonnet tracks produced and kept 19.
This document turns that verdict into work: each item gets an entry point, a
first failing test, and a done condition.

**This supersedes [`09-roadmap.md`](../research/2026-09-08/09-roadmap.md)'s
wave ordering.** That synthesis was written from the tracks alone; the
consultation read the code and found the ordering wrong in ways §6 of that
document sets out. Where the two disagree, this file wins.

## Verification pass

The consultation is a lead, not a finding — the same bar every Sonnet track was
held to, and the bar this repo's own frontier-audit rules set. Eight
load-bearing claims were re-checked here before acceptance. All eight hold:

| Claim | Verified |
|---|---|
| Agent path fabricates verification | `api/assistant.py:641-648` — `verified_claims=len(citations)`, `failed_claims=0`, `faithfulness_score=1.0`, `authority_score=1.0`, all hardcoded, `enabled=True` |
| `draft` cannot render two of the eight tools | `nodes/draft.py:12-20` — "`retrieve_chunks`/`lookup_reference` composition is left for later stories" |
| The planner never selects those tools | `grep -c "retrieve_chunks\|lookup_reference" nodes/plan.py` → 0 |
| Groundedness is positional | `guardrails/groundedness.py:51` — `citations[index] if index < len(citations)` |
| `interpret.py` bypasses `ModelRunner` | `modules/interpret.py:761` → `model_selector.run_inference` (`model_selector.py:538`) |
| Step budget is 5 | `modules/agent/state.py:19` |
| Security gate documents exit 2 but cannot return it | `scripts/security_gate.py:9` documents "2 — report parsing error"; the only exit is `sys.exit(main())` at :192, and the parse handlers `return []` |
| Legacy RAG citation dialects disagree | prompt asks for `[cite:N]` (`rag.py:126`) *and* `[YOUR_RESULTS:N]`/`[REFERENCE:N]` (:128,133-134); `validate_response` parses only `r"\[cite:(\d+)\]"` (:819) |

**One finding was escalated beyond what the consultation assigned it.** The
fabricated verification is not merely inconsistent — it is **rendered to
patients today**. `ExplainAssistant.tsx:607` shows the verification block
whenever `enabled` is true, and the agent path hardcodes `enabled=True`. The
frontend requests `min_faithfulness_score: 0.6` (:315); a hardcoded `1.0` passes
it unconditionally. A health app is currently displaying a perfect trust score
that no verifier computed.

The consultation bundled this fix into **C3** (Phase B, weeks). It moves to
Phase A here, split from the wire-format work, because it is wrong *now* and the
fix does not depend on anything else. This is the only place this roadmap
reorders the consultation.

---

## Phase A — Wrong today (hours to days)

Nothing here is a feature. Each item removes a way the project currently
misleads someone.

### A1 · Stop reporting fabricated verification
**Entry:** `api/assistant.py:637-651` (`_agent_terminal_to_response_parts`).
**First test:** a route test through `tests/support/routes.py::route_client`
asserting an agent-path answer does **not** return `faithfulness_score == 1.0`
with `failed_claims == 0` unless a real mapping produced those numbers.
**Do:** derive the fields from the guard's `MappingResult` — `surviving` and
`dropped` counts — and set `summary="agent:groundedness"` so nothing implies
`faithfulness.py` ran. Where no verifier ran, `enabled=False` is the honest
value; the frontend already branches on it (`ExplainAssistant.tsx:607`).
**Done:** the UI shows "N of M sentences kept" or nothing — never an invented 1.0.
**Note:** this does not call `faithfulness.py`, so it is not an ask-first change.
It stops *implying* that module ran.

### A2 · Security gate fails closed
**Entry:** `scripts/security_gate.py:44-51, 71-78`; `.github/workflows/ci.yml:92,95`.
**First test:** `tests/test_security_gate.py` — delete the report, assert exit 2.
Today that test goes green against a broken gate, which is the whole problem.
**Do:** return exit 2 on missing/malformed report (already documented at :9,
never implemented); stop swallowing scanner exit codes with `|| true`.
**Done:** a crashed scanner turns CI red. That is the correct failure direction.
**Risk accepted:** CI may go red on a scanner hiccup. Preferred to shipping green.

### A3 · Wire `repo_hygiene_check.py` into CI
**Entry:** `.github/workflows/ci.yml`; `CONTRIBUTING.md:75` already claims it runs.
**Done:** a stray file at repo root fails a job.

### A4 · Delete claims the repo cannot evidence
**Entry:** `docs/agentic/harness.md:25-30` (subagents in a directory that does not
exist), the PreToolUse-hook description, `AGILE_PLAN.md:50,53` (moved files),
the OpenWiki present tense in `CLAUDE.md`; add `CS4610_Report_Demo/README.md`
naming which report claims were aspirational; gitignore and delete the two
LibreOffice lock files.
**Done:** `ls .claude/agents` after reading `harness.md` produces no surprise.
**Not:** do not *build* the subagents or the hook to make the reports true
retroactively. Hooks are "a convenience feature for automation, not a security
boundary" (upstream docs), and the real guarantee already exists in
`core/llm/ollama_provider.py` and `modules/redaction.py`.

### A5 · Optional: `scripts/harness_drift_check.py`
Assert every path, script and CI step named in `docs/agentic/*.md` exists. It
would have caught A4's gaps on first run. Cheap; skip if A4 feels sufficient.

---

## Phase B — Let the patient see what the agent did (weeks)

### B1 · `ChatResponse` carries the run
**Entry:** `api/assistant.py:637`; `nodes/draft.py:271-301` already holds
`sentences` parallel to `citations`, and `guardrails/guard.py:173` flattens them
with `" ".join(...)`.
**First test:** route test asserting `run_id`, `terminal`, and `sentences[]`
parallel to `citations[]` are present; legacy path tolerates their absence.
**Do:** stop discarding data the agent already computes.
**Done:** the frontend can pair sentence *i* with citation *i* without guessing.

### B2 · Abstain and escalate as trustworthy outcomes
**Entry:** `pages/ExplainAssistant.tsx:332` currently infers uncertainty by
string-matching `'knowledge base only'`.
**Do:** distinct cards driven by `terminal` from B1, each showing what the agent
checked (tool names from the `RunLog`) and one next step. Wire the existing,
already-accessible `CitationTooltip` inline per sentence — it is built and used
only under `lab-interpreter/`.
**Done:** an abstention reads as a considered answer, not a failure.
**Why it matters:** this is the largest legibility gain available, and it is the
change the abstention-first safety bet lives or dies on.

### B3 · `GET /audit-log`
**Entry:** new route beside `api/*.py`; schema is already correct and indexed
(`models/audit.py:20-71`). Exactly one route reads `AuditLog` today, and only to
count rows before a purge.
**First test:** route test via `route_client` including a cross-profile 404.
**Do:** paginated, filterable by date / event_type / entity_type / `run_id`,
re-applying `core/audit.py:86-106`'s `ALLOWED_DETAIL_KEYS` **on read**.
**Blast:** if the allowlist is not re-applied, PHI-adjacent details reach the UI.

### B4 · Correlation IDs into logs and audit rows
**Entry:** `monitoring/correlation.py` — `get_correlation_id` is unused outside
that package. One unit test on the formatter. Makes B3's rows joinable to logs.

---

## Phase C — Instrument before generating (weeks)

### C1 · Trajectory scoring
**Entry:** `tests/agent/golden/*.json` (74 cases, `expect` carries only
`terminal`, `min_citations`, `advice_leakage`); `modules/agent/eval/scorer.py`;
per-node timing already recorded at `graph.py:64-74`.
**Do:** add `expect.tool_sequence` (or `first_tool`), a tool-selection accuracy
axis, and step-count aggregation.
**Why first:** it is the only instrument that can show a planner improved
*trajectories* rather than *terminals*. Everything in Phase D is judged by it,
and it produces the number that decides whether D3 is worth building at all.

### C2 · Eval card for the gate that already exists
**Entry:** new `docs/agentic/eval-cards/agent-gate.md`, numbers **generated**
from `agent_eval_gate.py` output, with a human-written "not covered" section.
**Rot rule:** hand-typed numbers rot; generated ones cannot. The generator is
the test.

---

## Phase D — The generative seam, reshaped (a quarter)

The consultation's central argument, verified: **the LLM planner is the wrong
first generative node.** A smarter planner would route to `retrieve_chunks` and
`lookup_reference` — the two tools `draft` cannot render and the planner never
selects. The patient sees the same templated sentence or an abstain either way.

### D1 · Deterministic reach (no LLM)
Extend `_default_planner` to `lookup_reference` (analyte questions with no
verified rows) and `retrieve_chunks` (free-text questions), and add the two
missing `draft` branches. `reflect.py:36` already treats `chunks` as grounding.
**Blast:** `retrieve_chunks` is the highest-injection-risk tool; extend the
`injection_resistance` golden cases with it.
**Patient gain:** "what is TSH?" returns a cited reference sentence instead of an
abstain. No model involved.

### D2 · Measure constrained decoding — owner's machine
One script, one tier, one `PlanDecision` schema, unconstrained vs
`response_format`. Tracks 2 and 3 disagree by roughly an order of magnitude and
neither measured it here; `llama_cpp` does not import in any agent sandbox.
On a CPU tier at tens of tok/s, an 8× multiplier on a 60-token decision is ~15 s
per plan turn against `MAX_STEPS = 5`. **This measurement gates D3.**

### D3 · LLM planner — conditional
Build **only if** C1 shows a material keyword-planner miss rate **and** D2 shows
a plan turn under ~3 s. Async `Planner`, compressed tool menu from the registry,
schema-constrained with post-hoc `model_validate_json`, falling back to
`_default_planner` on any failure, turn-1 only, mid/high tier only.
**This item may legitimately never be built.** That is a success condition, not
a failure.

### D4 · Per-sentence explainer — the node that changes what a patient reads
Between `draft` and `guard`: restate each grounded sentence in plain language
**without changing** value, unit, date or analyte; accept only if those tokens
survive verbatim, else keep the template sentence. Citations unchanged, so
`groundedness.map_sentences` still pairs positionally.
**Owner decision required before code** (see below).

### D5 · Dictation honesty
Default the dictation flag off and state plainly in the existing modal that
audio goes to the browser's speech service, which may be cloud-based
(`hooks/useSpeechRecognition.ts:2` wraps `window.SpeechRecognition`). This is
the one shipped path where data leaves the device. XS, and it closes the gap
whisper.cpp was proposed to close at High cost.

### D6 · Provenance panel
Reuse `PageImageOverlay` from trend points and interpreted-result cards; add an
accessible `<details>` data table under the trends chart.

### D7 · Route `interpret.py` through `ModelRunner`
`modules/interpret.py:761` calls `model_selector.run_inference`, bypassing the
facade `CLAUDE.md` §3 requires for every LLM call. Add a grep-shaped test that
no module outside `core/llm/` imports `Llama`.

---

## Phase E — Ceiling of two per quarter

Named, not "by appetite": **E1** HC-M06 extraction eval card in C2's format;
**E2** abstention-tolerance user study with the health-anxiety persona using B2's
cards — the cheapest item on this list with the largest unknown behind it.

Also, doc-only and unscheduled: FTC HBNR / EU AI Act / MHMDA compliance lines,
with the FDA patient-facing CDS carve-out routed to counsel **before** any "not a
medical device" copy ships.

---

## Not being built, and why

MCP router and scoped tokens · SMART Health Link resolver · whisper.cpp ·
Kokoro TTS · Qwen3-Embedding swap · BioMistral high-tier swap · two-model
routing · KV-state caching · real llama.cpp streaming · live in-flight step tray
· `TrendChart` consolidation · motion tokens · Tailwind v4 · React 19 ·
retroactive ADR log · harness-history narrative · "how this was built" doc ·
building subagents or a dev-time PHI hook.

Three reasons, applied consistently. **Collectively unaffordable:** by the
tracks' own effort labels these exceed a year of one maintainer's evenings
before maintenance. **New egress or new dependency:** MCP and SHL each convert
"no network calls in product paths" from a grep-verifiable property into a
policy with a carve-out; off-by-default network paths are still network paths.
**Nothing to optimize yet:** routing, KV cache and streaming all describe a
model call that does not exist.

Two decisions to record rather than revisit: **no MCP until a concrete client
exists**, and **no on-disk KV state** — the latter worth a grep-shaped CI rule,
since `llama-cpp-python`'s `LlamaDiskCache` writes PHI-derived state unencrypted.

---

## Owner decisions

| Decision | Why it is yours |
|---|---|
| **D4's paraphrase policy** | The first place the product's voice stops being fixed strings. Which form is audit-replayable — template or paraphrase (`graph.py:235-304 replay`)? Needs an answer before code. This is the highest-risk change in the plan for a health app and deserves the most scrutiny, not the least |
| **D3 vs skipping it** | If C1 shows the keyword planner misses under ~10%, spend the quarter on D4 instead |
| **D5's default** | Turning dictation off by default changes a shipped feature; disclosure-only is the alternative |
| **FDA posture** | Counsel, before any non-device copy |
| **A2's CI risk** | A fail-closed gate can redden the build on a scanner hiccup |

## Still unmeasured

No latency, RAM or throughput figure anywhere in this plan was measured on this
codebase — `llama_cpp` imports in no agent sandbox. D2 exists because of that.
Whether `response_format` with a schema actually constrains on Phi-4-mini under
0.3.35 was checked against source at a tag and never executed. Three tier repo
paths remain unverified pending `python scripts/download_models.py verify` on a
machine with network access.
