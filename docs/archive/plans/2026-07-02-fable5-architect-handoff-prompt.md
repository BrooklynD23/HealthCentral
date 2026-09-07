# Handoff Prompt for Claude Fable 5 — System Architect Review

> Historical Reference: this handoff prompt is retained for history and is not an active tracker. For active remaining work, use [`docs/features/TASK_LIST.md`](../../features/TASK_LIST.md).

**Purpose of this file:** a ready-to-paste prompt for a *separate* Claude Fable 5 (`claude-fable-5`)
session, asking it to review [`2026-07-02-consolidated-findings-report.md`](2026-07-02-consolidated-findings-report.md)
as a system architect and synthesize new feature/improvement ideas — not to write code, and not to
be run inside this repo's agent session. Paste everything below the `---` divider as the user turn.

## Why this prompt is shaped the way it is

Fable 5 performs best when given the complete task spec in one turn rather than progressively, so
the entire findings report is embedded below rather than referenced by path. The instructions also
apply several documented Fable-5-specific behavioral tunings rather than generic prompting advice:

- **Effort:** run this at `output_config.effort: "high"` (or `"xhigh"` if available in your client)
  — this is exactly the "capability-sensitive, ambiguity-navigation" workload the higher effort
  tiers are tuned for, not routine work.
- **Anti-overplanning:** synthesis tasks like this can otherwise turn into an exhaustive survey of
  every option; the prompt tells it to commit to a ranked shortlist instead of enumerating
  everything it considered.
- **Explicit boundary:** this is a review-and-propose task, not an implementation task. The prompt
  states plainly that no code should be written and no files in any repository should be touched —
  Fable 5 sometimes takes unrequested-but-adjacent actions, so the boundary is stated rather than
  assumed.
- **Grounded claims:** the prompt requires every proposal to cite which section of the findings
  report motivates it, so speculative ideas are traceable back to real evidence instead of
  free-floating suggestions.
- **Lead-with-outcome / readability:** the requested output format puts the ranked recommendation
  list first, reasoning after — matching how Fable 5 is tuned to structure long-form answers for a
  reader who wants the TLDR before the detail.
- **"Reason, not just request":** the prompt opens by stating who this is for and why, rather than
  jumping straight to the ask — Fable 5 uses that framing to weigh proposals against actual project
  constraints (local-first, safety-critical modules) instead of generic SaaS-health-app patterns.

If your client exposes a separate system prompt field, everything from **"You are acting as..."**
through **"...before proposing it."** works as the system prompt, with the report and task section
as the user turn. If not, paste it all as one user message — Fable 5 does not require the split.

---

I'm handing you the consolidated findings from a full audit of a local-first patient health app
(HealthCentral), done by a coding agent over an extended session of codebase exploration, targeted
research, and verified code review. I want your read on it as a system architect: given everything
below, what should this project build or change next that isn't already on its list? This feeds
directly into the next planning cycle, so treat it as a real input, not a writing exercise.

**Your role:** act as a system architect encountering this project for the first time through this
report. Your job is to review the tech stack, what's shipped, what's gap/partial, and what's
already been recommended — then propose *new* feature or architecture ideas that complement or
extend the app, beyond what's already listed in Section 4 of the report. Don't re-propose items
already in Section 4; if you think one of those deserves re-prioritization, say so briefly, but
your main value-add is what's *missing* from this list entirely.

**Constraints that must hold for anything you propose** (this is a real medical-adjacent product,
not a prototype):
- Local-first: no proposal may require sending patient data off-device. Cloud APIs are acceptable
  only for non-patient-data functionality (e.g., fetching public reference ranges), and must be
  optional/degradable, never required for core function.
- No medical advice: outputs must stay educational/citation-grounded, never diagnostic or
  prescriptive (no dosing, no diagnosis).
- Safety-critical modules (`interpret_safety.py`, `redaction.py`, `faithfulness.py`,
  `verifier_agent.py`, auth/encryption) require explicit human sign-off for any change — treat any
  proposal touching these as needing a "flag for review" callout, not a shovel-ready plan.
- Prefer extending existing abstractions (the `core/llm/` provider layer, the existing agent state
  machine, the existing redaction/faithfulness modules) over introducing new dependencies or
  parallel systems, unless you can justify why the existing one is the wrong shape entirely.
