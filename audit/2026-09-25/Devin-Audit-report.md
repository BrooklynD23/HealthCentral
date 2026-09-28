# Asclexis Repository Audit — Unified State Model

6 audit agents + reconciliation + independent orchestrator verification · 2026-09-25 · main @ `40f590e`

> ## Correction addendum — 2026-09-27
>
> The report text below is preserved as the 2026-09-25 historical record. Where the 2026-09-27 re-check found a statement wrong or unsupported, it is corrected **here**, and short inline `[2026-09-27: …]` markers point back to this addendum. Full dispositions: [`review/2026-09-27-followup.md`](review/2026-09-27-followup.md). Current-state architecture and gaps: [`docs/capstone-report/architecture-overview.md`](../../docs/capstone-report/architecture-overview.md) and [`specs-compliance-matrix.md`](../../docs/capstone-report/specs-compliance-matrix.md).
>
> **Corrected facts (numbered A-1 … A-8)**
>
> - **A-1 (§9, §17, §22; review F-05).** Branch `claude/healthcentral-agentic-research-r1n54x` is **19** commits ahead of main, not 21. Command: `git rev-list --count HEAD..origin/claude/healthcentral-agentic-research-r1n54x` → `19`. Branch A is 5 ahead. Both are 0 behind and fork from `40f590e`.
> - **A-2 (§1, §7; review F-06).** Backend collection was re-measured on 2026-09-27: `1245 tests collected` at `40f590e`. Command: `cd src/backend && /mnt/c/Python313/python.exe -B -m pytest tests/ --collect-only -q -p no:cacheprovider` (Windows Python 3.13.7; CI pins 3.11). This report executed no tests (see the methodology note). The figure's earlier provenance is commit `fd8984e` (2026-08-03), whose message reports CI "1245 passed" on `7897e47`. The "155 vitest" and "25 Playwright" figures were **not** re-measured and remain unverified.
> - **A-3 (§1, §8, §11 P1-4, §22; review F-03).** `datetime.utcnow`: the "~50 sites / 13 files" estimate is superseded. Main has 101 product **lines** in 30 files (`grep`), which hold **109 references** (AST), plus 16 test references in 6 files. The count is identical on both branch tips and on their merge.
> - **A-4 (§8 line "Full reconciler table had 40 rows", closing "Artifacts produced"; review F-12).** The 40-row reconciler table is **not in the package** and was not found anywhere in the checkout. The dashboard **does** exist at `audit/repository-audit-dashboard.html`: untracked, 32,761 bytes, dated 2026-09-25 01:51. Its §4 "Documentation vs Code" table has **12** rows, and it lists 19 severity-graded findings. It is a *pre-reconciliation* snapshot and disagrees with this report in two places. It calls the `model_selector` `llama_cpp` path a live P1 (this report and a 2026-09-27 re-check say dormant). It gives the `utcnow` count as "2 sites".
> - **A-5 (methodology note, §21; review F-16).** The separate agent reports, the raw reconciliation table, and any per-claim verification output are not packaged. "Verified by two independent agents" therefore reads as **reported in audit; not independently reproducible from this package**. The §21 owner answers are an agent-recorded Q&A with no linked source record. The program treats them as the best available record of owner intent, and re-confirms each one at the phase that depends on it.
> - **A-6 (§4 LLM bullet).** Re-verified 2026-09-27 as **dormant**: `modules/interpret.py:877 interpret_with_model` has zero callers (`grep -rn interpret_with_model src/backend` → definition only). It is the only caller of `_llm_interpretation` → `model_selector.run_inference` → `from llama_cpp import Llama` (`modules/model_selector.py:438`). A second non-ModelRunner inference path is **live but opt-in**: `core/external_runner.py:261-300` calls the OpenAI/Anthropic HTTPS APIs via `httpx` when a profile sets `use_external_api` (default `False`, `models/model_settings.py:78-81`), behind a strict-redaction gate (`core/external_runner.py:166-236`).
> - **A-7 (§6 "all five core flows… wired", §11; new this pass).** Four behaviours the report does not state:
>   1. CSV, JSON and doctor-summary exports do **not** pass through `modules/redaction.py` (`modules/export.py:82,223,267,290,358`; redaction only at `:533,637`). `docs/compliance/data-privacy.md:173-174` says every export except backups does.
>   2. The trends endpoint and the legacy RAG retrieval read unverified observations (`api/observations.py:529-535`, `modules/rag.py:322-328`).
>   3. On main the agent path reports a hard-coded `faithfulness_score=1.0` to the UI (`api/assistant.py:608-617`). The fix is on branch B (`cc202d9`).
>   4. The agent path makes no LLM call at all (`modules/agent/` imports no ModelRunner/provider).
> - **A-8 (§12, §21 Q2; context).** This report's body gives no user-level agent count. The "34" appeared in plan 03 and claims-ledger H5; the re-counted figure is **33** (review F-17). A disabled plugin's cache lists an `agentshield-pack` component, but no AgentShield hook is registered in `~/.claude/settings.json`.
>
> **Superseded guidance:** the §22 handoff's "Baseline: 1245" rule and "~40 stale items" work order are corrected in the [implementation program](../../docs/capstone-report/implementation-program.md). Downstream phases measure their baseline on the tree they start from.

## 1. Executive Summary

Asclexis (née HealthCentral) is a substantially implemented, well-tested, actively-developed local web application — not a scaffold, and not (yet) a desktop app. Patients import lab PDFs/images/FHIR exports into per-profile SQLCipher vaults, verify AI-extracted data through a human-in-the-loop workbench, view longitudinal trends, and chat with a local-LLM assistant that must cite every claim and is constitutionally barred from diagnosis. It is simultaneously Cal Poly Pomona CS4610 Senior Project (Danny Tran, Part 1 submitted 2026-05-15) studying the adoption of agentic software-engineering practice — and the repo shows it: 67% of its 355 commits are Claude-authored, with an entire development methodology (skills, machine-checked task ledger, behavioral eval gates, a written failure-mode memory) engineered as first-class artifacts.

