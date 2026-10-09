**READY** (plan-only) — the owner's "Plan only" answer is recorded, the evidence is in the tree, and no plan file exists yet. Nothing under `src/` is edited by this phase.

# AUDIT-ORDER (+ AUDIT-DENIALS) — plan-writing phase (readiness pack)

**Measured:** 2026-10-07, worktree `hc-scaffold` @ `8d6f02e`, `origin/main` = `6b4dd84`. All `src/**` lines below are identical on `origin/main` (this branch changes docs only).
**Output of the phase:** one new file `docs/plans/2026-10-0X-AUDIT-ORDER.md` (plus the regenerated `docs/INDEX.md`, `docs/_link_graph.json`), one docs PR, **not approved for execution**. Precedent: PROHIBITED-PARAPHRASE plan PR #47, NPM-MAJORS plans PR #43.
**Kind:** DOCS (plan). Architectural subject (audit path, ask-first `core/audit.py`) → Codex plan review.

## 1. Readiness verdict

| Input | State |
|---|---|
| Owner licence | `owner-decisions-2026-09-27.md:63`, AUDIT-ORDER, **Plan only**: "An architect writes a plan with options (audit-intent row first, outbox, or accept and document) plus a Codex review. It touches ask-first core/audit.py, so nothing is edited until you approve the plan. AUDIT-DENIALS is planned with it." |
| That row on `origin/main` | **no** (0 hits) until PR #49 merges |
| Plan file | none: `git ls-files 'docs/plans/*AUDIT-ORDER*' \| wc -l` → 0 |
| Code evidence | present and measured (§2) |
| Execution of any option | NOT licensed; needs a later owner approval of the plan |

## 2. Task 0 evidence (measured)

