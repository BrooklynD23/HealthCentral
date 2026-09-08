# Track 2: Local inference and serving infrastructure

Read `00-brief.md` first for verified repo state and binding constraints. This
document does not restate that premise except where it needed correction —
see the note on §4.

## Summary

The agent loop (`modules/agent/graph.py`) is, today, **entirely LLM-free**:
`plan` ([plan.py](../../../src/backend/modules/agent/nodes/plan.py)) is
keyword matching, `reflect` is a dict-key check, `draft` is sentence
templating, and `guard`'s advice/groundedness gates
([classifier.py](../../../src/backend/modules/agent/guardrails/classifier.py),
[groundedness.py](../../../src/backend/modules/agent/guardrails/groundedness.py))
are regex and citation-index arithmetic. The only place a model is actually
invoked today is the legacy single-shot path (`modules/rag.py`),
`modules/extract_visit_notes.py`, and the opt-in `core/external_runner.py`.
Every recommendation below is therefore about **what a future LLM-backed
node should do**, landing on the one seam the repo already built for this:
`plan()`'s injectable `planner: Planner = _default_planner` parameter
([plan.py:311-320](../../../src/backend/modules/agent/nodes/plan.py#L311-L320)).

Five findings, one per area:

1. **Structured decoding**: use llama-cpp-python's native
   `response_format={"type":"json_object","schema":...}` path (GBNF under the
   hood), one grammar pre-compiled per tool at process start. It measurably
   slows CPU decode (roughly 60-78% fewer tok/s in published benchmarks) but
   the payload is ~20-80 tokens, so the absolute cost is small. The critical
   finding: llama.cpp's own server **fails open** on grammar-parse failure —
   generates unconstrained free text with no error
   ([ggml-org/llama.cpp#19051](https://github.com/ggml-org/llama.cpp/issues/19051))
   — so the repo-side fallback must be a Pydantic `model_validate_json()`
   check after generation, not trust in the grammar alone; on any failure,
   fall back to the existing deterministic `_default_planner`, never raise.
2. **KV cache**: the provider is already a process-wide singleton
   ([factory.py:22-38](../../../src/backend/core/llm/factory.py#L22-L38)), so
   consecutive same-prefix calls already get llama.cpp's built-in prefix
   reuse for free — *if* prompts are built stable-prefix-first. llama-server's
   slot/`--cache-reuse` machinery doesn't apply (this repo embeds the library,
   it doesn't run a server). The hard constraint: llama-cpp-python's on-disk
   KV cache (`LlamaDiskCache`, via `diskcache`) is **unencrypted** and would
   put PHI-derived state outside the SQLCipher vault — it must never be used
   here.
3. **Routing**: the actual node shapes (plan=structured/short,
   act=no LLM, reflect=binary, draft=long/quality, guard=classification) map
   cleanly onto a two-model split — a small "fast" tier for plan/reflect,
   the user's selected tier for draft, and **guard staying non-LLM**, which
   is already correct and should stay that way. Speculative decoding and
   multi-model concurrent GPU serving (vLLM/SGLang) don't fit this app's
   CPU-first, `n_gpu_layers=0`-by-default posture.
4. **MoE**: correcting the brief's framing —
   [`TIER_MODEL_CONFIG`](../../../src/backend/modules/model_selector.py#L50-L116)
   does **not** actually contain a Gemma-4-26B-MoE entry; it's mentioned only
   in comments
   ([model_selector.py:39,42](../../../src/backend/modules/model_selector.py#L39-L42))
   and absent from `docs/model_tiers/README.md`'s tier table. The gap is more
   basic than "unexploited architecture" — it isn't a selectable tier at all.
   And on investigation, it shouldn't become one: total params (26B, ~16GB at
   Q4_K_M) govern disk/RAM regardless of the 3.8B active, so it needs a
   32GB+ floor for roughly a 4B-dense-model's generation quality/speed. A
   dense model at the same active size is strictly better on this hardware.
5. **Quantization**: Q4_K_M remains the right default (already what every
   tier ships) — ~92-95% perplexity retention, best-supported, predictable
   CPU speed. The one real free upgrade: Unsloth Dynamic 2.0/3.0 GGUFs
   (per-layer mixed precision) beat uniform Q4_K_M at the *same file size*
   for architectures they cover — a filename/repo change in
   `TIER_MODEL_CONFIG`, not new code, when a build exists for the target
   model.

---

## 1. Structured / constrained decoding

### Verified repo state

`grep -rn "grammar\|response_format\|json_schema\|GBNF\|logits_processor" core/llm/ modules/` returns nothing (re-verified this session). `LlamaCppProvider.generate()`
calls `create_chat_completion(messages=..., max_tokens=..., temperature=...,
top_p=..., stop=...)` with no `response_format`
([llama_cpp_provider.py:237-243](../../../src/backend/core/llm/llama_cpp_provider.py#L237-L243)).
`requirements.txt` pins only `llama-cpp-python>=0.2.0` — an unbounded floor
that predates reliable JSON-schema mode. `OllamaProvider._build_request_body`
([ollama_provider.py:130-142](../../../src/backend/core/llm/ollama_provider.py#L130-L142))
sends no `format` field either. Every one of the agent's 8 tools already
exposes a typed Pydantic `InputModel`
([tools/base.py:16-20](../../../src/backend/modules/agent/tools/base.py#L16-L20)),
validated in `tools/registry.py:validate_args()` — this is the schema a
constrained planner would target; it's not new work to define.

### The landscape

**llama.cpp / llama-cpp-python native GBNF.** `response_format={"type":
"json_object", "schema": {...}}` on `create_chat_completion` triggers
`LlamaGrammar.from_json_schema()` internally, masking invalid tokens at every
decode step
([discussion #1173](https://github.com/abetlen/llama-cpp-python/discussions/1173),
[instructor guide](https://python.useinstructor.com/integrations/llama-cpp-python/)).
Already ships with the pinned dependency family — zero new packages. Overhead
on CPU without GPU offload is real: one report measured throughput dropping
from ~80 tok/s to ~30 tok/s with a JSON grammar, another from 80.16 to 17.79
tok/s
([Ekansh Jain, "Squeezing Every Drop of Performance out of llama.cpp"](https://medium.com/@ekansh.jain2011/squeezing-every-drop-of-performance-out-of-llama-cpp-the-practitioners-guide-to-local-ai-2bcc3663f06f);
[abetlen/llama-cpp-python discussion #1376](https://github.com/abetlen/llama-cpp-python/discussions/1376)).
Some users report the gap closing with full GPU offload, which doesn't apply
to this repo's `n_gpu_layers: 0` default across every tier
([model_selector.py:56,66,79,91,101,113](../../../src/backend/modules/model_selector.py)).
Grammars can also pathologically stall on certain repetitive patterns
([llama.cpp grammars README](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md);
["Lost in Space: Optimizing Tokens for Grammar-Constrained Decoding"](https://arxiv.org/html/2502.14969v1)).

**llguidance.** Now built into llama.cpp core (`cmake -DLLAMA_LLGUIDANCE=ON`,
requires Rust/cargo) — a Rust Earley-parser token-mask engine, ~50μs/token,
near-zero startup cost, JSON Schema and Lark CFGs
([llama.cpp docs/llguidance.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/llguidance.md);
[guidance-ai/llguidance](https://github.com/guidance-ai/llguidance)). Its
documented failure mode is the opposite of vanilla GBNF's: "unsupported
schemas generate errors rather than silently ignoring keywords" — fails
*closed*, which is the safer default for a health app. But this is a
`llama-server`/C++ build flag, not something the pip wheel
`llama-cpp-python` (what this repo imports) exposes today as far as these
searches could confirm — adopting it means building `llama-server` from
source with a Rust toolchain and talking to it over HTTP, which is a new
process and a new native build dependency. **[UNVERIFIED]** whether current
`llama-cpp-python` wheels wire this through Python.

**XGrammar / Outlines / LM Format Enforcer.** All three target
vLLM/SGLang/TensorRT-LLM/Transformers integration primarily. XGrammar is now
the default structured backend for those three engines, under 40μs/token
([XGrammar-2 paper](https://arxiv.org/pdf/2601.04426)); a September 2025
benchmark had it edging out llguidance on repeated-schema caching, while the
JSONSchemaBench paper found llguidance ("Guidance") fastest and most
schema-compliant overall, and Outlines weakest — compilation times of 40s to
10+ minutes on complex schemas, causing timeouts
([JSONSchemaBench](https://arxiv.org/html/2501.10868v1)). None of the three
integrate with llama-cpp-python's chat-completion path directly; the only
clean seam is llama-cpp-python's `logits_processor` callback on
`create_completion`, which is exactly how LM Format Enforcer integrates today
([ggml-org/llama.cpp discussion #3665](https://github.com/ggml-org/llama.cpp/discussions/3665)).
That's a real integration point that adds *no new layer* (CLAUDE.md rule 2)
since it plugs into the existing provider's existing call, but it is a new
Python dependency for a benefit (faster masking) that's dwarfed by CPU
matmul cost at this app's model sizes — not worth it as a first move.

**Compiled once or per request?** In llama-cpp-python's own
`response_format` path, the grammar is rebuilt from the schema on every call
unless the caller constructs and reuses a `LlamaGrammar` object itself. For
this repo, the tool set is small and fixed (8 tools,
[tools/registry.py:44-58](../../../src/backend/modules/agent/tools/registry.py#L44-L58)) —
compiling one grammar per `InputModel.model_json_schema()` once at process
start (or lazily, memoized) and reusing it across every planning turn avoids
paying GBNF-compile cost on every step of every run.

**Schema vs. chat-template disagreement.** This is the load-bearing finding.
`llama-server` "fails open" on a grammar-parse failure: it logs
`llama_grammar_init_impl: failed to parse grammar` and then **generates
unconstrained text with no error surfaced to the caller**
([ggml-org/llama.cpp#19051](https://github.com/ggml-org/llama.cpp/issues/19051)).
There is also a documented case of the OpenAI-compatible endpoint rejecting
requests that pass both `json_schema` and `grammar`
([ggml-org/llama.cpp#11847](https://github.com/ggml-org/llama.cpp/issues/11847)),
and a "falling back to default grammar" path when a function-body schema
fails to parse (search-verified, not independently fetched — treat as
directional). None of this is unique to llama.cpp; it is the generic risk of
trusting the constraint mechanism instead of the output.

### Recommendation

Primary approach: **`response_format={"type": "json_object", "schema":
ToolInput.model_json_schema()}`** on `LlamaCppProvider.generate()`'s
`create_chat_completion` call
([llama_cpp_provider.py:237](../../../src/backend/core/llm/llama_cpp_provider.py#L237)),
one grammar per registered tool pre-compiled at process start from
`tools/registry.py`'s existing `InputModel`s. Extend `OllamaProvider` the
same way via its native `format` field (Ollama wraps the same underlying
grammar mechanism, so behavior won't drift between providers — this is
"add inside `core/llm/`," not a new layer, per CLAUDE.md rule 2). Pin
`llama-cpp-python` to a specific tested version rather than the current
unbounded `>=0.2.0` floor in `requirements.txt`.

**On constraint violation, never raise — fall back.** Wrap the constrained
call, then attempt `PlanDecision.model_validate_json(result.text)`
(mirroring `tools/registry.py`'s existing `validate_args()` pattern). Any
failure — grammar-compile error, well-formed-but-invalid JSON, timeout (the
provider already has a canonical timeout-fallback shape at
[llama_cpp_provider.py:282-295](../../../src/backend/core/llm/llama_cpp_provider.py#L282-L295)) —
routes to the existing deterministic `_default_planner`
([plan.py:188](../../../src/backend/modules/agent/nodes/plan.py#L188)) as the
fallback, exactly as `TIER_MODEL_CONFIG`'s tier-unavailable fallback chain
already works
([model_selector.py:403-417](../../../src/backend/modules/model_selector.py#L403-L417)).
This makes an LLM planner strictly additive — it can only match or exceed
the deterministic planner's coverage, never regress below it — and keeps
`plan()`'s contract exception-free.

---

## 2. KV cache and prompt reuse

### Verified repo state

`Llama(...)` is constructed with `model_path`, `n_ctx`, `n_threads`,
`n_gpu_layers`, `verbose`, `chat_format="auto"` only
([llama_cpp_provider.py:131-141](../../../src/backend/core/llm/llama_cpp_provider.py#L131-L141)) —
no `n_batch`, no `cache_prompt`, no state save/load. `core.llm.factory.get_provider()`
caches the provider **module-level, process-wide**
([factory.py:22,37-38](../../../src/backend/core/llm/factory.py#L22-L38)):
one `LlamaCppProvider`/`Llama` instance serves every request in the process,
regardless of profile. `modules/rag.py.compose_prompt()`
([rag.py:616-689](../../../src/backend/modules/rag.py#L616-L689)) puts
retrieved chunks (re-sorted by similarity every call) and session history
*before* the question — an order that changes call to call, which is
exactly the layout that defeats prefix reuse.

### The landscape

**llama.cpp/llama-server prompt caching.** `llama-server`'s slot mechanism
auto-matches a new request's prompt against cached per-slot KV state; default
similarity threshold 50% (`-sps 0.5`), transparent to the client
(`"cache_prompt": true` is the default)
([discussion #13606](https://github.com/ggml-org/llama.cpp/discussions/13606)).
`--cache-reuse`, `--cache-ram` + `--cache-idle-slots`, and `--slot-save-path`
+ the `/slots` save/restore API extend this to cross-session persistence
(search-verified). **None of this applies here**: this is a `llama-server`
(standalone HTTP daemon) feature, and this repo embeds `llama_cpp.Llama`
directly in-process — adopting it would mean spawning and managing a second
local process, a real architecture change for a desktop app that normally
serves one user with one generation in flight at a time (no concurrency
problem to solve).

**llama-cpp-python state save/load.** `Llama.save_state()`/`load_state()`
serialize the full native KV-cache blob into a `LlamaState`
([DeepWiki: State Management and Caching](https://deepwiki.com/abetlen/llama-cpp-python/4.6-state-management-and-caching) — not independently fetchable this session, corroborated by
[llama-cpp-python PR #1296](https://github.com/abetlen/llama-cpp-python/pull/1296)).
The library ships two built-in caches in `llama_cache.py`: `LlamaRAMCache`
(in-memory `OrderedDict`, LRU-evicted) and **`LlamaDiskCache`, which persists
`LlamaState` objects to disk via the `diskcache` library at a default path of
`.cache/llama_cache`, with no encryption** (confirmed by reading
[`llama_cache.py`](https://github.com/abetlen/llama-cpp-python/blob/main/llama_cpp/llama_cache.py)
directly this session).

**PRIVACY — this is the hard constraint, not a footnote.** A KV cache is a
deterministic function of the prompt tokens that produced it. For this app,
the prompt is routinely PHI: `modules/rag.py`'s `SYSTEM_PROMPT` template
embeds `[YOUR_RESULTS:N]`-labeled patient lab values directly
([rag.py:133](../../../src/backend/modules/rag.py#L133)), and any future
LLM-backed agent node would embed retrieved chunks and observation rows the
same way. `LlamaDiskCache` writing that state to an unencrypted file at
`.cache/llama_cache` is functionally equivalent to writing PHI to disk
outside the SQLCipher vault — a direct violation of "per-profile data
isolation... via `ProfileDbSession`" (CLAUDE.md hard invariant) even though
it is not literally a database row. **`LlamaDiskCache` must never be used in
this repo.** If cross-call reuse beyond the same in-process `Llama` object's
own native prefix diffing is ever wanted, it must be in-RAM only, keyed with
`profile_id` explicitly (the process-wide singleton in `factory.py` means a
naive prefix-hash cache with no profile scoping could theoretically let one
profile's cached state be reused for another's request), and wiped on
profile lock / process exit — the same posture `modules/agent/cache.py`
already documents for its own in-process answer cache ("no cross-process/
cross-restart persistence... no PHI on disk",
[cache.py:14-17](../../../src/backend/modules/agent/cache.py#L14-L17)).

**vLLM automatic prefix caching / SGLang RadixAttention.** Both share KV
blocks across requests with common prefixes, resident in **GPU VRAM**, evicted
via LRU or a radix tree — same underlying idea, but GPU-memory-resident by
design and only reachable at all if vLLM/SGLang are shippable in this product
(they are not — see §3). Useful as technique reference only: RadixAttention
adds no measurable overhead even on a cache miss, so if this app ever grows
a GPU-serving tier the *pattern* (stable-prefix-first prompt construction)
is the transferable idea, not the library
([SGLang RadixAttention](https://www.lmsys.org/blog/2024-01-17-sglang/);
[vLLM APC docs](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/)).

**Cache-aware prompt ordering.** This is the one lever this repo can pull
today with a small, surgical change and zero new dependencies. llama.cpp's
own in-process prefix reuse (the `Llama` object diffing the new prompt's
tokens against the last call's, independent of any explicit cache API) only
helps when the new prompt is byte-identical up to some prefix point and the
*new* content is appended at the end. `rag.py.compose_prompt()` currently
does the opposite — chunks and history are interleaved before the question
and reordered by similarity every call. A future agent node's prompt builder
should instead fix the order: system prompt + tool schemas + any
per-run-constant instructions **first** (byte-identical across every step of
one run), then the accumulating, append-only `RunLog` delta, with the
question or newest tool result **last**.

### Quantify the realistic win

`MAX_STEPS = 5`
([state.py:19](../../../src/backend/modules/agent/state.py#L19)): an
LLM-driven loop could call the model up to 5× for `plan`, 5× for `reflect`,
plus `draft` — each resending a stable system prompt + tool-schema block if
one is not reused. Small CPU-only models prefill much faster than they
generate (order of several hundred tok/s prefill vs. tens of tok/s decode is
typical for sub-1B–4B GGUF models on CPU), so a ~1-2K-token stable prefix
costs low single-digit seconds per re-encode on the `low`/`gemma4-e2b` tier's
target hardware. Skipping that re-encode on 4 of 5 `plan` steps (once the
prefix is genuinely stable and reused via ordering, not an explicit cache)
is a real, low-cost win — but it requires the prompt-ordering discipline
above; it is not automatic just from using the same model object.

### Memory cost on an 8-16GB laptop

KV cache size: `bytes = 2 × n_layers × n_kv_heads × head_dim × seq_len ×
bytes_per_element`
([KV cache memory calculator](https://dev.to/jagmarques/kv-cache-memory-calculator-how-much-does-your-llm-actually-use-85n)).
Exact Gemma-4 layer/head-dim figures were not independently confirmed this
session (source pages blocked by the egress proxy) — **[UNVERIFIED]**
precise numbers — but for small edge-class GQA models the order of magnitude
is roughly 0.1-0.3 MB/token in fp16; at the `gemma4-e4b` tier's configured
`context_size: 16384`
([model_selector.py:78](../../../src/backend/modules/model_selector.py#L78)),
a *fully retained* context-window's worth of KV state could run into the
low single-digit GB — a meaningful bite out of an 8-16GB budget that already
has to cover model weights (E2B ~1.5GB, E4B ~2.8GB per
`docs/model_tiers/README.md`), OS, and the Electron/browser shell. Practical
guidance: never retain/reuse the full context window's KV state — only the
short, genuinely-stable prefix (system prompt + tool schemas, likely under
2K tokens, tens of MB), which is what stable-prefix-first ordering combined
with the *existing* singleton's native diffing already gives for free.

### Recommendation

Do not adopt llama-server's slot/prompt-cache machinery or vLLM/SGLang (wrong
architecture / platform-blocked, see §3). Do: (a) verify and preserve the
existing process-singleton provider behavior
([factory.py:37-38](../../../src/backend/core/llm/factory.py#L37-L38)) so
sequential same-prefix calls keep getting llama.cpp's native reuse for free;
(b) restructure any future LLM-backed node's prompt-building function to
stable-prefix-first / volatile-suffix-last ordering; (c) explicitly forbid
`LlamaDiskCache`/any on-disk KV persistence in `LlamaCppProvider`; (d) if
cross-turn reuse beyond one process lifetime is wanted later, implement a
small in-RAM, profile-scoped `LlamaState` cache (same shape as
`modules/agent/cache.py`'s existing in-process dict), wiped on profile lock,
never written to `.cache/` or any plaintext path.

---

## 3. Task-aware model routing

### Verified repo state

Routing today is purely per-machine, at settings-load time:
`ModelSelector.get_active_tier()`
([model_selector.py:321-357](../../../src/backend/modules/model_selector.py#L321-L357))
picks one tier for the whole profile (user preference, else hardware
recommendation), and `core.llm.factory.get_provider()` instantiates exactly
one provider for the whole process
([factory.py:25-75](../../../src/backend/core/llm/factory.py#L25-L75)). There
is no per-node or per-request model selection anywhere in `modules/agent/`.
Every `TIER_MODEL_CONFIG` entry hardcodes `n_gpu_layers: 0`
([model_selector.py:56,66,79,91,101,113](../../../src/backend/modules/model_selector.py)) —
CPU-only is the default posture for every tier, not just `low`.

### The landscape

**RouteLLM / semantic routers.** RouteLLM (UC Berkeley, ICLR 2025) learns a
routing policy from preference data (matrix factorization or a causal-LM
classifier), reporting >85% cost reduction on MT-Bench while retaining ~95%
of a strong model's quality by sending only ~14% of queries to it
([digitalapplied.com summary](https://www.digitalapplied.com/blog/llm-model-routing-2026-cost-quality-optimization-engineering-guide)).
Semantic routers instead embed the query and match to a topic cluster.
Both assume a pool of *distinct-capability* models to route between — this
repo's tiers are distinct-capability by RAM class, not by task, so the
transferable idea is the *cascade* pattern below, not RouteLLM's learned
policy itself (training a router is its own project, disproportionate to
this repo's node count).

**Cascade / verification (small-first, escalate on low confidence).**
"Cascade routing sends the query to the cheap model first and only escalates
if the response does not meet a confidence threshold"
([Cluster, Route, Escalate](https://arxiv.org/pdf/2606.27457);
[Is Escalation Worth It?](https://arxiv.org/pdf/2605.06350)). This repo
already has this shape organically and doesn't need a new escalation tier
for planning specifically: the *existing* deterministic `_default_planner`
already is the safe fallback when an LLM planner's output fails validation
(§1) — a bigger model doesn't reduce format-validity risk, only constrained
decoding does.

**Speculative decoding.** `llama-server -m target.gguf -md draft.gguf
--spec-type draft-simple`, with `--spec-draft-ngl`/`--spec-draft-device`
controlling the draft model's placement
([llama.cpp docs/speculative.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md)).
Traditional speculative decoding requires the draft and target to share a
tokenizer/vocabulary; newer cross-vocabulary methods (HF's Universal
Assisted Generation, OmniDraft) relax this but add re-encoding overhead and
aren't llama.cpp features (transformers-side only)
([OmniDraft](https://arxiv.org/pdf/2507.02659)). EAGLE-3 (0.80-0.88 draft
acceptance, 3-4x throughput on H100/H200) is **not yet supported in
llama.cpp** as of these searches, only in TRT-LLM/vLLM/SGLang
([ggml-org/llama.cpp discussion #15902](https://github.com/ggml-org/llama.cpp/discussions/15902)).
For this repo's actual tiers (0.5B-12B, CPU-only by default), speculative
decoding's case is weak: it shines accelerating a genuinely large target
(30B-70B+) with a much smaller same-family draft on GPU; on CPU, drafting
consumes cycles that could go straight to the target, and running a second
resident model (however small) adds RAM on hardware that's already at its
tier floor. **Skip for now** — revisit only if a GPU-accelerated tier
becomes the common case (today it's the exception, not the default).

**Multi-model serving on one machine.** Model weights dominate RAM; "for
fewer than 15-20 concurrent users, a single well-configured `llama-server`
instance... is cheaper and simpler than a full vLLM stack," and forcing
concurrent loads on constrained VRAM causes OOM where swap-based execution
works reliably
(search-verified, multiple sources incl.
[llama-swap model management notes](https://notes.itsvasugrover.com/kb/ai/llama-swap/model-management/)).
For a single-user desktop app, this favors **at most two resident models**
(a small "fast" one plus the user's selected "quality" tier), never a larger
pool, and only on tiers with RAM headroom (see below).

### Routing table

| Node | Shape | Today | Proposed routing | RAM cost |
|---|---|---|---|---|
| `plan` | structured, short (~20-80 tok output: tool name + typed args) | Deterministic keyword match, 0 LLM calls ([plan.py:188](../../../src/backend/modules/agent/nodes/plan.py#L188)) | Smallest available tier (Qwen2.5-0.5B / gemma4-e2b) + constrained decoding (§1); malformed output falls back to the existing deterministic planner | Shared with `reflect`/`guard` if same small model kept resident: ~350MB-1GB extra *only* on tiers ≥16GB (see below) |
| `act` | tool execution, no generation | Deterministic Python, 0 LLM calls | N/A — never route an LLM here; tools are typed, read-only, and already validated ([tools/registry.py:31-37](../../../src/backend/modules/agent/tools/registry.py#L31-L37)) | none |
| `reflect` | binary-ish ("do I have grounding yet?") | Deterministic dict-key check ([reflect.py:24-43](../../../src/backend/modules/agent/nodes/reflect.py#L24-L43)) | **Keep deterministic.** A solved problem with a cheap, auditable check; an LLM here adds latency/risk with no clear quality upside | none |
| `draft` | long, grounded, quality-critical prose | Deterministic sentence templating ([draft.py:262-321](../../../src/backend/modules/agent/nodes/draft.py#L262-L321)) | The user's selected/hardware-recommended tier (existing `TIER_MODEL_CONFIG` selection) — the *only* node type that should pay that model's full per-token cost | already budgeted (existing tier RAM) |
| `guard` | classification (advice / groundedness) | Deterministic regex + citation-index arithmetic ([classifier.py](../../../src/backend/modules/agent/guardrails/classifier.py), [groundedness.py](../../../src/backend/modules/agent/guardrails/groundedness.py)) | **Keep non-LLM.** Already passes the `injection_resistance`/`phi_leakage` eval axes (per brief) with zero model-drift risk; if an LLM signal is ever added, it must be additive-only (can escalate to abstain, never loosen the existing gate) and use the small "fast" tier, never `draft`'s | none if kept as-is |

**Gating the two-model idea by tier.** On `low`/`gemma4-e2b` (8GB floor),
keep single-model routing — everything, including a future LLM planner,
shares the one small model already resident (that model *is* the "fast"
model). Only on `mid`/`gemma4-e4b`/`high`/`gemma4-12b` (16GB+) does adding a
second, small, always-resident "fast" model for `plan`/`reflect` alongside
the larger `draft`-tier model become affordable — the RAM delta is roughly
the small model's own footprint (~350MB for Qwen2.5-0.5B, ~1.5GB for
gemma4-e2b) layered on top of the existing tier, which needs to be an
explicit, tier-gated decision in `factory.py`/`ModelSelector`, not a blanket
default.

---

## 4. Mixture of Experts locally

### Correcting the premise

The brief states `TIER_MODEL_CONFIG` "lists Gemma-4-26B-MoE." On direct
inspection of the full dict
([model_selector.py:50-116](../../../src/backend/modules/model_selector.py#L50-L116)),
that is not accurate: the six actual entries are `low`, `gemma4-e2b`,
`gemma4-e4b`, `mid`, `gemma4-12b`, `high` — no `gemma4-26b`/MoE key exists.
The 26B-A4B model is named only in comments
([model_selector.py:39,42](../../../src/backend/modules/model_selector.py#L39-L42)
and [core/config.py:106](../../../src/backend/core/config.py#L106)), and
`docs/model_tiers/README.md`'s tier table
(`low | gemma4-e2b | mid | gemma4-e4b | high | gemma4-12b | template`) omits
it too. Per CLAUDE.md's own recurring-failure entry on "figures asserted
instead of measured," this is worth stating precisely: the MoE model isn't
an under-exploited feature of the code, it's **not present as a downloadable
or selectable option at all today.** That said, the substance of the brief's
question stands and is worth answering honestly: should it become one?

### What MoE actually buys

Gemma-4-26B-A4B: 26.0B total parameters, 3.8B active per token, 128 experts
([DEV.to breakdown](https://dev.to/pulkitgovrani/gemma-4-26b-a4b-what-mixture-of-experts-actually-means-for-your-inference-budget-13hj) —
fetch blocked this session, corroborated by
[Jetson AI Lab model page](https://www.jetson-ai-lab.com/models/gemma4-26b-a4b/)
and [unsloth/gemma-4-26B-A4B-it-GGUF](https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF)).
Activating ~14.6% of total params per token means the *compute* per
generated token approximates a ~4B dense model — that's the entire value
proposition, and it's real, on hardware where compute (not memory bandwidth
or capacity) is the bottleneck.

**But total params, not active params, govern RAM/disk**, because routing is
dynamic per-token and per-layer: a different subset of the 128 experts can
fire for every token, so there's no way to know in advance which experts to
leave unloaded. Q4_K_M quantization of the full 26B model runs ~16GB
(source above). That alone exceeds this repo's `high` tier's documented
32GB *minimum*... no — it's roughly half the `high` tier's 32GB floor in
weights alone, before KV cache, OS, and app overhead, which pushes the
realistic minimum toward that same 32GB floor `high` (BioMistral-7B, ~4GB
weights) already uses, for a **worse** CPU-inference bandwidth story than a
same-size dense model: a dense 4B model's weights are the *same* 4B every
token, so they stay resident in cache across the whole generation; a 26B MoE
touches a different ~4B *slice* of a much larger file each token, with much
worse locality, and CPU inference is memory-bandwidth-bound, not
compute-bound, at these sizes.

**`--n-cpu-moe` / expert CPU-offload.** This flag moves routed-expert
feed-forward tensors to CPU RAM while attention, KV cache, the router, and
shared experts stay on GPU
([Doctor-Shotgun's MoE offload guide](https://huggingface.co/blog/Doctor-Shotgun/llamacpp-moe-offload-guide);
[aliteq.com explainer](https://aliteq.com/n-cpu-moe-llama-cpp-what-it-actually-does)).
It solves the *opposite* hardware profile from this app's default: a machine
with a small-to-mid GPU (12-24GB VRAM) that can't fit the whole MoE model in
VRAM. With `n_gpu_layers: 0` as this repo's default everywhere, there is no
VRAM to offload *from* — every expert is already "on CPU." The flag's own
documentation is explicit that CPU-offload usually makes an MoE model
*slower*, not faster; the win "only happens when the model didn't fit in
VRAM in the first place." It would only matter for the narrow slice of
patient laptops with an 8-16GB discrete GPU willing to load a 26B model, and
even then it makes the model *possible*, not fast.

### Verdict

**MoE is not the win here — an honest finding, as requested.** For 8/16/32GB
target tiers, a dense model with active-size ≈ the MoE's active param count
(gemma4-e4b at ~2.8GB, or the existing `gemma4-12b`/Phi-3-mini entries)
delivers comparable-or-better quality per generated token at a fraction of
the disk/RAM footprint, with full weight-cache locality and no routing
overhead. Recommend: leave the 26B MoE **out** of `TIER_MODEL_CONFIG`
entirely — this matches current reality, not a regression — and if a
materially higher-quality option is wanted at the 32GB tier, prefer a
well-quantized dense 12B-14B model (`gemma4-12b` is already configured) over
adding the 26B MoE as a new "high+" bucket.

---

## 5. Quantization and footprint

### Verified repo state

Every tier in `TIER_MODEL_CONFIG` targets `q4_k_m` (`filename_pattern:
"q4_k_m"` or an explicit `q4_k_m` filename)
([model_selector.py:53-115](../../../src/backend/modules/model_selector.py#L53-L115)).
`docs/model_tiers/*.md` documents the same choice consistently across all
three shipped tiers.

### The landscape

**Q4_K_M remains the right default as of late 2026.** Multiple 2026 sources
converge: "Q4_K_M is the universal default, saving 72% VRAM while retaining
92-95% of quality"
([RunLocalModel quantization guide](https://runlocalmodel.com/choosing-quantization-2026.html)),
with one benchmark citing 92% perplexity retention (1.6% drop from FP16) at
100 tok/s
([DevShelfHub](https://www.devshelfhub.com/tutorials/run-llms-locally/quantization-performance/)).
Quality degrades unevenly under quantization: "logical reasoning is very
resistant to quantization, while arithmetic starts to degrade below Q4" —
relevant since this app's job is explaining lab *values* (numeric), which
argues against going below Q4 for any tier.

**IQ4_XS and importance-matrix quants.** ~95% perplexity retention (better
than Q4_K_M) but slower CPU decode in the same benchmark (80 vs 100 tok/s) —
a worse fit for this app's CPU-first, latency-sensitive low tiers *except*
where the 3-4GB size saving is what makes a higher-capability model fit an
existing tier's RAM/disk floor at all (e.g., squeezing `gemma4-12b` or
`high`/BioMistral-7B comfortably into `mid`'s 16GB floor).
([Unified evaluation of llama.cpp quantization on Llama-3.1-8B](https://arxiv.org/html/2601.14277v1)
corroborates IQ-quants as importance-matrix-calibrated, generally
higher-quality-per-bit than uniform K-quants but with CPU throughput
penalties.)

**Newer 2026 formats: MXFP4, TQ1_0/TQ2_0.** Both are now in llama.cpp's
`llama-quantize` tool
([discussion #23853, advanced GGUF quantizer](https://github.com/ggml-org/llama.cpp/discussions/23853);
[tools/quantize/README.md](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md)).
MXFP4 is native to OpenAI's gpt-oss models; TQ1_0/TQ2_0 are ~1.6-2 bits/weight
ternary formats, BitNet-lineage. Neither applies to this repo's target
models: MXFP4 needs a source model trained/released in that format (none of
Qwen2.5, Phi-3, BioMistral, or Gemma-4 are), and ternary quantization
generically needs quantization-*aware* training to hold quality — retrofitting
it post-hoc onto an ordinary dense transformer (as opposed to a
purpose-built ternary/BitNet model) is expected to degrade badly.
**[UNVERIFIED numeric]**, directional based on how ternary quantization is
documented elsewhere to require QAT rather than post-training quantization —
flagged as not applicable to this repo's model choices, not recommended.

**Unsloth Dynamic 2.0/3.0 GGUFs — the one free upgrade.** Per-layer,
architecture-tuned mixed-bit quantization rather than one uniform format
across every layer; published to beat uniform quants on MMLU/KL-divergence
retention at the *same file size*, because more bits go to layers measured
to be more sensitive (search-verified this session; primary blog fetch was
blocked by the egress proxy — treat specific numeric claims as
**[UNVERIFIED]**, the mechanism and general claim are corroborated across
multiple independent 2026 sources). Loads as an ordinary GGUF — zero runtime
code change, zero new dependency. Coverage for the specific model+size this
repo targets (Qwen2.5-0.5B, Phi-3-mini, BioMistral-7B) is **[UNVERIFIED]** —
Unsloth publishes primarily for high-traffic families (Gemma, Llama,
DeepSeek, Qwen); would need a Hugging Face check at ship time for each
tier's specific repo.

### Per-tier recommendation

| Tier | Current | Recommendation | Rationale |
|---|---|---|---|
| `low` (Qwen2.5-0.5B) | Q4_K_M, ~350MB | Keep Q4_K_M; check for an Unsloth Dynamic build as a same-size drop-in swap | Smallest model, least quantization headroom to spend on IQ-quant CPU penalty |
| `gemma4-e2b`/`gemma4-e4b` | Q4_K_M (pattern) | Keep Q4_K_M | Edge-tuned models, CPU-only target hardware; speed matters more than the last perplexity point |
| `mid` (Phi-3-mini) | Q4_K_M | Keep Q4_K_M; consider IQ4_XS only if disk-constrained | 16GB floor has headroom; IQ4_XS's CPU slowdown is a real cost, not free |
| `gemma4-12b`/`high` (BioMistral-7B) | Q4_K_M | Keep Q4_K_M as default; IQ4_XS is a reasonable opt-in for disk-constrained installs at this size | Bigger files benefit most from IQ's 3-4GB savings; 32GB tier has RAM slack to absorb the CPU penalty |
| Any tier | — | Do not adopt MXFP4 or TQ1_0/TQ2_0 | Not native to any target model; post-hoc retrofit expected to degrade quality without QAT |

---

## Recommendations

| Change | Repo integration point (file:line) | Impact | Effort | Risk | Blocked by |
|---|---|---|---|---|---|
| Native JSON-schema constrained decoding for a future LLM planner, one grammar per tool precompiled at startup | `core/llm/llama_cpp_provider.py:237` (`create_chat_completion` call); schemas sourced from `modules/agent/tools/registry.py`'s existing `InputModel`s | Makes an LLM planner emit machine-parseable tool calls instead of free text; the actual "fragile execution under load" fix the brief names | M | Grammar-parse failures "fail open" (unconstrained text) upstream in llama.cpp — must be caught by post-hoc `PlanDecision.model_validate_json()`, not trusted | An actual LLM-backed planner existing to constrain (currently `plan()` has none — this is prep work for that future story) |
| Deterministic fallback on any constraint/validation failure | `modules/agent/nodes/plan.py:311-320` (`Planner` seam, `planner: Planner = _default_planner`) | Guarantees an LLM planner can only add coverage, never regress below today's keyword planner | S | Low — mirrors the existing `TIER_FALLBACK_ORDER` pattern | Same as above |
| Pin `llama-cpp-python` to a specific tested version (currently unbounded `>=0.2.0`) | `src/backend/requirements.txt:52` | Removes ambiguity about whether `response_format`/JSON-schema mode is actually available in the installed wheel | S | None | — |
| Extend `OllamaProvider` request body with the native `format` field for schema-constrained output | `core/llm/ollama_provider.py:130-142` | Keeps the two providers' structured-output behavior from drifting apart | S | Low | Same tool-schema plumbing as the llama_cpp change |
| Stable-prefix-first prompt construction for any future LLM-backed node | New prompt-builder function alongside `modules/rag.py:616` (`compose_prompt`) as a model, applied to the future agent draft/plan prompt path | Lets llama.cpp's existing in-process prefix reuse actually fire across the up-to-5-step `MAX_STEPS` loop | M | Low — pure reordering, no new dependency; must not silently change citation/grounding behavior | An LLM-backed node whose prompt this applies to |
| Explicit prohibition of `LlamaDiskCache`/on-disk KV persistence | `core/llm/llama_cpp_provider.py` (constructor — never instantiate `llama_cpp.LlamaDiskCache`) | Prevents PHI-derived state from landing outside the SQLCipher vault, unencrypted, at `.cache/llama_cache` | S (as a "never do this" guard/comment + code review rule) | High if violated — direct PHI-at-rest exposure | — |
| Bounded, profile-scoped, in-RAM `LlamaState` cache (only if cross-turn reuse is wanted beyond one process lifetime) | New module alongside `modules/agent/cache.py` (same in-process-dict, no-disk pattern) | Cross-turn KV reuse without the disk-cache privacy risk | M | Must key on `profile_id` explicitly — the process-wide provider singleton (`core/llm/factory.py:22`) means an unscoped cache could theoretically mix profiles | Confirm real-world win justifies the added code (§2's "quantify the realistic win" is modest at MAX_STEPS=5) |
| Two-model routing: small "fast" model resident for `plan`/`reflect`, larger tier reserved for `draft`, gated to `mid`+ tiers only | `core/llm/factory.py:25-75` (`get_provider` — needs a second named provider slot); `modules/model_selector.py:321-357` (`get_active_tier`) | Cheaper/faster `plan` turns without paying `draft`-tier latency on every step | M | RAM regression on `low`/`gemma4-e2b` tier if not gated correctly | An LLM-backed `plan`/`reflect` to route in the first place |
| Keep `guard` and `reflect` non-LLM | `modules/agent/guardrails/guard.py`, `modules/agent/nodes/reflect.py` | Preserves the deterministic, audited, injection-resistant behavior already passing eval gates | None (no change) | Regression risk if someone *does* add an LLM here without this being additive-only | — |
| Do not add speculative decoding | N/A | Avoids RAM/complexity cost with a weak payoff at this repo's CPU-only, 0.5B-12B tier range | — | — | Would need a GPU-accelerated tier to become the common case first |
| Do not add `--n-cpu-moe` / expert offload tooling | N/A | This repo's `n_gpu_layers: 0` default everywhere means there's no VRAM to offload from — the flag's entire value proposition doesn't apply | — | — | A GPU tier with 8-16GB VRAM becoming common among target users |
| Do not add Gemma-4-26B-MoE as a `TIER_MODEL_CONFIG` entry | `modules/model_selector.py:50-116` | Avoids a 32GB-floor tier that delivers worse CPU-inference locality than an equal-active-size dense model already in the config (`gemma4-12b`) | — | — | — |
| Check Unsloth Dynamic 2.0/3.0 builds for each tier's specific model before next model refresh | `modules/model_selector.py`'s `repo`/`filename`/`filename_pattern` fields per tier | Same-size, better-quality quant swap for architectures Unsloth covers | S (config/data change only, if a build exists) | Coverage for Qwen2.5-0.5B/Phi-3-mini/BioMistral-7B specifically is unverified — needs a Hugging Face check | Availability of a matching published build |

---

## Sources

- [ggml-org/llama.cpp issue #19051 — llama-server fails open on JSON schema grammar parsing failure](https://github.com/ggml-org/llama.cpp/issues/19051)
- [ggml-org/llama.cpp issue #11847 — response_format json_schema/grammar conflict](https://github.com/ggml-org/llama.cpp/issues/11847)
- [ggml-org/llama.cpp issue #11988 — json_schema under response_format not working](https://github.com/ggml-org/llama.cpp/issues/11988)
- [ggml-org/llama.cpp discussion #20459 — Structured Output problem](https://github.com/ggml-org/llama.cpp/discussions/20459)
- [ggml-org/llama.cpp docs/llguidance.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/llguidance.md)
- [guidance-ai/llguidance](https://github.com/guidance-ai/llguidance)
- [XGrammar-2: Efficient Dynamic Structured Generation Engine for Agentic LLMs](https://arxiv.org/pdf/2601.04426)
- [Generating Structured Outputs from Language Models: Benchmark and Studies (JSONSchemaBench)](https://arxiv.org/html/2501.10868v1)
- [abetlen/llama-cpp-python discussion #1173 — response_format mechanism](https://github.com/abetlen/llama-cpp-python/discussions/1173)
- [abetlen/llama-cpp-python discussion #1376 — grammar throughput impact](https://github.com/abetlen/llama-cpp-python/discussions/1376)
- [Instructor: structured outputs with llama-cpp-python](https://python.useinstructor.com/integrations/llama-cpp-python/)
- [Ekansh Jain — Squeezing Every Drop of Performance out of llama.cpp](https://medium.com/@ekansh.jain2011/squeezing-every-drop-of-performance-out-of-llama-cpp-the-practitioners-guide-to-local-ai-2bcc3663f06f)
- [llama.cpp grammars/README.md](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)
- [Lost in Space: Optimizing Tokens for Grammar-Constrained Decoding](https://arxiv.org/html/2502.14969v1)
- [Simon Willison — Using llama-cpp-python grammars to generate JSON](https://til.simonwillison.net/llms/llama-cpp-python-grammars)
- [ggml-org/llama.cpp discussion #12110 — how to use lazy grammars](https://github.com/ggml-org/llama.cpp/discussions/12110)
- [ggml-org/llama.cpp discussion #3665 — custom sampler / logits processor](https://github.com/ggml-org/llama.cpp/discussions/3665)
- [abetlen/llama-cpp-python — llama_cache.py](https://github.com/abetlen/llama-cpp-python/blob/main/llama_cpp/llama_cache.py)
- [abetlen/llama-cpp-python PR #1296 — compact on-disk saved state](https://github.com/abetlen/llama-cpp-python/pull/1296)
- [ggml-org/llama.cpp issue #17107 — KV cache persistence on disk feature request](https://github.com/ggml-org/llama.cpp/issues/17107)
- [ai-muninn.com — llama.cpp KV cache disk restore proxy](https://ai-muninn.com/en/blog/kv-cache-disk-restore-7x)
- [ggml-org/llama.cpp discussion #13606 — KV cache reuse with llama-server tutorial](https://github.com/ggml-org/llama.cpp/discussions/13606)
- [vLLM — Automatic Prefix Caching docs](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/)
- [SqueezeBits — vLLM vs TensorRT-LLM: Automatic Prefix Caching](https://blog.squeezebits.com/vllm-vs-tensorrtllm-12-automatic-prefix-caching-38189)
- [LMSYS — Fast and Expressive LLM Inference with RadixAttention and SGLang](https://www.lmsys.org/blog/2024-01-17-sglang/)
- [SGLang HiCache design docs](https://docs.sglang.ai/advanced_features/hicache_design.html)
- [aivrar/vllm-windows-build — native Windows vLLM wheels](https://github.com/aivrar/vllm-windows-build)
- [fazm.ai — vLLM on Windows in 2026](https://fazm.ai/t/vllm-windows-support-2026)
- [DEV.to — KV cache memory calculator](https://dev.to/jagmarques/kv-cache-memory-calculator-how-much-does-your-llm-actually-use-85n)
- [Spheron — KV Cache Optimization Guide 2026](https://www.spheron.network/blog/kv-cache-optimization-guide/)
- [Cluster, Route, Escalate: Cascaded Framework for Cost-Aware LLM Serving](https://arxiv.org/pdf/2606.27457)
- [Is Escalation Worth It? A Decision-Theoretic Characterization of LLM Cascades](https://arxiv.org/pdf/2605.06350)
- [NeuralTrust — LLM Model Routing](https://neuraltrust.ai/blog/llm-model-routing)
- [Digital Applied — LLM Model Routing in 2026: Cost-Quality Optimization](https://www.digitalapplied.com/blog/llm-model-routing-2026-cost-quality-optimization-engineering-guide)
- [ggml-org/llama.cpp docs/speculative.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md)
- [ggml-org/llama.cpp discussion #15902 — Eagle-3 speculative decoding support](https://github.com/ggml-org/llama.cpp/discussions/15902)
- [OmniDraft: Cross-vocabulary, Online Adaptive Drafter for On-device Speculative Decoding](https://arxiv.org/pdf/2507.02659)
- [Notes — llama-swap model management](https://notes.itsvasugrover.com/kb/ai/llama-swap/model-management/)
- [Doctor-Shotgun — Performant local MoE CPU inference with GPU acceleration in llama.cpp](https://huggingface.co/blog/Doctor-Shotgun/llamacpp-moe-offload-guide)
- [Aliteq — --n-cpu-moe (llama.cpp): the CPU-offload flag explained](https://aliteq.com/n-cpu-moe-llama-cpp-what-it-actually-does)
- [Aliteq — llama.cpp --n-cpu-moe: Run a Big MoE Model on a Small GPU](https://aliteq.com/run-big-moe-model-small-gpu-n-cpu-moe-guide)
- [unsloth/gemma-4-26B-A4B-it-GGUF (Hugging Face)](https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF)
- [Jetson AI Lab — Gemma 4 26B-A4B model page](https://www.jetson-ai-lab.com/models/gemma4-26b-a4b/)
- [DEV.to — Gemma 4 26B A4B: What MoE Actually Means for Your Inference Budget](https://dev.to/pulkitgovrani/gemma-4-26b-a4b-what-mixture-of-experts-actually-means-for-your-inference-budget-13hj)
- [Android Developers Blog — Announcing Gemma 4 in the AICore Developer Preview](https://android-developers.googleblog.com/2026/04/AI-Core-Developer-Preview.html)
- [Google Developers Blog — Gemma 4 12B: The Developer Guide](https://developers.googleblog.com/gemma-4-12b-the-developer-guide/)
- [Winbuzzer — Google Releases Smaller Gemma 4 QAT Models for Local AI](https://winbuzzer.com/2026/06/06/google-releases-smaller-gemma-4-models-for-local-ai-xcxwbn/)
- [Google AI for Developers — Gemma releases](https://ai.google.dev/gemma/docs/releases)
- [RunLocalModel — Choosing the Right Quantization for Local LLMs in 2026](https://runlocalmodel.com/choosing-quantization-2026.html)
- [DevShelfHub — LLM Quantization 2026: GGUF, Q4_K_M vs Q8, GPU Offload](https://www.devshelfhub.com/tutorials/run-llms-locally/quantization-performance/)
- [Which Quantization Should I Use? A Unified Evaluation of llama.cpp Quantization on Llama-3.1-8B-Instruct](https://arxiv.org/html/2601.14277v1)
- [ggml-org/llama.cpp discussion #23853 — advanced-gguf-quantizer for NVFP4/MXFP6](https://github.com/ggml-org/llama.cpp/discussions/23853)
- [ggml-org/llama.cpp tools/quantize/README.md](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md)
- [Unsloth Dynamic 2.0 GGUFs](https://unsloth.ai/blog/dynamic-v2)
- [Unsloth Dynamic 3.0 GGUFs docs](https://unsloth.ai/docs/basics/dynamic-3.0-ggufs)
- [llama-cpp-python changelog](https://llama-cpp-python.readthedocs.io/en/stable/changelog/)

### Repo files read this session

- `src/backend/core/llm/llama_cpp_provider.py`
- `src/backend/core/llm/provider.py`
- `src/backend/core/llm/ollama_provider.py`
- `src/backend/core/llm/factory.py`
- `src/backend/core/model_runner.py`
- `src/backend/core/external_runner.py` (partial)
- `src/backend/core/config.py` (partial, model/inference settings section)
- `src/backend/modules/model_selector.py`
- `src/backend/modules/hardware_detection.py`
- `src/backend/modules/rag.py` (partial: `SYSTEM_PROMPT`, `compose_prompt`, `generate_response`)
- `src/backend/modules/agent/graph.py`
- `src/backend/modules/agent/state.py` (partial: `MAX_STEPS`)
- `src/backend/modules/agent/settings.py`
- `src/backend/modules/agent/cache.py`
- `src/backend/modules/agent/nodes/plan.py`
- `src/backend/modules/agent/nodes/reflect.py`
- `src/backend/modules/agent/nodes/draft.py`
- `src/backend/modules/agent/guardrails/classifier.py`
- `src/backend/modules/agent/guardrails/groundedness.py`
- `src/backend/modules/agent/guardrails/guard.py`
- `src/backend/modules/agent/tools/base.py`
- `src/backend/modules/agent/tools/registry.py`
- `src/backend/modules/agent/tools/retrieve_chunks.py` (partial)
- `src/backend/requirements.txt` (grep)
- `docs/model_tiers/README.md`, `tier1_low.md`, `tier2_mid.md`, `tier3_high.md`
- `docs/research/2026-09-08/00-brief.md`
