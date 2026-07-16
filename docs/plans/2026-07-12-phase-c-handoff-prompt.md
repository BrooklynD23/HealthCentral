# Handoff Prompt — Phase C (Pinboards, Search, Confidence UX)

> Status: HANDOFF for the next orchestration session (Fable 5)
> Date: 2026-07-12
> Prior session delivered Phases A and B of the post-visit roadmap via orchestrated subagents.

Copy everything below the line into the new session.

---

You are orchestrating subagents in the HealthCentral repo to implement **Phase C** of the post-visit & record-intelligence roadmap. Phases A and B are done. Read `CLAUDE.md` and `AGENT.md` first — they override everything.

## Roadmap and prior context

- Full roadmap: `docs/plans/2026-07-10-post-visit-record-intelligence-roadmap.md` — **only on branch `claude/healthcentral-post-visit-roadmap-g6vhb3`**, not on main or the integration branches. Fetch that branch to read it (`git fetch origin claude/healthcentral-post-visit-roadmap-g6vhb3 && git show origin/claude/healthcentral-post-visit-roadmap-g6vhb3:docs/plans/2026-07-10-post-visit-record-intelligence-roadmap.md`).
- Per-milestone Session Notes: `docs/features/TASK_LIST.md` (on the integration branches) documents everything shipped in Phases A/B with test IDs and verification numbers.

## Current state (all pushed, no PRs opened, nothing merged to main)

| Branch | Contents |
|---|---|
| `claude/hc-phase-a-integration` | HC-M12 source spans + entity verification, HC-M13 after-visit/discharge extraction (+opt-in LLM-assist), HC-M14 health timeline, HC-M15 follow-up task tracker, plus 4 adversarial-review fixes (LLM-assist value grounding, due-date anchoring, reprocess-safe dedup, med stoplist) |
| `claude/hc-phase-b-integration` | ↑ plus HC-M16 smart highlights, HC-M17 multi-source doctor questions, HC-M18 visit-prep packet (confirm-required, strict redaction, unverified-excluded), HC-M19 read-only medication reconciliation. **This is the base for Phase C.** |

Feature branches (already merged into the above, kept for review): `claude/hc-m12-source-spans` → `claude/hc-m13-after-visit` → `claude/hc-m15-followup-tasks` (stacked), `claude/hc-m14-timeline`, `claude/hc-m16-highlights`, `claude/hc-m19-med-reconcile`, `claude/hc-m17-m18-export`.

**Verified baseline on `claude/hc-phase-b-integration` (HEAD a427090):**
- Backend: `cd src/backend && python -m pytest tests/ -p no:cacheprovider -q` → **900 passed / 1 failed** — the 1 is the known env-only RAG embedding-similarity test (needs a real embedding model; NEVER "fix" its 0.7 threshold).
- Frontend: `npx vitest run` → **128/128**; `npx tsc --noEmit` → exit 0 (one pre-existing TS5101 baseUrl deprecation notice — not yours).
- `python -c "from main import app"` boots.
- Profile migration chain head: `011_care_plan_tasks` (chain: `009_agent_enabled` → `010_entity_source_spans` → `011_care_plan_tasks`). The next migration is 012 and its `down_revision` must be the exact string `"011_care_plan_tasks"`. Alembic resolves by revision ID string, not filename number.