**What works:** All five core flows are implemented end-to-end and wired — document→extract→verify→trends; assistant→agent-or-RAG→ModelRunner→`validate_response`; backup/restore with a live lifespan scheduler; ordered crypto-erase on profile delete; feedback→strict-redacted RL export. 18 routers, ~50 modules, 16 pages, ~1,245 collected backend tests, 155 vitest, 25 Playwright, and a 6-job CI that includes a 74-case behavioral gate for the assistant.

**What's unfinished:** packaging (zero desktop shell), the notification/reminder engine (built but never started — reminders cannot fire), recovery-code issuance UI for existing profiles, medication-correlation wiring, the NLI faithfulness axis (HC-M11, gated), and observability gaps (HC-M07).

**Biggest risks:** (1) The CI security gate fails open on main — a scanner crash reports "zero findings" and ships green; the fix exists only on an unmerged branch. (2) Two substantive unmerged branches carry fixes for the security gate, recovery-code UI, correlation wiring, and a care-task quote leak — main is behind its own repair work. (3) Documentation drift is systemic — ~40+ verified stale/contradictory claims, including several the repo's own `recurring-failures.md` predicts. (4) `datetime.utcnow()` invariant breach is systemic (~50 sites, not the 2 initially reported) [2026-09-27: 101 lines / 109 references / 30 product files — A-3] — latent naive/aware datetime bugs in timestamp-sensitive paths.

**Recommended direction:** Land the two unmerged branches (security-gate fail-closed first), then decide the notification scheduler's fate, then a focused doc-drift reconciliation pass — before new feature work. The repository's own failure-mode memory says this is the right order: every confirmed defect in its history coexisted with a green signal.

## 2. Repository Identity

| Field | Value |
|---|---|
| Product | Local-first, privacy-first "medical results companion": lab-PDF/image/FHIR import → extraction → human verification → trends → cited local-LLM assistant. Education only, never diagnosis. |
| Users | Primary: patients with frequent testing (author's motivation: mother's autoimmune labs); secondary: caregivers via separate vaults; implicit: CS4610 reviewers |
| Core workflows | ① upload→extract→verify→trends ② cited assistant chat (agent graph or legacy RAG) ③ record intelligence (timeline/care-tasks/highlights/med-reconcile/questions/pinboards/search/FHIR) ④ profile lifecycle incl. recovery codes + crypto-erase ⑤ feedback→redacted RL datasets |
| Hard boundary | No medical advice; `[YOUR_RESULTS:N]` / `[REFERENCE:N]` citations; PHI never leaves device except explicit HF model downloads |
| Research purpose | Evidence artifact for "developer → orchestrator" shift: vibe coding → meta-prompting → context engineering → harness engineering; the harness itself is the deliverable (extracted from `CS4610_Report_Demo/*.docx`) |
| Repo | `github.com/BrooklynD23/HealthCentral` (private; `gh` unauthenticated in this env) |

## 3. Repository Map

```
HealthCentral/
├── src/backend/          → FastAPI app: main.py (7-layer middleware, lifespan)
│   ├── api/              → 19 router files, ALL registered under /api/v1
│   ├── modules/          → ~50 feature modules + agent/ subpackage (graph,
│   │                       nodes, 8 read-only tools, guardrails, eval scorer)
│   ├── core/             → config, auth, security, sqlcipher_driver,
│   │                       profile_database, llm/ provider layer, model_runner,
│   │                       document_crypto, audit, time, rate_limiter
│   ├── models/ + migrations/{master,profile}/  → dual Alembic chains
│   ├── tests/            → 90 files, ~1174 test fns (1245 collected claim plausible)
│   └── scripts/          → backup.py, download_models.py (canonical), migrate, seeds
├── src/frontend/         → React 18 + TS strict + Vite 7 + Tailwind + TanStack
│                         Query + Zustand; 16 pages; services barrel; e2e/ Playwright
├── docs/                 → ~110 md files: plans/, agentic/, features/, roles/,
│                         compliance/, archive/, superpowers/ (plans+specs)
├── .claude/skills/       → 14 vendored Superpowers process skills (only
│                         committable .claude content — gitignore blocks the rest)
├── skills/               → 4 authored domain skills (asclexis-{backend,agent,
│                         guardrails,evals})
├── scripts/              → CI gates: agent_eval_gate, docs_lint (13 rules),
│                         security_gate, feature_list_lint, repo_hygiene_check
├── feature_list.json     → machine-checked task ledger (HC-M01..M24)
├── openwiki/             → STUB: README only, generated map never produced
├── .serena/              → LSP config + STALE memories (frozen Jan-2026)
├── CS4610_Report_Demo/   → course deliverables (.docx/.pdf + committed lock files)
├── .github/workflows/ci.yml → 6 jobs: docs-lint, backend, frontend, security,
│                              agent-evals, e2e
└── audit/                → NEW: this audit's HTML dashboard + this report
```

**Suspicious areas:** `scripts/download_models.py` (stale duplicate of the canonical backend script), `.vite/` stray dep-cache at root, `.bg-shell/`, `modules/test_intent.py` (name suggests test code in product dir — actually intent classification).

## 4. Current Architecture (verified in code)