- The team is small; weight recommendations by leverage (safety/trust impact, user value) against
  implementation cost — don't propose enterprise-scale infrastructure for a single-user-per-profile
  desktop app.

**What NOT to do:** don't write code, don't produce a step-by-step implementation plan, don't touch
any file or repository — this is a review-and-propose task. If you want to sanity-check a technical
claim (e.g., whether a library exists or is actively maintained), say so explicitly and flag it as
worth verifying rather than presenting it as confirmed.

**How to structure your answer:**
1. Lead with a ranked shortlist (5-10 items) of new feature/architecture proposals — one line each,
   most valuable first. This is the part someone skims for the TLDR.
2. For each shortlisted item, give: what it is, why it matters *for this specific app* (cite the
   section/finding below that motivates it — e.g. "motivated by Section 3 item 2"), rough
   complexity/risk, and whether it touches a safety-critical module.
3. Don't pad this with an exhaustive list of options you considered and rejected — if you weighed
   alternatives, name the one you'd recommend and why, not a survey of all of them.
4. Close with anything you noticed that's a genuine gap in the report itself (missing context you'd
   want before finalizing a recommendation), not a feature idea.

Here is the full findings report:

<findings-report>

# HealthCentral — Consolidated Findings Report (2026-07-02)

## 1. Tech Stack

**Backend**
- Python 3.10/3.11, FastAPI, SQLAlchemy 2.0, Alembic — dual migration chains (`migrations/master/`, `migrations/profile/`)
- SQLCipher per-profile encrypted DBs; master DB unencrypted (profile metadata, audit logs)
- Security: JWT via `python-jose` (HS256, `TokenRevocationList`), `bcrypt` password hashing (cost factor 12 — meets OWASP floor), rate limiting, security headers, input validation middleware, `SecurityAuditMiddleware`

**LLM / AI pipeline**
- `core/llm/` provider abstraction (4 files: `provider.py`, `factory.py`, `ollama_provider.py`, `llama_cpp_provider.py`) — Ollama (localhost-only) + llama-cpp-python (GGUF) providers, selected via `LLM_PROVIDER`/`LLM_MODEL` env vars
- `core/model_runner.py`'s `ModelRunner` — the only sanctioned LLM entry point for feature code
- Tiered local models: BioMistral-7B (high/32GB+), Phi-3-mini (mid/16GB+), Qwen2.5-0.5B (low/8GB+), template-only fallback (zero RAM). Ollama default `gemma4:12b` + edge variants — these Gemma4 GGUF repo URLs are marked PLACEHOLDER/unverified in code, not a shipped confirmed default
- `modules/embeddings.py` — sentence-transformers `all-MiniLM-L6-v2` (384-dim), SHA256 hash-based fallback when model unavailable
- `modules/rag.py` — linear-scan cosine similarity retrieval (no vector index; confirmed adequate at current per-patient corpus scale)
- `modules/agent/` — hand-rolled state machine, NOT LangGraph (explicit design choice, own docstring confirms it, zero LangGraph dependency anywhere). Plan → Act → Reflect → Draft → Guard loop, MAX_STEPS=5, deterministic replay from logged steps. Guardrails subpackage: groundedness, redaction gate, classifier, templates.
- `modules/faithfulness.py` / `modules/verifier_agent.py` — rule-based/regex entailment scoring (see gaps below)
- `modules/redaction.py` — deterministic regex PHI/PII redaction, policy levels strict/standard/minimal

**Frontend**
- React 18.2, TypeScript 5.3, Vite 7, Tailwind 3.4, Radix UI
- Recharts 3.9.1
- Zustand (state), TanStack Query (server state), Framer Motion
- 12 pages: TrendsDashboard, LabInterpreter, ExplainAssistant, DocumentInbox, MedicationCoach, MedicationDetail, SettingsPage, VerificationWorkbench, NotificationSettings, ExportPage, ProfileSetup, etc.

