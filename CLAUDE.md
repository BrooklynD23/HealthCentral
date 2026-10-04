# CLAUDE.md — Asclexis

Behavioral rules for AI agents working in this repo. Repo facts, commands, and architecture live in [AGENT.md](AGENT.md) — read it first.

## 1. Surface assumptions — never guess silently

- If a request has multiple interpretations, state your assumption and ask before writing code.
- ALWAYS ask before touching: `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, anything auth/encryption. These are medical-safety and privacy guarantees, not ordinary code.
- For read-only investigation across unfamiliar areas, prefer one broad
  exploration pass over many narrow sequential greps; dispatch independent
  searches in parallel when they share no state. Then verify what matters
  yourself — an agent's report is a lead, not a finding.
- This is a health app for real patients. When in doubt between a clever fix and a conservative one, pick conservative and say why.

## 2. Enforce simplicity

- If 200 lines could be 50, rewrite. No speculative flexibility, no abstractions for single-use code, no features nobody asked for.
- The provider abstraction already exists (`core/llm/`). Do not add new layers on top of it — add providers inside it.
- Prefer extending an existing module over creating a new one. The `modules/` directory is already large, and there is usually prior art.

## 3. Surgical edits only

- Modify only what the task requires. No drive-by reformatting, no touching adjacent comments, no surprise refactors.
- Never weaken a safety check, lower a test threshold, or relax a validation to make something pass. If a guard blocks you, the guard is probably right — stop and ask.
- All LLM calls go through the `ModelRunner` facade. Never import `llama_cpp` or call Ollama directly from feature code.

## 4. Loop toward verifiable success criteria

- Write or extend a test first, then make it pass. Tests live in `src/backend/tests/` (pytest, `HC-XXX-NNN` naming) and `src/frontend` (vitest + Playwright e2e).
- Baseline: **1350 backend tests collected.** Where a real embedding model is
  installed (CI) all 1288 pass; without one, `test_api_rag_index_002b` fails on
  embedding similarity. That failure is environmental — it is not yours, and you
  must not "fix" it by lowering the 0.7 threshold. Judge yourself on the
  **collected** count, which does not vary by environment: if it differs from
  1350, this line is stale — update it in the same commit rather than working
  around it.
- **Run verification; never assert it.** Report the command and its actual
  output. "Tests pass" without the output is not a result. If a check was
  skipped, say which and why.
- **A green suite is evidence, not proof.** On this branch a green backend suite
  coexisted with a restore endpoint that returned 400 for every request
  and a backup download that shipped every profile's password hash. The route
  tests called handlers as plain functions, so FastAPI's dependency graph never
  ran; the isolation test asserted on filenames, so it could not see data
  leaking inside a file. Ask what your test would fail to notice.
- **Route tests go through HTTP.** A test that calls a route function directly
  cannot see a broken `Depends(...)`. Use `tests/support/routes.py::route_client`
  for anything asserting auth, path scoping, or status codes.
- **Read [docs/agentic/recurring-failures.md](docs/agentic/recurring-failures.md)
  before claiming done.** Eight failure modes this repo has actually produced,
  each with the evidence that exposed it and a specific recheck. Catch a new
  instance of one — or a mode that is not listed — and add it in the same commit.
- Done is defined once, in [AGENT.md](AGENT.md#definition-of-done). It requires seeing the output, not believing it.

## Hard invariants (violations = broken build or broken trust)

- **Target Python 3.11+.** Do not use Python 3.12+ only syntax or APIs unless the project explicitly raises the minimum version. Use `core.time.utcnow` as the single timestamp helper.
- **Per-profile data isolation.** Patient data lives in per-profile SQLCipher DBs via `ProfileDbSession`. Never query profile data through the master `get_db()`.
- **Local-first.** No network calls in product code paths. Ollama provider is localhost-only by design — keep it that way.
- **Redaction before anything leaves.** Any path that writes user text to exportable files or external runners must pass through `modules/redaction.py` first.
- **Audit logging** on every route that touches documents, observations, or profile data.
- **No medical advice.** Outputs are educational, grounded, cited (`[REFERENCE:N]` / `[YOUR_RESULTS:N]`). `interpret_safety` prohibited patterns (diagnosis, dosing) must keep passing.
- **Dual migrations.** Master DB and per-profile DB have separate Alembic chains (`migrations/master/`, `migrations/profile/`). New profile tables = new profile migration, linear `down_revision`.

## OpenWiki usage

`openwiki/` is reserved for OpenWiki-generated repo-navigation docs, but generation has not run yet — see `openwiki/README.md` for status and regeneration commands. Until it has, use `docs/architecture/` for hand-maintained navigation instead. Once generated, use OpenWiki output to locate code, trace dependencies, and identify likely files for a task, but never as authority over safety, privacy, medical, compliance, architecture decisions, or backlog state. If OpenWiki ever conflicts with `CLAUDE.md`, `AGENT.md`, `docs/00_architecture_plans_index.md`, or `docs/roles/00_roles_index.md`, the hand-maintained docs win.

## Skills

This repo ships 36 skills — process skills in `.claude/skills/`, project-domain
skills in `skills/`. The routing table is in [AGENT.md](AGENT.md#skills).

- Check for a covering skill **before** improvising a workflow. A skill exists
  because someone already worked out the right approach and wrote it down.
- `test-driven-development` and `systematic-debugging` apply to essentially all
  feature and bug work in this repo. Reach for them by default, not as a
  ceremony when a task feels large.

## Commit style

`fix(scope):` / `feat(scope):` / `docs:` prefixes; small, single-purpose commits on a feature branch.
