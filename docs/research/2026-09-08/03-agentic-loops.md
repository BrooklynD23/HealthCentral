# Track 3 — Agentic loop engineering

Research for the Asclexis (formerly HealthCentral) local-first health app.
Read [`00-brief.md`](00-brief.md) first — it records the verified repo state
this track builds on and the constraints that bind every recommendation
below. Knowledge cutoff May 2026; this research ran 2026-09-08. External
claims carry a fetched URL; anything published after the cutoff that could
not be independently verified is marked `[UNVERIFIED]`.

## Summary

The agent graph (`src/backend/modules/agent/graph.py`) is **ReAct-shaped but
not ReAct-driven**: `plan -> act -> reflect -> (loop | draft) -> guard ->
terminal` already matches the loop structure Yao et al. described in the
original ReAct paper[^react], but `nodes/plan.py`'s `_default_planner` is a
keyword matcher, not a model. The one change this track recommends without
hedging is the one the brief already named: **swap the injectable `planner`
parameter for an LLM-backed planner, gated to turn 1 of otherwise-unmatched
questions, with the existing deterministic planner kept as the permanent
fallback** — not a stepping stone to be deleted once the LLM planner ships,
but the safety net that makes the swap safe to ship at all.

Everything else in the "ReAct successors" literature — Reflexion-style
self-critique, LATS tree search, self-consistency voting — is a **reject or
narrow-scope-only** for this deployment, and the reasons are not aesthetic:
small models are measurably bad at judging their own output when the judge
and the generator are the same model and share the same error modes
(§1, §3), tree search multiplies calls to an already CPU-bound local model
(§1), and this repo's `reflect` node already implements the pattern the
2025-2026 literature converged on as the *reliable* alternative — a
deterministic, tool-result-based verifier (`_has_grounding`,
`reflect.py:24-43`) — which this track recommends **keeping**, not
replacing with a second LLM call (§3).

The two highest-leverage, lowest-risk items in this track are not the
planner swap at all: (1) the memory API (`api/memory.py`) has **zero audit
logging** and **zero redaction/injection scrubbing on write** — a verified
gap, not a hypothetical one, and a smaller fix than anything else here
(§4); and (2) the eval harness's 74 golden cases score only the *final*
terminal, never the *trajectory* that produced it — a planner swap without
trajectory-level scoring is flying blind on the one axis that actually
changes when you add a model to `plan()` (§5).

No recommendation here requires LangGraph. Every recommendation keeps
`guard.py` as the sole gate; nothing in this document proposes inlining a
safety check into a node.

---

## 1. ReAct and its successors, honestly assessed

### What the literature actually says, by 2026

**ReAct** (Yao et al., 2022, ICLR 2023)[^react] interleaves a reasoning
trace ("thought") with an action and an observation, in a loop, until the
model emits a final answer. This *is* the shape of `graph.py`'s
`plan -> act -> reflect` cycle — the gap is that nothing in `plan.py`
currently produces a "thought"; it produces a dict lookup.

**Reflexion** (Shinn et al., 2023, NeurIPS)[^reflexion] adds a verbal
self-reflection step after a failed attempt, stored in an episodic buffer,
that biases the next attempt. Reflexion's own architecture makes its
dependency explicit: an Actor, an **Evaluator that scores the Actor's
output**, and a Self-Reflection model that only fires once the Evaluator
has already produced a verdict. That structure only works when there is a
crisp, external pass/fail signal (Reflexion's benchmarks are coding tasks
with unit tests, and text games with a win/loss). A health-QA agent has no
such oracle per turn — "did this answer succeed" is exactly the judgment
`guard.py` exists to avoid delegating to the model. Naively porting
Reflexion here would mean asking the drafting model to critique its own
draft, which is the specific failure mode Huang et al. document: **"Large
Language Models Cannot Self-Correct Reasoning Yet"**[^selfcorrect] — LLMs
asked to self-correct without external feedback often get *worse*, not
better, and Kamoi et al.'s survey of when self-correction actually works
concludes the same[^tacl-survey]. The effect is worse at small scale: Wu et
al. find small models specifically fail at *verifying* correctness even
when they can produce a plausible-sounding critique, and that fine-tuning
for self-correction improves calibration but not accuracy at judging
correctness[^small-verifiers]. **Recommendation: do not add a Reflexion-style
self-critique step to this loop.** §3 covers what to do instead.

**Plan-and-Solve** (Wang et al., 2023) separates "devise a plan" from
"execute the plan" to reduce missing-step errors versus vanilla
chain-of-thought. Its core insight — make the plan explicit and separate
from execution — is already structurally present here: `plan.py` decides
one step, `act.py` executes it, and the loop repeats with real tool-result
feedback between decisions. That is arguably *better* for a small model
than Plan-and-Solve's own shape (commit to a multi-step plan up front),
because it never asks the model to enumerate steps it hasn't seen evidence
for yet — matches Anthropic's "give agents tools, not just instructions"
framing[^anthropic-agents] more than it matches Plan-and-Solve. No change
recommended here; it's already the right shape.

**LATS** (Zhou et al., 2023, ICML 2024)[^lats] unifies MCTS, a value
function, and reflection, and beats ReAct/Reflexion on HotpotQA — "at a
higher computational cost," and is explicitly recommended by its own
literature "for difficult tasks like programming... where performance is
prioritized over efficiency"[^lats]. That is the inverse of this
deployment's tradeoff: a 0.5B-12B dense (or 26B-MoE-with-4B-active) model
running on CPU on a patient's laptop, `MAX_STEPS = 5` (`state.py:19`), 8
narrow read-only tools. Tree search multiplies calls to the slowest
component in the stack by a branching factor for a task space (biomarker
lookups, trends, record navigation) that is already close to fully solved
by keyword matching. **Reject** for this deployment; flag as
`[UNVERIFIED]` whether any 2026 LATS variant has closed this cost gap for
CPU-only local inference — nothing found in this research suggests it has.

**Self-consistency / majority voting** (Wang et al., 2022) samples k times
and takes the majority answer. It transfers poorly to *agentic* action
selection specifically: "Soft Self-Consistency Improves Language Model
Agents"[^soft-sc] reports that plain self-consistency gives "minimal gains
in several interactive settings where LLMs act as agents to generate a
sequence of actions," and it is expensive in exactly the currency this repo
has least of (k× inference on an already CPU-bound model). It also
actively fights a hard repo invariant: `graph.replay()` (`graph.py:235-304`)
must deterministically reconstruct the same terminal from a logged run —
sampling variance in the planner is a bug against that contract, not a
feature. **Reject as a default.** If a future story wants disambiguation
for a genuinely ambiguous multi-topic question, the deterministic
planner's existing broaden-don't-guess strategy (`plan.py`'s R-12
handling, `_TOPIC_KEYWORDS`) already does this without any sampling.

### What actually works for a 4B-12B *local* model, synthesized

- **Format fidelity dominates prose quality** for small-model agent stacks
  — getting *valid, schema-conformant tool calls* out reliably matters more
  than getting eloquent reasoning traces[^small-agentic-survey]. This is
  the argument for structured output over free-text parsing in §2, and it
  is also the argument for keeping the planner's job narrow (one tool call,
  not a paragraph of reasoning).
- **Verifier models beat self-critique**, and the reason is mechanistic,
  not just empirical: when the same model generates and judges, "generator
  and evaluator share failure modes," so self-evaluation is "weak
  evidence of correctness"[^selfconsistency-ceiling]. Cross-model or
  rule-based verification consistently outperforms
  same-model self-critique[^verifier-vs-selfcritique]. `reflect.py`'s
  `_has_grounding` already *is* a rule-based verifier (§3).
