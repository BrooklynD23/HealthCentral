# Remediation, Rename to Asclexis, and Agent-Instruction Reoptimization

**Date:** 2026-07-30
**Status:** Approved
**Scope:** Three independently-executable phases. Intended for execution by an Opus 5.0 agent.

## Why this exists

A pre-merge audit of PR #18 (branch `claude/backlog-repo-docs-yl7isc`, 22 commits, 133 files) found ten defects, three of them merge blockers, in a branch whose CI was fully green. Separately, two owner asks became actionable: the product rename (`HC-M10`, previously blocked on owner clearance, now named **Asclexis**) and a refresh of the agent-instruction files for current model capability.

These are three unrelated projects that share one repository, and two of them edit the same files. This spec keeps them separated with explicit ordering so an implementing agent cannot interleave them by accident.

**Ordering: A → B → C.** Phase A unblocks the merge. Phase B is a mechanical identity sweep best run on a quiet tree. Phase C rewrites `AGENT.md`, which Phase B also touches — doing C last means that file is written once, already carrying the new name.

---

# Phase A — Audit fix pass

**Objective:** make the features PR #18 introduces actually reachable and correct, and close the structural testing gap that let a completely dead endpoint pass 32 tests.

## A0 — Route-level test harness *(do this first)*

**Scope:** `src/backend/tests/` — a shared fixture, plus conversion of the auth-bearing route tests in `test_backup_api.py` and `test_profile_deletion.py`.

**Problem.** Every route test calls the handler as a plain function (`await restore_backup(backup_id, payload=..., session=...)`). FastAPI's dependency graph never executes, so a broken `Depends(...)` is invisible. This is precisely how A1 survived 32 passing tests.

**Solution.** Add a `TestClient`-based fixture with `app.dependency_overrides` for `require_auth` and `get_db`, mirroring the pattern already proven in this session's live reproduction. Convert the tests that assert on auth, path-scoping, or status codes to go through HTTP. Direct-call tests may remain where they assert pure logic.

**Logic choice.** Fixing A1 alone leaves the suite blind to the entire class of bug. The harness is the actual deliverable; A1 is one symptom. This lands first so the remaining fixes are written against a suite that can see them.

## A1 — Restore endpoint returns 400 on every request *(blocker)*

**Scope:** `src/backend/api/backup.py:360`.

**Problem.** `session: Session = Depends(require_profile_access())` reads `request.path_params["profile_id"]`. The route's only path parameter is `backup_id`, so the dependency raises before any handler logic. Verified live: `400 {"detail":"Missing profile_id parameter"}`. The restore feature — BK-01's data-correctness fix and the FE-02/FE-03 UI built on it — has never worked over HTTP.

**Solution.** Replace with `RequireAuth` and derive scope from `session.profile_id`, matching every other route in the module.

**Logic choice.** `require_profile_access` was never the right dependency here, not merely misconfigured: the route is single-profile by construction (`_resolve_backup_dir(session.profile_id, backup_id)` already scopes it). Adding a `profile_id` path parameter to satisfy the dependency would introduce a redundant, spoofable input for no gain.

## A2 — Downloaded backups leak every other profile's credentials *(blocker)*

**Scope:** `src/backend/scripts/backup.py:229`, `src/backend/api/backup.py` (`download_backup`).

**Problem.** Profile-scoped backups deliberately retain `healthcentral.db` (`db.name == "healthcentral.db" or db.parent.name == profile_id`), and `download_backup` does `path.rglob("*")` into the zip. A user downloading their own backup receives every profile's `display_name`, bcrypt `password_hash`, `password_salt`, and the entire `audit_logs` table. This breaks the per-profile isolation invariant on the multi-profile (family) use the product supports.

`HC-BKUP-014` appeared to cover this but asserts on *filenames* (`not any("profile-b" in n for n in names)`), so it passes while the data leaks inside a file whose name is innocuous.

**Solution.** Separate the two directions. Keep `healthcentral.db` in the on-disk backup — restore needs the password hash. **Exclude it from the download archive**, substituting a single-row extract containing only the requesting profile. Replace HC-BKUP-014's filename assertion with one that opens `healthcentral.db` inside the archive and asserts exactly one profile row.

