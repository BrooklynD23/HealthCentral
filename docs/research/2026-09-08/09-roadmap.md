# Synthesis — sequenced roadmap

Merges the eight tracks into one dependency-ordered plan. Written after the
tracks returned, against [`00-brief.md`](00-brief.md) and the execution record
in [`PLAN.md`](PLAN.md) §9.

**This is a research synthesis, not an accepted backlog.** Nothing here is
verified by running it. Items are proposals with sourced reasoning; each still
needs a failing test before it becomes work.

---

## 1. What the eight tracks agree on

Cross-track agreement is the strongest signal this pass produced, because the
researchers worked in isolated contexts and could not coordinate.

**Three tracks independently reached the same conclusion about the planner
swap** — Track 2 (serving), Track 3 (loops), Track 5 (models). Stated as one
sentence they all support: *an LLM planner is viable, but only at mid/high
tier, only behind constrained decoding with post-hoc validation, and only with
the existing deterministic planner kept permanently as the fallback — not as a
stepping stone to be deleted.* Track 5 supplies the hard number that makes the
tier gate non-negotiable: Qwen3-0.6B-class models score **~1.4%** on
BFCL-style multi-turn tool-calling accuracy. The `low` tier can never plan.

**Two tracks independently found the same unreported bug.** Track 3 (from the
memory-as-agent-surface angle) and Track 7 (from the data-control angle) both
landed on `api/memory.py` writing `MemoryItem` rows through `ProfileDbSession`
with **zero audit logging and zero redaction on write**. Verified by the
orchestrator: 14 of the 15 other `api/` routers audit; memory is the sole
outlier, and `CLAUDE.md` requires auditing on every route touching profile
data. Two isolated agents converging on one finding from different directions
is the closest this method gets to proof.

**Two tracks agree the guard and reflect nodes should stay non-LLM.** Track 2
and Track 3 both recommend this as an explicit *non-change*. Track 3's reason
is the sharper one: `reflect.py:24-43`'s deterministic `_has_grounding` is
already the pattern the 2025-2026 literature converged on as the reliable
alternative to self-critique, just written in plain Python. Replacing it with
a model call would be a regression dressed as an upgrade.

**Three tracks agree the agent-trace UI is blocked on the backend.** Tracks 1,
3, and 8 all note that `POST /assistant/chat` (`api/assistant.py:657`) awaits
`run_agent()` and flattens the result: no `run_id`, no `terminal`, no
per-sentence citation mapping — all of which the agent **already computes**
(`nodes/draft.py:44-46` holds `sentences` parallel to `citations`;
`guard.py:173` joins them with `" ".join(...)`). This is the cheapest
high-value item in the entire research pass: stop discarding data that exists.

## 2. Where the tracks disagree

Two disagreements, both worth preserving rather than resolving by fiat.

**Constrained-decoding cost.** Track 2 measures GBNF at roughly 60-78% fewer
tokens/sec on CPU but argues the absolute cost is negligible because the
planner payload is 20-80 tokens. Track 3 cites a 3.6-8.2x slowdown and treats
it as a real budget item. Both are probably right about different things —
Track 2 is reasoning about a tiny constrained span, Track 3 about the
whole-generation multiplier. **Resolution: measure locally before committing.**
Neither figure was produced on this codebase, and §5 of `PLAN.md` already flags
that no benchmarks were run.

**MCP spec target.** Track 4 recommends targeting revision **2025-06-18**, not
the current 2026-07-28, on the grounds that the newest revision reached GA
seven weeks before the research and its SDK ecosystem is immature. This is a
conservative call that trades capability for stability. It is the right default
for a health app, and it should be revisited on a date, not on a feeling.

---

## 3. The sequence

Ordering is driven by one rule: **you cannot safely add a generative node to a
system that cannot see what its loop did.** Observability and evals come before
the model, not after it.

### Wave 0 — Verified defects (do these first; none depend on anything)

These are not roadmap items. They are things that are currently wrong.

