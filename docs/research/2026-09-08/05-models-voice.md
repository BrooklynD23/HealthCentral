# Track 5 — Open-Weight Models, the NVIDIA Local Stack, and Voice

Research date: 2026-09-08. Model knowledge cutoff: May 2026 — everything below
about releases after that date is either backed by a fetched/searched source
(cited inline) or marked `[UNVERIFIED]`. `huggingface.co` and `hf.co` were
**not directly fetchable** from this session (network egress proxy blocks
them, confirming the suspicion already recorded in
`modules/model_selector.py`'s own comment). Where a claim rests on Hugging
Face repo existence, it is corroborated through independent search-engine
indexing of the HF page (title + snippet), not a direct page fetch — this is
weaker evidence than a fetch and is flagged as such.

## Summary

- **PersonaPlex is real.** It is NVIDIA's open-sourced full-duplex
  speech-to-speech conversational model, built on Kyutai's Moshi, released as
  code (MIT) + weights (NVIDIA Open Model License) on GitHub and Hugging Face.
  It is **not a fit for this app**: it wants a 24GB+ VRAM GPU for real-time
  operation, is English-only, has no documented Windows path, and — more
  fundamentally — it is an end-to-end dialogue agent that generates its own
  spoken responses, which is architecturally incompatible with a system whose
  every LLM output must pass through `modules/agent/guardrails/`. Full
  findings and citations in §1.
- **The repo's two placeholder Gemma 4 GGUF org paths are substantially
  correct** (both `unsloth` and `ggml-org` publish Gemma 4 GGUFs), but the
  exact casing in `model_selector.py` (`e2b`/`e4b`/`12b`, all lowercase)
  disagrees with what search-indexed HF pages show (`E2B`/`E4B` capitalized,
  `12B`/`12b` inconsistent across mirrors). This needs a live
  `huggingface_hub.list_repo_files()` check at download time, not a hand
  edit — see §2.
- **0.5B models cannot reliably plan multi-turn tool use.** Public
  tool-calling benchmarks put Qwen3-0.6B's BFCL-style multi-turn accuracy at
  ~1.4% and Qwen2.5-0.5B-class models fail "judgment traps" even when
  single-call latency is fine. An LLM planner is only defensible at ~1.7B+
  and should still ship behind the existing deterministic planner as
  fallback. See §3.
- **A medically-tuned generator is a plausible liability, not a clear win,**
  for this app's zero-tolerance advice-leakage axis — the literature found
  in this pass says medical fine-tuning raises domain confidence without a
  matching increase in the model's willingness to withhold or redirect. The
  existing "general instruct model + retrieval + citation gate +
  `interpret_safety`" design is the safer shape. Clinical **embedding**
  models are a different, lower-risk story. See §4.
- **Voice must move off the browser's cloud STT.** The already-implemented
  MED-VOICE-001 feature uses the Web Speech API, and its own PRD says so in
  writing: *"Speech recognition may be processed by the browser's speech
  service (e.g., Google for Chrome)"* — that is a live violation of this
  track's own "voice is biometric, cloud is disqualified" constraint, sitting
  in production today. whisper.cpp (MIT, proven Windows CPU support) and
  Kokoro-82M (Apache-2.0, proven Windows CPU support) are ready, small,
  license-clean local replacements. See §5.
- **Embeddings: swap `all-MiniLM-L6-v2` for `Qwen3-Embedding-0.6B`** (Apache
  2.0, CPU-friendly, real MTEB uplift) rather than a clinical model — the
  standout clinical option (BioLORD-2023) carries an unresolved UMLS/SNOMED-CT
  redistribution-license question that should not be defaulted into a
  shipping product silently. Also found: `core/config.py`'s
  `default_embeddings_model = "bge-small-en-v1.5"` is dead code — nothing
  reads it. See §6.

---

## 1. PersonaPlex — verification (read this section first)

**Verdict: real project, correctly named "PersonaPlex," not a fit for this app.**

The project owner's "PersonaPlex" is a real NVIDIA release, not a
misremembering of Riva/Parakeet/Canary/NeMo/Magpie/ACE. It sits *inside* the
NVIDIA ACE family of conversational-AI work but is its own named model.

**What it is.** A 7B-parameter, full-duplex (listens and speaks
simultaneously) speech-to-speech conversational model. It is built directly
on Kyutai's open-source **Moshi** architecture and weights, extended by
NVIDIA's Applied Deep Learning Research (ADLR) group for persona control
(text-prompt role definition + audio voice conditioning). Speaker switching
is reported around 70ms; end-to-end response latency around 257ms.
[research.nvidia.com/labs/adlr/personaplex](https://research.nvidia.com/labs/adlr/personaplex),
[GitHub: NVIDIA/personaplex](https://github.com/NVIDIA/personaplex).

**License.**
- Code: **MIT**.
- Model weights: **NVIDIA Open Model License**.
Confirmed directly from the repo's own README (fetched via
`raw.githubusercontent.com/NVIDIA/personaplex/main/README.md`, since
`huggingface.co`/`github.com` HTML pages for this repo were reachable but the
HF model card itself was not).
[GitHub: NVIDIA/personaplex](https://github.com/NVIDIA/personaplex),
[HF (gated): nvidia/personaplex-7b-v1](https://huggingface.co/nvidia/personaplex-7b-v1) —
title/gating notice only, page contents not fetchable this session.
The NVIDIA Open Model License itself is a generally permissive
commercial-use license (no explicit health/medical field-of-use carve-out
found), but it does auto-terminate if a model's built-in safety guardrails
are bypassed, and it carries the standard export-control and patent-litigation
termination clauses common to NVIDIA's open licenses.
[NVIDIA Open Model License Agreement PDF](https://developer.download.nvidia.com/licenses/nvidia-open-model-license-agreement-june-2024.pdf).

**Release timeline.** The underlying research paper is numbered
`arXiv:2602.06053` (arXiv's YYMM numbering places the submission around
February 2026); the public GitHub open-sourcing was covered by trade press
in August 2026. [Open Source For You, Aug 2026](https://www.opensourceforu.com/2026/08/nvidia-open-sources-personaplex-built-on-moshi/).
So: research paper ~Feb 2026, code+weights publicly open-sourced by ~Aug 2026
— both after this model's May-2026 knowledge cutoff, hence entirely
outside prior knowledge and correctly a "verify, don't assume" item.

**Hardware.** NVIDIA's own guidance (per the fetched README) is GPU-first:
install steps assume CUDA, note a temporary Blackwell-GPU compatibility
issue, and offer `--cpu-offload` (via `accelerate`) only for "insufficient
GPU memory," not as a first-class CPU deployment path. Community writeups
converge on **24GB+ VRAM** (A10G/A40/RTX 3090/4090-class) for low-latency
real-time operation, with heavier quantization (down to Q3_K_M, ~4.5GB VRAM)
usable at "noticeable quality loss for voice tasks." A pure-CPU "offline
evaluation" mode is mentioned in the README, but nothing in this research
pass shows CPU-only timings — and PersonaPlex's own streaming design
requires ~80ms-per-audio-frame turnaround, which is a very tight budget for
a 7B model on CPU. Treat "runs acceptably CPU-only" as **not demonstrated**.
[README via raw.githubusercontent.com](https://raw.githubusercontent.com/NVIDIA/personaplex/main/README.md),
GPU/VRAM figures from search-aggregated community guides (madebyagents.com,
kunalganglani.com) — **[UNVERIFIED against a primary source]**, treat as
directional only.

**Windows.** The README (primary source, fetched) gives no Windows-specific
instructions; installation is Linux/CUDA-shaped (`libopus-dev` via
apt/dnf, CUDA 13 notes for Blackwell). No evidence of an official Windows
build path was found.

**Language.** English-only — inherited from Moshi, which was trained
primarily on the Fisher English channel-separated conversational corpus (the
only public dataset of its kind); NVIDIA/Kyutai discussion threads describe
multilingual fine-tuning as an open, unsolved problem, not a roadmap item.
[Kyutai moshi FAQ](https://github.com/kyutai-labs/moshi/blob/main/FAQ.md),
[HF discussion #40](https://huggingface.co/nvidia/personaplex-7b-v1/discussions/40) (title/snippet only).

**Why it is the wrong fit even setting hardware aside.** PersonaPlex is an
end-to-end conversational agent: it decides what to say and says it, in one
model, trained for natural turn-taking and persona-consistent dialogue. This
app's entire safety architecture (per `docs/research/2026-09-08/00-brief.md`
§2) depends on every LLM output routing through
`modules/agent/guardrails/{classifier,groundedness,guard,redaction_gate}`
and citation enforcement (`[REFERENCE:N]`/`[YOUR_RESULTS:N]`) before it
reaches the user. A model that speaks its own turns doesn't have a seam to
insert that pipeline into without either (a) neutering PersonaPlex down to
a TTS-only role — at which point its 7B/24GB-VRAM cost buys nothing that
Kokoro-82M doesn't already deliver on a CPU — or (b) letting it originate
un-vetted spoken content, which the project's own hard invariants forbid.
**Conclusion: do not pursue PersonaPlex for this app.** It is legitimate,
interesting NVIDIA research, and a reasonable choice for a GPU-equipped,
English-only, open-domain voice-assistant product — none of which describes
this repo's target (Windows-native, 8–32GB RAM, often no GPU, closed-domain,
guardrail-gated, no-medical-advice).

---

## 2. Open-weight LLM landscape, September 2026

All version/date claims below were confirmed via web search this session;
none were assumed from pre-cutoff knowledge.

| Family | Current flagship / relevant sizes | Context | License | Notes |
|---|---|---|---|---|
| **Qwen** | Qwen3.8-Max (API-first); **Qwen3.8-27B** open weights (Aug 14, 2026), multimodal text/image/video | not specified in search | **Apache 2.0** | Qwen3.8-Flash-Next (MoE) also opened as an early Qwen4-architecture preview. [codersera.com](https://codersera.com/blog/qwen-3-5-complete-guide-2026/), [digitalapplied.com](https://www.digitalapplied.com/blog/qwen-closed-flagship-pivot-open-weight-retreat-2026) |
| **Gemma** | **Gemma 4** (Apr 2, 2026): E2B (2.3B eff.), E4B (4.5B eff.), 26B-A4B MoE (25.2B total/3.8B active), 31B dense | 128K (small) / 256K (medium+) | **True Apache 2.0** — a real change from the old "Gemma Terms of Use" custom license used through Gemma 3 | Multimodal (text+image all sizes; +audio on E2B/E4B/12B). [ai.google.dev/gemma/docs/core](https://ai.google.dev/gemma/docs/core), [winbuzzer.com](https://winbuzzer.com/2026/04/03/google-releases-gemma-4-open-models-under-apache-20-license-xcxwbn/) |
| **Llama** | Llama 4 (Apr 2025 gen.), MoE, multimodal | — | Meta custom license | Acceptable Use Policy explicitly prohibits "unauthorized or unlicensed practice of... medical/health... professional practices" and restricts processing others' health data without a legal basis — worth flagging if Llama is ever added to this repo, even though this app is explanatory/educational, not a medical service. [llama.com/llama4/use-policy](https://www.llama.com/llama4/use-policy/) |
| **Mistral** | Mistral Large 3 (per search) | — | Apache 2.0 | Not currently pinned in this repo; no blocker found. |
| **DeepSeek** | DeepSeek V4 (Apr 24, 2026): V4-Flash (284B total/13B active), V4-Pro (1.6T total/49B active) | 1M tokens | MIT | **Not viable for this app regardless of license** — even the "Flash" variant's 284B total parameters means ~140GB+ on disk at Q4, far outside "8–32GB RAM, often no GPU." [kingy.ai state-of-open-weight roundup](https://kingy.ai/blog/state-of-open-weight-ai-models/) |
| **Phi** | Phi-4 (Jan 2025, 14B); **Phi-4-mini (Feb 2026, 3.8B, 128K ctx)**; Phi-4-multimodal (Feb 2026, 5.6B); Phi-4-reasoning-vision (Mar 2026, 15B) | up to 128K | **MIT** | The repo's currently pinned "mid" tier, `Phi-3-mini-4k-instruct`, is a 2024-vintage, 4K-context model — Phi-4-mini is a same-size-class (3.8B), same-license (MIT) successor with 32x the context and a year-plus of further training. Direct swap candidate. [presenc.ai Phi-4 lineage](https://presenc.ai/research/microsoft-phi-4-family-lineage-2026) |
| **OLMo** | OLMo 3 (announced Nov 2025), 7B & 32B, base/instruct/reasoning | — | Apache 2.0 | Distinctive: ships weights **+ full training data + training code + every checkpoint** — the most auditable option found, if provenance/transparency ever becomes a stated requirement (it is not currently a stated requirement, but is relevant to a health app's evidentiary posture). [allenai.org/blog/olmo3](https://allenai.org/blog/olmo3) |
| **gpt-oss** | gpt-oss-20b, gpt-oss-120b (OpenAI) | — | Apache 2.0 | Ships with **native function-calling / tool-use / structured-output support** as a first-class training target (the "harmony" response format), not a prompt convention. 20B fits ~12–16GB at Q4_K_M/MXFP4, runs on llama.cpp/GGUF. Directly relevant to the brief's gap #2 ("no constrained decoding") — this is the one family in this table explicitly trained for the exact capability this app's planner needs. [intuitionlabs.ai hardware reqs](https://intuitionlabs.ai/articles/hardware-requirements-gpt-oss-20b), [willitrunai.com](https://willitrunai.com/models/gpt-oss-20b) |

### Gemma 4 GGUF placeholder verification (the specific ask)

`model_selector.py` flags three repo strings as `PLACEHOLDER (verify before
production)`:

| Repo string in code | Search-indexed HF pages found | Verdict |
|---|---|---|
| `unsloth/gemma-4-e2b-it-GGUF` | `unsloth/gemma-4-E2B-it-GGUF`, plus `-qat-GGUF` and `-qat-mobile-GGUF` variants | **Repo exists in substance; casing differs** (`E2B` capitalized in indexed pages vs. lowercase `e2b` in code) |
| `unsloth/gemma-4-e4b-it-GGUF` | `unsloth/gemma-4-E4B-it-GGUF`, `-qat-GGUF` variant | Same casing discrepancy |
| `ggml-org/gemma-4-12b-it-GGUF` | `ggml-org/gemma-4-12B-it-GGUF` (confirmed via a fetched search summary describing an Apache-2.0-licensed, `gemma4`-architecture GGUF repo with Q4_0/Q8_0 quants and `llama serve -hf ggml-org/gemma-4-12B-it-GGUF` as the run command) | Repo exists; casing differs (`12B` vs `12b`) |

Because `huggingface.co` is unreachable from this session (confirmed by
repeated `EGRESS_BLOCKED` errors on `huggingface.co` and `hf.co`, matching
the code's own comment that "automated sandboxed sessions may not be able to
confirm them"), this is **search-index verification, not a page fetch** —
solid enough to say "these are not fabricated placeholders, something real
is there," not solid enough to hand-edit the exact string with confidence.
**Recommendation stays what the code already does defensively**: keep
`filename=None` + `filename_pattern` discovery via
`huggingface_hub.list_repo_files()` at download time (this already tolerates
casing drift), and additionally have `download_model()` try the repo ID
case-insensitively or log a clear "repo not found, verify org/name" error
rather than a bare exception — a small, surgical robustness fix, not a
rewrite of the placeholder strings by hand.

Also note: the release-date comment in `model_selector.py`
(*"released 2026-06-03"*) doesn't match the primary Gemma 4 release date
found in this research (**April 2, 2026**); June 2026 activity found in
search results (e.g., an Unsloth QAT-GGUF blog post dated 2026-06-08) looks
like *quantization tooling* catching up to the model, not the model's own
release. Minor, but worth a one-line correction in the same commit that
touches this file next.

---

## 3. Small-model tool-calling and structured-output quality

This is the load-bearing question for whether Track 3's LLM planner is
viable at the "low" (0.5B) tier, and the evidence says **no**.

**Berkeley Function-Calling Leaderboard (BFCL) and successors**, queried for
sub-3B models:
- Qwen3-0.6B: 45.76% overall BFCL accuracy, but **1.38% multi-turn accuracy**.
- xLAM-2-1b-fc-r: 53.97% overall, 8.38% multi-turn.
- Qwen3-1.7B: 55.49% overall, 16.88% multi-turn.
- xLAM-2-3b-fc-r: 65.74% overall, 55.62% multi-turn (the first size class in
  this scan with multi-turn accuracy in a plausible-to-ship range).
[arxiv 2511.22138 "TinyLLM" search summary](https://arxiv.org/pdf/2511.22138)
(fetch blocked, search-summary only).

**A second, independently run local-model benchmark**
([lintware/tool-calling-benchmark](https://github.com/lintware/tool-calling-benchmark),
a fork of MikeVeerman's tool-calling-benchmark, fetched directly) tested 21
models including this repo's exact "low" tier pin:
- `qwen2.5:0.5b` — Agent Score **0.640**, one of only two models fast enough
  for sub-1-second latency, but the benchmark's own conclusion: *"both fail
  on judgment traps... full autonomy is still premature at this model size
  ... even the best model misses 10% of actionable prompts."*
- `qwen3:0.6b` — 0.880 at 3.4s.
- `qwen3:1.7b` — **0.960**, the top score in the whole sweep (0.900 action +
  1.000 restraint + zero wrong-tool calls), at 10.7s latency.
- `lfm2.5:1.2b` — 0.920 at 1.6s (state-space architecture, not transformer —
  evidence that "parameter count is a weak predictor" of tool-calling
  quality; architecture and post-training matter as much as raw size).
- `ministral-3:3b` — 0.800; `phi4-mini:3.8b` — 0.780 (both *below* the 1–2B
  leaders in this particular sweep, reinforcing the "size is not the whole
  story" point).

**Ceiling for context:** on BFCL v4, the best self-hostable model found in
this pass is `Llama-3-Groq-70B-Tool-Use` at 90.76% overall — 70B, outside
this app's "consumer hardware" scope, included only to show how much
headroom exists above what a laptop can run.
[qaskills.sh BFCL guide](https://qaskills.sh/blog/bfcl-berkeley-function-calling-leaderboard-guide-2026),
[localaimaster.com Ollama tool-calling ranking](https://localaimaster.com/blog/best-ollama-models-tool-calling).

**Bottom line for this repo:** the "low" tier's pinned model (Qwen2.5-0.5B)
sits in the range where single-shot, low-stakes tool selection is roughly
workable but multi-turn agentic planning is not — and this app's agent loop
(`plan → act → reflect → loop|draft → guard`, per the brief) is exactly the
multi-turn shape that collapses hardest at this scale. **An LLM planner
should not be enabled at the "low" tier.** It becomes plausible starting
around 1.7B (the "mid" tier's Gemma4-E4B at 4.5B effective, or a Phi-4-mini
swap at 3.8B, are both comfortably above the size where multi-turn accuracy
stops being near-zero) — and even there, the existing deterministic
`_ANALYTE_KEYWORDS` planner should stay wired as a fallback/parallel check
rather than being fully retired, given that even the best-scoring small
model in the benchmark above still "misses 10% of actionable prompts."

---

## 4. Medical/clinical open models

| Model | License | Status Sept 2026 | Verdict for this app |
|---|---|---|---|
| **MedGemma** (Google) | "Health AI Developer Foundations" terms — open-weight, permissive for research+commercial, but **not** the plain Apache 2.0 that Gemma itself now uses | MedGemma 1.5 shipped Jan 13, 2026; built on Gemma 3, not Gemma 4 | License needs its own read before use (it is not Apache 2.0 despite the Gemma name). [developers.google.com/health-ai-developer-foundations/medgemma/model-card](https://developers.google.com/health-ai-developer-foundations/medgemma/model-card) |
| **OpenBioLLM** | Apache 2.0 claimed for the flagship — but several checkpoints are Llama-derived and may carry Llama's AUP on top | 70B flagship; smaller sizes exist historically | License must be checked **per artifact**, not assumed from the family name. |
| **Meditron / "Fully Open Meditron"** (EPFL) | Open code+data+eval pipeline | arXiv paper May 2026; [github.com/EPFLiGHT/FullyOpenMeditron](https://github.com/EPFLiGHT/FullyOpenMeditron) | Explicitly framed as **clinical decision support (LLM-CDSS)** — that framing is in direct tension with this app's "no diagnosis" invariant regardless of how well-audited the pipeline is. |
| **BioMistral-7B** (this repo's current "high" tier pin) | **Apache 2.0**, confirmed on the HF model card; deliberately trained only on the "Commercial Use Allowed" (non-NC) subset of PubMed Central OA, so no hidden CC-BY-NC contamination | Feb 2024 vintage — ~2.5 years stale relative to the field | License is genuinely clean (this was worth checking — a CC-BY-NC leak into a commercial-license-sensitive pin would have been a real finding, and it isn't one). Staleness, not licensing, is the actual concern. |

**Should a medically-tuned generator be used at all? No — this is the
brief's "assess honestly" question, and the evidence found points one way.**
Two independent pieces of research surfaced in this pass say the same thing
from different angles:
- *"Medical specialization can improve domain confidence without
  necessarily improving safety: the model gains more usable medical
  knowledge, but not a correspondingly stronger boundary for when such
  knowledge should be withheld or safely redirected."* — from a benchmark on
  high-risk medical queries. [arXiv 2606.28332, "When Medical Safety
  Alignment Fails"](https://arxiv.org/html/2606.28332) (search-summary; fetch
  blocked).
- *"Safety and accuracy follow different scaling laws in clinical large
  language models"* — the title alone states the finding: better medical
  accuracy is not correlated with better refusal/redirection behavior.
  [arXiv 2605.04039](https://arxiv.org/pdf/2605.04039) (search-summary; fetch
  blocked).
- A third summary source put it plainly: models with high diagnostic recall
  showed *"low safety pass rates — identifying the diagnosis but not
  recognizing the risk."* [cortico.health](https://cortico.health/article/medsafedx-ai-safety/).

A model trained to sound clinically fluent and confident is, almost by
definition, trained in the opposite direction from "abstain, cite, defer to
a clinician" — which is this app's entire safety posture
(`modules/interpret_safety.py`, the citation-enforcement templates in
`docs/model_tiers/*`, the `advice-leakage` eval axis in
`modules/agent/eval/scorer.py` per the brief). **Recommendation: do not add
a medically-tuned generator, and treat BioMistral's "high" tier slot as a
candidate for retirement/relabeling** (its license is fine; its *design
intent* — sound more clinical — is arguably working against this app's
stated goal) **in favor of a general-purpose, well-behaved instruct model**
(Gemma4-12B or gpt-oss-20b, both Apache 2.0, both with native
function-calling) at that hardware budget.

**Clinical embedding models are a different, better trade.** An embedding
model doesn't generate patient-facing text — it only changes which
knowledge-base/reference chunks get retrieved for the generator to cite. The
risk surface is retrieval precision/recall, not "the model said something
unsafe out loud." That makes a domain-tuned embedding model a much lower-risk
lever than a domain-tuned generator, and is why §6 recommends investing there
instead of in a clinical LLM.

---

## 5. Voice, fully offline

### What's already in the repo (read before proposing anything new)

`docs/plans/2026-03-04-prd-voice-gamification-ingest-design.md` (MED-VOICE-001,
already implemented per `docs/plans/2026-03-04-gam-voice-ingest-implementation.md`
Tasks 10–13) ships dose-note dictation via the browser's native
`SpeechRecognition`/`webkitSpeechRecognition` API. Its own PRD text:

> *"Audio storage: None — HealthCentral stores only the confirmed text
> transcript. Speech recognition may be processed by the browser's speech
> service (e.g., Google for Chrome)"*
> *(Non-Goals) — "Offline voice recognition"*

This is a **real, already-shipped gap** relative to this track's own
constraint ("voice is biometric data, so anything cloud-based is
disqualified") and relative to `CLAUDE.md`'s "Local-first: No network calls
in product code paths" invariant, even though it is technically the
*browser*, not this app's backend, making the network call. Nothing in this
research changes that this is worth closing; §5 below is written with that
in mind — every option evaluated is chosen specifically because it can
replace the cloud STT step without touching the rest of the already-built
transcript/notes/badge pipeline.

### ASR (speech → text)

| Option | License | Size | CPU/Windows | Medical-vocabulary accuracy |
|---|---|---|---|---|
| **whisper.cpp** (OpenAI Whisper ported to C/C++) | MIT | tiny ~75MB / base ~140MB / small ~460MB | Mature — prebuilt Windows `.exe` releases exist (e.g. `regstuff/whisper.cpp_windows`), CPU-only fully viable | General Whisper has **no medical entity tuning**; one comparison found Whisper at 25.3% WER on radiology dictation vs. a medically-tuned model's 4.6% — a **5x gap specifically on drug/analyte-style vocabulary**, exactly the failure mode the brief asks about. Whisper *does* support `initial_prompt` vocabulary biasing, which can be used to inject a patient's own medication/analyte names at inference time as a cheap mitigation. [assemblyai.com medical voice recognition](https://www.assemblyai.com/blog/medical-voice-recognition) |
| **NVIDIA Parakeet** (TDT-0.6B-v3) | **CC-BY-4.0** — cleaner than most, no field-of-use restriction | 0.6B | NVIDIA's own runtime is NeMo/PyTorch (GPU-leaning); **third-party** CPU/ONNX/pure-C ports exist and report Windows/macOS/Linux CPU support out of the box (`parakeet.cpp`, various `parakeet-onnx` repos) — real dependency risk: these are community-maintained, not NVIDIA-maintained | 25-language coverage with auto language ID; general-purpose WER, not medically benchmarked in this pass — **[UNVERIFIED for medical vocabulary]** |
| **NVIDIA Canary-Qwen-2.5B** | CC-BY-4.0 | 2.5B | Tops the general Open ASR Leaderboard at 5.63% WER | Heavier than needed for short symptom-note dictation; not medically benchmarked here |
| **Moonshine** (Useful Sensors) | **[UNVERIFIED — exact license not confirmed this session]** | Tiny 26MB (12.66% WER) / Base 58MB (10.07% WER) | Explicitly designed CPU-first for Raspberry-Pi-class edge devices; Moonshine V2 (arXiv 2602.12241) adds streaming attention for lower time-to-first-token | Not medically benchmarked in this pass |

**For use case (a) — dictating a symptom/observation note:** whisper.cpp
`base.en`/`small.en` is the safe default (mature, MIT, proven Windows
support, tunable via `initial_prompt` vocabulary biasing to mitigate the
drug/analyte-name weakness directly). Parakeet via a vetted ONNX/ggml port is
a credible "mid/high tier" upgrade if the team is comfortable depending on a
community-maintained runtime port rather than NVIDIA's own tooling.

### Speaker diarization

**Not required for either of the two use cases in scope** (both are
single-speaker: the patient dictating, or the app reading text back). Noted
for completeness: `pyannote.audio` code is MIT; the `speaker-diarization-3.1`
pipeline is MIT, the newer `speaker-diarization-community-1` pipeline is
CC-BY-4.0; both run fully offline once weights are cached, but weights are
gated behind free HF registration. DER ~11–19% on standard benchmarks.
[pyannote.ai/blog/community-1](https://www.pyannote.ai/blog/community-1).
Recommendation: do not build this now; revisit only if a future feature
needs to separate a caregiver's voice from a patient's in one recording.

### TTS (text → speech)

| Option | License | Size | Windows/CPU evidence | Verdict |
|---|---|---|---|---|
| **Kokoro-82M** | **Apache 2.0** | ~327MB, 54 voices/8 languages | Confirmed real-time-factor as low as **0.16x** (≈6x faster than realtime) on general hardware; a specific Windows 11 + 11th-gen Core i7 CPU benchmark reported **35x–100x** realtime generation | **Recommended default across all tiers.** Small, fast, license-clean, Windows-proven. |
| **Piper** | MIT | very small, ~40ms first-audio latency | Long-time Raspberry-Pi/embedded default | **Upstream archived on GitHub, Oct 6, 2025** — read-only, unmaintained. Still functions (e.g. as a Home Assistant Wyoming add-on) but should not be adopted as a *new* dependency in 2026; multiple current sources explicitly point migrators to Kokoro or XTTS instead. |
| **Orpheus** | [UNVERIFIED — license not confirmed this session] | 3B | Described as rivaling ElevenLabs-quality emotional speech | Much heavier footprint than needed for "read this explanation aloud"; reserve as an optional high-tier nicety only, not a default. |
| **XTTS v2 (Coqui)** | **[UNVERIFIED — Coqui's model licenses have historically carried non-commercial/paid-tier terms above a revenue threshold; confirm before use]** | heavier, voice-cloning capable | — | Do not adopt without an explicit license check; voice cloning is also a capability this app has no stated need for. |

**For use case (b) — reading a grounded explanation aloud (accessibility for
low-vision/low-literacy users):** Kokoro-82M is a strong, low-risk match.
The text being spoken is app-authored, already-cited, already
guardrail-passed content — the TTS step adds **no new biometric exposure at
all** (the "voice" is synthetic, not the patient's), so this is one of the
lowest-risk, highest-value additions in this whole track relative to its
cost.

---

## 6. Embeddings

**Current state (verified by reading the code, not inferred):**
- `modules/embeddings.py:18,34` — `EmbeddingsModule`'s actual default is
  `all-MiniLM-L6-v2` (384-dim, general-purpose, 2021-era, ~22M params).
- `modules/rag.py:168` and `api/documents.py:850` both instantiate
  `EmbeddingsModule()` with **no arguments** — so the MiniLM default is what
  actually runs in production.
- `core/config.py:89` declares `default_embeddings_model: str =
  "bge-small-en-v1.5"` — **grep confirms nothing else in the codebase reads
  this field.** It is dead configuration that looks load-bearing but isn't;
  worth a one-line fix (wire it up or delete it) independent of any model
  choice made below.

**Candidates surveyed:**

| Model | License | Size | Notes |
|---|---|---|---|
| `all-MiniLM-L6-v2` (current) | Apache 2.0 | ~22M params, 384-dim | General-purpose, no clinical tuning, dated. |
| **Qwen3-Embedding-0.6B** | **Apache 2.0** | ~0.6B params, ~1.2–1.5GB, CPU-friendly, 32K context | 70.7 on MTEB-eng-v2 (per search-aggregated benchmark) — a real quality jump over MiniLM-class models, still self-hostable on CPU, no field-of-use complications. **Recommended default.** [qwenlm.github.io/blog/qwen3-embedding](https://qwenlm.github.io/blog/qwen3-embedding/) |
| **BioLORD-2023** | Model code MIT; **but trained on UMLS/SNOMED-CT-derived data (AGCT glossary)**, and the model card itself says users must independently hold proper UMLS/SNOMED-CT licensing | 768-dim, based on `all-mpnet-base-v2` | Best clinical-domain candidate found, but the UMLS/SNOMED-CT terms are **not simply "free everywhere"** — UMLS requires free U.S. NLM registration, SNOMED-CT licensing varies by country. For a Windows-native app with a potentially non-US install base, this is a real, unresolved compliance question, not a footnote. **Do not default to this without a legal/compliance sign-off on redistribution terms.** [huggingface.co/FremyCompany/BioLORD-2023](https://huggingface.co/FremyCompany/BioLORD-2023) (search-indexed, not fetched) |
| MedEmbed | [UNVERIFIED — exact license/size not confirmed this session] | — | Named in search results as a PubMed-triplet-trained clinical embedding model; needs its own verification pass before consideration. |

**Cost of switching (asked for explicitly, stated plainly):**
1. **Full re-embed required.** Vector spaces from different models are not
   comparable — swapping the embedding model means every existing chunk in
   every profile's RAG index must be re-embedded through the new model. This
   is a per-profile local job (small individually, but must run as a
   background migration on upgrade, not silently on next query).
2. **Dimensionality changes.** MiniLM/BGE-small are 384-dim; Qwen3-Embedding-0.6B
   is larger natively (with Matryoshka truncation options); BioLORD is
   768-dim. Any fixed-dimension index/schema assumption needs updating
   alongside the model swap.
3. **`test_api_rag_index_002b`'s 0.7 cosine-similarity threshold is tuned to
   `all-MiniLM-L6-v2`'s specific embedding space.** Absolute cosine-similarity
   magnitudes are not a universal constant across embedding models — a
   swap requires **re-deriving** an appropriate threshold against the new
   model's own similarity distribution for equivalent semantically-similar
   pairs, documented in the same commit. This is explicitly **not** "lower
   the threshold to make the test pass" (which `CLAUDE.md` and this test's
   own history already forbid) — it is "measure what 'similar' looks like in
   the new space and set the gate there," which may land above, at, or below
   0.7 depending on the model; either outcome is fine as long as it's
   measured, not assumed.

---

## Proposed tier table

| Tier | RAM floor | LLM (generation) | LLM license | Embedding | ASR | TTS |
|---|---|---|---|---|---|---|
| **Low** | 8GB, no GPU | Qwen2.5-0.5B-Instruct (**keep** — existing pin; do not enable an LLM planner at this tier, see §3) | Apache 2.0 | Qwen3-Embedding-0.6B | whisper.cpp `tiny.en`/`base.en` (~75–140MB) | Kokoro-82M |
| **Mid** | 16GB | **Phi-4-mini-instruct (3.8B, 128K ctx)** replacing the stale `Phi-3-mini-4k-instruct`; or Gemma4-E4B (4.5B eff., native function-calling) as the multimodal alt | MIT (Phi-4-mini) / Apache 2.0 (Gemma4) | Qwen3-Embedding-0.6B | whisper.cpp `base.en`/`small.en` | Kokoro-82M |
| **High** | 32GB | Gemma4-12B or gpt-oss-20b (native tool-calling/structured-output) as the **default**; keep BioMistral-7B available but non-default given §4's advice-leakage finding | Apache 2.0 (both) | Qwen3-Embedding-0.6B (BioLORD-2023 only after UMLS/SNOMED-CT sign-off) | whisper.cpp `small.en`/`medium.en`, or Parakeet-TDT-0.6B via a vetted CPU/ONNX port | Kokoro-82M (Orpheus-3B optional, non-default) |

All footprints above are chosen to stay within this app's own stated
"8–32GB RAM, often no GPU" ceiling; nothing in this table requires a GPU.

---

## Recommendations

| Change | Integration point | Impact | Effort | Risk | License OK? |
|---|---|---|---|---|---|
| Do **not** integrate PersonaPlex | N/A | Closes the research question the project owner raised; avoids a GPU-only, English-only, guardrail-incompatible dependency entering the roadmap | N/A | N/A | MIT/NVIDIA Open Model License — moot, not adopting |
| Verify Gemma4 GGUF repo casing via `list_repo_files()` at download time rather than trusting the hardcoded string | `src/backend/modules/model_selector.py` `TIER_MODEL_CONFIG` comments | Removes "PLACEHOLDER" ambiguity flagged in `docs/model_tiers/README.md` | Low | Low — existing `filename_pattern` discovery already tolerates this | Apache 2.0 confirmed for Gemma 4 — OK |
| Swap "mid" tier `Phi-3-mini-4k-instruct` → `Phi-4-mini-instruct` | `model_selector.py` `TIER_MODEL_CONFIG["mid"]`, `docs/model_tiers/tier2_mid.md` | 4K → 128K context, same MIT license, newer training, same size class | Medium (retest citation-template prompting against the new model) | Low | MIT — OK |
| Gate any future LLM planner (Track 3) to mid/high tier only, never the 0.5B "low" tier; keep the deterministic keyword planner as a parallel fallback even at mid/high | `modules/agent/nodes/plan.py` injectable `planner` param | Prevents shipping a planner that BFCL-style evidence says will fail multi-turn tool selection ~10%+ of the time even at its best | N/A (policy decision) | Avoids a real reliability regression | N/A |
| Swap default embedding model `all-MiniLM-L6-v2` → `Qwen3-Embedding-0.6B` | `modules/embeddings.py` `EmbeddingsConfig` default; `modules/rag.py:168`; `api/documents.py:850` | Real retrieval-quality uplift (MTEB) | Medium–High — requires a re-embed migration and a re-derived (not lowered) similarity threshold for `test_api_rag_index_002b` | Medium | Apache 2.0 — OK |
| Delete or wire up the dead `default_embeddings_model = "bge-small-en-v1.5"` config | `core/config.py:89` | Removes a misleading unused setting | Low | Low | N/A |
| Add local ASR (whisper.cpp) as the engine behind dictation, replacing the browser Web Speech API's cloud dependency | New module (e.g. `modules/voice_asr.py`); wires into the existing MED-VOICE-001 transcript/notes flow | Closes a live local-first gap that is shipping today per the PRD's own text | High — new binary dependency, model packaging for Windows, mic-capture plumbing | Medium — new surface area, but touches no guardrail files | MIT — OK |
| Add Kokoro-82M for a "read this explanation aloud" accessibility feature | New module + a "listen" affordance on already-cited, guardrail-passed explanation views | Directly serves the app's stated low-vision/low-literacy accessibility motivation; zero biometric exposure (synthetic voice, app-authored text) | Medium | Low — text-in, audio-out, no guardrail-file changes | Apache 2.0 — OK |
| Do not adopt a medically-tuned generator (MedGemma/OpenBioLLM/Meditron) as the interpretation model | Advisory against a future change | Avoids the advice-leakage regression the cited safety-scaling-law research predicts | N/A | Avoids risk | Varies by model — moot, not recommending adoption |
| Reconsider BioMistral-7B's "high" tier default status (license is clean; design intent — sound more clinical — cuts against this app's goal; also 2.5 years stale) | `model_selector.py` `TIER_MODEL_CONFIG["high"]`, `docs/model_tiers/tier3_high.md` | Modernizes "high" tier toward a general-purpose, tool-calling-capable model without adding medical-generator risk | Medium | Low | Apache 2.0 — OK either way |
| Before ever adopting BioLORD-2023 (or any UMLS/SNOMED-trained embedding model), get a compliance read on redistribution terms | Pre-work for any future `embeddings.py` change | Avoids a real license-compliance gap for a Windows-native app with a potentially non-US install base | Low (a review, not code) | Medium if skipped | UNVERIFIED — needs explicit legal check, not a default |
| Treat Piper as end-of-life; do not add it as a new TTS dependency | Advisory | Avoids building a new feature on an archived, unmaintained upstream | N/A | N/A | MIT, but unmaintained since Oct 2025 |

---

## Sources

- [GitHub: NVIDIA/personaplex](https://github.com/NVIDIA/personaplex) — fetched directly (README)
- [research.nvidia.com/labs/adlr/personaplex](https://research.nvidia.com/labs/adlr/personaplex) (search-indexed)
- [Open Source For You — "Nvidia Open Sources PersonaPlex Built On Moshi"](https://www.opensourceforu.com/2026/08/nvidia-open-sources-personaplex-built-on-moshi/) (search-indexed)
- [DataCamp — NVIDIA PersonaPlex Tutorial](https://www.datacamp.com/tutorial/nvidia-personaplex-tutorial) (search-indexed)
- [Hugging Face: nvidia/personaplex-7b-v1](https://huggingface.co/nvidia/personaplex-7b-v1) (gated, search-indexed)
- [NVIDIA Open Model License Agreement (PDF)](https://developer.download.nvidia.com/licenses/nvidia-open-model-license-agreement-june-2024.pdf)
- [arXiv:2602.06053 — PersonaPlex paper](https://arxiv.org/pdf/2602.06053) (search-indexed; direct fetch blocked)
- [Kyutai moshi FAQ](https://github.com/kyutai-labs/moshi/blob/main/FAQ.md) (search-indexed)
- [madebyagents.com — PersonaPlex hardware](https://www.madebyagents.com/models/personaplex-7b) (search-indexed)
- [NVIDIA — 2026 European Open Speech Models: Parakeet, Canary, Nemotron](https://perspectives.nvidia.com/nemotron-speech/task/faq/what-are-the-most-production-ready-open-speech-recognition-models-for-european-l/) (search-indexed)
- [Hugging Face: nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) (search-indexed)
- [parakeet.cpp guide](https://news.creeta.com/en/parakeet-cpp-gguf-guide-2026/) (search-indexed)
- [Qwen release notes / codersera Qwen 3.5–3.8 guide](https://codersera.com/blog/qwen-3-5-complete-guide-2026/) (search-indexed)
- [digitalapplied.com — Qwen's open-weight retreat](https://www.digitalapplied.com/blog/qwen-closed-flagship-pivot-open-weight-retreat-2026) (search-indexed)
- [ai.google.dev/gemma/docs/core — Gemma 4 model overview](https://ai.google.dev/gemma/docs/core) (search-indexed)
- [winbuzzer.com — Google Releases Gemma 4 Under Apache 2.0](https://winbuzzer.com/2026/04/03/google-releases-gemma-4-open-models-under-apache-20-license-xcxwbn/) (search-indexed)
- [Hugging Face: unsloth/gemma-4-E2B-it-GGUF](https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF) (search-indexed)
- [Hugging Face: ggml-org/gemma-4-12B-it-GGUF](https://huggingface.co/ggml-org/gemma-4-12B-it-GGUF) (search-indexed)
- [Llama 4 Acceptable Use Policy](https://www.llama.com/llama4/use-policy/)
- [kingy.ai — State of Open-Weight AI Models](https://kingy.ai/blog/state-of-open-weight-ai-models/) (search-indexed)
- [intuitionlabs.ai — GPT-OSS-20B hardware requirements](https://intuitionlabs.ai/articles/hardware-requirements-gpt-oss-20b) (search-indexed)
- [willitrunai.com — GPT-OSS 20B VRAM requirements](https://willitrunai.com/models/gpt-oss-20b) (search-indexed)
- [presenc.ai — Microsoft Phi-4 Family Lineage 2026](https://presenc.ai/research/microsoft-phi-4-family-lineage-2026) (search-indexed)
- [allenai.org/blog/olmo3 — Olmo 3](https://allenai.org/blog/olmo3) (search-indexed)
- [Gorilla / BFCL leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)
- [qaskills.sh — BFCL explained 2026](https://qaskills.sh/blog/bfcl-berkeley-function-calling-leaderboard-guide-2026) (search-indexed)
- [localaimaster.com — Best Ollama Models for Tool Calling](https://localaimaster.com/blog/best-ollama-models-tool-calling) (search-indexed)
- [GitHub: lintware/tool-calling-benchmark](https://github.com/lintware/tool-calling-benchmark) — fetched directly
- [arXiv 2511.22138 — TinyLLM](https://arxiv.org/pdf/2511.22138) (search-indexed; direct fetch blocked)
- [developers.google.com/health-ai-developer-foundations/medgemma/model-card](https://developers.google.com/health-ai-developer-foundations/medgemma/model-card) (search-indexed)
- [arXiv 2605.16215 — Fully Open Meditron](https://arxiv.org/abs/2605.16215) / [github.com/EPFLiGHT/FullyOpenMeditron](https://github.com/EPFLiGHT/FullyOpenMeditron) (search-indexed)
- [Hugging Face: BioMistral/BioMistral-7B](https://huggingface.co/BioMistral/BioMistral-7B) (search-indexed)
- [arXiv 2402.10373 — BioMistral paper](https://arxiv.org/pdf/2402.10373) (search-indexed)
- [arXiv 2606.28332 — When Medical Safety Alignment Fails](https://arxiv.org/html/2606.28332) (search-indexed; direct fetch blocked)
- [arXiv 2605.04039 — Safety and accuracy follow different scaling laws in clinical LLMs](https://arxiv.org/pdf/2605.04039) (search-indexed; direct fetch blocked)
- [cortico.health — AI can pass medical exams, but clinical safety...](https://cortico.health/article/medsafedx-ai-safety/) (search-indexed)
- [assemblyai.com — Medical voice recognition: How AI solves terminology problems](https://www.assemblyai.com/blog/medical-voice-recognition) (search-indexed)
- [assemblyai.com — Best medical speech recognition software and APIs in 2026](https://www.assemblyai.com/blog/best-medical-speech-recognition-software-and-apis) (search-indexed)
- [GitHub: moonshine-ai/moonshine](https://github.com/moonshine-ai/moonshine) (search-indexed)
- [arXiv 2602.12241 — Moonshine v2](https://arxiv.org/abs/2602.12241) (search-indexed)
- [GitHub: regstuff/whisper.cpp_windows](https://github.com/regstuff/whisper.cpp_windows) (search-indexed)
- [GitHub: ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp) (search-indexed)
- [pyannote.ai/blog/community-1](https://www.pyannote.ai/blog/community-1) (search-indexed)
- [GitHub: pyannote/pyannote-audio](https://github.com/pyannote/pyannote-audio) (search-indexed)
- [localclaw.io — Best Local TTS Models in 2026](https://localclaw.io/blog/local-tts-guide-2026) (search-indexed)
- [localaimaster.com — Kokoro TTS Local Setup](https://localaimaster.com/blog/kokoro-tts-local-setup) (search-indexed)
- [contracollective.com — Kokoro vs Piper vs XTTS v2](https://contracollective.com/blog/kokoro-vs-piper-vs-xtts-local-text-to-speech-m5-max-2026) (search-indexed)
- [qwenlm.github.io/blog/qwen3-embedding](https://qwenlm.github.io/blog/qwen3-embedding/) (search-indexed)
- [Hugging Face: Qwen/Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) (search-indexed)
- [Hugging Face: FremyCompany/BioLORD-2023](https://huggingface.co/FremyCompany/BioLORD-2023) (search-indexed)
- [GitHub: abhinand5/MedEmbed](https://github.com/abhinand5/MedEmbed) (search-indexed)

### Repo evidence (read directly, not searched)

- `docs/research/2026-09-08/00-brief.md`
- `src/backend/modules/model_selector.py` (full `TIER_MODEL_CONFIG`)
- `docs/model_tiers/README.md`, `tier1_low.md`, `tier2_mid.md`, `tier3_high.md`
- `docs/plans/2026-03-04-gam-voice-ingest-implementation.md` (Tasks 10–13, MED-VOICE-001)
- `docs/plans/2026-03-04-prd-voice-gamification-ingest-design.md` (§1 Voice Logging)
- `src/backend/modules/embeddings.py`, `src/backend/core/config.py:89`, `src/backend/modules/rag.py:168`, `src/backend/api/documents.py:850`
- `src/backend/tests/test_rag_pipeline.py` (`test_api_rag_index_002b`)