**Logic choice.** Restore and export have opposite requirements: restore must have the master row or a post-backup password change strands the vault; export must never carry another profile's data off the device. One artifact cannot satisfy both. BK-01 correctly solved the restore direction and never asked what happens when the same file leaves the machine.

## A3 — Restore reports "Nothing was changed" after replacing the vault *(blocker)*

**Scope:** `src/backend/scripts/backup.py:452`, `src/backend/api/backup.py`, `src/frontend/src/components/settings/BackupCard.tsx`.

**Problem.** If `_reapply_profile_row` raises, `restore()` returns `success=False` *after* the copy loop already replaced `vault.db`, `key.bin` and `key.recovery.bin`. The API returns 500 and the UI displays "Restore failed. Nothing was changed." That is false, and the user is left with a vault whose keys may not match the live password hash.

**Solution.** Distinguish two failure modes on `RestoreResult`: `success=False` (nothing was touched — validation or verification failed before any copy) and a new `partial=True` (files were replaced, reconciliation failed). Surface partial failure with copy that says the data was replaced, names the `.bak` safety copies, and states which password now applies.

**Logic choice.** A false reassurance during data loss is worse than an alarming true message. `_reapply_profile_row` is code introduced by BK-01, so this failure mode is a regression from that commit, not pre-existing.

## A4–A8 — Medium findings

| ID | Scope | Solution | Logic |
|---|---|---|---|
| **A4** | `api/backup.py:170` | Reject `candidate == root` in `_resolve_backup_dir` | The guard's first clause (`candidate != root and ...`) makes the whole condition false at the root, so `backup_id="."` zips the entire backup directory as one archive. The root is not a backup and must never resolve. |
| **A5** | `VerificationWorkbench.tsx:196` | Gate the cited-observation effect on a `hasAppliedCitation` ref | The effect depends on `observations`; verifying invalidates that query, so every refetch re-applies the citation and snaps the user's selection away. A citation should be applied once per navigation, not once per fetch. |
| **A6** | `VerificationWorkbench.tsx:214` | Clear `citedNotFound` when an entity resolves; stop emitting entity links with no `doc_id` | The reset effect only fires on param *change*, so an unresolvable entity latches the notice. A citation that cannot be inspected should render as plain text at emit time — consistent with the rule already applied to reference-corpus citations. |
| **A7** | `api/profiles.py:732` | `core.time.utcnow` | New code on this branch violates a hard invariant the same branch enforces elsewhere. The six other occurrences in the file are pre-existing and out of scope for this pass. |
| **A8** | `core/audit.py:181` | Skip the warning when `action == event_type` | `_scrub_action` logs "Unregistered audit action" even when the caller deliberately passed the static `event_type`. Routine medication create/delete and password change therefore trip a drift alarm, training readers to ignore the one signal that would catch real drift. |

## A9 / A10 — Two tickets recorded DONE that are not

**Scope:** `docs/features/TASK_LIST.md`, PR #18 description (immediate); `src/frontend/` (follow-up).

**Problem.** Verified zero callers outside `services/` for both:

- **`SEC-RECOV-001`** — `useIssueRecoveryCode` is dead. Recovery codes are issued only at profile creation, so pre-existing profiles can never obtain one, and `RecoverProfile.tsx` directs them to a screen that does not exist.
- **`MED-CORR-001`** — the correlations endpoint is dead. `TrendsDashboard.tsx` and `MedicationDetail.tsx` both still use `utils/correlation.ts`, and the two implementations already disagree on the `verified_only` default.

**Solution, split by kind.** Correct the tracker rows and the PR description **now** — the claim is false as written. Implement the missing recovery-code settings entry point and wire the correlations endpoint (reconciling `verified_only`) in the follow-up PR.

**Logic choice.** An inaccurate DONE is a documentation defect fixable today. Building a new settings screen is a feature, and adding it to a 133-file PR would repeat the mistake that produced this audit. Two definitions of one clinical rule is the more urgent of the two to reconcile, because divergence is silent.