| Check | Command | Output |
|---|---|---|
| DDI fix on main (PR #41) | `git merge-base --is-ancestor 421c441 origin/main; echo $?` | 0 |
| SAFE-INTERP-GROUNDED (PR #48) | `git merge-base --is-ancestor ee5721d origin/main; echo $?` | 0 |
| Owner row, worktree | `grep -c AUDIT-ORDER docs/capstone-report/owner-decisions-2026-09-27.md` | 2 |
| Owner row, main | `git show origin/main:docs/capstone-report/owner-decisions-2026-09-27.md \| grep -c AUDIT-ORDER` | **0** |
| Program items | `implementation-program.md:487` (AUDIT-ORDER), `:488` (AUDIT-DENIALS) | present in this worktree |

### Commit order, measured on 2 write routes

**Route 1: `DELETE /documents/{document_id}`**, `src/backend/api/documents.py`

| Line | What happens |
|---|---|
| `:1813-1819` | `delete_document(…, profile_db: ProfileDbSession, master_db: AsyncSession = Depends(get_db))` |
| `:1873` | `await profile_db.delete(document)` |
| **`:1874`** | **`await profile_db.commit()`** — the patient-data delete is durable here |
| `:1883-1891` | `doc_path.unlink()` at `:1885`; an `OSError` is logged and swallowed |
| `:1894-1900` | `await log_document_event(db=master_db, event="delete", …)` — only `db.add()` (see below) |
| **`:1901`** | **`await master_db.commit()`** — the audit row is durable here |

**Route 2: `POST /observations/{observation_id}/verify`**, `src/backend/api/observations.py`

| Line | What happens |
|---|---|
| `:380-387` | `verify_observation(…, profile_db: ProfileDbSession, master_db: AsyncSession = Depends(get_db))` |
| `:458` | `observation.user_verified = True` |
| **`:491`** | **`await profile_db.commit()`** |
| `:494` | `await log_observation_event(…)` |
| **`:506`** | **`await master_db.commit()`** |

**`src/backend/core/audit.py`**

| Line | What happens |
|---|---|
| `:201-266` | `create_audit_log`: builds the row, `db.add(audit_log)` at `:252`, `logger.info` at `:257`. No `flush`, no `commit` |
| `:305-335` | `log_document_event` → `create_audit_log` |
| `:474-487` | `audit_and_commit`: `entry = await log_fn(db=db, **log_kwargs)` `:485`; `await db.commit()` `:486`. Docstring: "Used by read (view) routes … a view that cannot be audited must not be served" |
| `core/database.py:104-119` | `get_db`: `yield session` `:115`, `await session.commit()` `:116`, rollback on exception `:117-119` |

So on both routes the two databases commit in the order profile → master, with nothing linking them. If the master commit at `:1901` / `:506` raises, the request returns 500, the change stays, and no audit row exists. For `delete_document` the file is already unlinked (`:1885`).

Size of the pattern (grep counts per file in `src/backend/api/`, not a route-by-route walk):

| File | `await profile_db.commit()` | `await master_db.commit()` / `await db.commit()` | `audit_and_commit(` |
|---|---|---|---|
| `documents.py` | 12 | 5 | 8 |
| `medications.py` | 8 | 2 | 1 |
| `model_settings.py` | 8 | 0 | 0 |
| `pinboards.py` | 6 | 0 | 8 |
| `assistant.py` | 5 | 0 | 1 |
| `memory.py` | 3 | 0 | 5 |
| `care_tasks.py` | 2 | 2 | 2 |
| `notifications.py` | 2 | 0 | 0 |
| `observations.py` | 1 | 1 | 5 |
| `feedback.py` | 1 | 1 | 0 |
| `interpretations.py` | 1 | 0 | 1 |
| `profiles.py` | 1 | 11 | 0 |
| `backup.py` | 0 | 2 | 7 |
| `export.py` | 0 | 0 | 9 |

A real audit-commit failure is on record: CI run 37453242129 on main `29c11e8`, `sqlcipher3 … disk I/O error` on the commit at `core/audit.py:486`, called from `api/documents.py:1547` (program item E2E-MASTER-CORRUPT).

### AUDIT-DENIALS, measured

| Fact | Evidence |
|---|---|
| The security middleware logs mutating methods only; GET is skipped | `security/audit_middleware.py:20` `MUTATING_METHODS = {"POST","PUT","PATCH","DELETE"}`; `:42` `if method not in MUTATING_METHODS:` → pass through |
| A cross-profile 403 **is** logged, at WARNING, with both profile IDs, but writes no audit row | `core/auth.py:279-286` (`logger.warning("Profile access denied: session profile … attempted to access …")`, then `HTTPException(403)`) |
| The program text "not audited or logged anywhere" is therefore too strong for this 403 | `implementation-program.md:488` says "not re-measured by L0" |
| GET 404 denials (wrong ID inside the caller's own profile) | no log or audit site found by grep for `access_denied` / `.denied` / `event_type="security.` in `api/`, `core/`, `security/` (0 hits); a full route walk is UNMEASURED |

## 3. Owner questions the plan must put (ready-to-ask wording)

These go into the plan as unsigned lines. None is asked before the plan exists, except question 6.

1. **AO-DESIGN.** "On write routes the audit row is saved after your data change, in a different database. If saving the audit row fails, the change stays with no record. Which design?"
   - A. **Intent row first:** save a 'started' audit row in the master DB, make the change, then mark the row 'done'. A failed change leaves a visible 'started' row. Needs a new status column (master migration), `core/audit.py` and `models/audit.py` edits.
   - B. **Outbox:** write the audit record inside the patient vault in the same transaction as the change, and copy it to the master DB afterwards. Needs a new vault table (profile migration), a relay, and a rule for a locked vault.
   - C. **Accept and document:** keep the order; state the window in the compliance docs; log an ERROR when the audit commit fails.
   - D. **Intent row for irreversible routes only** (document delete, profile delete, restore), accept and document for the rest.
   - Recommended starting point for the architect: D, to be confirmed or overturned by the plan's own measurements and the Codex review. The owner decides.
2. **AO-FAIL.** "If the audit row cannot be saved *before* the change, should the request fail and change nothing?" A. Yes, fail closed, as view routes already do (`core/audit.py:479-484` docstring) **(recommended)** · B. Proceed and log an error.
3. **AO-SCOPE.** "Which routes?" A. Every route with both commits (list from the plan's route walk) · B. Irreversible deletes only **(recommended first PR)** · C. Documents and observations only.
4. **AD-DENIALS.** "Denied requests (403 across profiles, 404 on someone else's ID) leave no audit row. What do you want?"
   - A. Audit row for every 403/404 on patient-data routes (grows the master DB; an attacker can fill it; needs a cap).
   - B. Audit row for cross-profile 403 only; 404 stays unlogged. **(recommended starting point)**
   - C. Log line only (already true for the 403 at `core/auth.py:279`), no audit row.
   - D. Leave as is and document it.
5. **AO-ASKFIRST.** "The chosen option edits these files. Approve each by name?" `core/audit.py` (functions: ____), `models/audit.py` + a master migration (options A, D), a profile migration (option B), `core/auth.py:279-286` (AD-DENIALS A or B: auth, ask-first under CLAUDE.md §1). One line per file, signed separately.
6. **AO-BRIEF4 (ask before the plan is written).** "The audit-row schema is also the subject of packet Brief 4 (audit retention, purge-on-erase; unsigned). May the AUDIT-ORDER plan assume today's behaviour (rows kept, `delete(AuditLog)` on profile erase at `api/profiles.py:909`), and list Brief 4 as an open dependency?" A. Yes **(recommended)** · B. Decide Brief 4 first.

Ask-first touches of this phase: **none** (plan file only). Ask-first touches the plan will request: `core/audit.py` (ask-first by the owner's own wording at owner-decisions `:63`; CLAUDE.md §1 does not list it by name), `models/audit.py`, `core/auth.py`.

## 4. Plan drift check

No plan exists. The citations in the registers were re-checked:

| Register citation | Now | Result |
|---|---|---|
| `implementation-program.md:487`: "`delete_document` unlink at `api/documents.py:1885` @`25c993e`" | `:1885` | MATCH |
| same: "the ordering itself not re-walked by L0" | walked here for 2 routes (§2) | now MEASURED |
| `:502` E2E-MASTER-CORRUPT: `core/audit.py:486` from `api/documents.py:1547` | `:486` commit; `:1547` `await audit_and_commit(` | MATCH |
| `:488` AUDIT-DENIALS "not audited or logged anywhere" | 403 is logged at `core/auth.py:279` | **CHANGED** (claim too strong) |
| `:472` AUDIT-KEYS-DROPPED: `ALLOWED_DETAIL_KEYS` allowlist | `core/audit.py:89`, `_scrub_details` `:118` | MATCH (same file; the plan should say whether it folds this in) |
| `:480` DOC-OVERCLAIM "append-only" vs `delete(AuditLog)` at `api/profiles.py:908-910` | `:909` | MATCH |

Amendment for the registers (L0's edit, not this pack's): correct `implementation-program.md:488` to "the cross-profile 403 is logged at WARNING (`core/auth.py:279`), with no audit row; GET 404s are not logged".

## 5. File ownership and overlap

**Owned by this phase:** `docs/plans/2026-10-0X-AUDIT-ORDER.md` (new), `docs/INDEX.md`, `docs/_link_graph.json` (regenerated), and one link line in `docs/capstone-report/implementation-program.md` if L0 adds it (L0's edit).
**Read-only:** all of `src/**`, `CLAUDE.md`, `AGENT.md`.

| Other phase | Overlap | Note |
|---|---|---|
| W-2 | its plan names `core/audit.py` 6 times (`ALLOWED_DETAIL_KEYS`, a `redaction_count` detail) and `models/audit.py` | the AUDIT-ORDER plan must order itself against W-2 |
| W-11a PR-1 | adds audit rows to 4 profile routes in `api/profiles.py` | new call sites inherit whatever order the plan picks |
| W-7 | adds audit rows on interpretation routes if its OG-3 is signed | same |
| P5 | `utcnow` swaps in `api/*.py`, including `documents.py`, `observations.py` | line numbers in §2 will move; re-measure |
| P6 | master and profile engines, FK pragma; migrations | options A, B, D add a migration: linear `down_revision` after P6's |
| G-C1 | profile migration `014`; `api/export.py`, `api/profiles.py` | option B's profile migration must not collide with `014` |
| P7 | test-reset tuple | a new table (option B) must be added to the reset tuple |
| W-10 / W-10b | option C needs a `data-privacy.md` sentence; W-10 is that file's only editor | route the sentence through W-10b or a W-10 addendum |
| G-C2, G-C3a, P4-deferred | `docs/INDEX.md`, `docs/_link_graph.json` | generated; the PR that merges second regenerates |
| PROHIBITED-PARAPHRASE, NPM-AUDIT-2, React Router 7, Tailwind 4, W-3, W-4, W-8, W-11a PR-3, G-C5 | none | — |

Count slots (ground rule 8): the plan PR adds no test; `CLAUDE.md` / `AGENT.md` are not edited.

## 6. Briefs

### L1 brief (filled)

```
You are the L1 Wave Orchestrator for the AUDIT-ORDER plan-writing phase of the
Asclexis execution program. Follow docs/agentic/orchestration.md §3; you are L1.
This phase writes a PLAN. It edits no file under src/, scripts/, config/ or .github/.
Licence (owner-decisions-2026-09-27.md:63, verbatim): "An architect writes a plan
with options (audit-intent row first, outbox, or accept and document) plus a Codex
review. It touches ask-first core/audit.py, so nothing is edited until you approve
the plan. AUDIT-DENIALS is planned with it."
Base: origin/main @ <sha after PR #49>. Starting evidence:
audit/2026-09-25/waves/scaffold/AUDIT-ORDER.md §2 (re-measure every line).
Worktree ../hc-audit-order, branch docs/audit-order-plan, one PR titled
"docs(audit): AUDIT-ORDER + AUDIT-DENIALS plan (not approved for execution)".
Step 1: spawn the plan author: Agent(general-purpose, model="opus") with the
brief below. (The `architect` agent type has no Write tool, so it cannot create
the file; use it only as a second read-only opinion if you want one.)
Step 2: Codex plan review, read-only (handoff §7; owner direction 2026-10-07:
model "6.1 sol", fallback "6-luna" at high effort; confirm the IDs with `codex`
first). Prompt from docs/reviews/2026-09-27-swarm/W04-r1-prompt.md. Focus: failure atomicity across two
databases; fail-open paths; PHI in any new audit or outbox column; migration
order vs P6 and G-C1. At most 2 rounds. Store prompt, output and response under
docs/reviews/2026-09-27-swarm/AUDIT-ORDER-r<N>-*. Verify each finding
against the code before the author applies it.
Step 3: reviewers: code-reviewer (opus) for plan quality and security-reviewer
(opus), because the subject is audit integrity and an auth file.
Step 4: python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py
--link-graph on the clean worktree; commit the plan + the two generated files.
Acceptance, pasted:
  git diff --name-only origin/main...HEAD -> the plan, docs/INDEX.md,
    docs/_link_graph.json only
  git diff --name-only origin/main...HEAD -- src scripts config .github | wc -l -> 0
  grep -c '^- \[x\]' docs/plans/2026-10-0X-AUDIT-ORDER.md -> 0 (no ticked box)
  grep -c "not approved for execution" <plan>  -> >= 1
  python3 scripts/docs_lint.py                   -> Docs lint passed.
  python3 scripts/generate_docs_index.py --check -> exit 0
  python3 scripts/harness_drift_check.py         -> passed
  python3 scripts/repo_hygiene_check.py          -> passed
  collect-only (D9 venv, HF_HUB_OFFLINE=1)       -> unchanged vs origin/main
Return the PR URL, the Codex verdict per round, the owner questions as the plan
states them, and the open findings.
Do not merge. Do not sign gates. Do not edit core/audit.py or any other code.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

### Plan-author brief (filled)

```
Write docs/plans/2026-10-0X-AUDIT-ORDER.md in worktree
/mnt/c/Users/DangT/Documents/GitHub/hc-audit-order (branch docs/audit-order-plan).
Use the superpowers:writing-plans skill. You are read-only on everything except
that one new file. Do not edit any file under src/. Do not run the full suite.
Read first: CLAUDE.md, AGENT.md, docs/agentic/recurring-failures.md (§1, §2, §9),
audit/2026-09-25/waves/scaffold/AUDIT-ORDER.md, the program rows AUDIT-ORDER,
AUDIT-DENIALS, AUDIT-KEYS-DROPPED, E2E-MASTER-CORRUPT, DDI-ORPHAN-BIN, and
docs/plans/2026-10-04-DDI-doc-delete-interpretation.md as the format precedent.
Problem: on write routes the patient-data commit (per-profile SQLCipher vault)
happens before the audit commit (master DB); a failed audit commit leaves a change,
including an irreversible document delete, with no audit row.
Evidence you must gather and cite as file:line at the tree you measure:
 1. Re-walk DELETE /documents/{id} end to end (api/documents.py delete_document:
    profile commit, unlink, log_document_event, master commit) and
    POST /observations/{id}/verify. Confirm or correct the pack's lines.
 2. Walk EVERY route that performs both a profile-DB commit and a master audit
    write. Table: route, file:line of each commit, order, reversible or not.
    Mark routes that write no audit row at all.
 3. core/audit.py in full: create_audit_log (add only), audit_and_commit, the
    scrubbers and ALLOWED_DETAIL_KEYS; core/database.py get_db commit-on-exit;
    how ProfileDbSession commits; models/audit.py columns; both Alembic chains'
    current heads.
 4. Failure injection, on paper: for each option, what the user sees and what
    each database holds when (a) the audit write fails first, (b) the change
    fails, (c) the process dies between the two commits, (d) the vault is locked.
 5. AUDIT-DENIALS: every place a 403 or 404 is raised on a patient-data route;
    what is logged today (core/auth.py:279-286 logs the cross-profile 403 at
    WARNING; security/audit_middleware.py:42 skips non-mutating methods).
 6. Which existing tests would notice a missing audit row, and which go through
    HTTP (tests/support/routes.py::route_client). State what each would fail to
    notice.
The plan must contain: approval scope with the owner text verbatim; the options
(audit-intent row first; outbox; accept and document; any hybrid you can defend),
each with files touched, migrations (dual chains, linear down_revision), PHI
exposure of any new column (the master DB is unencrypted), test list with
HC-AUD-ORD-NNN IDs through route_client, break-it steps, rollback, and effort;
a recommendation; the unsigned owner questions AO-DESIGN, AO-FAIL, AO-SCOPE,
AD-DENIALS, AO-ASKFIRST, AO-BRIEF4 with 2-4 options each; shared-file ordering
against W-2, W-11a PR-1, W-7, P5, P6, P7, G-C1; a recurring-failures recheck.
Status line: "PROPOSED — plan only, not approved for execution". No ticked boxes.
Never write that a behaviour exists unless you cite the line. Write UNMEASURED
where you did not measure.
Stop and report if the code contradicts the problem statement, or if an option
would need a threshold, safety check or validation to be weakened.
Do NOT spawn agents. Do NOT push. Do not commit; L1 commits.
Return: the plan path, the route table, the list of ask-first edits each option
needs, and what you could not measure.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

## 7. Risks and open findings

| # | Finding | Evidence | Recurring-failures mode |
|---|---|---|---|
| 1 | Two databases, no shared transaction: no option gives true atomicity; each only moves or shrinks the window | `profile_db.commit()` `documents.py:1874` vs `master_db.commit()` `:1901` | #2 the fix that creates the next bug one layer over |
| 2 | A fix applied to `delete_document` alone repeats the DDI lesson | counts table in §2: 14 route files commit patient data | #9 an invariant enforced at one site, not across its class |
| 3 | Intent rows and outbox rows are new places for PHI; the master DB is not encrypted | `core/audit.py:237-240` (AUDIT-PHI-001 choke point) | privacy invariant; must stay behind `_scrub_details` |
| 4 | Auditing every denial lets an unauthenticated or wrong-profile caller grow the master DB | `security/audit_middleware.py:42`; rate limiter is per-IP | new DoS surface; needs a cap in the plan |
| 5 | The 403 log line prints two profile IDs at WARNING to stderr | `core/auth.py:279-282` | PRIV-06 neighbourhood; ask-first file |
| 6 | Tests that assert "an audit row exists" on the happy path cannot see the failure window | route tests call the route once, both commits succeed | #1 a green suite that could not have failed: the plan needs a commit-failure injection test |
| 7 | `get_db` also commits on dependency exit (`core/database.py:116`), so an `add` without an explicit commit is still persisted when the handler returns normally, and rolled back on exception | `core/database.py:113-119` | hidden second commit path; the plan must account for it |
| 8 | The owner row licensing this phase is not on `origin/main` | grep count 0 | merge PR #49 first, so the plan can cite it |

Next action: merge PR #49, ask question 6 (AO-BRIEF4), then dispatch the L1 brief.
