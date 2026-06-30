# Tech Upgrade Survey: 9 Component Areas

**Date:** 2026-06-30
**Status:** Research complete — awaiting implementation planning (no code changed)
**Context:** A full-repo exploration pass (3 parallel Explore agents) mapped HealthCentral's current architecture and feature set. A follow-up research pass (9 parallel research agents, each with WebSearch/WebFetch + read-only repo access) then surveyed open-source repos and recent papers (2024–2026) for technologies that could upgrade specific components. This document is the persisted, full-detail record of that survey, intended to be read by a higher-reasoning agent that will turn selected recommendations into an implementation plan. **No code was changed to produce this document.** A branch-history check (see "Overlap Check" below) confirmed none of these specific recommendations are already implemented elsewhere in the repo.

---

## Table of Contents

1. [Repo State Summary (from exploration phase)](#1-repo-state-summary-from-exploration-phase)
2. [Overlap Check — Related Work Already on `main`](#2-overlap-check--related-work-already-on-main)
3. [Priority Summary](#3-priority-summary)
4. [Area 1: Faithfulness / Entailment Scoring](#area-1-faithfulness--entailment-scoring)
5. [Area 2: Retrieval / Vector Indexing](#area-2-retrieval--vector-indexing)
6. [Area 3: PHI/PII Redaction](#area-3-phipii-redaction)
7. [Area 4: Document Extraction & OCR](#area-4-document-extraction--ocr)
8. [Area 5: Agent Orchestration Pattern](#area-5-agent-orchestration-pattern)
9. [Area 6: Frontend Stack](#area-6-frontend-stack)
10. [Area 7: Notifications & Background Scheduling](#area-7-notifications--background-scheduling)
11. [Area 8: Auth & Encryption](#area-8-auth--encryption)
12. [Area 9: Gamification & Analytics](#area-9-gamification--analytics)
13. [Notes for the Implementation-Planning Agent](#13-notes-for-the-implementation-planning-agent)

---

## 1. Repo State Summary (from exploration phase)

**Backend**: FastAPI + SQLAlchemy 2.0 + dual-chain Alembic (`migrations/master/`, `migrations/profile/`) + SQLCipher per-profile encrypted DBs, Python 3.10/3.11 compatible.

**LLM pipeline**: `modules/chunking.py` (200-token chunks, 50-token overlap, sentence-boundary aware) → `modules/embeddings.py` (sentence-transformers `all-MiniLM-L6-v2`, 384-dim; falls back to SHA256 hash-based deterministic embeddings when the real model is unavailable) → `modules/rag.py` (prompt composition enforcing citation tags `[YOUR_RESULTS:N]` / `[REFERENCE:N]` / `[KB:N]` / `[INT:N]`) → `modules/interpret.py` (template mode default — hardcoded clinical templates with inline citations; LLM mode via tiered `model_selector.py`) → safety/faithfulness verification → `modules/redaction.py` before any export.

**Model tiers** (`modules/model_selector.py`): High tier BioMistral-7B (32GB+ RAM), Mid tier Phi-3-mini (16GB+), Low tier Qwen2.5-0.5B (8GB+), Template-only fallback (zero RAM, all hardware). Ollama default model: `gemma4:12b` (+ edge variants `e2b`/`e4b`).

**Provider abstraction** (`core/llm/`): exactly 4 files — `provider.py` (`ProviderProtocol`, `CapabilityFlags`, `ChatMessage`), `factory.py` (`get_provider()` reads `LLM_PROVIDER`/`LLM_MODEL` env, `reset_provider()`), `ollama_provider.py` (localhost-only), `llama_cpp_provider.py` (local GGUF). `core/model_runner.py`'s `ModelRunner` is the facade all callers use. **New providers belong only in `core/llm/` — no new abstraction layers elsewhere (CLAUDE.md hard rule).**

**Safety/trust modules** (CLAUDE.md: ask before touching):
- `modules/interpret_safety.py` — regex-based prohibited-pattern detection (no diagnosis, no dosing), disclaimer enforcement, citation validation.
- `modules/redaction.py` — deterministic regex PHI/PII redaction (SSN, email, phone, DOB, address, name-context), policy levels strict/standard/minimal, immutable `RedactionResult` objects, metadata-only logging (plaintext never logged).
- `modules/faithfulness.py` — `FaithfulnessScorer`: 50% entailment (rule-based pseudo-entailment via entity/value matching, real NLI only used if `entailment_scores` is explicitly passed in — confirmed no production caller does this) + 30% lexical n-gram Jaccard overlap + 20% semantic (embedding cosine if available, else lexical-estimated). `consistency_score` is hardcoded to `1.0` — a dormant placeholder.
- `modules/verifier_agent.py` — `VerifierAgent`: rule-based entailment via regex contradiction pairs (high/low, elevated/normal), negation detection, 5%-tolerance numeric value matching, Jaccard lexical overlap. `use_llm_entailment` config flag exists but routes to `_check_entailment_llm`, which just calls `_check_entailment_rules` — **unimplemented in practice**.

**Document extraction**: `modules/extract.py` (pdfplumber `extract_tables()` + regex line-pattern fallback), `extract_pathology.py`, `extract_imaging.py`, `extract_visit_notes.py` (type-specific extraction), OCR via pdf2image + pytesseract gated behind `settings.ocr_enabled` + per-user toggle (confidence capped/penalized vs. text-layer extraction). `modules/document_classifier.py` — pure keyword/regex scoring across 4 categories (imaging, pathology, visit_notes, lab), hard 0.7 confidence threshold, `classified_by: "rule"` hardcoded — no ML.

**Agent orchestration** (`modules/agent/`): **Confirmed NOT LangGraph** — `graph.py`'s own docstring states it is "a small hand-rolled state machine — NO LangGraph dependency unless the client explicitly approves it (local-first footprint stays clean)." No `langgraph`/`langchain` import anywhere in the package or in `requirements.txt`/`pyproject.toml`. Real implementation: a single bounded `for` loop in `run_agent()` (~308 LOC in `graph.py`) calling four plain async node functions (`plan`, `act`, `reflect`, `draft`), plain Pydantic state (`state.py`), hard `MAX_STEPS=5` budget, deterministic `replay()` from logged steps. `guardrails/` subpackage (`guard.py`, `classifier.py`, `groundedness.py`, `redaction_gate.py`, `templates.py`) wires advice → groundedness → confidence → audit gating. Total package ~2,662 LOC. **This corrects an earlier (incorrect) exploration-phase finding that described this as LangGraph-based.**

**Frontend**: React 18.2.0 + TypeScript 5.3.3 + Vite 7.3.0 + Tailwind 3.4.1 + Radix UI + Recharts 2.10.3 + Zustand 4.4.7 + TanStack Query 5.17.0 + Framer Motion 10.18.0. 12 pages (`TrendsDashboard`, `LabInterpreter`, `ExplainAssistant`, `DocumentInbox`, `MedicationCoach`, etc.), 16 service modules. 65 backend pytest files, 14 frontend vitest files, 5 Playwright e2e specs.

**Notifications**: `modules/notification_scheduler.py` is a **hand-rolled `asyncio` polling loop** (`while ... await asyncio.sleep(60)`) — **`apscheduler` is declared in `requirements.txt` but never imported anywhere in `src/backend`** (confirmed via grep — a dead/unused dependency). `modules/platform_notifications.py` (not `notify.py` — that file does not exist; this was another exploration-phase naming error) implements `NotificationProvider` abstraction: `WindowsToastProvider` (native `winsdk`) tried first, falls back to `PlyerProvider` (cross-platform via `plyer`), `MockProvider` for tests.

**Auth/security**: `src/backend/core/security.py` — JWT via `python-jose` (HS256, `TokenRevocationList`), password hashing via `bcrypt`. `src/backend/security/` — `input_validator.py`, `rate_limit_middleware.py`, `security_headers.py`, `audit_middleware.py` (structured JSON logging, optional DB persistence, **no integrity/tamper-evidence protection on the log itself**), `sqlcipher_driver.py`. `requirements.txt`: `cryptography>=42.0.0`, `python-jose[cryptography]>=3.3.0`, `bcrypt>=4.1.2`.

**Gamification/analytics**: `modules/badge_evaluator.py` (~165 LOC, dict-based `BADGE_DEFS` registry), `modules/streak_engine.py` (~80 LOC, pure-function calendar-date streak/gap math, timezone-aware via `zoneinfo`), `modules/analytics.py` (~270 LOC, deterministic trend/delta/rolling-average/abnormal-flag logic) — all bespoke, dependency-free, no external libraries.

---

## 2. Overlap Check — Related Work Already on `main`

Before persisting this survey, all branches and full commit history were searched for work matching any of the 9 areas' specific recommended technologies (NLI/entailment models, sqlite-vec, Recharts upgrade, PyJWT, argon2, desktop-notifier, LangGraph, Presidio, Philter, docTR, PaddleOCR). **No genuine duplicate work was found** — none of these specific technologies appear anywhere in branch history. Three adjacent-but-distinct commits exist on `main` and are noted here so they aren't mistaken for already-done versions of these recommendations:

1. **`43f7a4b`** — `feat(agent-overhaul): S4 — PHI redaction gate + offline test + golden set to ~30` — touches `modules/agent/guardrails/redaction_gate.py`, `modules/agent/nodes/plan.py`, plus 27 test golden files. This adds a redaction **gate** around the agent pipeline (i.e., enforcement/wiring), but does **not** change the underlying detection logic in `modules/redaction.py`, which remains regex-only. **Area 3's core recommendation (NER-based augmentation) is still open.**
2. **`4eab43c`** — `security: enforce strict external LLM redaction (F-001/F-002)` — touches `core/config.py`, `modules/external_runner.py`, `tests/test_redaction.py`. Tightens **enforcement** of redaction before external calls; same relationship as above — doesn't touch the regex-only detection gap.
3. **`0a9af5b`** — `fix: eliminate OCR double-processing, fix false-positive tests, add missing API error paths` — touches `api/documents.py`, `modules/extract.py`. A **bug fix** in the existing pdfplumber/pytesseract pipeline, not a new OCR model adoption. **Area 4's recommendation (held as "no change justified" anyway) is unaffected.**

---

## 3. Priority Summary

**If you only fund one: Area 1 (Faithfulness/Entailment)** — the only safety-critical module confirmed running in 100% rule-based fallback in production today, with dormant hooks already built for exactly this fix.

| Tier | Areas | Verdict |
|---|---|---|
| 🔴 Safety-critical | 1 (Faithfulness/Entailment), 3 (Redaction), 8 (Auth/Encryption) | Prototype recommended; **requires explicit human sign-off before code changes** per CLAUDE.md |
| 🟡 Confirmed unfinished feature | 2 (Retrieval/Vector Indexing) | No change justified at current scale; cleanup of dead config recommended |
| 🟢 Moderate value | 4 (OCR/Extraction), 6 (Frontend), 7 (Notifications) | Mixed: one clear win (Recharts v3), others are "prototype if/when needed" |
| ⚪ Sanity-check, no gap found | 5 (Agent Orchestration), 9 (Gamification/Analytics) | No change justified |

---

## Area 1: Faithfulness / Entailment Scoring

### Current State
`src/backend/modules/faithfulness.py` computes `overall_score` as 50% entailment + 30% lexical n-gram Jaccard + 20% semantic, but `entailment_score` only uses real NLI when an external `entailment_scores` list is passed in (`score_claim`, line 117) — otherwise it falls back to `_calculate_pseudo_entailment` (regex value/entity matching, line 191). A grep of callers (`api/interpretations.py`, `modules/agent/guardrails/guard.py`, `modules/rag.py`) found **no caller passing `entailment_scores` or `embedding_similarity`** — in production this gate runs in 100% rule-based/lexical mode today. `consistency_score` is hardcoded to `1.0` (line 134), a dormant no-op. `verifier_agent.py`'s `use_llm_entailment` flag (line 88) routes to `_check_entailment_llm`, which simply calls `_check_entailment_rules` (line 321) — it is unimplemented. Both modules rely on regex contradiction pairs, negation lists, and 5%-tolerance numeric matching — no actual NLI inference exists anywhere in the safety gate today. `sentence-transformers>=2.2.0` is already a backend dependency (`requirements.txt:53`), so embedding infra exists but isn't wired to faithfulness scoring either.

### Candidates Considered

| Name | License | Size/RAM footprint | Maturity/recency | Fit notes |
|---|---|---|---|---|
| cross-encoder/nli-deberta-v3-xsmall | MIT (DeBERTa-v3 base, MIT) | 22M backbone params (~70-90MB incl. embeddings), <500MB RAM at inference | Mature, widely used since 2021, 91.6% SNLI / 87.8% MNLI-mm accuracy | True 3-way NLI (entailment/neutral/contradiction) cross-encoder; loads via `sentence-transformers` CrossEncoder API (already a dependency); CPU inference fast for short claim/source pairs. Fits low tier (8GB) easily. |
| cross-encoder/nli-deberta-v3-small / -base | MIT | Small: ~140MB; Base: ~370MB | Same family, same maturity | Better accuracy than xsmall, still CPU-viable; reasonable mid/high-tier upgrade path. |
| LettuceDetect (KRLabsOrg, ModernBERT-based) | MIT | Base 150M (~600MB fp32, less @ int8); Large 396M (~1.6GB); TinyLettuce/Ettin variants 17M/32M/68M (well under 200MB) | Very recent (arXiv 2502.17125, Feb 2025); F1 79.2% on RAGTruth, beats GPT-4-turbo-as-judge (63.4%) and prior encoder SOTA (Luna, 65.4%) | Purpose-built for RAG faithfulness/hallucination span detection (token-level, not just sentence-level), exactly this use case. TinyLettuce variants give a true zero/near-zero-RAM tier option. Newer, smaller maintainer community than DeBERTa-v3 NLI models — watch for maintenance risk. |
| MedNLI-tuned clinical NLI models | Varies (research artifacts, often no clear redistribution license) | Unverified | Academic dataset/benchmark, not a turnkey redistributable model | No off-the-shelf MIT/Apache clinical-domain NLI checkpoint surfaced in search; MedNLI is a *dataset* for fine-tuning, not a ready model. Would require an in-house fine-tune — future option only, not "adopt now." |
| LLM-as-judge (via existing ModelRunner/Ollama) | N/A (reuses existing local model) | Reuses whatever local LLM is already loaded (1-8GB+) | Common pattern but explicitly the alternative this survey is trying to avoid for a fast gate | Slower, less deterministic, harder to unit-test as a hard safety floor; better reserved as an optional high-tier secondary opinion, not the primary entailment signal. |

### Recommendation
**Prototype `cross-encoder/nli-deberta-v3-xsmall` first**, as an additive secondary signal — not a replacement. Wire its 3-way entailment/contradiction/neutral output into `verifier_agent._check_entailment` as a new code path (e.g., make `use_llm_entailment` actually do something, or add a parallel `use_nli_model` flag) and into `faithfulness.score_claim` by populating the existing-but-unused `entailment_scores` parameter. Keep current regex/lexical checks running unconditionally as the fast, dependency-free safety floor (per CLAUDE.md's "conservative over clever" rule) — the NLI model becomes a confirmation/tightening pass, especially valuable for catching contradictions (high/low flips) the regex list doesn't anticipate. Follow-up: LettuceDetect is worth a second prototype specifically for its token-span localization (showing *which phrase* is unsupported is more actionable for a patient-facing UI than a single score) and its TinyLettuce variants for the zero-RAM tier — but it's newer/less battle-tested, so xsmall-DeBERTa is the safer first step.

### Risks
- **Safety**: An NLI model can itself misclassify (especially on numeric/clinical claims, underrepresented in generic MNLI/SNLI training) — must not let a "neutral/entailment" verdict override a rule-based contradiction; combine via AND/floor logic, not replacement; validate on a held-out set of synthetic lab-result claims before trusting it as a gate input.
- **Perf**: Cross-encoder inference adds latency per claim-source pair (sub-100ms on CPU for short text, but scales with number of cited sources per response) — needs benchmarking on low-tier (8GB) hardware.
- **License**: All shortlisted candidates (DeBERTa-v3 family, LettuceDetect/ModernBERT) are MIT — no GPL/AGPL/non-commercial blockers found.
- **Maintenance**: LettuceDetect is a small-team OSS project (KRLabsOrg), higher abandonment risk than Microsoft-backed DeBERTa-v3; `cross-encoder/nli-deberta-v3-xsmall` has years of stable usage and many derivative checkpoints.
- **No clinical-domain validation**: none of the shortlisted models are fine-tuned/validated specifically on clinical text or medical QA faithfulness benchmarks — genuine gap, mitigated by keeping rule-based checks (which encode domain-specific patterns like "elevated/normal") as the non-negotiable floor.

### Effort Estimate
**M** — new dependency wiring inside `core/llm/` is not required (this is a classifier, not a generative provider), but it does need a small new loader path (likely alongside existing `sentence-transformers` usage), a benchmark/validation pass on synthetic clinical claims, and careful integration into two safety-critical files that require explicit sign-off per CLAUDE.md.

### Sources
- https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall
- https://huggingface.co/MoritzLaurer/DeBERTa-v3-xsmall-mnli-fever-anli-ling-binary
- https://huggingface.co/microsoft/deberta-v3-xsmall
- https://arxiv.org/abs/2502.17125 (LettuceDetect paper)
- https://github.com/KRLabsOrg/LettuceDetect
- https://towardsdatascience.com/lettucedetect-a-hallucination-detection-framework-for-rag-applications/
- https://huggingface.co/KRLabsOrg/lettucedect-base-modernbert-en-v1
- https://github.com/EdinburghNLP/awesome-hallucination-detection

---

## Area 2: Retrieval / Vector Indexing

### Current State
Retrieval in `src/backend/modules/rag.py` (~line 567-590) is a literal linear scan: for every `(chunk, embedding, document)` row returned from the per-profile DB query, it unpacks the stored blob (`embeddings.py:232 blob_to_vector`), computes `cosine_similarity` (`embeddings.py:245`) in pure Python, appends to a list, then sorts and slices to `top_k` (default 10, `rag.py:196`). **No index structure exists.** `core/config.py:108` declares `vector_store_type: Literal["sqlite-vss", "faiss"] = "sqlite-vss"` but this field is **never read** in `rag.py` or `embeddings.py` — confirmed dead. `requirements.txt:67` lists `faiss-cpu>=1.7.4` but `faiss` is never imported anywhere in `src/backend` (confirmed via grep). Embeddings use `sentence-transformers` `all-MiniLM-L6-v2` (384-dim, 23M params), with a SHA256 hash-based bag-of-words fallback (`embeddings.py:138-218`) when the real model isn't installed — a deliberate, test-friendly, offline design choice.

### Candidates Considered

| Name | License | Size/RAM footprint | Maturity/recency | Fit notes |
|---|---|---|---|---|
| sqlite-vss | MIT (built on Faiss/C++) | Moderate; loads Faiss C++ | **Unmaintained** — author abandoned it due to build/integration pain | Currently declared in config but dead code; do not finish wiring this up |
| sqlite-vec | MIT | Tiny, pure C, no Faiss dep | Actively maintained (Mozilla-backed), brute-force by design | Best-in-class for embedding directly into SQLite if an index were ever justified; clean C reimplementation, portable to mobile/WASM |
| faiss-cpu | MIT | ~tens of MB; IndexFlat is just brute force matrix math | Mature, Meta-maintained | Already a dependency but unused; `IndexFlatIP` would just reimplement the existing linear scan with a faster inner loop — marginal win at this corpus size |
| usearch | Apache-2.0 | Very small, single-header C++ | Active | Good for true ANN if corpus ever scaled; unnecessary complexity now |
| hnswlib | Apache-2.0 | Small, in-memory only | Mature, widely used (backs Chroma) | In-memory index means rebuild-per-session overhead for tens-of-chunks corpora — not worth it |
| chromadb (embedded) | Apache-2.0 | Heavier (full client/server-capable stack, extra deps) | Active | Overkill — pulls in a much larger dependency surface for a feature this small |
| lancedb | Apache-2.0 | Rust-backed, disk columnar format, moderate footprint | Active | Designed for larger/growing corpora with disk persistence; unnecessary weight here |
| BAAI/bge-small-en-v1.5 (alt. embedding model) | MIT | 33M params, 384-dim (drop-in dimension compatibility with current model) | Active | Scores modestly higher on MTEB retrieval than `all-MiniLM-L6-v2`; same license/size class, worth a low-cost eval |
| e5-small (alt. embedding model) | MIT | 118M params | Active | Exceeds the <100M ceiling for an 8GB-tier target; ~5x current model size for incremental gain — not justified |

### Recommendation
**No change justified at this corpus scale.** Per-patient retrieval is tens to low-hundreds of chunks (`top_k=10` default), and benchmarks consistently show brute-force linear scan is competitive with or faster than ANN indexing up to roughly 100k vectors when data fits in memory — several orders of magnitude above this app's actual per-patient ceiling. The existing pure-Python loop is simple, correct, easy to audit for a safety-critical app, and has no index-staleness/rebuild concerns.

Do **not** finish wiring `sqlite-vss`: it's unmaintained upstream and the config field should either be removed or, if kept for future-proofing, repointed at `sqlite-vec` as the only viable embedded-SQLite option (still not needed today). If patient corpora ever grow into the thousands of chunks (e.g., multi-decade records, imaging reports at scale), revisit with `sqlite-vec` (lightweight, MIT, actively maintained, no new heavy dependency) as the first prototype, since `faiss-cpu` is already a dependency but unused and could serve as a fallback `IndexFlatIP` if pure-Python latency ever becomes the bottleneck — that's a profiling question, not an architecture one.

On embeddings: `all-MiniLM-L6-v2` (23M params, MIT) remains a reasonable, well-tested default for offline use. `BAAI/bge-small-en-v1.5` (33M params, MIT, same 384-dim) scores modestly higher on MTEB retrieval and is worth a low-cost prototype/eval against real lab-report chunks before committing, since it's same-license and same-size class.

### Risks
- **Safety/correctness**: none from current approach — exact search guarantees no recall loss, important for citation-grounded medical text.
- **Maintenance**: dead `vector_store_type` config is a minor footgun — a future engineer could "finish" wiring sqlite-vss into an unmaintained library. Worth flagging for cleanup/removal even though out of scope here.
- **License**: all viable candidates (sqlite-vec, faiss-cpu, usearch, hnswlib, chromadb, lancedb, bge-small) are MIT/Apache-2.0 — no GPL/AGPL exposure found.
- **Perf**: low-RAM (8GB) tier should be re-checked if `top_k`/corpus size grows substantially or chunk text gets long, but no current evidence of a bottleneck.

### Effort Estimate
**S** (if/when corpus growth ever justifies a prototype: sqlite-vec swap-in is S-M; embedding model swap is S, mostly re-embedding existing chunks + eval).

### Sources
- https://marcobambini.substack.com/p/the-state-of-vector-search-in-sqlite
- https://github.com/asg017/sqlite-vec
- https://github.com/asg017/sqlite-vss
- https://github.com/asg017/sqlite-vec/issues/94
- https://huggingface.co/BAAI/bge-small-en-v1.5
- https://innovativeais.com/blog/best-embedding-models-for-rag-in-2026
- https://zilliz.com/comparison/chroma-vs-lancedb

---

## Area 3: PHI/PII Redaction

### Current State
`src/backend/modules/redaction.py` implements `RedactionEngine`, a stateless, deterministic regex engine over a fixed `_RULES` tuple (SSN, email, phone, `name_context`, DOB, address), gated by policy level (`strict`/`standard`/`minimal`, see `VALID_POLICY_LEVELS`). Output is an immutable `RedactionResult` (text + count + position-only metadata; plaintext never logged, per the dataclass docstring). The `name_context` rule (lines 81-89) only catches capitalized two-word names preceded by a label like "Patient:"/"Dr."/"Mr." — it cannot catch a name mentioned in free-running prose without that trigger phrase, nicknames, non-Western name orders, or PHI in malformed/unusual formats. **Related work already on `main`** (see [Section 2](#2-overlap-check--related-work-already-on-main)): commits `43f7a4b` and `4eab43c` add a redaction *gate* around the agent pipeline and strict enforcement before external LLM calls, respectively — both wire/enforce the existing regex engine more tightly but do not change its detection logic. The gap below is the actual target.

### Candidates Considered

| Name | License | Size/RAM footprint | Maturity/recency | Fit notes |
|---|---|---|---|---|
| **Microsoft Presidio** (analyzer + anonymizer) | MIT (core) | Core lib small; needs a spaCy model. `en_core_web_lg` ≈741MB disk (MIT); transformer option `en_core_web_trf` ≈438MB disk but heavier at inference. CPU-only, no GPU required. | Active, 8.8k+ stars, releases into 2026 (v2.2.x) | Fully offline once spaCy model is downloaded/bundled at build time (no runtime network call). General-purpose PII, not clinical-trained — recognizers tuned for finance/general PII, would need a custom recognizer for clinical name/MRN contexts. |
| **Philter** (UCSF, BSD-3) / **philter-lite** (SironaMedical fork) | BSD-3-Clause | Pure Python + regex + statistical components; no large neural model bundled — lightest of the ML-aware options | Published/validated (npj Digital Medicine 2020; JAMIA Open certification 2023); philter-lite is a maintained production fork | Purpose-built for clinical free text. Reported 99.46% recall on UCSF notes, 99.92% recall on i2b2 2014 (vs. 87.8% for NLM Scrubber) — directly relevant to the false-negative bias this app needs. Permissive license, modest footprint, designed exactly for this problem. |
| **obi/deid_roberta_i2b2** (HuggingFace) | MIT | roberta-large backbone, 355M params, ~1.3GB on disk; PyTorch CPU inference plausible but noticeably heavier than the above at low-end tiers | Trained on i2b2 2014 deid corpus; widely cited but community-maintained, not a vendor product | Best raw recall potential for contextual names/dates in clinical narrative, but heaviest dependency (PyTorch + transformers + checkpoint), worst fit for 8GB tier without careful quantization/lazy-loading. |

General finding (no single rigorous 2024-2026 head-to-head regex-vs-NER false-negative benchmark was found): multiple 2025 sources converge that hybrid regex+NER/statistical approaches outperform regex-only on recall, and that NER-based systems trade some false positives (over-redaction) for fewer false negatives — consistent with this app's stated bias toward over-redaction over under-redaction.

### Recommendation
**Prototype Philter / philter-lite first**, as an *additive* second pass layered after the existing `RedactionEngine.redact()` output — **never replacing the deterministic regex floor.** Philter is purpose-built for clinical text, BSD-3 licensed, has published recall numbers directly addressing the false-negative concern, and has the lightest footprint of the ML-aware candidates, making it the most plausible fit across all three hardware tiers (likely fine at 8GB; needs validation). Presidio is a reasonable second prototype target if Philter's accuracy on this app's note styles disappoints, but its spaCy model adds real footprint and its recognizers aren't clinical-tuned out of the box. The transformer NER model (`obi/deid_roberta_i2b2`) should be deferred — flag for mid/high tier (16GB+) only, not recommended as a default given footprint risk at 8GB.

### Risks
- **Safety**: any ML layer introduces false negatives of its own (model blind spots) and must never be allowed to *remove* coverage the regex floor already provides — needs to run as an additive union of redactions, not a replacement.
- **Perf**: spaCy/transformer model load time and per-document inference cost on 8GB devices is unvalidated; needs empirical profiling before any adoption decision.
- **License**: all three candidates clear redistribution (MIT/MIT/BSD-3); spaCy models used by Presidio are also MIT — no GPL/AGPL exposure found.
- **Maintenance**: philter-lite and obi models are community-maintained forks/cards, not vendor-backed — ongoing support risk should be weighed against Presidio's larger maintainer base.
- **False-negative/positive tradeoff**: literature consistently shows ML layers reduce false negatives at the cost of more false positives (over-redaction) — acceptable per this app's stated bias, but will need product-level UX handling for the increased redaction noise.

### Effort Estimate
**M** (prototype + offline benchmarking on representative synthetic clinical text across hardware tiers, before any integration decision).

### Sources
- https://github.com/microsoft/presidio
- https://github.com/microsoft/presidio/blob/main/docs/installation.md
- https://microsoft.github.io/presidio/faq/
- https://github.com/BCHSI/philter-ucsf
- https://github.com/SironaMedical/philter-lite
- https://www.nature.com/articles/s41746-020-0258-y (Philter npj Digital Medicine 2020)
- https://pmc.ncbi.nlm.nih.gov/articles/PMC10320112/ (Philter JAMIA Open 2023 certification)
- https://huggingface.co/obi/deid_roberta_i2b2
- https://spacy.io/models/en
- https://intuitionlabs.ai/articles/open-source-phi-de-identification-tools
- https://censinet.com/perspectives/2025-benchmark-de-identification-tools
- https://arxiv.org/pdf/2204.07056 (Comparative Evaluation of Transformer Models for De-Identification)

---

## Area 4: Document Extraction & OCR

### Current State
`modules/extract.py` uses pdfplumber for text-layer PDFs with `extract_tables()` (header-keyword column matching) plus two regex line-patterns as a fallback for tableless text. OCR (`extract_from_scanned_pdf`/`extract_from_image`) uses pdf2image + pytesseract, gated by `is_ocr_available()` (requires Tesseract binary + `settings.ocr_enabled`) and a per-user `ocr_preference_enabled` toggle, defaulting OCR-derived confidence to 0.4–0.7 (capped, ×0.8 penalty) vs. text-extraction's 0.5+ baseline. `document_classifier.py` is pure regex/keyword scoring across 4 categories (imaging, pathology, visit_notes, lab) over the first two pages, with a hard 0.7 confidence threshold and no ML at all — `classified_by: "rule"` is hardcoded. **Related work already on `main`**: commit `0a9af5b` fixed OCR double-processing and false-positive test bugs in this existing pipeline — a maintenance fix, not a model/library change; does not overlap with the recommendation below.

### Candidates Considered

| Name | License | Size/RAM footprint | Maturity/recency | Fit notes |
|---|---|---|---|---|
| PaddleOCR / PP-StructureV3 | Apache-2.0 (code + weights) | Lightweight configs available for CPU; ~3.7s/image on server CPU (Intel 8350C), smaller PP-OCRv3/v4 mobile models much lighter | Mature, very active (2026 v3 tech report) | Best license fit; strong table-structure recognition for scanned lab tables; CPU-viable at mid/low tiers with lightweight model variants; large added dependency (PaddlePaddle) |
| docTR (Mindee) | MIT | Two-stage detector+recognizer; ONNX/int8 variant (OnnxTR) for fast CPU inference | Mature, actively maintained | Best license simplicity (pure MIT); good CPU story via OnnxTR; weaker table-structure recognition than PP-StructureV3 — would still need pdfplumber-style table logic |
| Surya (datalab-to) | Code Apache-2.0; **model weights under modified OpenRAIL-M** (free for research/personal/startups <$5M, paid for broader commercial use) | Surya 2 is a single 650M-param model; CPU-only feasible but 10–50x slower than GPU | Very active, modern (table/layout/reading-order in one model) | License is a blocker for unrestricted redistribution — must verify revenue threshold before any adoption; otherwise strong accuracy |
| LayoutLMv3(-base) | **CC BY-NC-SA 4.0 (non-commercial)** | 133M params; ~6.1s/page CPU, 0.2 pages/sec | Mature but stagnant; no maintained small/distilled variant found | License alone disqualifies for a redistributed patient app |
| Donut | MIT | Swin-encoder + BART-decoder; no OCR engine needed | Mature (ECCV 2022), maintenance slowed | License-clean but architecturally a poor fit: generative seq2seq extractor tuned per-document-type via fine-tuning, not a generic table/layout extractor — high effort to adapt to 4 heterogeneous report types, and hallucination risk is a real concern for a faithfulness-constrained app |
| DistilBERT (generic) for classifier | Apache-2.0/MIT (varies) | ~66M params, 40% smaller / 60% faster than BERT, CPU-friendly | Mature, ubiquitous | Plausible classifier upgrade path, but no medical-document-specific checkpoint found; would need labeled training data the team doesn't appear to have |

### Recommendation
**No change to extraction; no change to classifier.** For clean text-layer lab PDFs, pdfplumber's `extract_tables()` is already structurally adequate — the gap in `extract.py` is in regex robustness (header synonyms, multi-line cells), not in lacking a layout model. For the OCR path specifically, **prototype docTR (MIT) or PaddleOCR's lightweight CPU config** as a pytesseract replacement/supplement *only if* real-world scanned-document accuracy is measured and found wanting — this hasn't been demonstrated, only assumed. For `document_classifier.py`: 4 well-separated categories with strong keyword anchors ("FINDINGS/IMPRESSION", "biopsy/histologic", "chief complaint", "CBC/mg/dL") is a textbook case where rule-based classification is "good enough"; no labeled training corpus exists to fine-tune a classifier, and the failure mode of rules (returns "unknown" below 0.7) is already safe-by-default.

If document understanding is revisited later, **docTR or PaddleOCR (lightweight) are the only candidates clearing both the license and CPU-at-mid-tier bars** simultaneously; Surya's model-weight license and LayoutLMv3's NC license are blockers as currently written, and Donut is a poor architectural fit for this app's table/provenance/faithfulness requirements.

### Risks
License: Surya weights and LayoutLMv3 are redistribution blockers, not just attribution footnotes — must not silently slip in via a dependency. Perf: any of these models add 100MB+ RAM and meaningfully slower per-page latency on the 8GB tier; must stay opt-in/gated like current OCR flag, never default-on. Safety: a generative/seq2seq extractor (Donut-style) risks fabricating values, conflicting with `faithfulness.py`'s grounding guarantees — any such candidate needs explicit verifier-agent review, not silent adoption. Maintenance: adding PaddlePaddle or a transformer stack significantly grows the dependency surface for an app that currently has a thin OCR boundary.

### Effort Estimate
**S** (no immediate code change) for the recommendation as stated; **M** if docTR/PaddleOCR prototyping is greenlit later.

### Sources
- https://github.com/datalab-to/surya
- https://www.solosoft.dev/post/surya-ocr-2026/
- https://github.com/PADDLEPADDLE/PADDLEOCR
- http://www.paddleocr.ai/main/en/version3.x/algorithm/PP-StructureV3/PP-StructureV3.html
- https://arxiv.org/html/2507.05595v1 (PaddleOCR 3.0 Technical Report)
- https://deepwiki.com/PaddlePaddle/PaddleOCR/7.3-cpu-optimization
- https://huggingface.co/docs/transformers/model_doc/layoutlmv3
- https://huggingface.co/microsoft/layoutlmv3-base
- https://github.com/clovaai/donut
- https://github.com/mindee/doctr
- https://github.com/felixdittrich92/OnnxTR
- https://intuitionlabs.ai/articles/non-llm-ocr-technologies
- https://www.kdnuggets.com/distilbert-resource-efficient-natural-language-processing

---

## Area 5: Agent Orchestration Pattern

### Current State
`modules/agent/` is **not** LangGraph-based — `graph.py`'s own docstring states: *"A small hand-rolled state machine — NO LangGraph dependency unless the client explicitly approves it (local-first footprint stays clean)."* Confirmed: no `langgraph`/`langchain` import anywhere in `modules/agent/` and no such dependency in `requirements.txt`/`pyproject.toml`. (This corrects the initial exploration-phase report, which mischaracterized this module as LangGraph-based.)

The real implementation is a single bounded `for` loop in `run_agent()` (`graph.py:144-227`, 308 LOC total) calling four plain async functions — `plan` (264 LOC), `act` (61 LOC), `reflect` (82 LOC), `draft` (147 LOC) — plus a `guardrails/` package (`guard.py` 218 LOC, `classifier.py`, `groundedness.py`, `redaction_gate.py`, `templates.py`, ~451 LOC total). State is a plain Pydantic `RunLog`/`RunStep` (`state.py`, 60 LOC), with a hard `MAX_STEPS=5` budget enforced both in `reflect` and as a defense-in-depth backstop in the loop itself. Deterministic `replay()` reconstructs any terminal from the logged steps with zero re-execution (`graph.py:235-308`) — pure-Python data replay, something LangGraph's checkpointer would have made heavier, not simpler, for this single-user case. Audit events, node timing, and guardrail gating (advice → groundedness → confidence → audit) are already wired in cleanly with no framework scaffolding.

### Candidates Considered

| Name | License | Size/RAM footprint | Maturity/recency | Fit notes |
|---|---|---|---|---|
| LangGraph (current 1.2.x, June 2026) | MIT | Adds langchain-core + langgraph-checkpoint deps; checkpointing/persistence layer is overhead for single-user local use | Reached 1.0 milestone, stable API, no breaking changes promised until 2.0 | Would add a dependency and indirection for distributed/multi-tenant features (checkpointers, threads, streaming v3) this app doesn't need — a net complexity *increase*, not decrease |
| pydantic-ai / pydantic-graph | MIT | Lighter than LangGraph but still a new dependency; typed FSM library | Actively developed, 2026-current | Closest conceptual match (typed nodes, Pydantic-native), but the codebase already gets typed nodes via plain Pydantic models — adopting it would replace working code with equivalent code wrapped in a new abstraction, for no LOC reduction |
| Hand-rolled (status quo) | N/A (in-house) | Zero extra deps | Already shipped, tested, replayable | Matches CLAUDE.md's "no abstractions for single-use code" directly |

### Recommendation
**No change justified.** The module already is the lightweight, dependency-free alternative that this research area was looking for — this isn't a LangGraph codebase that needs migrating away from a framework, and there is no smaller framework that would reduce its ~2,662 LOC without reintroducing a dependency the team explicitly chose to avoid. Re-litigating "LangGraph vs. lightweight" doesn't apply because that decision was already made and implemented correctly.

### Risks
None from inaction. Adopting any framework here would add a dependency surface (license/audit review, version pinning, supply-chain exposure) for a local-first, single-user app that doesn't need distributed checkpointing, multi-agent orchestration, or streaming — pure downside per CLAUDE.md's complexity bar.

### Effort Estimate
**S** (sanity-check only; no action required).

### Sources
- https://docs.langchain.com/oss/python/releases/changelog
- https://www.langchain.com/blog/langchain-langgraph-1dot0
- https://pydantic.dev/docs/ai/overview/
- https://pydantic.dev/docs/ai/guides/multi-agent-applications/

---

## Area 6: Frontend Stack

### Current State
From `src/frontend/package.json`: React 18.2, TypeScript 5.3.3, Vite 7.3, Tailwind 3.4.1, Radix UI (~1.0/2.0, individual packages), Recharts 2.10.3, Zustand 4.4.7, TanStack Query 5.17.0, Framer Motion 10.18.0. `TrendsDashboard.tsx` uses Recharts `LineChart`/`ReferenceLine` plus hand-rolled SVG→canvas PNG export logic. `ExplainAssistant.tsx` is a request/response chat (`useSendMessage` mutation, no token-level streaming) with inline citation objects (`{source, page, docId}`), session history restore, and a feedback UI — all hand-built, no chat component library. Services layer (`src/services/*.ts`) is a flat, per-domain TanStack Query hook pattern (`observations.ts`, `assistant.ts`, `feedback.ts`, etc.) — clean and worth preserving as-is.

### Candidates Considered

| Name | License | Size/footprint | Maturity/recency | Fit notes |
|---|---|---|---|---|
| React 19 | MIT | n/a (same lib) | Stable since late 2024; React Compiler 1.0 stable Oct 2025 | Real wins (automatic memoization, ref-as-prop, simpler Suspense) but `ReactDOM.render`/`hydrate`, PropTypes, `defaultProps` removed; JSX namespace moved (TS friction). Not urgent — 18.2 fully supported. |
| Tailwind v4 | MIT | smaller runtime, CSS-first config | Stable, widely adopted by 2026 | Config moves from `tailwind.config.js` to `@theme` CSS; utility renames (`flex-shrink-0`→`shrink-0` etc.); border-color default changes from gray-200→currentColor — would touch nearly every component file. High blast radius for a "looks fine" gain. |
| TanStack Query v5 (current minor) | MIT | — | Actively released (5.101.x as of search) | Already on v5; just a routine minor bump, no migration. |
| Zustand v5 | MIT | — | Stable | Drops React <18 support (irrelevant here), removes deprecated v4 APIs. Low-risk bump, no new capabilities needed for current store usage. |
| Recharts v3 | MIT | ~150kB | Released 2024, **v2 now unmaintained** (repo explicitly flags v2 EOL) | Rewritten state management, dropped `recharts-scale`/`react-smooth` deps, removed internal-state props, CartesianGrid axis-ID behavior changed. This is the one with a forcing function: v2 is unmaintained, so staying is itself a risk, not a neutral choice. |
| visx | MIT | ~15kB (modular) | Mature, Airbnb-maintained | Lowest-level toolkit, not a chart library — would mean rebuilding the existing LineChart/ReferenceLine/export logic from D3 primitives. 2-3x build time per chart. Wrong fit for a small team needing standard trend lines. |
| Nivo | MIT | 500kB+ full install | Mature, WCAG-conscious, Canvas option for 10k+ points | Overkill for lab panels (dozens of points, not 10k); bundle cost not justified. |
| Tremor | Apache-2.0 | ~200kB | Active, shadcn-style pre-styled dashboard charts | Closer to current Recharts wrapper aesthetic; not a clear enough win over upgrading Recharts in place to justify a swap. |
| assistant-ui | MIT | moderate (Radix-style headless primitives) | Active 2025-2026, designed around Vercel AI SDK's `useChat`/streaming | Solves streaming, citation rendering, markdown, accessibility out of the box — but assumes a Vercel AI SDK-shaped backend (SSE/stream protocol) which conflicts with the existing custom `useSendMessage` + local FastAPI/Ollama contract. Would mean adapting the backend response shape, not just the frontend. |
| Vercel AI SDK (`ai` package) | Apache-2.0 | — | 20M+ monthly downloads, Ollama community providers exist | Same caveat: built around its own provider/streaming abstraction; this repo's `core/llm/ModelRunner` facade is the equivalent layer already and per CLAUDE.md must not be duplicated or wrapped. |

### Recommendation
**No core framework change** (React 19, Tailwind v4) — insufficient payoff for the migration cost right now; revisit React 19 + Compiler opportunistically on a slower cycle. **Adopt Recharts v3** — v2 is unmaintained upstream, so this is risk-reduction, not speculative; budget time for the CartesianGrid axis-ID and prop-removal changes in `TrendsDashboard.tsx`'s custom export path. **Prototype streaming UI patterns from assistant-ui (read the source for patterns, not as a dependency)** for `ExplainAssistant`, since true token streaming (vs. current full-response mutation) is the one concrete UX gap found — but don't adopt assistant-ui/Vercel AI SDK wholesale, since their streaming protocol assumes a server shape this local-first FastAPI backend doesn't have.

### Risks
Recharts v3: API surface changes ripple through `TrendsDashboard.tsx` and `MedicationOverlay`. Tailwind v4: near-universal file touch for marginal gain — main risk is scope creep, not technical failure. Streaming chat: backend (`assistant.py`/`ModelRunner`) would need an SSE/chunked response path — that's a backend change, not just frontend, and out of this area's scope.

### Effort Estimate
Recharts v2→v3: **S-M**. Streaming chat prototype: **M** (frontend) + backend dependency. Tailwind/React major bumps: **L**, not recommended now.

### Sources
- https://react.dev/blog/2024/04/25/react-19-upgrade-guide
- https://react.dev/blog/2025/10/07/react-compiler-1
- https://tailwindcss.com/docs/upgrade-guide
- https://github.com/recharts/recharts/wiki/3.0-migration-guide
- https://github.com/recharts/recharts/issues/7361 (Recharts v2 EOL)
- https://www.pkgpulse.com/guides/recharts-v3-vs-tremor-vs-nivo-react-charting-2026
- https://www.kylegill.com/essays/react-chart-libraries/
- https://github.com/assistant-ui/assistant-ui
- https://github.com/vercel/ai
- https://github.com/tanstack/query/releases
- https://zustand.docs.pmnd.rs/reference/migrations/migrating-to-v5

---

## Area 7: Notifications & Background Scheduling

### Current State
- `src/backend/modules/notification_scheduler.py`: hand-rolled `asyncio`-based polling loop (`while ... await asyncio.sleep(60)`), **not actually using APScheduler despite `apscheduler>=3.10.0` being declared in `requirements.txt`**. No `import apscheduler` found anywhere in `src/backend`.
- `src/backend/modules/platform_notifications.py` (the actual notification module — **`modules/notify.py` does not exist** in this repo, correcting an earlier exploration-phase reference): abstract `NotificationProvider` with `WindowsToastProvider` (native `winsdk`, Windows-only) as primary and `PlyerProvider` as cross-platform fallback, plus a `MockProvider` for tests. `NotificationService` tries Windows toast first, falls back to plyer.

### Candidates Considered
| Name | License | Size/footprint | Maturity/recency | Fit notes |
|---|---|---|---|---|
| APScheduler 3.11.x (current pin family) | MIT | Already a dependency | Active; 3.11.3 released June 28, 2026 — actively maintained by agronholm | Stable, fine for single-user local scheduling; but currently **unused** — the hand-rolled loop duplicates what it offers (interval jobs, misfire handling, persistence) |
| APScheduler 4.x | MIT | N/A | Still pre-release (4.0.0a1); explicitly marked "do NOT use in production"; no stable date announced | Not viable now — disqualified by its own maintainer warning |
| plyer (current) | MIT | Small | Stale — last PyPI release 2.1.0 was Nov 2022 (3.5+ yrs); 119 open issues; known Windows toast/Android-targeting bugs | License and footprint fine, but maintenance signal is weak |
| desktop-notifier | MIT | Small, pure-Python deps | Active — 6.2.0 released Aug 2025; supports Py 3.9–3.13; async-native | Best maintenance signal. Needs a running asyncio loop (already true here — FastAPI/uvicorn) and macOS requires a signed executable (same constraint any native macOS toast approach has) |
| win10toast / platform-native | Varies | Trivial | win10toast itself is unmaintained/abandoned | Not a real alternative; would still need per-OS code, which is what plyer/desktop-notifier already abstract |

### Recommendation
**Prototype `desktop-notifier` as a parallel `NotificationProvider`; do not touch APScheduler.**
- Scheduler: no change justified. The real gap isn't the library choice, it's that `apscheduler` is declared but unused — that's a separate cleanup item (remove the unused pin, or actually adopt 3.x for the polling loop) rather than a "new tech" decision. APScheduler 4.x is not production-ready; stay on 3.11.x if/when adopted.
- Notifications: plyer's multi-year release gap and open reliability issues are a real signal worth addressing, but this is low-complexity/low-risk territory, so the bar is "prototype first," not "rip and replace." `desktop-notifier` is MIT, async-native (fits the existing FastAPI/asyncio runtime), actively maintained, and supports the same OS set. Validate actual notification delivery on the team's target OSes (especially macOS signing) before committing.

### Risks
- **Maintenance**: plyer risk is real but not urgent — it still functions; failure mode is silent/degraded delivery, not a crash.
- **License**: all candidates are MIT; no GPL/AGPL exposure.
- **Perf**: negligible either way — these are infrequent (per-minute-checked, per-dose) local notification calls, not a hot path.
- **Platform**: desktop-notifier's macOS code-signing requirement could block notifications in unsigned dev/test builds — needs verification, not assumed to work.

### Effort Estimate
**S** (prototype desktop-notifier as an additional provider behind the existing `NotificationProvider` interface; separately, S to either wire up or drop the unused apscheduler pin).

### Sources
- https://pypi.org/project/APScheduler/
- https://github.com/agronholm/apscheduler/issues/465 (APScheduler 4.0 progress tracking)
- https://pypi.org/project/APScheduler/4.0.0a1/
- https://pypi.org/project/plyer/
- https://snyk.io/advisor/python/plyer
- https://github.com/kivy/plyer
- https://pypi.org/project/desktop-notifier/
- https://github.com/samschott/desktop-notifier

---

## Area 8: Auth & Encryption

### Current State
JWT auth and password hashing live in `src/backend/core/security.py`: token issuance/verification via `from jose import JWTError, jwt` (python-jose, HS256, JWT secret cached from `settings.jwt_secret` or a local file, with a `TokenRevocationList` for revocation), and password hashing via `bcrypt.gensalt(rounds=PASSWORD_HASH_ROUNDS)` / `bcrypt.hashpw` / `bcrypt.checkpw`. Encrypted per-profile storage uses `sqlcipher3-binary` through `src/backend/core/sqlcipher_driver.py`. `src/backend/security/` holds non-crypto middleware: `audit_middleware.py` (structured JSON logging of mutating requests, optional DB persistence, **no integrity protection on the log itself**), plus `input_validator.py`, `rate_limit_middleware.py`, `security_headers.py`. `requirements.txt` pins `cryptography>=42.0.0`, `python-jose[cryptography]>=3.3.0`, `bcrypt>=4.1.2`.

### Candidates Considered
| Name | License | Maturity/recency | Fit notes |
|---|---|---|---|
| python-jose (current) | MIT | v3.5.0 (May 2025); no release in ~12mo; 4 known CVEs, one (ecdsa dep) marked won't-fix by maintainers | FastAPI's own docs/community now steer away from it; low activity is the real concern, not active exploitation |
| PyJWT | MIT | v2.13.0 (May 2026), actively released, minimal deps | Does only JWT (no JWE) — sufficient since this app only needs signed tokens, not encrypted ones; FastAPI ecosystem's de facto replacement for python-jose |
| Authlib / joserfc | BSD-3-Clause | Actively maintained, broader OAuth2/OIDC scope | Overkill — this is a local single-user app with no OAuth/OIDC flows; adds surface area not needed |
| bcrypt (current) | Apache-2.0 | Mature, still safe at cost≥12 | Not broken, but OWASP now ranks it #3 behind Argon2id and scrypt |
| argon2-cffi | MIT | v25.1.0 (Jun 2025), wraps reference Argon2 C lib | OWASP's current default recommendation (memory-hard, GPU/ASIC-resistant); good fit for a health-data app |
| SQLCipher (current) | BSD-style (community ed.) | Long-established, widely audited, current product | No change warranted |
| SQLite3 Multiple Ciphers (sqlite3mc) | MIT | Active, v2.3.5 (Jun 2026), supports ChaCha20-Poly1305 | Genuine alternative but no migration motivation — SQLCipher works, is audited, app already built on it |
| Hash-chained audit log (custom, SHA-256 prev-hash field) | N/A (pattern, not a library) | Common tamper-evident pattern | Worth a light follow-up: current `audit_middleware.py` has no integrity field; a `prev_hash`/`hash` column on the audit table would be a small, local-only addition (no new deps) |

### Recommendation
- **JWT: prototype PyJWT first**, then migrate off python-jose. This is the clearest, lowest-risk win in this batch — drop-in replacement, MIT, actively maintained, smaller dependency surface, sidesteps the unfixed `ecdsa` CVE chain. **Requires human sign-off per CLAUDE.md before touching `core/security.py`.**
- **Password hashing: prototype argon2-cffi**, but treat as lower urgency than the JWT swap. Current bcrypt usage isn't broken (cost factor should be confirmed ≥12, not verified in this pass), so this is "should modernize," not "must fix." **Requires human sign-off.**
- **SQLCipher: no change justified.** Still the conservative, audited choice; sqlite3mc is interesting but offers no concrete problem it solves here.
- **Audit log hash-chaining: prototype/spike only.** Worth a small design spike (no new dependency, pure stdlib `hashlib`) to add a `prev_hash` chain to the audit table for tamper evidence — but this is additive logging, not auth/crypto-library replacement, so it carries lower review weight than the JWT/password items (though it still touches audit logging, so still flag for review per CLAUDE.md's audit-logging invariant).

### Risks
- **Safety/trust**: any change to `core/security.py` affects every authenticated request — must be paired with full regression of the auth test suite and a careful look at JWT claim/algorithm handling during migration (e.g., explicit `algorithms=["HS256"]` allow-list, no `alg:none`).
- **Perf**: Argon2id is intentionally memory-hard; needs local tuning (OWASP baseline ~19MiB/t=2/p=1, or stronger) to avoid noticeable login latency on lower-end hardware this local app may run on.
- **License**: all top candidates (PyJWT, argon2-cffi, sqlite3mc) are MIT — no GPL/AGPL exposure.
- **Maintenance**: python-jose is the one clear maintenance red flag in the current stack; bcrypt and SQLCipher are not at risk, just incrementally behind best practice.

### Effort Estimate
PyJWT migration: **S**. argon2-cffi migration: **S–M** (touches stored-hash format; needs a migration/verification path for existing bcrypt hashes). Audit hash-chaining spike: **S**.

### Sources
- https://github.com/mpdavis/python-jose/issues/340
- https://github.com/mpdavis/python-jose/issues/341 (ecdsa CVE, won't-fix)
- https://security.snyk.io/package/pip/python-jose
- https://github.com/fastapi/fastapi/discussions/9587
- https://pypi.org/project/python-jose/
- https://pypi.org/project/PyJWT/
- https://pypi.org/project/argon2-cffi/
- https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- https://www.zetetic.net/sqlcipher/comparison/
- https://utelle.github.io/SQLite3MultipleCiphers/
- https://appmaster.io/blog/tamper-evident-audit-trails-postgresql

**Note**: This research read `core/security.py` and `src/backend/security/` files read-only for grounding; no secret values were read or reported, per scope boundary given to the research agent.

---

## Area 9: Gamification & Analytics

### Current State
`badge_evaluator.py` is ~165 lines: a dict-based badge registry (`BADGE_DEFS`) evaluated inline after each dose log, with dedup via `existing_badge_keys` and timezone-aware date logic delegated to `streak_engine.py`. `streak_engine.py` (~80 lines) does pure-function calendar-date streak/gap math over `taken_at`/`was_skipped` using `zoneinfo`. `analytics.py` (~270 lines) is deterministic trend/delta/rolling-average/abnormal-flag logic over lab observations, no LLM, no gamification overlap. All three are dependency-free, synchronous-friendly, and tightly coupled to this app's domain models (`EarnedBadge`, dose/observation shapes) — not generic enough to externalize cleanly.

### Candidates Considered
| Name | License | Maturity/recency | Fit notes |
|---|---|---|---|
| Trophy (PyPI `trophy`) | MIT (client lib) | Active, June 2026 release | Hard blocker: client for a hosted SaaS API requiring an account/API key — violates local-first/zero-network constraint outright |
| gamification-engine (gengine) | MIT | Abandoned — last release Jan 2020 | Pyramid+SQLAlchemy server framework, heavy (own DB schema, web UI); wrong shape (full service vs. inline function) and unmaintained |
| django-gamification | MIT | Low activity, Django-coupled | Wrong framework (this is FastAPI, no Django ORM); badge/points model less flexible than current per-medication/timezone logic |
| Differential-privacy libs (PyDP, diffprivlib, PipelineDP) for analytics.py | Apache-2.0/MIT | Active | Solve cross-user aggregate privacy, not applicable — `analytics.py` only computes a single patient's own trends locally; no aggregation step exists to protect |

No strong candidates found for either sub-area.

### Recommendation
**No change justified.** Bespoke is correct here — the badge/streak logic is small, domain-specific (timezone-aware adherence calendars, per-medication dedup), and every general-purpose library found is either a network-dependent SaaS client (constraint violation) or an abandoned/oversized server framework. For `analytics.py`, no replacement category even applies.

One soft, evidence-informed nudge (not a library adoption): scoping-review literature (JMIR mHealth 2022/2024, Frontiers 2025) suggests gamification effectiveness correlates with longer intervention windows (6+ months) and patient-perspective-informed reward framing, not just streak counts — could inform future badge design tuning, not an architecture change.

### Risks
None from inaction. Risk of adopting Trophy: silent network dependency violating local-first invariant. Risk of gengine: unmaintained dependency, license-compatible but operationally dead.

### Effort Estimate
**S** (research only; no action recommended).

### Sources
- https://pypi.org/project/trophy/
- https://pypi.org/project/gamification-engine/
- https://pypi.org/project/django-gamification/
- https://mhealth.jmir.org/2024/1/e50851
- https://www.frontiersin.org/journals/pharmacology/articles/10.3389/fphar.2025.1632474/full
- https://mhealth.jmir.org/2022/2/e30671/citations

---

## 13. Notes for the Implementation-Planning Agent

1. **This document is research only — no code has been changed.** Every recommendation above is "prototype first" or "no change," never "ship directly."
2. **Areas 1 (Faithfulness/Entailment), 3 (Redaction), and 8 (Auth/Encryption) require explicit human sign-off** before any code change touches `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, or `src/backend/core/security.py` — this is a hard rule from `CLAUDE.md`, not a suggestion. Do not draft an implementation plan for these areas without first confirming the user wants to proceed on that specific area.
3. **Every safety-critical recommendation is additive/prototype-first by design** — e.g., the NLI model in Area 1 augments the rule-based floor rather than replacing it; the NER pass in Area 3 augments the regex floor. Any implementation plan should preserve this framing, not propose wholesale replacement of deterministic safety checks.
4. **Areas 2, 5, and 9 concluded "no change justified."** Do not re-litigate these without new evidence (e.g., corpus size actually growing past tens-of-thousands of chunks for Area 2, or a concrete LOC-reduction case for Area 5).
5. **Two corrections from the original exploration phase are baked into this document** and should be treated as ground truth going forward: (a) `modules/agent/` is a hand-rolled state machine, not LangGraph; (b) `apscheduler` is an unused/dead dependency and the real file is `modules/platform_notifications.py`, not `modules/notify.py`.
6. **One confirmed dead-code item independent of any specific area's recommendation**: `core/config.py`'s `vector_store_type` field and the unused `faiss-cpu` dependency are candidates for a small, low-risk cleanup PR regardless of whether Area 2's "no change" recommendation is revisited.
7. **License discipline matters in this codebase** — every candidate surfaced and recommended above is MIT/Apache-2.0/BSD-3. Several candidates considered and explicitly rejected (Surya model weights, LayoutLMv3) were disqualified specifically on licensing grounds (OpenRAIL-M commercial restrictions, CC BY-NC-SA). Any new candidate introduced during implementation planning should be checked against the same bar.
8. **All new LLM/ML components must integrate via existing facades** — `core/llm/` (`ModelRunner`/`ProviderProtocol`) for any generative component, and the existing `sentence-transformers` dependency path for any embedding/classifier component — per CLAUDE.md's "no new abstraction layers" rule.
