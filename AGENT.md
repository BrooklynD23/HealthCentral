# AGENT.md — Asclexis

Onboarding for any AI agent or new contributor. Behavioral rules are in [CLAUDE.md](CLAUDE.md). Treat this file like a new-hire briefing: what the project is, where things live, how to verify your work.

## What this is

Local-first, privacy-first desktop app: patients import lab PDFs/medical documents, verify extracted data, see longitudinal trends, and chat with a local-LLM assistant that explains results with citations. All data stays on-device (SQLCipher-encrypted per-profile DBs). Education only — never diagnosis or treatment advice.

## Stack & layout

- **Backend** `src/backend/` — Python 3.11+, FastAPI, SQLAlchemy, Alembic (dual chains), llama-cpp-python (lazy/optional import).
  - `api/` — routes (each router included in `api/__init__.py`; `main.py` mounts that aggregate at `/api/v1`): documents, observations, assistant, memory, feedback, model_settings, profiles…
  - `modules/` — feature logic: `ingest`/`extract*` (document pipeline), `rag` (retrieval + prompt composition), `normalize`/`glossary` (analyte synonyms), `interpret*`/`faithfulness`/`verifier_agent`/`redaction` (safety — do not touch casually), `rl_dataset` (DPO/GRPO export)
  - `core/` — config, security, `database` (master) / `profile_database` (vaults) / `migrations` (both Alembic runners), `auth`, `audit`, `time` (use `core.time.utcnow`), `llm/` (provider layer: `LlamaCppProvider` default, `OllamaProvider` localhost-only, `factory.get_provider()`), `model_runner` (stable facade — the only LLM entry point for feature code)
  - `models/` — SQLAlchemy; profile-scoped tables (observations, chat_sessions, chat_turns, response_feedback) live in per-profile DBs
  - `migrations/master/` + `migrations/profile/` — separate Alembic chains (see `docs/plans/implementation-log/2026-02-04_alembic-dual-migrations.md`)
- **Frontend** `src/frontend/` — React + Vite + TS, Tailwind, React Query, Zustand.
  - `src/App.tsx` (every route; `/` redirects to `/overview`), `src/components/layout/navConfig.ts` (every nav name, sidebar groups and the phone tab bar), `src/pages/` (OverviewPage, ResultsPage, ExplainAssistant, VerificationWorkbench, SettingsPage…; `/trends` and `/interpret` redirect to `/results`), `src/services/` (API client + React Query hooks, one file per backend area; export everything through the `services/index.ts` barrel — `backup`, `donation`, `interpretations` and `medications` are not re-exported there today), `e2e/` Playwright. Map: [`docs/architecture/frontend.md`](docs/architecture/frontend.md)