## Phase A delivery

- **PR #18:** A0, A1, A2, A3, plus the A9/A10 documentation corrections. Shipping a dead endpoint and a cross-profile credential leak is not acceptable.
- **Follow-up PR:** A4–A8, and the A9/A10 implementations.

**Verification.** Each fix test-first, failure observed before the fix. Full backend suite with no new failures (baseline 1205 passed, 1 known env-only embedding failure — the 0.7 threshold stays untouched). `npx tsc --noEmit` clean. Playwright 25 passed / 3 skipped. **A route-level test asserting `POST /backup/{id}/restore` returns 200** — the assertion whose absence caused A1.

---

# Phase B — Rename to Asclexis, and branding guidelines

**Objective:** execute the pre-written rename, extended to cover surfaces the original audit could not see, and record the brand philosophy.

## Name status

**Asclexis.** Asclepius (Greek god of medicine) with a second reading — "ask" — matching a product whose purpose is clarifying uncertainty rather than resolving it.

**Screening performed 2026-07-30 (one web-search pass, the same filter the 2026-07-07 shortlist received).** No exact collision: no product, company, or application named Asclexis surfaced. The Asclepius-derived namespace is, however, dense and actively trademarked in adjacent goods: **Ascletis Pharma** (HKEX 1672 — one letter apart in the stem), **AsclepiX Therapeutics**, **Asclemed USA Inc.** (24 registered marks in medicines), Asclepius Pharmaceuticals (India), Asclepius Pharma (Egypt), Asclepios Inc.

**This is a search pass, not clearance.** `asclexis.com` registrar status was not verifiable by search. USPTO TESS and app-store checks remain the owner's. Patient software (classes 9/42) is a different class from pharmaceuticals (class 5), which helps; phonetic and etymological proximity to two biotech marks is the residual risk.

## B1 — Rename execution

**Scope:** the surface table in `docs/plans/2026-07-07-rename-audit-and-shortlist.md` — approximately 45 user-visible strings across roughly 20 files. Follow that document's stage-3 procedure.

Changes: `src/frontend/index.html` (`<title>`, meta description, apple-mobile-web-app-title), `src/frontend/package.json` name, frontend components (App, Sidebar, DocumentInbox, NotificationSettings, ProfileSetup, ExportPage, `api.ts`, `authStore.ts`), FastAPI `title=` in `main.py`, `dev.ps1` / `dev.bat` banners, `README.md`, `CONTRIBUTING.md`, `AGENT.md`, `SECURITY.md`, `config/.env.example` app-name values, and product-presenting docs.

**Explicitly preserved** — prior owner decision, recorded 2026-07-07:

- `HC-*` ticket and test prefixes (111 identifiers)
- `HC_*` environment variables
- vault filenames (`vaults/{profile_id}/vault.db`, `key.bin`, `key.method`) — these never carried the product name
- historical `docs/plans/` logs and git history

**Logic choice.** `HC-*` and `HC_*` are internal identifiers with no user-facing surface; churning 111 test IDs would produce a large diff with no benefit and would break every cross-reference in the historical logs. The `client_info` string written into audit rows *does* change to `"Asclexis v0.1.0"` — that is user-facing provenance, not a storage key.

## B1a — Master database filename *(supersedes the 2026-07-07 decision)*

**Scope:** `src/backend/core/config.py:173`, a new startup migration, `src/backend/scripts/backup.py` (`MASTER_DB_NAME`), `config/.env.example`.

**Why the prior decision is superseded.** The 2026-07-07 audit kept `healthcentral.db` on the stated grounds that "renaming breaks existing vaults." That rationale is inaccurate: vaults are named `vault.db` / `key.bin` / `key.method` and never contained the product name. Renaming the master DB cannot corrupt a vault.

**The real failure mode.** The master database is the sole index of which profiles exist, and the only home of `password_hash` and `encryption_key_id`. Point the app at a filename that does not exist and Alembic creates an empty one: the profile list renders empty and every vault on disk becomes unreachable. **No data is destroyed; all of it becomes invisible.** For a health-record application that is a severe user-facing outcome, which is why the migration below is mandatory rather than optional.