**Testing / CI**
- ~676 backend pytest tests passing (7 pre-existing env-only failures: date-extraction, PDF-extraction, embedding-similarity threshold — all environment-dependent, not code bugs)
- 14 frontend vitest files (105 tests), 5 Playwright e2e specs (auth, document-import, settings-smoke, assistant, ui-full-verification)
- GitHub Actions CI: docs-lint, backend-tests, frontend-tests, security scan (bandit + pip-audit), agent-eval gate (fails on advice leakage/ungrounded answers), e2e smoke
- CI gap: bandit/pip-audit both run with `continue-on-error: true` — security scan findings never fail the build

**Docs tooling**
- `scripts/docs_lint.py` — 10 rules (canonical ownership, historical banners, required sections, internal-link validation, canonical-doc-order consistency) + `--link-graph` flag emitting `docs/_link_graph.json`
- `scripts/generate_docs_index.py` — generates `docs/INDEX.md`, a flat repo-wide doc map
- `docs/roles/` — 8 domain-based architecture entry-point docs

**Skills**
- `.claude/skills/` — 14 vendored Superpowers skills for Claude Code web/cloud sessions
- `skills/` (no dot, separate) — 4 project-domain skills: `healthcentral-backend`, `healthcentral-guardrails`, `healthcentral-evals`, `healthcentral-agent`

## 2. Shipped Features (Confirmed Implemented)