| # | Item | Source | Why first |
|---|---|---|---|
| 0.1 | Audit logging on all five `api/memory.py` routes | T3, T7 | Verified hard-invariant violation |
| 0.2 | ~~Route memory `value` through `sanitize_untrusted_field` before persisting~~ | T3 | **REJECTED on implementation — see below** |
| 0.3 | Fix answer-cache staleness | T7 | Root cause was deeper than "bump on deletion" — see below |
| 0.4 | Pin `llama-cpp-python` (was unbounded `>=0.2.0`) | T2 | Pinned `==0.3.2` on the owner's answer — **and it surfaced a model/runtime contradiction, see below** |
| 0.5 | Delete the dead `default_embeddings_model = "bge-small-en-v1.5"` config | T5 | `core/config.py:89` is unused and misleading; `all-MiniLM-L6-v2` is what actually loads |

### What implementation changed (2026-09-08)

Wave 0 was implemented the same day it was written. Three of the five items
survived contact with the code unchanged; two did not.

**0.2 is rejected, not deferred.** Track 3 was right that memory items are
untrusted text that later enters prompts, and wrong about where to act on it.
Two findings, both verified before rejecting:

1. **The protection already exists, at the better layer.**
   `modules/rag.py::_retrieve_memory_context` already checks each item's
   combined `key`/`category`/`value` with `_contains_prompt_injection` and
   **skips the whole item** when it matches, logging "Filtered potentially
   unsafe memory item". Filtering at compose time is strictly safer than
   scrubbing at write time: it fails closed on the entire item rather than
   silently handing a partially-mangled string to the model.
2. **Applying it at write time would have destroyed user data.**
   `sanitize_untrusted_field` runs `RedactionEngine(policy_level="strict")`.
   Memory items are things a patient deliberately saved into their own
   encrypted vault — "my nephrologist is Dr. Chen", "metformin 500mg twice
   daily". Strict-redacting those on write corrupts them irreversibly, since
   the original is never stored. `CLAUDE.md`'s invariant is *redaction before
   anything **leaves***; a write into the per-profile SQLCipher vault is the
   PHI arriving at its designed home, not leaving it.

**0.3's root cause was deeper than the roadmap stated.** "Bump
`profile_version` on deletion" describes a symptom. `_profile_version` derived
the version from a **COUNT of verified observations**, and a count is not a
version — it decreases on delete, so deleting one verified observation and
verifying a different one returns the key to a value the cache has already
seen. Demonstrated by `HC-CACHE-VER-001`, which failed with *"both 2"*: a
cached answer about the deleted observation was still served. The fix
fingerprints both evidence sources the agent's tools actually read — verified
observations and verified documents (`retrieve_chunks` filters on
`Document.status == "verified"`) — each as a count paired with its latest
`verified_at`. Memory items are deliberately **excluded**: no agent tool reads
them, so they cannot change an agent answer; including them would be
speculative.

**0.4 is done, and it was worth more than a pin.** The owner supplied the
version actually in use: **0.3.2**, now pinned exactly. Two facts were verified
against the `v0.3.2` tag rather than assumed:

*Good news for Wave 2.* 0.3.2 already exposes the constrained-decoding hook the
LLM planner needs. `ChatCompletionRequestResponseFormat`
(`llama_cpp/llama_types.py:158-162`) declares
`type: Literal["text","json_object"]` **and** `schema: NotRequired[JsonType]`,
and `llama_cpp/llama_chat_format.py:586` routes it through
`_grammar_for_response_format` → `LlamaGrammar.from_json_schema`. So Wave 2's
step 2.3 is not blocked by the runtime — only by the work itself.

*Bad news for the model tiers.* **0.3.2 was released 2024-11-16**, so it vendors
a llama.cpp predating the **Gemma 4 architecture (released 2026-06-03)** by
roughly nineteen months. Three of the six `TIER_MODEL_CONFIG` entries named
Gemma 4 GGUFs and could not have loaded on it.

**The owner confirmed a Gemma 4 tier has never loaded**, which resolved the
question: the Gemma 4 entries were aspirational, exactly as the config's own
`# PLACEHOLDER URLs (verify before production)` comment hinted, and the mid and
high tiers had never run the models the docs claimed. That mattered because
Wave 2's tier gate — keeping the LLM planner off the 0.5B tier — assumes a
working mid tier exists.

