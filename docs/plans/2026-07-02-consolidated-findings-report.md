# HealthCentral — Consolidated Findings Report (2026-07-02)

> Snapshot compiled from a single agent session's exploration, research, and code-review passes.
> Not a new codebase scan — it synthesizes findings already verified during that session (Explore
> agents, research agents, direct code reads, and a review pass). Intended as structured input for
> a subsequent planning/ideation pass, not as a standalone roadmap. See
> [`docs/features/TASK_LIST.md`](../features/TASK_LIST.md) for the live, actively-maintained backlog
> and [`docs/00_architecture_plans_index.md`](../00_architecture_plans_index.md) for canonical doc
> order.

---

## 1. Tech Stack

**Backend**
- Python 3.10/3.11, FastAPI, SQLAlchemy 2.0, Alembic — **dual migration chains** (`migrations/master/`, `migrations/profile/`)
- SQLCipher per-profile encrypted DBs; master DB unencrypted (profile metadata, audit logs)
- Security: JWT via `python-jose` (HS256, `TokenRevocationList`), `bcrypt` password hashing (cost factor 12 — meets OWASP floor), rate limiting, security headers, input validation middleware, `SecurityAuditMiddleware`

**LLM / AI pipeline**
- `core/llm/` provider abstraction (exactly 4 files: `provider.py`, `factory.py`, `ollama_provider.py`, `llama_cpp_provider.py`) — Ollama (localhost-only) + llama-cpp-python (GGUF) providers, selected via `LLM_PROVIDER`/`LLM_MODEL` env vars
- `core/model_runner.py`'s `ModelRunner` — the only sanctioned LLM entry point for feature code
- Tiered local models: BioMistral-7B (high/32GB+), Phi-3-mini (mid/16GB+), Qwen2.5-0.5B (low/8GB+), template-only fallback (zero RAM). Ollama default `gemma4:12b` + edge variants — **note: these Gemma4 GGUF repo URLs are marked `PLACEHOLDER`/unverified in code**, not a shipped confirmed default
- `modules/embeddings.py` — sentence-transformers `all-MiniLM-L6-v2` (384-dim), SHA256 hash-based fallback when model unavailable
- `modules/rag.py` — linear-scan cosine similarity retrieval (no vector index; confirmed adequate at current per-patient corpus scale)
- `modules/agent/` — **hand-rolled state machine, NOT LangGraph** (explicit design choice, own docstring confirms it, zero LangGraph dependency anywhere). Plan → Act → Reflect → Draft → Guard loop, `MAX_STEPS=5`, deterministic replay from logged steps. Guardrails subpackage: groundedness, redaction gate, classifier, templates.
- `modules/faithfulness.py` / `modules/verifier_agent.py` — rule-based/regex entailment scoring (see Section 3)
- `modules/redaction.py` — deterministic regex PHI/PII redaction, policy levels strict/standard/minimal

**Frontend**
- React 18.2, TypeScript 5.3, Vite 7, Tailwind 3.4, Radix UI
- **Recharts 3.9.1** (upgraded this session from 2.10.3 — v2 was EOL upstream)
- Zustand (state), TanStack Query (server state), Framer Motion
- 12 pages: TrendsDashboard, LabInterpreter, ExplainAssistant, DocumentInbox, MedicationCoach, MedicationDetail, SettingsPage, VerificationWorkbench, NotificationSettings, ExportPage, ProfileSetup, etc.

**Testing / CI**
- ~676 backend pytest tests passing (7 pre-existing env-only failures: date-extraction, PDF-extraction, embedding-similarity threshold — all environment-dependent, not code bugs)
- 14 frontend vitest files (105 tests), 5 Playwright e2e specs (auth, document-import, settings-smoke, assistant, ui-full-verification)
- GitHub Actions CI: docs-lint, backend-tests, frontend-tests, security scan (bandit + pip-audit), agent-eval gate (fails on advice leakage/ungrounded answers), e2e smoke
- **CI gap**: bandit/pip-audit both run with `continue-on-error: true` — security scan findings never fail the build

**Docs tooling**
- `scripts/docs_lint.py` — 10 rules (canonical ownership, historical banners, required sections, internal-link validation, canonical-doc-order consistency) + `--link-graph` flag emitting `docs/_link_graph.json`
- `scripts/generate_docs_index.py` — generates `docs/INDEX.md`, a flat repo-wide doc map
- `docs/roles/` — 8 domain-based architecture entry-point docs (Backend/API, Frontend, Data & Migrations, AI/LLM Pipeline & Safety, Security & Compliance, DevOps/CI, Product/PRD, plus the roles index)

