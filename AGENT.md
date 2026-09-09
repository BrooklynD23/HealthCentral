# AGENT.md — Asclexis

Onboarding for any AI agent or new contributor. Behavioral rules are in [CLAUDE.md](CLAUDE.md). Treat this file like a new-hire briefing: what the project is, where things live, how to verify your work.

## What this is

Local-first, privacy-first desktop app: patients import lab PDFs/medical documents, verify extracted data, see longitudinal trends, and chat with a local-LLM assistant that explains results with citations. All data stays on-device (SQLCipher-encrypted per-profile DBs). Education only — never diagnosis or treatment advice.

## Stack & layout

- **Backend** `src/backend/` — Python 3.11+, FastAPI, SQLAlchemy, Alembic (dual chains), llama-cpp-python (lazy/optional import).
  - `api/` — routes (registered in `main.py`): documents, observations, assistant, memory, feedback, model_settings, profiles…
  - `modules/` — feature logic: `ingest`/`extract*` (document pipeline), `rag` (retrieval + prompt composition), `normalize`/`glossary` (analyte synonyms), `interpret*`/`faithfulness`/`verifier_agent`/`redaction` (safety — do not touch casually), `rl_dataset` (DPO/GRPO export)
  - `core/` — config, security, db, `time` (use `core.time.utcnow`), `llm/` (provider layer: `LlamaCppProvider` default, `OllamaProvider` localhost-only, `factory.get_provider()`), `model_runner` (stable facade — the only LLM entry point for feature code)
  - `models/` — SQLAlchemy; profile-scoped tables (observations, chat_sessions, chat_turns, response_feedback) live in per-profile DBs
  - `migrations/master/` + `migrations/profile/` — separate Alembic chains (see `docs/plans/implementation-log/2026-02-04_alembic-dual-migrations.md`)
- **Frontend** `src/frontend/` — React + Vite + TS, Tailwind, React Query, Zustand.
  - `src/pages/` (TrendsDashboard, ExplainAssistant, VerificationWorkbench, SettingsPage…), `src/services/` (API client + hooks; export everything through `services/index.ts` barrel), `e2e/` Playwright