### Resolution (2026-09-09): pin raised to 0.3.35, mid tier swapped

Both were done together because neither works alone.

**Pin `0.3.2` → `0.3.35`.** Verified against upstream, not assumed: 0.3.35
(2026-08-17) vendors `ggml-org/llama.cpp@4df29be4f`, whose `src/llama-arch.cpp`
declares `gemma4`, `gemma4-assistant`, `gemma3n`, `qwen3` and `phi3`. So Gemma 4
is real and *is* supported by a current runtime — the blocker was only ever the
22-month-old wheel. The constrained-decoding hook Wave 2 needs exists in both
versions, so raising the pin does not put it at risk.

**Mid tier `Phi-3-mini-4k` → `Phi-4-mini-instruct`** (Track 5's
recommendation). Same size class, same MIT license, and it escapes a 4K context
window too small to hold retrieved chunks, a tool menu and a question at once.
Phi-4-mini loads under llama.cpp's existing `phi3` architecture — there is no
separate `phi4` arch — but it postdates the 0.3.2 wheel, so it required the pin
raise. Context capped at 16K rather than the model's 128K: the KV cache for
128K is impractical on this tier's CPU-only path (`n_gpu_layers: 0`).

**Two things this did NOT resolve, both requiring a machine that can run the
wheel:**

1. **Nothing here was executed.** `llama-cpp-python` is a compiled package the
   sandbox cannot build, so neither the pin nor the model swap has been run.
   The first local run is the real test — load one model per configured tier.
2. **The Phi-4-mini repo path is unverified.** `huggingface.co` is unreachable
   from this environment, so `bartowski/microsoft_Phi-4-mini-instruct-GGUF`
   comes from search results, not a live check. Microsoft publishes no
   first-party Phi-4-*mini* GGUF (`microsoft/phi-4-gguf` is the 14B), so this is
   a community quantizer — a supply-chain choice as much as a quality one.
   Confirm with `huggingface_hub.list_repo_files()` and record a checksum in
   `modules/model_integrity.py` before first download.

**Still open:** the Gemma 4 repo paths remain `PLACEHOLDER` and unverified for
the same reason, and the `low` tier still pins `Qwen2.5-0.5B` while llama.cpp
now declares `qwen3`, `qwen35` and `qwen4exp` architectures — that tier is two
generations behind, though Track 5's finding that 0.5B-class models cannot plan
(~1.4% multi-turn tool-calling accuracy) applies regardless of generation.

### Wave 1 — See before you change (blocks Wave 2)

| # | Item | Source | Note |
|---|---|---|---|
| 1.1 | Add `expect.tool_sequence` to golden cases + a **tool-selection-accuracy** scorer axis | T3 | The 6 existing axes score only the final terminal. A planner swap changes *trajectory*, which nothing currently measures |
| 1.2 | Add step-count / unnecessary-step + per-node cost aggregation to the scorer | T3 | `metrics.py` already collects per-node timing (S5-3); this is aggregation, not new instrumentation |
| 1.3 | `GET /audit-log` — paginated, filterable, with a phrase-table translator | T7 | The schema is already correct and indexed (`models/audit.py:20-71`); exactly one route reads `AuditLog` today, and only to count rows before purging |
| 1.4 | Return `run_id`, `terminal`, and per-sentence `sentences`/`citations` on `ChatResponse` | T1, T3, T8 | Stop discarding computed data. Unblocks every Wave 3 UI item |
| 1.5 | Wire `get_correlation_id()` into the log formatter and `create_audit_log` | T7 | HC-M07 plumbing exists but is unused |

### Wave 2 — The generative seam (the actual thesis)

This is where the product stops being a template engine. Ordering inside the
wave is strict.