- **Critique-aware supervised training** can materially improve small
  models at tool calling — CAST-Policy-4B, a 4B model trained with
  critique-aware supervision, improved 18.9% pass@1 over its base instruct
  model on a retail tool-use benchmark[^cast]. This requires a fine-tuning
  pipeline the repo does not have (no training infrastructure found under
  `modules/` or `scripts/`); flag as a longer-horizon option contingent on
  Track 5's model findings, not a near-term recommendation.
- **Tool count matters, and this repo is fine.** Production tool-selection
  accuracy degrades noticeably past ~15-20 tools in active rotation, and
  catastrophically past ~200[^tool-count]. This repo's registry
  (`tools/registry.py`) holds exactly 8. **No tool-retrieval/routing layer
  is needed** — a genuinely useful negative finding: do not build one
  speculatively.
- **Small local models with function-calling ability exist below 12B**, but
  non-monotonically — Qwen3-0.6B and Qwen3-4B outperformed Qwen3-1.7B on
  one 2026 benchmark, and the tool-calling circuit itself is reported
  "absent at 270M parameters, starts emerging at 1B, and gets sharper with
  instruction tuning"[^tool-calling-benchmark]. This directly informs the
  tier gate in §2: below a size/tier floor, don't attempt an LLM planner at
  all — fall back deterministically, always.

---

## 2. The LLM planner design

### The exact swap point

`nodes/plan.py:308-312` declares the seam:

```python
Planner = Callable[[str, RunLog], PlanDecision]

async def plan(
    question: str,
    run_log: RunLog,
    ctx: ToolContext,
    *,
    planner: Planner = _default_planner,
) -> PlanDecision:
    decision = planner(question, run_log)   # <-- NOT awaited today
    ...
```

Two facts matter for the swap, both verified by reading the code, not
inferred:

1. `Planner` is a **synchronous** callable — `decision = planner(...)` is
   never awaited. `_default_planner` is pure Python so this is fine today.
   An LLM planner needs a model call, which is I/O- or CPU-bound and must
   be `await`ed (through `ModelRunner.generate_async`,
   `core/model_runner.py`) — it cannot be a blocking call inside an async
   FastAPI request handler without stalling the event loop. **This is the
   one line of `plan()` that has to change**: `Planner` widens to admit an
   awaitable, and `plan()` awaits the result if it is one. This is
   additive to `plan()`'s body, not a rewrite of it.