- **Docs** `docs/` — start at [`docs/00_architecture_plans_index.md`](docs/00_architecture_plans_index.md) (canonical order) or [`docs/roles/00_roles_index.md`](docs/roles/00_roles_index.md) (domain-based "which doc for X"); `docs/plans/` (active + historical plans/decisions log, incl. `implementation-log/` for point-in-time notes). Skills live in `.claude/skills/` and `skills/` — see [Skills](#skills) below.
- **Generated repo map** [`openwiki/`](openwiki/README.md) — OpenWiki-generated navigation for coding agents (where code lives, how files connect). Advisory only: it never overrides CLAUDE.md, this file, or `docs/`. See `openwiki/README.md` for regeneration commands and review rules.

## Skills

Two directories, different purposes. `.claude/skills/` holds vendored **process**
skills; `skills/` (no dot) holds this project's **domain** skills. Invoke by name.

| Skill | Reach for it when |
|---|---|
| `test-driven-development` | Implementing any feature or bugfix, before writing implementation code |
| `systematic-debugging` | Encountering any bug, test failure, or unexpected behavior, before proposing fixes |
| `writing-plans` | You have a spec or requirements for a multi-step task, before touching code |
| `executing-plans` | You have a written implementation plan to execute in a separate session with review checkpoints |
| `subagent-driven-development` | Executing an implementation plan whose tasks are independent, in the current session |
| `brainstorming` | Before any creative work — creating features, building components, adding functionality, or modifying behavior |
| `verification-before-completion` | About to claim work is complete, fixed, or passing, before committing or creating PRs — evidence before assertions |
| `requesting-code-review` | Completing a task or major feature, or before merging, to verify the work meets requirements |
| `receiving-code-review` | Receiving review feedback, before implementing suggestions — especially if it seems unclear or technically questionable |
| `dispatching-parallel-agents` | Facing 2+ independent tasks with no shared state or sequential dependencies |
| `using-git-worktrees` | Starting feature work that needs isolation from the current workspace, or before executing a plan |
| `finishing-a-development-branch` | Implementation is complete and tests pass, and you need to decide how to integrate the work |
| `writing-skills` | Creating a new skill, editing an existing one, or verifying a skill works before deployment |
| `using-superpowers` | Starting any conversation — establishes how to find and use skills before any other response |
| `asclexis-backend` | Backend routes, feature modules under `src/backend/modules/`, SQLAlchemy models, Pydantic schemas, the SQLCipher per-profile vault, the dual Alembic chains, security/monitoring middleware, LLMOps (semantic cache, model tiers, llama.cpp serving, timing/token tracking), or the proof bundle |
| `asclexis-agent` | Anything under `src/backend/modules/agent/` — the graph runner, plan/act/reflect/draft nodes, the tool registry, read-only tools over the profile vault, the step budget, audit hooks, or wiring the agent into the `/assistant/` route |
| `asclexis-guardrails` | The guard node, advice classifier, abstention/escalation templates, groundedness and claim-to-source mapping, confidence thresholds, or the PHI redaction gate before any opt-in external LLM call |
| `asclexis-evals` | Golden eval cases, synthetic vault states, the four scoring axes (groundedness, citation accuracy, abstention correctness, advice leakage), or the CI workflow that gates PRs on agent behavior |

The `.claude/skills/` directory also vendors
[mattpocock/skills](https://github.com/mattpocock/skills)' engineering set
(18 skills, MIT). The ones that fill a genuine gap here:

| Skill | Reach for it when |
|---|---|
| `improve-codebase-architecture` | Scanning for deepening opportunities across a module or the whole repo, then working through the one you pick |
| `codebase-design` | Designing or improving a module's interface, deciding where a seam goes, making code more testable |
| `domain-modeling` | Working on codebase terminology, a CONTEXT.md, or recording an ADR |
| `wayfinder` | Navigating an area of the codebase you don't know yet |
| `triage` / `to-tickets` / `to-spec` | Turning a plan or a pile of findings into independently-grabbable work items |
| `prototype` | Sanity-checking whether a state model or UI shape feels right, throwaway |

Four of that set overlap with the superpowers skills above (`tdd`,
`diagnosing-bugs`, `code-review`, and the `to-spec`/`to-tickets` pair).
**Prefer the superpowers skill by default** — CLAUDE.md and the definition of
done below are written against its vocabulary. The disambiguation table is in
[`.claude/skills/README.md`](.claude/skills/README.md).

Each skill's full description is the `description:` front matter in its own
`SKILL.md`. For where the two directories come from and why they are separate,
see [`.claude/skills/README.md`](.claude/skills/README.md) and
[`skills/README.md`](skills/README.md).

## Commands (Windows is the native dev environment)

```powershell
.\dev.ps1                                  # full stack, auto-selects free ports
cd src/backend; python -m pytest tests/ -p no:cacheprovider -q   # backend tests (1269 collected; 1269 pass in CI, 1268 without an embedding model)
cd src/frontend; npm run dev               # frontend only
cd src/frontend; npx tsc --noEmit; npm run build; npx vitest run
cd src/frontend; npx playwright test       # e2e
cd src/backend; python scripts/download_models.py list     # GGUF tiers + ollama pull tags
cd src/backend; python scripts/download_models.py verify   # check every tier repo exists on HuggingFace (needs network)
```

Known env-only failure: `test_api_rag_index_002b` needs a real embedding model, so it fails locally and passes in CI. WSL/9p mounts: clear `__pycache__` before pytest (stale bytecode causes phantom results); `node_modules` may be unusable — run frontend toolchain on Windows.

## Key flows (trace these before changing them)

1. **Document → graph**: upload (`api/documents`) → `modules/ingest` → `modules/extract` (date extraction is format-sensitive; canonical ISO-8601; collection-label priority) → observations stored per-profile → `api/observations` trends → `TrendsDashboard`. Undated observations are listed but excluded from time-series; `POST /{id}/reprocess` re-extracts.
2. **Assistant chat**: `api/assistant` → ChatSession/ChatTurn persistence → `modules/rag`: retrieves user observations (`[YOUR_RESULTS:N]`), reference knowledge (`[REFERENCE:N]`, auto-seeded at startup from `scripts/seed_knowledge_base.py`), memory items + bounded session history (labeled non-citable) → ModelRunner → `validate_response()` + safety guards. No-LLM fallback must stay functional.
3. **Feedback → RL datasets**: thumbs/corrections (`api/feedback`, upsert per turn) → `modules/rl_dataset` export (DPO pairs, SFT, GRPO reward JSONL) — redaction mandatory, explicit confirmation required.
4. **Backup → restore**: `api/backup` (create/verify/download/restore/prune) → `scripts/backup.py` engine → per-profile `backups/{profile_id}/`. Backups are **deliberately unredacted** (a redacted backup cannot be restored) and are the one export-shaped path that is. Restore is profile-scoped: vault and sealed keys verbatim, only this profile's master row re-applied. `modules/backup_scheduler` runs due backups from the lifespan task and records `skipped_locked` honestly when a vault is closed.
5. **Profile lifecycle**: create (`api/profiles`) issues a one-time recovery code sealing a *second copy of the same DEK* (`SEC-RECOV-001`); `DELETE /profiles/{id}` is an ordered crypto-erase — sealed keys first as the commit point, then the vault sweep, then the backup sweep, then one master transaction that purges audit rows and writes an anonymized tombstone.

## Configuration

`.env` from `config/.env.example`. Notable: `LLM_PROVIDER` (`llama_cpp`|`ollama`), `LLM_MODEL`, `OLLAMA_BASE_URL` (must stay localhost), `ASSISTANT_MEMORY_ENABLED` (default true; ANDed with per-profile toggle and request flag).

## Definition of done

A task is done when all of the following are true **and you have seen the output
that proves each one**:

- Tests written or updated, and the new ones observed failing before the fix.
- `cd src/backend && python -m pytest tests/ -p no:cacheprovider -q` shows no new
  failures against the baseline above.
- `cd src/frontend && npx tsc --noEmit` is clean and `npx vitest run` passes.
- The app boots: `cd src/backend && python -c "from main import app"`.
- Every hard invariant in [CLAUDE.md](CLAUDE.md) still holds.
- Non-trivial work logged in `docs/features/TASK_LIST.md` Session Notes, or a
  dated file under `docs/plans/` for a substantial standalone plan.
- [`docs/agentic/recurring-failures.md`](docs/agentic/recurring-failures.md)
  re-read, and any new instance of a listed failure mode recorded there.

"I believe these pass" is not done. Run them. Every failure mode in
`recurring-failures.md` shipped alongside a passing signal.
