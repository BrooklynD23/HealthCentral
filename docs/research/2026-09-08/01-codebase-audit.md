# Track 1 — Codebase capability audit

All paths are relative to `src/backend/` unless stated otherwise. Line numbers
verified 2026-09-08 by direct file read, not by memory or by trusting docstrings.

## Summary

The agent graph (`modules/agent/graph.py`) is real, and it is more
deterministic than the brief's own hypothesis assumed: **the entire
`plan → act → reflect → draft → guard → terminal` loop calls zero LLMs, not
just `plan`.** `draft` composes answer sentences by string-templating tool
output rows (`nodes/draft.py:69-119, 262-321`); `guard` filters and thresholds
those sentences mechanically (`guardrails/guard.py`); `reflect` checks for the
presence of `rows`/`points`/`chunks`/`status` keys in the last tool output
(`nodes/reflect.py:24-43`). The module's own guardrail docstring states this
outright: *"`run_agent` (graph.py) is fully local/deterministic... every tool
in `tools/` is read-only... `draft`/`guard` only compose/filter already-gathered
local evidence"* (`guardrails/redaction_gate.py:11-14`). In the entire product
codebase there is exactly **one** LLM generation code path —
`RAGModule.generate_response`/`RAGModule.query` → `ModelRunner.generate_async`
→ provider (`modules/rag.py:747-791, 1174-1298`) — and it is reached only by
the **legacy fallback** (`agent_enabled=False` or an agent exception,
`api/assistant.py:723-754`) and by `api/interpretations.py:442-452`, which
calls the same `RAGModule.query`. The agent path that serves `/assistant/chat`
by default therefore never touches a model at all; it is a fully auditable,
template-driven read-only query planner with a real step budget and a real
four-gate filter, wearing ReAct's shape without any of its generative risk.
The LLM layer (`core/llm/`) is a clean two-provider abstraction with zero
constrained-decoding surface, one real (unused) streaming implementation and
one fake one, and a facade (`ModelRunner`) that collapses every call into a
single unstructured user-role string. RAG retrieval is brute-force cosine
similarity with no reranking and no ANN index; a separate FTS5/BM25 keyword
search (`modules/search.py`) exists for record browsing and is entirely
disconnected from the answer pipeline. The audit trail is real, redacted by a
single allowlisted choke point (`core/audit.py:36-167`), lives in the
unencrypted master DB, and has **no read route anywhere in `api/`** — confirmed
by grep, not just by the brief. Test collection reproduces the baseline
exactly: **1245 tests collected, 0 errors**, verified live in this sandbox
using only pure-Python dependencies (no `llama-cpp-python`, no
`sentence-transformers` installed) — direct evidence that the entire LLM/embedding
stack is lazily imported and untouched at collection time. All 78
`tests/agent/` tests pass and run the real graph against a real in-memory
SQLite vault (`tests/agent/eval_harness.py:37-159`) — no node is mocked, and
because the graph itself never calls a model, **no test anywhere in the agent
suite exercises an LLM-backed path**. Two flags described in code comments as
NLI/LLM hooks — `VerifierAgent.use_llm_entailment` and
`core.config.settings.use_llm_entailment` — are both hardwired `False`,
disconnected from each other (the real `VerificationConfig` construction site,
`api/assistant.py:207-210`, never reads the settings field), and even the
method they'd gate, `_check_entailment_llm`, is a stub that calls the
rule-based path regardless (`modules/verifier_agent.py:304-317`).

---

## 1. The agent graph, end to end

### 1.1 Where an LLM gets called — verified, not just `plan`

Repo-wide grep for real inference call sites:

```
grep -rn "ModelRunner|model_runner\." --include="*.py" . | grep -v /tests/
```

Only two call sites reach a provider: `modules/rag.py:779`
(`RAGModule.generate_response`) and `modules/rag.py:1291`
(`RAGModule._generate_with_runner`, used by `RAGModule.query`). Neither is
inside `modules/agent/`. Confirmed by direct read of every file in
`modules/agent/`: `nodes/plan.py`, `nodes/act.py`, `nodes/reflect.py`,
`nodes/draft.py`, all 8 files in `tools/`, all 5 files in `guardrails/`,
`cache.py`, `audit.py`, `metrics.py` — none imports `core.model_runner` or
`core.llm`. `guardrails/redaction_gate.py:9-19` states this as a design
invariant verified "at S4 implementation time."

So the brief's hypothesis ("only `draft` calls a model") is **refuted in the
stronger direction**: nothing in the graph calls a model. `draft` composes
canned English sentences from tool-output dict fields
(`nodes/draft.py:69-80` for observations, `83-119` for trends, `122-259` for
care-tasks/med-changes/timeline) — string interpolation, not generation.

The only place a live model enters a user-facing answer is the **legacy
fallback path**: `api/assistant.py:731-754` tries `_serve_via_agent` first,
and on any exception (or when `agent_enabled=False`) falls through to
`rag.query(...)` at `api/assistant.py:755-769`, which is the RAG module's
`query()` → `_generate_with_runner()` → `ModelRunner.generate_async()` chain.
`api/interpretations.py:442-452` independently calls the same
`RAGModule.query()` for the per-observation "explain this result" feature —
not a new call site, the same one.

### 1.2 Control flow

`run_agent(question, ctx)` (`modules/agent/graph.py:144-227`):

1. **Pre-model advice gate** (`graph.py:168-172`): `classify_advice(question)`
   (deterministic keyword match, `guardrails/classifier.py:22,76`) on the raw
   question. A hit short-circuits directly to `terminal="escalate"` with the
   fixed `ESCALATE_TEMPLATE` — no plan/act/draft node runs at all.
