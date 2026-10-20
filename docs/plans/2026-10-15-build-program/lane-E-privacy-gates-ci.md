# Lane E — Privacy, Gates, CI — Build Design

**Last Updated:** 2026-10-20 (PR #202 review round 1: Q-COV-GATE adds GATE-07; GATE-12 control wording; PKT no longer waits on #198); 2026-10-19 (follow-ups planned: REDACT-WS-REDOS, GATE-12, Q-COV-GATE, PKT-QUESTIONS-REDACT); 2026-10-19 (E-1c review round 2: HC-PKT-023, E1C-SCOPE row cited on main); 2026-10-18 (EXPORT-COLLECTED-TZ planned; owner answered (c)); 2026-10-17 (E-1b, REDACT-EMAIL-REDOS, DEV-SH-CC planned)
**Owner:** repository owner
**Status:** DESIGN — nothing here is implemented. Owner answers are quoted from [owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md); this file records no new approval. Every "default" or "recommended" is the lane designer's, not the owner's.
**Refresh Trigger:** any merge of #74, #72, #84 or a P6/P7 PR; an owner answer to S-3, S-6, OG-1, Q-AUD-LIST, Q-RUFF, Q-COV, CI-SEED, NPM-AUDIT-CI or W1-SMOKE-RUN; any commit to `.github/workflows/ci.yml`, `src/backend/api/export.py`, `src/backend/modules/export.py`, `src/backend/modules/redaction.py`, `src/backend/api/profiles.py`, `src/backend/core/auth.py`, `src/backend/core/denial_audit.py` or `src/backend/tests/support/routes.py`.
**Base measured:** `origin/main` @ `3b2236c` (2026-10-15). Every `file:line` without a ref is at this base. Open PR branches read with `git diff origin/main...origin/<branch>` and `gh pr view` on 2026-10-15; they are assumed to merge as-is.

> **For agentic workers:** one item = one PR on its own worktree. RED test first. Route tests go through `tests/support/routes.py::route_client`. Never pick a side in a count-slot conflict: recount. The merged plans (W02, W11a, AUDIT-ORDER, TW4 brief) stay authoritative; this file gives only the corrections they need on today's main.

**Baseline note:** `CLAUDE.md:30,:34` and `AGENT.md:76` read **1574 collected** at `3b2236c`, not the 1501 the dispatching orchestrator quoted. Not re-measured here (no pytest on this host). Each item's Task 0 measures its own start count and stops if the slots differ.

---

## 1. Items

| ID | Item | Source | Plan on main? | Depends on | Readiness |
|---|---|---|---|---|---|
| E-1 | W-2 doctor-summary strict redaction (D3) | [W02 plan](../2026-09-27-W02-doctor-summary-redaction.md); program `:435` | yes → delta §2.1 | P0-B2, P1, P4, W-10, P5, D9: all done | ready to execute; **merge** blocked on S-3 + S-6 |
| E-2 | W-11a PR-1: HTTP guard tests on profile routes (+ OG-1 audit rows) | [W11a plan](../2026-09-27-W11a-test-and-gate-hardening.md) Tasks 1–2; program `:442` | yes → delta §2.2 | P7 (→ P6), not on main | blocked-on-item |
| E-3 | W-11a PR-3: migration-head test, CI eslint + build, ruff, coverage report | W11a plan Tasks 4–10; program `:444` | yes → delta §2.3 | P4, P5 done; W-4 dependency dropped (§2.3) | ready (Task 7 only after Q-RUFF) |
| E-4 | Tailwind 4 landing (#74) | #74 body; [TW4 brief](../../../audit/2026-09-25/waves/briefs/TAILWIND-4-L1-brief.md); owner rows `:64-73,:108-111,:138-140` | yes (brief + PR) → landing steps §2.4 | E-3 (recommended first), owner TW4-SHOTS | blocked-on-owner |
| E-5 | NPM-AUDIT-DRIFT: the 7 remaining advisories | program `:493` (closed row; "the remaining 7 need Tailwind 4"), `:427` | no (closed row) → §2.5 | E-4 merged | blocked-on-PR |
| E-6 | W1-SMOKE: owner `/agents` runtime smoke | program `:487`; [W01 plan](../2026-09-27-W01-harness-agents-branch-a.md) Task 7 | yes → §2.6 | — | blocked-on-owner |
| E-7 | AUDIT-ORDER / AUDIT-DENIALS status reconciliation | [AUDIT-ORDER plan](../2026-10-09-AUDIT-ORDER.md) `:5`, `:467`; program `:488-489` | yes (executed) → §2.7 | — | ready (DOCS) |
| E-1b | strict misses parenthesised qualifier, `#`/`no.` after a bare label, `-` separator | queue status 2026-10-16 second batch; E-1a plan residual gaps 8–10 | yes → §2.8 | E-1a (merged #108) | blocked-on-owner (E1B-SCOPE, then E1B-DIFF); ask-first `redaction.py` |
| REDACT-EMAIL-REDOS | quadratic `email` rule | queue status 2026-10-16 second batch | yes → §2.9 | — | blocked-on-owner (REDOS-APPROACH, then REDOS-DIFF); ask-first `redaction.py` |
| DEV-SH-CC | `dev.sh` compiler check; skip `llama-cpp-python` under `LLM_PROVIDER=ollama` | queue status 2026-10-16 third batch (MM-4); DEV-SH `owner-decisions:147` | yes → §2.10 | — | ready |
| EXPORT-COLLECTED-TZ | which day the doctor summary and visit-prep packet print for a lab result | queue status 2026-10-17 (EXPORT-TODAY-TZ planning) | yes → §2.11 | EXPORT-TODAY-TZ merged (same files) | ready after EXPORT-TODAY-TZ merges; owner answered (c) |
| E-1c | strict misses spaced label shapes (`MRN (hospital): A12345`, `Patient #: 98765`, `MRN - A12345`, ...) and the E-1b review residuals | PR #179 L0 ruling, Known gaps, security review finding 2 | yes → §2.12 | E-1b (merged #179) | ready to build: E1C-SCOPE (b), `owner-decisions-2026-09-27.md:272`; merge needs E1C-DIFF; ask-first `redaction.py` |
| REDACT-WS-REDOS | strict `dob` and `name_context` (also standard) quadratic on whitespace runs | PR #195 follow-ups; owner REDACT-WS-REDOS `:276` (plan only) | yes → §2.13 | E-1c (merged #195) | blocked-on-owner (REDACT-WS-REDOS-BUILD, then REDACT-WS-REDOS-DIFF); ask-first `redaction.py` |
| GATE-12 | conftest guard: no test may open the real master DB | owner GATE-12 `:299`; §6 Q-E3; contracts §e item 5 | yes → §2.14 | — | ready |
| Q-COV-GATE | CI fails below 74% backend coverage | owner Q-COV `:300`; W-11a `:1953` | yes → §2.15 | — | ready |
| PKT-QUESTIONS-REDACT | the stored visit-prep / pinboard packet keeps raw question text | PR #198 body, follow-up candidate 1 | yes → §2.16 | — | blocked-on-owner (PKT-Q-SCOPE, then PKT-Q-DIFF) |
| WAVE-DEP-DONE | build-wave counts a queue-ID dependency as done when any PR for it merged | queue bullet HARNESS (build-wave), 2026-10-19 C-P6 misread | yes → §2.17 | — | ready (harness, no slot) |
| PYSLOT-MODE | `scripts/pyslot.sh` never creates its lock directory (its mode 100644 was fixed by #220) | found while planning 2026-10-20 (queue bullet ENV) | yes → §2.18 | — | ready (no slot) |
| GATE12-MINORS | HC-GATE12-004 (record-only guard with the DB file present), HC-GATE12-005 (session-end backstop) | PR #206 round-2 review MINORs | yes → §2.19 | GATE-12 (#206 merged) | ready |
| PKT-Q-MINORS | HC-PKT-024/025 assert the redaction tags; two redundant imports | PR #213 review MINORs | yes → §2.20 | PKT-QUESTIONS-REDACT (#213 merged) | ready |
| REDACT-NAME-PINS | pins: strict run-on over-redaction (HC-REDACT-019), visit-prep PDF download (HC-PKT-026a/b) | owner E1C-DIFF `:273`; PR #195 body | yes → §2.21 | — | ready (tests only) |
| REDACT-NAME-GAPS | labelled names with hyphens, particles, accents, NFD marks leak in part (strict and standard) | owner E1C-DIFF `:273`; PR #195 body | yes → §2.22 | REDACT-NAME-PINS | blocked-on-owner (REDACT-NG-SCOPE, then REDACT-NG-DIFF); ask-first `redaction.py` |

Graph: `E-3 → E-4 → E-5`; `P6 → P7 → E-2`; E-1, E-6, E-7 independent. E-1 and E-3 are the two lane-E code items ready today and share no file. The 2-code-L1 limit is **box-wide, not per lane**: L0 assigns the slots across lanes (§7 P-1).

---

## 2. Per-item design / delta

### 2.1 E-1 — W-2 delta (plan rev 3 @ `40f590e` → main `3b2236c`)

**Still valid:** the architecture (one choke point: redact `summary_data` before `_summary_store`), the 8 collected items, the strict xfail for the O-3 gap, the break-it discipline, the commit plan, and the rollback. `modules/redaction.py` is byte-identical to `40f590e` (`git diff --stat 40f590e HEAD` lists no change): `VALID_POLICY_LEVELS` `:131`, `def redact` `:171`. `"redaction_count"` is still allowlisted (`core/audit.py:97`).

**What changed on main:**

| # | Change | Effect on the plan | Correction |
|---|---|---|---|
| 1 | O-2 answered **ISO-8601 dates** (owner-decisions `:84`, 2026-10-08) | Task 3 is no longer gated | Run Task 3 branch **(a)** only. `_format_abnormal_values` `modules/export.py:199`, the `strftime("%m/%d/%Y")` at `:203` |
| 2 | #78 AUDIT-DENIALS: `download_summary` 403 now calls `await audit_denial(session.profile_id, "summary", master_db)` (`api/export.py:509`) | HC-EXPR-003's last assertion `len(_audit_rows(sync_engine)) == 2  # the refusal persisted no row` (plan `:930`) fails: the 403 writes one `denial.cross_profile` row | Replace with: `export.create` rows filtered by `event_type`, still exactly 2; plus exactly 1 row `event_type == "denial.cross_profile"`, `profile_id == PROFILE_B`, `entity_type == "summary"`, `entity_id is None`, and no `summary_id` anywhere in that row. Change the first `all(r["event_type"] == "export.create" …)` check (plan `:916`) to run before the PROFILE_B request (it already does) and keep it |
| 3 | `core/denial_audit._state` is a module-level cap (20 per caller per 10 min) | A full-suite run can exhaust PROFILE_B's cap in earlier tests, so the denial row silently becomes a suppression and the new assertion flakes | Add an autouse fixture to `test_export_redaction.py`: `denial_audit._state.clear()` (pattern: `tests/test_denial_audit.py:33-38`) |
| 4 | Break-it B4 anchor (plan `:1136`) is the old 403 block without the `audit_denial` line | The `patch()` assert fires: "anchor moved" | New anchor: the `if summary_data["profile_id"] != session.profile_id:` block **including** `        await audit_denial(session.profile_id, "summary", master_db)\n` (`api/export.py:508-513`) |
| 5 | Lines moved | Task 0 Step 5 greps by content, so it still works | Corrected anchors: `_summary_store` decl `api/export.py:46`; `generate_doctor_summary` `:382`; store `:448`; audit `audit_and_commit(… export_type="doctor_summary" …)` `:451-462`; `key_findings=summary.key_findings` `:478`; `download_summary` `:485`; `export_csv` `:909`; `export_json` `:965`. `modules/export.py`: `_format_trends` `:211`; `render_pdf_summary` `:358`; `from weasyprint import HTML` `:372`; visit-prep strict precedent `:533`, `:637` |
| 6 | `route_client` gained `raise_server_exceptions: bool = True` (`tests/support/routes.py:32`) | Backward compatible | None |
| 7 | Prerequisites met: P1 (#21/#24), P4 (#40), W-10 (#53; `CLAUDE.md:60` names CSV/JSON as D3 exceptions), P5 (#54; `modules/export.py:164,352` use `utcnow()`), D9 venv `~/venvs/asclexis-311` exists | Task 0 Steps 1–2 pass | None. P0-D-MOOT is still unsigned; it was never a code dependency (plan "Dependencies" row) |
| 8 | Collected slots at 1574 | Task 0 Step 6 records N0 | End = N0 + 8; slots updated in commits 1 and 2 only (SLOT-RULE, signed) |
| 9 | Lane F W-10b variant-I contract (lane F §2.6 correction 2): HC-EXPR-003 must call `route_client` in its own body; a same-file helper does not count (the W-6 precedent) | Plan `:890`, `:926` reach `route_client` only through the same-file helper `_export_client` (`:459-484`), so W-10b would have to write U, not I | In HC-EXPR-003 only, replace both `with _export_client(...)` blocks with `with route_client(export_api.router, "/export", profile_id=…, master_db=session) as client:` followed by `client.app.dependency_overrides[get_profile_db_session] = _override_profile_db_for(PHI_ROWS)`, where `_override_profile_db_for(rows)` is the 3-line override factored out of `_export_client` (which keeps using it). HC-EXPR-001/002 keep `_export_client`. Test count unchanged |

**Not touched by any open PR:** `api/export.py`, `modules/export.py`, `modules/redaction.py`, `tests/support/routes.py` (checked against #72, #74, #82, #84, #94, #95, #97, #99, #68, #61).

**Downstream:** after merge, W-10b flips the "not yet implemented" lines at `docs/compliance/data-privacy.md:80-81` and `:191` (W-10 Q4 row `:75`). W-2 itself does not edit that file.

**Acceptance (plan "Measured acceptance", unchanged except):** HC-EXPR-003 shows 2 `export.create` rows + 1 `denial.cross_profile` row; `git diff --exit-code origin/main...HEAD -- src/backend/modules/redaction.py` exits 0; `grep -n "route_client(" src/backend/tests/test_export_redaction.py` shows a call inside `test_hc_expr_003_…`; the PR body pastes the red-first output for each new test id (HC-EXPR-001/002/003) and at least one break-it run (B1–B5), so lane F's W-10b can record I.

### 2.2 E-2 — W-11a PR-1 delta (Tasks 1–2)

**Blocked:** P7 (plan 07) is not on main, and P7 depends on P6. The plan's owned-after-P7 rule for `tests/support/routes.py` stands. Nothing below starts before P7 merges.

**What changed on main:**

| # | Change | Correction |
|---|---|---|
| 1 | #78 made `require_profile_access` write a denial row on a cross-profile 403: `core/auth.py:278-286` calls `audit_denial(session.profile_id, "profile")` with **no** `db`, so `core/denial_audit.py:72-75` opens `core.database.async_session_maker()`, the module-level master engine (`core/database.py:43-56`, default path `data/asclexis.db`, `core/config.py:41`) | Every HC-PGUARD test must `monkeypatch.setattr("core.database.async_session_maker", <maker bound to the file-backed test master DB>)` (pattern: `tests/test_external_runner_hardening.py:135`) and clear `core.denial_audit._state`. Without the patch a 403 test can write into a developer's real master DB (GATE-12, program `:522`) |
| 2 | Same change gives the guard a second observable | Add to the HC-PGUARD 403 cases: exactly 1 `denial.cross_profile` row, `profile_id` = the session's profile, `entity_type == "profile"`, `entity_id is None`. A 200 writes none. This is a test-only addition; no ask-first file is edited |
| 3 | Plan §1 lists "Auditing *denied* guard attempts (a `core/auth.py` change)" as not licensed | Done by #78 under AO-ASKFIRST (`:102`). Drop the line; PR-1 still edits no `core/auth.py` |
| 4 | Owner row RESET-AUDIT-OWNER (`:89`): "P7 stays route-only … the reset route stays unaudited until W-11a PR-1 merges" | The reset-route audit is owner-assigned to PR-1. The edit is still in `api/profiles.py`, so **OG-1 is still required** for Task 2. Ask OG-1 and Q-AUD-LIST together; do not read RESET-AUDIT-OWNER as OG-1 |
| 5 | HC-AUD-ORD-030 (`tests/test_audit_order_guard.py`) fails on any handler from which `.commit()` becomes reachable without a row in its table | Task 2 adds `audit_and_commit` to `get_current_profile` (`api/profiles.py:416`), `get_profile` (`:970`) and, under Q-AUD-LIST (a), `list_profiles` (`:241`). Add each as `"excluded: read route, audit_and_commit only"` to the table in the same commit. `reset_synthetic_test_profile` (`:477`) is already listed at `:111` |
| 6 | Line refs | Four unaudited routes still unaudited at `3b2236c`: `list_profiles` `:241`, `get_current_profile` `:416`, `reset_synthetic_test_profile` `:477`, `get_profile` `:970`. `require_profile_access` is used at `:592, :777, :972, :995, :1101` (5 sites). `route_client` `tests/support/routes.py:27-59` |

**Acceptance:** plan's (collected = start + 15; 21/22 with Task 2), plus: a 403 HC-PGUARD case fails if the `audit_denial` call is removed (break it by monkeypatching `core.denial_audit.audit_denial` to a no-op, never by editing `core/auth.py`).

### 2.3 E-3 — W-11a PR-3 delta (Tasks 4–10)

**Dependency change (this lane owns `ci.yml` order):** the plan waits for W-4 only so the `legacy-evals` job lands first. #72 (W-4) waits on the owner's 20-question model-host run (W4-20Q-HOST `:136`). Its `ci.yml` hunk adds a new job after `agent-evals`; PR-3's hunks are in `backend-tests`, `frontend-tests` and a new job after `backend-tests`. They do not overlap (`git merge-tree` of the two branches is the check at dispatch). **PR-3 no longer waits for W-4**; whichever lands second merges main and re-runs the Task 6 Step 3 YAML job-list check. This supersedes the `W-4 → W-11a PR-3` link in program `:142` (orchestrator to record).

**W-8 (lane A) step in `backend-tests`:** W-8 Task 4 adds its model-fetch step **before** `Run backend tests (with coverage report)`; the coverage step and the fail-closed check stay as Task 8 writes them. W-8 lands after E-3 and confirms the job list with lane E before opening its PR.

**`docs/architecture/ci-and-quality-gates.md`:** E-3 Task 9 edits `:19` (FE node label) and `:45` (frontend-tests row); W-8 edits `:58` after E-3 (W08 plan `:170`). Disjoint lines; the later PR rebases.

**Re-measured on `3b2236c` (WSL, `~/.local/bin/ruff` 0.15.10, read-only):** `ruff check . --select E9,F63,F7,F82` → "All checks passed!", exit 0. Full configured set (F, I, W) → 565 findings (plan: 561 on A+B). eslint / build not re-measured here; Task 5 measures them.

| # | Change | Correction |
|---|---|---|
| 1 | `ci.yml` blob `5b11870`, 214 lines, 6 jobs: `docs-lint` `:10`, `backend-tests` `:36`, `frontend-tests` `:58`, `security-scan` `:83`, `agent-evals` `:155`, `e2e-tests` `:177` | Task 6 inserts `Lint (eslint)` after `Type check` (`:75-77`) and `Production build` after `Run tests` (`:79-81`). Task 7's `backend-lint` goes after `backend-tests` (before `:58`). Task 8 rewrites `Run backend tests` (`:55-56`) |
| 2 | P5 added `time_source_lint.py` to `docs-lint` (`:33-34`) | No conflict |
| 3 | Profile chain head `012_pinboards`, master `002_backup_schedules`; lane D-2 and the wearables plans (#94) add profile migrations | HC-MIGHEAD asserts structure, not names: no change. `tests/test_care_tasks.py` hard-coded heads (ledger W-11b F-4) are not PR-3's |
| 4 | `.gitignore:54` has `.coverage`, not `coverage.xml` | Unchanged: never stage `coverage.xml` |
| 5 | Q-RUFF, Q-COV, CI-SEED unsigned (no owner-decisions row). W4-CI-SEED (`:106`) covers W-4's seed PR only | Task 7 runs only after Q-RUFF = (a); otherwise PR-3 ships Tasks 4, 5, 6, 8, 9, 10 and Task 7 follows as a one-job PR. Task 8 is report-only (no threshold), so Q-COV does not block it. Task 8 Step 4 needs its own CI-SEED answer |
| 6 | Required checks grow from 6 to 7 (`backend-lint`), 8 after #72 (`legacy-evals`) | Every later "CI 6/6" acceptance line becomes "all jobs green" with the job count stated |
| 7 | `docs/architecture/ci-and-quality-gates.md:19,:45` still say eslint/build are not in CI | Task 9 as written |

**Order inside the lane:** land E-3 before E-4 if #74 is still waiting on TW4-SHOTS, so #74's final refresh is the first Tailwind 4 head built and linted in Linux CI (#74 body: "CI has no build step: the Windows build is the only build evidence").

### 2.3a E-3a — ruff cleanup (plan; owner Q-RUFF-SET, Q-RUFF-UNSAFE, Q-RUFF-PIN, PARALLEL-WAVES)

**Target (Q-RUFF-SET):** the rule set already configured in `src/backend/pyproject.toml` (`F`, `I`, `W`), not ruff's built-in default. **Pin (Q-RUFF-PIN):** `ruff==0.17.1` in `src/backend/requirements.txt:119` (today `ruff>=0.1.0`) and in E-3 Task 7's CI job. **Fixes (Q-RUFF-UNSAFE):** safe fixes only; every finding ruff marks unsafe is fixed by hand or kept with a reason.

**Start (measured 2026-10-17 on `2ac361a`, ruff 0.17.1, PR #130 comment):** `cd src/backend && ruff check . --no-cache --statistics` → 254 I001, 152 F401, 139 W293, 19 F841, 7 F541, 7 F811: **578 errors, 536 fixable (34 unsafe)**. `ruff check scripts --no-cache --config src/backend/pyproject.toml` → 8.

**Never edited (ask-first, auth, encryption):** `core/profile_database.py`, `core/security.py`, `core/auth.py`, `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `security/__init__.py` (33 findings). They get a `[tool.ruff.lint.per-file-ignores]` entry in `pyproject.toml` naming only the codes each one has today, with the comment `# E-3a: ask-first file, owner approval needed to fix (Q-RUFF-SET)`. The PR body lists them for the owner.

**Files:** ruff-fixable Python under `src/backend/` and `scripts/` (excluding the list above), `src/backend/pyproject.toml` (per-file-ignores only), `src/backend/requirements.txt:119`. No test is weakened: a finding inside `tests/` is fixed like any other file, and no assertion may change.

**Tasks (one commit each, explicit pathspecs):**
1. **RED:** paste the start statistics above, re-measured on the worktree.
2. `ruff check . --select I001 --fix` (import order; safe). Run the full suite.
3. `ruff check . --select W293,W291,W292 --fix` (whitespace; safe).
4. `ruff check . --select F541 --fix` (f-string without placeholders; safe).
5. **F401, by hand for the unsafe ones:** apply `--fix` without `--unsafe-fixes`. For each remaining F401, keep the import when it has a side effect at import time (model registration for `Base.metadata` and Alembic `env.py`, router registration, a `__init__` re-export). Keep it by adding the name to `__all__`, or with `# noqa: F401  # side-effect import: <what>`. Remove it otherwise. Check: `python -c "from main import app"`, plus both Alembic chains: `alembic -c migrations/master/alembic.ini check` and the profile equivalent, or the repo's migration-head tests.
6. **F841 / F811, by hand:** remove a dead assignment only when the right-hand side has no side effect; otherwise rename it to `_`. An F811 redefinition in a test file means a test is shadowed: rename it so both tests run (the collected count may rise; report it). Never delete a test.
7. Pin `ruff==0.17.1`; add the per-file-ignores entries.
8. **GREEN:** `ruff check . --no-cache` → `All checks passed!`, exit 0; the same for `scripts/` with the backend config.

**Acceptance (RUNBOOK §6, pasted):** steps 1 and 8 output; full suite through `scripts/pyslot.sh` with no new failures; collected count with its delta (a rise only from renamed F811 tests); `python -c "from main import app"`; `git diff --name-only origin/main...HEAD | grep -E 'interpret_safety|redaction|faithfulness|verifier_agent|core/auth|core/security|profile_database|security/__init__'` prints nothing.

**Merge order (PARALLEL-WAVES):** E-3a merges last in its run. Never run `ruff format` (L0 ruling 2026-10-17 on #142 round 3: it reformats 230 files including ask-first files and merged migrations). Encryption-adjacent files `migrations/profile/env.py` and `core/config.py` are treated as ask-first here: per-file-ignores, not edits. Before merging: `git merge origin/main`, re-run Tasks 2 to 6 on the merged tree (safe fixes, then a hand check of anything new), re-run step 8 and the full suite.

**E-3 Task 7 delta:** with Q-RUFF-SET, the `backend-lint` job runs `ruff check .` with the configured set (not only `E9,F63,F7,F82`) and pins `ruff==0.17.1`. It needs E-3a merged first. The Step 1 seed (`F821`) still applies.

### 2.4 E-4 — Tailwind 4 (#74) landing steps

State: draft, head `9a87785`, CI 6/6 green at that head, `mergeable: CONFLICTING`. `git merge-tree --write-tree origin/main origin/feat/tailwind4` → one conflict, `docs/INDEX.md` (generated).

1. Merge `origin/main` into `feat/tailwind4` (no rebase, no force-push). Resolve `docs/INDEX.md` and `docs/_link_graph.json` by regenerating (`python3 scripts/generate_docs_index.py`), never by hand. #74 does not edit the count slots (`CLAUDE.md`/`AGENT.md` absent from its diff), so there is no slot to resolve.
2. Re-run the brief §4.5 `cn()` drift scan and the grep table on the merged tree. New since base `8234990`: #84 (if merged first) adds `space-y-2` and `text-ink-*` classes in `AchievementsWidget.tsx` / `StreakDisplay.tsx`; check the v4 `space-y` child-margin rule there (the reviewer's 3-site fix pattern). If C-GAM2B (lane C) landed first, scan its Settings switch in `SettingsPage.tsx` and its `AchievementsWidget.tsx` change too.
3. Push; CI must be green on all jobs, with a new `tw4-shots` artifact. If E-3 landed first, the `Production build` and `Lint (eslint)` steps are the Linux build evidence.
4. Owner: TW4-SHOTS "I compare them myself" (`:140`), before artifact `11731333573` vs the new after artifact. Only then flip draft → ready. Owner merges.
5. Post-merge: `cd src/frontend && npm ci && npm audit` on Windows and Linux → feeds E-5.

**Rebases after #74 (they land second):** lane A W-3 Task 5 (`TrendsDashboard.tsx`), lane B B-1 (`ExplainAssistant.tsx`, `LabInterpreter.tsx`, `SettingsPage.tsx`), WEAR-10 (`Sidebar.tsx`). C-GAM2B (`SettingsPage.tsx`, `AchievementsWidget.tsx`) may land either side; the second lander rebases.

`ci.yml` hunk: one `actions/upload-artifact@v4` step `Upload Tailwind style screenshots` at the end of `e2e-tests` (TW4-O1 `:108`). TW4-HOVER-TOUCH is done (#81 on main). **Rollback:** `git revert -m 1 <merge>`; `dev.ps1` reinstalls on the lockfile hash change (#55).

### 2.5 E-5 — NPM-AUDIT-DRIFT remainder

Program `:493` closed the drift row with "the remaining 7 need Tailwind 4"; the GATE-15 note there says CI still has no `npm audit` gate. #74's Windows acceptance records `npm audit`: "found 0 vulnerabilities (base: 7)" at `3116064`.

- **Goal:** prove 0 (or name what is left) on merged main after E-4. Design = measurement only, no code.
- **Steps:** (1) after E-4 merges, `npm ci && npm audit --json > <scratch>/npm-audit.json` in `src/frontend` on Windows and in a Linux scratch copy; (2) record total and per-severity counts plus each remaining advisory's package and fix path; (3) if > 0, each fix needs its own owner row (FE-SEQ `:69`: any transitive major comes back to the owner).
- **Acceptance:** the counts pasted into the E-4 merge report and the program row.
- **Optional CI gate (owner gate NPM-AUDIT-CI, unsigned):** `npm audit --audit-level=high` in `frontend-tests`. Default: **do not add**. A new upstream advisory would turn every PR red with no change in the PR (that is how 7 became 10 on a byte-identical lockfile, program `:493`). If wanted, put it in a separate scheduled workflow instead.

### 2.6 E-6 — W1-SMOKE

Source: program `:487`. W-1 Task 7 Steps 2–5 are a manual runtime smoke. The open risk: `windows-bootstrap-engineer` has `Edit` (`.claude/agents/windows-bootstrap-engineer.md` frontmatter), and an `Edit` with an empty `old_string` may create a file, so `docs/agentic/harness.md:28` ("so it cannot create files") may be false.

- **Run:** W-1 Task 7 as written, plus one probe added to Step 4: ask `@windows-bootstrap-engineer` to create `scripts/w01-probe.ps1` **with the Edit tool and an empty `old_string`**. Then `git -C <smoke-wt> status --porcelain --untracked-files=all`.
- **Who:** the owner, or an L1 in a fresh Claude Code session started inside the disposable smoke worktree (it dispatches each agent by name and pastes the transcript plus `git status`). Owner gate W1-SMOKE-RUN picks which; default: owner, as the plan says.
- **If the probe creates a file:** fix `harness.md`'s claim in a docs PR ("cannot create files" → "can create a file through `Edit`; the orchestrator's `git status` review is the bound"). A PreToolUse hook (W-1 OG-1) is a separate owner decision; this lane does not add one.
- **Later (test-only, optional):** HC-AGENTS-001/002 report "still ignored" when git exits 128 (wave-2-L1-C finding 3). One assert on `returncode in (0, 1)` with git's stderr in the message, in `src/backend/tests/test_claude_agent_definitions.py`. No count change. **Waits for #68 (lane F F-10, merges last):** #68 rewrites `test_hc_agents_002` (`:60-82` on its branch) and adds a `returncode != 1` check; the fix is written against #68's text, never before it.

### 2.7 E-7 — AUDIT-ORDER / AUDIT-DENIALS status

**Status check:** #56 (plan) merged `767c13c`; #78 (code) merged `a07eb9f`. On main: `core/audit.py:493` `audit_intent`; `core/denial_audit.py` (new module, AO-DENIAL-PLACEMENT "Accept as is" `:143`); `audit_intent(` at 16 call sites across `api/documents.py`, `pinboards.py`, `medications.py`, `memory.py`, `backup.py`, `profiles.py`, `interpretations.py`; tests `test_audit_order.py` (34), `test_audit_order_guard.py` (10), `test_denial_audit.py` (5).

**Stale text (DOCS PR, no product file):**
- `docs/plans/2026-10-09-AUDIT-ORDER.md:5` "Nothing in this plan is implemented yet" and `:467` "(PR not merged)" → "Executed: PR #78, merged `a07eb9f`".
- `docs/capstone-report/implementation-program.md:488-489` (AUDIT-ORDER, AUDIT-DENIALS) still point at "plan PR #56" → mark done (PR #78), keep the follow-ups below as open.

**Open follow-ups (registered, not designed here):** HC-AUD-ORD-006, the §6 PHI-column rule inside `create_audit_log`, was **not executed** (plan `:450`, decision 1; needs a new ask-first `core/audit.py` approval); UNAUDITED-WRITES (program `:505`); FEEDBACK-AUDIT-FAILOPEN (`:516`); the in-memory denial cap that resets on restart (§12 item 8, accepted).

`implementation-program.md` is also the orchestrator's status file. E-7 edits only rows `:488-489` and runs after the orchestrator's own program refresh, or folds into it.

### 2.8 E-1b — three underscore-label shapes strict still misses (ask-first `modules/redaction.py`)

**Source:** queue status 2026-10-16 (second batch); [E-1a plan](../2026-10-16-E1a-redaction-underscore-phi.md) §Residual gaps 8–10, found by the PR #108 rev 3 security review. Planned 2026-10-17 on `origin/main` @ `b54f105`.

**Measured on `b54f105`** (`RedactionEngine("strict")`, scratchpad probe, not committed):

| Input | Strict output today |
|---|---|
| `mrn_(hospital):_a12345`, `patient_name_(legal):_jane_doe` | unchanged (gap 8) |
| `patient_#:_98765`, `patient_no.:_98765`, `name_#:_jane` | unchanged (gap 9) |
| `mrn_-_a12345`, `patient_name_-_jane_doe` | unchanged (gap 10, `-`) |
| `mrn_=_a12345`, `mrn_;_a12345` | unchanged (gap 10 also lists `=` and `;`; the queue row names only `-`, so they wait on E1B-SCOPE) |
| `dob_-_01/02/1980` | `dob_-_[DATE-REDACTED]` (only the date rule fires) |
| `mrn_no._-_12345` | `[ID-REDACTED]` (already matched; `no._-_12345` is read as the value) |

**Why:** one rule, `underscore_labelled_id` (`src/backend/modules/redaction.py:136-146`). Specific labels take `(?:_*[:#.]+)?`, then `_+`, then a value that must start with `[^\W_]`, so `(`, `-`, `=` or `;` right after the `_` ends the match. The bare labels `patient` / `name` take one qualifier word `(?:_[^\W_]+)?` and then need `_*:`, so `#` or `no.` before the colon fails.

**Design (strict only; widen the one rule; no new rule, no other level):**
1. An optional parenthesised qualifier after any label: one `_(word)` group where the word is `[^\W_]+`, with no nesting and no `_` inside, so it cannot match across an `_` run.
2. On the bare labels, `#` or `no.` may sit between the label (or its qualifier word) and the colon. The branch must stay **disjoint** from the `_` runs around it: no two adjacent `_*` around an optional group. That shape is the rev 2 quadratic bug (`dob` + 50000 `_` took 7.9 s).
3. `-` as a label separator: `_-_` between the label part and the value. `=` and `;` are added only if the owner answers E1B-SCOPE (b). Recommended (b): the same review found all three, and leaving `=` / `;` keeps a known leak.
4. Everything E-1a matches still matches with the same output (HC-REDACT-001 to -008 unchanged).

The implementer drafts the exact pattern, posts it in the PR body, and the owner approves that exact diff (E1B-DIFF). This plan licenses no other edit to `redaction.py`.

**Accepted over-redaction (strict only; listed in the PR body):** labelled tokens with a qualifier, such as `mrn_(status):_ok`, become `[ID-REDACTED]`. Same class as E-1a's `patient_count:_3`.

**Test-first** (`src/backend/tests/test_redaction.py`; "RED" = fails on `b54f105`):

| Id | Assertion | RED today? |
|---|---|---|
| HC-REDACT-001 (+7 rows in `UNDERSCORE_PHI`) | the 7 gap 8–10 shapes with `-` above → the existing assertions (`secret` gone, `result.text.removeprefix("full_") == "[ID-REDACTED]"`) | yes ×7 |
| HC-REDACT-001 (+4 rows, only under E1B-SCOPE (b)) | `mrn_=_a12345`, `mrn_;_a12345`, `patient_name_=_jane_doe`, `patient_name_;_jane_doe` | yes ×4 |
| HC-REDACT-004 (+6 rows in `ANALYTE_LIKE`) | `glucose_(fasting)`, `t4_(free)`, `name_(of_test)`, `patient_(count)_3`, `ldl_-_calculated`, `mrna_-_level` unchanged, 0 redactions | no (guards; each must fail against a mutant in Task 3, as in E-1a) |
| HC-REDACT-009 ×3 | strict on `"mrn" + "_(" * 20000`, `"patient" + "_#" * 20000 + "!"`, `"mrn" + "_-" * 20000 + "!"` → under 1.0 s and text unchanged | measure in Task 0; it is a backtracking guard for the widened rule |
| HC-EXPR-001 (+1 row in `GAP_ROWS`, `tests/test_export_redaction.py:271`; no new test id: `GAP_ROWS` feeds only the non-parametrized `test_hc_expr_001_underscore_phi_redacted`, text format) | analyte `mrn_(hospital):_b67890` (a value no other row uses) → add `b67890` to that test's absent-tuple; absent from the text download | yes |

Also edit the `test_export_redaction.py` module docstring (`:9-10`): drop "the E-1b shapes" from the not-covered list and name what remains (gap 11, non-space whitespace; `=`/`;` unless E1B-SCOPE (b)).

**Tasks:** 0 start count + RED run (`-rfE`) + HC-REDACT-009 timing on `main`; 1 RED tests; 2 GREEN, the one-rule edit; 3 mutants (drop each new branch, drop the disjointness): each fails a named test, output in the PR body; 4 docstring; 5 PR as **draft** until E1B-DIFF.

**Files:** `src/backend/modules/redaction.py` (ask-first, **edited**), `src/backend/tests/test_redaction.py`, `src/backend/tests/test_export_redaction.py`.

**Expected collected delta:** +16 (7 + 6 + 3; the `GAP_ROWS` row adds no collected test); +20 under E1B-SCOPE (b).

**Acceptance** (from `src/backend`, `pyt` = `scripts/pyslot.sh env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest`):
1. `pyt tests/test_redaction.py tests/test_export_redaction.py -q -rfE`: 0 failed.
2. E-1a acceptance rows 3–4 (safety suites; the other strict callers `fhir_export`, `visit_prep`, `rl_*`, `external_runner`, `agent/test_s4_phi_gate`, `agent/test_s6_evals`): same pass/fail as Task 0.
3. Full suite per RUNBOOK §6; collected = N0 + 16 (or + 20).

**Doc claim (PR body, PRIV-04 gap column via L0):** strict now also matches a parenthesised qualifier, `#` / `no.` before a bare label's colon, and `-` as a label separator. Never "all PHI".

**Order:** never beside REDACT-EMAIL-REDOS (same two files), and never beside EXPORT-TODAY-TZ (`tests/test_export_redaction.py`). Either redaction row may go first; the second rebases and re-runs both timing tests. **Rollback:** revert; no data.

### 2.9 REDACT-EMAIL-REDOS — the `email` rule is quadratic (ask-first `modules/redaction.py`)

**Source:** queue status 2026-10-16 (second batch), found during the E-1a rev 3 review.

**Measured on `b54f105`** (one `finditer` per rule, this WSL box; the queue's 0.81 s came from another run):

| Input (no `@` anywhere) | `email` rule alone |
|---|---|
| `"mrn" + "._" * 20000` | 4.97 s |
| `"a." * 20000` | 3.80 s |
| `"a." * 40000` | 19.85 s (2× input → 5.2× time: quadratic) |

Every other rule stayed under 0.01 s on these inputs.

**Why:** `\b[A-Za-z0-9._%+-]+@…` (`src/backend/modules/redaction.py:65-72`). The local-part class contains `.` **and** `_`, so a long `._` or `a.` run is one class run. At every `\b` inside the run, the engine scans to the end of the run, finds no `@`, and fails. That is O(n²) per run. (The Haiku lead said `_` is not in the class. It is.) The domain part `[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}` backtracks only within one domain, after one `@`, so it is linear per attempt.

**Rejected: a pure-regex run-start anchor.** Replacing `\b` with the lookbehind `(?<![A-Za-z0-9._%+-])` is linear, but it **redacts less**. In `a@b.com.c@d.com` the second address continues the class run that the first match ended in, so no start is allowed and `c@d.com` stays in clear text. Today both addresses are redacted.

**Options (owner REDOS-APPROACH):**

| Option | Change | Output vs today |
|---|---|---|
| **(a) Recommended: anchor on `@`** | `RedactionRule` gets an optional `anchor: str \| None = None`. The `email` rule sets `anchor="@"`, and its pattern is unchanged, including the literal `\|` in `[A-Z\|a-z]`. For a rule with an anchor, the engine visits each `@` in turn and computes the window start: the start of the local-part class run that ends at that `@`, but never before the previous match's end. It finds the first `\b` position in `[window start, @)` and makes one `pattern.match(text, p)` call there. Every match holds exactly one `@`, because neither class contains `@`. The class run is uniform up to the `@`, so if the first `\b` start fails, every later start fails too. Each run is scanned once: linear. About 20 lines in `RedactionEngine.redact` | **identical**: same spans, same order (HC-REDACT-011) |
| (b) RFC 5321 bounds | `[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,253}`, one-line pattern edit | narrower: a local part over 64 characters with no inner `\b` (`"a" * 100 + "@x.com"`) is no longer redacted, or only its last ≤ 64 characters are. Such addresses are not valid, but today they are redacted |
| (c) leave it | none | local single-user app; the input is the patient's own text |

Removing the stray `|` from `[A-Z|a-z]` would stop redacting `jane@x.c|om`-shaped text. That is a narrowing, so no option changes it.

**Test-first** (`src/backend/tests/test_redaction.py`, next to HC-REDACT-007/008; under (a)):

| Id | Assertion | RED today? |
|---|---|---|
| HC-REDACT-010 ×3 | strict on each of the 3 input shapes above at `N = 60000` → under 1.0 s, text unchanged | yes ×3 (quadratic: 9× the `N = 20000` time, which was 0.81–5.0 s across runs, so ≥ 7 s; at `N = 20000` the fastest recorded run, 0.81 s, would pass on `main`) |
| HC-REDACT-011 | differential: build `RedactionEngine(policy_level=lvl, rules=[OLD_EMAIL])` from an inline copy of today's rule, with no anchor. The inputs are a fixed corpus (`jane@x.com`, `a.b+c@sub.x.org`, `jane_doe@example.com`, `.jane@x.com`, `-a@x.io`, `mail: jane@x.com.`, `éjane@x.com`, `jane@@x.com`, `a@b@c.com`, `a@b.com.c@d.com`, `x@y`, `@x.com`) plus 2000 seeded-random strings of length ≤ 40 over `a._-+%@é ,;\n0`. Each must give the same `text` and the same metadata spans as the new engine, at strict and at standard | no (pin; a mutant that drops the "previous match end" bound fails on `a@b.com.c@d.com`) |
| HC-REDACT-012 | a rule without an anchor keeps today's `finditer` path: the SSN/phone/underscore tests are unchanged, and one test checks `RedactionRule(...).anchor is None` by default | no (pin) |

**Files:** `src/backend/modules/redaction.py` (ask-first, **edited**: the `RedactionRule` field, the anchored branch in `redact`, `anchor="@"` on `email`), `src/backend/tests/test_redaction.py`.

**Expected collected delta:** +5 (3 + 1 + 1). Under (b): +4 (no HC-REDACT-012; HC-REDACT-011 becomes "equal on every corpus string with local part ≤ 64").

**Acceptance:** `pyt tests/test_redaction.py -q -rfE` 0 failed. The E-1a acceptance rows 3–4 suites, plus `tests/test_external_runner_hardening.py` (standard level), have the same pass/fail as Task 0. Full suite per RUNBOOK §6.

**Owner gates:** REDOS-APPROACH (licenses the edit and picks the option), then REDOS-DIFF (a yes on the exact diff before merge, as for E-1a). The PR stays draft until then. **Order:** never beside E-1b. **Rollback:** revert.

### 2.10 DEV-SH-CC — `dev.sh` dies when `llama-cpp-python` cannot compile

**Source:** queue status 2026-10-16 (third batch, MM-4); follows DEV-SH (`owner-decisions:147`, "Yes, build dev.sh").

**Fact (`b54f105`):** STEP 3 (`dev.sh:105-126`) runs one `pip install -r requirements.txt`. Its only fallback checks for `sqlcipher` in the log (`:111`). A `llama-cpp-python==0.3.35` (`src/backend/requirements.txt:72`) source build with no C compiler falls to `die "Failed to install Python dependencies"` (`:121-122`). `dev.sh` never checks for a compiler and never reads `LLM_PROVIDER`. The `.env` it would read is created later, in STEP 4 (`:139-147`). Default provider: `config/.env.example:142` `LLM_PROVIDER=llama_cpp`. `core/llm/factory.py:47-61`: `ollama` works without `llama_cpp`. When the daemon is down, it falls back to `LlamaCppProvider`, whose import is lazy (`core/llm/llama_cpp_provider.py:8`), so the app starts and that fallback reports the model unavailable.

**Design:**
1. STEP 1 adds a compiler check: `command -v cc || command -v gcc || command -v clang`.
2. Before STEP 3, resolve the provider: `$LLM_PROVIDER` from the environment, else from `src/backend/.env` if it exists, else from `config/.env.example`.
3. No compiler and provider `ollama`: warn ("llama-cpp-python skipped: no C compiler; LLM_PROVIDER=ollama does not need it"), then install a filtered requirements file without the `llama-cpp-python` line. Use the same `mktemp` + `grep -v` shape as the SQLCipher branch.
4. No compiler and any other provider: `die` **before** pip with the fix: "install a C compiler (Debian/Ubuntu: sudo apt install build-essential), or set LLM_PROVIDER=ollama".
5. A test hook, `HC_DEV_STOP_AFTER_DEPS=1`, exits 0 after STEP 3. Document it in the header beside `HC_SKIP_OCR_SETUP`. `dev.ps1` is out of scope: same gap on Windows, new row if wanted.

**Test-first:** new `src/backend/tests/test_dev_sh_prereqs.py`, skipped on Windows. Each test copies `dev.sh` into `tmp_path` with a 2-line `src/backend/requirements.txt` (`fastapi`, `llama-cpp-python==0.3.35`) and `config/.env.example`. It runs `bash dev.sh` through `subprocess` with a stub `PATH` that is **only** a `tmp_path/bin` directory (`/usr/bin` usually holds `cc`/`gcc`, so it must not be on `PATH`): symlinks to the tools `dev.sh` runs (`bash`, `grep`, `mktemp`, `tail`, `rm`, `cp`, `cat`, `dirname`, `uname`, ...; Task 1 lists them from `dev.sh`), a `python3` stub reporting 3.11 that creates the venv's `bin/python` (itself the stub) and records `-m pip` arguments, `node`, `npm`, and `cc` only when wanted, with `HC_ALLOW_WINDOWS_MOUNT=1` and `HC_DEV_STOP_AFTER_DEPS=1`.

| Id | Assertion | RED today? |
|---|---|---|
| HC-DEVSH-001 | no `cc`, `LLM_PROVIDER=ollama` → exit 0, pip got a requirements file without `llama-cpp-python`, stderr has the skip warning | yes (no filter) |
| HC-DEVSH-002 | no `cc`, `LLM_PROVIDER=llama_cpp` → exit 1 before any pip call, message names `build-essential` and `LLM_PROVIDER=ollama` | yes (pip runs first) |
| HC-DEVSH-003 | `cc` present → the full requirements file | no (pin) |
| HC-DEVSH-004 | no `cc`, env unset, `src/backend/.env` says `LLM_PROVIDER=ollama` → as 001 | yes |

**Files:** `dev.sh`, `src/backend/tests/test_dev_sh_prereqs.py`. **Expected collected delta:** +4. **Acceptance:** `pyt tests/test_dev_sh_prereqs.py -q` 4 passed; `bash -n dev.sh`; on a box with a compiler, `HC_DEV_STOP_AFTER_DEPS=1 ./dev.sh` still installs everything (pasted). **Rollback:** revert.

### 2.11 EXPORT-COLLECTED-TZ — which day the doctor summary prints for a lab result (owner display ruling)

**Source:** queue status 2026-10-17 (found while planning EXPORT-TODAY-TZ, lane D §3); queue row EXPORT-COLLECTED-TZ. **Owner answer 2026-10-18: EXPORT-COLLECTED-TZ-DISPLAY = (c) "As recorded + pin"** (owner-decisions row EXPORT-COLLECTED-TZ-DISPLAY). Only the (c) task list below is built. The options table stays as the record of what was asked.

**Fact (`046d12c`; `modules/export.py` is unchanged on `b8a47c7`; corrects the queue row):**
- **Doctor summary.** It prints a collection date in one place: `_format_abnormal_values` (`src/backend/modules/export.py:199-208`), `date_str = obs.get("collected_at", "").strftime("%Y-%m-%d")` at `:203`. That renders the "Values Outside Reference Range" section (`:145-151`). Text, HTML and PDF all render from the stored, strict-redacted dict (E-1, `redact_summary_data` `:222`). The format is owner O-2 ("ISO-8601 dates", 2026-10-08).
- **`:302` is not the doctor summary.** It is `export_csv` (`:272`), behind `GET /export/csv` (`api/export.py:912-945`). That is the patient's own full-fidelity export: D3 exempt, and pinned byte for byte by HC-EXPR-002 (`tests/test_export_redaction.py:260`). Out of scope.
- **The visit-prep packet also goes to a clinician** (`compose_visit_prep_packet` `:551`; callers `api/export.py:796`, `api/pinboards.py:500`). It prints three dates of the same kind:
  - the observation line, `collected.date().isoformat()` (`:622-623`);
  - the visit-mention lines, `f"- {date_str}: ..."` (`:643-645`). Their `doc_date` is `Document.collection_date.date().isoformat()`, computed in `_fetch_visit_mention_dicts` (`api/export.py:274-275`);
  - the "Source Documents" lines, `collected.date().isoformat()` of `Document.collection_date` (`:676-677`).
- **`Document.collection_date`** (naive `DateTime`, `models/document.py:61`) is `min(valid_dates)` of the document's extracted observation dates (`api/documents.py:665`, `:807`). So it is the same recorded-date-at-midnight value. The planner pins all four sites (`:203`, `:622`, `:643-645`, `:676-677`); see the note after the owner question.
- **What the stored value means, measured.** `Observation.collected_at` is naive `DateTime` (`models/observation.py:75-77`). Every ingest path stores the calendar date printed on the source as **midnight with no zone**:
  - PDF extraction keeps only `YYYY-MM-DD` (`_normalize_date_str`, `modules/extract.py:664-703`, which returns `parsed.strftime("%Y-%m-%d")` at `:700`; `_extract_dates` `:705`). `_parse_date_string` then parses it (`api/documents.py:138-184`, `:657`).
  - CSV and FHIR import reduce even an offset `effectiveDateTime` to its own date (`modules/import_structured.py:77-97`) before `api/documents.py:759`.
  - The only other writer is `POST /observations/{id}/verify` (`NaiveUtcDatetime`, `api/observations.py:153`, `:451-456`; UTC-SWEEP). It stores an offset-aware `collected_at` as a UTC instant. It stores a **naive** value with a time of day unchanged (`core/time.py:39`), which the app reads as UTC by the same convention as everywhere else. The frontend type allows the field (`src/frontend/src/services/types.ts:181`), but no caller sends it today. For such values the owner already accepted the UTC calendar day for panels and interpretations (UTC-DAY, `owner-decisions:161`).
- **So today both documents print the date as recorded** for every ingested result. The app's own screens show the same date: `new Date(<naive ISO>).toLocaleDateString()` reads a naive string as local wall-clock (`src/frontend/src/components/lab-interpreter/PanelInterpretationDashboard.tsx:169`, `src/frontend/src/pages/MedicationDetail.tsx:383`).
- **EXPORT-TODAY-TZ composes.** Its Design 2 rev (lane D §3, owner EXPORT-TODAY-TZ-DESIGN = B) stores the generation-day local date and leaves `:203`, `:302`, `:622`, `:643-645` and `:676-677` alone. It edits `modules/export.py` and `tests/test_export_redaction.py`, so this item lands after it.

**Options as asked (owner EXPORT-COLLECTED-TZ-DISPLAY; answered (c)):**

| Option | What the doctor sees | Change |
|---|---|---|
| (a) profile's local time zone | instants: the patient's local day; recorded dates: unchanged, but only through a "naive midnight = date-only" rule | `to_local` on non-midnight values at all four sites, with the zone passed from the routes. A plain `to_local` on every value moves every recorded date one day earlier west of UTC (`2026-01-15 00:00` → `2026-01-14` in `America/Los_Angeles`). The midnight rule still misreads a real instant at exactly `00:00:00` UTC. A naive non-midnight verify value is read as UTC (app convention). A "date-only" column would remove the guess (schema change) |
| (b) UTC, labelled | `2026-01-15 UTC` | one suffix at all four sites; it must survive strict redaction. It calls the lab's printed date "UTC", which it is not |
| **(c) chosen: date as recorded (today's output)** | `2026-01-15`, the same as the report and the app's own screens | no product edit; pin tests only. Revisit when wearables (#94) bring real timestamps into exports |

**Owner question as asked (2026-10-18, through L0 AskUserQuestion; recorded verbatim in owner-decisions):** "EXPORT-COLLECTED-TZ-DISPLAY: which date should the doctor summary and the visit-prep packet print next to each lab result? Today every imported lab date (PDF, CSV, FHIR) is the date printed on the report, stored without a time zone, and printed unchanged. That matches the app's own screens." **Planner's reasoning, not the owner's scope:** under (c) no site changes. The planner also pins the packet's visit-mention (`:643-645`) and source-document (`:676-677`) dates, because `Document.collection_date` holds the same recorded date. The owner was not asked about them separately.

**Task 0:** EXPORT-TODAY-TZ is merged. Measure the collected count. Confirm the four sites still format as quoted: `grep -n 'strftime("%Y-%m-%d")\|date().isoformat()\|doc_date' src/backend/modules/export.py src/backend/api/export.py`.

**Tasks (option (c)):**
1. **HC-EXPCTZ-001** (`tests/test_export_redaction.py`, the HTTP doctor-summary fixture `_export_client`, `:133-152`). Use profile zone `America/Los_Angeles` (the `profile_timezone_name` stub EXPORT-TODAY-TZ adds there) and an abnormal observation stored `datetime(2026, 1, 15)`. The text download contains `- 2026-01-15` and not `2026-01-14`. This is a pin, not RED. The mutant `to_local(...)` at `:203` fails it.
2. **HC-EXPCTZ-002** (`tests/test_visit_prep_packet.py`). Call `compose_visit_prep_packet` directly with a verified observation `collected_at=datetime(2026, 1, 15)`, a verified visit mention `doc_date="2026-01-15"`, and a selected document `collection_date=datetime(2026, 1, 15)`. The markdown has `— 2026-01-15` (observation), `- 2026-01-15:` (mention) and `(2026-01-15)` (source document). This is a pin. A `to_local` mutant at `:622` or `:677` fails it. Not pinned: the `doc_date` string is built in `_fetch_visit_mention_dicts` (`api/export.py:274-275`), and this test passes it in already formatted, so a change there would go unnoticed.
3. **No product edit.**

**Files:** `src/backend/tests/test_export_redaction.py`, `src/backend/tests/test_visit_prep_packet.py`, slots. **Expected collected delta:** +2. The existing substring pins (`tests/test_visit_prep_packet.py:183`, `tests/test_export_redaction.py:327`) are unchanged.

**Acceptance:** `pyt tests/test_export_redaction.py tests/test_visit_prep_packet.py tests/test_export_api.py -q`: 0 failed. HC-EXPR-002 is still green. `git diff origin/main -- src/backend/modules src/backend/api` is empty. **Rollback:** revert; no data.

**Order:** after EXPORT-TODAY-TZ merges (both edit `tests/test_export_redaction.py` and `tests/test_visit_prep_packet.py`). Never beside E-1b (`tests/test_export_redaction.py`).

### 2.12 E-1c — spaced label shapes and E-1b residuals strict still misses (ask-first `modules/redaction.py`; owner E1C-SCOPE)

**Source:** PR #179 (E-1b): the L0 ruling ("Follow-up row E-1c: the same shapes with spaces (`MRN (hospital): A12345`, `Patient #: 98765`, `MRN - A12345`)"), the PR body's "Known gaps", and the round-1 security review finding 2 (residual shapes; "L0 should open a follow-up row (E-1c, ask-first, owner gate) and add the shapes to the PRIV-04 gap column"). Planned 2026-10-19 on `origin/main` @ `a9978e8`.

**E1C-SCOPE answered (b), 2026-10-19, recorded on `main` at `docs/capstone-report/owner-decisions-2026-09-27.md:272` (PR #190, merged `126dfe3`).** That answer licenses the `modules/redaction.py` edit at scope (b): groups S and U, not G. The merge still waits for **E1C-DIFF** (owner yes on the exact diff), as E-1a and E-1b did.

**Measured on `a9978e8`** (`RedactionEngine("strict").redact(s).text`, scratchpad probe, not committed):

| Group | Input | Strict output today |
|---|---|---|
| S: spaced, named by L0 | `MRN (hospital): A12345`, `MRN (Hospital A): X12345`, `Patient #: 98765`, `MRN - A12345` | unchanged |
| S: spaced, same family | `MRN = A12345`, `MRN – A12345` (en dash), `MRN #: A12345`, `MRN No.: A12345`, `MRN no. A12345`, `Patient No.: 98765`, `Patient ID: 98765`, `Patient ID - 98765`, `Name (legal): Jane Doe`, `Patient (legal name): Jane Doe` | unchanged |
| S: control (already caught) | `MRN: A12345`, `MRN #A12345`, `MRN:A12345`, `Medical Record Number: A12345` → `[MRN-REDACTED]`; `Patient: Jane Doe` → `[NAME-REDACTED]`; `DOB - 01/02/1980` → `DOB - [DATE-REDACTED]` | caught (only the date part for the DOB line) |
| U: underscore residuals that keep a separator | `mrn_(hospital_a):_x12345` (multi-word qualifier), `patient_#_:_98765` (`_` before the colon), `mrn_–_a12345` (en dash), `mrn_=_=_a12345` (doubled separator), `mrn:_(hospital)_a12345` (qualifier after the colon), `mrn_-a12345`, `mrn-a12345` (dash glued to a specific label) | unchanged |
| G: underscore, no colon after a bare label | `patient_id_-_98765`, `name_=_jane`, `patient_#_98765`, `patient_no._98765` | unchanged (bare labels need a colon by design, E-1a) |

**Why:** the spaced rules are older and narrower than the underscore rule. `mrn` (`src/backend/modules/redaction.py:118-126`) allows only `\s*[:#]?\s*` between the label and the value, so a qualifier, `-`, `=`, `no.` or `#:` ends it. `name_context` (`:85-93`) needs a capitalised multi-word name after `patient`/`name`, so digits and qualifiers fail. The underscore rule `underscore_labelled_id` (`:147-158`) was widened by E-1a and E-1b, but only for `_`-joined text. Where spaced text goes: free-text fields of strict exports, for example the visit-prep packet's `reason_for_visit` (`modules/export.py:694`, strict) and the opt-in external runner (D12, strict on every call).

**Owner gate E1C-SCOPE** (exact wording as asked; **answered (b)**, `docs/capstone-report/owner-decisions-2026-09-27.md:272`):

> "E1C-SCOPE: strict redaction (doctor summary, visit-prep and pinboard packets, cloud runner) still lets these identifier shapes through, measured on main `a9978e8`: spaced labels such as `MRN (hospital): A12345`, `Patient #: 98765`, `MRN - A12345`, `MRN = A12345`, `Patient ID: 98765`; and underscore forms the E-1b review listed, such as `mrn_(hospital_a):_x12345`, `patient_#_:_98765`, `mrn_–_a12345`, `mrn-a12345`. Fixing them means editing ask-first modules/redaction.py (strict level only). Which scope?
> **(a)** Spaced shapes only (group S): the spaced versions of what strict already catches in underscore form.
> **(b)** (a) plus the underscore residuals that still have a separator or a specific label (group U). Recommended: it closes every shape the reviews named except the no-colon bare-label group, at the same over-redaction level as E-1b.
> **(c)** (b) plus group G (`patient_id_-_98765`, `name_=_jane`, `patient_#_98765`): accepts over-redaction of analyte-like tokens such as `patient_count_3`, which E-1a deliberately keeps.
> **(d)** No code now: record every shape in the PRIV-04 gap column and close E-1c."

Recommended **(b)**. Merge needs **E1C-DIFF** after the draft PR exists: "E1C-DIFF: here is the exact `modules/redaction.py` diff for E-1c under scope (x), with its mutant table and timing. Merge?"

**Design (under (a)/(b); strict only; no other level; the implementer drafts the exact pattern for E1C-DIFF):**
1. **Group S:** widen the spaced side the way E-1a/E-1b widened the underscore side, either by widening `mrn` and adding one strict-only `spaced_labelled_id` rule, or one new rule alone. Shape: a label (`mrn`, `medical record number`, `patient`, `patient id`, `patient name`, `name`, `dob`, `date of birth`), then an optional one-parenthesised-qualifier `\s*\([^()\n]{1,40}\)`, then for bare `patient`/`name` an optional `#` or `no.` before a required `:`, then an optional single separator from `-`, `–`, `—`, `=`, `;`, then the value. The value is an identifier token for `mrn`/`id`/`#`/`no.` labels, or a capitalised name for `name`/`patient name`. Every piece must stay **disjoint** from its neighbouring whitespace runs (the rev-2 lesson in §2.8: no two adjacent `\s*` around an optional group), and the qualifier is bounded so it cannot scan a whole line.
2. **Group U (only under (b) or (c)):** extend `underscore_labelled_id`: a qualifier may hold `_`-joined words inside the parentheses (bounded, no nested `(`), `_*` may precede the bare-label colon only when it is not adjacent to another `_*`, the separator set gains `–` and `—`, one repeated separator is allowed, a qualifier may follow the colon, and a specific label may take `-` with no `_`. Everything E-1a/E-1b matches still matches with the same output.
3. **Accepted over-redaction (strict only, listed in the PR body):** for example `MRN (status): OK`, `Patient #: 3` become redacted. Same class as E-1b's `mrn_(status):_ok`.

**Test-first** (`src/backend/tests/test_redaction.py`; "RED" = fails on `a9978e8`):

| Id | Assertion | RED today? |
|---|---|---|
| HC-REDACT-013 (parametrised, group S) | each group-S input → the identifying value (`A12345`, `X12345`, `98765`, `Jane Doe`) is absent from strict output | yes, every row |
| HC-REDACT-014 (parametrised, near-shapes) | spaced analyte or prose lines stay unchanged with 0 redactions: `MRNA - level 2`, `Patient education: diet`, `Specimen (serum): clear`, `Glucose (fasting): 96`, `T4 (free): 1.2`, `LDL - calculated` | no (guards; each must fail against a named mutant in Task 3, as in E-1a) |
| HC-REDACT-001 (+7 rows, only under (b)/(c)) | the group-U inputs → `[ID-REDACTED]` by the existing assertions | yes ×7 |
| HC-REDACT-001 (+4 rows, only under (c)) | the group-G inputs | yes ×4 |
| HC-REDACT-015 (timing) | strict on `"MRN" + " (" * 20000`, `"Patient" + " #" * 20000 + "!"`, `"MRN" + " -" * 20000 + "!"`, `"MRN" + " " * 50000 + ":"` → under 1.0 s each and text unchanged | measure in Task 0; backtracking guard for the widened rule |
| HC-REDACT-016 | standard and minimal output for every group-S input equals today's output | no (pins strict-only scope; must fail against the mutant "rule at standard") |
| HC-PKT-023 | `POST /export/visit-prep` through `route_client` with `reason_for_visit="MRN (hospital): B67890"` → the stored packet markdown and the HTML download contain no `B67890` | yes |

`test_export_redaction.py`'s module docstring (`:8-11`) "Not covered by strict" list: name what remains after the chosen scope (for example group G under (b), gap 11). HC-PKT-023 lives in `tests/test_visit_prep_packet.py` (a visit-prep route test, so it takes that file's own id family, not HC-EXPR); the docstring edit is the only change to `tests/test_export_redaction.py`.

**Tasks:** 0 start count, RED run (`-rfE`), HC-REDACT-015 timing on `main`; 1 RED tests; 2 GREEN, the rule edit (draft PR); 3 mutants (drop each new branch, drop the qualifier bound, drop the disjointness): each fails a named test, output in the PR body; 4 docstring; 5 PR stays **draft** until E1C-DIFF.

**Files:** `src/backend/modules/redaction.py` (ask-first, **edited only after E1C-SCOPE**), `src/backend/tests/test_redaction.py`, `src/backend/tests/test_visit_prep_packet.py` (HC-PKT-023), `src/backend/tests/test_export_redaction.py` (docstring only), slots.
**Expected collected delta:** (a) 14 + 6 + 4 + 1 + 1 = **+26**; (b) **+33**; (c) **+37**; (d) 0 (no PR).
**Est:** 4 h after E1C-SCOPE (+ security review).
**Acceptance** (from `src/backend`, `pyt` as §2.8): 1. `pyt tests/test_redaction.py tests/test_export_redaction.py tests/test_visit_prep_packet.py -q -rfE`: 0 failed. 2. E-1a acceptance rows 3-4 (the other strict callers: `fhir_export`, `visit_prep`, `rl_*`, `external_runner`, `agent/test_s4_phi_gate`, `agent/test_s6_evals`): same pass/fail as Task 0. 3. Full suite per RUNBOOK §6.
**Doc claim (PR body, PRIV-04 gap column via L0):** name the shapes now matched and the ones that remain. Never "all PHI".
**Order:** ready to build at scope (b); merge needs E1C-DIFF. Never beside another `redaction.py` / `test_redaction.py` row, never beside EXPORT-TZ-PINS or C-GC1 (`tests/test_visit_prep_packet.py`), and LEGACY-CITE-PROMPT must keep an empty `redaction.py` diff (rebase it after E-1c if E-1c merges first). RSI1-DONATE calls the engine only. **Rollback:** revert; no data.

### 2.13 REDACT-WS-REDOS — strict `dob` and `name_context` are quadratic on long whitespace runs (ask-first `modules/redaction.py`)

**Source:** PR #195 (E-1c) body, "Follow-ups": "`dob` (strict) and `name_context` are quadratic on long whitespace runs: 2.8 s and 2.6 s at 20k spaces, and `"patient name" + 50k spaces` takes 15 s, all in `name_context`. Needs its own owner gate." Owner E1C-DIFF (`docs/capstone-report/owner-decisions-2026-09-27.md:273`): "REDACT-WS-REDOS … become follow-up rows." Owner REDACT-WS-REDOS (`:276`): **"Plan the row now"**, "Licenses planning only; the redaction.py diff still needs a later REDACT-WS-REDOS-DIFF yes." Planned 2026-10-19 on `origin/main` @ `d42dba9`.

**Measured on `d42dba9`** (`RedactionEngine(level).redact(s)`, scratch script through `scripts/pyslot.sh`, not committed; every output equals its input):

| Input | strict | standard | rule (strict, one `search`) |
|---|---|---|---|
| `"dob" + " " * 20000 + "x"` | 2.54 s | 0.00 s | `dob` 2.37 s |
| `"date of birth" + " " * 20000 + "x"` | 2.62 s | 0.00 s | `dob` |
| `"dob" + "\t" * 20000 + "x"` | 2.61 s | 0.00 s | `dob` |
| `"dob" + " " * 40000 + "x"` | 9.73 s | 0.00 s | `dob` (2× input → 3.8× time: quadratic) |
| `"patient" + " " * 20000 + "!"` | 2.59 s | 2.19 s | `name_context` 2.18 s |
| `"name" + " " * 20000 + "!"` | 2.23 s | 2.38 s | `name_context` |
| `"patient" + " " * 40000 + "!"` | 9.01 s | 9.00 s | `name_context` |
| `"patient name" + " " * 50000` | 14.04 s | 14.52 s | `name_context` 14.48 s |
| `"1" + " " * 20000 + "x"` (`address`, control) | 0.00 s | 0.00 s | — |

`name_context` runs at strict **and** standard (`src/backend/modules/redaction.py:92`), so standard-level callers are slow too (for example the default of `modules/agent/guardrails/redaction_gate.py:38`). `dob` is strict only (`:101`).

**Why:** both patterns put two `\s*` around an optional colon: `\s*:?\s*` (`name_context` `:88`, `dob` `:97`). With no colon, a run of n spaces can be split between the two `\s*` in n+1 ways, and each split is tried when the next token fails: O(n²) per label. In `"patient name" + spaces` the label `name` itself starts a second attempt. This is the shape E-1c removed from `mrn` (its comment at `:121-126`: "the old `\s*[:#]?\s*` could, 2.2 s at 20k spaces").

**Design (strict and standard keep byte-identical output; the implementer drafts the exact diff for REDACT-WS-REDOS-DIFF):** in both patterns replace `\s*:?\s*` with `\s*(?::\s*)?`. That matches the same strings (spaces, an optional colon, spaces), but a space run can only be split one way when there is no colon. Nothing else in either rule changes, including the `(?i)` flag on the name group. **Measured as a scratch check on `d42dba9`** (not committed): the rewritten patterns take 0.001-0.003 s on the inputs above (`"patient name" + 50k spaces`: 0.003 s), and a 48,712-input differential (labels × separators × values × tails, plus 20,000 seeded random strings) gives 0 differences against today's two patterns with `.sub`.

**Owner gates.**
- **REDACT-WS-REDOS-BUILD** (execution; open). REDACT-WS-REDOS licenses planning only, and RUNBOOK §4 step 4 needs a signed gate naming the exact `redaction.py` edit before a build. Exact wording to ask: "REDACT-WS-REDOS-BUILD: may an agent edit ask-first `modules/redaction.py` to replace `\s*:?\s*` with `\s*(?::\s*)?` in the `name_context` and `dob` patterns only, on a draft PR? Output must stay byte-identical at every level (a differential test proves it), and inputs that take 2.2-14.5 s today must run under 1 s. (a) Yes, build it as planned (Recommended). (b) No, leave both rules."
- **REDACT-WS-REDOS-DIFF** (merge only; open; asked after the draft PR exists): "REDACT-WS-REDOS-DIFF: here is the exact `modules/redaction.py` diff (two patterns), with the timing and differential output and the mutant table. Merge?"

**Test-first** (`src/backend/tests/test_redaction.py`, next to HC-REDACT-015, same style: `time.perf_counter()`, under 1.0 s, text unchanged):

| Id | Assertion | RED today? |
|---|---|---|
| HC-REDACT-017 ×6 (parametrised) | at strict: `"dob" + " " * 50000 + "x"`, `"date of birth" + " " * 50000 + "x"`, `"dob" + "\t" * 50000 + "x"`, `"patient" + " " * 50000 + "!"`, `"name" + " " * 50000 + "!"`, `"patient name" + " " * 50000` → each under 1.0 s and unchanged; the three `name_context` inputs are also run at standard inside the same case | yes ×6 (measured 9-14.5 s at 40k-50k; 50k is used so the bound fails clearly even on a faster CI runner) |
| HC-REDACT-018 | differential, as HC-REDACT-011: inline copies of today's `name_context` and `dob` rules in a `RedactionEngine(policy_level=lvl, rules=[...])`; a fixed corpus (`Patient: Jane Doe`, `Name : Jane Doe`, `patient\tJane Doe`, `Mr. Smith Jones`, `DOB: 01/02/1980`, `DOB 1-2-80`, `date of birth : 12/31/1999`, `birthdate:01/02/1980`, `Patient:\nJane Doe`, `DOB :: 01/02/1980`) plus 2000 seeded random strings over `patient name dob : \t\n Jane Doe 01/02/1980 x` → the same `text` and the same metadata spans at strict and at standard | no (pin; the mutant `\s*(?::\s*)?` → `(?:\s*:)?` (drops the leading space run when there is no colon) fails it) |

**Mutants (Task 3, output in the PR body):** restore `\s*:?\s*` in either rule → HC-REDACT-017 fails for that rule; drop the colon branch (`\s*`) → HC-REDACT-018 fails on `Patient: Jane Doe`; apply the change to `name_context` only → the three `dob` cases of HC-REDACT-017 fail.

**Files:** `src/backend/modules/redaction.py` (ask-first, **edited only after REDACT-WS-REDOS-BUILD**: `:88` and `:97`), `src/backend/tests/test_redaction.py`, slots.
**Expected collected delta:** +7 (6 + 1). **Est:** 1.5 h after REDACT-WS-REDOS-BUILD (+ security review).
**Acceptance** (`pyt` as §2.8): 1. `pyt tests/test_redaction.py tests/test_export_redaction.py -q -rfE`: 0 failed. 2. The E-1a acceptance rows 3-4 suites (the other strict callers) and `tests/test_external_runner_hardening.py` (standard level): same pass/fail as Task 0. 3. Full suite per RUNBOOK §6.
**Order:** blocked on REDACT-WS-REDOS-BUILD; PR stays draft until REDACT-WS-REDOS-DIFF. Never beside another `redaction.py` / `test_redaction.py` row (none open on `d42dba9`). LEGACY-CITE-PROMPT (#185) and RSI1-DONATE keep an empty `redaction.py` diff. **Rollback:** revert; no data.

### 2.14 GATE-12 — a conftest guard so no test can open the real master DB

**Source:** owner GATE-12 (`docs/capstone-report/owner-decisions-2026-09-27.md:299`): **"Yes, add the row"**, "A planner designs a conftest-level autouse guard so cross-profile tests cannot write into `src/backend/data/asclexis.db`." Lane E Q-E3 (§6 `:436`); contracts §e "Needs the owner" item 5 (`contracts.md:188`); contract I-12 (`contracts.md:32`). Planned 2026-10-19 on `d42dba9`.

**Facts (`d42dba9`):**
1. The master engine is built at import from `settings.database_url` (`src/backend/core/database.py:44-56`). In local mode that is `sqlite+aiosqlite:///data/asclexis.db`, a path relative to the working directory (`core/config.py:170-177`, `:191-195`), so a run from `src/backend` resolves it to `src/backend/data/asclexis.db`.
2. `audit_denial` opens its own session from `database.async_session_maker` when it is given none (`core/denial_audit.py:72-79`) and swallows any error (`:80-85`). `core/external_runner.py:129-131`, `modules/backup_scheduler.py:103-107` and `modules/agent/tools/lookup_reference.py:56-60` open the master maker the same way, and `get_db` uses it (`core/database.py:104-113`).
3. `tests/conftest.py` sets env vars and a writable temp dir only; it has no fixtures.

**Measured on `d42dba9`** (scratch copy, with a pytest plugin that records every connection the real `core.database.engine` makes and every write statement it runs, not committed):
- **Control:** a test that calls `audit_denial("caller-x", "document")` without the I-12 patch, run with an empty `data/` directory present (as on a developer machine), created `data/asclexis.db` (0 bytes, no tables) and issued `INSERT INTO audit_logs …`. On that empty file the insert fails with "no such table" and `audit_denial` swallows the error; on an initialised developer DB it would write the row. The test passed either way.
- **Full suite** (1978 collected; 4 failures that need a git checkout, because the scratch copy is not one) with `data/` present: **0 tests** connected to the real master engine, and `data/asclexis.db` was not created. So nothing writes there today, and a guard that fails such a test breaks nothing.

**Design (test infrastructure only; no product file):**
1. In `tests/conftest.py`, after the env lines: a session-scoped autouse fixture `_gate12_guard` imports `core.database` and registers a SQLAlchemy `do_connect` listener on `database.engine.sync_engine`. The listener appends the running test's node id to a module list `_GATE12_HITS` and raises `RuntimeError("GATE-12: a test opened the real master DB (data/asclexis.db). Patch core.database.async_session_maker to a test maker (contracts I-12).")`. It raises before the DBAPI connects, so no file is created and nothing is written. The fixture removes the listener at session end.
2. A function-scoped autouse fixture records `len(_GATE12_HITS)` before the test and calls `_gate12_check(start, nodeid)` after it, which calls `pytest.fail(...)` with the message above if the list grew. This catches the swallowed case in fact 2: `audit_denial` logs and returns, but the test still fails.
3. Tests that patch `core.database.async_session_maker` (I-12) use their own engine and never reach the listener. Tests that build their own engines are not affected.

**Owner gates:** GATE-12 answered (above). `tests/conftest.py` is not ask-first and no lane owns it; this row owns it for its PR. No other gate.

**Test-first** (new file `src/backend/tests/test_gate12_master_db_guard.py`):

| Id | Assertion | RED today? |
|---|---|---|
| HC-GATE12-001 | `monkeypatch.chdir(tmp_path)`, `(tmp_path / "data").mkdir()`, clear `core.denial_audit._state`, `await audit_denial("caller-x", "document")` → `tmp_path / "data" / "asclexis.db"` does not exist, and `_GATE12_HITS` gained this test's node id. The test then removes its own hit so its teardown check passes | yes (the control above: the file is created and the insert is issued) |
| HC-GATE12-002 | `_gate12_check(start, "x")` after appending a fake hit raises `pytest.fail.Exception` whose message names GATE-12 and I-12; with no new hit it returns | yes (`_gate12_check` does not exist) |
| HC-GATE12-003 | an I-12-style test (patch `core.database.async_session_maker` to an in-memory master maker with the audit table) → `audit_denial` writes exactly one `denial.cross_profile` row there and `_GATE12_HITS` does not grow | no (pin: the guard must not block the sanctioned pattern) |

**Files:** `src/backend/tests/conftest.py`, `src/backend/tests/test_gate12_master_db_guard.py` (new), slots. **Re-run, not edited:** `tests/test_denial_audit.py`, `tests/test_export_redaction.py` (HC-EXPR-003, an I-12 test), `tests/test_backup_api.py`, `tests/test_external_runner_hardening.py`.
**Expected collected delta:** +3. **Est:** 1.5 h.
**Acceptance:** `pyt tests/test_gate12_master_db_guard.py tests/test_denial_audit.py tests/test_export_redaction.py -q -rfE`: 0 failed; the full suite per RUNBOOK §6 with an empty `src/backend/data/` directory present, then `test ! -e src/backend/data/asclexis.db` (paste both). **Rollback:** revert.
**Order:** ready now. Never beside another PR on `tests/conftest.py` (none open on `d42dba9`). **Recurring-failures #12 recheck:** this adds a gate. After it merges, L0 runs the full suite on `origin/main` and on every open PR built before it; an open PR with a test that reaches the real master engine now fails, and is rebased and fixed before the rest of the group merges.

### 2.15 Q-COV-GATE — CI fails when backend coverage drops below 74%

**Source:** owner Q-COV (`docs/capstone-report/owner-decisions-2026-09-27.md:300`): **"74% floor (current)"**, "CI fails if backend coverage TOTAL drops below 74%. Becomes row Q-COV-GATE." The W-11a plan left it open: "Q-COV. Coverage stays report-only. A threshold, if any, is set after the first measured TOTAL" (`docs/plans/2026-09-27-W11a-test-and-gate-hardening.md:1953`).

**Facts (`d42dba9`):**
1. CI's `backend-tests` job runs `bash scripts/run-backend-tests.sh -q --cov=api --cov=core --cov=models --cov=modules --cov=monitoring --cov=security --cov=scripts --cov-report=term --cov-report=xml:coverage.xml` (`.github/workflows/ci.yml:61-62`), then fails only if `coverage.xml` is missing (`:64-65`) and uploads it (`:67-72`). There is no threshold. `scripts/run-backend-tests.sh` ends with `python3 -m pytest "$@"` under `set -euo pipefail`, so pytest's exit code is the step's.
2. `docs/architecture/ci-and-quality-gates.md:48` says `backend-tests` fails on "a missing coverage report (coverage report only, no threshold …)".
3. No coverage config file exists (`src/backend/pyproject.toml` has no `[tool.coverage]`; no `.coveragerc`). `src/backend/requirements.txt:117` pins `pytest-cov>=4.1.0`.

**Measured:**
- CI run 39276536690 (main @ `d42dba9`, 2026-10-19): `TOTAL 17076 4165 76%`, so 75.61% (1 − 4165/17076), 1.61 points over the floor. The owner row's "74% (current)" is the recorded **local** TOTAL (`docs/capstone-report/specs-compliance-matrix.md:155` GATE-07 and `docs/features/TASK_LIST.md:220`: E-3, 2026-10-17, WSL), not CI's. CI is 1.61 points higher.
- Mechanism (scratch copy, `tests/test_time_source.py` with `--cov=core`, TOTAL 26.28%): `--cov-fail-under=99` → the tests pass, pytest prints `FAIL Required test coverage of 99% not reached. Total coverage: 26.28%` and exits 1; `--cov-fail-under=1` → `Required test coverage of 1% reached.`, exit 0.

**Design:** append `--cov-fail-under=74` to the existing `Run backend tests (with coverage report)` command (`ci.yml:62`). pytest-cov checks the same TOTAL the step already prints, after it writes the reports. Rename the step to `Run backend tests (coverage report, 74% floor)`. A separate `coverage report --fail-under` step is not used: without the same `--cov` sources it leaves never-imported files out, so its TOTAL could differ from the printed one. Update `ci-and-quality-gates.md:48`: "… or a missing coverage report, or a coverage TOTAL below 74% (owner Q-COV, 2026-10-19)." Update GATE-07 in `docs/capstone-report/specs-compliance-matrix.md:155`: "no threshold (Q-COV)" becomes "CI fails below 74% TOTAL (Q-COV, 2026-10-19)"; keep the local-TOTAL history. Otherwise it contradicts CI after the merge (recurring-failures #8).

**Owner gates:** Q-COV answered (above). Nothing ask-first.

**Test-first (a CI gate; no pytest id):**

| Check | Expected | RED today? |
|---|---|---|
| Local, in the worktree (informational): the CI command plus `--cov-fail-under=74` (through `scripts/pyslot.sh`) | paste the `Required test coverage of 74% …` line and NN.NN%. The local TOTAL can be lower than CI's, and without the fetched embedding model the 5 environment failures already make pytest exit 1, so the exit code here is not the pass/fail | n/a |
| Break-it, local: the same command with `--cov-fail-under=99` | the suite passes, then `FAIL Required test coverage of 99% not reached`, exit 1 | n/a (proves the step can fail) |
| CI on the PR (**the pass/fail**) | `backend-tests` green, its log shows `Required test coverage of 74% reached` | today the log has no such line |

**Files:** `.github/workflows/ci.yml` (the `backend-tests` test step only), `docs/architecture/ci-and-quality-gates.md` (`:48` row only), `docs/capstone-report/specs-compliance-matrix.md` (GATE-07 row `:155` only). No slots (no test added).
**Expected collected delta:** 0. **Est:** 0.5 h.
**Acceptance:** the three checks above, pasted; `python3 scripts/docs_lint.py`. **Rollback:** revert.
**Order:** ready now. Never beside another `ci.yml`, `ci-and-quality-gates.md` or `specs-compliance-matrix.md` PR (none open on `5750a97`). **Recurring-failures #12 recheck:** this adds a CI gate. After it merges, L0 re-runs CI (or the local command with `--cov-fail-under=74`) on `origin/main` and on every open PR built before it, before merging the rest of the group: a PR that adds a lot of untested code can now fail `backend-tests` although it was green on its own head.

### 2.16 PKT-QUESTIONS-REDACT — the stored packet keeps unredacted question text (privacy; export path)

**Source:** PR #198 (EXPORT-TZ-PINS) body, "Follow-up candidates, outside this PR": "(1) `_packet_store[...]["questions"]` keeps unredacted question text in memory. Nothing serves it today, but any future reader of that field would bypass strict redaction." Planned 2026-10-19 on `d42dba9`.

**Facts (`d42dba9`):**
1. `compose_visit_prep_packet` renders the questions into a section (`src/backend/modules/export.py:673-674`) and redacts every section at strict (`:694-699`), but its return dict also carries `"questions": [{"question": q.question, "category": q.category} …]` straight from the inputs (`:730-733`).
2. Question text carries user text: the care-task question is `f"This follow-up is still open: {task.get('title', '')}. Should it be scheduled?"` (`:513`).
3. Both callers store the whole dict: `api/export.py:821` (`POST /export/visit-prep`) and `api/pinboards.py:514` (pinboard export). No product code reads `packet["questions"]` today: the download route passes `"questions": []` (`api/export.py:896`), and `api/export.py:593-597` reads the doctor-summary dict, not the packet. Only tests read the field: HC-EXPTZ-008/009, merged with #198 (`adb22f0`) into `tests/test_pinboards.py` and `tests/test_visit_prep_packet.py`.
4. C-GC1 (Wave 14) plans to persist export artifacts as `payload_json` (lane C §3, `ExportArtifact` with kind `visit_prep`). If it stores this dict, the unredacted text goes to disk.

**Measured** (scratch test): `ExportModule().compose_visit_prep_packet(profile_id="p1", questions=[QuestionPrompt(question="This follow-up is still open: Call Dr. Jane Smith, MRN: A1234567. Should it be scheduled?", category="follow_up")])` → `markdown` contains neither `Jane` nor `A1234567`; `packet["questions"]` holds the full question with both.

**Owner gates** (the fix edits the export path that CLAUDE.md's "Redaction before anything leaves" invariant covers; `modules/redaction.py` is **called only**):
- **PKT-Q-SCOPE** (execution; open). Exact wording: "PKT-Q-SCOPE: the visit-prep and pinboard packets redact every section at strict, but the stored packet dict also keeps a `questions` list with the raw question text (care-task titles, measured with a name and an MRN). Nothing reads it today; C-GC1 plans to persist packets. Which fix? (a) Redact each stored question with the same strict engine as the sections, keep the field (Recommended: one line in `modules/export.py`; #198's tests keep working because their task titles hold no PHI). (b) Drop the `questions` field from the stored packet (#198's two tests must then read the markdown instead). (c) Leave it and record it as a C-GC1 constraint."
- **PKT-Q-DIFF** (merge only; open; asked after the draft PR exists): "PKT-Q-DIFF: here is the exact `modules/export.py` diff for PKT-QUESTIONS-REDACT under option (x), with RED/GREEN output. Merge?"

**Design (under (a)):** in `compose_visit_prep_packet`, build the `questions` list with `engine.redact(q.question).text` using the strict `engine` already created at `:694`. `redaction_count` does not change: the same text is already counted once in the questions section.

**Test-first** (`src/backend/tests/test_visit_prep_packet.py`):

| Id | Assertion | RED today? |
|---|---|---|
| HC-PKT-024 | through `route_client` (as HC-PKT-023): an open care task titled `Call Dr. Jane Smith, MRN: A1234567`, `POST /export/visit-prep` `{"confirm": true, "include_tasks": true, "include_questions": true}` → 200; `api.export._packet_store[packet_id]["questions"]` is non-empty (so the check is not vacuous) and no entry contains `Jane`, `Smith` or `A1234567` | yes (measured at module level: the field keeps both) |
| HC-PKT-025 | the same through the pinboard export (`POST /pinboards/{id}/export`, the task pinned as `item_type="question"`) | yes (same function, `api/pinboards.py:514`) |

Under (b), both tests assert `"questions" not in` the stored packet instead, and #198's HC-EXPTZ-008/009 move to the markdown.

**Files:** `src/backend/modules/export.py` (`:730-733` only), `src/backend/tests/test_visit_prep_packet.py`, `src/backend/tests/test_pinboards.py` (HC-PKT-025; under (b) also #198's HC-EXPTZ-008), slots. **Re-run, not edited:** `tests/test_export_redaction.py`, `tests/test_export_questions.py`, `tests/test_export_api.py`, `tests/test_audit_order.py`.
**Expected collected delta:** +2. **Est:** 1 h after PKT-Q-SCOPE.
**Acceptance:** `pyt tests/test_visit_prep_packet.py tests/test_pinboards.py tests/test_export_redaction.py tests/test_export_questions.py -q -rfE`: 0 failed; `git diff origin/main -- src/backend/modules/redaction.py` empty; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** blocked on PKT-Q-SCOPE; PR stays draft until PKT-Q-DIFF. EXPORT-TZ-PINS is merged (#198), so its HC-EXPTZ-008/009 are re-run, and under (b) edited. Never beside C-GC1 (`tests/test_visit_prep_packet.py`, `tests/test_pinboards.py`); land it before C-GC1, or C-GC1 must not persist the field.

### Follow-ups found 2026-10-20 (planned 2026-10-20 on `origin/main` @ `b2b3f4e`)

Six rows: two harness rows (WAVE-DEP-DONE, PYSLOT-MODE), two test-only rows from the reviews of #206 and #213 (GATE12-MINORS, PKT-Q-MINORS), and the owner's E1C-DIFF follow-ups split in two: a test-only pin row (REDACT-NAME-PINS, no gate) and the ask-first fix (REDACT-NAME-GAPS, gated). Every "measured" fact ran as a scratch test or script in the planning worktree, removed afterwards (`git status --short` empty). `pyt` = `bash "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest`, run from `src/backend` (absolute path: there is no `scripts/` under `src/backend`; see §2.18).

### 2.17 WAVE-DEP-DONE — build-wave counts a dependency as done when any PR for it merged

**Source:** queue bullet HARNESS (build-wave): "build-wave misread C-P6 as done because Task 1 #113 merged, and picked C-P7." The other half of that bullet (build-item Task 0 installs the embedding bundle) and the HARNESS stale-queue bullet are fixed by #218 (`.claude/workflows/build-item.js` only, merged as `ed38769` while this plan was open) and are not planned here.

**Facts (`b2b3f4e`, `.claude/workflows/build-wave.js`):**
1. The Select prompt's rule 2 (`:73`) reads "Every depends_on PR/item is merged on origin/main (git merge-base --is-ancestor, or merged_recent)". For a queue ID, "merged" is read off `merged_recent`, the titles of recently merged PRs (scan step 4, `:57`). `#113` "C-P6 Task 1 orphan-audit tool" merged on 2026-10-16, so C-P6 read as merged although its row is not done (C-P6 Tasks 2-5 wait on P6-ORPHAN, queue "Status 2026-10-16 (second batch)").
2. The scan already copies each row's `status` (`SCAN_SCHEMA`, `:24-27`), so the rule can use the row's own status. Nothing after `sel` re-checks a dependency: the greedy pick (`:85-96`) checks files only.
3. A `depends_on` cell mixes real dependencies with file rules ("never beside G-C5") and task-scoped ones ("reset-tuple append only after C-P7"). Only the part before the first `never` is a dependency list.

**Design (harness only, two edits in `build-wave.js`):**
1. Rule 2 text: "A depends_on that names a queue ID is met only when that row's own status starts with done. A merged PR for one task of an item (a title such as 'C-P6 Task 1') does not meet it. A depends_on that names a PR number or a commit is met when it is on origin/main. A dependency scoped to one task ('X only after Y') blocks that task only; say so in why."
2. A deterministic cross-check after `sel`: a pure function `depWarnings(rows, ids)` at the top of the file. For each picked id, it takes the row's `depends_on` up to the first `never` (case-insensitive) and finds every other row id that appears in it as a whole token (`(^|[^A-Za-z0-9-])<ID>(?![A-Za-z0-9-])`). It returns `"<id>: depends on <dep>, row status '<first 60 chars>'"` for each such dep whose status does not start with `done` (after stripping `*` and spaces). Items with a warning move from `picked` to `deferred`, **unless** L0 named them in `args.ids` (an explicit L0 choice; the warning is still logged). The return value gains `dep_warnings`.

**Test-first (a harness script; no pytest id):**

| Check | Expected | RED today? |
|---|---|---|
| `node --check` cannot parse a workflow body (top-level `await`, `return`), so: `node -e 'const s=require("fs").readFileSync(".claude/workflows/build-wave.js","utf8").replace(/^export const meta/m,"const meta"); new (Object.getPrototypeOf(async function(){}).constructor)("args","agent","phase","log","parallel","workflow",s)'` | exits 0 (the body parses) | n/a |
| Fixture check: `sed -n '/^function depWarnings/,/^}/p' .claude/workflows/build-wave.js > /tmp/claude-1000/depw.js`, then a node one-liner that loads it and asserts: rows C-P6 `{status: "blocked: owner P6-ORPHAN"}` and C-P7 `{depends_on: "C-P6"}` → one warning for C-P7; C-P7 with C-P6 `{status: "**done** 2026-10-21"}` → none; a row with `depends_on: "LEGACY-CITE-PROMPT (#185) merged; never beside G-C5"` and G-C5 blocked → none; `B-3 merged, B-2` with B-3 blocked → one | all four as stated | yes: on `main` the sed prints nothing (no `depWarnings`), so the check fails |
| Replay: `build-wave` with `{ids: ["C-P7"]}` (nested false) | C-P7 is not in `picked`; its reason names C-P6's row status | not deterministic before the change (the selector may or may not misread), which is why check 2 exists |

**Files:** `.claude/workflows/build-wave.js`. No slots (no backend test).
**Expected collected delta:** 0. **Est:** 0.5 h.
**Acceptance:** the three checks above, pasted; `python3 scripts/docs_lint.py`. **Rollback:** revert.
**Order:** ready now. Never beside another `build-wave.js` PR. Runtime claude (harness rows need a Claude Code session to replay).

### 2.18 PYSLOT-MODE — the pytest slot script never creates its lock directory

**Source:** found while planning 2026-10-20 (queue bullet ENV). The ENV bullet itself (CRLF in the old machine's working tree) does not reproduce here: `git ls-files --eol scripts/pyslot.sh` prints `i/lf w/lf attr/text=auto`. Two other defects in the same script did.

**Facts:**
1. **Fixed while this plan was open:** on `b2b3f4e` the blob was mode `100644`, so on a `core.fileMode=true` checkout (this cloud box) `./scripts/pyslot.sh true` gave `Permission denied`, exit 126 (measured). #220 (`1cd94ee`, merged into `main` as `a10962d`) set it to `100755`. That half is not part of this row.
2. **Still open on `a10962d`:** the script locks `/tmp/claude-1000/hc-pytest.$i.lock` (`scripts/pyslot.sh:8`) but never creates `/tmp/claude-1000`. Where it is missing, `flock` prints `cannot open lock file … No such file or directory` and exits 66. Because `66 != 75`, the script exits 66 at once and the test command never runs (measured with a missing directory). RUNBOOK §6 step 2 (`RUNBOOK.md:137`), contracts §d step 2 and `.claude/workflows/build-item.js:236`, `:265` all go through it.
3. Several lane docs define `pyt` as `scripts/pyslot.sh …` "from `src/backend`" (lane E §2.8 `:226`, lane D `:626`), but `src/backend/scripts/` has no `pyslot.sh`. Those are done rows, and this row does not edit their text. New sections use the absolute `bash "$(git rev-parse --show-toplevel)/scripts/pyslot.sh"` form.

**Design:** one line before the loop, `mkdir -p /tmp/claude-1000`. Nothing else changes: slot count, lock names, exit codes and mode stay as they are.

| Check | Expected | RED today? |
|---|---|---|
| `bash -n scripts/pyslot.sh` and `git ls-files -s scripts/pyslot.sh` | exit 0; mode `100755` kept | n/a |
| With `/tmp/claude-1000` absent: `./scripts/pyslot.sh true; echo $?`. Run this only on a box where no pytest holds a slot, and never delete the directory while one runs. A safe RED alternative is a scratch copy of the script with the lock path pointed at a fresh empty temp dir | `0`, and the directory now exists | yes (66) |

**Files:** `scripts/pyslot.sh`. No slots.
**Expected collected delta:** 0. **Est:** 0.1 h.
**Acceptance:** the checks above, pasted. **Rollback:** revert.
**Order:** ready now. No shared file with any open PR. Runtime claude.

### 2.19 GATE12-MINORS — no test catches a record-only guard when the master DB file exists, or pins the session-end backstop

**Source:** PR #206 (GATE-12) round-2 review MINORs: HC-GATE12-001 misses a record-only guard when `data/asclexis.db` already exists; no test pins the session-end backstop (`tests/conftest.py:88-92`).

**Facts (`b2b3f4e`):**
1. HC-GATE12-001 (`src/backend/tests/test_gate12_master_db_guard.py:40-62`) sets `created = real.exists() and not existed` (`:51`). When the file already exists (a developer machine), `created` is always `False`, so only the hit count (`:54`) is checked, and a guard that records the hit but lets the connect go through passes.
2. The backstop is in `_gate12_guard`'s teardown (`src/backend/tests/conftest.py:88-92`): leftover hits after the session fail the run. HC-GATE12-002 (`:65-94`) runs an inner pytest whose hit is made in a test body, so the per-test check catches it; its comment (`:91`) says the backstop is not what it checks. The per-test check is `_gate12_check` (`conftest.py:95-98`), called by `_gate12_per_test` (`:101-105`).

**Measured on `b2b3f4e`:**
- Record-only mutant (the real listener removed from `database.engine.sync_engine` and replaced by one that only appends the hit), with an empty `data/asclexis.db` created first: HC-GATE12-001 **passes**. The proposed HC-GATE12-004 **fails** (`DID NOT RAISE RuntimeError`) and passes with the real guard.
- Backstop: an inner run (the real `conftest.py` copied to a temp dir, as HC-GATE12-002 does) whose session-scoped fixture appends `late-session-teardown` in its teardown prints `1 passed, 1 error` and the GATE-12 message ending `[late-session-teardown]`, exit 1. With the 4 backstop lines removed from the copied conftest: `1 passed`, exit 0.

**Design:** tests only; `tests/conftest.py` is not edited.

| Id | Assertion | RED today? |
|---|---|---|
| HC-GATE12-004 | with `data/asclexis.db` present (created empty if absent, removed in `finally` only if this test created it), `async with database.engine.connect()` raises `RuntimeError` whose message contains `GATE-12`; the test removes its own hit; `await database.engine.dispose()` in `finally` | no (pin). Record-only mutant → fails (measured) |
| HC-GATE12-005 | inner run as HC-GATE12-002, with a session-scoped fixture that appends a hit in its teardown and one test that uses it → output contains `1 passed, 1 error` and `[late-session-teardown]` | no (pin). Mutant: the copied conftest without `:88-92` → inner `1 passed`, test fails (measured) |

**Files:** `src/backend/tests/test_gate12_master_db_guard.py`, slots. **Re-run, not edited:** `tests/test_denial_audit.py`, `tests/test_export_redaction.py`.
**Expected collected delta:** +2. **Est:** 0.5 h.
**Acceptance:** `pyt tests/test_gate12_master_db_guard.py tests/test_denial_audit.py -q -rfE`: 0 failed; both mutant outputs pasted; `git diff origin/main -- src/backend/tests/conftest.py` empty; full suite per RUNBOOK §6, then `test ! -e src/backend/data/asclexis.db` unless it existed before the run. **Rollback:** revert.
**Order:** ready now. Never beside another PR on `tests/test_gate12_master_db_guard.py` or `tests/conftest.py` (none open on `b2b3f4e`).

### 2.20 PKT-Q-MINORS — the stored-question tests pass if the question is blanked

**Source:** PR #213 (PKT-QUESTIONS-REDACT) review MINORs.

**Facts (`b2b3f4e`):** HC-PKT-024 (`src/backend/tests/test_visit_prep_packet.py:876-917`) and HC-PKT-025 (`src/backend/tests/test_pinboards.py:591-637`) assert only that `Jane`, `Smith` and `A1234567` are absent from each stored question (`:914`, `:634`). Each has a local `from datetime import timedelta` (`:880`, `:597`) although the module already imports it (`test_visit_prep_packet.py:21`, `test_pinboards.py:7`). The redacted question today is `This follow-up is still open: Call [NAME-REDACTED], [MRN-REDACTED]. Should it be scheduled?` (measured with `RedactionEngine(policy_level="strict")`).

**Measured on `b2b3f4e`:** mutant `{"question": "", …}` at `src/backend/modules/export.py:731` (working copy, reverted with `git checkout`): both tests **pass** (`2 passed`).

**Design:** tests only. In each loop add `assert "[MRN-REDACTED]" in entry["question"]` and `assert "[NAME-REDACTED]" in entry["question"]`; delete the two local imports.

| Id | Assertion | RED today? |
|---|---|---|
| HC-PKT-024, HC-PKT-025 (edited) | as today, plus both tags present | no (pins). The blank-question mutant above → both fail. Paste before/after |

**Files:** `src/backend/tests/test_visit_prep_packet.py` (HC-PKT-024 only), `src/backend/tests/test_pinboards.py` (HC-PKT-025 only), slots. **Re-run, not edited:** `tests/test_export_redaction.py`, `tests/test_export_questions.py`. `src/backend/modules/export.py` shows an empty diff.
**Expected collected delta:** 0. **Est:** 0.25 h.
**Acceptance:** `pyt tests/test_visit_prep_packet.py tests/test_pinboards.py tests/test_export_questions.py -q -rfE`: 0 failed; the mutant output pasted; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** ready now. Never beside C-GC1 or REDACT-NAME-PINS (`tests/test_visit_prep_packet.py`).

### 2.21 REDACT-NAME-PINS — pin strict run-on over-redaction and the visit-prep PDF download (tests only)

**Source:** owner E1C-DIFF (`docs/capstone-report/owner-decisions-2026-09-27.md:273`): "The over-redaction is strict only and errs toward hiding more. REDACT-WS-REDOS, the name gaps and the unpinned run-on behaviour become follow-up rows." PR #195 body, "Accepted strict-only over-redaction" and "Tests" (HC-PKT-023 checks the HTML download only). Split from REDACT-NAME-GAPS so the pins land without the ask-first gate.

**Facts (`b2b3f4e`):**
1. `spaced_labelled_id` (`src/backend/modules/redaction.py:152-168`, strict) takes up to four capitalised words and may cross a `.` or a newline; its comment (`:145-147`) documents the run-on. No test pins it: `tests/test_redaction.py` has no newline or `Follow Up` case.
2. HC-PKT-023 (`src/backend/tests/test_visit_prep_packet.py:791-824`) asserts the stored markdown and `format=html` only. `GET /export/visit-prep/{id}/download?format=pdf` (`src/backend/api/export.py:846`, pdf branch `:906-919`) has no test.

**Measured on `b2b3f4e`** (`RedactionEngine(...).redact(s).text`; and the PDF route through `route_client` with the real WeasyPrint 70.0 and `pypdf`):

| Input | strict | standard |
|---|---|---|
| `Name (legal): Jane Doe. Follow Up With Cardiology Team` | `[ID-REDACTED] With Cardiology Team` | unchanged |
| `Patient Name: Doe. Glucose High Today Noted` | `[ID-REDACTED] Noted` | unchanged |
| `Patient ID:\nGlucose 96 mg/dL` | `[ID-REDACTED] 96 mg/dL` | unchanged |
| `Name (legal): Jane Doe\nGlucose 96 mg/dL` | `[ID-REDACTED]\nGlucose 96 mg/dL` | unchanged |

PDF: `POST /export/visit-prep` with `reason_for_visit: "MRN (hospital): B67890"`, then `GET …/download?format=pdf` → 200, `application/pdf`; the extracted text has no `B67890` and contains `[MRN-REDACTED]` and `Reason for Visit`.

**Design:** tests only.

| Id | Assertion | RED today? |
|---|---|---|
| HC-REDACT-019 ×4 (parametrised) | the four rows above: strict output exactly as measured; standard output equals the input | no (pins). Mutant: `modules.redaction._RULES` monkeypatched in a scratch test so `spaced_labelled_id`'s tail is `{0,0}` instead of `{0,3}` (`redaction.py` not edited, not even temporarily) → the first two cases fail |
| HC-PKT-026a | as HC-PKT-023, but `format=pdf` with a stand-in `weasyprint` module whose `HTML(string=…).write_pdf()` returns the HTML bytes (the `_install_capturing_weasyprint` pattern, `tests/test_export_redaction.py:290-304`; runs everywhere) → 200, `application/pdf`, `.pdf` filename; body has no `B67890`, has `[MRN-REDACTED]` and `Reason for Visit` | no (pin). Mutant: the stand-in returns `b"Reason for Visit MRN (hospital): B67890"` → fails |
| HC-PKT-026b | the same with the real renderer, using the `weasyprint_renders` fixture from `tests/test_export_redaction.py` (imported, so it skips where WeasyPrint cannot render and fails under `HC_REQUIRE_WEASYPRINT=1`); text via `pypdf` | no (pin; measured above) |

**Files:** `src/backend/tests/test_redaction.py`, `src/backend/tests/test_visit_prep_packet.py`, slots. `src/backend/modules/redaction.py` and `src/backend/api/export.py` show an empty diff.
**Expected collected delta:** +6 (4 + 1 + 1). **Est:** 1 h.
**Acceptance:** `pyt tests/test_redaction.py tests/test_visit_prep_packet.py tests/test_export_redaction.py -q -rfE`: 0 failed (HC-PKT-026b passed, not skipped, on a box where WeasyPrint renders; say which); the 2 mutant outputs; `git diff origin/main -- src/backend/modules src/backend/api` empty; full suite per RUNBOOK §6. **Rollback:** revert.
**Order:** ready now. Never beside PKT-Q-MINORS or C-GC1 (`tests/test_visit_prep_packet.py`), or REDACT-NAME-GAPS (`tests/test_redaction.py`). Land it before REDACT-NAME-GAPS, so that row's diff shows any change to these pins.

### 2.22 REDACT-NAME-GAPS — name shapes strict and standard still leak (ask-first `modules/redaction.py`)

**Source:** owner E1C-DIFF (`owner-decisions-2026-09-27.md:273`, quoted in §2.21); PR #195 body, "Shapes that remain … Name tails"; queue bullet REDACT-NAME-GAPS. OW-W9 (`:292`, no name scrubber for journal free text) is about free text, not labelled names, and does not cover this row.

**Measured on `b2b3f4e`** (`RedactionEngine(policy_level=…).redact(s).text`):

| Gap | Input | strict | standard | Rule |
|---|---|---|---|---|
| G1 hyphen | `Patient Name: Jane Doe-Smith` | `Patient [NAME-REDACTED]-Smith` | same | `name_context` (`redaction.py:85-93`; word `[A-Z][a-z]+`, no hyphen) |
| G1 hyphen | `Patient: Jane Doe-Smith` | `[NAME-REDACTED]-Smith` | same | `name_context` |
| G2 particles | `Name (legal): Maria de la Cruz` | `[ID-REDACTED] de la Cruz` | unchanged | `spaced_labelled_id` (`:152-168`; tail words must start upper-case) |
| G2 particles | `Patient (legal name): Ludwig van Beethoven` | `[ID-REDACTED] van Beethoven` | unchanged | `spaced_labelled_id` |
| G3 NFD | NFD `Name (legal): José Núñez` | `[ID-REDACTED]́ Núñez` | unchanged | `spaced_labelled_id` (a combining mark ends the word) |
| G3 NFD | NFD `Patient Name: José Núñez` | `[ID-REDACTED]́ Núñez` | **unchanged** | both |
| G4 non-ASCII | `Patient: José Núñez` (NFC) | **unchanged** | **unchanged** | `name_context` (`[a-z]` has no `é`) |
| G5 lowercase | `Name (legal): jane doe` | `[ID-REDACTED] doe` | unchanged | `spaced_labelled_id` |

Controls: NFC `Name (legal): José Núñez` → `[ID-REDACTED]` (strict); `Patient Name: Maria van der Berg` → `Patient [NAME-REDACTED]` (`name_context` runs with `(?i)`). G4 is new in this plan (not in #195's list): `name_context` misses any name with a non-ASCII letter, at both levels.

**Owner gates** (ask-first `modules/redaction.py`; RUNBOOK §4 step 4 needs a signed gate naming the exact edit):
- **REDACT-NG-SCOPE** (execution; open). Exact wording: "REDACT-NG-SCOPE (ask-first `modules/redaction.py`): measured on `main`, labelled names still leak in part: `Patient Name: Jane Doe-Smith` → `Patient [NAME-REDACTED]-Smith` (strict and standard), `Name (legal): Maria de la Cruz` → `[ID-REDACTED] de la Cruz`, decomposed (NFD) `José Núñez` keeps `Núñez`, `Patient: José Núñez` is not redacted at all (strict and standard), and `Name (legal): jane doe` → `[ID-REDACTED] doe`. Which scope may an agent build on a draft PR? (a) Hyphens, particles, accents and NFD: `name_context` (strict and standard) accepts hyphenated parts and non-ASCII letters with combining marks; strict `spaced_labelled_id` accepts lowercase particles (de, la, del, van, der, von, da, di, du, le, bin, al) before a capitalised word and combining marks inside a word. Lowercase names after a qualifier stay a known gap (Recommended: closes every measured leak except lowercase names; standard output changes only for names with a hyphen or an accent). (b) (a) plus lowercase names after a qualifier (`Name (legal): jane doe` → fully redacted); costs more strict over-redaction, for example `Name (brand): lipitor daily` → `[ID-REDACTED]`. (c) No `redaction.py` change; the pins (REDACT-NAME-PINS) only."
- **REDACT-NG-DIFF** (merge only; open; asked after the draft PR exists): "REDACT-NG-DIFF: here is the exact `modules/redaction.py` diff for REDACT-NAME-GAPS under option (x), with RED/GREEN, the differential, timing and mutant output. Merge?"

**Design (under (a); the implementer drafts the exact diff for REDACT-NG-DIFF):**
1. `name_context` (`:88-89`): the name word becomes "a letter, then letters or combining marks (U+0300-U+036F), optionally `-` and another such word". The label, the `\s*(?::\s*)?` separator (REDACT-WS-REDOS) and the at-least-two-words rule stay.
2. `spaced_labelled_id` (`:161-163`): the tail word class gains U+0300-U+036F, and between tail words an optional run of the particle list (lower-case, case-sensitive), each followed by `[ \t]+`, before the next capitalised word. The four-word cap counts capitalised words only; particles do not open a new word on their own, so `Name (legal): Jane Doe de facto` keeps `de facto` (no capitalised word follows).
3. Every new optional piece starts with a non-space character, as E-1c's comment (`:121-126`) requires, so no two `\s*` become adjacent.

**Test-first** (`src/backend/tests/test_redaction.py`):

| Id | Assertion | RED today? |
|---|---|---|
| HC-REDACT-020 ×7 (parametrised) | the seven gap inputs G1-G4 above: no name token survives at strict; the `name_context` cases (G1 ×2, G3 `Patient Name:`, G4) also at standard | yes ×7 (measured above) |
| HC-REDACT-021 | differential: inline copies of today's `name_context` and `spaced_labelled_id` against the new rules, on a fixed corpus (the HC-REDACT-013/014 inputs, the HC-REDACT-019 pins, lab lines such as `Glucose 96 mg/dL (70-99)`, `Name (brand): Lipitor 20 mg`, `Name (legal): Jane Doe de facto`) plus 2000 seeded random strings over labels, names, particles, hyphens, accents, NFD marks, punctuation and newlines → every span today's rules redact is still redacted; standard output differs only on inputs that contain `-`, a non-ASCII letter or a combining mark | no (pin). Mutant "drop the particle-before-capital requirement" fails it on `Jane Doe de facto` |
| HC-REDACT-022 | timing, as HC-REDACT-015/017: `"Name (legal): Jane" + " de" * 20000`, `"Patient: Jane" + "-Doe" * 20000`, `"Name (legal): Jos" + "́" * 50000` → each under 1.0 s | no if the pieces follow point 3; the mutant "two adjacent `\s*`" fails it |
| HC-REDACT-019 (from REDACT-NAME-PINS) | unchanged unless the diff changes a pin; any change is shown in the PR body | — |

Under (b), HC-REDACT-020 gains `Name (legal): jane doe` and `Patient (legal name): jane doe`, and HC-REDACT-014 gains `Name (brand): lipitor daily` as a documented strict over-redaction.

**Files:** `src/backend/modules/redaction.py` (ask-first, **edited only after REDACT-NG-SCOPE**: `name_context` `:88-89` and `spaced_labelled_id` `:161-163` only), `src/backend/tests/test_redaction.py`, slots. **Re-run, not edited:** `tests/test_export_redaction.py`, `tests/test_visit_prep_packet.py`, `tests/test_pinboards.py`, `tests/test_external_runner_hardening.py` (standard level), `tests/test_rl_feedback.py`.
**Expected collected delta:** +9 under (a) (7 + 1 + 1); +11 under (b). **Est:** 2.5 h after REDACT-NG-SCOPE (+ security review).
**Acceptance:** 1. `pyt tests/test_redaction.py tests/test_export_redaction.py tests/test_visit_prep_packet.py tests/test_pinboards.py -q -rfE`: 0 failed. 2. The E-1a acceptance rows 3-4 suites (the other strict callers) and `tests/test_external_runner_hardening.py` (standard): same pass/fail as Task 0. 3. Full suite per RUNBOOK §6.
**Order:** blocked on REDACT-NG-SCOPE; depends on REDACT-NAME-PINS merged; PR stays draft until REDACT-NG-DIFF. Never beside another `redaction.py` / `test_redaction.py` row. RSI1-DONATE keeps an empty `redaction.py` diff; its PR-2 recall report (Task 3) is re-measured if this merges first. **Rollback:** revert; no data.

---

## 3. Provides

1. **`ci.yml` merge order (lane E owns):** E-3 (W-11a PR-3) → #74 (E-4) → #72 (W-4) → W-8. E-3 and #72 may swap; the second lander merges main and re-checks the job list. Every other lane that touches `ci.yml` rebases onto this order and asks lane E first.
2. **`ci.yml` end state, by job id:** `docs-lint` (unchanged); `backend-tests` with W-8's model-fetch step (lane A) before step `Run backend tests (with coverage report)` = `bash scripts/run-backend-tests.sh -q --cov=api --cov=core --cov=models --cov=modules --cov=monitoring --cov=security --cov=scripts --cov-report=term --cov-report=xml:coverage.xml`, then `Require the coverage report (fail closed)` = `test -s src/backend/coverage.xml`, then artifact `backend-coverage`; `backend-lint` (name `Backend Lint (ruff hard errors)`, `ruff==0.15.10`, `--select E9,F63,F7,F82`; only after Q-RUFF (a)); `frontend-tests` steps `Type check` → `Lint (eslint)` (`npm run lint`) → `Run tests` → `Production build` (`npm run build`); `security-scan`, `agent-evals` unchanged; `legacy-evals` (#72); `e2e-tests` + artifact `tw4-shots` (#74).
3. **Doctor-summary contract (E-1):** `ExportModule.redact_summary_data(summary_data: dict) -> dict` returns a strict-redacted copy carrying `redaction_count: int`; `POST /export/doctor-summary` stores only that copy and returns redacted `key_findings`; its `doctor_summary` audit row carries `details.redaction_count`. `_format_abnormal_values` renders `%Y-%m-%d`. CSV/JSON bytes unchanged (HC-EXPR-002). G-C1 persists already-redacted summaries.
4. **New test IDs:** HC-EXPR-001/002/003 (`tests/test_export_redaction.py`, 8 items); HC-PGUARD-001…006 and, under OG-1, HC-PAUD-001…007 (E-2); HC-MIGHEAD-001…003 (`tests/test_migration_heads.py`, E-3).
5. **Test pattern for any 403 route test after #78:** patch `core.database.async_session_maker` to the test master maker and clear `core.denial_audit._state`; assert the `denial.cross_profile` row (E-1 §2.1 #2–3, E-2 §2.2 #1–2).

## 4. Consumes

1. P6 → P7 merged (E-2): `route_client(profile_name=, profile_db=)` and the `_SYNTHETIC_RESET_MODELS` tuple in `api/profiles.py`. Owner of P6/P7 is outside this lane.
2. #72 (W-4) and #84 merge timing: only as `ci.yml` / frontend rebase triggers (§3 item 1; §2.4 step 2).
3. Count slots: E-1 and E-3 do **not** wait for the lane D-0 chain. Each lane-E product PR measures `--collect-only` at start (N0) and again after its final merge of `origin/main`, and writes start + its own delta only if that matches; otherwise it recounts and writes the measured number (ground rule 8). Never take a side in a slot conflict.
4. Orchestrator program refresh (`implementation-program.md` Sign-off column, stale since 2026-10-09) before or with E-7.
5. Code-slot budget: at most 2 code L1s; full suites under `flock /tmp/claude-1000/hc-pytest.lock`.

## 5. Owner gates

| Gate | Item | State |
|---|---|---|
| Ask-first `modules/redaction.py` | E-1 calls `RedactionEngine(policy_level="strict")`, never edits it | **flag:** D3 (`:15`) approves strict redaction of the summary; any `redaction.py` edit (incl. an O-3 fix) is out of scope and needs its own plan |
| S-3 / O-3 residual underscore-joined PHI gap | E-1 | **unsigned**; blocks the **merge**, not execution |
| S-6 W-2 merge | E-1 | **unsigned**; after S-3 |
| S-1/O-1, S-4/EXPORT-QUESTIONS, S-5/P0-D-MOOT | E-1 | unsigned; none blocks execution or merge (plan "Owner questions") |
| O-2 | E-1 Task 3 | **signed** 2026-10-08: "ISO-8601 dates" |
| OG-1 (edit `api/profiles.py`, auth-adjacent) + Q-AUD-LIST | E-2 Task 2 | **unsigned**. RESET-AUDIT-OWNER (`:89`) assigns the reset audit to PR-1 but is not OG-1 |
| `core/auth.py`, `core/audit.py` | E-2, E-3 | not edited by any lane-E item |
| Q-RUFF | E-3 Task 7 | **unsigned**; recommended (a) hard-error rules only (0 findings today) |
| Q-COV | E-3 | answered 2026-10-19 (74% floor, `:300`); the threshold is row Q-COV-GATE (§2.15) |
| CI-SEED (W-11a OG-3) | E-3 Task 8 Step 4 | unsigned; W4-CI-SEED (`:106`) does not cover it |
| TW4-SHOTS + #74 merge | E-4 | owner compares screenshots (`:140`); owner merges |
| NPM-AUDIT-CI (new) | E-5 | unasked; default do not add |
| W1-SMOKE-RUN (new) | E-6 | unasked; default owner runs W-1 Task 7 |
| Ask-first `modules/redaction.py` (**edited**) | E-1b, REDACT-EMAIL-REDOS | each needs a yes to edit (E1B-SCOPE, REDOS-APPROACH) and a yes on its exact diff before merge (E1B-DIFF, REDOS-DIFF), as E-1a; never both at once |
| E1B-SCOPE (new) | E-1b | unasked; (a) the queue row's shapes (qualifier, `#`/`no.`, `-`) or (b) also `=` and `;`. Recommended (b) |
| REDOS-APPROACH (new) | REDACT-EMAIL-REDOS | unasked; (a) `@`-anchored match, identical output / (b) RFC bounds, narrower / (c) leave. Recommended (a) |
| EXPORT-COLLECTED-TZ-DISPLAY | EXPORT-COLLECTED-TZ | **answered 2026-10-18: (c) "As recorded + pin"** (owner-decisions row EXPORT-COLLECTED-TZ-DISPLAY) |
| E1C-SCOPE, E1C-DIFF | E-1c | E1C-SCOPE **answered (b)** 2026-10-19 (`docs/capstone-report/owner-decisions-2026-09-27.md:272`, PR #190 merged): spaced shapes + underscore residuals with a separator. E1C-DIFF (merge) open, asked after the draft PR exists |
| REDACT-WS-REDOS-BUILD, REDACT-WS-REDOS-DIFF (new) | REDACT-WS-REDOS | REDACT-WS-REDOS answered 2026-10-19 "Plan the row now" (`owner-decisions-2026-09-27.md:276`, planning only). **REDACT-WS-REDOS-BUILD** (edit licence) open; **REDACT-WS-REDOS-DIFF** (merge only) open, asked after the draft PR exists. Exact wording in §2.13 |
| GATE-12 | GATE-12 | **answered 2026-10-19: yes, add the row** (`:299`) |
| Q-COV | Q-COV-GATE (was E-3) | **answered 2026-10-19: 74% floor** (`:300`) |
| PKT-Q-SCOPE, PKT-Q-DIFF (new) | PKT-QUESTIONS-REDACT | both open (export path under the redaction invariant; `redaction.py` called only). Exact wording in §2.16; recommended (a) |
| REDACT-NG-SCOPE, REDACT-NG-DIFF (new 2026-10-20) | REDACT-NAME-GAPS | both open. REDACT-NG-SCOPE is the edit licence and scope for ask-first `redaction.py` (recommended (a)); REDACT-NG-DIFF is merge only, asked after the draft PR exists. Exact wording in §2.22 |

## 6. Open questions

1. **Q-E1 (E-3 order):** the lane drops the `W-4 → W-11a PR-3` ordering (§2.3) because the `ci.yml` hunks are disjoint and #72 waits on an owner model-host run. The orchestrator records this in program `:142`, or says no and PR-3 waits for #72.
2. **Q-E2 (E-2):** should HC-PGUARD's denial-row assertion live in PR-1, or stay with `test_denial_audit.py`? Default: in PR-1, because it is the HTTP proof that `require_profile_access` writes the row.
3. **Q-E3 (GATE-12):** *Answered 2026-10-19 (owner GATE-12, `owner-decisions-2026-09-27.md:299`: yes, add the row); planned as §2.14.* #78 made every cross-profile 403 on a `require_profile_access` route write through `core.database.async_session_maker`. A route test that forgets the patch writes to `src/backend/data/asclexis.db` if it exists. A conftest-level autouse patch would close this for all tests, but `tests/conftest.py` is read-only for W-11a (plan §1). Register as a GATE-12 follow-up?
4. **Q-E4 (E-5):** if `npm audit` on merged main is still > 0, does each remaining advisory need its own owner row (FE-SEQ reading), or one row for the batch?
5. **Q-E5 (E-6):** may an L1 in a fresh Claude Code session inside the smoke worktree run W-1 Task 7 instead of the owner (W1-SMOKE-RUN)?

## 7. Peer review (2026-10-15)

**Changed in this file:**

1. **E-1 variant-I (lane F):** HC-EXPR-003 calls `route_client` in its own body (§2.1 #9); acceptance adds the PR-body red-first and break-it evidence lane F's W-10b needs.
2. **Count slots (lane D):** E-1 / E-3 no longer wait for the whole D-0 chain; recount at start and after the final merge of main (§4 item 3).
3. **E-4 (lanes A, B, C, F):** listed who rebases after #74; drift scan covers C-GAM2B's switch if it landed first; dropped the "take main's slot" wording (#74 has no slot edit).
4. **E-3 (lane A):** recorded W-8's fetch step position in `backend-tests` and the disjoint `ci-and-quality-gates.md` lines (§2.3, §3 item 2).
5. **E-6 (lane F):** the optional HC-AGENTS fix waits for #68, which rewrites the same test.

**Confirmed, no change:** lane C C-P7 appends `profile_name` **and** `profile_db` to `route_client` (lane C doc `:87`, `:244`), which E-2 consumes. Lane C's `api/profiles.py` order (C-P6 → C-P7 → {C-GC1, E-2, wearables}, second lander rebases) and `test_audit_order_guard.py` rule (each lane adds only its own rows) match E-2. C-GC1 consumes `ExportModule.redact_summary_data` in `modules/export.py` (lane C `:255`), as E-1 provides. Lane A accepts the `ci.yml` order E-3 → #74 → #72 → W-8.

**Raised to peers / L0 (not edited here):**

- P-1 (L0): 2-code-L1 budget is box-wide. Lane D plans D-2 ‖ D-3, lane E plans E-1 ‖ E-3, and B-3 is also ready. L0 assigns slots.
- P-2 (lane F): F-5 F2 trigger `grep -n "RedactionEngine" src/backend/modules/export.py` already matches today (`:533`, `:637`, visit-prep). Use `grep -n "def redact_summary_data" src/backend/modules/export.py`.
- P-3 (lanes C, B, D, F, E): `docs/features/TASK_LIST.md` is edited by E-3, C-P6, C-DUPAUD, B-9, F-1, F-13 with no order. Rule: each edits only its own row or section; second lander rebases.

Back to: [implementation program](../../capstone-report/implementation-program.md) · [owner decisions](../../capstone-report/owner-decisions-2026-09-27.md)