**Why now.** No packaged distribution exists — `HC-M08a` through `HC-M08d` (decision spike, frozen backend, static frontend, distribution checklist) are all `pending`. No end user can install the application today, so the affected installs are developer machines and test data. The cost of this rename rises monotonically from here: once shipped, it becomes a migration across machines nobody can inspect. Leaving it means `healthcentral.db` persists in every future user's data directory permanently — the most durable remaining evidence of the name being retired for trademark distance.

**Solution, in order:**

1. **`config.py:173`** — derive the filename from settings rather than hardcoding `"healthcentral.db"`. This also fixes a latent bug found during diagnosis: `database_url` uses only the *parent* of `sqlite_database_path`, so `SQLITE_DATABASE_PATH=data/mydb.db` silently has no effect on the filename. The setting advertises control it does not have.
2. **Startup migration, before any connection is opened.** If `asclexis.db` is absent and `healthcentral.db` is present, rename it **together with its `-wal` and `-shm` sidecars**. Nothing in the codebase handles sidecars today; orphaning a `-wal` containing unflushed transactions loses them. Guard on absent-target *and* present-source so the operation is idempotent and a no-op on fresh installs.
3. **Backup compatibility.** `MASTER_DB_NAME` is what `restore()` matches on, and every pre-rename backup manifest lists `healthcentral.db`. Accept **either** name on restore. Changing the constant naively makes `_reapply_profile_row`'s `if backup_master.exists()` guard skip silently, restoring a vault whose sealed keys may not match the live password hash — exactly the failure BK-01 was written to prevent.
4. **Test with a populated old-named database:** profiles still list, and a vault still unlocks after migration.

**Logic choice.** Renaming without step 2 is data-invisibility; renaming without step 3 reintroduces the BK-01 bug through a side door. The three are one change, not a rename plus optional extras.

## B2 — The four `skills/healthcentral-*` directories

**Scope:** `skills/healthcentral-agent`, `-backend`, `-evals`, `-guardrails`, plus references in `skills/README.md` and `AGENT.md`.

**Problem.** These postdate the 2026-07-07 audit, so its scope table does not mention them. Directory names are how agents invoke skills, making them part of the agent-facing surface.

**Solution.** Rename to `asclexis-agent`, `asclexis-backend`, `asclexis-evals`, `asclexis-guardrails`, and update the two referring files. **Owner-confirmed 2026-07-30.**

**Logic choice.** Low blast radius, and leaving them makes the retired name permanent in the surface agents read every session. This is an addition to the prior decision, not a contradiction of it — that decision scoped out `HC-*` *identifiers*, which these are not.

## B3 — Branding guidelines

**Scope:** new `docs/brand/brand-guidelines.md`.

**Contents.** Brand philosophy anchored in the product's real constraints: the name's dual reading; the positioning as an explanatory companion; and the hard boundary that **the product explains and never diagnoses**, already enforced in code by `modules/interpret_safety.py`. Voice and tone rules derived from existing UI copy that gets this right — for example the deletion warning, which states a mechanism ("Your encryption key is destroyed, which makes the data unreadable") instead of a reassurance. Prohibited constructions: anything implying diagnosis, dosing, or prognosis. The existing Tailwind tokens (`surface`, `accent`, status colours) documented as the palette.

**Logic choice.** For this product, branding is mostly a safety document. The largest brand risk is not visual inconsistency but copy that implies medical advice — which is also a compliance risk and a violated invariant. Documenting the palette that already exists, rather than inventing one, keeps the guidelines true on the day they are written.

**Verification.** Grep for the old name returns only historical logs and the preserved identifiers. App boots with the new title. `npx tsc --noEmit`, vitest, and the docs gates (`docs_lint.py`, `generate_docs_index.py --check`) pass. `feature_list.json` `HC-M10` → `completed`; decision recorded in `docs/agentic/progress.md`.

---