- **Runtime:** uvicorn `127.0.0.1:8000` + Vite `:3000` dev proxy; `dev.ps1`/`dev.bat` one-click Windows bootstrap (winget Python/Node/Tesseract install). No packaged shell — CONFIRMED no Tauri/Electron/PyInstaller/Docker.
- **API:** 18 routers under `/api/v1` + `/health` + `/monitoring/metrics`; middleware stack CORS→CorrelationID→Headers→RateLimit→InputValidation→Audit→Timing.
- **Data:** unencrypted master SQLite (profile metadata, audit, knowledge base, backup schedules) + per-profile SQLCipher `vault.db` + sealed DEK + recovery-code copy; AES-GCM document files; dual Alembic chains.
- **Auth:** JWT HS256, bcrypt, bearer auth, per-profile `ProfileDbSession`; token revocation exists.
- **LLM:** `ModelRunner` facade → `core/llm/` factory → `LlamaCppProvider` (GGUF, default) | `OllamaProvider` (localhost-only) | opt-in external runners behind redaction gate. Exception: `modules/model_selector.py` imports `llama_cpp` directly — but reconciler proved its `interpret_with_model` path is dead code (zero callers); the invariant violation is real-but-dormant, not live.
- **Agent:** `modules/agent/` plan→act→reflect→draft→guard graph, `MAX_STEPS=5`, 8 registered read-only tools (2 unreachable via planner), metrics→monitoring. Default ON (`settings.py:19` — README wrongly says default OFF).
- **Embeddings/retrieval:** sentence-transformers + pure-Python cosine scan (FAISS removed 2026-07-01).
- **Exports:** CSV/JSON/doctor-summary/visit-prep/FHIR; in-memory artifact stores (downloads 404 after restart).

## 5. Intended Architecture (docs-ahead items)

| Intended | Gap |
|---|---|
| "Desktop app" (Tauri/PyInstaller/portable) | HC-M08a–d all pending; `.gitignore` pre-reserves `src-tauri/` |
| `.claude/agents/` subagent definitions (5 named) | Directory absent AND `.gitignore:44` would ignore it |
| OpenWiki generated repo map | README stub only |
| Notification reminder loop | Built, deliberately(?) unwired — rationale undocumented |
| NLI cross-encoder faithfulness | HC-M11 pending; `consistency_score` placeholder 1.0 |
| Postgres/multi-user `APP_MODE=server` | Reserved config branches; README calls it "a different product" |
| Observability (JSON logs, correlation→audit, /health e2e) | HC-M07 pending |

## 6. Capability Matrix

| System | Intended | Implemented | Tested | Documented | Deployed* | Confidence |
|---|---|---|---|---|---|---|
| Import/extract/verify pipeline | ✅ | ✅ | ✅ | ✅ | local | High |
| Trends/timeline/search | ✅ | ✅ | ✅ | partial | local | High |
| Assistant chat + citations | ✅ | ✅ | ✅ (74-case gate) | ⚠️ stale (default-OFF claim) | local | High |
| Governed agent graph | ✅ | ✅ | ✅ | ⚠️ "SCAFFOLD ONLY" docstring | local | High |
| Backup/restore + scheduler | ✅ | ✅ | ✅ | ✅ | local | High |
| Profile crypto-erase | ✅ | ✅ | ✅ | ✅ | local | High |
| Recovery codes | ✅ | ⚠️ backend only | ✅ | ⚠️ faq.md contradicts | local | High |
| Feedback→RL export | ✅ | ✅ | ✅ | ⚠️ archive docs stale | local | High |
| Med reconciliation | ✅ | ✅ endpoint | ✅ | ⚠️ missing endpoints.md row | local | High |
| Notifications/reminders | ✅ | ⚠️ engine built, never started | ⚠️ tests only | ⚠️ contradictory docs | — | High |
| Gamification | ✅ | ✅ | ✅ | ✅ | local | High |
| Desktop packaging | ✅ | ❌ | — | ✅ aspirational | — | High |
| Security gate CI | ✅ | ⚠️ fails open | ✅ on branch | ✅ | CI | Verified |
| Observability | partial | ⚠️ | ⚠️ | ✅ | local | Med |

\* Deployed = local-only by design; nothing is deployed anywhere.

## 7. Implementation Inventory (evidence-selected)

| System | Evidence |
|---|---|
| Upload→extract→observations | `api/documents.py` upload ~:400 → `_run_extraction_pipeline` :567 → `modules/extract*.py` / normalize / chunking / embeddings → `_create_chunks_and_embeddings` :827 → `_classify_and_extract_entities` :928 |
| Assistant dual path | `api/assistant.py` `POST /chat` ~:669 → `_serve_via_agent` :622 → `run_agent` (:657) or `RAGModule.query` (rag.py:1174) → `validate_response` :793 |
| Backup | `api/backup.py` 8 routes → `scripts/backup.py`; scheduler in `main.py` lifespan :66-81; restore gated on password + `RESTORE MY DATA` |
| Crypto-erase | `api/profiles.py` ~:773: phrase `DELETE MY HEALTH DATA` → sealed keys first → vault sweep → backup sweep → tombstone |
| RL export | `api/feedback.py` :311 `confirmed=true` → `modules/rl_dataset.py` strict redact → JSONL |
| Per-profile vaults | `core/profile_database.py`, `sqlcipher_driver.py`, `security.py` DEK sealing |
| Golden evals | `tests/agent/golden/` 74 cases; `agent/eval/scorer.py` 6 axes + 2 probes; `scripts/agent_eval_gate.py` |
| Dead code | `modules/analytics.py`, `modules/verify.py` (self-documents supersession), agent tools `retrieve_chunks` / `lookup_reference`, `interpret_with_model` |

## 8. Documentation vs Reality (reconciliation)

Full reconciler table had 40 rows [2026-09-27: not packaged — addendum A-4]. Headline entries:

| Area | Docs say | Code says | Class |
|---|---|---|---|
| Test baseline | evals.md "~620 tests, 4 axes" | 1,245 collected, 6-axis gate | STALE DOC |
| `.claude/agents/` | harness cites 5 subagents | absent + gitignore-blocked | CONTRADICTORY |
| README API table | 12 router groups | 18 mounted | DOCS BEHIND |
| Notifications | features-index "all implemented" | never wired | CONTRADICTORY + PARTIAL |
| Agent default | README "flag OFF, stubs" | `AGENT_ENABLED_DEFAULT=True`, live | CONTRADICTORY |
| FAISS | README stack + `.env.example` | removed; linear cosine scan | STALE DOC |
| INGEST-FHIR-001 | tracker OPEN | HC-M23 shipped | STALE DOC (tracker rot) |
| S06-SEC-003/004 | "STILL OPEN" review | both fixed in code | STALE DOC |
| `datetime.utcnow()` | "use `core.time.utcnow`" invariant | ~50 sites, 13 files [2026-09-27: 101 lines / 109 refs / 30 files — A-3] | CONTRADICTORY (systemic) |
| `faq.md:44` | "no password recovery" | recovery codes shipped | CONTRADICTORY |
| `.serena/memories/` | agent context | frozen Jan-2026, pre-`models/`, pre-Alembic | STALE DOC |
| `.gsd/KNOWLEDGE.md` | CONTRIBUTING says update it | doesn't exist, gitignored | STALE DOC |