2. **Loop** (`graph.py:176-214`), bounded by `for _ in range(MAX_STEPS + 1)`
   (defense-in-depth on top of `reflect`'s own budget enforcement):
   - `plan(question, run_log, ctx)` → `PlanDecision{action: call_tool|draft|abstain}`.
     `action="abstain"` returns `terminal="abstain"` immediately
     (`graph.py:183-188`), bypassing act/reflect for that turn.
     `action="draft"` breaks the loop (`graph.py:190-191`).
   - Otherwise `act(tool_name, tool_args, ...)` executes exactly one tool call
     (`graph.py:193-196`).
   - `reflect(run_log, ctx)` → `ReflectDecision{decision: loop|draft|abstain_budget}`.
     `abstain_budget` returns `terminal="abstain"` (`graph.py:204-209`); `draft`
     breaks the loop (`graph.py:211-212`); `loop` falls through to `plan` again.
3. **Draft**: `draft(question, run_log, ctx)` composes sentences+citations from
   every `act` step's logged output (`graph.py:216-219`).
4. **Guard**: `_guard_draft(...)` calls the real `guardrails.guard.guard()`
   four-step gate (`graph.py:221-224`), which returns the final
   `AgentTerminal`.

**Terminal states** (all three are first-class, schema-validated via
`AgentTerminal.terminal: Literal["answer","abstain","escalate"]`,
`schemas.py:32-42`):
- `escalate` — fixed `ESCALATE_TEMPLATE`, reached via (a) the pre-model advice
  gate (`graph.py:168-172`) or (b) the guard's advice gate on the draft
  (`guardrails/guard.py:102-124`).
- `abstain` — fixed `ABSTAIN_TEMPLATE`, reached via (a) `plan` deciding
  `action="abstain"` (`graph.py:183-188`, e.g. an analyte confirmed
  "unverified"), (b) `reflect` deciding `abstain_budget` (`graph.py:204-209`),
  (c) guard's groundedness gate finding zero surviving sentences
  (`guardrails/guard.py:126-144`), or (d) guard's confidence gate scoring
  below `CONFIDENCE_THRESHOLD` (`guardrails/guard.py:146-168`).
- `answer` — all four guard steps pass; text is the join of surviving
  sentences, never model-generated prose (`guardrails/guard.py:170-176`).

There is no path in `run_agent` that returns anything other than a
schema-validated `AgentTerminal`; a Python exception from within the agent
propagates up to `api/assistant.py`'s try/except and triggers the legacy
fallback (`api/assistant.py:743-752`), not a partial/undefined agent result.

### 1.3 `reflect` — mechanical grounding check

`_has_grounding(run_log)` (`nodes/reflect.py:24-43`) walks every `act` step's
logged `output` dict and returns `True` if it contains a non-empty `rows`,
`points`, or `chunks` key, **or** a `status` key equal to `"unverified"`/`"verified"`
(so a definitive `check_verification` answer counts as grounding even with no
rows). This is a dict key/truthiness check — no scoring, no LLM judgment, no
semantic reasoning about whether the evidence actually answers the question.
`reflect()` itself (`nodes/reflect.py:46-82`) then picks `draft` if grounded,
`abstain_budget` if `MAX_STEPS - act_count() <= 0`, else `loop`.

### 1.4 `MAX_STEPS` and budget exhaustion

`MAX_STEPS = 5` (`state.py:19`) — hard cap on `act` (tool) calls per question,
enforced two ways: `reflect` returns `abstain_budget` before a call that would
exceed the cap (`nodes/reflect.py:55-62`), and `act()` itself raises
`StepBudgetExceeded` if invoked after the budget is already spent
(`nodes/act.py:25-26, 43-44`) — the graph never calls `act` in that state
because `reflect` already stopped the loop, so this is defense-in-depth, not a
normally-reached path. `run_agent`'s own `for` loop is separately bounded to
`MAX_STEPS + 1` iterations (`graph.py:176`) as a third, independent backstop
against a planner bug spinning forever. At budget exhaustion the run always
terminates `abstain` with the fixed `ABSTAIN_TEMPLATE` — never a crash, never
a partial answer.

### 1.5 Tool `run` signature and state feedback

Every tool implements the structural `ReadOnlyTool` protocol
(`tools/base.py:25-37`): `name: ClassVar[str]`, `InputModel`/`OutputModel:
ClassVar[type[...]]`, and `async def run(self, args: ToolInput, ctx:
ToolContext) -> ToolOutput`. `act()` (`nodes/act.py:34-61`) looks the tool up
in the registry, validates raw args against `InputModel` via
`registry.validate_args` — **malformed args raise `pydantic.ValidationError`
before `run` is ever reached** (`tools/registry.py:32-39`) — then calls
`tool.run(validated_args, ctx)`, serializes the result with
`output.model_dump(mode="json")`, and appends a `RunStep(node="act",
payload={"tool_name": tool_name, "output": output_dict})` to `run_log.steps`
(`nodes/act.py:52-59`). All downstream nodes (`reflect`, `draft`) read this
`RunStep.payload` from `run_log.steps` — there is no other state channel; the
`RunLog` **is** the agent's working memory for a single turn.

8 tools are registered (`tools/registry.py:53-64`):
`query_observations`, `compute_trend`, `check_verification`,
`lookup_reference`, `retrieve_chunks`, `query_care_tasks`,
`query_medication_changes`, `query_timeline`. All are read-only, profile-scoped
via `ctx.db_session()`, and self-emit an `agent.act` audit event
(handles/counts only, never raw PHI — enforced centrally, see §5).

**Two registered tools are never selected by the deterministic planner.**
`_default_planner` (`nodes/plan.py:188-306`) only ever returns `tool_name` ∈
{`query_care_tasks`, `query_medication_changes`, `query_timeline`,
`compute_trend`, `query_observations`, `check_verification`} — `retrieve_chunks`
and `lookup_reference` are registered and fully functional
(`tools/retrieve_chunks.py`, `tools/lookup_reference.py`) but structurally
unreachable through the shipped planner. `nodes/draft.py:17-20` documents this
explicitly: composing their output "is left for later stories." They are only
exercised directly by tests (e.g. `eval/scorer.py`'s use of `plan`/`act`/`draft`
as library calls, not through the default planner's tool selection).

### 1.6 Cache, audit, metrics

- **`cache.py`** (`modules/agent/cache.py:29-74`): `CacheKey{normalized_question,
  profile_version}` (frozen pydantic model), exact-match only
  (`normalize_question` = lowercase/strip/collapse-whitespace,
  `cache.py:36-44` — not fuzzy or embedding-based), backed by an
  in-process `dict[CacheKey, AgentTerminal]` under a `threading.Lock`
  (`cache.py:47-48`) — no cross-process or cross-restart persistence, no PHI
  on disk. `profile_version` is the count of `Observation.user_verified=True`
  rows, computed by `api/assistant.py:552-564` (**not** by a
  `cache.profile_version_for` function — the cache module's own docstring
  references that name, `cache.py:9`, but no such function exists anywhere in
  the codebase; it's a stale cross-reference to the actual private helper in
  `api/assistant.py`).
- **`audit.py`** (`modules/agent/audit.py`): every node emits an
  `AgentAuditEvent` through `emit_audit_event()`, which forwards to
  `core.audit.create_audit_log` (the same central choke point every other
  audit event uses — see §5). `AGENT_NODE_ACTIONS` (`audit.py:41-46`) maps
  `plan`/`act`/`draft`/`reflect` to static action strings but has **no entry
  for `guard`** — a guard-node event falls through to the generic `"Agent
  step"` default (`audit.py:79`, `AGENT_NODE_ACTIONS.get(event.node, "Agent step")`).
  Not a bug (the event still records `gate_fired`/`terminal` in `details`),
  but an incomplete mapping worth closing alongside any other audit work.
- **`metrics.py`** (`modules/agent/metrics.py:15-32`): `record_node_timing`
  writes into the existing `monitoring.metrics.metrics_collector` keyed
  `agent.<node>`, surfaced on `GET /api/v1/monitoring/metrics`. Accepts a
  `tokens` param that is explicitly accepted-but-discarded
  (`metrics.py:26`, `_ = tokens # reserved for future token tracking`) —
  since the graph never calls a model, there is no token count to record yet.

### 1.7 Eval harness

`modules/agent/eval/scorer.py` scores every case in `tests/agent/golden/*.json`
(74 files, confirmed via `ls tests/agent/golden/*.json | wc -l`) on 6 axes:
`groundedness`, `citation`, `abstention` (all fractions, target 1.0),
`advice_leakage`, `phi_leakage` (counts, target 0), and `injection_resistance`
(fraction, target 1.0) — matching the brief exactly. `scripts/agent_eval_gate.py`
(repo root) imports this scorer for CI gating. Two additional end-to-end checks
run alongside the per-case scoring: `score_composed_drop_case`
(`eval/scorer.py:267-368`) drives a **real** `plan→act→draft` run then appends
one synthetic uncited sentence and feeds it through the **real**
`guardrails.guard.guard()` to prove the drop mechanism works live, not just in
a unit test that hand-calls `map_sentences`; `score_injection_compose_case`
(`eval/scorer.py:371-411`) exercises `RAGModule.compose_prompt` — the chat/RAG
surface, not the agent graph — to prove injection markers are neutralized
before entering a model prompt.

---

## 2. The LLM layer (`core/llm/`, `core/model_runner.py`)

### 2.1 Provider interface

`ProviderProtocol` (`core/llm/provider.py:73-151`, `@runtime_checkable`):
`capabilities() -> CapabilityFlags`, `is_available()`, `health_check()`,
`generate(messages, config)`, `generate_async(messages, config)`,
`generate_stream(messages, config) -> AsyncIterator[str]`, `load()`, `unload()`.
`CapabilityFlags` (`provider.py:26-46`) carries `context_len`, `multimodal`,
`function_calling`, `streaming`, `provider_name`, `model_name` — self-reported
per provider, not derived from a live probe of the model file.

Two concrete providers, selected by `core.llm.factory.get_provider()`
(`factory.py:25-75`) from `settings.llm_provider` (default `"llama_cpp"`):

- **`LlamaCppProvider`** (`core/llm/llama_cpp_provider.py`): lazy `llama_cpp`
  import (`_load_llama_class`, line 32-38), locates a GGUF by glob pattern in
  `settings.models_path` (`_find_model_path`, lines 71-99), checks the file
  against a pinned SHA256 advisory-only (`MODEL-INT-001`,
  `modules.model_integrity.verify_and_log`, lines 116-126 — logs a warning on
  mismatch, never blocks load), then constructs `Llama(model_path, n_ctx,
  n_threads, n_gpu_layers, verbose, chat_format="auto")` (lines 128-141).
  `capabilities().streaming` is **hardcoded `False`**
  (`llama_cpp_provider.py:193`, comment: "streaming support requires
  llama.cpp stream API"). `generate_stream()` (lines 297-302) is a **fake**
  implementation: it awaits the full `generate_async()` result and yields it
  as one chunk — not real token streaming.
- **`OllamaProvider`** (`core/llm/ollama_provider.py`): talks to
  `http://127.0.0.1:11434` over `httpx`; `_assert_localhost()`
  (lines 40-54) raises `ValueError` at construction if the base URL's
  hostname isn't in `{"localhost","127.0.0.1","::1","[::1]"}` — a hard,
  code-level privacy guard, not just a default. `capabilities().streaming` is
  `True` (line 159) and `generate_stream()` (lines 269-301) is **real**:
  `stream=True` against `/api/chat`, `aiter_lines()`, yields each token as it
  arrives.

**`generate_stream` is defined on both providers but has zero callers in
production code** — confirmed by
`grep -rn "generate_stream" --include="*.py" . | grep -v /tests/`, which
returns only the three definitions (protocol + two providers), no call site.
Neither the agent graph nor the RAG chat path streams a response; `/assistant/chat`
returns a complete `ChatResponse` in one shot. The Ollama provider's real
streaming implementation is fully wired at the provider layer and completely
unused above it — the cheapest possible path to a streaming `/assistant/chat`
endpoint when running Ollama, and a dead end when running the default
`llama_cpp` provider until real llama.cpp streaming is implemented.

### 2.2 Generation parameters exposed vs. hardcoded

`InferenceConfig` (`core/model_runner.py:31-38`): `max_tokens`, `temperature`,
`top_p`, `stop_sequences`, `timeout_seconds`. That is the complete surface
exposed to any caller. Confirmed by
`grep -rn "grammar|response_format|json_schema|GBNF|logits_processor|seed=|top_k|repeat_penalty|frequency_penalty|presence_penalty" core/llm/ modules/ core/model_runner.py`
— zero hits (the only `top_k` hits in the whole search are retrieval
`top_k` in `modules/rag.py`/`modules/embeddings.py`, an unrelated concept).
No seed (non-reproducible generation), no `top_k`/`repeat_penalty` sampling
controls, no grammar/JSON-schema constraint, no logit bias. Both providers'
`generate()` pass exactly `max_tokens`/`temperature`/`top_p`/`stop` through to
the underlying API (`llama_cpp_provider.py:237-243`,
`ollama_provider.py:130-142`) — there is no intermediate layer stripping
anything; the parameters simply were never added.

`ModelRunner.generate`/`generate_async` (`core/model_runner.py:135-221`) wrap
every call as `messages = [ChatMessage(role="user", content=prompt)]` — a
**single unstructured user message**. Even though `ChatMessage`/the provider
protocol supports a real system/user/assistant list, the facade every caller
uses collapses everything (system prompt + context + question, all already
concatenated into one string by `RAGModule.compose_prompt`) into one user
turn. A caller cannot ask `ModelRunner` for a proper system-role message, a
multi-turn chat array, or per-message metadata — that structure would have to
be added to the facade, not just to a caller.

### 2.3 Model load/unload

Lazy, per-provider: `LlamaCppProvider._ensure_initialized()`
(`llama_cpp_provider.py:101-153`) loads once and caches `self._model`;
`unload()` (lines 307-312) `del`s the model and resets `_initialized=False`.
`OllamaProvider` has no real load step — the daemon owns the model lifecycle;
`load()`/`unload()` (`ollama_provider.py:303-309`) just probe/clear the
availability cache. `core.llm.factory` caches one provider instance
module-level (singleton, `factory.py:22,37-38`); `reset_provider()`
(`factory.py:78-86`) unloads and discards it — used by tests/hot-reload, not
by any per-request logic. There is no model-swap-per-request mechanism and no
KV-cache save/load anywhere — confirmed, `llama_cpp_provider.py` passes only
`n_ctx`/`n_threads`/`n_gpu_layers` to `Llama(...)`; no `n_batch`, no
`save_state`/`load_state`, no prefix-cache reuse across calls.

### 2.4 What a caller cannot currently ask for (the extension surface)

- Structured/constrained output (grammar, JSON schema, function-calling
  despite `CapabilityFlags.function_calling` being set `True` for Gemma-4
  models at both providers — `llama_cpp_provider.py:187-196`,
  `ollama_provider.py:148-162` — the flag is advertised but nothing in
  `core/llm/` or `ModelRunner` implements tool-call parsing).
- Sampling controls beyond temperature/top_p (no `top_k`, no repetition
  penalty, no seed for reproducibility — relevant for eval-harness
  determinism if an LLM planner/drafter is ever added).
- Multi-message chat structure through the facade (`ModelRunner` flattens to
  one user message; only providers see role-structured `ChatMessage` lists,
  and only when called directly, bypassing the facade every current caller
  uses).
- KV-cache prefix reuse / session state across calls (no such concept exists
  at any layer).
- Real streaming for the default provider (`llama_cpp` — `OllamaProvider`
  already has it, unused).
- Per-request/per-node model routing (see §4 — tier selection is per-profile,
  not per-call).

---

## 3. RAG pipeline

### 3.1 Chunking (`modules/chunking.py`)

Sentence-boundary-respecting, overlapping chunker. `ChunkConfig` defaults:
`chunk_size=200` tokens (approx.), `chunk_overlap=50`, `min_chunk_size=20`,
`chars_per_token=4.0` (`chunking.py:14-21`). `_split_sentences` uses a regex
(`r'([.!?:])(?=\s+[A-Z]|\s*$)'`, `chunking.py:143`) to find sentence
boundaries; `_build_chunks_from_sentences` (lines 176-229) packs sentences
into chunks up to `target_chars = chunk_size * chars_per_token`, carrying
`overlap_chars` worth of trailing sentences into the next chunk
(`_get_overlap_sentences`, lines 231-251). Token counts are **estimated from
character count** (`len(text) / 4.0`, line 255), not a real tokenizer.

### 3.2 Embedding model (`modules/embeddings.py`)

`all-MiniLM-L6-v2` via `sentence_transformers.SentenceTransformer`, 384
dimensions, normalized (`EmbeddingsConfig`, `embeddings.py:16-21`). Lazily
loaded (`_ensure_initialized`, lines 49-71); **if `sentence-transformers` is
not importable, silently falls back to a deterministic hash-based bag-of-words
embedding** (`_embed_with_fallback`/`_hash_to_vector`, lines 138-218 —
unigram + bigram SHA-256 token hashing into the same 384-dim space, L2-normalized).
This fallback is the exact reason `test_api_rag_index_002b` fails outside CI
per the brief/CLAUDE.md baseline: the fallback embeddings are not semantically
meaningful, so cosine similarity between paraphrases stays below the test's
0.7 threshold. Confirmed in this sandbox: `sentence-transformers` is not
installed, and the file's own docstring for the fallback (lines 138-147)
states it is "not a replacement for real semantic embeddings."

### 3.3 Retrieval method — pure dense vector, no ANN, no reranking

`RAGModule.retrieve_context()` (`modules/rag.py:188-268`) assembles context
from three independent sources, concatenated (not merged/reranked against
each other):

1. **Vector search over user documents** — `_search_vectors_async`
   (`rag.py:515-614`): embeds the query, `SELECT Chunk JOIN Embedding JOIN
   Document` with optional date/analyte/category `WHERE` filters
   (lines 549-587), computes `cosine_similarity(query_vector, stored_vector)`
   **in Python, over every matching row fetched from SQL** (lines 594-609) —
   brute-force, no FAISS/sqlite-vec/ANN index of any kind — then
   `candidates.sort(key=..., reverse=True)` and slices `[:top_k]`
   (lines 612-614). **The similarity score is the final rank — there is no
   separate reranking step anywhere in this pipeline.**
2. **Synthetic "YOUR RESULTS" chunks from the profile's own `Observation`
   rows** — `_get_observation_chunks` (`rag.py:270-453`): for each analyte
   mentioned in the query (matched against `NormalizeModule.ANALYTE_SYNONYMS`),
   builds a formatted text block (latest value, reference range, flag, 3-point
   trend) with `relevance_score=0.95` (line 445 — a fixed constant, not a
   computed score) and `is_observation_summary=True`. Capped at 5 analytes
   (line 321).
3. **Curated reference-corpus chunks** — `_get_reference_chunks`
   (`rag.py:455-513`): looks up `BiomarkerKnowledge` rows from the master DB
   via `KnowledgeLoader` for each analyte mentioned in the query, fixed
   `relevance_score=0.8` (line 506).

Observation chunks are prepended so they get the lowest citation indices
("YOUR RESULTS" appears as `[1]`, `[2]`... before reference material) —
`rag.py:264-266`.

**`modules/search.py` is a separate system, not part of this pipeline.** It
implements FTS5 (with `bm25()` ranking, `search.py:359-375`) with a `LIKE`
fallback (lines 378-401) over a derived `search_records`/`search_records_fts`
table, used exclusively by `api/search.py` for the "search my records" browse
feature (confirmed: `grep -rln "from modules.search" api/ modules/` returns
only `api/__init__.py` and `api/search.py`). It is keyword/BM25 search for
record navigation, entirely disconnected from `RAGModule`'s answer-generation
retrieval. A future "hybrid retrieval" story would need to actually wire
these two systems together — they do not currently share a code path.

### 3.4 Citation composition

`compose_prompt()` (`rag.py:616-689`) labels each retrieved chunk
`[YOUR_RESULTS:N]` (observation summaries, line 636) or
`[{SOURCE_TYPE}:N]` e.g. `[REFERENCE:N]`/`[USER_DOCUMENT:N]` (line 640),
1-indexed in the order chunks were assembled (observations first, per §3.3).
The system prompt (`rag.py:123-140`) instructs the model to cite with
`[cite:N]` — the model is expected to reuse the same index `N` from the
source label it's citing. `validate_response()` (`rag.py:793-872`) then
extracts `[cite:(\d+)]` via regex (line 819), checks every citation ID is
`<= len(retrieved_chunks)` (lines 822-826), and requires every `report_facts`
segment to carry at least one citation (lines 828-833). This citation
contract depends on the model correctly echoing the label index — there is no
independent verification that citation `N` in the output actually corresponds
to the chunk the model meant; a model that miscounts indices produces a
citation that still passes `validate_response`'s bounds check but points at
the wrong source.

### 3.5 `_sanitize_chunk_text` — injection neutralization

`rag.py:723-745`. Applies only to `source_type in
("reference","user_document","user_observation")` (line 737) — i.e. every
chunk type that can contain attacker-influenceable text. Runs 4 compiled
regex patterns (`PROMPT_INJECTION_PATTERNS`, `rag.py:143-148`: instruction
override, system-prompt/jailbreak naming, safety-bypass phrasing, role-hijack
phrasing) and **substitutes** each match with the literal string
`[UNTRUSTED-INSTRUCTION-REMOVED]` (lines 741-744) — it does not drop the whole
chunk, preserving the surrounding citable prose while defanging the embedded
instruction. The same pattern list is reused (imported, not copied) by
`modules/agent/guardrails/redaction_gate.sanitize_untrusted_field`
(`redaction_gate.py:80`) and by the eval scorer's `injection_resistance` axis
(`eval/scorer.py:158-173`) — one source of truth for what counts as an
injection marker across the chat surface, the agent surface, and the eval.

---

## 4. Model tier system

### 4.1 `TIER_MODEL_CONFIG` — actual contents

`modules/model_selector.py:50-116` — **6 configured entries**, not the "3 real
+ 3 alt" the brief's Gemma-4-26B-MoE framing might suggest:

| tier id | model | context | multimodal/fn-call | notes |
|---|---|---|---|---|
| `low` | Qwen2.5-0.5B-Instruct GGUF | 2048 | no | default |
| `gemma4-e2b` | Gemma 4 E2B (placeholder HF repo) | 8192 | yes | |
| `gemma4-e4b` | Gemma 4 E4B (placeholder HF repo) | 16384 | yes | |
| `mid` | Phi-3-mini-4k-instruct | 4096 | no | |
| `gemma4-12b` | Gemma 4 12B (placeholder HF repo) | 32768 | yes | |
| `high` | BioMistral-7B | 4096 | no | |

`n_gpu_layers: 0` for every single entry — CPU-only by config default across
the board.

**Doc/code divergence on the "26B-MoE" claim** (see §7): "Gemma-4-26B-MoE
(A4B active)" appears **only in a comment** describing the general Gemma 4
model family (`model_selector.py:39`, `core/config.py:106`), never as a key
in `TIER_MODEL_CONFIG` and never referenced by `TIER_REQUIREMENTS`/`TIER_ORDER`
in `modules/hardware_detection.py`. There is no 26B or 31B tier configured
anywhere; the largest configured tier is `gemma4-12b`.

### 4.2 Tier selection

Hardware gating: `TIER_REQUIREMENTS` (`hardware_detection.py:27-34`, RAM+disk
minimums per tier) and `TIER_ORDER` (line 38, highest→lowest:
`high, gemma4-12b, mid, gemma4-e4b, gemma4-e2b, low`).
`get_recommended_tier_from_hardware()` (lines 337-355) walks `TIER_ORDER` and
returns the first tier whose RAM/disk requirements are met by
**effective RAM** — physical RAM plus a capped GPU-VRAM boost when VRAM ≥ 8GB
(`_effective_ram_gb`, lines 49-55, boost capped at +24GB). `can_run_tier()`
(lines 320-334) checks one specific tier the same way.

`ModelSelector.get_active_tier()` (`modules/model_selector.py:321-357`):
priority is **user preference** (if `can_run_tier` allows it) → **hardware
recommendation** → `"low"` default. This is re-evaluated on every call — so
the effective tier *can* change between requests if hardware detection state
or the stored preference changes — but it is **not per-request or per-node
routing**: one tier is chosen for the whole profile/session, not per
question or per agent step, confirming the brief's gap G3. Since the agent
graph itself never calls a model (§1), tier selection today only ever affects
the legacy RAG fallback path.

### 4.3 API surface restricts to 3 tiers

`api/model_settings.py:116-131`: `TierSetRequest`/`TierDownloadRequest` both
constrain `tier` with `pattern="^(low|mid|high)$"` — the Gemma-4 alt tiers
are registered/readable in `TIER_MODEL_CONFIG` but **not selectable or
downloadable** through this API. `docs/model_tiers/README.md` states this
restriction explicitly and accurately (no divergence there): "the current
set/download request schemas only accept `low`, `mid`, and `high`." Runtime
provider switching is a **separate, orthogonal mechanism**:
`PUT /api/v1/settings/model/provider` (`api/model_settings.py:778-800`)
changes `LLM_PROVIDER`/`LLM_MODEL` directly (llama_cpp ↔ ollama, or an
arbitrary model string), independent of the tier system entirely — two
overlapping "which model do I run" knobs that don't share validation or
state.

### 4.4 `UserModelSettings` interaction

`models/model_settings.py:17` — `UserModelSettings(ProfileDatabaseBase)`,
stored in the **per-profile encrypted SQLCipher DB**, not the master DB.
Columns include `preferred_tier` (default `"low"`), `auto_detect_enabled`,
`last_hardware_json`/`last_detection_at` (cached hardware snapshot), and
`agent_enabled` (`model_settings.py:131`, added by migration
`009_agent_enabled`, comment references RECONCILIATION R-8 — the same row
that gates the agent-vs-legacy path in §1.1 lives alongside the tier
preference). `ModelSelector.set_user_preference`/`get_user_preference`/
`save_hardware_detection` (`model_selector.py:210-319`) are the only writers.

---

## 5. Data/audit plane

### 5.1 Audit events and storage

`core/audit.py` is the **single choke point** every audit call site funnels
through — `create_audit_log()` (lines 198-263) is called by every
`log_*_event` convenience function (`log_profile_event`, `log_document_event`,
`log_observation_event`, `log_care_task_event`, `log_pinboard_event`,
`log_export_event`, `log_auth_event`) and directly by
`modules/agent/audit.emit_audit_event` (§1.6). Before anything is written,
`_scrub_action()` (lines 170-189) replaces any `action` string not in the
`ALLOWED_ACTIONS` frozenset (lines 36-63, ~40 static templates covering
profile/document/observation/agent-node/care-task/pinboard/export/auth/backup
events) with the static `event_type` instead, and `_scrub_details()`
(lines 115-167) allowlist-filters the `details` dict against
`ALLOWED_DETAIL_KEYS` (lines 86-106: ids, counts, enums, booleans only — no
free text, no filenames, no analyte/medication names) using a bounded
`^[A-Za-z0-9_.:/\-]{1,64}$` regex on every surviving string value
(`_ENUM_VALUE_RE`, line 109). This is PHI minimization enforced in code, not
by convention — a new call site inherits it automatically.

`AuditLog` (`models/audit.py:20-72`) lives in the **master (unencrypted) DB**
— it extends `core.database.Base` (not `ProfileDatabaseBase`) and
`profile_id` is a nullable `ForeignKey("profiles.id", ondelete="CASCADE")`
(lines 39-44). This is the one place patient-linked data crosses the
SQLCipher encryption boundary, which is why the PHI-minimization allowlist in
§5.1 exists — audit rows can only ever carry handles/counts, never raw
clinical text, precisely because the table itself is unencrypted.

### 5.2 No audit read route — confirmed by grep, not assumption

```
grep -rn "AuditLog\b" api/*.py
```
returns exactly one hit outside `api/backup.py`: `api/profiles.py:909`,
`delete(AuditLog).where(AuditLog.profile_id == profile_id)` — a **delete**
inside profile deletion, not a read. No `select(AuditLog)` appears in any
`api/*.py` file. There is no GET route anywhere that returns audit rows to a
client. This fully confirms brief gap G7 at the code level, not just by
absence of a router file.

### 5.3 Deterministic analytics (not audit, adjacent)

`modules/analytics.py` — trend/delta/abnormal-event calculations for chart
data, explicitly deterministic (`analytics.py:61-67`, "no LLM involved").
Not part of the audit trail; included here because it's the other
data-summarization surface a "data control plane" story would touch.

### 5.4 Export surface — what's exposed over HTTP today

`api/export.py` (1295 lines) exposes, all profile-scoped and none calling an
LLM (confirmed: `grep -n "model_runner|ModelRunner|generate_async" api/export.py
modules/export.py modules/fhir_export.py` → no hits):

- `POST /doctor-summary` + `GET /doctor-summary/{id}/download`
- `POST /questions` (question-prep list)
- `POST /visit-prep` + `GET /visit-prep/{id}/download`
- `GET /csv`, `GET /json`
- `POST /fhir` + `GET /fhir/{id}/download` (`modules/fhir_export.py` backs the
  FHIR bundle construction)

`api/backup.py` exposes `GET /` (list), `POST /` (create), `POST /{id}/verify`,
`GET /{id}/download`, `POST /{id}/restore`, `POST /prune`,
`GET`/`PUT /schedule`. Restore requires password re-authentication plus a
confirmation phrase (`backup.py:363-414`). `download_backup`
(`backup.py:313-360`) streams an in-memory zip and audits
`export_type="backup_archive"` (lines 348-354); its docstring notes the
archive source directory is already scoped to one profile's rows at backup
**creation** time (`scripts.backup.backup`), not re-scoped at download —
current code is consistent with that invariant, not merely aspirational.

---

## 6. Test topology

### 6.1 `tests/agent/` — count and character

8 test files + `conftest.py` + `eval_harness.py` + 74 golden-case JSON files
under `tests/agent/golden/`. Collected count, verified live:

```
python -m pytest tests/agent/ -p no:cacheprovider -q --collect-only
→ 78 tests collected in 0.57s
```

Ran the full subset (not the full 1245-test suite, per the task's
run-nothing-slow constraint — 78 tests is a small, fast slice):

```
python -m pytest tests/agent/ -p no:cacheprovider -q
→ 78 passed, 6 warnings in 27.86s
```

(The 6 warnings are `PytestUnhandledThreadExceptionWarning` from
`aiosqlite`'s connection-worker thread on event-loop teardown between test
functions — cosmetic, not test failures.)

**These are real graph runs, not mocked nodes.** `tests/agent/eval_harness.py:37-118`
(`build_vault`) creates a fresh in-memory `sqlite+aiosqlite://` engine per
case, runs `ProfileDatabaseBase.metadata.create_all`, and seeds real
`Document`/`Observation`/`Chunk` rows from the golden case's `vault` block.
`run_golden_case()` (lines 121-159) then calls the actual `run_agent(question,
ctx)` against that real database through a real `RunContext` — no node is
patched, mocked, or stubbed. Since the graph itself never calls a model
(§1.1), **no test in `tests/agent/` exercises an LLM-backed path** — this
isn't a testing gap, it's a direct consequence of the graph being
model-free.

### 6.2 LLM-layer tests are fully mocked

`grep -rln "generate_async|ModelRunner" tests/` finds 7 files (excluding
`__pycache__`): `test_redaction.py`, `test_llm_provider_layer.py`,
`test_rag_pipeline.py`, `test_external_runner.py`, `test_visit_note_extraction.py`,
plus 2 more. `test_llm_provider_layer.py` uses `unittest.mock.MagicMock` for
the `Llama` class itself (line 110) and mocked `httpx` responses for the
Ollama client (lines 330-410) — no real GGUF file and no real Ollama daemon is
ever exercised anywhere in the suite. Combined with §6.3, this means the
distinction the brief/CLAUDE.md baseline draws — "1245 pass in CI with a real
embedding model, 1244 without" — applies **only** to the embedding model
(`sentence-transformers`, §3.2); there is no equivalent "real vs. fallback"
split for text generation anywhere in the test suite, because generation is
always mocked.

### 6.3 Full-suite collection — reproduced live

Task instruction: run `--collect-only` and report the actual number, honestly,
even if collection errors on missing deps. This sandbox initially had no
`pytest` installed at all (`ModuleNotFoundError`). After installing `pytest`
+ `pytest-asyncio` only:

```
python -m pytest tests/ -p no:cacheprovider -q --collect-only
→ 255 tests collected, 65 errors in 2.16s
```

All 65 errors were `ModuleNotFoundError: No module named 'pydantic_settings'`
(traced through `core/config.py:12`) — a missing pure-Python dependency, not a
code defect. Installing the **remaining pure-Python** requirements
(`fastapi`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `alembic`,
`sqlcipher3-binary`, `cryptography`, `PyJWT`, `httpx`, etc. — the full
`requirements.txt` list **minus** `llama-cpp-python`, `sentence-transformers`,
and `torch`) and re-running:

```
python -m pytest tests/ -p no:cacheprovider -q --collect-only
→ 1245 tests collected in 2.04s
```

**Exactly 1245, zero errors — matching the documented baseline exactly**,
achieved deliberately **without** `llama-cpp-python` or `sentence-transformers`
installed. This is direct, positive evidence (not an assumption) that every
import of those two packages in the codebase is lazy/deferred (confirmed at
the source level in §2.1/§3.2: `_load_llama_class()`,
`EmbeddingsModule._ensure_initialized()`) — collection never touches them.
Per the task constraint, the full 1245-test suite was **not executed** (only
collected); the `tests/agent/` subset (78 tests, §6.1) was run to completion
as a bounded, fast verification of real-graph behavior.

---

## 7. Dead ends and scaffolding

### 7.1 `modules/faithfulness.py` / `modules/verifier_agent.py` — HC-M11 stub boundary (read-only, per CLAUDE.md)

Both modules are **fully rule-based today**, with an NLI/LLM hook that is
disconnected at every layer it would need to pass through to matter:

1. `VerificationConfig.use_llm_entailment: bool = False`
   (`modules/verifier_agent.py:88`) — the per-call switch `_check_entailment()`
   reads (`verifier_agent.py:213-226`) to choose `_check_entailment_llm` vs.
   `_check_entailment_rules`.
2. **Even if flipped**, `_check_entailment_llm()` (`verifier_agent.py:304-317`)
   is a stub: despite its docstring "LLM-based entailment checking... Uses
   secondary LLM to evaluate claim-source relationship," the body is exactly
   `return self._check_entailment_rules(claim, source)` — it calls the
   rule-based path regardless. There is no LLM call anywhere in
   `verifier_agent.py` (confirmed: no `ModelRunner`/`model_runner` import in
   the file).
3. A **second, independent copy** of the same flag exists at
   `core.config.settings.use_llm_entailment` (`core/config.py:152`, with a
   comment pointing at `docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md`
   Area 1 for "planned NLI wiring"). **This settings field is never read
   anywhere** — `grep -rn "use_llm_entailment"` outside `verifier_agent.py`
   and `core/config.py` returns nothing. The real `VerificationConfig`
   construction site, `api/assistant.py:207-210`
   (`VerificationConfig(min_faithfulness_score=0.6, fail_on_contradiction=True)`),
   never passes `use_llm_entailment` at all, so it silently takes the
   dataclass default (`False`) regardless of what `settings.use_llm_entailment`
   holds. Setting `USE_LLM_ENTAILMENT=true` in `.env` today would do
   **nothing** — it's a fully dead configuration knob, disconnected from its
   own consumer.
4. `modules/faithfulness.py`'s analogous seam — `score_claim(...,
   entailment_scores: Optional[list[float]] = None)` (`faithfulness.py:99-108`)
   — is designed to accept pre-computed real NLI scores and fall back to
   `_calculate_pseudo_entailment` (lexical/pattern matching,
   `faithfulness.py:120-121,191-...`) only when they're absent. **No
   production call site ever passes `entailment_scores`**
   (`grep -rn "entailment_scores=" --include="*.py" . | grep -v /tests/` →
   no hits) — the pseudo-entailment lexical fallback is not a fallback in
   practice, it is the only path ever exercised.

Net: this is a real, load-bearing rule-based verifier (contradiction-pattern
matching, negation detection, value-extraction matching, lexical overlap
scoring — `verifier_agent.py:102-128,228-302`) with a genuine seam for a real
NLI model, but the seam itself is a documented no-op stub at its deepest
point, and the flag meant to switch it on is disconnected from the object it
would configure. **Per CLAUDE.md, this section was produced read-only —
no edits were made to either file.**

### 7.2 Stale scaffold docstring

`modules/agent/__init__.py:1-18` — the module docstring reads *"SCAFFOLD
ONLY. Bodies raise NotImplementedError; feature logic lands sprint by
sprint."* This describes Phase-0 state and is now false: every node
(`plan`/`act`/`reflect`/`draft`), every one of the 8 tools, and the full
`guardrails/` gate are implemented and covered by 78 passing tests (§6.1).
`grep -rln "NotImplementedError" --include="*.py" . | grep -v /tests/`
confirms the string appears **only in this docstring**, nowhere in actual
tool/node bodies. Low-risk but genuinely misleading to a reader who trusts it
over reading the code — worth a one-line docstring fix whenever this file is
next touched for a real reason.

### 7.3 Dead config flag: `ai_assisted_lab_extraction`

`core/config.py:120` — `ai_assisted_lab_extraction: bool = False`. Repo-wide
search (`grep -rn "ai_assisted_lab_extraction" .`, excluding `.git/`) finds
**only this one declaration** — not read by any module, any route, or any
test. Fully inert.

### 7.4 Two registered-but-unreachable agent tools

Covered in §1.5: `retrieve_chunks` and `lookup_reference` are real,
functional, audited, read-only tools that the shipped deterministic planner
never selects. Not a stub in the NotImplementedError sense — they work if
called — but they are dead code from the default agent path's perspective
today, and the natural place an LLM-backed planner (brief gap G1) would first
prove itself is by actually reaching these two tools.

---

## Doc/code divergences

| Claim | Source | Actual state | File:line |
|---|---|---|---|
| "Gemma-4-26B-MoE (A4B active) appears in `TIER_MODEL_CONFIG`" | `00-brief.md` §2 gap 5 | 26B/31B never appear as a config key; only named in a descriptive comment about the general Gemma 4 model family. Largest configured tier is `gemma4-12b`. | `modules/model_selector.py:39,50-116`; `core/config.py:106` |
| Only `draft` calls a model | `00-brief.md` §2 gap 1 hypothesis (stated as needing verification) | Refuted in the stronger direction: **nothing** in the agent graph calls a model, including `draft`. `draft` is pure string-template composition. | `modules/agent/nodes/draft.py:69-119,262-321`; `modules/agent/guardrails/redaction_gate.py:11-19` |
| `modules/agent/cache.py`'s own docstring names `modules.agent.cache.profile_version_for` | `modules/agent/cache.py:9` | No such function exists anywhere in the repo. The real implementation is the private `api/assistant.py::_profile_version`. | `modules/agent/cache.py:9` vs. `api/assistant.py:552-564` |
| "SCAFFOLD ONLY. Bodies raise NotImplementedError" | `modules/agent/__init__.py:3` | Stale — every node/tool/guardrail is fully implemented; the string appears nowhere in actual code. | `modules/agent/__init__.py:1-18` |
| `AGENT_NODE_ACTIONS` implies every agent node has a mapped audit action | `modules/agent/audit.py:41-46` (docstring says "AUDIT-PHI-001") | `guard` has no entry; guard events log the generic `"Agent step"` action (details still carry `gate_fired`/`terminal`, so no data is lost, but the action string is less specific than for other nodes). | `modules/agent/audit.py:41-46,79` |
| `settings.use_llm_entailment` suggests an env-togglable NLI mode | `core/config.py:152` | Never read outside its own declaration; the live `VerificationConfig` is constructed with hardcoded kwargs that omit it. Toggling the env var has zero effect. | `core/config.py:152` vs. `api/assistant.py:207-210` |

---

## Extension points

Each row: the exact file:line where a future capability would plug in, and
the contract it must satisfy today.

| Capability | File:line | Current contract |
|---|---|---|
| **LLM-backed planner** (close brief gap G1) | `modules/agent/nodes/plan.py:314-319` (`Planner = Callable[[str, RunLog], PlanDecision]`, injected via `plan(..., planner: Planner = _default_planner)`) | Must return a `PlanDecision{action: "call_tool"\|"draft"\|"abstain", tool_name, tool_args, abstain_reason}` synchronously (or the caller awaited — check call site). Tool name must exist in `tools/registry.py`; args must validate against that tool's `InputModel` or `act()` will reject them (`nodes/act.py:47`). No prompt/context assembly exists yet for this seam — a real implementation needs its own prompt template, not reuse of `RAGModule.SYSTEM_PROMPT`. |
| **LLM-backed draft** (natural-language answer instead of templated sentences) | `modules/agent/nodes/draft.py:262` (`async def draft(question, run_log, ctx) -> Draft`) | Must return `Draft{sentences: list[str], citations: list[Citation]}` where `citations` is **parallel to `sentences` by index** — `guardrails/groundedness.map_sentences` (`guardrails/groundedness.py:42-65`) walks both lists by matching index and drops any sentence whose same-index citation is missing/empty. Any generative drafter MUST preserve this 1:1(+trailing) alignment or every sentence gets silently dropped by the groundedness gate. |
| **Constrained decoding / structured output** | `core/llm/llama_cpp_provider.py:237-243` (`create_chat_completion(...)` call) and `core/llm/ollama_provider.py:130-142` (`_build_request_body`) | Neither passes `grammar`/`response_format`/`json_schema` today. `llama-cpp-python`'s `create_chat_completion` supports a `grammar=` kwarg (GBNF) natively; Ollama's `/api/chat` supports a `format` field (`"json"` or a JSON schema) — both are additive, not breaking, changes to these two functions. `InferenceConfig` (`core/model_runner.py:31-38`) would need a new optional field threaded through both providers and `ModelRunner.generate*`. |
| **Real streaming for the default provider** | `core/llm/llama_cpp_provider.py:297-302` (`generate_stream`, currently fake) | `llama-cpp-python`'s `create_chat_completion(..., stream=True)` yields an iterator of partial-completion dicts — the real implementation pattern already exists next door in `OllamaProvider.generate_stream` (`ollama_provider.py:269-301`) to copy. No caller exists yet above the provider layer (`ModelRunner` has no `generate_stream` method at all) — wiring a caller is a separate, larger change than fixing the provider. |
| **Per-request/per-node model routing** (close gap G3) | `modules/model_selector.py:321-357` (`get_active_tier`) and `core/llm/factory.py:25-75` (`get_provider`, module-level singleton) | Today one provider/tier is resolved per profile and cached as a singleton. Per-node routing (e.g. a small model for `plan`, a larger one for `draft`) needs `ModelRunner`/`factory.get_provider()` to accept a routing hint and would break the singleton-cache assumption — every current caller expects one shared instance. |
| **KV-cache / prefix reuse across agent steps** (close gap G4) | `core/llm/llama_cpp_provider.py:131-141` (`Llama(...)` construction — no `n_batch`, no session save/load) | `llama-cpp-python`'s `Llama` object exposes `save_state()`/`load_state()`, unused here. Since the graph currently issues zero model calls per turn (§1.1), this only becomes relevant once a generative planner/drafter is added — at that point each `act` iteration would re-encode a near-identical system prompt, which is exactly the reuse opportunity. |
| **User-facing audit/data-control surface** (close gap G7) | `core/audit.py:198-263` (`create_audit_log`, the only writer) — no reader exists | A new `GET /api/v1/audit` (or similar) route would `select(AuditLog).where(AuditLog.profile_id == ...)` — straightforward given the schema (`models/audit.py:20-72`), but every `details_json` field must be surfaced through the same allowlist philosophy already enforced on write (`core/audit.py:86-106`) since the table itself is unencrypted; no new PHI-shaped field should reach a response body that wasn't already permitted into `details` at write time. |
| **Tool use for `retrieve_chunks`/`lookup_reference`** | `modules/agent/nodes/plan.py:188` (`_default_planner`) | Both tools are fully implemented and registered (`tools/registry.py:53-64`) but never selected. Extending `_default_planner`'s keyword rules — or replacing it with an LLM planner — to route free-text/general-knowledge questions to these tools is the lowest-risk way to broaden the agent's coverage without touching guardrail code. |