| # | Item | Source | Note |
|---|---|---|---|
| 2.1 | Widen the `Planner` type + `plan()`'s one `decision = planner(...)` line to admit an awaitable | T3 | `plan.py:311,322` — currently `Callable[[str, RunLog], PlanDecision]`, synchronous. One function body. Blocks everything after it |
| 2.2 | Compressed-signature tool menu built from `tools/registry.py` at import time | T3 | Never hand-duplicate the tool list; the registry is the source of truth |
| 2.3 | Native JSON-schema constrained decoding, one grammar precompiled per tool at startup | T2 | `llama_cpp_provider.py:237`. **llama.cpp fails open on grammar-parse failure** ([#19051](https://github.com/ggml-org/llama.cpp/issues/19051)) — so this alone is not a guarantee |
| 2.4 | Post-hoc `PlanDecision.model_validate_json()` check; **on any failure fall back to `_default_planner`, never raise** | T2, T3 | This, not the grammar, is what makes the swap safe. It guarantees an LLM planner can only add coverage, never regress below today's behavior |
| 2.5 | `_llm_planner`, gated to **mid/high tier only**, turn-1 only, catch-all questions only | T3, T5 | Never at `low` tier (§1). Narrow entry, widen only on eval evidence |
| 2.6 | Mirror the structured-output path in `OllamaProvider` (native `format` field) | T2 | Keeps the two providers from drifting |
| 2.7 | Stable-prefix-first prompt construction for any LLM-backed node | T2 | Cache-friendliness is a design property, not a later optimization |

**Explicitly not in Wave 2:** in-RAM `LlamaState` reuse (T2 — only if cross-turn
reuse is wanted, and never on disk), and two-model routing (T2 — real, but it
needs a second resident provider slot and is only defensible at mid+ tiers).

### Wave 3 — Make it legible (depends on 1.3, 1.4)

| # | Item | Source |
|---|---|---|
| 3.1 | Distinct abstain/escalate cards — render them as trustworthy outcomes, not failures | T8 |
| 3.2 | Wire the already-built, already-accessible `CitationTooltip` into chat citations | T8 |
| 3.3 | Live step tray during an in-flight turn, replacing the static "Searching…" bubble | T8 |
| 3.4 | Reuse the step tray as the historical audit-log entry view | T7, T8 |
| 3.5 | Accessible data-table fallback under the trends chart | T8 |
| 3.6 | Consolidate the two divergent trend charts into one shared `TrendChart` | T8 |
| 3.7 | Reuse `PageImageOverlay` as a shared provenance panel | T7, T8 |
| 3.8 | Local Diagnostics settings panel over the existing `/monitoring/metrics` | T7 |

### Wave 4 — Reach (independent; sequence by appetite)

| # | Item | Source | Note |
|---|---|---|---|
| 4.1 | HC-M06 extraction eval card (synthetic Synthea-derived golden set) | T7 | The named, overdue flagship data-science deliverable |
| 4.2 | `char_start`/`char_end` on `Observation`; wire `extract_spans.with_span()` into lab extraction | T7 | Today a diagnosis traces to an exact quote but a **lab value only traces to a page** — backwards, given the product's purpose |
| 4.3 | SMART Health Link resolver → existing `parse_fhir_bundle` import path | T4 | The one standards-track lane where a patient pulls their own records with no cloud intermediary |
| 4.4 | Gated, opt-in MCP HTTP router inside the existing FastAPI app | T4 | Off by default; `Origin`/`Host` allowlist + loopback bind; `retrieve_chunks` excluded from the default set |
| 4.5 | Local ASR (whisper.cpp) behind dictation | T5 | Closes a live local-first gap — the current path uses the browser Web Speech API, which is cloud |
| 4.6 | Kokoro-82M TTS for "read this explanation aloud" | T5 | Serves the stated low-vision/low-literacy accessibility motivation |
| 4.7 | Embedding upgrade to Qwen3-Embedding-0.6B | T5 | Real MTEB uplift, but requires a re-embed migration — and interacts with `test_api_rag_index_002b`'s 0.7 threshold, which must **not** be lowered |
| 4.8 | Compliance doc sections: FTC HBNR, EU AI Act, MHMDA/state health-data laws | T7 | Currently silent on three regimes that plausibly touch this product shape |

---

## 4. The "do not build" list

Research that concludes "don't" is worth as much as research that concludes
"do," and is easier to lose. Each of these was an explicit recommendation.

| Don't | Why | Source |
|---|---|---|
| **Integrate PersonaPlex** | Real (NVIDIA, full-duplex speech-to-speech on Kyutai's Moshi, MIT code / NVIDIA Open Model License weights) but wants 24GB+ VRAM, is English-only, has no documented Windows path, and generates its own spoken responses — architecturally incompatible with a system where every output must pass `guardrails/` | T5 |
| **Use `LlamaDiskCache` / any on-disk KV persistence** | `llama-cpp-python` persists KV state **unencrypted** to `.cache/llama_cache` via `diskcache`. KV cache is PHI-derived. This is a hard never, not a tradeoff | T2 |
| **Add Reflexion-style self-critique to `reflect`** | Small models share error modes between generator and judge; the existing deterministic check is the better-evidenced pattern | T3 |
| **Use an LLM as judge for any of the six safety axes** | Judge-ranking instability across 21 judges; these axes gate CI | T3 |
| **Add a Gemma-4-26B-MoE tier entry** | Imposes a 32GB floor for worse CPU-inference locality than the equal-active-size dense `gemma4-12b` already configured | T2 |
| **Add speculative decoding or `--n-cpu-moe` expert offload** | `n_gpu_layers: 0` everywhere — there is no VRAM to offload from | T2 |
| **Adopt a medically-tuned generator (MedGemma / OpenBioLLM / Meditron)** | A model trained to sound more clinical cuts directly against a zero-tolerance advice-leakage axis | T5 |
| **Add Piper as a new TTS dependency** | Effectively end-of-life; unmaintained since Oct 2025 | T5 |
| **Build direct Epic/Cerner OAuth-to-EHR this cycle** | Gated by institutional sponsorship, not cryptography. Record as a documented decision, not a silent omission | T4 |
| **Build a home-grown severity/risk score over lab flags** | Crosses the diagnosis boundary `interpret_safety.py` exists to hold | T7 |
| **Tailwind v4 / React 19 migrations now** | No product-facing payoff on a localhost build; ~92 files touched | T8 |

---

## 5. Items requiring approval before work starts

Per `CLAUDE.md`, these cannot be started by an agent acting alone.

**Owner approval (ask-before-touching files):**
- Anything touching `modules/verifier_agent.py` or `modules/faithfulness.py` — Track 3 flags them as prior art for a future verifier; both are on the ask-first list (HC-M11).
- Wave 4.4's scoped personal-access-token model touches `core/auth.py`.

**Legal / compliance review:**
- **FDA non-device posture** — Track 7 rates this the single item with real regulatory exposure if asserted incorrectly. Confirm before any "not a medical device" claim ships in product or marketing copy.
- MHMDA / state consumer-health-data laws — the regime with the least clean local-only-architecture defense.
- BioLORD-2023 or any UMLS/SNOMED-trained embedding model — redistribution terms.

**A note on Fable 5.1 and PHI:** Claude Fable 5.1 requires 30-day data
retention and is not available under zero-data-retention unless expressly
authorized by Anthropic. That has no bearing on the product (which is local and
sends nothing anywhere), but it does bear on **development**: no real or
realistic PHI may appear in a frontier-model audit context. See
[`FRONTIER-AUDIT-PROMPT.md`](FRONTIER-AUDIT-PROMPT.md) §Data boundary.

---

## 6. What this synthesis does not tell you

- **No effort estimate is calibrated.** S/M/L came from eight agents applying
  their own scales in isolation. Treat them as ordinal within a track, not
  comparable across tracks.
- **No latency, RAM, or quality figure was measured on this codebase.** Every
  number is reported from a source. The two constrained-decoding figures (§2)
  disagree by roughly an order of magnitude, which is what unmeasured numbers do.
- **Wave 4 is not ordered.** Those items are genuinely independent; sequence
  them by appetite, not by this document.
- **The competitive picture may already be stale.** Track 6's central finding —
  that Epic's native in-portal AI result summaries are a bigger strategic threat
  than any startup — is a market claim, and markets move faster than this
  document will be updated.