2. `_default_planner(question, run_log)` (`plan.py:189`) does not receive
   `ctx`. An LLM planner needs `ctx` — to gate on hardware tier (below), and
   to emit its own `agent.plan`-adjacent audit distinguishing "LLM decided"
   from "fell back to deterministic" (the audit trail is the governance
   deliverable per `skills/asclexis-agent/SKILL.md`, and "which path
   decided this" is exactly the kind of fact that trail exists to answer).
   The surgical option is a thin sync wrapper around today's
   `_default_planner` rather than touching its signature — see the sketch
   below.

### Tool presentation: three options, real costs

The registry (`tools/registry.py`) holds 8 tools, each a Pydantic
`InputModel` with 0-2 fields, all primitives or optional dates/strings
(`tools/*.py`). Three ways to present them to the model, and their
approximate per-`plan()`-call token cost (English, rough tokenizer
estimate):

| Option | What it looks like | ~Tokens (8 tools) | What's lost |
|---|---|---|---|
| Full JSON schema | `InputModel.model_json_schema()` dumped verbatim, `$defs` included | 1200-3200 | Nothing — but this is stable, boilerplate-heavy text that belongs in the cache-friendly prefix (§6), not regenerated per call |
| **Compressed signature** (recommended) | `query_observations(analyte?: str, limit?: int=20) -> verified rows` — one line per tool | 150-250 | Field-level constraints (`ge`/`le` on `limit`) — acceptable, because the registry's Pydantic validation (`registry.validate_args`) enforces them regardless of what the model was told |
| Natural-language menu | Prose, no types: "You can look up lab results, compute trends, ..." | 60-100 | Type information the model needs to produce valid args at all — pushes more load onto the fallback/repair path below |

**Recommendation: compressed signatures**, generated once from the
registry at import time (never hand-duplicated — the same "single source
of truth" discipline the codebase already applies to
`RAGModule.PROMPT_INJECTION_PATTERNS` being imported, not copied, by
`sanitize_untrusted_field`), placed in the system-prompt-equivalent stable
prefix. Full JSON schema is disproportionate for tools this simple, and —
per Track 2's finding that no `grammar`/`response_format`/`GBNF` call
exists anywhere in `core/llm/` or `modules/` today — a full schema's real
payoff (constraining the model's *output* to conform) only materializes
*if* constrained decoding ships. Coordinate: build the compressed-signature
menu regardless (cheap, always useful for prompting); treat the
schema-derived GBNF grammar as an additive layer that activates only when
Track 2's structured-output finding says it's available, never a
precondition for the planner to function at all (see "degradation" below).

One real cost to weigh in: llama.cpp's own grammar-constrained decoding is
reported at **3.6x-8.2x slower than unconstrained generation** on GSM8K,
because llama.cpp's GBNF implementation does full runtime token checking
rather than the caching newer engines like XGrammar use[^gbnf-cost]. On a
CPU-bound local model, that multiplier lands on every `plan()` call in the
loop (up to 5 per question) — budget for it explicitly rather than assume
grammar is "free" once available, and prefer a **narrow, tool-scoped**
grammar (an 8-way enum on `tool_name` unioned with each tool's small
per-field grammar) over compiling a grammar for the full JSON-schema union,
since grammar-compile/constraint cost scales with grammar complexity, not
just presence.

### One tool per step, never batched — keep this, it helps small models

`act.py`'s docstring and the `asclexis-agent` skill are both explicit:
"execute EXACTLY ONE tool call; never batch." This is a hard existing
invariant, and an LLM planner should not be allowed to propose otherwise —
its output schema is a single `PlanDecision`, not a list. This is a
genuine point in the design's favor, not just a constraint to work around:
single-step selection ("what's the very next action, given what I've
already seen") is a much easier task for a small model than committing to
a whole multi-tool plan up front, and it caps the blast radius of one bad
LLM decision to one tool call rather than a batch of them.

### Handling a nonexistent tool or malformed args

Layered, reusing what already exists rather than adding a second
validation path:

1. **Prevention** (only if Track 2 confirms grammar support): constrain
   `tool_name` to the literal enum of `registry._REGISTRY` keys, sourced
   from the registry at grammar-build time so the grammar and the registry
   cannot drift.
2. **Parse**: tolerant JSON parsing of the model's output into a candidate
   `PlanDecision`-shaped dict; a parse failure is treated exactly like a
   model-unavailable failure (falls to step 4).
3. **Validate — already exists, reuse it verbatim**: `act.py` and
   `tools/registry.py` already enforce "malformed args fail validation and
   are NEVER executed" (`registry.get` raises `KeyError` on an unknown
   tool name, `registry.validate_args` raises `pydantic.ValidationError` on
   malformed args). The LLM planner's candidate decision must pass through
   this **before** `plan()` returns it, not after `act()` receives it — so
   a bad LLM output degrades to the deterministic fallback for that turn,
   rather than surfacing a `ValidationError` up through the graph loop
   (which today has no catch for one, because it's never had a source of
   malformed *plan* decisions before — only malformed *tool args* reaching
   `act`, which `act.py` already handles by refusing to execute).
4. **Fallback**: on any of {model unavailable, timeout, parse failure,
   validation failure}, call `_default_planner(question, run_log)` for that
   step. No new abstain path, no new terminal — the run continues exactly
   as it does today when the deterministic planner is the only planner.

### When to use the deterministic fallback — be concrete, not just "on failure"

The brief's framing ("the current keyword planner is a perfectly good
fallback — say when to use it") calls for more than an error handler:

- **Always try the deterministic planner first.** The four already-solved
  intents (care-task / med-change / timeline / single-analyte trend) are
  reliably keyword-detected; spending an LLM call on a question the regex
  already answers correctly is pure latency with no accuracy upside, and
  conflicts with Anthropic's own guidance to add complexity only when
  simpler solutions fall short[^anthropic-agents]. Invoke the LLM only when
  `_default_planner`'s turn-1 decision would be the generic, no-filter
  `query_observations` catch-all — i.e., precisely when the keyword
  dictionary had no signal, which is the case an LLM should exist to
  extend coverage for, not replace working code.
- **Only let the LLM own turn 1.** `_default_planner`'s turn-2+ logic
  (`plan.py:229-243`: check_verification after an empty
  `query_observations`, abstain after a confirmed-unverified status) is
  already close to the optimal reflex these tools support, and turn-2+
  decisions run later in the budget where an LLM misfire has less runway
  to recover in (`MAX_STEPS = 5`). Bounding the LLM's role to exactly one
  decision per run is the conservative choice CLAUDE.md asks for ("pick
  conservative and say why").
- **Gate by hardware tier.** Per `modules/model_selector.py`'s
  `TIER_MODEL_CONFIG`, the *default* tier is `low` (Qwen2.5-0.5B). The
  tool-calling-circuit finding above says function-calling ability is
  "absent at 270M, starts emerging at 1B"[^tool-calling-benchmark] —
  attempting an LLM plan on the 0.5B default tier is exactly the regime
  that finding warns against. Gate LLM-planner usage to `mid` tier and up
  (configurable), and treat `low`/`template` tier as an automatic,
  permanent deterministic-only path — not a fallback triggered by failure,
  a precondition never attempted.

### Pseudo-code sketch

Matches the existing injectable `planner` contract; additive next to
`_default_planner`, which is untouched:

```python
# nodes/plan.py — additive; _default_planner (line 189) is UNCHANGED.

from ..tools import registry as tool_registry

# Built once at import time FROM the registry — never hand-duplicated,
# same discipline as RAGModule.PROMPT_INJECTION_PATTERNS being imported
# by sanitize_untrusted_field rather than copied.
_TOOL_MENU: str = _build_compressed_tool_menu(tool_registry)

_PLANNER_SYSTEM_PROMPT = (
    "You choose the next step for a READ-ONLY health-record assistant.\n"
    f"Available tools:\n{_TOOL_MENU}\n"
    'Respond with exactly one JSON object: {"action": "call_tool"|"draft"|'
    '"abstain", "tool_name": <tool name or null>, "tool_args": {...}, '
    '"abstain_reason": <string or null>}. Choose "draft" once evidence has '
    'been gathered; choose "abstain" only if a prior tool call already '
    "ruled out an answer."
)  # STABLE across a run -> the cache-friendly prefix (see section 6)


def _llm_planner_available(ctx: ToolContext) -> bool:
    """Tier gate: mid/high only, model actually loaded. Never attempt an
    LLM plan on the low/template tier (tool-calling ability is unreliable
    below ~1B parameters per the 2026 benchmark literature)."""
    ...


async def _llm_planner(question: str, run_log: RunLog, ctx: ToolContext) -> PlanDecision:
    """Production planner. Falls back to `_default_planner` on ANY
    failure — unavailable model, timeout, unparseable output, or a
    tool_name/args that fails the SAME registry validation `act()` already
    enforces. Never raises past this function; a failure here degrades,
    it never crashes the run (mirrors act.py's own fail-closed contract).
    Only ever asked to decide turn 1 of an otherwise-unmatched question —
    see the call site note below.
    """
    if not _llm_planner_available(ctx):
        return _default_planner(question, run_log)

    try:
        raw = await model_runner.generate_async(
            system=_PLANNER_SYSTEM_PROMPT,             # stable prefix
            user=_render_turn(question, run_log),      # accumulates, see S6
            grammar=_PLAN_DECISION_GRAMMAR,             # optional; degrades
                                                          # to plain-JSON parse
                                                          # if the active
                                                          # provider has no
                                                          # grammar support
                                                          # (Track 2 seam)
            max_tokens=160,
            temperature=0.0,                             # determinism, not
        )                                                 # creativity, here
        candidate = _parse_plan_decision(raw.text)         # tolerant parse
    except (TimeoutError, ValueError, ProviderUnavailableError):
        return _default_planner(question, run_log)

    if candidate.action == "call_tool":
        try:
            tool_registry.validate_args(candidate.tool_name, candidate.tool_args or {})
        except (KeyError, ValidationError):
            # nonexistent tool OR malformed args -> never execute; degrade
            return _default_planner(question, run_log)

    return candidate


def _first_turn_planner(question: str, run_log: RunLog, ctx: ToolContext):
    """Call-site wiring (e.g. in api/assistant.py's run_agent construction,
    NOT inside plan.py itself): only reach the LLM when the deterministic
    planner's turn-1 decision is the generic no-filter catch-all AND no
    act() has happened yet. Turn 2+ always stays deterministic.
    """
    default_decision = _default_planner(question, run_log)
    is_turn_one = run_log.act_count() == 0
    is_unmatched_catchall = (
        default_decision.tool_name == "query_observations"
        and not (default_decision.tool_args or {}).get("analyte")
    )
    if is_turn_one and is_unmatched_catchall:
        return _llm_planner(question, run_log, ctx)   # awaitable
    return default_decision                             # sync, unchanged


# Widened seam: admits an async planner and the ctx an LLM path needs for
# its own tier gate / audit. `_default_planner` itself is NOT touched —
# `plan()` just awaits the result only if it is one.
Planner = Callable[
    [str, RunLog, ToolContext], "PlanDecision | Awaitable[PlanDecision]"
]


async def plan(
    question: str,
    run_log: RunLog,
    ctx: ToolContext,
    *,
    planner: Planner = _default_planner,   # DEFAULT UNCHANGED: tests/CI stay
                                            # 100% deterministic, zero model
                                            # dependency, exactly like today
) -> PlanDecision:
    decision = planner(question, run_log, ctx)
    if inspect.isawaitable(decision):
        decision = await decision
    # ... audit emission below is UNCHANGED
```

Note the default parameter of `plan()` stays `_default_planner` — the
existing 2-arg function — so a 3-arg call breaks it. The actual call site
that wants the LLM path passes `_first_turn_planner` (3-arg, matches the
widened `Planner` type) explicitly; `_default_planner` never needs to learn
about `ctx` at all. This keeps every existing test (`plan()` called with no
`planner=` override) byte-for-byte unchanged, satisfying "the loop is
ReAct-shaped but not ReAct-driven" without breaking the thing that makes it
safe today.

---

## 3. Reflection that works on small models

### What `reflect` already does, and why it's already the right pattern

`reflect.py:24-43`'s `_has_grounding` is a **mechanical, tool-result-based
check**: did the most recent `act` step return non-empty `rows` /
`points` / `chunks`, or a definitive `check_verification` status? It never
asks a model to judge its own — or anyone's — output. This is, without
having been framed this way in the code, *exactly* the pattern the 2025-26
literature converges on as the reliable alternative to self-critique:

- Self-critique is unreliable specifically because "generator and
  evaluator share failure modes" when they're the same
  model[^selfconsistency-ceiling] — the model that hallucinated a claim is
  poorly positioned to notice it hallucinated.
- Verifier models (separate from the generator, even if small) consistently
  outperform same-model self-critique on hallucination
  detection[^verifier-vs-selfcritique].
- `_has_grounding` isn't even a *model*-based verifier — it's a plain
  boolean check on structured tool output, which sidesteps the small-model
  self-evaluation problem entirely by not asking any model to evaluate
  anything. That is a stronger guarantee than a trained verifier, not a
  weaker one, for the narrow question `reflect` actually needs answered
  ("did I get evidence back," not "is this evidence correct" — the latter
  is `guard.py`'s groundedness/confidence gates' job, already separate).

**Recommendation: keep `reflect` exactly as deterministic as it is today.**
Do not add an LLM self-critique call to it. This is the most conservative
option available and it is *also* the one the external evidence favors —
not a case of safety and capability trading off against each other.

### What signal, if any, should be added

The task asks what should drive loop/draft/abstain_budget beyond what's
there. Three real candidates, assessed against this repo's actual cost
structure:

1. **Logprob-based confidence** — the cheapest option in principle (no
   extra model call), computed from the same generation that already ran.
   **Not currently available**: `core/model_runner.py:42-47`'s
   `InferenceResult` carries `text` / `tokens_generated` / `finish_reason`
   / `model_name` — no logprobs field anywhere in `core/llm/`. Adding one
   means widening `ProviderProtocol` and both concrete providers
   (`llama_cpp_provider.py`, `ollama_provider.py`) — a change to the
   shared facade Track 2 also touches; coordinate rather than duplicate.
   Even once available, logprobs are a noisy per-token signal at the
   response level on their own — "The Confident Liar" finds log-probability
   signals need care to be trustworthy even in a debate-diagnosis
   setting[^confident-liar]; semantic entropy across paraphrase samples is
   reported more accurate[^semantic-entropy] but costs k× generations,
   which is the same expensive-on-CPU problem self-consistency has in §1.
   **Recommend deferring**, not rejecting: real cost, uncertain payoff for
   the specific decision `reflect` makes (which is not "how confident is
   this answer," a question `guard.py`'s confidence gate already owns —
   it's "do I have any evidence yet," a question `_has_grounding` already
   answers deterministically and for free).
2. **A separate small verifier/classifier model** — the pattern the
   literature actually recommends over self-critique. **This repo already
   has one**, unused by the agent graph: `modules/verifier_agent.py`'s
   `VerifierAgent.verify_claim` does rule-based entailment checking
   (regex-pattern value/range/status matching, `verifier_agent.py:102-119`)
   with an optional LLM-based path for complex claims, feeding
   `modules/faithfulness.py`'s composite scoring — built for the older
   `/assistant/` RAG path (`RAGModule(enable_verification=True)`), not
   wired into `modules/agent/`. Both files are on CLAUDE.md's "ask before
   touching" list. This is prior art worth pointing a future story at
   rather than a new module — CLAUDE.md's own instruction ("prefer
   extending an existing module... there is usually prior art") applies
   directly — but it needs explicit sign-off before any integration work
   touches either file, and a careful audit of whether its "optional
   LLM-based entailment for complex claims" path is itself a self-critique
   risk in disguise before it's pointed at the agent's own drafts.
3. **Tool-result-based heuristics, extended** — the cheapest, safest
   option, and the one this track recommends *actively investing in*
   instead of a model call. `_has_grounding` today is binary (grounding
   exists or it doesn't); it does not currently distinguish "one row came
   back, weakly on-topic" from "five rows came back, exactly on-topic," and
   it does not track *which tool* produced the grounding across turns
   (useful for §5's tool-selection-accuracy axis). Extending this
   deterministic function — e.g., counting rows, checking the returned
   `analyte_canonical` matches the question's detected topic — costs
   nothing in latency or footprint and stays inside the "verifier model"
   camp the research favors, just without the "model" part.

### Abstention as the conservative default, with health-domain backing

The task's framing — "a wrong 'I have enough evidence' is worse than an
extra step" — matches a growing 2026 clinical-LLM literature on calibrated
abstention specifically: providing an explicit abstention option
"consistently increases model uncertainty and safer abstention, far more
than input perturbations, while scaling model size or advanced prompting
brings little improvement"[^abstain-med]. This repo's `abstain` and
`escalate` are already first-class terminals (`schemas.py:32-41`,
`ESCALATE_TEMPLATE`/`ABSTAIN_TEMPLATE` in `guardrails/templates.py`),
scored as *correct* outcomes in the golden set (`eval/scorer.py`'s
`abstention` axis) — the architecture already reflects this literature's
recommendation; no change needed here beyond not eroding it when the
planner swap lands (§2's "only turn 1" and hardware-tier gating are both
in service of this — an LLM misfire should cost at most one wasted step,
never a false "enough evidence").

---

## 4. Agent memory beyond the current cache

### What exists today, verified

- `modules/agent/cache.py`: exact-match, `(normalized_question,
  profile_version)`-keyed, in-process dict. Invalidates on any
  observation-verify (the version bump), no TTL, no cross-process
  persistence, and it stores no PHI on disk (`cache.py:14-16`). This is a
  same-turn answer cache, not agent memory in any of the senses below —
  it never influences what the agent *does*, only whether it re-does it.
- `models/memory_item.py` / `api/memory.py`: a per-profile, SQLCipher-vault
  CRUD store (`MemoryItem.profile_id`, free-text `key`/`value`/`category`,
  capped at `settings.max_memory_items_per_profile = 100`,
  `core/config.py:129`). Full user-facing CRUD (create/list/get/update/
  delete) already exists. **Verified, not wired to the agent**: nothing
  under `modules/agent/` imports `models.memory_item` or `MemoryItem`
  (confirmed by grep across the module) — this store is currently inert
  from the agent's perspective, a separate feature (`ASSIST-MEM-001`) that
  predates and does not yet touch the agent graph.
- **Two verified gaps in the existing memory route, before any new
  capability is even proposed**: `api/memory.py` has **no
  `create_audit_log`/`emit_audit_event` call anywhere in the file** —
  every create/update/delete of profile data is silent, which is a direct
  gap against CLAUDE.md's hard invariant ("audit logging on every route
  that touches documents, observations, or profile data" — a memory item
  is profile data by the model's own docstring). And `MemoryItemCreate`/
  `MemoryItemUpdate`'s `value` field is stored **with no pass through
  `sanitize_untrusted_field` or `classify_advice`** — today that's a latent
  gap rather than a live one (nothing reads it back into a prompt yet), but
  it is exactly the shape of injection surface `draft.py` already treats
  observation `analyte`/`unit` fields as (HC-M05) and that §6 requires for
  anything entering the loop's context. **Fix these two before wiring
  memory into the agent at all** — they are smaller than anything else in
  this section and they are prerequisites for it, not follow-ups.

### The 2026 state of agent memory, briefly

- **Episodic / semantic / procedural** is not a 2026 invention — it's
  Tulving's 1972 episodic/semantic distinction plus Squire's 1987
  procedural addition, formalized for LLM agents by the CoALA
  paper[^mem0-paper] and adopted by Mem0's production
  taxonomy[^mem0-types]: episodic = raw events/interactions; semantic =
  consolidated, detached-from-context facts (user preferences,
  configuration); procedural = learned tool-use patterns and workflow
  heuristics. Mapped onto this repo: `MemoryItem` rows as currently
  designed are semantic-shaped (a `key`/`value`/`category` fact store, not
  an episode log); the agent's `RunLog` (`state.py:42-60`) is closer to an
  episodic trace, but it is per-run and not persisted or consolidated
  across runs today.
- **MemGPT/Letta**'s contribution is the OS-paging metaphor: treat the
  context window as RAM, page facts in/out of longer-term storage via the
  model's own tool calls, with three tiers — core memory (pinned in every
  prompt), archival memory (a vector store, searched on demand), recall
  memory (full history, on disk)[^letta]. The **agent runs the paging
  itself**, as tool calls — which is directly relevant here: it means a
  MemGPT-style memory subsystem is not a passive store, it's a 9th (or
  10th) *tool* the planner can invoke, with all of §2's malformed-args and
  validation concerns applying to it identically. Full Letta is a heavy
  dependency (its production deployments back archival memory with
  Postgres + pgvector[^letta]) — **not appropriate here**: this repo has no
  Postgres, is local-first, and already has a per-profile SQLCipher vault
  that plays the "archival store" role natively. The *pattern* (tiered,
  agent-paged, core-vs-archival) is worth borrowing; the *implementation*
  is not.
- **Mem0** (ECAI 2025)[^mem0-paper] extracts salient facts from
  conversation via an LLM call, consolidates them against existing memory
  (add/update/merge/no-op), and retrieves by embedding similarity at query
  time; reports 90% token-cost savings and 91% lower p95 latency versus
  full-context stuffing on its own benchmark[^mem0-paper] — figures from
  the paper's own benchmark, not independently reproduced here, so treat
  as directional. The extraction step is the one to scrutinize hardest for
  this repo (next point) — it is an LLM call that decides what becomes a
  durable "fact."

### The most important risk in this section: summarization laundering an unverified claim into a "fact"

This is the crux the task calls out, and 2026 research gives it a name and
measured severity, not just a plausibility argument. Two directly relevant
findings:

1. **"Governance Decay"** (2026)[^governance-decay]: in 1,323 episodes
   across multiple models, in-context constraints (e.g., "confirm before
   emailing outside the org") that agents reliably obeyed while the
   constraint was visible in context were **silently dropped by routine
   compaction/summarization**, and violation rates rose from 0% (constraint
   in full context) to 30% overall, reaching 59% for some models, once the
   constraint was compacted away — versus 0% violation whenever the
   constraint survived the summary. The paper's framing matters directly
   here: "Governance Decay is a property of the harness, not the model" —
   it is specifically the compaction *step* that is unaudited, not a model
   capability gap. Applied to this repo: if a future memory-summarization
   step ever compresses a run's history, it must be built with the same
   suspicion this repo already applies to retrieved chunk text — **a
   summarizer is exactly the kind of untrusted transformation
   `_sanitize_chunk_text`/`sanitize_untrusted_field` exist to gate, except
   here the "untrusted" content it's transforming would be the agent's
   *own prior output*, not a retrieved document.** Any abstain/escalate
   reasoning, and any medical-advice-adjacent guard decision embedded in a
   run's history, must survive verbatim through compaction or not be
   compacted at all — never "summarized faithfully, we hope."
2. **"Agent Memory Is a Surface for Endogenous Authorization Laundering"**
   (2026)[^auth-laundering]: names the general mechanism — a memory system
   that consolidates raw, provisional, or unverified content into a
   compact "fact" representation can cause that fact to be treated with
   more authority downstream than the original content warranted, because
   the consolidation step itself is invisible to whatever later reads the
   memory. This is the abstract version of the concrete risk in this
   repo's own terms: an agent run that **abstained** because
   `check_verification` reported "unverified" (the exact
   `abstain-unverified-*` golden-case family) must never have that
   abstention *summarized* into a memory entry that reads as "LDL is
   probably fine" or drops the unverified qualifier — the citation
   discipline `guard.py` enforces on live answers (§6) has to be enforced
   on anything written to durable memory with the same rigor, or memory
   becomes the one path in this system where an ungrounded claim can reach
   a future turn without ever passing through `guard`.

**Recommendation, concretely**: if/when `MemoryItem` is wired into the
agent (a new story, not assumed by this track), (a) route every write
through `sanitize_untrusted_field` at minimum, matching draft.py's existing
discipline for vault-derived free text, closing the gap noted above; (b)
**never let an LLM summarization step write to `MemoryItem` directly** —
any candidate memory fact derived by summarization must itself pass
through `guard.py`'s groundedness mapping (does this claim map to a real
citation?) before being persisted, exactly as it would before being shown
to the user, because a fact silently written to memory and a fact silently
shown to the user carry the same downstream risk, just deferred; (c) keep
memory writes strictly additive/append-only from the agent's own runs (no
agent-initiated overwrite of a user-authored memory item) so a
hallucinated "consolidation" can never quietly replace something the user
verified themselves.

### Retention, visibility, deletion

- **Visibility**: already solved by the existing CRUD (`GET /`, `GET
  /{id}`) — a real foundation for the brief's gap #7 ("no user-facing data
  control plane"). No new UI primitive needed at the API layer; a frontend
  surface is Track 8's territory.
- **Deletion**: `DELETE /{item_id}` exists and is a hard delete scoped to
  `profile_id` (`api/memory.py:210-235`) — correct isolation, but paired
  with the audit gap above: a user cannot currently see *when* something
  was deleted, only that it's gone, because nothing logs the delete.
- **Retention**: no TTL, no automatic expiry, only the count cap
  (`max_memory_items_per_profile = 100`). For PHI-adjacent free text sitting
  in a vault indefinitely with no expiry and no audit trail of who/what
  wrote it, this is worth a deliberate policy decision (explicit retention
  window, or explicit "keep forever, user-deletable" with the audit gap
  closed) rather than the current implicit "until the user notices and
  deletes it, and no one can prove when."

---

## 5. Evaluating agent loops

### What the current harness scores, and its real blind spot

`modules/agent/eval/scorer.py` scores 74 golden cases
(`tests/agent/golden/*.json`) on six axes: groundedness, citation,
abstention, advice_leakage, injection_resistance, phi_leakage — all scored
against the **final terminal only** (`AgentTerminal.terminal` /
`.text` / `.citations`). `RunLog.steps` (which tool was called, in what
order, with what args) is never inspected by the scorer. This is a
reasonable design for a deterministic planner, where the trajectory is a
pure function of the question and thus not an independent source of risk —
**it stops being reasonable the moment `plan()` can call a model**, because
now two different trajectories can produce the same correct final answer
while one of them, say, called `retrieve_chunks` on a question that names
no analyte at all, burned three of five steps before finding the right
tool, or "got lucky" that a wrong tool's empty result still routed to the
right fallback. None of that is visible today. This is the gap the summary
calls out as more urgent than the planner swap itself: **do not ship an
LLM planner without adding at least trajectory-level scoring first**, or
the eval gate that is supposed to catch a regression cannot see the
regression's actual location.

### What a 2026 looping-agent eval adds, mapped to this repo

The 2026 literature is consistent on the shape of what final-answer-only
scoring misses: "a 12-span agent run with the right final answer can have
8 wrong tool calls, 3 unnecessary retries, and a 6x cost overrun" — the
trace, not just the outcome, is "the unit of evaluation"[^trajectory-eval].
Concrete axes to add, each mapped to an existing repo primitive:

1. **Tool-selection accuracy.** For each golden case, add an expected
   `tool_sequence: list[str]` (or an expected *first* tool, looser and more
   robust to legitimate multi-path solutions) to the golden JSON schema
   (`tests/agent/golden/*.json` already carries `expect.terminal` /
   `expect.min_citations` — this is the same shape of addition). Score:
   does `RunLog.steps` filtered to `node == "act"` (`state.py`'s
   `RunStep`) match, or at minimum start with, the expected tool? This
   directly answers "did the planner pick the right tool," which is the
   one thing an LLM planner changes that the current scorer cannot see at
   all.
2. **Unnecessary-step detection.** `RunLog.act_count()` (`state.py:55-57`)
   already exists — the missing piece is a *golden-case-level expected
   step count* to compare it against. A case expecting a single-hop answer
   (e.g. any `grounded-*-latest` case) that resolves in 3 `act` steps
   instead of 1 is a real regression signal even though its terminal is
   unchanged — flag it as a new axis (`efficiency` or
   `unnecessary_steps`), scored as actual steps minus expected steps,
   never negative-credit for using *more* of the budget than the
   deterministic planner would have, since abstain-avoidance sometimes
   legitimately costs an extra step.
3. **Cost-per-answer.** `metrics.py`'s `record_node_timing` already times
   every node (`graph.py`'s `_timed_node` context manager, S5-3) — the
   missing piece is aggregating it per golden case into the score report
   rather than only into the live `/api/v1/monitoring/metrics` p50/p95/p99.
   An LLM planner adds one model call to the hot path; this axis is what
   catches "the swap works but tripled latency on the common case" before
   it ships.
4. **Trajectory/step-level scoring vs. final-answer-only.** Rather than a
   single new axis, treat this as the organizing change: every existing
   axis (groundedness, citation, etc.) stays final-answer scored (they are
   about what the user sees, and that's correctly unchanged by *how* the
   agent got there); the *new* axes above are trajectory-scored,
   additively, alongside them — not a replacement for the four-axis
   safety gate (`ScoreReport.passed`, `scorer.py:116-135`), which must keep
   its current hard bars (`== 1.0` / `== 0`) untouched. A trajectory
   regression should be visible and reviewable; it should not by itself
   fail the safety gate the way an `advice_leakage > 0` does, because
   "took an extra step" and "leaked medical advice" are not the same
   severity and conflating them would either weaken the safety gate's
   signal or make trajectory noise block every PR.

### LLM-as-judge: can a local model be the judge at all?

Short answer for this repo: **no, not as the primary mechanism**, and the
2026 evidence is specific about why. A large-scale 2026 evaluation across
21 judge models and ~541,000 judgments found judge rankings shifting by up
to 14 positions across benchmarks and a measurable "kappa deflation"
between exact-match metrics and judge-assigned
rankings[^judge-reliability] — even *frontier* judges disagree with each
other more than expected; "smaller and more cost-efficient models are less
effective judges compared to the best available LLMs"[^judge-reliability].
There is a counter-data-point worth naming honestly: a 7B model
specifically *trained* as a reward-model judge (Master-RM-7B) reportedly
reached Cohen's kappa 0.91 with GPT-4o and 0.90 with human
judgment[^judge-reliability] — but that is a purpose-trained judge model,
not this repo's general-purpose Qwen2.5/Gemma-4 tiers repurposed for
judging, and building/maintaining a second trained model is a new
long-lived artifact this repo has no infrastructure for (same caveat as
CAST in §1). **Recommendation**: keep the golden-set scorer's existing
mechanical checks (regex/pattern matching against fixed templates,
citation-handle presence, RedactionEngine pattern counts) as the sole
judge for the safety axes — they are already deterministic, reproducible,
and immune to the judge-disagreement problem entirely, because they are
not judges, they are assertions. Reserve any LLM-as-judge role (e.g.,
"is this trend sentence's phrasing natural") for a non-gating,
advisory-only signal a human reviews, never for anything that can flip
`ScoreReport.passed`.

---

## 6. Context engineering for the loop

### What should stay in the stable, cache-friendly prefix

Per Track 2's verified finding (no `n_batch`/prefix-reuse/state save-load
anywhere in `llama_cpp_provider.py`) and the 2026 consensus on prefix
caching — "keeping prefix prompts stable" and "enforcing append-only,
deterministic updates" is the single highest-leverage practice for cache
hit rate, since even a timestamp at the top of a system prompt invalidates
the whole cache[^prompt-caching] — the loop's prompt should be assembled in
two strict zones:

- **Stable prefix** (identical across all `MAX_STEPS` iterations of one
  run, and across runs that share nothing but the same tool registry):
  the compressed tool menu from §2, the planner's fixed system-prompt
  framing, and the guard-relevant standing instructions ("read-only,
  never diagnose, cite everything"). None of this should ever include a
  timestamp, a run id, or anything else that varies per call — if any of
  those are needed, they belong in the accumulating zone, not the prefix,
  specifically because a variable prefix defeats the entire point of
  caching it.
- **Accumulating zone** (grows step to step within one run, reset between
  runs): the question, and a compact rendering of `RunLog.steps` so far —
  which tool was called, with what args, and its output summary. This is
  exactly the "recall memory" tier in the MemGPT taxonomy (§4), scoped to
  one run rather than persisted across runs.

Given `MAX_STEPS = 5`, the accumulating zone is bounded by construction —
there is no unbounded-growth risk within a single run the way there is in
a long-lived chat session, so **no compaction/summarization step is needed
inside the loop itself**, which sidesteps the Governance Decay risk (§4)
entirely for the in-run case: nothing here is ever compacted, so nothing
here can be silently dropped by a compaction pass. That risk becomes real
only if/when cross-run memory (§4's `MemoryItem`) starts feeding into this
prompt — at which point the same "never summarize a guard decision or an
abstain reason without it surviving verbatim" rule from §4 applies here as
the actual mechanism, not just the policy.

### When to compact — the one place it's genuinely needed

The one place compaction is real, even under `MAX_STEPS = 5`: a single
tool's output can be large (`retrieve_chunks` returns up to 10 chunks,
`RetrieveChunksOutput`; `query_care_tasks`/`query_medication_changes`/
`query_timeline` each cap at 50 rows). Rendering all of that verbatim into
the accumulating zone on every subsequent `plan()` call re-encodes it
repeatedly. Recommend rendering **tool outputs as compact structured
summaries** in the accumulating zone (counts + a few representative
handles, e.g. "5 verified LDL rows found, ids [...]"), not the full row
set — the *full* rows are already durably available from `RunLog.steps`
for `draft.py` to compose from at the end; the planner only ever needs
enough to decide the *next* action, not the full payload. This is
compaction of *volume*, not compaction of *meaning* — no summarizing
model call involved, no laundering risk, just a smaller rendering of
already-structured data.

### Keeping the injection-neutralization guarantee intact when tool results enter context

Two existing chokepoints already do this work and must not be bypassed or
duplicated by the loop's prompt assembly:

- `modules/rag.py::_sanitize_chunk_text` (`rag.py:723-746`) neutralizes
  `RAGModule.PROMPT_INJECTION_PATTERNS` matches in `reference` /
  `user_document` / `user_observation` chunk text before it enters the
  **chat** path's composed prompt — this is the RAG surface, not the agent
  graph, but it is the canonical pattern-list source
  `guardrails/redaction_gate.py::sanitize_untrusted_field` already imports
  rather than re-implements (`redaction_gate.py:73`), and `eval/scorer.py`
  imports the same list a third time for the `injection_resistance` axis
  (`scorer.py:168`) — three call sites, one source list, verified by
  reading all three.
- `guardrails/redaction_gate.py::sanitize_untrusted_field` is what
  `draft.py` already runs vault-derived free text (`analyte`, `unit`,
  care-task `title`/`source_quote`, medication-change `entity_value`/
  `quote`, timeline `title`) through before composing a sentence
  (`draft.py`'s module docstring, HC-M05).

**The rule for the planner's context assembly**: any tool-output field
that is extraction-derived free text (the same fields `draft.py` already
sanitizes) MUST be passed through `sanitize_untrusted_field` **before**
being rendered into the accumulating prompt zone that a future `plan()`
call reads — not just before it's shown to the user. This closes a gap
that doesn't exist today only because `plan()` never reads tool output
text at all (today's deterministic planner only inspects
`output.get("rows")`/`.get("status")`, structural checks, never the string
fields inside them). The moment an LLM planner starts reading rendered
tool-output text to decide its next move, an unsanitized `analyte` field
containing an injection payload becomes a **live attack surface against
the planner itself**, not just against the eventual user-facing sentence
— a strictly new risk this section exists to name before it ships, not
an existing one merely being re-described. Concretely: reuse
`sanitize_untrusted_field` at the render step in `_render_turn` (the
sketch in §2), do not write a second sanitizer — this is the same
"single source of truth" discipline the codebase already applies
everywhere else in the guardrail chain.

---

## Recommendations

| Change | Integration point (file:line) | Impact | Effort | Risk | Safety review needed? |
|---|---|---|---|---|---|
| Widen `Planner` type + `plan()`'s one `decision = planner(...)` line to admit an awaitable; `_default_planner` untouched | `src/backend/modules/agent/nodes/plan.py:308-343` | High — unblocks every other planner recommendation | Small (one function body, one type alias) | Low — default parameter unchanged, existing tests unaffected | No (no behavior change with the default planner) |
| Add `_llm_planner` + tier-gated, turn-1-only, catch-all-only call-site wiring (§2 sketch) | New code in `nodes/plan.py`; call-site wiring in `api/assistant.py`'s `run_agent(...)` construction | High — the actual capability upgrade this track targets | Medium — new function, new grammar/prompt asset, tier-gate plumbing | Medium — new failure mode (bad tool call) fully mitigated by existing `registry.validate_args`, but is new *code path* through a new *source* of untrusted planner output | **Yes** — touches `modules/agent/` core loop; per CLAUDE.md, ask before any PR, and this must ship with new golden cases (below) before merge |
| Compressed-signature tool menu built from `tools/registry.py` at import time (not hand-duplicated) | New helper near `tools/registry.py` or `nodes/plan.py` | Medium — keeps prompt small and cache-friendly | Small | Low | No |
| Optional GBNF grammar for `PlanDecision`, sourced from `registry._REGISTRY` keys, activated only if Track 2 confirms grammar support | Coordinate with Track 2's `02-inference-serving.md` finding | Medium — but budget the reported 3.6-8.2x llama.cpp GBNF slowdown[^gbnf-cost] explicitly | Medium (depends on Track 2's provider-layer change) | Low if the plain-JSON-parse path stays as the always-available fallback | No (additive, degrades safely) |
| Do **not** add Reflexion-style self-critique to `reflect` | N/A — explicit non-change to `reflect.py` | High (avoided regression) | None | N/A | N/A |
| Extend `_has_grounding` with row-count / topic-match signal, still deterministic | `src/backend/modules/agent/nodes/reflect.py:24-43` | Low-Medium — sharper loop/draft decisions at zero model cost | Small | Low | Recommend a lightweight review (touches a guard-adjacent node) but not a full safety review — no new model call, no new terminal path |
| Point a future story at `modules/verifier_agent.py` / `modules/faithfulness.py` as prior art before building any new verifier | N/A — research pointer, no code change | N/A | N/A | N/A | **Yes, explicitly** — both files are on CLAUDE.md's "ask before touching" list; this is a flag for the *next* story, not an instruction to touch them now |
| Add audit logging to every `api/memory.py` route | `src/backend/api/memory.py` (all five handlers, currently zero `emit_audit_event`/`create_audit_log` calls) | High — closes a verified hard-invariant gap, independent of any agent wiring | Small | Low | Recommend review — it's a compliance/audit fix, low technical risk but touches profile-data handling |
| Route `MemoryItemCreate`/`Update.value` through `sanitize_untrusted_field` before persisting | `src/backend/api/memory.py` (`create_memory_item`, `update_memory_item`); reuses `guardrails/redaction_gate.py:55-82` | Medium — prerequisite for ever safely wiring memory into the agent loop | Small | Low | Recommend review — writes to PHI-adjacent vault storage |
| Never let a memory-summarization step write to `MemoryItem` without passing through `guard.py`'s groundedness mapping first | Design constraint for any future memory-consolidation story; call site would be new, guard call reuses `guardrails/guard.py:68-187`/`map_sentences` | High — the specific "laundered unverified claim" risk named in the brief | N/A (policy for a future story, not code today) | N/A | **Yes** — this is exactly the kind of guarantee CLAUDE.md says must be "called, never inlined" |
| Add `expect.tool_sequence` (or expected first tool) to golden-case JSON + a tool-selection-accuracy scorer axis | `src/backend/tests/agent/golden/*.json` (schema addition); `src/backend/modules/agent/eval/scorer.py` (new axis, additive to `ScoreReport`) | High — the one thing that lets the LLM planner ship safely (§5) | Medium — 74 existing cases need the new field backfilled | Low | Recommend review of the new axis's pass/fail bar, not a full safety review (it's an eval-only change) |
| Add step-count / unnecessary-step and per-node cost aggregation to the scorer, reusing `metrics.py`'s existing timing | `src/backend/modules/agent/eval/scorer.py`; `src/backend/modules/agent/metrics.py` (already has per-node timing, S5-3) | Medium — catches latency/step-count regressions before they ship | Small-Medium | Low | No |
| Do **not** use an LLM (local or otherwise) as judge for any of the six existing safety axes | N/A — explicit non-change to `scorer.py`'s pattern-matching checks | High (avoided regression) | None | N/A | N/A |
| Sanitize tool-output free-text fields at the point they're rendered into the planner's accumulating context, reusing `sanitize_untrusted_field` | New `_render_turn` helper in `nodes/plan.py` (§2/§6) | High — closes a new attack surface the LLM planner itself introduces | Small (one call site, existing sanitizer) | Medium if skipped — untrusted text would reach the planner's decision-making, not just the final answer | **Yes** — new call site for redaction discipline, in the same class as `draft.py`'s existing HC-M05 handling |

---

## Sources

- [ReAct: Synergizing Reasoning and Acting in Language Models (arXiv:2210.03629)](https://arxiv.org/pdf/2210.03629)
- [Reflexion: Language Agents with Verbal Reinforcement Learning (arXiv:2303.11366)](https://arxiv.org/abs/2303.11366)
- [Large Language Models Cannot Self-Correct Reasoning Yet (arXiv:2310.01798)](https://arxiv.org/abs/2310.01798)
- [When Can LLMs Actually Correct Their Own Mistakes? A Critical Survey of Self-Correction of LLMs (TACL / MIT Press)](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00713/125177)
- [Small Language Models Need Strong Verifiers to Self-Correct Reasoning (arXiv:2404.17140)](https://arxiv.org/pdf/2404.17140)
- [Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models (arXiv:2310.04406)](https://arxiv.org/abs/2310.04406) / [EmergentMind summary](https://www.emergentmind.com/topics/language-agent-tree-search-lats)
- [Soft Self-Consistency Improves Language Model Agents (arXiv:2402.13212)](https://arxiv.org/pdf/2402.13212)
- [Building Effective AI Agents — Anthropic](https://www.anthropic.com/engineering/building-effective-agents)
- [Small Language Models for Agentic Systems: A Survey of Architectures, Capabilities, and Deployment Trade-offs (arXiv:2510.03847)](https://arxiv.org/pdf/2510.03847)
- [CAST: Critique-Aware Supervision for Training Reliable Long-Horizon Tool-Calling Agents (arXiv:2608.30147)](https://arxiv.org/html/2608.30147v1)
- [AI Agent Tool Calling Benchmarks on GPU Cloud: BFCL v4, tau-Bench (Spheron Blog, 2026)](https://www.spheron.network/blog/tool-calling-benchmarks-bfcl-tau-bench-latency-optimization/)
- [How Many Tools Should an LLM Agent See? A Chance-Corrected Answer (arXiv:2605.24660)](https://arxiv.org/html/2605.24660v1)
- [The Over-Tooled Agent Problem: Why More Tools Make Your LLM Dumber (tianpan.co, 2026)](https://tianpan.co/blog/2026-04-19-over-tooled-agent-problem)
- [llama.cpp GBNF grammars README](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)
- [When Correct Isn't Usable: Improving Structured Output Reliability in Small Language Models (arXiv:2605.02363)](https://arxiv.org/pdf/2605.02363)
- [Verify when Uncertain: Beyond Self-Consistency in Black Box Hallucination Detection (OpenReview)](https://openreview.net/forum?id=6tlLISSgiu)
- [The Confident Liar: Diagnosing Multi-Agent Debate with Log-Probabilities and LLM-as-Judge (arXiv:2606.10296)](https://arxiv.org/html/2606.10296)
- [A Survey of Confidence Estimation and Calibration in Large Language Models (arXiv:2311.08298)](https://arxiv.org/pdf/2311.08298)
- [Knowing When to Abstain: Medical LLMs Under Clinical Uncertainty (ACL Anthology, EACL 2026)](https://aclanthology.org/2026.eacl-long.291/)
- [When silence is safer: a review and decision-theoretic framework for LLM abstention in healthcare (npj Digital Medicine)](https://www.nature.com/articles/s41746-026-02882-1)
- [Hindsight vs Letta (MemGPT): Agent Memory Compared (2026)](https://vectorize.io/articles/hindsight-vs-letta)
- [Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory (arXiv:2504.19413, ECAI 2025)](https://arxiv.org/abs/2504.19413)
- [Semantic vs Episodic vs Procedural Memory in AI Agents (Mem0 blog)](https://mem0.ai/blog/semantic-vs-episodic-vs-procedural-memory-in-ai-agents-a-complete-comparison)
- [Governance Decay: How Context Compaction Silently Erases Safety Constraints in Long-Horizon LLM Agents (arXiv:2606.22528)](https://arxiv.org/abs/2606.22528)
- [Agent Memory Is a Surface for Endogenous Authorization Laundering (arXiv:2609.01836)](https://arxiv.org/html/2609.01836)
- [Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents (arXiv:2510.02837)](https://arxiv.org/html/2510.02837v3)
- [AI Agent Evaluation (2026): Metrics, Frameworks, and Production Failures (Morph LLM)](https://www.morphllm.com/ai-agent-evaluation)
- [Reliability without Validity: A Systematic, Large-Scale Evaluation of LLM-as-a-Judge Models Across Agreement, Consistency, and Bias (arXiv:2606.19544)](https://arxiv.org/html/2606.19544v1)
- [Context Engineering for Production AI Agents: KV Cache, Prefix Caching (Spheron Blog, 2026)](https://www.spheron.network/blog/context-engineering-production-ai-agents-kv-cache-long-context/)

[^react]: [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/pdf/2210.03629)
[^reflexion]: [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)
[^selfcorrect]: [Large Language Models Cannot Self-Correct Reasoning Yet](https://arxiv.org/abs/2310.01798)
[^tacl-survey]: [When Can LLMs Actually Correct Their Own Mistakes? A Critical Survey of Self-Correction of LLMs](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00713/125177)
[^small-verifiers]: [Small Language Models Need Strong Verifiers to Self-Correct Reasoning](https://arxiv.org/pdf/2404.17140)
[^lats]: [Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models](https://arxiv.org/abs/2310.04406)
[^soft-sc]: [Soft Self-Consistency Improves Language Model Agents](https://arxiv.org/pdf/2402.13212)
[^anthropic-agents]: [Building Effective AI Agents — Anthropic](https://www.anthropic.com/engineering/building-effective-agents)
[^small-agentic-survey]: [Small Language Models for Agentic Systems: A Survey](https://arxiv.org/pdf/2510.03847)
[^selfconsistency-ceiling]: [Verify when Uncertain: Beyond Self-Consistency in Black Box Hallucination Detection](https://openreview.net/forum?id=6tlLISSgiu)
[^verifier-vs-selfcritique]: search-synthesized from the above plus contemporaneous 2025-26 hallucination-detection literature (cross-model/verifier consistency outperforming same-model self-critique); no single canonical paper — treat the general claim as `[UNVERIFIED]` pending Track-level confirmation, the *mechanism* (shared error modes) is directly sourced to [^selfconsistency-ceiling]
[^cast]: [CAST: Critique-Aware Supervision for Training Reliable Long-Horizon Tool-Calling Agents](https://arxiv.org/html/2608.30147v1)
[^tool-count]: [How Many Tools Should an LLM Agent See? A Chance-Corrected Answer](https://arxiv.org/html/2605.24660v1); [The Over-Tooled Agent Problem](https://tianpan.co/blog/2026-04-19-over-tooled-agent-problem)
[^tool-calling-benchmark]: [AI Agent Tool Calling Benchmarks on GPU Cloud: BFCL v4, tau-Bench](https://www.spheron.network/blog/tool-calling-benchmarks-bfcl-tau-bench-latency-optimization/)
[^gbnf-cost]: [When Correct Isn't Usable: Improving Structured Output Reliability in Small Language Models](https://arxiv.org/pdf/2605.02363)
[^confident-liar]: [The Confident Liar: Diagnosing Multi-Agent Debate with Log-Probabilities and LLM-as-Judge](https://arxiv.org/html/2606.10296)
[^semantic-entropy]: [A Survey of Confidence Estimation and Calibration in Large Language Models](https://arxiv.org/pdf/2311.08298)
[^abstain-med]: [Knowing When to Abstain: Medical LLMs Under Clinical Uncertainty](https://aclanthology.org/2026.eacl-long.291/)
[^mem0-paper]: [Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413)
[^mem0-types]: [Semantic vs Episodic vs Procedural Memory in AI Agents](https://mem0.ai/blog/semantic-vs-episodic-vs-procedural-memory-in-ai-agents-a-complete-comparison)
[^letta]: [Hindsight vs Letta (MemGPT): Agent Memory Compared (2026)](https://vectorize.io/articles/hindsight-vs-letta)
[^governance-decay]: [Governance Decay: How Context Compaction Silently Erases Safety Constraints in Long-Horizon LLM Agents](https://arxiv.org/abs/2606.22528)
[^auth-laundering]: [Agent Memory Is a Surface for Endogenous Authorization Laundering](https://arxiv.org/html/2609.01836) — title and mechanism confirmed via search snippet; full text not independently fetched (arXiv fetch blocked in this environment), treat detailed claims beyond the title/abstract framing as `[UNVERIFIED]`
[^trajectory-eval]: [Beyond the Final Answer: Evaluating the Reasoning Trajectories of Tool-Augmented Agents](https://arxiv.org/html/2510.02837v3); [AI Agent Evaluation (2026)](https://www.morphllm.com/ai-agent-evaluation)
[^judge-reliability]: [Reliability without Validity: A Systematic, Large-Scale Evaluation of LLM-as-a-Judge Models](https://arxiv.org/html/2606.19544v1)
[^prompt-caching]: [Context Engineering for Production AI Agents: KV Cache, Prefix Caching](https://www.spheron.network/blog/context-engineering-production-ai-agents-kv-cache-long-context/)
