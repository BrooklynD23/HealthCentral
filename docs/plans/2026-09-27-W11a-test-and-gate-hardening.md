# W-11a Test and Gate Hardening (G-B1, G-B2, G-B4, G-B6) Implementation Plan

**Last Updated:** 2026-09-27
**Owner:** repository owner
**Refresh Trigger:** P1, P4, P5, P7 or W-4 merges (re-verify every `main@40f590e` / `B@7b2ff1f` line reference on the tree that exists then); an owner answer to OG-1, OG-2, Q-AUD-LIST, Q-RUFF or Q-COV; any edit to `src/backend/api/profiles.py`, `src/backend/tests/support/routes.py`, `src/backend/core/profile_database.py`, `src/backend/core/migrations.py` or `.github/workflows/ci.yml`.
**Status:** PROPOSED — not executed
**Review status:** 3 Codex rounds; round-3 findings fixed after the last round (owner decides on round 4).
**Prerequisites:** P0-B and P1 merged to `origin/main`. Also: P5 + P7 (PR-1), P4 + P5 + W-4 (PR-3), the D9 venv `~/venvs/asclexis-311` (all backend steps). Before P1 lands, Task 0 Step 2's ancestry check fails; that STOP is intended, not a defect.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Also load `test-driven-development` and, for Task 3, `asclexis-backend` (SQLCipher vault, dual Alembic chains).

**Goal:** Close four test/gate gaps with evidence that can fail: HTTP tests for the profile-route guard (plus, if the owner signs, audit rows on the four unaudited profile routes), an on-disk ciphertext test, a one-head-per-chain migration test, frontend build/eslint + backend ruff + coverage steps in CI, and measured frontend test counts in place of the unmeasured "155 vitest / 25 Playwright" claims.

**Architecture:** Four independent PRs, each from its own worktree off post-P1 `origin/main`:

| PR | Gap | Kind | Earliest start |
|---|---|---|---|
| PR-1 | G-B1 | tests (Task 1) + owner-gated route edit (Task 2) | after P7 |
| PR-2 | G-B2 | tests only, encryption area (owner confirmation OG-2) | after P1 |
| PR-3 | G-B4 | test + CI config | after P5 and W-4 |
| PR-4 | G-B6 | DOCS only | after P1 (and P0-B) |

- **Guard tests** drive `api/profiles.py` through `route_client` against a real, file-backed master DB. The DB is read back through a separate connection, so a test sees only committed rows.
- **Durable break-it controls.** Each safety test ships with a control that removes the thing under test and asserts the test's check then fails: a dependency-override mutation for the guard, a plaintext-vault control for encryption, a forked-chain copy for migrations.
- **Nothing in `core/auth.py`, `core/profile_database.py`, `core/security.py`, `core/migrations.py`, `core/audit.py` or `tests/conftest.py` is edited.**

**Tech Stack:** pytest + pytest-asyncio, FastAPI `TestClient`, SQLAlchemy (sync + aiosqlite), Alembic `ScriptDirectory`, sqlcipher3-binary, GitHub Actions, ruff 0.15.10, eslint 9, vitest 4, Playwright 1.58. Backend interpreter: D9 venv `~/venvs/asclexis-311/bin/python` (Python 3.11). Frontend: Windows PowerShell for G-B6; a Linux-native scratch copy for CI-parity checks in G-B4.

**Spec:**
- [handoff §5 W-11](../../audit/2026-09-25/handoff-2026-09-27-execution.md)
- [program "Gap phases" G-B1/G-B2/G-B4/G-B6](../capstone-report/implementation-program.md)
- [contract](../capstone-report/architecture-engineering-contract.md): C-ISO-1, C-ISO-2, C-AUDIT-1, C-KEY-1, C-MIG-1, C-MIG-2, C-API-3, C-GATE-1…4
- [matrix](../capstone-report/specs-compliance-matrix.md): ISO-02, AUD-02, KEY-02, MIG-02, GATE-03, GATE-06, GATE-07
- [owner decisions](../capstone-report/owner-decisions-2026-09-27.md)

---

## Global Constraints

- Python 3.11 target. Use `core.time.utcnow` (naive UTC) for every timestamp a test seeds (CLAUDE.md "Hard invariants"). No test in this plan calls `datetime.now(...)` or `datetime.utcnow()`. The one place a `Session` is needed (HC-PGUARD-005) reuses the `Session` that `route_client` already built, so no timestamp is constructed. `core/auth.py` `Session.is_expired` compares `expires_at` against an *aware* now, so a naive value there would raise `TypeError`.
- **Shell conventions for every bash block:**
  - Each block starts with `set -o pipefail` and an absolute `WT=` line naming its worktree: `/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1|gb2|gb4|gb6`. Shell state does not persist between blocks.
  - Paths are absolute (`"$WT/src/backend"`). There is at most one `cd` per block, always to an absolute path, never a relative `cd` after a `cd`.
  - Whenever pytest output is piped (`| tail`, `| tee`), print `pytest exit=${PIPESTATUS[0]}` so a failing run cannot hide behind `tail`'s exit 0.
- **Break-it runs on files this plan marks read-only** (e.g. `api/profiles.py` in Task 1, `migrations/`) happen by monkeypatch or in a disposable **detached** worktree, never by editing and `git checkout --` in the phase worktree.
- Route, auth and status tests go through HTTP with `src/backend/tests/support/routes.py::route_client` (CLAUDE.md §4; contract C-ISO-2).
- Per-profile isolation: patient data is read only through `ProfileDbSession`. The tests seed only master tables (`profiles`, `audit_logs`) through the master `Base`.
- Audit rows carry no PHI. Every audit write goes through `core/audit.py` helpers, whose `_scrub_action` / `_scrub_details` (`B@7b2ff1f core/audit.py:118-193`) are the choke point. This plan does not edit that file.
- Never lower a threshold. Never weaken a guard, a validation or `DATABASE_ENCRYPTION_REQUIRED` semantics to get green. `tests/conftest.py:57` (`DATABASE_ENCRYPTION_REQUIRED=false`, main@40f590e and B@7b2ff1f) stays as it is. The ciphertext test overrides it for itself only.
- Local-first: no product code gains a network call. The CI steps install tools only inside the runner.
- Commit prefixes are `fix(scope):`, `feat(scope):` or `docs:`. Stage with explicit pathspecs; never `git add -A` or `git add .` (contract C-GATE-3).
- Line numbers below are labelled with their ref. Plans execute **after** P1, P5 and P7, which shift `api/profiles.py` lines. **Re-verify every cited line on the worktree before editing.**

## Review Focus

The five failure modes most likely to bite, each pinned by a test in the owning task:

