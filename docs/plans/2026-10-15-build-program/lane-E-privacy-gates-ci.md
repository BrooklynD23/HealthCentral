# Lane E — Privacy, Gates, CI — Build Design

**Last Updated:** 2026-10-17 (E-1b, REDACT-EMAIL-REDOS, DEV-SH-CC planned)
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
| HC-EXPR-001 (+1 row in `GAP_ROWS`, `tests/test_export_redaction.py:271`) | analyte `mrn_(hospital):_a12345` → absent from every doctor-summary download format | yes |

Also edit the `test_export_redaction.py` module docstring (`:9-10`): drop "the E-1b shapes" from the not-covered list and name what remains (gap 11, non-space whitespace; `=`/`;` unless E1B-SCOPE (b)).

**Tasks:** 0 start count + RED run (`-rfE`) + HC-REDACT-009 timing on `main`; 1 RED tests; 2 GREEN, the one-rule edit; 3 mutants (drop each new branch, drop the disjointness): each fails a named test, output in the PR body; 4 docstring; 5 PR as **draft** until E1B-DIFF.

**Files:** `src/backend/modules/redaction.py` (ask-first, **edited**), `src/backend/tests/test_redaction.py`, `src/backend/tests/test_export_redaction.py`.

**Expected collected delta:** +17 (7 + 6 + 3 + 1); +21 under E1B-SCOPE (b).

**Acceptance** (from `src/backend`, `pyt` = `scripts/pyslot.sh env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest`):
1. `pyt tests/test_redaction.py tests/test_export_redaction.py -q -rfE`: 0 failed.
2. E-1a acceptance rows 3–4 (safety suites; the other strict callers `fhir_export`, `visit_prep`, `rl_*`, `external_runner`, `agent/test_s4_phi_gate`, `agent/test_s6_evals`): same pass/fail as Task 0.
3. Full suite per RUNBOOK §6; collected = N0 + 17 (or + 21).

**Doc claim (PR body, PRIV-04 gap column via L0):** strict now also matches a parenthesised qualifier, `#` / `no.` before a bare label's colon, and `-` as a label separator. Never "all PHI".

**Order:** never beside REDACT-EMAIL-REDOS (same two files). Either may go first; the second rebases and re-runs both timing tests. **Rollback:** revert; no data.

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
| HC-REDACT-010 ×3 | strict on each of the 3 inputs above at `N = 20000` → under 1.0 s, text unchanged | yes ×3 (3.8–5.0 s) |
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

**Test-first:** new `src/backend/tests/test_dev_sh_prereqs.py`, skipped on Windows. Each test copies `dev.sh` into `tmp_path` with a 2-line `src/backend/requirements.txt` (`fastapi`, `llama-cpp-python==0.3.35`) and `config/.env.example`. It runs `bash dev.sh` through `subprocess` with a stub `PATH` (`python3` reporting 3.11 and recording `-m pip` arguments, `node`, `npm`, and `cc` only when wanted), with `HC_ALLOW_WINDOWS_MOUNT=1` and `HC_DEV_STOP_AFTER_DEPS=1`.

| Id | Assertion | RED today? |
|---|---|---|
| HC-DEVSH-001 | no `cc`, `LLM_PROVIDER=ollama` → exit 0, pip got a requirements file without `llama-cpp-python`, stderr has the skip warning | yes (no filter) |
| HC-DEVSH-002 | no `cc`, `LLM_PROVIDER=llama_cpp` → exit 1 before any pip call, message names `build-essential` and `LLM_PROVIDER=ollama` | yes (pip runs first) |
| HC-DEVSH-003 | `cc` present → the full requirements file | no (pin) |
| HC-DEVSH-004 | no `cc`, env unset, `src/backend/.env` says `LLM_PROVIDER=ollama` → as 001 | yes |

**Files:** `dev.sh`, `src/backend/tests/test_dev_sh_prereqs.py`. **Expected collected delta:** +4. **Acceptance:** `pyt tests/test_dev_sh_prereqs.py -q` 4 passed; `bash -n dev.sh`; on a box with a compiler, `HC_DEV_STOP_AFTER_DEPS=1 ./dev.sh` still installs everything (pasted). **Rollback:** revert.

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
| Q-COV | E-3 | unsigned; only a threshold needs it; report-only proceeds |
| CI-SEED (W-11a OG-3) | E-3 Task 8 Step 4 | unsigned; W4-CI-SEED (`:106`) does not cover it |
| TW4-SHOTS + #74 merge | E-4 | owner compares screenshots (`:140`); owner merges |
| NPM-AUDIT-CI (new) | E-5 | unasked; default do not add |
| W1-SMOKE-RUN (new) | E-6 | unasked; default owner runs W-1 Task 7 |
| Ask-first `modules/redaction.py` (**edited**) | E-1b, REDACT-EMAIL-REDOS | each needs a yes to edit (E1B-SCOPE, REDOS-APPROACH) and a yes on its exact diff before merge (E1B-DIFF, REDOS-DIFF), as E-1a; never both at once |
| E1B-SCOPE (new) | E-1b | unasked; (a) the queue row's shapes (qualifier, `#`/`no.`, `-`) or (b) also `=` and `;`. Recommended (b) |
| REDOS-APPROACH (new) | REDACT-EMAIL-REDOS | unasked; (a) `@`-anchored match, identical output / (b) RFC bounds, narrower / (c) leave. Recommended (a) |

## 6. Open questions

1. **Q-E1 (E-3 order):** the lane drops the `W-4 → W-11a PR-3` ordering (§2.3) because the `ci.yml` hunks are disjoint and #72 waits on an owner model-host run. The orchestrator records this in program `:142`, or says no and PR-3 waits for #72.
2. **Q-E2 (E-2):** should HC-PGUARD's denial-row assertion live in PR-1, or stay with `test_denial_audit.py`? Default: in PR-1, because it is the HTTP proof that `require_profile_access` writes the row.
3. **Q-E3 (GATE-12):** #78 made every cross-profile 403 on a `require_profile_access` route write through `core.database.async_session_maker`. A route test that forgets the patch writes to `src/backend/data/asclexis.db` if it exists. A conftest-level autouse patch would close this for all tests, but `tests/conftest.py` is read-only for W-11a (plan §1). Register as a GATE-12 follow-up?
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