- **Docs** `docs/` — start at [`docs/00_architecture_plans_index.md`](docs/00_architecture_plans_index.md) (canonical order) or [`docs/roles/00_roles_index.md`](docs/roles/00_roles_index.md) (domain-based "which doc for X"); `docs/plans/` (active + historical plans/decisions log, incl. `implementation-log/` for point-in-time notes). Skills live in `.claude/skills/` and `skills/` — see [Skills](#skills) below.
- **Generated repo map** [`openwiki/`](openwiki/README.md) — reserved home for a repo-navigation layer that OpenWiki would generate for coding agents (**not yet generated**; README-only stub). Advisory only once generated: it never overrides CLAUDE.md, this file, or `docs/`. See `openwiki/README.md` for regeneration commands and review rules.
- **Agent model routing** (owner, 2026-10-29): the rule is in [CLAUDE.md](CLAUDE.md) (Hard invariants). Workflow scripts in `.claude/workflows/` apply it as `model: 'sonnet', effort: 'high'` for implementers, `model: 'haiku', effort: 'medium'` for test runners and `model: 'haiku', effort: 'xhigh'` for exploration and scans.

## Skills

Two directories, different purposes. `.claude/skills/` holds 1 vendored
**process** skill; `skills/` (no dot) holds this project's 4 **domain** skills.
The other process skills come from the superpowers plugin.
Invoke by name. Each skill's `description:` front matter says when to use it,
and the Skill tool already lists those, so they are not repeated here.

Domain skills — read the matching one before editing its area:

| Skill | Area |
|---|---|
| `asclexis-backend` | Backend routes, `src/backend/modules/`, models and schemas, the per-profile vault, the dual Alembic chains, middleware, LLMOps, the proof bundle |
| `asclexis-agent` | `src/backend/modules/agent/`: graph runner, nodes, tool registry, step budget, audit hooks, the `/assistant/` wiring |
| `asclexis-guardrails` | Guard node, advice classifier, abstention templates, groundedness, confidence thresholds, the PHI redaction gate |
| `asclexis-evals` | Golden eval cases, synthetic vault states, the six scoring axes, the CI gate on agent behavior |

Process skills:

- [obra/superpowers](https://github.com/obra/superpowers) plugin (install with
  `/plugin install superpowers@claude-plugins-official`): `test-driven-development`, `systematic-debugging`,
  `writing-plans`, `executing-plans`, `subagent-driven-development`, `brainstorming`,
  `verification-before-completion`, `requesting-code-review`, `receiving-code-review`,
  `dispatching-parallel-agents`, `using-git-worktrees`, `finishing-a-development-branch`,
  `writing-skills`. CLAUDE.md and the definition of done below are written against its
  vocabulary.
- Vendored: `resolving-merge-conflicts` (mattpocock/skills, MIT).

Sources and why the directories are separate:
[`.claude/skills/README.md`](.claude/skills/README.md) and [`skills/README.md`](skills/README.md).

## Commands (Windows is the native dev environment)

```powershell
.\dev.ps1                                  # full stack; if 8000/3000 are busy it first stops the listeners (UAC retry), then falls back to the next free port
cd src/backend; python -m pytest tests/test_<area>.py -p no:cacheprovider -q   # focused: the test files your diff touches (the local default)
cd src/backend; python -m pytest tests/ -p no:cacheprovider -q   # full backend suite, optional locally: CI runs it on the PR (5114 collected; 5 tests fail without the fetched embedding model, see Known env-only failure)
cd src/frontend; npm run dev               # frontend only
cd src/frontend; npx tsc --noEmit; npm run build; npx vitest run
cd src/frontend; npx playwright test       # e2e
cd src/backend; python scripts/download_models.py list     # GGUF tiers + ollama pull tags
cd src/backend; python scripts/download_models.py verify   # check every tier repo exists on HuggingFace (needs network)
```

Known env-only failure: since W-8 the embedding model is a fetched, gitignored bundle. Without it exactly 5 tests fail: `test_embedding_bundle.py::test_hc_emb_002_fetched_model_loads_offline` and, in `test_rag_pipeline.py`, `test_api_rag_index_002`, `test_api_rag_index_002b`, `test_api_rag_index_002c`, `test_search_vectors_async_calculates_similarity`. Fix: `cd src/backend && python scripts/download_models.py embedding`; never lower the 0.7 threshold. CI fetches the model. WSL/9p mounts: clear `__pycache__` before pytest (stale bytecode causes phantom results); `node_modules` may be unusable — run frontend toolchain on Windows.

## Key flows (trace these before changing them)

1. **Document → graph**: upload (`api/documents`) → `modules/ingest` → `modules/extract` (date extraction is format-sensitive; canonical ISO-8601; collection-label priority) → observations stored per-profile → `api/observations` trends → `ResultsPage` (`/results`). Undated observations are listed but excluded from time-series; `POST /{id}/reprocess` re-extracts.
2. **Assistant chat**: `api/assistant` → ChatSession/ChatTurn persistence → `modules/rag`: retrieves user observations (`[YOUR_RESULTS:N]`), reference knowledge (`[REFERENCE:N]`, auto-seeded at startup from `scripts/seed_knowledge_base.py`), memory items + bounded session history (labeled non-citable) → ModelRunner → `validate_response()` + safety guards. No-LLM fallback must stay functional.
3. **Feedback → RL datasets**: thumbs/corrections (`api/feedback`, upsert per turn) → `modules/rl_dataset` export (DPO pairs, SFT, GRPO reward JSONL) — redaction mandatory, explicit confirmation required.
4. **Backup → restore**: `api/backup` (create/verify/download/restore/prune) → `scripts/backup.py` engine → per-profile `backups/{profile_id}/`. Backups are **deliberately unredacted** (a redacted backup cannot be restored); with `GET /export/csv` and `GET /export/json` (owner decision D3) they are the only unredacted export-shaped paths. Restore is profile-scoped: vault and sealed keys verbatim, only this profile's master row re-applied. `modules/backup_scheduler` runs due backups from the lifespan task and records `skipped_locked` honestly when a vault is closed.
5. **Profile lifecycle**: create (`api/profiles`) issues a one-time recovery code sealing a *second copy of the same DEK* (`SEC-RECOV-001`); `DELETE /profiles/{id}` is an ordered crypto-erase — sealed keys first as the commit point, then the vault sweep, then the backup sweep, then one master transaction that purges audit rows and writes an anonymized tombstone.

## Configuration

`.env` from `config/.env.example`. Notable: `LLM_PROVIDER` (`llama_cpp`|`ollama`), `LLM_MODEL`, `OLLAMA_BASE_URL` (must stay localhost; today it is read only by `api/model_settings.py`, for display and the localhost check on a provider switch: `core/llm/factory.py` builds `OllamaProvider` with its built-in `127.0.0.1:11434`), `ASSISTANT_MEMORY_ENABLED` (default true; ANDed with per-profile toggle and request flag).

## Definition of done

A task is done when all of the following are true **and you have seen the output
that proves each one**:

- Tests written or updated, and the new ones observed failing before the fix.
- Backend: the focused tests (every test file the diff adds or changes, plus the
  plan's acceptance commands) pass locally, and the PR's CI Backend Tests run on
  the final head SHA, which is the full suite, is SUCCESS (owner WF-FOCUSED-LOCAL).
  Pending or skipped is not a pass. Running
  `cd src/backend && python -m pytest tests/ -p no:cacheprovider -q` locally is
  still allowed and optional. For a diff that `scripts/change_scope.py` reports as
  `backend=false`, the PR's CI Backend Tests run is the full-suite evidence,
  unless it also reports `docs_only=true`: then no tracked file under `src/`,
  `scripts/`, `.github/`, `.claude/mods/` names the changed paths and CI skips
  Backend Tests by design (owner SPEEDUP-1-3).
- `cd src/frontend && npx tsc --noEmit` is clean and `npx vitest run` passes.
- The app boots: `cd src/backend && python -c "from main import app"`.
- Every hard invariant in [CLAUDE.md](CLAUDE.md) still holds.
- Non-trivial work logged in `docs/features/TASK_LIST.md` Session Notes, or a
  dated file under `docs/plans/` for a substantial standalone plan.
- [`docs/agentic/recurring-failures.md`](docs/agentic/recurring-failures.md)
  re-read, and any new instance of a listed failure mode recorded there.

"I believe these pass" is not done. Run them. Every failure mode in
`recurring-failures.md` shipped alongside a passing signal.