1. **A case or encoding variant of the profile id in the path**, e.g. `PROFILE-A` against a `profile-a` session, must still get 403. The guard compares exactly. → HC-PGUARD-006 (Task 1).
2. **A new `/{profile_id}/…` route added without `require_profile_access`**, or the guard attached to a route with no `{profile_id}` param (the restore-400 bug, recurring-failures #1). → HC-PGUARD-004 (Task 1).
3. **The audit store fails on a read route.** The profile must not be served (fail-closed `audit_and_commit`). → HC-PAUD-007 (Task 2).
4. **A synthetic reset fails halfway.** No committed audit row may claim the reset happened. → HC-PAUD-004 (Task 2).
5. **A CI runner where `sqlcipher3` cannot be imported.** The ciphertext proof must FAIL there, not skip. → HC-KEYCT-005 (Task 3).

---

## 1. Approval scope

**No owner option text licenses W-11a's scope directly.** The owner's 2026-09-27 answers ([owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md)) cover D1–D13, P0-B and G-B5. None covers G-B1, G-B2, G-B4 or G-B6. This plan rests on:

- the program's G-B rows, which are PLAN ONLY (quoted in §2);
- CLAUDE.md engineering rules;
- the owner's merge of each PR ("Humans merge", program ground rule 6).

The records that come closest, quoted verbatim so nobody reads them as covering this plan:

- **D9** ("New 3.11 venv"): "Build a 3.11 venv from src/backend/requirements.txt so local results match CI." W-11a uses this venv for every measurement. It does not build it.
- **D13** ("Approve"): "Same value (naive UTC), one import + swap per site; tests must show identical serialization. Reviewer checks the auth hunks specifically." This covers P5's `utcnow` swap in `api/profiles.py` **only**.
- **Handoff hard rule** (`handoff-2026-09-27-execution.md`, code block): "Ask-first files stay read-only unless the owner approves that exact change: modules/interpret_safety.py, redaction.py, faithfulness.py, verifier_agent.py, anything auth/encryption. Approved exceptions: the plan-02 core/auth.py hooks (D6), the utcnow swap in api/profiles.py auth hunks (D13), the FK pragma listener beside the SQLCipher key hook (D5)."

**This plan does, without further approval (engineering work, owner merges the PR):**
1. New test files under `src/backend/tests/` and one new helper, `tests/support/master_db.py`.
   - One backward-compatible, opt-in `real_auth` parameter on `tests/support/routes.py::route_client`. The file is test harness, not product code, and W-11a edits it only after P7.
2. `.github/workflows/ci.yml`:
   - frontend `npm run lint` and `npm run build` steps;
   - a coverage report on the existing backend run, failing closed if the report is missing.
3. Docs:
   - status rows in the capstone matrix, contract and claims ledger;
   - a dated-snapshot annotation on the frontend-count note in `audit/repository-audit-dashboard.html` (G-B6);
   - `docs/architecture/ci-and-quality-gates.md`;
   - the measured baseline sentences in `CLAUDE.md` / `AGENT.md`;
   - a `docs/features/TASK_LIST.md` Session Note.

**Does NOT license (owner-gated; each has an unsigned line in §11):**
- **OG-1:** any edit to `src/backend/api/profiles.py`, including adding audit calls (Task 2). The program says "auth-adjacent: tests only unless the owner approves route edits"; D13 does not cover audit calls.
- **Q-AUD-LIST:** auditing the unauthenticated `GET /profiles/` (no actor, NULL `profile_id`), versus documenting it as an exemption.
- **OG-2:** committing the encryption-area test (Task 3). It touches no encryption code, but the program's G-B2 stop gate says "encryption: ask first".
- **Q-RUFF:** which ruff rules gate CI. Fixing the 561 current findings would touch all four safety modules plus `core/auth.py`, `core/security.py` and `core/profile_database.py` (§4 measurement).
- **Q-COV:** any coverage *threshold*. This plan adds a report only.
- **OG-3:** pushing a deliberately failing "seed" branch to prove a gate in real CI.
- Any edit to `core/auth.py`, `core/audit.py` (including registering new `ALLOWED_ACTIONS` strings), `core/profile_database.py`, `core/security.py`, `core/migrations.py`, `core/sqlcipher_driver.py`, `tests/conftest.py`, `src/backend/requirements.txt`, `src/frontend/package.json`, `eslint.config.js` or `pyproject.toml`.
- Auditing *denied* guard attempts (a `core/auth.py` change).
- Fixing N-03, where `/test/reset` echoes `{exc}` in its 500 detail (`api/profiles.py:528-531`, main@40f590e). It is recorded, not fixed.
- black, mypy, `--max-warnings` for eslint, or any other gate not named in the G-B4 row.

## 2. Traceability

| Kind | ID | Verified text (grep, 2026-09-27) |
|---|---|---|
| Handoff | §5 W-11 | "remaining gaps \| G-B1 (HTTP tests for profile guards + 4 audit rows), G-B2 (on-disk ciphertext test), G-B4 (single-head migration test, CI build/eslint/ruff), G-C1…C4 per the program table" |
| Program | G-B1 | "HTTP tests for `require_profile_access` on profile routes; audit rows for the 4 unaudited profile routes (ISO-02, AUD-02) \| P7 … \| auth-adjacent: tests only unless the owner approves route edits \| Tests go red when the guard is removed; each of the 4 routes writes an audit row, asserted over HTTP" |
| Program | G-B2 | "On-disk ciphertext test with encryption required (KEY-02) \| P1 \| encryption: ask first \| A test fails if the vault header reads `SQLite format 3`" |
| Program | G-B4 | "Single-head migration test (MIG-02); CI `npm run build`, eslint, ruff; coverage report (GATE-07) \| P5 (shares `ci.yml`) \| — \| Each new gate fails on a seeded violation" |
| Program | G-B6 | "DOCS \| Measure the frontend counts (vitest, Playwright) on Windows and replace the 155/25 claims \| P1 \| — \| Command output recorded" |
| Contract | C-ISO-1 | "HTTP coverage of `require_profile_access` on `api/profiles.py` routes is missing (matrix ISO-02)" |
| Contract | C-ISO-2 | "Any test asserting auth, path scoping, or status codes MUST go through HTTP (`route_client`)" |
| Contract | C-AUDIT-1 | "Every route that touches documents, observations or profile data MUST write an audit row via `core/audit.py` … Profiles 9/13: missing on `GET /` (`api/profiles.py:241`), `GET /me` (`:416`), `POST /test/reset` (`:477`), `GET /{profile_id}` (`:943`)" |
| Contract | C-KEY-1 | "no pytest proves on-disk ciphertext (matrix KEY-02)" |
| Contract | C-MIG-1 / C-MIG-2 | "Each chain stays linear (a single `down_revision`, a single head)" / "PROPOSED … A test MUST assert exactly one head per chain" |
| Contract | C-API-3 | "PROPOSED … `npm run build` and eslint run in CI" |
| Contract | C-GATE-1…4 | measured claims; fail-closed gates; explicit pathspecs; docs lint |
| Matrix | ISO-02 | "Cross-profile access is refused over HTTP … used 5× in `api/profiles.py` \| no HTTP test … \| **gap** (test coverage)" |
| Matrix | AUD-02 | "Profile routes are audited … 9/13 … **partial**" |
| Matrix | KEY-02 | "On-disk ciphertext is proven by tests … `tests/conftest.py:57` … **gap**" |
| Matrix | MIG-02 | "One head per chain is asserted \| (proposed, C-MIG-2) … **gap**" |
| Matrix | GATE-03 | "**partial**: no `npm run build`, no eslint in CI; the 155-test figure is unverified" |
| Matrix | GATE-06 | "**partial**: 25-test figure unverified; not run this pass" |
| Matrix | GATE-07 | "ruff/black/mypy/eslint configured, not run in CI; no coverage threshold \| none \| **gap**" |

**New test IDs:**
- `HC-PGUARD-001…006` (Task 1)
- `HC-PAUD-001…007` (Task 2)
- `HC-KEYCT-001…005` (Task 3)
- `HC-MIGHEAD-001…003` (Task 4)

**Collision check:**
- On 2026-09-27, `git grep -il "<p>" <ref> -- src scripts docs audit` returned 0 hits for each of `pguard`, `paud`, `keyct`, `mighead` at main@40f590e, B@7b2ff1f and A@692fdf3.
- **Substring warning:** `paud` occurs inside "pipaudit" in the untracked `audit/2026-09-25/plans/01-merge-branches.md:306-326`. That is doc text, not a test name. Always select with the full `-k hc_paud_` (trailing underscore).
- The new file `test_migration_heads.py` matches plan 06's `-k migration` (`audit/2026-09-25/plans/06-sql-fk-audit.md:296`). P6 runs before W-11a and asserts no count on that selector.
- Task 0 re-checks all of this.

## 3. Files

**Create (W-11a owns):**
- `src/backend/tests/support/master_db.py`: file-backed master DB helpers for route tests.
- `src/backend/tests/test_profile_route_guards.py`: HC-PGUARD.
- `src/backend/tests/test_profile_route_audit.py`: HC-PAUD (OG-1 only).
- `src/backend/tests/security/test_vault_ciphertext.py`: HC-KEYCT (OG-2 before commit).
- `src/backend/tests/test_migration_heads.py`: HC-MIGHEAD.

**Modify:**
- `src/backend/tests/support/routes.py`: **owned by W-11a only after P7 merges** (P7 edits it first). Adds `real_auth: bool = False` to `route_client`; the default keeps every existing caller unchanged (Task 1 Step 1b).
- `audit/repository-audit-dashboard.html` `:255`: dated-snapshot annotation (Task 11).
- `src/backend/api/profiles.py`: **only under OG-1**. Audit calls in `get_current_profile`, `get_profile`, `reset_synthetic_test_profile` (+ its `db` dependency), and `list_profiles` only under Q-AUD-LIST (a).
- `.github/workflows/ci.yml`:
  - `frontend-tests` job: lint + build steps;
  - `backend-tests` job: coverage flags + report steps;
  - a new `backend-lint` job (Q-RUFF).
- Docs:
  - `docs/capstone-report/specs-compliance-matrix.md`, `architecture-engineering-contract.md`, `claims-ledger.md`, `architecture-overview.md` (row-scoped edits only);
  - `docs/architecture/ci-and-quality-gates.md` (PR-3);
  - `CLAUDE.md` and `AGENT.md` (baseline sentences only);
  - `docs/features/TASK_LIST.md` (append a Session Note);
  - `docs/INDEX.md` and `docs/_link_graph.json`, only if `generate_docs_index.py --check` says stale.

**Read-only (ask-first or owned elsewhere):**
- `core/auth.py` (`require_profile_access` `:251-290`, main@40f590e; unchanged at B/A)
- `core/audit.py` (B@7b2ff1f; `audit_and_commit` `:474`, `log_profile_event` `:271`, `create_audit_log` `:201`)
- `core/profile_database.py` (`:259-379`, main@40f590e; unchanged at B/A)
- `core/migrations.py` (`_get_alembic_config` `:34-48`; SQLCipher gate `:213-217`)
- `core/security.py`, `core/sqlcipher_driver.py`, `tests/conftest.py`
- `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`
- `src/backend/requirements.txt`, `src/frontend/package.json`

**Shared-file order** (program: "no two phases may edit the same file at the same time"):

| File | Order | Note |
|---|---|---|
| `src/backend/api/profiles.py` | P5 (D13 swaps) → P7 (reset tuple) → **W-11a Task 2** | Task 2 edits the reset route P7 just rewrote. Re-read it first |
| `src/backend/tests/support/routes.py` | **P7 edits first → W-11a edits after P7 merges** (owned-after-P7). W-2 / W-3 only read it | Task 1 Step 1b adds opt-in `real_auth`, default `False`, on top of P7's `route_client(…, profile_name=…, profile_db=…)` (plan 07 line 74). Existing callers are unchanged. If P7 has not merged, **STOP** |
| `.github/workflows/ci.yml` | P1 → P5 (step in `docs-lint`) → W-4 (`legacy-evals` job) → **W-11a Tasks 6–8** | W-7 does not edit it. If W-4 has not merged, see stop gate 9 |
| `docs/architecture/ci-and-quality-gates.md` | P4 (divergence fix) → W-8 (`:58`) → **W-11a Task 9** | Whichever of W-8/W-11a lands second rebases |
| `docs/capstone-report/*.md` | W-1 (claims H5/H6), W-8 (several rows), other W plans' status rows | Row-scoped edits only; rebase and re-read the row before each docs commit |
| `CLAUDE.md` / `AGENT.md` baseline sentences | every PRODUCT phase, serially | Write only this PR's measured END collected count |
| `docs/features/TASK_LIST.md` | append-only; P8 also edits | Append at the end of "Session Notes" |

## 4. Dependencies and measured context

| Dependency | Needed by | Why |
|---|---|---|
| P0-B | all | the capstone docs and this plan are on `main` |
| D9 venv | all backend measurement | `~/venvs/asclexis-311/bin/python`. **Not built yet**, and **no `python3.11` exists on this WSL machine** (`/usr/bin` has 3.12 only, measured 2026-09-27). The handoff says to report that and ask |
| P1 | all | post-P1 tree, the `B@7b2ff1f` `ci.yml` / `core/audit.py` |
| P4 | PR-3 docs | P4 fixes the `ci-and-quality-gates.md:19,45` "build" claim first |
| P5 | PR-1, PR-3 | `api/profiles.py` utcnow hunks (D13) and the `ci.yml` time-source step |
| P7 | PR-1 | reset tuple (`_SYNTHETIC_RESET_MODELS`) and `route_client(profile_name=, profile_db=)` |
| W-4 | PR-3 | the `legacy-evals` job lands in `ci.yml` first |
| OG-1, Q-AUD-LIST | Task 2 | route edit in an auth-adjacent file |
| OG-2 | Task 3 commit | encryption area |
| Q-RUFF | Task 7 | ruff baseline |

**Measured 2026-09-27, by this author, read-only.** These are context for Task 0, not targets.

Trees were extracted with `git archive` into the session scratchpad:
- main@40f590e;
- B@7b2ff1f;
- the A+B merge-tree `86606d018fe1` (`git merge-tree --write-tree` B A). The 5 doc conflicts are unresolved; no product file conflicts.

| What | Command (run from `<tree>/src/backend` or `<tree>/src/frontend`) | main | B | A+B |
|---|---|---|---|---|
| ruff 0.15.10, configured rules (F, I, W) | `~/.local/bin/ruff check . --no-cache --statistics` | 555 | 561 | 561 (I001 245, F401 150, W293 140, F841 19, F541 7) |
| same, ruff 0.14.10 | `/mnt/c/Python313/python.exe -m ruff check . --no-cache --statistics` | — | — | 561 |
| same, excluding `tests/` | `… --extend-exclude tests` | — | — | 347 |
| ruff hard-error subset | `ruff check . --no-cache --select E9,F63,F7,F82` | 0 ("All checks passed!") | 0 | 0, both versions |
| ruff findings in ask-first / auth / encryption files | `ruff check . --output-format concise` then grep | — | — | 37 in 10 files (next line) |
| eslint 9.39.2, node v22.21.0 (Linux copy, `npm ci --ignore-scripts`) | `npx eslint . -f json` | — | — | 143 files, **0 errors, 5 warnings** (all `@typescript-eslint/no-explicit-any`), exit 0 |
| `npm run build` (Linux copy) | `npm run build` | — | — | exit 0, "✓ built in 11.22s"; chunk-size warning (index 540.89 kB) |
| vitest 4.0.16, **listed** (Linux, not Windows) | `npx vitest list --json=<file>` | 165 tests / 28 files | — | 179 / 31 |
| Playwright 1.58.1, **listed** | `npx playwright test --list --project chromium` | 28 / 5 files | — | 30 / 6 |
| Playwright, all projects | `npx playwright test --list` | 33 / 6 | — | 35 / 7 |

The 37 ask-first findings, by file (A+B): `modules/faithfulness.py` 2, `interpret_safety.py` 2, `redaction.py` 2, `verifier_agent.py` 1, `core/auth.py` 3, `core/security.py` 10, `core/profile_database.py` 12, `core/audit.py` 1, `core/migrations.py` 1, `api/profiles.py` 3. Fixing everything would touch 154 files.

**SQLCipher availability** (decides where Task 3 can run):
- `/mnt/c/Python313/python.exe -c "import sqlcipher3"` → `ModuleNotFoundError`. The Wave 0 "1241 passed" baseline therefore ran every vault unencrypted.
- WSL `python3` 3.12.3 → `ModuleNotFoundError`.
- `python3 -m pip download "sqlcipher3-binary>=0.5.0" --no-deps --only-binary=:all: --platform <p> --python-version 3.11`:
  - `win_amd64` → "No matching distribution found";
  - `manylinux2014_x86_64` → `sqlcipher3_binary-0.6.0-cp311-cp311-manylinux2014_x86_64…whl`.
- `dev.ps1:471-500` (main@40f590e) drops `sqlcipher3-binary` on Windows and runs the vault unencrypted.
- **Consequence:** the ciphertext proof can only run on Linux (CI, or the D9 venv in WSL). On native Windows it must skip loudly. In CI it must fail if it cannot run (Task 3).

---

## Task 0: Worktree, dependency proof and START measurement (repeat per PR)

**Files:** none in the repo. Write measurements outside the worktree.

- [ ] **Step 1: Create the worktree for this PR.** Run exactly one block. Every later block in this PR sets `WT` to the same absolute path.

PR-1 (G-B1):
```bash
set -o pipefail
git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral fetch origin && git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree add /mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1 -b fix/w11a-gb1-profile-guards origin/main && echo worktree-ok
```
PR-2 (G-B2):
```bash
set -o pipefail
git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral fetch origin && git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree add /mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb2 -b fix/w11a-gb2-vault-ciphertext origin/main && echo worktree-ok
```
PR-3 (G-B4):
```bash
set -o pipefail
git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral fetch origin && git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree add /mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb4 -b feat/w11a-gb4-ci-gates origin/main && echo worktree-ok
```
PR-4 (G-B6):
```bash
set -o pipefail
git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral fetch origin && git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree add /mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb6 -b docs/w11a-gb6-frontend-counts origin/main && echo worktree-ok
```

- [ ] **Step 2: Prove the tree is post-P1.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1   # gb2 / gb4 / gb6 for the other PRs
git -C "$WT" merge-base --is-ancestor 7b2ff1f HEAD && git -C "$WT" merge-base --is-ancestor 692fdf3 HEAD && echo post-P1-ok
```
Expected: `post-P1-ok`. Anything else → **STOP** (stop gate 1). Before P1 lands this STOP is the intended outcome.

- [ ] **Step 3: Prove this PR's other dependencies.** Each command must print its expected line; else **STOP**.
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1   # gb2 / gb4 / gb6 for the other PRs
# all PRs: the capstone package is on main (P0-B)
test -f "$WT/docs/capstone-report/specs-compliance-matrix.md" && echo p0b-ok
# PR-1: P5 and P7 merged
test "$(grep -c 'datetime.utcnow' "$WT/src/backend/api/profiles.py")" = 0 && echo p5-profiles-ok
grep -n "_SYNTHETIC_RESET_MODELS" "$WT/src/backend/api/profiles.py" | head -2        # non-empty = P7
grep -n "def route_client" -A8 "$WT/src/backend/tests/support/routes.py"              # must show profile_name and profile_db params
# PR-3: P5 and W-4 merged, P4 merged
grep -n "time_source_lint" "$WT/.github/workflows/ci.yml"                             # non-empty = P5
grep -n "legacy-evals:" "$WT/.github/workflows/ci.yml"                                # non-empty = W-4
git -C "$WT" log --oneline -3 -- docs/architecture/ci-and-quality-gates.md            # read: P4's commit is here
```
For PR-1, write down the exact `route_client` signature printed. Task 1 and Task 2 call it with `profile_id=`, `profile_name=` and `profile_db=` keywords. If `profile_db` is absent, **STOP** (stop gate 12).

- [ ] **Step 4: Confirm the interpreter and SQLCipher.**
```bash
set -o pipefail
~/venvs/asclexis-311/bin/python -c "import sys; assert sys.version_info[:2] == (3, 11), sys.version; print(sys.version)" || { echo "STOP: D9 venv missing or not 3.11"; exit 1; }
~/venvs/asclexis-311/bin/python -c "import sqlcipher3; print(sqlcipher3.connect(':memory:').execute('PRAGMA cipher_version').fetchone())"
```
Expected: `3.11.x …`, then a tuple such as `('4.x.x community',)`. If the venv is missing → **STOP** (D9 not executed). If `import sqlcipher3` fails in this Linux venv → **STOP** (stop gate 6).

- [ ] **Step 5: START measurement** (WSL: clear stale bytecode first, per AGENT.md).
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1; PR=gb1   # gb2 / gb4 / gb6 for the other PRs
find "$WT/src/backend" -name __pycache__ -type d -prune -exec rm -rf {} +
cd "$WT/src/backend"
~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1 | tee /mnt/c/Users/DangT/Documents/GitHub/w11a-$PR-start-collected.txt; echo "pytest exit=${PIPESTATUS[0]}"
~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q 2>&1 | tail -25 | tee /mnt/c/Users/DangT/Documents/GitHub/w11a-$PR-start-run.txt; echo "pytest exit=${PIPESTATUS[0]}"
```
Record in the PR description: interpreter, OS, command, `N tests collected`, the printed `pytest exit=` codes, and every failing node id. The collect-only exit must be 0; a non-zero run exit is expected only if START failures exist. These START failures are context and are not fixed here. The measurement files live next to the worktrees, outside every repo tree.

- [ ] **Step 6: Re-check the test-ID prefixes** (PR-1/2/3).
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1   # gb2 / gb4 for the other PRs
for p in pguard paud keyct mighead; do printf "%s " $p; git -C "$WT" grep -il "$p" HEAD -- src scripts | wc -l; done
cd "$WT/src/backend"
~/venvs/asclexis-311/bin/python -m pytest tests --collect-only -q -p no:cacheprovider -k "hc_pguard_ or hc_paud_ or hc_keyct_ or hc_mighead_" 2>&1 | tail -1; echo "pytest exit=${PIPESTATUS[0]}"
```
Expected: `0` for each prefix, and `no tests collected` (or `0 selected`), with `pytest exit=5` (pytest's "no tests collected" code). Any hit → pick a new prefix and update this plan's IDs before writing tests.

- [ ] **Step 7: Re-verify the cited lines** on this tree.
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1; cd "$WT"   # gb2 / gb4 for the other PRs
grep -nE '^@router\.|require_profile_access\(\)|audit_and_commit|log_profile_event\(' src/backend/api/profiles.py
grep -n "def require_profile_access" -A40 src/backend/core/auth.py | grep -n "path_params\|403\|Access denied"
grep -nE 'detail="(Incorrect password|Current password is incorrect|Not authenticated)"' src/backend/api/profiles.py src/backend/core/auth.py
grep -n "SQLCipher is required but not available" src/backend/core/migrations.py
grep -n "^async def audit_and_commit\|^async def log_profile_event\|^async def create_audit_log" src/backend/core/audit.py
sed -n '50,60p' src/backend/tests/conftest.py
```
Expected: 13 routes. `require_profile_access()` on `recovery-code`, `DELETE /{profile_id}`, `GET /{profile_id}`, `lock`, `change-password` (5). No audit call in `list_profiles`, `get_current_profile`, `reset_synthetic_test_profile` or `get_profile`. Detail string `"Access denied to this profile"`. `conftest.py` still sets `DATABASE_ENCRYPTION_REQUIRED` to `"false"`. Use the line numbers printed here, not the ones in this plan.

---

## Task 1 (PR-1, G-B1a): HTTP tests for `require_profile_access` on profile routes

**Files:**
- Create: `src/backend/tests/support/master_db.py`
- Modify (owned after P7): `src/backend/tests/support/routes.py` (opt-in `real_auth`)
- Create: `src/backend/tests/test_profile_route_guards.py`

**Interfaces:**
- Consumes: `route_client(router, prefix, profile_id="profile-a", profile_name="T", master_db=None, profile_db=None)` from P7 (`tests/support/routes.py`; confirm in Task 0 Step 3). `profiles_api.router`, `profiles_api.PROFILE_DELETE_CONFIRMATION`, `profiles_api.settings`, `core.auth.Session`, `core.database.Base`/`get_db`, `models.Profile`/`AuditLog`.
- Produces: `route_client(router, prefix, profile_id="profile-a", profile_name="T", master_db=None, profile_db=None, real_auth: bool = False)`. With `real_auth=True` the `require_auth` override is **not** installed, so the real `require_auth → get_current_session` chain runs (HC-PGUARD-003). With the default `False`, behaviour is byte-for-byte P7's.
- Produces (Task 2 uses these): `MasterDb(path: Path, maker: async_sessionmaker[AsyncSession])`, `make_master_db(tmp_path: Path) -> MasterDb`, `seed_profile(db: MasterDb, profile_id: str, display_name: str) -> None`, `use_master(client: TestClient, db: MasterDb) -> None`, `audit_rows(db: MasterDb) -> list[AuditLog]`, `profile_row(db: MasterDb, profile_id: str) -> Profile | None`.

These are **characterization tests**: the guard exists, so they pass on first run. Their RED is produced on purpose:
- durably, by HC-PGUARD-005, which removes the guard through `dependency_overrides` and asserts the requests then get through;
- once, manually, in Step 4.

- [ ] **Step 1: Write the helper** `src/backend/tests/support/master_db.py`:

```python
"""A real, file-backed master DB for route tests (W-11a).

route_client's default master_db is an AsyncMock. That shows an audit helper was
*called*, never that a row was *committed*. These helpers build a SQLite master
DB on disk. The request uses it through a fresh AsyncSession per request, and
the test reads it back through a separate sync connection, which only sees
committed rows.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session as SyncSession
from sqlalchemy.pool import NullPool

from core.database import Base, get_db
from core.time import utcnow
from models import AuditLog, Profile


@dataclass(frozen=True)
class MasterDb:
    path: Path
    maker: async_sessionmaker[AsyncSession]

    def sync_engine(self) -> Engine:
        return create_engine(f"sqlite:///{self.path}", poolclass=NullPool)


def make_master_db(tmp_path: Path) -> MasterDb:
    path = tmp_path / "master.db"
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    engine.dispose()
    # NullPool: every request opens its connection inside TestClient's own loop.
    async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    return MasterDb(path=path, maker=async_sessionmaker(async_engine, expire_on_commit=False))


def seed_profile(db: MasterDb, profile_id: str, display_name: str) -> None:
    now = utcnow()
    with SyncSession(db.sync_engine()) as session:
        session.add(
            Profile(
                id=profile_id,
                display_name=display_name,
                encryption_key_id=f"key-{profile_id}",
                password_hash=None,  # authenticate_profile() then refuses every password
                password_salt=base64.b64encode(b"\x00" * 16).decode("ascii"),
                is_locked=False,
                created_at=now,
                updated_at=now,
                last_accessed_at=None,
            )
        )
        session.commit()


def use_master(client: TestClient, db: MasterDb) -> None:
    async def _session() -> AsyncIterator[AsyncSession]:
        async with db.maker() as session:
            yield session

    client.app.dependency_overrides[get_db] = _session


def audit_rows(db: MasterDb) -> list[AuditLog]:
    with SyncSession(db.sync_engine(), expire_on_commit=False) as session:
        return list(session.scalars(select(AuditLog).order_by(AuditLog.timestamp)))


def profile_row(db: MasterDb, profile_id: str) -> Optional[Profile]:
    with SyncSession(db.sync_engine(), expire_on_commit=False) as session:
        return session.get(Profile, profile_id)
```

- [ ] **Step 1b: Extend `route_client` with an opt-in real-auth mode** (`src/backend/tests/support/routes.py`, owned after P7).

C-ISO-2 requires auth tests to go through `route_client`, but it always overrides `require_auth` (main@40f590e `:54`). This step makes that override opt-out.
- Read the post-P7 function first:
  ```bash
  grep -n "def route_client" -A40 /mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1/src/backend/tests/support/routes.py
  ```
- Then make exactly two edits.
- **If P7 changed the structure so that the override cannot be made conditional in one place, STOP and report.** Do not build a bare `FastAPI()` / `TestClient` in the test instead.

1. Add the keyword-only parameter last in the signature, after P7's `profile_db`:
   ```python
       profile_db: Optional[object] = None,
       real_auth: bool = False,
   ) -> Iterator[TestClient]:
   ```
   Extend the docstring with one line: "`real_auth=True` leaves `require_auth` un-overridden, so the real token check runs (401 tests)."
2. Make the existing auth override conditional; the `get_db` and P7 profile-DB overrides stay as they are:
   ```python
       if not real_auth:
           app.dependency_overrides[require_auth] = _override_auth
   ```

Check that nothing else moved:
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1; cd "$WT"
git diff --stat -- src/backend/tests/support/routes.py        # expect: 1 file, a handful of lines
git grep -n "route_client(" -- src/backend/tests | wc -l      # every existing caller still passes no real_auth
```

- [ ] **Step 2: Write the tests** `src/backend/tests/test_profile_route_guards.py`:

```python
"""HC-PGUARD — require_profile_access on api/profiles.py, over HTTP (ISO-02, C-ISO-1/2).

A route test that calls a handler as a function never runs Depends(...)
(recurring-failures #1). Every test here goes through FastAPI.
HC-PGUARD-005 removes the guard and asserts that the same requests then get
through. That proves HC-PGUARD-001's 403 comes from the guard.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

import api.profiles as profiles_api
from core.auth import Session, require_auth
from tests.support.master_db import (
    MasterDb,
    audit_rows,
    make_master_db,
    profile_row,
    seed_profile,
    use_master,
)
from tests.support.routes import route_client

OWN = "profile-a"
OTHER = "profile-b"
WRONG_PASSWORD = "Wrong-Horse-42"

# (method, path template, JSON body) for every route that carries the guard.
GUARDED = [
    pytest.param("POST", "/{pid}/recovery-code", {"password": WRONG_PASSWORD}, id="recovery-code"),
    pytest.param(
        "DELETE",
        "/{pid}",
        {
            "password": WRONG_PASSWORD,
            "confirmation_phrase": profiles_api.PROFILE_DELETE_CONFIRMATION,
            "export_acknowledged": True,
        },
        id="delete",
    ),
    pytest.param("GET", "/{pid}", None, id="get"),
    pytest.param("POST", "/{pid}/lock", None, id="lock"),
    pytest.param(
        "POST",
        "/{pid}/change-password",
        {"current_password": WRONG_PASSWORD, "new_password": "Brand-New-Pass-9"},
        id="change-password",
    ),
]

GUARDED_KEYS = {
    ("POST", "/{profile_id}/recovery-code"),
    ("DELETE", "/{profile_id}"),
    ("GET", "/{profile_id}"),
    ("POST", "/{profile_id}/lock"),
    ("POST", "/{profile_id}/change-password"),
}
# Unauthenticated by design: recover (lost password, api/profiles.py docstring
# "Unauthenticated by necessity") and unlock (password in the body).
UNAUTHENTICATED_BY_DESIGN = {
    ("POST", "/{profile_id}/recover"),
    ("POST", "/{profile_id}/unlock"),
}


@pytest.fixture
def master(tmp_path, monkeypatch) -> MasterDb:
    monkeypatch.setattr(
        type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    db = make_master_db(tmp_path)
    seed_profile(db, OWN, "Own Profile")
    seed_profile(db, OTHER, "Other Profile")
    yield db
    # Task 1 bypass requests may count a failed delete re-auth; do not leak it.
    profiles_api.auth_rate_limiter.reset(f"delete:testclient:{OTHER}")


def _send(client: TestClient, method: str, path: str, body, pid: str = OTHER):
    url = "/profiles" + path.format(pid=pid)
    if body is None:
        return client.request(method, url)
    return client.request(method, url, json=body)


def _dependency_calls(dependant):
    for dep in dependant.dependencies:
        yield dep.call
        yield from _dependency_calls(dep)


def _is_guarded(route) -> bool:
    return any(
        getattr(call, "__name__", "") == "verify_profile_access"
        for call in _dependency_calls(route.dependant)
    )


@pytest.mark.parametrize(("method", "path", "body"), GUARDED)
def test_hc_pguard_001_cross_profile_request_is_refused(master, method, path, body):
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        response = _send(client, method, path, body)

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Access denied to this profile"
    # Nothing behind the guard ran: the other profile is untouched and unaudited.
    other = profile_row(master, OTHER)
    assert other is not None and other.is_locked is False
    assert audit_rows(master) == []


def test_hc_pguard_002_own_profile_passes_the_guard(master):
    """Positive control: the guard reads the right path param. A guard that read a
    missing param would 400 every request (the restore-endpoint bug)."""
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        response = client.get(f"/profiles/{OWN}")

    assert response.status_code == 200, response.text
    assert response.json()["id"] == OWN


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer not-a-jwt"}],
    ids=["no-token", "malformed-token"],
)
def test_hc_pguard_003_unauthenticated_request_is_401(master, headers):
    """route_client(real_auth=True): the real require_auth -> get_current_session
    chain runs, so a missing or malformed token must be refused before the guard."""
    with route_client(profiles_api.router, "/profiles", real_auth=True) as client:
        assert require_auth not in client.app.dependency_overrides  # harness really opted out
        use_master(client, master)
        response = client.get(f"/profiles/{OTHER}", headers=headers)

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Not authenticated"  # core/auth.py require_auth


def test_hc_pguard_004_every_profile_id_route_is_guarded():
    guarded_seen = set()
    all_keys = set()
    for route in profiles_api.router.routes:
        for method in route.methods:
            key = (method, route.path)
            all_keys.add(key)
            guarded = _is_guarded(route)
            if guarded:
                assert "{profile_id}" in route.path, (
                    f"{key} carries require_profile_access but has no {{profile_id}} "
                    "path param: every request would 400 (recurring-failures #1)"
                )
            if "{profile_id}" in route.path and key not in UNAUTHENTICATED_BY_DESIGN:
                assert guarded, f"{key} takes a profile_id but is not behind require_profile_access"
                guarded_seen.add(key)

    assert guarded_seen == GUARDED_KEYS
    assert UNAUTHENTICATED_BY_DESIGN <= all_keys


# What each handler does once the guard is gone (session = OWN, path = OTHER).
# OTHER is seeded with password_hash=None, so authenticate_profile() refuses
# every password. Strings verified at main@40f590e api/profiles.py (unchanged
# at B/A): :611, :828, :1103. Task 0 Step 7 re-verifies them post-P5/P7.
BYPASS_EXPECT = [
    pytest.param("POST", "/{pid}/recovery-code", {"password": WRONG_PASSWORD},
                 401, "Incorrect password", id="recovery-code"),
    pytest.param("DELETE", "/{pid}",
                 {"password": WRONG_PASSWORD,
                  "confirmation_phrase": profiles_api.PROFILE_DELETE_CONFIRMATION,
                  "export_acknowledged": True},
                 401, "Incorrect password", id="delete"),
    pytest.param("GET", "/{pid}", None, 200, None, id="get"),
    pytest.param("POST", "/{pid}/lock", None, 200, None, id="lock"),
    pytest.param("POST", "/{pid}/change-password",
                 {"current_password": WRONG_PASSWORD, "new_password": "Brand-New-Pass-9"},
                 401, "Current password is incorrect", id="change-password"),
]


@pytest.mark.parametrize(("method", "path", "body", "status", "detail"), BYPASS_EXPECT)
def test_hc_pguard_005_without_the_guard_the_same_request_gets_through(
    master, monkeypatch, method, path, body, status, detail
):
    """Mutation control (break-it, kept in CI): override every guard instance with
    a pass-through, then assert the EXACT response each handler gives and the
    side effect it has. A 500, a 422 or any other surprise fails here, so this
    cannot pass by accident."""
    monkeypatch.setattr(profiles_api, "revoke_jwt_token", lambda *a, **k: None)
    monkeypatch.setattr(profiles_api, "close_profile_database_on_logout", AsyncMock())

    # No timestamp is built here. The pass-through hands back the Session that
    # route_client's require_auth override already produced, so this test never
    # constructs a datetime. (Session.expires_at is compared against an AWARE
    # now in core/auth.py Session.is_expired; a naive core.time.utcnow() value
    # there would raise TypeError, so neither form is written in this file.)
    async def _pass_through(session: Session = Depends(require_auth)) -> Session:
        return session

    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        overridden = 0
        for route in profiles_api.router.routes:
            for call in _dependency_calls(route.dependant):
                if getattr(call, "__name__", "") == "verify_profile_access":
                    client.app.dependency_overrides[call] = _pass_through
                    overridden += 1
        assert overridden == 5, f"expected 5 guard instances, overrode {overridden}"
        response = _send(client, method, path, body)

    assert response.status_code == status, response.text
    other = profile_row(master, OTHER)
    vault_dir = master.path.parent / "vaults" / OTHER
    if detail is not None:
        # The handler ran and refused on its own re-auth, before any file or row change.
        assert response.json()["detail"] == detail
        assert other is not None and other.is_locked is False and other.password_hash is None
        assert not vault_dir.exists(), f"handler touched {vault_dir} before re-auth"
        assert audit_rows(master) == []
    elif method == "GET":
        # The leak the guard prevents: OWN's session reads OTHER's profile.
        assert response.json()["id"] == OTHER
        assert response.json()["display_name"] == "Other Profile"
    else:  # lock
        # The side effect HC-PGUARD-001 checks for is real: OWN's session locks
        # OTHER, and the lock is committed and audited under OTHER's id.
        assert other.is_locked is True
        assert [(r.event_type, r.profile_id) for r in audit_rows(master)] == [
            ("profile.lock", OTHER)
        ]


def test_hc_pguard_006_profile_id_match_is_exact(master):
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        response = client.get(f"/profiles/{OWN.upper()}")

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Access denied to this profile"
```

- [ ] **Step 3: Run the new tests.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1; cd "$WT/src/backend"
~/venvs/asclexis-311/bin/python -m pytest tests/test_profile_route_guards.py -p no:cacheprovider -v -k hc_pguard_
```
Expected: `15 passed`. That is 001×5 + 002 + 003×2 + 004 + 005×5 + 006.

Then prove the `routes.py` default is unchanged for every existing caller:
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1; cd "$WT/src/backend"
FILES=$(grep -rl "route_client" tests --include="test_*.py" | grep -v test_profile_route_guards.py)
test -n "$FILES" || { echo "STOP: no existing route_client callers found"; exit 1; }
~/venvs/asclexis-311/bin/python -m pytest $FILES -p no:cacheprovider -q 2>&1 | tail -5; echo "pytest exit=${PIPESTATUS[0]}"
```
Expected: `pytest exit=0`, with the same pass count as these files at START (Task 0 Step 5 run).

If any HC-PGUARD-005 case returns a status or detail other than its `BYPASS_EXPECT` row, the handler differs from the one verified on main@40f590e. **STOP**, read the handler, and correct the expectation only if the new behaviour is itself safe. Never loosen the assertion to a range.

If HC-PGUARD-003[malformed-token] errors while writing a JWT secret file, patch `app_data_path` as the `master` fixture already does. Report the path it tried.

- [ ] **Step 4: Break it on purpose once in the real file, in a disposable detached worktree.** `api/profiles.py` is read-only in Task 1, so the phase worktree is never edited. The throwaway worktree gets the uncommitted Task 1 files (including the `routes.py` extension) copied in; then `get_profile`'s guard is replaced by plain `RequireAuth` there.
```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1; BRK=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1-break
git -C "$WT" worktree add --detach "$BRK" HEAD || { echo "STOP: could not create $BRK"; exit 1; }
cp "$WT/src/backend/tests/support/master_db.py" "$BRK/src/backend/tests/support/master_db.py" \
  && cp "$WT/src/backend/tests/support/routes.py" "$BRK/src/backend/tests/support/routes.py" \
  && cp "$WT/src/backend/tests/test_profile_route_guards.py" "$BRK/src/backend/tests/test_profile_route_guards.py" \
  || { echo "STOP: copy failed"; git -C "$WT" worktree remove --force "$BRK"; exit 1; }
python3 - "$BRK/src/backend/api/profiles.py" <<'EOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding="utf-8")
head, sep, tail = s.partition("async def get_profile(")
assert sep, "get_profile not found"
old = "session: Session = Depends(require_profile_access()),"
assert old in tail.split("async def ", 1)[0], "guard line not found in get_profile"
p.write_text(head + sep + tail.replace(old, "session: RequireAuth,", 1), encoding="utf-8")
print("guard removed from get_profile (disposable worktree only)")
EOF
test "$(git -C "$BRK" diff --name-only -- src/backend/api/profiles.py)" = "src/backend/api/profiles.py" || { echo "STOP: guard removal did not apply"; git -C "$WT" worktree remove --force "$BRK"; exit 1; }
cd "$BRK/src/backend"
~/venvs/asclexis-311/bin/python -m pytest tests/test_profile_route_guards.py -p no:cacheprovider -q -k "hc_pguard_001 or hc_pguard_004 or hc_pguard_006" 2>&1 | tail -15; echo "pytest exit=${PIPESTATUS[0]}"
git -C "$WT" worktree remove --force "$BRK" && git -C "$WT" diff --exit-code -- src/backend/api/profiles.py && echo phase-worktree-untouched
```
Expected RED (`pytest exit=1`), exactly `3 failed, 4 passed` (7 selected: 001×5, 004, 006), and these three:
- HC-PGUARD-001[get]: `assert 200 == 403`;
- HC-PGUARD-004: `('GET', '/{profile_id}') takes a profile_id but is not behind require_profile_access`;
- HC-PGUARD-006: `assert 200 == 403`.

Last line: `phase-worktree-untouched`.

- [ ] **Step 5: What would these tests fail to notice?** Put this in the PR description.
- A guard bug that only appears with a *valid* real JWT. HC-PGUARD-003 runs the real `require_auth` (`real_auth=True`) but only for missing or malformed tokens; the other tests fake `require_auth`.
- Guards on routers other than `api/profiles.py`.
- Whether denied attempts are audited. They are not; that would be a `core/auth.py` change and is out of scope.

- [ ] **Baseline count (same commit, CLAUDE.md rule).** This commit changes the collected count, so it also updates **only the collected number** in the `CLAUDE.md` baseline sentence ("**N backend tests collected.**") and in the `AGENT.md` Commands comment ("(N collected; …)"), taking N from:
  ```bash
  set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1; cd "$WT/src/backend"
  ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1; echo "pytest exit=${PIPESTATUS[0]}"
  ```
  Leave every pass-count sentence ("all N pass", "N pass in CI, N−1 without an embedding model") unchanged unless a pass count was measured in this PR in a named environment (interpreter + embedding model present/absent). Otherwise flag it in the PR. Never write a collected number into a pass-count slot.

- [ ] **Step 6: Commit** (C-GATE-3).
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1; cd "$WT"
git add src/backend/tests/support/master_db.py src/backend/tests/support/routes.py src/backend/tests/test_profile_route_guards.py CLAUDE.md AGENT.md
git diff --cached --name-only   # expect exactly these 5 paths
git commit -m "fix(profiles): prove require_profile_access over HTTP on every guarded profile route (ISO-02)

HC-PGUARD-001..006. Includes a mutation control that removes the guard and
asserts the same requests get through, so the 403 is proven to come from it.
route_client gains opt-in real_auth (default unchanged) for the 401 tests.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/tests/support/master_db.py src/backend/tests/support/routes.py src/backend/tests/test_profile_route_guards.py CLAUDE.md AGENT.md
```

---

## Task 2 (PR-1, G-B1b): audit rows on the four unaudited profile routes — OWNER-GATED (OG-1)

**Gate:** start only if OG-1 in §11 is signed. `GET /` (HC-PAUD-006) needs Q-AUD-LIST = (a) as well.
- **OG-1 unsigned:** skip this task. PR-1 ships Task 1 only, and Task 10 records AUD-02 as still **partial**.
- **Q-AUD-LIST = (b):** omit HC-PAUD-006 and the `list_profiles` edit. Task 10 records the exemption in AUD-02 / C-AUDIT-1 as "owner-exempted (date)".

**Files:**
- Create: `src/backend/tests/test_profile_route_audit.py`
- Modify: `src/backend/api/profiles.py`. On main@40f590e: import line `:51`; `list_profiles` `:241-252`; `get_current_profile` `:416-435`; `reset_synthetic_test_profile` `:477-532`; `get_profile` `:943-963`. Re-verify post-P5/P7 (Task 0 Step 7).

**Interfaces:**
- Consumes: Task 1's `tests/support/master_db.py`; P7's `route_client(..., profile_name=..., profile_db=...)` and `profiles_api._SYNTHETIC_RESET_MODELS`; `core.audit.audit_and_commit(db, log_fn, **kwargs)` (B@7b2ff1f `:474`); `log_profile_event(db, event, profile_id, profile_name, details=None)` (`:271`); `create_audit_log(db, event_type, action, profile_id=None, entity_type=None, entity_id=None, details=None)` (`:201`).
- Produces: the audit rows listed below.

| Route | `event_type` | `action` | `profile_id` | `details` |
|---|---|---|---|---|
| `GET /me` | `profile.view` | `profile.view` | session profile | none |
| `GET /{profile_id}` | `profile.view` | `profile.view` | path = session profile | none |
| `POST /test/reset` | `profile.test_reset` | `profile.test_reset` | session profile | `{"count": len(_SYNTHETIC_RESET_MODELS)}` |
| `GET /` (Q-AUD-LIST a) | `profile.list` | `profile.list` | `NULL` | `{"count": <profiles returned>}` |

About the `action` values:
- `action` equals `event_type` on purpose. `log_profile_event`'s `action_map` has no `view` or `test_reset` entry, so it falls back to `f"profile.{event}"`, which equals `event_type`. `_scrub_action` (B@7b2ff1f `:173-193`) then keeps it without the "unregistered action" warning.
- A human-readable string would need a new `ALLOWED_ACTIONS` entry in `core/audit.py`. That is out of scope.

- [ ] **Step 1: Write the failing tests** `src/backend/tests/test_profile_route_audit.py`:

```python
"""HC-PAUD — the four previously unaudited profile routes write committed,
PHI-free audit rows (AUD-02, C-AUDIT-1). Rows are read back through a separate
connection, so an audit row that was only add()ed and never committed is missed."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import api.profiles as profiles_api
import models  # noqa: F401  registers every profile model on ProfileDatabaseBase
import models.response_feedback  # noqa: F401  not re-exported by models/__init__ (plan 07)
from core.profile_database import ProfileDatabaseBase
from tests.support.master_db import audit_rows, make_master_db, seed_profile, use_master
from tests.support.routes import route_client

OWN = "profile-a"
OTHER = "profile-b"
OWN_NAME = "Jane Canary Own"                   # must never reach an audit row
PLAYWRIGHT_NAME = "Playwright E2E Jane Canary"  # passes the reset name gate


@pytest.fixture
def master(tmp_path, monkeypatch):
    monkeypatch.setattr(
        type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    db = make_master_db(tmp_path)
    seed_profile(db, OWN, OWN_NAME)
    seed_profile(db, OTHER, "Other Canary")
    return db


@pytest.fixture
def vault_maker(tmp_path):
    """A plain SQLite profile DB with every ORM profile table. If P7's reset also
    clears the FTS `search_records*` tables (N-02), create them here the same way
    tests/test_profile_test_reset.py does."""
    path = tmp_path / "vault.db"
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    ProfileDatabaseBase.metadata.create_all(engine)
    engine.dispose()
    async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    return path, async_sessionmaker(async_engine, expire_on_commit=False)


def _summary(rows):
    return [(r.event_type, r.profile_id, r.entity_type, r.entity_id) for r in rows]


def test_hc_paud_001_get_me_writes_a_committed_audit_row(master):
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        response = client.get("/profiles/me")

    assert response.status_code == 200, response.text
    assert _summary(audit_rows(master)) == [("profile.view", OWN, "profile", OWN)]


def test_hc_paud_002_get_profile_writes_a_committed_audit_row(master):
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        response = client.get(f"/profiles/{OWN}")

    assert response.status_code == 200, response.text
    assert _summary(audit_rows(master)) == [("profile.view", OWN, "profile", OWN)]


def test_hc_paud_003_test_reset_writes_a_committed_audit_row(master, vault_maker, monkeypatch):
    monkeypatch.setattr(profiles_api.settings, "app_env", "development")
    _, maker = vault_maker
    with route_client(
        profiles_api.router, "/profiles",
        profile_id=OWN, profile_name=PLAYWRIGHT_NAME, profile_db=maker,
    ) as client:
        use_master(client, master)
        response = client.post("/profiles/test/reset")

    assert response.status_code == 204, response.text
    rows = audit_rows(master)
    assert _summary(rows) == [("profile.test_reset", OWN, "profile", OWN)]
    assert json.loads(rows[0].details_json) == {
        "count": len(profiles_api._SYNTHETIC_RESET_MODELS)
    }


def test_hc_paud_004_failed_reset_leaves_no_reset_audit_row(master, vault_maker, monkeypatch):
    """Order of effects: the row is written only after the vault commit succeeds."""
    monkeypatch.setattr(profiles_api.settings, "app_env", "development")
    path, maker = vault_maker
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE embeddings"))  # delete(Embedding) now raises
    engine.dispose()

    with route_client(
        profiles_api.router, "/profiles",
        profile_id=OWN, profile_name=PLAYWRIGHT_NAME, profile_db=maker,
    ) as client:
        use_master(client, master)
        response = client.post("/profiles/test/reset")

    assert response.status_code == 500, response.text
    assert response.json()["detail"].startswith("Synthetic profile reset failed")
    assert [r.event_type for r in audit_rows(master)] == []


def test_hc_paud_005_profile_audit_rows_carry_no_display_name(master, vault_maker, monkeypatch):
    monkeypatch.setattr(profiles_api.settings, "app_env", "development")
    _, maker = vault_maker
    with route_client(
        profiles_api.router, "/profiles",
        profile_id=OWN, profile_name=PLAYWRIGHT_NAME, profile_db=maker,
    ) as client:
        use_master(client, master)
        assert client.get("/profiles/me").status_code == 200
        assert client.get(f"/profiles/{OWN}").status_code == 200
        assert client.post("/profiles/test/reset").status_code == 204

    rows = audit_rows(master)
    assert len(rows) == 3, "expected one row per request"
    for row in rows:
        blob = " ".join(
            str(v) for v in (row.event_type, row.action, row.entity_type,
                             row.entity_id, row.details_json, row.client_info)
        )
        assert "Canary" not in blob, f"display name leaked into audit row: {blob}"


def test_hc_paud_006_list_profiles_writes_one_unattributed_audit_row(master):
    """Q-AUD-LIST option (a) only. Delete this test if the owner chose (b)."""
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        response = client.get("/profiles/")

    assert response.status_code == 200, response.text
    rows = audit_rows(master)
    assert [(r.event_type, r.profile_id) for r in rows] == [("profile.list", None)]
    assert json.loads(rows[0].details_json) == {"count": 2}


def test_hc_paud_007_audit_failure_does_not_serve_the_profile(master, monkeypatch):
    """audit_and_commit is fail-closed: a read that cannot be audited is not served."""
    async def _boom(**_kwargs):
        raise RuntimeError("audit store down")

    monkeypatch.setattr(profiles_api, "log_profile_event", _boom)
    with route_client(profiles_api.router, "/profiles", profile_id=OWN) as client:
        use_master(client, master)
        with pytest.raises(RuntimeError, match="audit store down"):
            client.get("/profiles/me")
```

- [ ] **Step 2: Run them and see RED.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1; cd "$WT/src/backend"
~/venvs/asclexis-311/bin/python -m pytest tests/test_profile_route_audit.py -p no:cacheprovider -q -k hc_paud_
```
Expected: 5 failed, 2 passed.

| Test | Result before the route edit |
|---|---|
| 001, 002 | fail: `assert [] == [('profile.view', 'profile-a', 'profile', 'profile-a')]` |
| 003 | fails: `assert [] == [('profile.test_reset', …)]` |
| 005 | fails: `AssertionError: expected one row per request` (`0 == 3`) |
| 006 | fails: `assert [] == [('profile.list', None)]` |
| 007 | fails: `Failed: DID NOT RAISE <class 'RuntimeError'>` |
| 004 | passes, because no audit is written at all yet. Its RED comes in Step 6 |

Any *other* failure (fixture error, import error, 404/422) means the setup is wrong. Fix the test setup, never the assertion.

- [ ] **Step 3: Implement.** Minimal edits to `src/backend/api/profiles.py`. Adapt to the post-P7 text of the reset route, keeping the audit call **after** the vault commit and **outside** the `try/except`.

Import (main@40f590e `:51`):
```python
from core.audit import audit_and_commit, create_audit_log, log_profile_event
```

`get_current_profile`: replace `return ProfileResponse.from_model(profile)` with:
```python
    response = ProfileResponse.from_model(profile)
    # AUD-02 / C-AUDIT-1: a profile read is audited. audit_and_commit is
    # fail-closed: if the row cannot be written, the profile is not served.
    await audit_and_commit(
        db, log_profile_event, event="view",
        profile_id=profile.id, profile_name=profile.display_name,
    )
    return response
```

`get_profile`: the same replacement, with `profile_id=profile.id`.

`reset_synthetic_test_profile`:
- Add `db: AsyncSession = Depends(get_db),` after `profile_db: ProfileDbSession,`.
- Insert before the final `return Response(status_code=status.HTTP_204_NO_CONTENT)`, after the `try/except`:
```python
    # AUD-02: written only after the vault commit, so a failed reset leaves no
    # row claiming it happened (HC-PAUD-004). Outside the try: an audit failure
    # must not be reported as "Synthetic profile reset failed".
    await audit_and_commit(
        db, log_profile_event, event="test_reset",
        profile_id=session.profile_id, profile_name=session.profile_name,
        details={"count": len(_SYNTHETIC_RESET_MODELS)},
    )
```

`list_profiles`, **only under Q-AUD-LIST (a)**: replace `return [ProfileListResponse.from_model(p) for p in profiles]` with:
```python
    response = [ProfileListResponse.from_model(p) for p in profiles]
    # AUD-02: unauthenticated entry point, so there is no actor to record.
    # profile_id stays NULL; only the count is kept (display names are PHI).
    await audit_and_commit(
        db, create_audit_log, event_type="profile.list", action="profile.list",
        entity_type="profile", details={"count": len(response)},
    )
    return response
```

- [ ] **Step 4: GREEN.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1; cd "$WT/src/backend"
~/venvs/asclexis-311/bin/python -m pytest tests/test_profile_route_audit.py tests/test_profile_route_guards.py tests/test_profile_test_reset.py tests/test_audit_phi_minimization.py -p no:cacheprovider -q
```
Expected: all pass, including P7's HC-RESET tests. HC-PAUD is `7 passed`, or `6 passed` without 006.

- [ ] **Step 5: Break it on purpose (a).** `api/profiles.py` is this task's own owned file (OG-1), so the break happens in the phase worktree and is undone by hand before the commit; Step 6 ends with a diff check. Run pytest from `/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1/src/backend`. Comment out the `audit_and_commit` call in `get_current_profile`, then run `-k "hc_paud_001 or hc_paud_007"`.
- Expected RED: 001 `assert [] == [...]`; 007 `DID NOT RAISE`.
- Restore the line and re-run for GREEN.

- [ ] **Step 6: Break it on purpose (b), order of effects.** Move the reset audit call to just **before** the delete loop, inside the `try`. Run `-k hc_paud_004`.
- Expected RED: `assert ['profile.test_reset'] == []`. The row was committed before the failure.
- Move it back and re-run for GREEN.
- Then `git diff src/backend/api/profiles.py` must show only the Step 3 hunks.

- [ ] **Step 7: Re-walk the whole flow** (recurring-failures #2). Ask what every other caller now believes:
- Playwright's `src/frontend/e2e/support/auth.ts:51` calls `POST /profiles/test/reset`. It now also writes a master audit row; its request is unchanged.
- The frontend's profile selector calls `GET /profiles/`. Under (a), every load writes one NULL-profile row. Retention is unbounded (AUD-03, owner-gated), and the PR states this.
- Backup scoping: `scripts/backup.py:281` (B@7b2ff1f) deletes `WHERE profile_id IS NULL OR profile_id != ?`. New NULL-profile `profile.list` rows are therefore excluded from a profile-scoped backup (recurring-failures #7). Verify with:
  ```bash
  grep -n "IS NULL OR profile_id" /mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1/src/backend/scripts/backup.py
  ```
- Profile deletion purges `audit_logs WHERE profile_id == ?` (main@40f590e `api/profiles.py:908`). NULL rows carry no profile id and are not purged. State this in the PR.

- [ ] **Step 8: What would these tests fail to notice?** Put this in the PR description.
- Log output (`core/audit.py` echoes each row at INFO, B@7b2ff1f `:257-264`). It holds the scrubbed action only; HC-AUD tests already cover it.
- Audit volume under real traffic.
- Routes outside `api/profiles.py`.

- [ ] **Baseline count (same commit, CLAUDE.md rule).** This commit changes the collected count, so it also updates **only the collected number** in the `CLAUDE.md` baseline sentence ("**N backend tests collected.**") and in the `AGENT.md` Commands comment ("(N collected; …)"), taking N from:
  ```bash
  set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1; cd "$WT/src/backend"
  ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1; echo "pytest exit=${PIPESTATUS[0]}"
  ```
  Leave every pass-count sentence ("all N pass", "N pass in CI, N−1 without an embedding model") unchanged unless a pass count was measured in this PR in a named environment (interpreter + embedding model present/absent). Otherwise flag it in the PR. Never write a collected number into a pass-count slot.

- [ ] **Step 9: Commit.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1; cd "$WT"
git add src/backend/api/profiles.py src/backend/tests/test_profile_route_audit.py CLAUDE.md AGENT.md
git diff --cached --name-only   # expect exactly these 4 paths
git commit -m "fix(profiles): audit profile reads and the synthetic test reset (AUD-02)

Owner-approved route edit (OG-1, <date>). GET /me, GET /{profile_id} and
POST /test/reset write committed, PHI-free audit rows via audit_and_commit;
the reset row is written only after the vault commit. GET / per Q-AUD-LIST.
HC-PAUD-001..007.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/api/profiles.py src/backend/tests/test_profile_route_audit.py CLAUDE.md AGENT.md
```

---

## Task 3 (PR-2, G-B2): on-disk ciphertext test with encryption required — OWNER CONFIRMATION (OG-2) before commit

**Is owner approval needed?** This task edits no encryption code; it adds one test file. CLAUDE.md §1 gates *touching* auth/encryption files, which this does not. The program's G-B2 row does say "encryption: ask first", so this plan treats it conservatively:
- write and run the test freely;
- **commit only after OG-2 is signed.**

**Files:**
- Create: `src/backend/tests/security/test_vault_ciphertext.py`
- No change to `tests/conftest.py`, `core/profile_database.py`, `core/migrations.py`, `core/security.py` or `core/sqlcipher_driver.py`.

**Interfaces:**
- Consumes (read-only, main@40f590e, unchanged at B/A):
  - `get_profile_db_manager().open_profile_database(profile_id, password)` (`core/profile_database.py:259`);
  - `.close_profile_database(profile_id)` (`:405`);
  - `ProfileDatabaseConnection.get_session()`, which commits on exit (`:74-85`);
  - `seal_key_with_dpapi(key, fallback_password=, force_password=True)` (`core/security.py:323-327`);
  - `generate_encryption_key()` (`:184`);
  - `core.sqlcipher_driver.SQLCIPHER_AVAILABLE` / `is_sqlcipher_available()` (`:11-22`);
  - `settings.database_encryption_required` (`core/config.py:40`, B@7b2ff1f).
- Produces: `_require_sqlcipher() -> None` and `_assert_vault_ciphertext(vault_dir: Path, canary: str) -> None`, both module-private.

**Skip-vs-fail semantics** (the core of this task):
- **Linux venv or CI with `sqlcipher3`:** HC-KEYCT-001/002 run.
- **`sqlcipher3` missing and `CI=true`** (set by GitHub Actions on every step) **or `HC_REQUIRE_SQLCIPHER=1`:** they **fail**.
- **Otherwise** (native Windows, where no wheel exists): they **skip**, with a reason that says how to force them.
- HC-KEYCT-005 pins this logic.
- HC-KEYCT-003/004 need no SQLCipher and run everywhere.

- [ ] **Step 1: Write the tests** `src/backend/tests/security/test_vault_ciphertext.py`:

```python
"""HC-KEYCT — a profile vault is ciphertext on disk (KEY-02, C-KEY-1).

The suite runs with DATABASE_ENCRYPTION_REQUIRED=false (tests/conftest.py), so
no other pytest proves a vault file is encrypted. These tests turn the
requirement back on for themselves and read the raw bytes.

sqlcipher3-binary publishes Linux wheels only (no win_amd64), so on native
Windows HC-KEYCT-001/002 skip. In CI (CI=true) or with HC_REQUIRE_SQLCIPHER=1
a missing sqlcipher3 is a FAILURE, never a skip (HC-KEYCT-005).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import aiosqlite.core
import pytest
from sqlalchemy import text

import core.sqlcipher_driver as sqlcipher_driver
from core.config import settings
from core.profile_database import get_profile_db_manager
from core.security import generate_encryption_key, seal_key_with_dpapi

SQLITE_PLAINTEXT_HEADER = b"SQLite format 3\x00"
PROFILE = "hc-keyct-profile"
PASSWORD = "Keyct-Pass-2026"
CANARY = "HC-KEYCT-CANARY-glucose-7f3a"


def _require_sqlcipher() -> None:
    if sqlcipher_driver.is_sqlcipher_available():
        return
    if os.environ.get("CI", "").lower() == "true" or os.environ.get("HC_REQUIRE_SQLCIPHER") == "1":
        pytest.fail(
            "KEY-02: sqlcipher3 is not importable, but CI / HC_REQUIRE_SQLCIPHER=1 requires "
            "the on-disk ciphertext proof. Install sqlcipher3-binary (Linux).",
            pytrace=False,
        )
    pytest.skip(
        "KEY-02 needs sqlcipher3 (Linux wheel only). "
        "Set HC_REQUIRE_SQLCIPHER=1 to turn this skip into a failure."
    )


def _assert_vault_ciphertext(vault_dir: Path, canary: str) -> None:
    db = vault_dir / "vault.db"
    assert db.exists(), f"{db} was never written"
    assert db.read_bytes()[:16] != SQLITE_PLAINTEXT_HEADER, (
        "vault.db has a plaintext SQLite header: the vault is NOT encrypted"
    )
    for sidecar in sorted(vault_dir.glob("vault.db*")):
        assert canary.encode() not in sidecar.read_bytes(), (
            f"canary found in plaintext in {sidecar.name}"
        )
    conn = sqlite3.connect(db)  # stdlib sqlite3, no key
    try:
        with pytest.raises(sqlite3.DatabaseError, match="file is not a database"):
            conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
    finally:
        conn.close()


@pytest.fixture
def vault_dir(tmp_path, monkeypatch) -> Path:
    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))
    monkeypatch.setattr(settings, "database_encryption_required", True)
    vault = tmp_path / "vaults" / PROFILE
    vault.mkdir(parents=True)
    sealed, method = seal_key_with_dpapi(
        generate_encryption_key(), fallback_password=PASSWORD, force_password=True
    )
    (vault / "key.bin").write_bytes(sealed)
    (vault / "key.method").write_text(method)
    return vault


async def _write_canary_and_close() -> None:
    manager = get_profile_db_manager()
    connection = await manager.open_profile_database(PROFILE, PASSWORD)
    try:
        async with connection.get_session() as session:
            await session.execute(text("CREATE TABLE hc_keyct_probe (note TEXT NOT NULL)"))
            await session.execute(
                text("INSERT INTO hc_keyct_probe (note) VALUES (:n)"), {"n": CANARY}
            )
    finally:
        await manager.close_profile_database(PROFILE)


@pytest.mark.asyncio
async def test_hc_keyct_001_vault_file_is_ciphertext_on_disk(vault_dir):
    _require_sqlcipher()
    await _write_canary_and_close()
    _assert_vault_ciphertext(vault_dir, CANARY)


@pytest.mark.asyncio
async def test_hc_keyct_002_the_same_vault_reopens_with_its_key(vault_dir):
    """Positive control: the bytes are a valid SQLCipher DB, not just garbage."""
    _require_sqlcipher()
    await _write_canary_and_close()
    manager = get_profile_db_manager()
    connection = await manager.open_profile_database(PROFILE, PASSWORD)
    try:
        async with connection.get_session() as session:
            note = (await session.execute(text("SELECT note FROM hc_keyct_probe"))).scalar_one()
    finally:
        await manager.close_profile_database(PROFILE)
    assert note == CANARY


@pytest.mark.asyncio
async def test_hc_keyct_003_negative_control_plaintext_vault_is_caught(vault_dir, monkeypatch):
    """Break-it, kept in CI: with SQLCipher off, the real open path writes a
    plaintext vault, and the assertion helper must catch it."""
    monkeypatch.setattr(settings, "database_encryption_required", False)
    monkeypatch.setattr(sqlcipher_driver, "SQLCIPHER_AVAILABLE", False)
    monkeypatch.setattr(aiosqlite.core, "sqlite3", sqlite3)  # undo any earlier sqlcipher patch
    await _write_canary_and_close()
    with pytest.raises(AssertionError, match="plaintext SQLite header"):
        _assert_vault_ciphertext(vault_dir, CANARY)


@pytest.mark.asyncio
async def test_hc_keyct_004_required_encryption_without_sqlcipher_fails_closed(vault_dir, monkeypatch):
    monkeypatch.setattr(sqlcipher_driver, "SQLCIPHER_AVAILABLE", False)
    monkeypatch.setattr(aiosqlite.core, "sqlite3", sqlite3)
    # core/migrations.py:213-217 (main@40f590e) refuses before any file is created.
    with pytest.raises(RuntimeError, match="SQLCipher is required but not available"):
        await get_profile_db_manager().open_profile_database(PROFILE, PASSWORD)
    assert not (vault_dir / "vault.db").exists(), "a vault file was written despite the refusal"
    assert not get_profile_db_manager().is_profile_open(PROFILE)


@pytest.mark.parametrize(
    ("env", "outcome"),
    [({"CI": "true"}, "fail"), ({"HC_REQUIRE_SQLCIPHER": "1"}, "fail"), ({}, "skip")],
    ids=["ci", "forced", "local"],
)
def test_hc_keyct_005_missing_sqlcipher_fails_in_ci_and_skips_locally(monkeypatch, env, outcome):
    monkeypatch.setattr(sqlcipher_driver, "SQLCIPHER_AVAILABLE", False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("HC_REQUIRE_SQLCIPHER", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    expected = pytest.fail.Exception if outcome == "fail" else pytest.skip.Exception
    with pytest.raises(expected):
        _require_sqlcipher()
```

- [ ] **Step 2: Run in the Linux D9 venv, forcing the no-skip mode.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb2; cd "$WT/src/backend"
HC_REQUIRE_SQLCIPHER=1 ~/venvs/asclexis-311/bin/python -m pytest tests/security/test_vault_ciphertext.py -p no:cacheprovider -v -rs -k hc_keyct_
```
Expected: `7 passed`, with **0 skipped**: 001, 002, 003, 004 and 005×3.
- Before this task the file does not exist, so the "red" state for KEY-02 is "no test". The RED for this suite is Steps 3–4.
- If HC-KEYCT-001 fails on its header or canary assertion in this correctly configured venv, that is a **real encryption finding**. **STOP**. Follow the security response protocol and report to the owner. Do not edit encryption code (stop gate 7).

- [ ] **Step 3: Break it on purpose, durable.** HC-KEYCT-003 is the break-it: it runs the real `open_profile_database` path with SQLCipher disabled and asserts that the check catches the plaintext file. Confirm it would be RED if the helper were weakened. Temporarily change `!= SQLITE_PLAINTEXT_HEADER` to `!= b"x"` in `_assert_vault_ciphertext` (this task's own new test file, not a read-only file), then run `-k hc_keyct_003` from `/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb2/src/backend`.
- Expected RED: `Failed: DID NOT RAISE <class 'AssertionError'>`.
- Restore the line.
- This plan does **not** break `core/profile_database.py` itself: that would be an edit to an encryption file.

- [ ] **Step 4: Prove "fails in CI, not skips".** Run the real tests in an interpreter *without* sqlcipher3, with `CI=true`. The Windows 3.13 install has no sqlcipher3 (measured):
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb2; cd "$WT/src/backend"
CI=true /mnt/c/Python313/python.exe -B -m pytest tests/security/test_vault_ciphertext.py -p no:cacheprovider -q -rs -k "hc_keyct_001 or hc_keyct_002"
```
Expected RED: `2 failed` with "KEY-02: sqlcipher3 is not importable, but CI / HC_REQUIRE_SQLCIPHER=1 requires …".

Then without `CI`:
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb2; cd "$WT/src/backend"
env -u CI /mnt/c/Python313/python.exe -B -m pytest tests/security/test_vault_ciphertext.py -p no:cacheprovider -q -rs -k "hc_keyct_001 or hc_keyct_002"
```
Expected: `2 skipped`, with the "Set HC_REQUIRE_SQLCIPHER=1" reason in the `-rs` summary.

If the Windows interpreter cannot import the backend at all, record `UNMEASURED` and why. HC-KEYCT-005 still proves the logic.

- [ ] **Step 5: What would these tests fail to notice?** Put this in the PR description.
- **Documents:** encrypted document files under `vaults/<id>/docs/` are not checked.
- **Master DB:** the master DB is plaintext by design (AUD-04).
- **Key strength:** a weak key is not detected. The test proves ciphertext exists, not that the key is strong.
- **CI with sqlcipher3 installed:** in CI the test runs only if `sqlcipher3` is importable there. If it is not, CI turns red. That is the intended outcome, and an owner-level finding.

- [ ] **Baseline count (same commit, CLAUDE.md rule).** This commit changes the collected count, so it also updates **only the collected number** in the `CLAUDE.md` baseline sentence ("**N backend tests collected.**") and in the `AGENT.md` Commands comment ("(N collected; …)"), taking N from:
  ```bash
  set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb2; cd "$WT/src/backend"
  ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1; echo "pytest exit=${PIPESTATUS[0]}"
  ```
  Leave every pass-count sentence ("all N pass", "N pass in CI, N−1 without an embedding model") unchanged unless a pass count was measured in this PR in a named environment (interpreter + embedding model present/absent). Otherwise flag it in the PR. Never write a collected number into a pass-count slot.

- [ ] **Step 6: STOP for OG-2**, then commit.
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb2; cd "$WT"
git add src/backend/tests/security/test_vault_ciphertext.py CLAUDE.md AGENT.md
git diff --cached --name-only   # expect exactly these 3 paths
git commit -m "fix(security): prove the profile vault is ciphertext on disk (KEY-02)

HC-KEYCT-001..005. Encryption required for the test only; conftest's suite-wide
DATABASE_ENCRYPTION_REQUIRED=false is unchanged. Fails (never skips) in CI when
sqlcipher3 is missing. No encryption code edited (owner confirmation OG-2, <date>).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/tests/security/test_vault_ciphertext.py CLAUDE.md AGENT.md
```

---

## Task 4 (PR-3, G-B4a): one head and a linear chain per Alembic chain

**Files:** Create `src/backend/tests/test_migration_heads.py`.

**Interfaces:**
- Consumes: `core.migrations._get_alembic_config(section: str) -> alembic.config.Config` (main@40f590e `core/migrations.py:34-48`, unchanged at B). This is the same config the runtime uses, so the test sees the same `script_location`.
- Also consumes: `alembic.script.ScriptDirectory`.
- Produces: `_single_head(script, label) -> str`.

The chains are linear today (contract C-MIG-1 verify line; heads master `002_backup_schedules`, profile `012_pinboards` at main; P6 adds `013`). HC-MIGHEAD-001/003 therefore pass on first run. HC-MIGHEAD-002 is the durable negative control, and Step 3 is the one-off break.

- [ ] **Step 1: Write the tests.**

```python
"""HC-MIGHEAD — each Alembic chain has exactly one head and stays linear
(MIG-02, C-MIG-1, C-MIG-2). Two heads mean `upgrade head` is ambiguous, and a
vault could miss a table."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory

from core.migrations import _get_alembic_config

CHAINS = ("master", "profile")


def _script(chain: str) -> ScriptDirectory:
    return ScriptDirectory.from_config(_get_alembic_config(chain))


def _single_head(script: ScriptDirectory, label: str) -> str:
    heads = script.get_heads()
    assert len(heads) == 1, (
        f"{label} chain has {len(heads)} heads {sorted(heads)}; expected exactly 1 (C-MIG-2)"
    )
    return heads[0]


@pytest.mark.parametrize("chain", CHAINS)
def test_hc_mighead_001_each_chain_has_exactly_one_head(chain):
    _single_head(_script(chain), chain)


def test_hc_mighead_002_a_forked_chain_is_detected(tmp_path):
    real = _script("profile")
    head = _single_head(real, "profile")
    parent = real.get_revision(head).down_revision
    assert isinstance(parent, str), "profile head has no single parent to fork from"

    fork_dir = tmp_path / "profile"
    shutil.copytree(Path(real.dir), fork_dir, ignore=shutil.ignore_patterns("__pycache__"))
    (fork_dir / "versions" / "999_hc_mighead_fork.py").write_text(
        'revision = "999_hc_mighead_fork"\n'
        f'down_revision = "{parent}"\n'
        "branch_labels = None\n"
        "depends_on = None\n\n\n"
        "def upgrade():\n    pass\n\n\n"
        "def downgrade():\n    pass\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="has 2 heads"):
        _single_head(ScriptDirectory(str(fork_dir)), "forked profile")


@pytest.mark.parametrize("chain", CHAINS)
def test_hc_mighead_003_every_revision_has_at_most_one_parent(chain):
    merges = [
        rev.revision
        for rev in _script(chain).walk_revisions()
        if isinstance(rev.down_revision, (tuple, list))
    ]
    assert merges == [], f"{chain} chain has merge revisions {merges}; C-MIG-1 requires linear"
```

- [ ] **Step 2: Run.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb4; cd "$WT/src/backend"
~/venvs/asclexis-311/bin/python -m pytest tests/test_migration_heads.py -p no:cacheprovider -v -k hc_mighead_
```
Expected: `5 passed`.

- [ ] **Step 3: Break it on purpose in the real chain, in a disposable detached worktree.** `migrations/` is not this plan's file, so the fork file is written only into a throwaway worktree that also gets the uncommitted test file.
```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb4; BRK=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb4-break
git -C "$WT" worktree add --detach "$BRK" HEAD || { echo "STOP: could not create $BRK"; exit 1; }
cp "$WT/src/backend/tests/test_migration_heads.py" "$BRK/src/backend/tests/test_migration_heads.py" \
  || { echo "STOP: copy failed"; git -C "$WT" worktree remove --force "$BRK"; exit 1; }
cd "$BRK/src/backend"
PARENT=$(~/venvs/asclexis-311/bin/python -c "from alembic.script import ScriptDirectory; from core.migrations import _get_alembic_config as c; s=ScriptDirectory.from_config(c('profile')); print(s.get_revision(s.get_heads()[0]).down_revision)")
printf 'revision = "999_hc_mighead_fork"\ndown_revision = "%s"\nbranch_labels = None\ndepends_on = None\n\n\ndef upgrade():\n    pass\n\n\ndef downgrade():\n    pass\n' "$PARENT" > "$BRK/src/backend/migrations/profile/versions/999_hc_mighead_fork.py"
~/venvs/asclexis-311/bin/python -m pytest tests/test_migration_heads.py -p no:cacheprovider -q -k hc_mighead_001 2>&1 | tail -8; echo "pytest exit=${PIPESTATUS[0]}"
git -C "$WT" worktree remove --force "$BRK" && git -C "$WT" status --short -- src/backend/migrations && echo phase-worktree-untouched
```
Expected RED (`pytest exit=1`), exactly `1 failed, 1 passed`: HC-MIGHEAD-001[profile] with `AssertionError: profile chain has 2 heads [...]; expected exactly 1 (C-MIG-2)`, while [master] passes. The `git status` prints nothing before `phase-worktree-untouched`.

- [ ] **Step 4: What would these tests fail to notice?** Put this in the PR description.
- **Model/DDL drift** (C-MIG-1's "Model and DDL must agree").
- **A migration that fails to run.**
- **A revision placed in the wrong chain.**

- [ ] **Baseline count (same commit, CLAUDE.md rule).** This commit changes the collected count, so it also updates **only the collected number** in the `CLAUDE.md` baseline sentence ("**N backend tests collected.**") and in the `AGENT.md` Commands comment ("(N collected; …)"), taking N from:
  ```bash
  set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb4; cd "$WT/src/backend"
  ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1; echo "pytest exit=${PIPESTATUS[0]}"
  ```
  Leave every pass-count sentence ("all N pass", "N pass in CI, N−1 without an embedding model") unchanged unless a pass count was measured in this PR in a named environment (interpreter + embedding model present/absent). Otherwise flag it in the PR. Never write a collected number into a pass-count slot.

- [ ] **Step 5: Commit.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb4; cd "$WT"
git add src/backend/tests/test_migration_heads.py CLAUDE.md AGENT.md
git diff --cached --name-only   # expect exactly these 3 paths
git commit -m "fix(migrations): assert one head and a linear chain per Alembic chain (MIG-02)

HC-MIGHEAD-001..003, with a forked-copy negative control.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/tests/test_migration_heads.py CLAUDE.md AGENT.md
```

---

## Task 5 (PR-3): measure the gates on the START tree before wiring them (no commit)

A gate that fails on day one on `main` needs an owner baseline decision; it must not be silently "fixed". Measure first. Use a **Linux-native scratch copy**: CI is `ubuntu-latest`, and `/mnt/c` stalls the toolchain (AGENT.md; program ground rule 3). **Every Task 5–8 measurement (eslint, build, ruff, coverage, seeds) runs in this one tree**, `/tmp/w11a-gb4`, a `git archive` of the committed HEAD recorded in `/tmp/w11a-gb4/MEASURED_COMMIT`. The copy lives outside the repo, so nothing here can be staged. The only `/mnt/c` runs are the Task 0 START / Task 10 END suite measurements, which compare the worktree with itself.

- [ ] **Step 1: Copy HEAD out and install.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb4
test -z "$(git -C "$WT" status --porcelain)" || { echo "STOP: worktree not clean; commit Task 4 first so HEAD is the measured tree"; exit 1; }
test ! -e /tmp/w11a-gb4 || { echo "STOP: /tmp/w11a-gb4 exists from an earlier run; remove it by hand first"; exit 1; }
mkdir -p /tmp/w11a-gb4 && git -C "$WT" archive HEAD src/frontend src/backend | tar -x -C /tmp/w11a-gb4 || { echo "STOP: archive failed"; exit 1; }
git -C "$WT" rev-parse HEAD | tee /tmp/w11a-gb4/MEASURED_COMMIT
cd /tmp/w11a-gb4/src/frontend
npm ci --no-audit --no-fund || { echo "STOP: npm ci failed (exit $?); no lint/build numbers from this tree"; exit 1; }
echo npm-ci-ok
```

- [ ] **Step 2: eslint and build.**
```bash
set -o pipefail; cd /tmp/w11a-gb4/src/frontend
test -d node_modules/.bin || { echo "STOP: Step 1 did not finish (no node_modules)"; exit 1; }
npx eslint --version && node --version
npx eslint . -f json -o /tmp/w11a-gb4/eslint.json; echo "eslint exit=$?"
python3 -c "import json;d=json.load(open('/tmp/w11a-gb4/eslint.json'));print('files',len(d),'errors',sum(f['errorCount'] for f in d),'warnings',sum(f['warningCount'] for f in d))"
npm run build; echo "build exit=$?"
```
Expected, per the 2026-09-27 A+B measurement: `eslint exit=0`, `errors 0`, `warnings 5`, `build exit=0`. If errors > 0 or the build fails → **STOP** (stop gate 11: baseline decision for the owner).

- [ ] **Step 3: ruff with the version CI will pin.**
```bash
set -o pipefail
python3 -m venv /tmp/w11a-gb4/ruffenv && /tmp/w11a-gb4/ruffenv/bin/pip install -q "ruff==0.15.10" || { echo "STOP: ruff install failed"; exit 1; }
/tmp/w11a-gb4/ruffenv/bin/ruff --version | grep -qx "ruff 0.15.10" || { echo "STOP: wrong ruff version"; exit 1; }
cd /tmp/w11a-gb4/src/backend
/tmp/w11a-gb4/ruffenv/bin/ruff check . --no-cache --statistics | tail -8; echo "ruff exit=${PIPESTATUS[0]}   (1 = findings exist; expected)"
/tmp/w11a-gb4/ruffenv/bin/ruff check . --no-cache --select E9,F63,F7,F82; echo "hard-error exit=$?"
```
Expected, per the A+B measurement: 561 configured-rule findings, and `All checks passed!` with `hard-error exit=0`. Record both numbers for Q-RUFF.

- [ ] **Step 4: Coverage run, in the same scratch tree** (`/tmp/w11a-gb4`, commit in `MEASURED_COMMIT`). Measure its cost and TOTAL against a plain run **of the same tree and interpreter**, so any difference comes from `--cov` alone. The flags and report path mirror the Task 8 CI step: `coverage.xml` is written in `src/backend`.
```bash
set -o pipefail; cd /tmp/w11a-gb4/src/backend
test -f /tmp/w11a-gb4/MEASURED_COMMIT || { echo "STOP: run Step 1 first"; exit 1; }
~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1; echo "pytest exit=${PIPESTATUS[0]}"
( time ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q ) 2>&1 | tail -30 | tee /tmp/w11a-gb4/run-plain.txt; echo "pytest exit=${PIPESTATUS[0]}"
( time ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q --cov=api --cov=core --cov=models --cov=modules --cov=monitoring --cov=security --cov=scripts --cov-report=term --cov-report=xml:coverage.xml ) 2>&1 | tail -40 | tee /tmp/w11a-gb4/run-cov.txt; echo "pytest exit=${PIPESTATUS[0]}"
test -s coverage.xml && echo coverage-xml-ok
```
Record:
- the commit;
- the collected line;
- both wall times;
- both failure lists;
- the `TOTAL … NN%` line;
- `coverage-xml-ok`.

Pass conditions:
- The collected count must equal the Task 0 START count plus Task 4's 5 (same commit content as the worktree).
- The coverage run's failures must equal the plain run's failures in this tree.
- Both must be ⊆ the START failures, or be explained by the scratch path, e.g. a test that reads a repo file outside `src/`. Name any such test.
- If `--cov` adds a failure → **STOP** (stop gate 10).

The TOTAL is today UNMEASURED; it is the input to Q-COV.

---

## Task 6 (PR-3, G-B4b): frontend `npm run lint` and `npm run build` in CI

**Files:** Modify `.github/workflows/ci.yml`, job `frontend-tests` (B@7b2ff1f `:53-76`; re-locate by content after P5/W-4).

- [ ] **Step 1: Seed each violation and confirm the exact CI command fails** (Linux copy from Task 5, never in the repo).
```bash
set -o pipefail; cd /tmp/w11a-gb4/src/frontend
test -d node_modules/.bin || { echo "STOP: run Task 5 Step 1 first"; exit 1; }
printf 'const hcSeededUnused = 1;\n' > src/hc_seed_lint.ts
npm run lint; echo "lint exit=$?"          # expect: error @typescript-eslint/no-unused-vars, lint exit=1
rm src/hc_seed_lint.ts && npm run lint; echo "lint exit=$?"   # expect 0
printf 'export const hcSeed: number = "not a number";\n' > src/hc_seed_build.ts
npm run build; echo "build exit=$?"        # expect: error TS2322, build exit=2 (non-zero)
rm src/hc_seed_build.ts && npm run build; echo "build exit=$?"  # expect 0
```

- [ ] **Step 2: Edit `ci.yml`.** In `frontend-tests`, insert after the `Type check` step:
```yaml
      - name: Lint (eslint)
        working-directory: src/frontend
        run: npm run lint
```
and append after the `Run tests` step:
```yaml
      - name: Production build
        working-directory: src/frontend
        run: npm run build
```

- [ ] **Step 3: Validate the YAML and the diff.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb4; cd "$WT"
~/venvs/asclexis-311/bin/python -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); print([s.get('name') for s in d['jobs']['frontend-tests']['steps']])"
git diff --stat -- .github/workflows/ci.yml
```
Expected: the step list includes `Lint (eslint)` after `Type check` and `Production build` last. If PyYAML is missing: `~/venvs/asclexis-311/bin/pip install pyyaml || { echo "STOP: pyyaml install failed"; exit 1; }` into the venv only, then re-run the one-liner. `requirements.txt` stays untouched.

- [ ] **Step 4: Commit.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb4; cd "$WT"
git add .github/workflows/ci.yml
git diff --cached --name-only   # expect 1 path
git commit -m "feat(ci): lint and build the frontend in CI (GATE-03, C-API-3)

npm run lint (eslint .) and npm run build (tsc && vite build) in frontend-tests.
Measured on the start tree: 0 eslint errors / 5 warnings; build exit 0.
Seeded unused-var and type error each fail the step locally.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- .github/workflows/ci.yml
```

---

## Task 7 (PR-3, G-B4c): ruff gate — OWNER DECISION (Q-RUFF)

**Gate:** Q-RUFF answered.

| Answer | Action |
|---|---|
| (a) — recommended | Do this task |
| (b) | Skip this task. Write a separate plan for the 561-finding cleanup; it touches ask-first files and needs per-file owner approval |
| (c) | Skip; record GATE-07 ruff as "owner declined" |

**Files:** Modify `.github/workflows/ci.yml`: add a job `backend-lint` directly after `backend-tests`.

- [ ] **Step 1: Seed and confirm the command fails** (Linux copy).
```bash
set -o pipefail; cd /tmp/w11a-gb4/src/backend
test -x /tmp/w11a-gb4/ruffenv/bin/ruff || { echo "STOP: run Task 5 Step 3 first"; exit 1; }
printf 'def hc_seed():\n    return undefined_name_hc_seed\n' > hc_seed_ruff.py
/tmp/w11a-gb4/ruffenv/bin/ruff check . --select E9,F63,F7,F82 --output-format=github; echo "ruff exit=$?"   # expect F821, exit=1
rm hc_seed_ruff.py && /tmp/w11a-gb4/ruffenv/bin/ruff check . --select E9,F63,F7,F82; echo "ruff exit=$?"    # expect 0
```

- [ ] **Step 2: Add the job** after the `backend-tests` job:
```yaml
  backend-lint:
    name: Backend Lint (ruff hard errors)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install ruff (pinned; rule behaviour changes between versions)
        run: pip install "ruff==0.15.10"

      - name: Ruff hard-error rules (syntax errors, undefined names, invalid comparisons)
        working-directory: src/backend
        # Owner decision Q-RUFF (<date>): gate on E9,F63,F7,F82 only. The full rule set
        # in src/backend/pyproject.toml (F, I, W) reported 561 findings on the post-P1
        # tree and stays advisory until a separately approved cleanup.
        run: ruff check . --select E9,F63,F7,F82 --output-format=github
```

- [ ] **Step 3: Validate** (same YAML one-liner, printing `sorted(d['jobs'])`). Expected: `backend-lint` present.

- [ ] **Step 4: Commit.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb4; cd "$WT"
git add .github/workflows/ci.yml
git diff --cached --name-only
git commit -m "feat(ci): gate the backend on ruff hard-error rules (GATE-07)

Pinned ruff 0.15.10; --select E9,F63,F7,F82 (0 findings on the start tree).
Owner decision Q-RUFF (<date>). Seeded F821 fails the step locally.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- .github/workflows/ci.yml
```

---

## Task 8 (PR-3, G-B4d): backend coverage report, failing closed if missing

A coverage *report* is not a threshold gate. The gate here is "the report exists" (C-GATE-2: a missing report must not pass). The threshold is Q-COV.

**Files:** Modify `.github/workflows/ci.yml`, job `backend-tests` (B@7b2ff1f `:33-51`).

- [ ] **Step 1: Seed and confirm, in the Task 5 scratch tree.** The fail-closed step is `test -s src/backend/coverage.xml`, which is the CI step verbatim, run from the tree root.
```bash
set -o pipefail; cd /tmp/w11a-gb4
test -s src/backend/coverage.xml; echo "report present: exit=$?"        # expect 0 (Task 5 Step 4 wrote it)
mv src/backend/coverage.xml /tmp/w11a-gb4/coverage.xml.bak || { echo "STOP: no report to move"; exit 1; }
test -s src/backend/coverage.xml; echo "report missing: exit=$?"        # expect 1: the step fails closed
mv /tmp/w11a-gb4/coverage.xml.bak src/backend/coverage.xml
```

- [ ] **Step 2: Edit.** Replace the `Run backend tests` step's `run:` line and add two steps after it:
```yaml
      - name: Run backend tests (with coverage report)
        run: bash scripts/run-backend-tests.sh -q --cov=api --cov=core --cov=models --cov=modules --cov=monitoring --cov=security --cov=scripts --cov-report=term --cov-report=xml:coverage.xml

      - name: Require the coverage report (fail closed)
        run: test -s src/backend/coverage.xml

      - name: Upload coverage report
        uses: actions/upload-artifact@v4
        with:
          name: backend-coverage
          path: src/backend/coverage.xml
          if-no-files-found: error
```
`scripts/run-backend-tests.sh` `cd`s into `src/backend` and passes `"$@"` to pytest (main@40f590e `:22-28`), so `coverage.xml` lands in `src/backend/`. `pytest-cov>=4.1.0` is already in `requirements.txt`. `.gitignore` has `.coverage` (B@7b2ff1f `:52`) but not `coverage.xml`: never stage it.

- [ ] **Step 3: Validate the YAML**, then commit.
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb4; cd "$WT"
git add .github/workflows/ci.yml
git diff --cached --name-only
git commit -m "feat(ci): publish a backend coverage report and fail if it is missing (GATE-07)

Report only; no threshold (owner question Q-COV). Local TOTAL: <NN>% on
scratch copy of <MEASURED_COMMIT>, D9 venv (Task 5 Step 4).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- .github/workflows/ci.yml
```

- [ ] **Step 4 (optional, OG-3): prove the gates in real CI.** Only if the owner signs OG-3:
1. Push a throwaway branch with the four seeds (lint, build, ruff, migration fork) on top of this PR's head.
2. Open it as a **draft PR** to `main`: `ci.yml` triggers on `pull_request` (B@7b2ff1f `:3-7`).
3. Record each failing job's name and log line.
4. Close the draft unmerged and delete the branch.

---

## Task 9 (PR-3 docs): describe the new gates

**Files:** `docs/architecture/ci-and-quality-gates.md`, re-read after P4/W-8.

- [ ] **Step 1: Update the mermaid `JOBS` block and the "What each gate actually protects" table** (B@7b2ff1f `:15-48`):
  - `FE` → `frontend-tests<br/>tsc --noEmit · eslint · vitest · build`.
  - Add `BLINT["backend-lint<br/>ruff E9,F63,F7,F82 (pinned 0.15.10)"]`, with an edge `BLINT --> MERGE`. Only if Task 7 was done.
  - `backend-tests` row: add "coverage report (no threshold; fails if the report is missing)".
  - Leave `:44` "Baseline is ~1160 passing" to P4/W-8. If it is still there, flag it in the PR. Do not guess a number.
- [ ] **Step 2: Lint.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb4; cd "$WT"
python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check; echo "exit=$?"
```
Expected: "Docs lint passed." and exit 0. If the index is stale, run `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph` and include `docs/INDEX.md docs/_link_graph.json` in Task 10's commit.

---

## Task 10 (end of each PR): status docs and the measured END baseline — DOCS commit

**Files:** row-scoped edits only.

| PR | Files and rows |
|---|---|
| PR-1 | `specs-compliance-matrix.md` ISO-02, AUD-02; contract C-ISO-1 and C-AUDIT-1 "Status today"/"Enforced at" |
| PR-2 | matrix KEY-02; contract C-KEY-1 |
| PR-3 | matrix MIG-02, GATE-03 (build/eslint part), GATE-07; contract C-MIG-2 and C-API-3 "Enforced at"; plus `docs/architecture/ci-and-quality-gates.md` from Task 9 |
| all | append one `docs/features/TASK_LIST.md` Session Note. `CLAUDE.md`/`AGENT.md` collected counts are already updated by the test commits; a pass-count sentence changes only with a measured pass count |

Do **not** change any contract's Class (PROPOSED → BINDING is the owner's call). Only the "Enforced at" / "Status today" fields and the matrix Tests/Gate/Status cells change.

- [ ] **Step 1: END measurement.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1   # gb2 / gb4 for the other PRs
find "$WT/src/backend" -name __pycache__ -type d -prune -exec rm -rf {} +
cd "$WT/src/backend"
~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1; echo "pytest exit=${PIPESTATUS[0]}"
~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q 2>&1 | tail -25; echo "pytest exit=${PIPESTATUS[0]}"
~/venvs/asclexis-311/bin/python -c "from main import app; print('boot ok')"
```
Expected END collected = START + tests added:

| PR | Added |
|---|---|
| PR-1 | 15, or 21/22 with Task 2 (15 + 6, or + 7 with HC-PAUD-006) |
| PR-2 | 7 |
| PR-3 | 5 |
| PR-4 | 0 |

Also: failures ⊆ START failures, each named; `boot ok`.

- [ ] **Step 2: Edit the rows** with the measured facts. Row text for PR-1 (adjust to what shipped):
  - ISO-02 Tests: `tests/test_profile_route_guards.py` (HC-PGUARD-001…006, HTTP, includes a guard-removal mutation control) · Status: **tested**.
  - AUD-02 Implementation: `13/13`, or `12/13 — GET / owner-exempted <date>`. Tests: `tests/test_profile_route_audit.py` (HC-PAUD) · Status: **tested**. If OG-1 is unsigned: unchanged, **partial**.

  The collected-count numbers in `CLAUDE.md` / `AGENT.md` were already updated by each test-adding commit (the "Baseline count" sub-steps). Here, confirm they equal this END collected count. Touch a **pass-count** sentence only if Step 1's run is the measured pass count in a named environment (interpreter + embedding model present/absent), and write that environment next to the number. Otherwise leave it and flag it in the PR. Never write a collected number into a pass-count slot. Keep the "do not lower the 0.7 threshold" guard sentence verbatim.

- [ ] **Step 3: Lint, then commit.**
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb1; cd "$WT"   # gb2 / gb4 for the other PRs
python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check; echo "exit=$?"
git add docs/capstone-report/specs-compliance-matrix.md docs/capstone-report/architecture-engineering-contract.md docs/features/TASK_LIST.md
# CLAUDE.md AGENT.md only if a measured pass-count sentence changed (Step 2)
# PR-3 also: docs/architecture/ci-and-quality-gates.md; any PR: docs/INDEX.md docs/_link_graph.json if regenerated
git diff --cached --name-only   # must list only the files above
git commit -m "docs: record <rows> status and the measured baseline after W-11a <gap>

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- <the same explicit paths>
```

- [ ] **Step 4: Push and open the PR.** The body follows handoff §6:
1. START/END measurements;
2. new tests with their RED evidence;
3. contract and matrix rows changed;
4. the explicit file list and any owner stop reached;
5. one next action.

End the body with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. **STOP** for the owner's merge.

---

## Task 11 (PR-4, G-B6): measure frontend counts on Windows and replace the 155/25 claims — DOCS

**Where the claims live** (grep, 2026-09-27):

| Kind | Location | Action |
|---|---|---|
| Live claim | `docs/capstone-report/claims-ledger.md:42` (H2) | replace |
| Live claim | `docs/capstone-report/architecture-overview.md:211` (§14 Unknowns) | replace |
| Live claim | `docs/capstone-report/specs-compliance-matrix.md:137` (GATE-03) | replace |
| Live claim | `docs/capstone-report/specs-compliance-matrix.md:140` (GATE-06) | replace |
| Live claim | `docs/capstone-report/specs-compliance-matrix.md:165` ("Unrun checks" row) | replace |
| Dated record | `docs/features/TASK_LIST.md:794` (main@40f590e), a 2026-08 Session Note: "vitest 155/155; **Playwright 25 passed / 3 conditional skips**" | leave |
| Dated record | `audit/2026-09-25/Devin-Audit-report.md:12,30` | leave |
| Undated live-looking claim | `audit/repository-audit-dashboard.html:255`: `~1,245 collected backend, 155 vitest, 25 Playwright; route_client harness.` The file is a 2026-09-25 pre-reconciliation snapshot (Devin-Audit-report.md A-4; follow-up F-12) that carries no date on the page | annotate in place, no rewrite (Step 3) |
| Dated record | `docs/superpowers/**/2026-07-30-*.md` ("25 passed / 3 skipped") | leave |

"25" was a **pass** count, not a test count. The chromium project lists 28 on main@40f590e (25 + 3 conditional skips), so the claim was a different quantity, not merely stale.

- [ ] **Step 1: Windows measurement** (PowerShell; one `Set-Location`; check `$LASTEXITCODE` after each command whose result matters).
```powershell
Set-Location C:\Users\DangT\Documents\GitHub\hc-w11a-gb6\src\frontend
npm ci
if ($LASTEXITCODE -ne 0) { throw "npm ci failed: $LASTEXITCODE" }
node --version; npx vitest --version; npx playwright --version
npx vitest list --json="$env:TEMP\w11a-vitest-list.json"
if ($LASTEXITCODE -ne 0) { throw "vitest list failed: $LASTEXITCODE" }
$list = Get-Content "$env:TEMP\w11a-vitest-list.json" -Raw | ConvertFrom-Json
"vitest listed: $($list.Count) tests in $(($list | Select-Object -ExpandProperty file -Unique).Count) files"
npx vitest run --reporter=default --reporter=json --outputFile="$env:TEMP\w11a-vitest-run.json"
$vitestExit = $LASTEXITCODE
$run = Get-Content "$env:TEMP\w11a-vitest-run.json" -Raw | ConvertFrom-Json
"vitest run: total $($run.numTotalTests) / passed $($run.numPassedTests) / failed $($run.numFailedTests) / skipped $($run.numPendingTests + $run.numTodoTests); exit $vitestExit"
npx playwright test --list --project chromium | Select-Object -Last 1
if ($LASTEXITCODE -ne 0) { throw "playwright list (chromium) failed: $LASTEXITCODE" }
npx playwright test --list | Select-Object -Last 1
```
Expected shape: `Total: N tests in M files`. Linux context from 2026-09-27: vitest listed 179/31 on the A+B tree; Playwright chromium 30/6, all projects 35/7.
- A Windows figure that differs is the finding, not an error.
- If `vitest run` exits non-zero, record the failing tests verbatim and do not fix them here.

- [ ] **Step 2: Playwright run** (records a pass count; environment-dependent, recurring-failures #4).
```powershell
npx playwright install chromium
if ($LASTEXITCODE -ne 0) { throw "playwright install failed: $LASTEXITCODE (record as the blocker; no run count)" }
npx playwright test --project chromium
"playwright exit: $LASTEXITCODE"
```
On Windows the e2e backend (`e2e/support/start-backend.mjs`) needs a Python with backend deps, and `sqlcipher3-binary` has no Windows wheel.
- If the run needs `DATABASE_ENCRYPTION_REQUIRED=false`, or fails to start the backend, record the exact blocker and write the pass count as `UNMEASURED on Windows (<blocker>)`.
- Never report an unencrypted local run as the CI e2e result.
- In a Linux sandbox, set `HC_E2E_CHROMIUM_PATH` as the config header says.

- [ ] **Step 3: Replace the live claims.** Write each figure **with its environment**, using collected/listed counts first (they do not vary by pass/fail). Substitute the Step 1/2 outputs:
  - **claims-ledger H2** claim cell: `…; vitest {VITEST_LISTED} listed / {VITEST_PASSED} passed; Playwright chromium {PW_LISTED} listed ({PW_RESULT})`. Evidence cell: the Step 1/2 commands, Windows version, node/vitest/Playwright versions, date. Status: vitest/e2e `VERIFIED (listed count, Windows, <date>)`; the pass count `VERIFIED` or `UNMEASURED (<blocker>)`.
  - **architecture-overview §14:** delete the "Frontend test counts (155 vitest / 25 e2e claimed…)" bullet and add the measured sentence to §14's neighbouring known-facts text, or keep it as an Unknown only for the part that stayed UNMEASURED.
  - **matrix GATE-03:** replace "the 155-test figure is unverified" with "vitest {VITEST_LISTED} listed, {VITEST_PASSED} passed (Windows, <date>)". If PR-3 has merged, also drop "no `npm run build`, no eslint in CI".
  - **matrix GATE-06:** replace "25-test figure unverified; not run this pass" with the chromium listed count and the run result or blocker.
  - **matrix "Unrun checks" row `:165`:** replace it with the measured status, or delete it if both figures were measured.
  - **TASK_LIST.md:** append a Session Note with the commands and outputs. Leave `:794` (dated history) untouched.
  - **`audit/repository-audit-dashboard.html:255`:** mark it as a dated snapshot and point to the measured figures, without rewriting the snapshot's other numbers. Replace the note's text with:
    `Snapshot 2026-09-25 (pre-reconciliation, unmeasured): ~1,245 collected backend, 155 vitest, 25 Playwright. Measured {DATE}: vitest {VITEST_LISTED} listed, Playwright chromium {PW_LISTED} listed; see docs/capstone-report/claims-ledger.md H2.`
    Keep the `<div class="bar-note">…</div>` element and its class.
  - **Final check:** re-run the inventory grep so no other live copy survives:
    ```bash
    set -o pipefail; cd /mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb6
    git grep -nE "155 vitest|25 Playwright|25 e2e|155/25|155-test|25-test" -- . ':!docs/archive' | grep -vE "Snapshot 2026-09-25|docs/features/TASK_LIST.md|^audit/2026-09-25/|docs/superpowers/|^docs/plans/|docs/capstone-report/implementation-program.md"; echo "grep exit=${PIPESTATUS[0]}"
    ```
    Expected: no lines printed. The exclusions are dated records (the TASK_LIST Session Notes, `audit/2026-09-25/`, `docs/superpowers/`), plans that describe this task (`docs/plans/`), and the program's G-B6 row, which names the claim rather than making it. On 2026-09-27 the same pattern and exclusions over the working tree printed exactly 5 lines: `claims-ledger.md:42`, `architecture-overview.md:211`, `specs-compliance-matrix.md:137,140` and the dashboard `:255`. The matrix `:165` row words it differently, so Step 3 lists it explicitly. Any hit is a missed live claim: add it to the table above and handle it the same way.

- [ ] **Step 4: Lint and commit** (WSL).
```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w11a-gb6; cd "$WT"
python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check; echo "exit=$?"
git add docs/capstone-report/claims-ledger.md docs/capstone-report/architecture-overview.md docs/capstone-report/specs-compliance-matrix.md docs/features/TASK_LIST.md audit/repository-audit-dashboard.html
git diff --cached --name-only   # exactly these 5 (+ docs/INDEX.md docs/_link_graph.json if regenerated)
git commit -m "docs: replace the unmeasured 155 vitest / 25 Playwright figures with measured counts

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- docs/capstone-report/claims-ledger.md docs/capstone-report/architecture-overview.md docs/capstone-report/specs-compliance-matrix.md docs/features/TASK_LIST.md audit/repository-audit-dashboard.html
```
Then push, open the PR (handoff §6 format) and **STOP** for merge.

---

## 7. Measured acceptance

| Gap | Command | Expected |
|---|---|---|
| all | `pytest tests/ --collect-only -q -p no:cacheprovider` (D9 venv) | END = START + {PR-1: 15 or 21/22; PR-2: 7; PR-3: 5} |
| all | full run | failures ⊆ START failures, each named |
| G-B1 | `pytest tests/test_profile_route_guards.py -k hc_pguard_ -v` | `15 passed`; Task 1 Step 4 break → exactly `3 failed, 4 passed`, as listed |
| G-B1 audit | `pytest tests/test_profile_route_audit.py -k hc_paud_ -v` | 7 (or 6) passed; RED observed in Steps 2, 5 and 6 |
| G-B2 | `HC_REQUIRE_SQLCIPHER=1 pytest tests/security/test_vault_ciphertext.py -rs -v` (Linux) | `7 passed`, 0 skipped; Task 3 Step 4 `CI=true` without sqlcipher3 → `2 failed` |
| G-B4 migration | `pytest tests/test_migration_heads.py -v` | `5 passed`; real-chain fork → `profile chain has 2 heads` |
| G-B4 CI | Task 6/7/8 seeded commands | lint exit 1, build non-zero, ruff exit 1, `test -s` exit 1; each 0 after removing the seed |
| G-B4 CI (real) | OG-3 draft PR, optional | failing job names recorded, or `UNMEASURED in CI (OG-3 not signed)` |
| G-B6 | Task 11 Steps 1–3 | outputs pasted in the PR; the 5 capstone claim sites replaced; the dashboard note annotated; the final inventory grep prints nothing |
| docs | `python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check` | "Docs lint passed.", exit 0 |
| boot | `cd src/backend && <venv> -c "from main import app"` | no error |

**UNMEASURED today, and how to measure:**

| Item | How |
|---|---|
| Backend coverage TOTAL % | Task 5 Step 4 (scratch tree `/tmp/w11a-gb4`, D9 venv, commit in `MEASURED_COMMIT`) |
| Windows vitest/Playwright counts | Task 11 |
| Whether `sqlcipher3` imports on the CI runner | the first PR-2 CI run; HC-KEYCT-001 fails there if not |
| The D9 venv's START counts | Task 0 Step 5 |
| eslint on Windows | optional: `npm run lint` in the Task 11 PowerShell session |

## 8. Stop gates (stop and ask the owner)

1. Task 0 Step 2 is not `post-P1-ok`, or a dependency check in Step 3 fails.
2. The D9 venv is missing, or `python3.11` is unavailable to build it.
3. OG-1 unsigned → skip Task 2 (PR-1 ships tests only). Q-AUD-LIST unanswered → implement the 3 authenticated routes only if OG-1 is signed; leave `GET /` and say so.
4. OG-2 unsigned → Task 3 stays uncommitted.
5. Q-RUFF unanswered → skip Task 7.
6. `import sqlcipher3` fails in the Linux D9 venv: requirements/CI parity is broken.
7. HC-KEYCT-001 fails its ciphertext assertion in a correctly configured Linux venv. This is a real encryption finding: security response protocol, owner report, no code edits.
8. Any step needs an edit to an ask-first file, `core/auth.py`, `core/audit.py`, `core/profile_database.py`, `core/security.py`, `core/migrations.py`, `tests/conftest.py`, `requirements.txt`, `package.json`, `eslint.config.js` or `pyproject.toml`.
9. PR-3 is ready but W-4 has not merged. Ask the orchestrator which lands first; W-4's plan expects to go first and to rebase if not.
10. The coverage flags change the collected count or add a failure.
11. eslint errors > 0 or `npm run build` fails on the START tree (baseline decision).
12. P7's `route_client` lacks `profile_db` / `profile_name`, the `real_auth` opt-out cannot be added in one place (Task 1 Step 1b), or P7 renamed `_SYNTHETIC_RESET_MODELS`. Adapt the call only if the rename is mechanical; otherwise stop.
13. Any failure not explained by this PR's own change.

## 9. Rollback

- Each PR is independent.
  - **Before merge:** `gh pr close <n> --delete-branch`, then `git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree remove /mnt/c/Users/DangT/Documents/GitHub/hc-w11a-<gb>` and `git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral branch -D <branch>`.
  - **After merge:** `git revert -m 1 <merge-sha>` on a branch off `main`, opened as its own PR for the owner to merge.
- There are no migrations or schema changes. No data is written except audit rows (Task 2), which are ordinary master rows; revert stops new ones.
- Task 2 alone: revert the `fix(profiles): audit …` commit. The HC-PGUARD tests stay.
- CI: reverting `ci.yml` restores the previous jobs. The coverage artifact and ruff job disappear with it.
- Docs: revert the `docs:` commit. The collected-count numbers live in the test commits, so reverting those restores the earlier count too.

## 10. Recurring-failures recheck ([recurring-failures.md](../agentic/recurring-failures.md))

| # | Applies | Concrete recheck in this plan |
|---|---|---|
| 1 Green suite that could not fail | yes | HC-PGUARD-005 (guard removed → requests get through), HC-KEYCT-003 (plaintext vault caught), HC-MIGHEAD-002 (fork caught), plus Task 1 Step 4, Task 2 Steps 5–6, Task 3 Steps 3–4, Task 4 Step 3 and Task 6/7/8 seeds |
| 2 Fix that creates the next bug | yes | Task 2 Step 7 re-walks e2e reset, the profile selector, backup scoping and profile delete; the reset audit sits outside the `try`, so it cannot produce a false "reset failed" |
| 3 Figures asserted, not measured | yes | every count in §4 carries its command; Task 11 replaces 155/25 only with pasted outputs |
| 4 Environment-dependent results | yes | Task 3 skip-vs-fail (Windows has no sqlcipher3 wheel); Task 11 records the environment and prefers listed counts; `HC_E2E_CHROMIUM_PATH` |
| 5 Gates in a contaminated tree | yes | one worktree per PR (Task 0); CI-parity checks in a `git archive` copy outside the repo (Task 5) |
| 6 Documented commands nobody ran | yes | every command in Tasks 5–11 is run as written; `ci-and-quality-gates.md` is updated to what CI now runs |
| 7 SQL three-valued logic | yes (Q-AUD-LIST a) | NULL-profile `profile.list` rows versus `scripts/backup.py:281` `IS NULL OR` (Task 2 Step 7) |
| 8 Stale guidance as authority | yes | "25 e2e" was a pass count, not a test count; "Windows is the native dev env" (AGENT.md) versus no Windows sqlcipher3 wheel, so Windows dev vaults are unencrypted (`dev.ps1:471-500`) |

## 11. Owner sign-offs (unsigned)

- [ ] **OG-1 (route edit, auth-adjacent file).** I approve adding audit calls to `src/backend/api/profiles.py`:
  - `GET /me` and `GET /{profile_id}`: `profile.view`;
  - `POST /test/reset`: `profile.test_reset`, written after the vault commit, plus a master `get_db` dependency on that route;
  - using the existing `core/audit.py` helpers unchanged.
  
  Signed: ____________ Date: ________
- [ ] **Q-AUD-LIST.** For the unauthenticated `GET /profiles/`, choose one:
  - **(a)** audit every call with `profile_id` NULL and `details={"count": n}`. Recommended: CLAUDE.md requires audit on routes touching profile data, and the list returns display names. Cost: one master row per selector load; retention is unbounded (AUD-03).
  - **(b)** exempt it and document the exemption in C-AUDIT-1/AUD-02.
  
  Choice: ____ Signed: ____________ Date: ________
- [ ] **OG-2 (encryption area, test only).** I confirm that adding `tests/security/test_vault_ciphertext.py`, which edits no encryption code and does not change `tests/conftest.py`, may be committed. I accept that in CI it fails, rather than skips, when `sqlcipher3` is missing. Signed: ____________ Date: ________
- [ ] **Q-RUFF.** Choose one:
  - **(a)** gate CI on `ruff check --select E9,F63,F7,F82` with ruff pinned to 0.15.10 (0 findings today). The configured F/I/W set (561 findings post-P1) stays advisory. Recommended.
  - **(b)** a separate cleanup of all 561 findings first. It touches 154 files, including `interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py`, `core/auth.py`, `core/security.py` and `core/profile_database.py`, each needing its own approval.
  - **(c)** no ruff gate.
  
  Choice: ____ Signed: ____________ Date: ________
- [ ] **Q-COV.** Coverage stays report-only. A threshold, if any, is set after the first measured TOTAL (Task 5 Step 4): ____% or "none". Signed: ____________ Date: ________
- [ ] **OG-3 (optional).** I allow a throwaway draft PR carrying seeded violations, to show each new CI gate failing in GitHub Actions. It is closed unmerged. Signed: ____________ Date: ________
- [ ] **Merge, per PR.** PR-1 ____ PR-2 ____ PR-3 ____ PR-4 ____ (owner merges; "Humans merge", program ground rule 6).

## 12. Commit plan (summary)

| PR | Commit | Pathspecs |
|---|---|---|
| PR-1 | `fix(profiles): prove require_profile_access over HTTP …` | `src/backend/tests/support/master_db.py src/backend/tests/support/routes.py src/backend/tests/test_profile_route_guards.py CLAUDE.md AGENT.md` (collected count only) |
| PR-1 | `fix(profiles): audit profile reads and the synthetic test reset (AUD-02)` (OG-1) | `src/backend/api/profiles.py src/backend/tests/test_profile_route_audit.py CLAUDE.md AGENT.md` (collected count only) |
| PR-1 | `docs: …` | matrix, contract, `docs/features/TASK_LIST.md` (+ `CLAUDE.md`/`AGENT.md` only for a measured pass count; + index files if regenerated) |
| PR-2 | `fix(security): prove the profile vault is ciphertext on disk (KEY-02)` (OG-2) | `src/backend/tests/security/test_vault_ciphertext.py CLAUDE.md AGENT.md` (collected count only) |
| PR-2 | `docs: …` | matrix, contract, `TASK_LIST.md` (+ `CLAUDE.md`/`AGENT.md` only for a measured pass count) |
| PR-3 | `fix(migrations): assert one head … (MIG-02)` | `src/backend/tests/test_migration_heads.py CLAUDE.md AGENT.md` (collected count only) |
| PR-3 | `feat(ci): lint and build the frontend in CI` | `.github/workflows/ci.yml` |
| PR-3 | `feat(ci): gate the backend on ruff hard-error rules` (Q-RUFF) | `.github/workflows/ci.yml` |
| PR-3 | `feat(ci): publish a backend coverage report …` | `.github/workflows/ci.yml` |
| PR-3 | `docs: …` | matrix, contract, `docs/architecture/ci-and-quality-gates.md`, `TASK_LIST.md` (+ `CLAUDE.md`/`AGENT.md` only for a measured pass count) |
| PR-4 | `docs: replace the unmeasured 155 vitest / 25 Playwright figures …` | the 3 capstone files + `TASK_LIST.md` + `audit/repository-audit-dashboard.html` |

Before every commit: `git diff --cached --name-only` must equal the pathspecs. Never `git add -A` / `git add .`. Never `git reset` shared work. Never stage `coverage.xml`, `.coverage`, `dist/` or scratch copies.