# Phase C — Agent instructions for Opus 5.0

**Objective:** correct what is false in `CLAUDE.md` and `AGENT.md`, surface what is hidden, and tune guidance to current model capability.

## C1 — Correct stale facts

**Scope:** `CLAUDE.md:26`, `AGENT.md:26`.

Both claim **"~620 backend tests"**. The real figure is **1205**, roughly double — in the two files agents trust most, used as the baseline for judging whether a change broke anything. Also refresh the key-flows section for what landed since it was written: backup/restore routes and the scheduler, profile recovery, profile deletion.

**Logic choice.** A stale baseline is worse than no baseline: an agent that reads "~620" and observes 1205 has no way to tell whether it is looking at drift or at its own breakage.

## C2 — Make the skills discoverable

**Scope:** `CLAUDE.md`, `AGENT.md`.

**Problem.** Eighteen skills exist — 14 process skills in `.claude/skills/` and 4 domain skills in `skills/`. `CLAUDE.md` does not mention skills at all. `AGENT.md` names the two directories and warns not to confuse them, but never names a single skill or says when to reach for one.

**Solution.** A compact routing table: skill name → when to invoke it. Grouped by process (test-driven-development, systematic-debugging, writing-plans, verification-before-completion, requesting-code-review …) and domain (the four `asclexis-*` skills after B2).

**Logic choice.** An unreferenced skill is a skill nobody invokes. This is the highest-value change in Phase C, because the skills already exist and are simply invisible.

## C3 — Tune guidance to Opus 5.0

**Scope:** `CLAUDE.md`, `AGENT.md`.

**Note:** neither file contains any model-version string, so this is not a find-and-replace. It is a change of register.

**Solution.**

- Replace prescriptive step-by-step scaffolding with intent plus invariants — state what must remain true, not the sequence of keystrokes.
- State that verification must be **run and its output reported**, never asserted. This audit's central lesson: 1205 green tests coexisted with a completely dead endpoint and a credential leak, because the tests exercised handlers instead of routes.
- Add the route-level testing expectation from A0 as a standing rule: a test that bypasses the framework's dependency graph does not prove the endpoint works.
- Add guidance on parallel subagent dispatch for independent read-only investigation, and on preferring one broad exploration pass over many narrow ones.
- Keep every existing hard invariant verbatim. They are load-bearing and were not the problem.

**Logic choice.** The useful adjustment for a more capable model is fewer procedural rails and sharper statements of what must hold — the model can derive the steps, but cannot derive an invariant nobody wrote down. The verification rule earns its place because this session produced a concrete, expensive counterexample.

**Verification.** `docs_lint.py`, `generate_docs_index.py --check`. Every factual claim in both files spot-verified by running the command it describes — the test count, the boot command, the gate commands. No claim ships unrun.

---

## Out of scope

- `PRAGMA foreign_keys` repo-wide (`SQL-FK-001`) — a behaviour change for every relationship, needs its own audit.
- Agent-path citation page numbers (`CITE-AGENT-001`) — requires widening agent tool return shapes.
- The absent sign-in / unlock screen. `useLogin` and `useUnlockProfile` exist with no consuming page, which makes the post-restore landing thinner than it should be. Pre-dates this work; worth its own ticket.
- Renaming the repository directory.
- The six pre-existing `datetime.utcnow()` calls in `api/profiles.py` outside line 732.

## Decision log

| Date | Decision | Supersedes |
|---|---|---|
| 2026-07-07 | Rename the product; keep `HC-*`/`HC_*` identifiers and storage filenames | — |
| 2026-07-30 | Name is **Asclexis**; screened (no direct collision), formal clearance still the owner's | 2026-07-07 stage 2 |
| 2026-07-30 | **Rename the master DB to `asclexis.db`** with a startup migration | The 2026-07-07 "keep storage filenames" decision, whose stated rationale ("renaming breaks existing vaults") was inaccurate — vaults never carried the product name |
| 2026-07-30 | Rename `skills/healthcentral-*` → `asclexis-*` | Not covered by 2026-07-07 (these skills postdate it) |