Also MATCH notes worth keeping: `endpoints.md` genuinely is the API source of truth (all 18 groups; one missing row); `performance-scalability-review.md` verified accurate in full; RL-export "drift" claim was a false positive (archive docs are historical by design).

## 9. Development History

| Era | Dates | What happened |
|---|---|---|
| E0 Import | 2025-12-28–29 | +14,397-line skeleton lands in 2 commits |
| E1 Human build | Jan–Feb 2026 | SQLCipher vaults, profile auth, interpret_safety, dual Alembic, CI, redaction; 100% human |
| E2 Course quiet | Mar–May | 34 commits; CS4610 deliverables 05-15; Cursor-era dev.ps1 |
| E3 Agentic pivot | Jun 11–13 | Human lays the rails: LLM provider layer, RAG memory, RL pipeline, CLAUDE.md + AGENT.md authored |
| E4 Agent factory | Jun 23–Jul 31 | First Claude commit `caacd93`; sprints S0–S6; `.claude/skills` vendored (+5,286 lines); July = 55% of all history; HC-M12–24 via parallel phase orchestration w/ adversarial review; backup-defect storm Jul 30–31 (restore 400s, credential leak, delete-all-profiles) |
| E5 Rename/truth | Aug 1–4 | HealthCentral→Asclexis; `recurring-failures.md` born from the audit |
| E6 Backlog + research | Sep 7–10 | PR #18; two unmerged branches ahead of main |

- **Authorship:** Claude ≈ 67% of commits (239/355); ~228 Co-Authored-By trailers across 8 model variants; Codex adversarial reviews in commit bodies; 1 Cursor co-author; human role post-June = merge approval + owner sign-offs.
- **Two remote branches newer than main, both forked from HEAD:** `claude/asclexis-repo-audit-349pjq` (5 commits — verified: `RecoveryCodeCard.tsx`, `MedicationCorrelations.test.tsx`, `utils/correlation.ts` rewiring, care-task quote fix, FK-audit plan; +1,660/−102) and `claude/healthcentral-agentic-research-r1n54x` (21 commits [2026-09-27: 19 — addendum A-1] — verified `934a842` fail-open gate fix, Phi-4-mini tier, Wave-0 memory/cache defects, tier-capability UI; +15,050).

## 10. Open Work

- **Partially implemented:** notifications engine (inert), SEC-RECOV-001 UI, MED-CORR-001 wiring + `verified_only` divergence, HC-M02 (unrun manual test), S06-SEC-005 (`/health` exemption rationale stale).
- **Planned:** HC-M06 eval card, HC-M07 observability, HC-M08 packaging, HC-M09 MCP tools, HC-M11 NLI faithfulness, SQL-FK-001 audit (plan written on branch1), CITE-AGENT-001 page-data citations, SPRINT_7 LoRA (deferred).
- **Active (unmerged):** the two `claude/*` branches above.
- **Abandoned/stale:** `openwiki/` generation, `.gsd/` refs, FAISS, `Security-Revamp-*` CI trigger, `scripts/download_models.py` root copy.
- **Unclear:** why notification scheduler is deliberately unwired (no decision record; likely the locked-vault problem — inference, not evidence); whether `.claude/agents/` exists on owner's machine untracked.

## 11. Bugs & Technical Risks

**P0: none confirmed.**

**P1 — confirmed:**

1. **Security gate fails OPEN on main** — `security_gate.py` swallows `FileNotFoundError`/`JSONDecodeError` → `[]` → exit 0. A scan that never ran reports clean. Fix verified on unmerged branch (`934a842`, 7 tests). Impact: CI security signal is meaningless on main.
2. **Notification scheduler never started** — zero production callers (`start_notification_scheduler` :559, `register_profile_session` :148); lifespan wires only `backup_scheduler`. Medication reminders — a safety-adjacent feature — can never fire. Docs contradict each other on whether this is deliberate.
3. **In-memory export stores** — `api/export.py` module dicts; downloads 404 after restart; `pinboards.py` imports private `_packet_store`.
4. **`datetime.utcnow()` systemic breach** — ~50 sites/13 files [2026-09-27: 101 lines / 109 refs / 30 files — A-3] vs the `core.time.utcnow` invariant; latent naive/aware comparison bugs in reminders/adherence/verification timestamps.

