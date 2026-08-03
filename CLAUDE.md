# CLAUDE.md — Asclexis

Behavioral rules for AI agents working in this repo. Repo facts, commands, and architecture live in [AGENT.md](AGENT.md) — read it first.

## 1. Surface assumptions — never guess silently

- If a request has multiple interpretations, state your assumption and ask before writing code.
- ALWAYS ask before touching: `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, anything auth/encryption. These are medical-safety and privacy guarantees, not ordinary code.
- This is a health app for real patients. When in doubt between a clever fix and a conservative one, pick conservative and say why.

## 2. Enforce simplicity

- If 200 lines could be 50, rewrite. No speculative flexibility, no abstractions for single-use code, no features nobody asked for.
- The provider abstraction already exists (`core/llm/`). Do not add new layers on top of it — add providers inside it.
- Prefer extending an existing module over creating a new one. The `modules/` directory is already large; check for prior art (`grep` first).

## 3. Surgical edits only

- Modify only what the task requires. No drive-by reformatting, no touching adjacent comments, no surprise refactors.
- Never weaken a safety check, lower a test threshold, or relax a validation to make something pass. If a guard blocks you, the guard is probably right — stop and ask.
- All LLM calls go through the `ModelRunner` facade. Never import `llama_cpp` or call Ollama directly from feature code.

## 4. Loop toward verifiable success criteria

- Write or extend a test first, then make it pass. Tests live in `src/backend/tests/` (pytest, `HC-XXX-NNN` naming) and `src/frontend` (vitest + Playwright e2e).
- Baseline: **1244 backend tests pass**; 1 known env-only failure (`test_api_rag_index_002b`, embedding similarity — needs a real embedding model). Do not "fix" it by lowering the 0.7 threshold. If your measured count differs from this line, the line is stale — update it in the same commit rather than working around it.
- A task is done when: relevant tests pass, `python -m pytest tests/ -q` shows no new failures, `npx tsc --noEmit` is clean, and the app boots (`from main import app`).

## Hard invariants (violations = broken build or broken trust)

- **Target Python 3.11+.** Do not use Python 3.12+ only syntax or APIs unless the project explicitly raises the minimum version. Use `core.time.utcnow` as the single timestamp helper.
- **Per-profile data isolation.** Patient data lives in per-profile SQLCipher DBs via `ProfileDbSession`. Never query profile data through the master `get_db()`.
- **Local-first.** No network calls in product code paths. Ollama provider is localhost-only by design — keep it that way.
- **Redaction before anything leaves.** Any path that writes user text to exportable files or external runners must pass through `modules/redaction.py` first.
- **Audit logging** on every route that touches documents, observations, or profile data.
- **No medical advice.** Outputs are educational, grounded, cited (`[REFERENCE:N]` / `[YOUR_RESULTS:N]`). `interpret_safety` prohibited patterns (diagnosis, dosing) must keep passing.
- **Dual migrations.** Master DB and per-profile DB have separate Alembic chains (`migrations/master/`, `migrations/profile/`). New profile tables = new profile migration, linear `down_revision`.

## OpenWiki usage

Generated repo-navigation docs live in `openwiki/`. Use them to locate code, trace dependencies, and identify likely files for a task. Do not treat OpenWiki as authority over safety, privacy, medical, compliance, architecture decisions, or backlog state. If OpenWiki conflicts with `CLAUDE.md`, `AGENT.md`, `docs/00_architecture_plans_index.md`, or `docs/roles/00_roles_index.md`, the hand-maintained docs win.

## Commit style

`fix(scope):` / `feat(scope):` / `docs:` prefixes; small, single-purpose commits on a feature branch.