**Outstanding items not yet done (flag to the user, don't silently do them):** Phase B has NOT had its own adversarial review pass (Phase A did; recommend running one — spawn a Fable 5 review-only agent on `git diff origin/claude/hc-phase-a-integration...origin/claude/hc-phase-b-integration` before or in parallel with Phase C). `feature_list.json` has not been updated with HC-M12+ milestones (owner approval required per the roadmap doc §6). No PRs exist; the user reviews via the integration branches.

## Phase C scope (from the roadmap)

- **HC-M20 Pinboards**: user-curated collections of documents/observations/tasks/questions. New profile tables `pinboard` + `pinboard_item` (ONE new migration, 012). CRUD API with audit logging. Each pinboard can export a focused packet by REUSING the HC-M18 packet composer (`ExportModule.compose_visit_prep_packet` / `POST /export/visit-prep` patterns — selected content instead of date-range). New PinboardsPage + "add to pinboard" affordances where items are already listed. Suggested test prefix HC-PIN-NNN.
- **HC-M21 Search & filtering**: cross-record search over documents/entities/observations using SQLite FTS5 **inside the per-profile DB** (stays local + encrypted; verify FTS5 is available in the SQLCipher build the app uses — if not, a LIKE-based fallback with the same API is acceptable, say so honestly). Filters: provider/date/category/highlight-type; reuse the timeline filter param conventions. Bounded results, audit-logged route, SearchPage or search bar in the layout. Suggested prefix HC-SRCH-NNN.
- **Opportunistic (small, can ride with either)**: OCR/extraction-confidence UX (surface existing confidence scores prominently pre-verification) and duplicate-upload warning (hash + date heuristic at import time, warn-only, never block).

Phase C adds NO LLM behavior. Everything computes from existing data. If both C-milestones need tables, put ALL new tables in migration 012 under HC-M20's agent, or run the migration-owning agent first — two parallel agents must NEVER both create migrations (linear chain).

## Orchestration playbook (what worked for Phases A/B)

1. Waves of parallel background agents (`Agent` tool, `isolation: "worktree"`), each with its own branch off `claude/hc-phase-b-integration` (e.g. `claude/hc-m20-pinboards`, `claude/hc-m21-search`). Parallel only when file scopes are disjoint; expected trivial overlaps (services barrel `src/frontend/src/services/index.ts`, `docs/features/TASK_LIST.md`, `api/__init__.py`) are fine — resolve by union at merge time.
2. Agent prompts must be SELF-CONTAINED: goal/user story, exact scope, files to inspect first, baseline numbers to hold (900/1 backend, 128 vitest), test-first with the HC-XXX-NNN naming, environment notes below, git rules below. Agents cannot see this conversation.
3. Verify every pushed branch yourself before merging: `git log`/`git diff --stat` against its base, and an EMPTY diff on the four protected safety modules: `git diff origin/main...<branch> -- src/backend/modules/interpret_safety.py src/backend/modules/redaction.py src/backend/modules/faithfulness.py src/backend/modules/verifier_agent.py`.
4. When all wave branches land: create `claude/hc-phase-c-integration` off `claude/hc-phase-b-integration`, merge each feature branch (`--no-ff`), union-resolve conflicts, run the FULL verification suite on the merged result (pytest / boot / tsc / vitest — expected counts = sum of the branches), push. Do NOT open PRs unless the user asks.
5. **Session usage limits WILL interrupt agents** ("You've hit your session limit · resets X"). This is not a code failure. When notified: check `date -u`; if past reset, resume the agent via `SendMessage` (use its agent id from the spawn result) with a short "limit reset — resume from where you left off" message restating the remaining scope; if before reset, schedule the resume. Always tell agents up front: "If you hit a session usage limit, commit coherent partial progress first."
6. Track waves with TaskCreate/TaskUpdate so state survives interruptions.
7. After Phase C integrates, offer the user an adversarial review pass (review-only Fable 5 agent, findings ranked CONFIRMED/PLAUSIBLE with concrete repros) and a follow-up fix agent for accepted findings — that loop caught 1 HIGH + 3 real bugs in Phase A.

## Hard invariants (enforce in every agent prompt)

- NEVER touch `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, or anything auth/encryption (calling redaction/interpret_safety functions is fine and sometimes required).
- Profile data only via `ProfileDbSession`; never the master `get_db()` for profile data. Audit logging on every new route (copy `audit_and_commit` / `log_document_event` conventions).
- Python 3.11+ syntax; `core.time.utcnow` for timestamps in new code.
- No network calls; LLM only via ModelRunner (Phase C shouldn't need it at all).
- No medical advice in any user-facing string; record-keeping framing only ("The note says…"). Anything exported/downloadable passes through the existing redaction engine.
- Unverified data: excluded or explicitly labeled, matching the HC-M18 "excluded everywhere" policy.
- Surgical edits; extend existing modules over creating new ones; no drive-by reformatting.

## Environment gotchas (put these in every agent prompt)

- Linux container. The checked-in `.wsl-pytest-venv` is a broken WSL husk; in the MAIN working copy `ln -sf /usr/bin/python3.12 .wsl-pytest-venv/bin/python3` repairs it (site-packages are populated). In agent WORKTREES it must be rebuilt: python3.12 venv + backend requirements MINUS llama-cpp-python / sentence-transformers / weasyprint (all lazy imports). NEVER commit venv files — `git restore .wsl-pytest-venv/` before every commit (a stop-hook rejects dirty trees).
- Clear `__pycache__` before pytest (stale bytecode → phantom results).
- Each worktree needs its own `npm install` in `src/frontend` before vitest. Playwright e2e is NOT runnable in this environment (no browsers provisioned) — skip with a note.
- Git: small single-purpose commits, `feat(scope):`/`fix(scope):`/`test(scope):`/`docs:` prefixes; `git push -u origin <branch>` with up-to-4 retries exponential backoff on network errors only; agents must never push to a branch other than their own.

## Definition of done (per milestone and for the integration branch)

New tests pass; zero new failures vs the stated baseline; `tsc --noEmit` unchanged; app boots; Session Notes entry appended to `docs/features/TASK_LIST.md`; branch pushed; safety-module diff empty.