**P2:** SEC-RECOV-001 stranded UX (doc says create a code while signed in; no signed-in UI exists on main); MED-CORR-001 dual implementations disagree on `verified_only` (UI silently uses looser rule); `/profiles/test/reset` misses 6 profile tables (ChatSession/ChatTurn/ResponseFeedback/CarePlanTask/Pinboard*); FK cascades inert (SQL-FK-001 — `PRAGMA foreign_keys` never set); `useIssueRecoveryCode` + `useCorrelations` hooks with zero callers; faithfulness `consistency_score=1.0` placeholder (disclosed, HC-M11); `POST /export/questions` returns unredacted `source_quote` in JSON (stays on-device, but is the likely target of branch1's quote-leak fix — interpretation of "leaves the device" needs pinning).

**P3:** dead modules `analytics.py`/`verify.py`; stale `agent/__init__.py` scaffold docstring; services barrel gaps (3 modules); duplicate `download_models.py`; unbounded audit retention; `.vite/` stray dir; committed Office lock files; `api/__init__.py` docstring names old product + 9/18 routers.

**Suspected, not confirmed:** runtime behavior of backup `skipped_locked`, agent cache rates — nothing was executed.

## 12. Agent / Skill / Workflow Inventory

| Layer | Contents | State |
|---|---|---|
| Constitution | CLAUDE.md (invariants, ask-first files, verification mandate) + AGENT.md (briefing, DoD) | Current, well-maintained |
| Process skills | `.claude/skills/` — 14 vendored Superpowers (TDD, systematic-debugging, plans, worktrees, code-review, etc.) | Current; 2 companion docs each avg |
| Domain skills | `skills/` — asclexis-backend/agent/guardrails/evals | Mostly current; `asclexis-agent` lists 5 tools (8 exist), `asclexis-evals` says 4 axes (6 exist) |
| Subagent definitions | `.claude/agents/` — PHANTOM: cited by harness.md/roadmap.md, absent, gitignore-blocked | Broken claim |
| Task ledger | `feature_list.json` (24 items, verification_steps, CI-linted) + TASK_LIST.md (797 lines) | Ledger current; tracker header stale, 2 rotted rows |
| Memory | `docs/agentic/progress.md` (session logs w/ outputs), `recurring-failures.md` (8 modes), implementation-log/, `.serena/memories/` | First three exemplary; serena memories stale |
| Gates | CI: docs_lint (13 DOC rules), feature_list_lint, security_gate (fail-open), agent_eval_gate (74 cases), e2e | Strong but one gate fails open |
| Hooks | None — no settings.json/PreToolUse in repo (CS4610 report claims AgentShield hook — user-level only, if it existed) | Absent from repo |
| Tooling | Serena MCP (`.mcp.json` pins 1.5.3), dev.ps1 bootstrap, e2e runners | Serena memories stale; dev.ps1 strong |

## 13. Harness Engineering Assessment

**Strengths (genuinely rare):** machine-checked feature ledger with per-item verification commands; docs_lint enforcing Last-Updated/Historical-banner/link-resolution/index-freshness in CI; behavioral eval gate with absolute bars; `route_client` harness built specifically to defeat the dependency-bypass blind spot; `recurring-failures.md` — a living postmortem memory that correctly predicted several of this audit's own findings; authority ordering (hand-docs > generated docs); honest in-progress statuses (HC-M02 stays open because a manual test never ran).

**Weaknesses:** enforcement is doc-level + CI-level only — zero hooks despite the course report claiming hook-based PHI enforcement (that claim is not repo-evidenced); phantom `.claude/agents/` layer + the gitignore that makes it impossible; stale Serena memories functioning as a second, contradicting context source that docs_lint never checks; lint configs (ruff/eslint/mypy) configured but ungated; no coverage thresholds; no PR-size guard.

**Where harness engineering would pay off:** a docs_lint rule for `.serena/` freshness or deleting the memories; one-canonical-path enforcement for duplicated scripts (recurring-failure #6 is codified in prose but not enforced); completed-plan markers in `docs/superpowers/plans/`; extending DOC rules to catch tracker-row rot like INGEST-FHIR-001.

## 14. Agentic-SWE Maturity Score

| Capability | Level | Evidence |
|---|---|---|
| Context engineering | L4 | AGENT.md briefing + roles index + link graph + initial_prompt mirroring |
| Agent specialization | L1 | claims exist (5 named agents); none committed; gitignore-blocked |
| Task decomposition | L3 | feature_list.json + phase plans + sprint docs; decomposition proven at scale in July |
| Reusable skills | L4 | 18 skills, routing table, vendored-vs-authored split documented |
| Human→agent delegation | L4 | 67% agent-authored; documented owner sign-offs |
| Agent→agent delegation | L2 | July parallel orchestration real but ephemeral (commit evidence, no persistent roster) |
| Verification/testing | L4 | HTTP-level route tests, eval gate, honest baselines, evidence-before-claims culture |
| Repo discoverability | L3 | INDEX/link-graph/endpoints.md; openwiki stub; serena stale |
| Guardrails | L3 | invariants + protected-files + evals; no hooks; fail-open gate |
| Specification quality | L3 | PRDs/plans/specs with archive discipline; drift in leaf docs |
| Code-review workflow | L3 | cross-vendor adversarial review evidenced in commits ("address Codex review", wip-recovery commits) |
| Observability of agent work | L4 | progress.md with command outputs; session notes; implementation-log |

**Overall: L3 structured, trending L4** — the harness is the strongest part of this repo, but its two weak spots (phantom agent layer, fail-open gate) sit exactly where claims exceed evidence.

## 15. Top Contradictions

1. **Security gate:** green signal that can't fail vs the repo's own gospel of verification (verified: pre-fix script exits 0 on missing reports).
2. **Notification scheduler:** "implemented" (features-index) vs "deliberately unwired" (architecture) vs reality (dead feature shipped).
3. **`.claude/agents/`** cited as portfolio evidence vs absent + impossible-to-commit under `.gitignore`.
4. **`modules/agent/__init__.py` "SCAFFOLD ONLY"** vs the default-ON production chat path — an agent trusting that docstring could bypass a live safety path.
5. **Recovery UX dead end:** `faq.md` "no password recovery" + RecoverProfile "create a code while signed in" + zero UI entry points for existing profiles on main.
6. **Test numbers:** "~620" vs "~1160" vs "1245" across three docs — the exact failure mode recurring-failures #3 warns about, recurring in the eval doc itself.
7. **CS4610 report** claims hook-based PHI enforcement + AgentShield wiring — no hooks exist in the repo (likely user-level config, unverifiable; report claims outrun committed evidence).

## 16. Recommended Next Workstreams

| # | Workstream | User value | Risk reduction | Dependency value | Research value | Effort | Urgency |
|---|---|---|---|---|---|---|---|
| 1 | Land both unmerged branches (gate fail-closed, recovery UI, correlation wiring, quote fix) | Med | **HIGH** | High | Med | Low | **Immediate** |
| 2 | Decide notification scheduler: wire (locked-vault problem) or remove | Med | Med | Med | High | Med | High |
| 3 | Doc-drift reconciliation sprint (evals.md, tracker rows, faq.md, serena memories, `.claude/agents` claim) | Low | Med | High | High (dogfoods recurring-failures) | Low | High |
| 4 | `datetime.utcnow()` → `core.time.utcnow` migration + lint rule | Med | Med | Med | Low | Med | Med |
| 5 | HC-M06 extraction eval card | Med | Med | Med | High (flagship DS artifact) | Med | Med |
| 6 | HC-M08a packaging decision spike | Med | Low | High | Med | Low-Med | Med |
| 7 | Export-store persistence + audit retention | Med | Med | Low | Low | Med | Low |
| 8 | UTC/FK systemic audits (SQL-FK-001 plan exists on branch1) | Med | Med | Med | Low | Med | Med |

## 17. Recommended Immediate Implementation Slice

**Goal:** Land `claude/healthcentral-agentic-research-r1n54x` and `claude/asclexis-repo-audit-349pjq` onto main — review, resolve any drift since Sep 10, merge.

**Why now:** The single highest-severity confirmed defect (fail-open security gate) plus the two tracked PARTIALs (SEC-RECOV-001, MED-CORR-001) and a PHI-adjacent quote fix are already written, tested (7+ new backend tests, 2 new vitest suites), and sitting 21+5 [2026-09-27: 19+5 — A-1] commits ahead of a clean main. Every day unmerged, CI's security signal is cosmetic.

**Scope:** fetch + diff both branches → conflict resolution → full gate suite (pytest, tsc, vitest, docs_lint, feature_list_lint, security_gate now failing closed, agent_eval_gate) → merge PRs → verify post-merge main.

**Non-goals:** no new features, no notification-scheduler decision, no doc-drift sweep, no packaging.

**Dependencies:** human merge approval (repo convention: human merges); WSL caveat — run pytest after clearing `__pycache__`, frontend toolchain on Windows.

**Files/subsystems:** `scripts/security_gate.py`, `ci.yml`, `core/external_runner.py` + memory/cache fixes, `modules/model_selector.py` / tiers, frontend `RecoveryCodeCard` / `MedicationDetail` / `correlation.ts` / `SettingsPage` / `RecoverProfile`, ~120 files net +15k lines (mostly docs/tests on branch2 — the code diff is much smaller).

**Tests required:** the branches carry their own (HC-SECGATE-001..007, tier-caps, verify-model-repos, MedicationCorrelations, RecoveryCodeCard); full suite re-run post-merge.

**Completion criteria:** security gate demonstrably fails on a poisoned report; recovery-code issuance reachable from Settings; correlations served by endpoint not utils; suite counts ≥ baseline.

**Risks:** branch2 is large (+15k lines — review cost); "care-task quote leak" fix interpretation needs pinning to a specific surface; Phi-4-mini tier swap is a product change bundled with fixes — may want splitting.

**Skills to use:** `verification-before-completion`, `requesting-code-review`, `finishing-a-development-branch`, `asclexis-backend`. New agent/skill warranted: no — existing coverage suffices; this is itself evidence for the research question (orchestrating merge of agent-produced work).

## 18. Repository Recovery Roadmap

**Immediate (this week):** land the two branches (§17); fix `faq.md` password-recovery answer; run the FK audit (plan already written on branch1).

**Short-term:** decide notification scheduler fate; reconcile the ~40 stale-doc items (evals.md numbers, tracker rows, `.claude/agents/` claim — either create+unignore or correct docs); refresh or delete `.serena/memories/`; `utcnow()` migration; add `npm run build` to CI or fix the gates doc; delete stale `scripts/download_models.py`.

**Medium-term:** HC-M06 eval card + HC-M07 observability; HC-M08 packaging spike (the "desktop app" claim needs a decision); HC-M11 NLI faithfulness (gated — owner sign-off); hooks layer if hook claims are to become real; lint/coverage gates.

## 19. Senior-Project Research Opportunities

Measurable artifacts this repo already produces:

- **Human→agent shift, quantified:** commit authorship time series (Dec–May: 100% human; Jun 23+: ~96% Claude) — a directly computable "developer→orchestrator" curve for the report.
- **Defect taxonomy:** `recurring-failures.md` + the July backup-defect storm (3 commits fixing cascading bugs) + the fail-open gate = a catalog of agentic-specific failure modes (verification theater, report-as-fact, contaminated-tree gates) with commit-hash evidence.
- **Harness-vs-drift correlation:** doc-drift items cluster exactly where no lint rule exists (serena memories, tracker rows, `evals.md` counts) vs near-zero drift where gates run (INDEX freshness, feature ledger). A/B-able claim: gates prevent drift; prose doesn't.
- **This audit itself:** 6-agent orchestration cost/benefit — reconciler caught 3 sibling-agent errors (model_selector dead-path, doctor-summary, barrel severity), demonstrating why "trust no single agent" matters; measurable as claims-verified / claims-corrected ratios.
- **The phantom layer:** `.claude/agents/` cited as evidence while impossible under `.gitignore` — a clean case study of specification drift in harness docs themselves.
- **CS4610 report vs repo:** the report claims hook-based enforcement unverifiable in-repo — honest Part-2 material on "claims vs committed artifacts."
- **Before/after metrics available:** test counts per era, commit cadence (July spike = orchestration era), PR-size distribution, per-sprint checklist/retro docs in `docs/agile/`.

## 20. Unanswered Questions (require owner input)

1. Why is the notification scheduler deliberately unwired — locked-vault constraint, unfinished, or superseded? No decision record exists.
2. Do `.claude/agents/` and the hook layer claimed in the CS4610 report exist at user level on your machine? If yes, should they be committed (requires unignoring)?
3. Is a CS4610 Part 2 planned, and do the two September research branches feed it? Should `agentic-research-r1n54x` merge as-is or split (fixes vs the Phi-4-mini product change)?
4. Post-course product direction: is desktop packaging (HC-M08) still the goal, or has the repo become primarily a research artifact?
5. Are the doc timeline dates (through Sep 2026) a fictional project calendar or real wall-clock?
6. HIPAA-adjacent deferred decisions (MFA, key rotation, pen test, audit retention): still gated on owner, or abandoned post-course?

---

**Artifacts produced:** `audit/repository-audit-dashboard.html` (32KB, self-contained, 8 sections, severity filters) [2026-09-27: present, untracked; pre-reconciliation snapshot — A-4] and this report at `audit/2026-09-25/Devin-Audit-report.md`. No repo files were modified; `git status` shows only `?? audit/`.

**Methodology note** [2026-09-27: provenance not packaged — A-5]**:** every load-bearing claim in this report was either verified by two independent agents or confirmed directly in git/source (security-gate fail-open, scheduler call-sites, branch diffs, gitignore block, CS4610 docx contents). Where evidence was unreachable (GitHub issues — repo is private and `gh` is unauthenticated; runtime behavior — no tests were executed), it's marked UNKNOWN rather than asserted.

---

## 21. Owner Q&A — Orchestrator Handoff Decisions

*Recorded 2026-09-25. Answers from the repository owner to resolve §20 and set the next workstream.*

| # | Question | Owner answer |
|---|---|---|
| Q1 | Notification scheduler: wire it, remove it, or keep inert? | **Wire it up** — solve the locked-vault constraints and start the scheduler in lifespan. |
| Q2 | `.claude/agents/` + hooks: commit user-level config, or correct the docs? | **Not sure** — orchestrator should check `~/.claude/` on the owner's machine and report what exists before deciding commit-vs-doc-fix. |
| Q3 | Unmerged branches: merge `agentic-research-r1n54x` as-is, or split fixes from the Phi-4-mini product change? | **Merge both as-is** — land both branches wholesale; fastest path to fail-closed gate. |
| Q4 | Product direction: desktop packaging (HC-M08) still the goal, or research artifact? | **Both** — continue product work AND mine it for research. HC-M08 stays on the roadmap. |
| Q5 | Doc timeline dates through Sep 2026: real wall-clock or fictional calendar? | **Real wall-clock** — dates reflect actual work days. |
| Q6 | HIPAA-adjacent deferred decisions (MFA, key rotation, pen test, audit retention): still gated on owner, or abandoned? | **Still want them** — keep gated; orchestrator should prep them for owner review, not implement unilaterally. |
| Q7 | First workstream for the next orchestrator: which of §16 should go first? | **Land the branches** — §17 slice first (fail-closed gate, recovery UI, correlation wiring, quote fix). |

### Decision summary for the next orchestrator

1. **Immediate:** land `claude/asclexis-repo-audit-349pjq` + `claude/healthcentral-agentic-research-r1n54x` onto main as-is (§17 slice). No splitting.
2. **Then:** wire the notification scheduler — owner confirmed it should run; the locked-vault problem is the design constraint to solve.
3. **Investigate:** `~/.claude/` on the owner's machine for the phantom `.claude/agents/` + hooks layer; report findings before touching docs or `.gitignore`.
4. **Keep gated:** HIPAA-adjacent items (MFA, key rotation, pen test, audit retention) are still wanted — prep for owner review only.
5. **Context:** doc timeline dates are real wall-clock; desktop packaging remains a product goal alongside the research-artifact role.

---

## 22. Handoff Prompt (paste-ready for the next orchestrator)

```
You are the orchestrator for the Asclexis repo (local-first medical results
companion; FastAPI + per-profile SQLCipher vaults + React/TS frontend).
Working dir: /mnt/c/Users/DangT/Documents/GitHub/HealthCentral
Repo rules: read CLAUDE.md and AGENT.md first — they are binding. Route tests
must go through HTTP (tests/support/routes.py::route_client). Run every
verification and paste real output; "I believe it passes" is not done.
Re-read docs/agentic/recurring-failures.md before claiming done.

Full context: audit/2026-09-25/Devin-Audit-report.md (repo audit + owner
decisions, recorded 2026-09-25, main @ 40f590e).

OWNER-APPROVED WORK ORDER:

1. LAND THE TWO UNMERGED BRANCHES (highest priority, owner confirmed):
   - claude/asclexis-repo-audit-349pjq (5 commits): RecoveryCodeCard UI,
     MedicationCorrelations tests, utils/correlation.ts rewiring, care-task
     source_quote leak fix, SQL-FK-001 audit plan.
   - claude/healthcentral-agentic-research-r1n54x (21 commits [2026-09-27: 19, A-1]): security-gate
     fail-closed fix (934a842 + 7 tests), Wave-0 memory/cache defects,
     Phi-4-mini tier, tier-capability UI.
   - Merge both AS-IS (owner decision — do not split the Phi-4-mini change).
   - Steps: git fetch → diff each vs main → resolve drift since Sep 10 →
     run full gate suite (pytest, tsc, vitest, docs_lint, feature_list_lint,
     security_gate must now FAIL on a poisoned report, agent_eval_gate) →
     open PRs → STOP for human merge approval (repo convention: human merges).
   - Post-merge: re-run suite on main; verify recovery-code issuance is
     reachable from Settings and correlations are served by the endpoint,
     not utils/correlation.ts.
   - WSL caveat: clear __pycache__ before pytest; run frontend toolchain
     (tsc/vitest) on Windows — node_modules may be unusable under WSL.

2. WIRE THE NOTIFICATION SCHEDULER (owner confirmed it should run):
   - modules/notifications: start_notification_scheduler (:559) and
     register_profile_session (:148) have zero production callers; lifespan
     wires only backup_scheduler.
   - The design constraint to solve is the locked-vault problem: reminders
     need profile data, but vaults may be closed when a reminder fires.
     Follow backup_scheduler's pattern — it records skipped_locked honestly.
   - Fix the contradictory docs (features-index says "all implemented",
     architecture doc says "deliberately unwired") in the same commit.
   - This is safety-adjacent (medication reminders): be conservative, ask
     before touching anything under modules/interpret_safety.py,
     redaction.py, faithfulness.py, verifier_agent.py.

3. INVESTIGATE THE PHANTOM LAYER (owner unsure):
   - Check ~/.claude/ on this machine for agents/ and any hook config
     (settings.json, PreToolUse, "AgentShield"). The CS4610 report claims
     5 named subagents + hook-based PHI enforcement; repo has neither and
     .gitignore:44 would block .claude/agents/.
   - Report findings to the owner BEFORE deciding: commit them (requires
     unignoring) vs correct harness.md/roadmap.md claims. Do not edit
     .gitignore or docs unilaterally.

4. THEN, IN ORDER (after 1–3):
   - Doc-drift sweep: ~40 stale items. Headliners: evals.md "~620 tests/
     4 axes" (real: 1245/6), README "agent flag OFF" (real: default ON),
     faq.md:44 "no password recovery" (recovery codes shipped), INGEST-FHIR-001
     tracker row, S06-SEC-003/004 "STILL OPEN", FAISS references, stale
     .serena/memories/ (refresh or delete).
   - datetime.utcnow() → core.time.utcnow migration: ~50 sites, 13 files [2026-09-27: A-3];
     add a lint rule so it can't regress.
   - Run SQL-FK-001 audit (plan exists on branch1): PRAGMA foreign_keys
     is never set — FK cascades are inert.
   - Fix /profiles/test/reset missing 6 profile tables (ChatSession,
     ChatTurn, ResponseFeedback, CarePlanTask, Pinboard*).

5. KEEP GATED — PREP ONLY, OWNER SIGN-OFF REQUIRED:
   - HIPAA-adjacent: MFA, key rotation, pen test, audit-retention policy.
   - HC-M11 NLI faithfulness (consistency_score=1.0 placeholder is
     disclosed; replacing it is gated).

HARD RULES (violations = broken trust):
- No network calls in product code paths; Ollama stays localhost-only.
- All LLM calls through ModelRunner facade. Never import llama_cpp in
  feature code (modules/model_selector.py's dead interpret_with_model is
  known — leave it or remove it as dead code, do not extend it).
- Per-profile data only via ProfileDbSession — never master get_db().
- Anything exportable passes through modules/redaction.py first.
- Audit log every route touching documents/observations/profile data.
- Python 3.11+ only; timestamps only via core.time.utcnow.
- New profile-table schema = new migration in migrations/profile/ (dual
  Alembic chains — master and profile are separate).
- Baseline: 1245 backend tests collected. test_api_rag_index_002b fails
  locally without an embedding model — environmental, do NOT lower the
  0.7 threshold. If collected count differs from 1245, update the baseline
  docs in the same commit.

KNOWN TRAPS (from recurring-failures.md + this audit):
- Green suite ≠ correct: route tests calling handlers directly bypass
  FastAPI Depends(). Use route_client for auth/scoping/status assertions.
- Filename-level assertions can't see data leaking inside files.
- security_gate.py on main swallows FileNotFoundError/JSONDecodeError →
  exit 0. Verify the gate can actually fail before trusting its green.
- In-memory export stores (api/export.py): downloads 404 after restart;
  pinboards.py imports private _packet_store.

DELIVERABLE: work items in order, one feature branch per item, commits as
fix(scope):/feat(scope):/docs:. Log non-trivial work in
docs/features/TASK_LIST.md Session Notes. Stop at merge approval and at
every gated item — the owner merges and signs off personally.
```

---

## 23. Plan Index (generated 2026-09-25, 8 parallel agents)

Detailed executable plans for every §22 work item, written in `writing-plans` format (TDD checkbox tasks, exact paths, verification commands). Investigations were code-verified against main @ `40f590e`; several corrected audit claims (noted per plan).

| Plan | File | Lines | Headline finding vs the audit |
|---|---|---|---|
| Merge branches | `plans/01-merge-branches.md` | 495 | Branch B first (fail-closed gate first); real conflicts verified via `merge-tree` (AGENT.md, CLAUDE.md, INDEX, link_graph, recurring-failures); `gh` IS authenticated (audit said not); merged baseline ≈1,291 |
| Notification scheduler | `plans/02-notification-scheduler.md` | 1,018 | Choke point found — register/unregister in `open/close_profile_database_on_login` covers all 8 vault call sites; bonus defect: `medication_name` logged at INFO (:517-520) — PHI into plaintext logs |
| Phantom layer | `plans/03-phantom-layer.md` | 191 | 5 claimed agents exist nowhere (repo, git history, or user level); AgentShield never installed; Branch-B doc fix already ~80% built on the unmerged branch (`7b2ff1f`) — recommended |
| Doc-drift sweep | `plans/04-doc-drift-sweep.md` | 687 | 16-task sweep; two audit claims were wrong on spot-check (endpoints.md row exists; openwiki README already honest) |
| utcnow migration | `plans/05-utcnow-migration.md` | 468 | Scope is 101 sites/30 files [2026-09-27: 101 lines = 109 refs — A-3] (audit said ~50/13); `core.time.utcnow` is naive — drop-in swap, no shim; aware-`.now()` hazards live elsewhere (`gamification.py:148`, `badge_evaluator.py:84`, `source_authority.py:216`) |
| SQL-FK-001 | `plans/06-sql-fk-audit.md` | 415 | Pragma set nowhere (4 engine sites); branch1 doc already inventoried 20 FKs + owner-approved constraint changes; new orphan: `delete(Observation)` orphans `lab_interpretations` today |
| test/reset tables | `plans/07-test-reset-tables.md` | 562 | 23 profile models exist — 6 missed + `badge_definition` must be *excluded* (seed data); `route_client` needs `profile_name`/`profile_db` params to test it at all |
| Gated items packet | `plans/08-gated-items-review-packet.md` | 292 | Password is also the DEK-unseal secret → MFA brief reframed to step-up re-auth; no rekey exists at all (`change_password` re-seals the same DEK); audit rows also echo to plaintext `logs/asclexis.log` |

**Meta-finding worth the report:** the planning pass itself caught 4 errors in this audit (gh auth status, Wave-0 file list, endpoints.md row, utcnow count) — the same "trust no single agent" pattern the audit found in its own reconciler.