**Skills**
- `.claude/skills/` — 14 vendored Superpowers skills (github.com/obra/superpowers, MIT) for Claude Code web/cloud sessions
- `skills/` (no dot, separate) — 4 project-domain skills: `healthcentral-backend`, `healthcentral-guardrails`, `healthcentral-evals`, `healthcentral-agent`

---

## 2. Shipped Features (Confirmed Implemented)

- **Document pipeline**: PDF/image import → OCR (pytesseract + pdfplumber, gated behind a feature flag) → classification (keyword/regex, 4 categories: lab/pathology/imaging/visit-notes) → extraction → verification workbench
- **Trends dashboard**: per-analyte charting (Recharts), medication overlay
- **RAG-grounded assistant** (ExplainAssistant): cites `[YOUR_RESULTS:N]` (patient data) / `[REFERENCE:N]` (general knowledge) / `[KB:N]` / `[INT:N]`; session memory; feedback (thumbs/corrections)
- **Medication coach**: adherence tracking, dose logging, correlation overlay in frontend (`utils/correlation.ts` heuristic — **no backend endpoint**, see Section 3)
- **Voice logging**: browser Web Speech API, transcript-only storage (no audio)
- **Gamification**: badges (`badge_evaluator.py`), streaks (`streak_engine.py`) — bespoke, dependency-free
- **Export**: CSV/JSON/PDF, doctor-ready summaries with clinician questions, RL dataset export (DPO/GRPO/SFT JSONL) — **redaction policy gap, see Section 3**
- **Notifications**: hand-rolled asyncio polling scheduler; `WindowsToastProvider` → `DesktopNotifierProvider` → `PlyerProvider` fallback chain
- **Model settings**: tier switching, hardware detection, external API settings, OCR toggle, agent-mode toggle (`agent_enabled`, cutover flag for the agent-graph vs. legacy retrieval path)
- **Audit logging**: complete on all document/observation read (GET) and write routes
- **Knowledge base**: `BiomarkerRelationship` table — confirmed live and wired (seeded, queried by `knowledge_loader.py`, consumed by `interpret.py`'s panel insights)

---

## 3. Unimplemented / Partial Features (Gaps Found)

Ranked roughly by safety/security stakes:

1. **RL-REDACT-001** (highest stakes found) — `modules/rl_dataset.py:103` hardcodes `RedactionEngine(policy_level="standard")` for RL dataset export. Standard policy does **not** redact lab values, dates, medication names, or biomarker values — only "strict" covers DOB/addresses/MRNs, and strict isn't the default. Exported DPO/GRPO/SFT training data may retain clinically identifying content.
2. **Faithfulness/entailment scoring is 100% rule-based in production** — `faithfulness.py`'s `entailment_score` only uses real NLI if `entailment_scores` is explicitly passed in; no production caller does this. `consistency_score` hardcoded to `1.0` (dormant placeholder). `verifier_agent.py`'s `use_llm_entailment` flag routes to a stub that just calls the rule-based path.
3. **PHI/PII redaction is regex-only** — `modules/redaction.py` has no NER/ML model; misses contextual PHI (e.g. a name in free text without a labeled field prefix).
4. **S06-SEC-003** — streaming request-body size enforcement raises a bare `ValueError` (`input_validator.py:101-104`) with no global exception handler converting it to a clean 413.
5. **HIPAA technical safeguards not implemented**: MFA, automated key rotation (currently manual via password change only), penetration testing (not yet performed), BAA template (not created).
6. **MED-CORR-001** — `GET /medications/{id}/correlations` backend endpoint does not exist; only a frontend heuristic.
7. **F-006** — proposed removal of `profile_id` from API response DTOs (`MemoryItemResponse`, `DocumentResponse`, `ObservationResponse`) — still just a review doc, not started, not approved.
8. **E2E-MED-001** — `MedicationDetail` page has zero Playwright e2e coverage (route exists and works, just untested end-to-end); every other page has at least one covering spec.
9. **Auth library maintenance risk** — `python-jose` has had no release in ~12 months and carries an unfixed `ecdsa`-dependency CVE (maintainers marked won't-fix). Not yet migrated to `PyJWT`.
10. **Gemma4 model URLs unverified** — marked `PLACEHOLDER` in `model_selector.py`/`download_models.py`. Treat the generative default LLM as not-yet-pinned.
11. **CI security scans don't gate the build** — `bandit`/`pip-audit` run with `continue-on-error: true`.
12. **Sprint 7 / LoRA fine-tuning** — explicit stretch goal in `AGILE_PLAN.md`/PRD, zero code exists, deferred by design pending user sign-off.
13. **Shared model-distribution infrastructure missing** — `scripts/download_models.py` is GGUF/Ollama-only; adding a real NLI model (item 2's fix) or NER model (item 3's fix) needs a non-GGUF acquisition + offline-loading path that doesn't exist yet. Also: `embeddings.py`'s `SentenceTransformer` load has no `local_files_only`/offline flag — a latent tension with the "no network calls" invariant.
14. **Retrieval has no index** — `rag.py` does a linear scan; confirmed fine at current per-patient corpus scale (tens–hundreds of chunks), not itself a gap, but noted since it interacts with item 13's model-loading work.

---

## 4. Features That Could Improve (Research-Backed Recommendations)

From a 9-area open-source technology survey (`docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md`), plus follow-on findings:

| Area | Recommendation | Status |
|---|---|---|
| **Faithfulness/Entailment** | Prototype `cross-encoder/nli-deberta-v3-xsmall` (MIT, 22M params, <500MB RAM) as an **additive** confirmation pass alongside the existing rule-based floor, never replacing it. Follow-up: LettuceDetect (ModernBERT-based, purpose-built for RAG hallucination detection, has a zero-RAM-tier variant). | Not started — requires sign-off (touches `faithfulness.py`/`verifier_agent.py`) |
| **PHI Redaction** | Prototype Philter/philter-lite (BSD-3, purpose-built for clinical de-identification, 99%+ recall in published benchmarks) as an **additive** NER pass. Presidio (MIT) as fallback if accuracy disappoints. | Not started — requires sign-off (touches `redaction.py`) |
| **Retrieval Indexing** | No change justified now; if corpus ever scales into thousands of chunks, `sqlite-vec` (MIT, actively maintained) over the currently-declared-but-dead `sqlite-vss`. Optional: `BAAI/bge-small-en-v1.5` embedding upgrade (same size/license class as current model, modestly better MTEB score). | Cleanup done (dead config removed); upgrade optional/deferred |
| **Document Extraction/OCR** | No change justified — pdfplumber/pytesseract adequate for now. If OCR accuracy is later measured as lacking: docTR (MIT) or PaddleOCR lightweight config are the only candidates clearing both license and hardware-tier bars (Surya and LayoutLMv3 both have license blockers for this use case). | No action needed unless a real accuracy problem is measured |
| **Agent Orchestration** | No change — already the lightweight, dependency-free choice; adopting LangGraph or pydantic-ai would add a dependency for zero LOC reduction. | Confirmed optimal as-is |
| **Frontend** | Recharts v3 upgrade (done). Consider studying `assistant-ui`'s streaming-chat UX patterns for `ExplainAssistant` (true token streaming vs. current full-response mutation) — as inspiration only, not as a dependency (its protocol assumes a different backend shape). | Recharts done; streaming chat UX unexplored |
| **Notifications** | `desktop-notifier` added as an additional provider (done), plyer/winsdk retained as fallback. Unused `apscheduler` dependency removed. | Done |
| **Auth/Encryption** | Migrate `python-jose` → `PyJWT` (clearest, lowest-risk win — active maintenance, sidesteps unfixed CVE). `argon2-cffi` is optional hardening only (bcrypt is already at the OWASP floor, not below it) — lower priority than the JWT swap. | Not started — requires sign-off (touches `core/security.py`) |
| **Gamification** | No change — bespoke badge/streak logic is appropriately scoped; every general-purpose library considered was either network-dependent (violates local-first) or abandoned/oversized. | Confirmed no action needed |
| **Doc-linking / "graphify"** | `github.com/safishamsi/graphify` is a real tool but not installed — sends doc content to a model API for semantic description, deferred given local-first bias and repo scale (~100 docs). Implemented lighter local alternative instead: backlink graph (`docs/_link_graph.json`) + flat `docs/INDEX.md`, both extending the existing `docs_lint.py` link-checker rather than adding a dependency. | Done (lighter alternative shipped instead) |

**Cross-cutting note:** Areas touching `faithfulness.py`, `verifier_agent.py`, `redaction.py`, `interpret_safety.py`, or `core/security.py` require explicit human sign-off before any code changes, per this project's `CLAUDE.md`. Every safety-critical recommendation above is framed as *additive* (new signal alongside the existing rule-based floor), never a wholesale replacement — that framing should be preserved in any implementation plan built from this report.