- Document pipeline: PDF/image import → OCR (pytesseract + pdfplumber, gated behind a feature flag) → classification (keyword/regex, 4 categories: lab/pathology/imaging/visit-notes) → extraction → verification workbench
- Trends dashboard: per-analyte charting (Recharts), medication overlay
- RAG-grounded assistant (ExplainAssistant): cites `[YOUR_RESULTS:N]` (patient data) / `[REFERENCE:N]` (general knowledge) / `[KB:N]` / `[INT:N]`; session memory; feedback (thumbs/corrections)
- Medication coach: adherence tracking, dose logging, correlation overlay in frontend (`utils/correlation.ts` heuristic — no backend endpoint)
- Voice logging: browser Web Speech API, transcript-only storage (no audio)
- Gamification: badges (`badge_evaluator.py`), streaks (`streak_engine.py`) — bespoke, dependency-free
- Export: CSV/JSON/PDF, doctor-ready summaries with clinician questions, RL dataset export (DPO/GRPO/SFT JSONL) — redaction policy gap, see below
- Notifications: hand-rolled asyncio polling scheduler; `WindowsToastProvider` → `DesktopNotifierProvider` → `PlyerProvider` fallback chain
- Model settings: tier switching, hardware detection, external API settings, OCR toggle, agent-mode toggle
- Audit logging: complete on all document/observation read (GET) and write routes
- Knowledge base: `BiomarkerRelationship` table — confirmed live and wired (seeded, queried by `knowledge_loader.py`, consumed by `interpret.py`'s panel insights)

## 3. Unimplemented / Partial Features (Gaps Found)

Ranked roughly by safety/security stakes:

1. **RL-REDACT-001** (highest stakes found) — `modules/rl_dataset.py:103` hardcodes `RedactionEngine(policy_level="standard")` for RL dataset export. Standard policy does not redact lab values, dates, medication names, or biomarker values — only "strict" covers DOB/addresses/MRNs, and strict isn't the default. Exported DPO/GRPO/SFT training data may retain clinically identifying content.
2. **Faithfulness/entailment scoring is 100% rule-based in production** — `faithfulness.py`'s `entailment_score` only uses real NLI if `entailment_scores` is explicitly passed in; no production caller does this. `consistency_score` hardcoded to 1.0 (dormant placeholder). `verifier_agent.py`'s `use_llm_entailment` flag routes to a stub that just calls the rule-based path.
3. **PHI/PII redaction is regex-only** — `modules/redaction.py` has no NER/ML model; misses contextual PHI (e.g. a name in free text without a labeled field prefix).
4. **S06-SEC-003** — streaming request-body size enforcement raises a bare `ValueError` (`input_validator.py:101-104`) with no global exception handler converting it to a clean 413.
5. **HIPAA technical safeguards not implemented**: MFA, automated key rotation (currently manual via password change only), penetration testing (not yet performed), BAA template (not created).
6. **MED-CORR-001** — `GET /medications/{id}/correlations` backend endpoint does not exist; only a frontend heuristic.
7. **F-006** — proposed removal of `profile_id` from API response DTOs (`MemoryItemResponse`, `DocumentResponse`, `ObservationResponse`) — still just a review doc, not started, not approved.
8. **E2E-MED-001** — `MedicationDetail` page has zero Playwright e2e coverage (route exists and works, just untested end-to-end); every other page has at least one covering spec.
9. **Auth library maintenance risk** — `python-jose` has had no release in ~12 months and carries an unfixed `ecdsa`-dependency CVE (maintainers marked won't-fix). Not yet migrated to `PyJWT`.
10. **Gemma4 model URLs unverified** — marked PLACEHOLDER in `model_selector.py`/`download_models.py`. Treat the generative default LLM as not-yet-pinned.
11. **CI security scans don't gate the build** — `bandit`/`pip-audit` run with `continue-on-error: true`.
12. **Sprint 7 / LoRA fine-tuning** — explicit stretch goal in `AGILE_PLAN.md`/PRD, zero code exists, deferred by design pending user sign-off.
13. **Shared model-distribution infrastructure missing** — `scripts/download_models.py` is GGUF/Ollama-only; adding a real NLI model (item 2's fix) or NER model (item 3's fix) needs a non-GGUF acquisition + offline-loading path that doesn't exist yet. Also: `embeddings.py`'s `SentenceTransformer` load has no `local_files_only`/offline flag — a latent tension with the "no network calls" invariant.
14. **Retrieval has no index** — `rag.py` does a linear scan; confirmed fine at current per-patient corpus scale (tens–hundreds of chunks), not itself a gap, but noted since it interacts with item 13's model-loading work.

## 4. Features That Could Improve (Research-Backed Recommendations Already Made)

| Area | Recommendation | Status |
|---|---|---|
| Faithfulness/Entailment | Prototype `cross-encoder/nli-deberta-v3-xsmall` (MIT, 22M params, <500MB RAM) as an additive confirmation pass alongside the existing rule-based floor, never replacing it. Follow-up: LettuceDetect (ModernBERT-based, purpose-built for RAG hallucination detection). | Not started — requires sign-off |
| PHI Redaction | Prototype Philter/philter-lite (BSD-3, purpose-built for clinical de-identification) as an additive NER pass. Presidio (MIT) as fallback. | Not started — requires sign-off |
| Retrieval Indexing | No change justified now; if corpus scales into thousands of chunks, `sqlite-vec` (MIT) over dead `sqlite-vss`. Optional `BAAI/bge-small-en-v1.5` embedding upgrade. | Cleanup done; upgrade optional/deferred |
| Document Extraction/OCR | No change justified — pdfplumber/pytesseract adequate. If accuracy is later measured as lacking: docTR (MIT) or PaddleOCR lightweight config. | No action needed unless measured problem |
| Agent Orchestration | No change — already the lightweight, dependency-free choice. | Confirmed optimal as-is |
| Frontend | Recharts v3 upgrade (done). Consider `assistant-ui`'s streaming-chat UX patterns for ExplainAssistant as inspiration only. | Recharts done; streaming chat UX unexplored |
| Notifications | `desktop-notifier` added as additional provider (done). Unused `apscheduler` removed. | Done |
| Auth/Encryption | Migrate `python-jose` → `PyJWT`. `argon2-cffi` optional hardening only. | Not started — requires sign-off |
| Gamification | No change — bespoke badge/streak logic appropriately scoped. | Confirmed no action needed |
| Doc-linking | `graphify` deferred (sends content to a model API, conflicts with local-first bias); lighter local backlink graph + flat index shipped instead. | Done (lighter alternative) |

**Cross-cutting note:** Areas touching `faithfulness.py`, `verifier_agent.py`, `redaction.py`, `interpret_safety.py`, or `core/security.py` require explicit human sign-off before any code changes. Every safety-critical recommendation above is framed as additive, never a wholesale replacement.

</findings-report>

Before proposing anything, make sure you understand why each constraint above exists (local-first,
no-medical-advice, sign-off-gated safety modules) — ground every proposal in this report's actual
findings, not in generic "health app" patterns you already know. If a proposal doesn't clearly trace
back to something in this report, say so explicitly rather than presenting it as if it does.
