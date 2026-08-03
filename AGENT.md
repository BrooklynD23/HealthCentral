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
- **Docs** `docs/` — start at [`docs/00_architecture_plans_index.md`](docs/00_architecture_plans_index.md) (canonical order) or [`docs/roles/00_roles_index.md`](docs/roles/00_roles_index.md) (domain-based "which doc for X"); `docs/plans/` (active + historical plans/decisions log, incl. `implementation-log/` for point-in-time notes). `.claude/skills/` has vendored process skills (TDD, debugging, planning — see `.claude/skills/README.md`); `skills/` (no dot) is Asclexis's own project-domain skills (`asclexis-agent`, `asclexis-backend`, `asclexis-evals`, `asclexis-guardrails`) — see `skills/README.md` to avoid confusing the two.
- **Generated repo map** [`openwiki/`](openwiki/README.md) — OpenWiki-generated navigation for coding agents (where code lives, how files connect). Advisory only: it never overrides CLAUDE.md, this file, or `docs/`. See `openwiki/README.md` for regeneration commands and review rules.

## Commands (Windows is the native dev environment)

```powershell
.\dev.ps1                                  # full stack, auto-selects free ports
cd src/backend; python -m pytest tests/ -p no:cacheprovider -q   # backend tests (1244 pass, 1 known env-only failure)
cd src/frontend; npm run dev               # frontend only
cd src/frontend; npx tsc --noEmit; npm run build; npx vitest run
cd src/frontend; npx playwright test       # e2e
python scripts/download_models.py          # GGUF / ollama pull (Gemma 4 tiers)
```

Known env-only failure: 1 RAG embedding-similarity test needs a real embedding model. WSL/9p mounts: clear `__pycache__` before pytest (stale bytecode causes phantom results); `node_modules` may be unusable — run frontend toolchain on Windows.

## Key flows (trace these before changing them)

1. **Document → graph**: upload (`api/documents`) → `modules/ingest` → `modules/extract` (date extraction is format-sensitive; canonical ISO-8601; collection-label priority) → observations stored per-profile → `api/observations` trends → `TrendsDashboard`. Undated observations are listed but excluded from time-series; `POST /{id}/reprocess` re-extracts.
2. **Assistant chat**: `api/assistant` → ChatSession/ChatTurn persistence → `modules/rag`: retrieves user observations (`[YOUR_RESULTS:N]`), reference knowledge (`[REFERENCE:N]`, auto-seeded at startup from `scripts/seed_knowledge_base.py`), memory items + bounded session history (labeled non-citable) → ModelRunner → `validate_response()` + safety guards. No-LLM fallback must stay functional.
3. **Feedback → RL datasets**: thumbs/corrections (`api/feedback`, upsert per turn) → `modules/rl_dataset` export (DPO pairs, SFT, GRPO reward JSONL) — redaction mandatory, explicit confirmation required.
4. **Backup → restore**: `api/backup` (create/verify/download/restore/prune) → `scripts/backup.py` engine → per-profile `backups/{profile_id}/`. Backups are **deliberately unredacted** (a redacted backup cannot be restored) and are the one export-shaped path that is. Restore is profile-scoped: vault and sealed keys verbatim, only this profile's master row re-applied. `modules/backup_scheduler` runs due backups from the lifespan task and records `skipped_locked` honestly when a vault is closed.
5. **Profile lifecycle**: create (`api/profiles`) issues a one-time recovery code sealing a *second copy of the same DEK* (`SEC-RECOV-001`); `DELETE /profiles/{id}` is an ordered crypto-erase — sealed keys first as the commit point, then the vault sweep, then the backup sweep, then one master transaction that purges audit rows and writes an anonymized tombstone.

## Configuration

`.env` from `config/.env.example`. Notable: `LLM_PROVIDER` (`llama_cpp`|`ollama`), `LLM_MODEL`, `OLLAMA_BASE_URL` (must stay localhost), `ASSISTANT_MEMORY_ENABLED` (default true; ANDed with per-profile toggle and request flag).

## Definition of done

Tests written/updated and passing, no new backend failures, `tsc --noEmit` clean, app boots, hard invariants in CLAUDE.md respected, non-trivial work logged in `docs/features/TASK_LIST.md`'s Session Notes (or a new dated file under `docs/plans/` for a substantial standalone plan).
