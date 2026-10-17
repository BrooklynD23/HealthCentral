# Lane E — Privacy, Gates, CI — Build Design

**Last Updated:** 2026-10-17 (E-3a plan delta §2.3a, L0 after PR #130 Task 0 stop)
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
| E-3a | Repo-wide ruff cleanup before E-3 Task 7 (Q-RUFF) | owner-decisions Q-RUFF (`:178`); W11a plan Task 7 option (b) (`:1587`), Q-RUFF option (b) (`:1949`); queue E-3a row | yes → §2.3a | — (runs alone) | ready |
| E-4 | Tailwind 4 landing (#74) | #74 body; [TW4 brief](../../../audit/2026-09-25/waves/briefs/TAILWIND-4-L1-brief.md); owner rows `:64-73,:108-111,:138-140` | yes (brief + PR) → landing steps §2.4 | E-3 (recommended first), owner TW4-SHOTS | blocked-on-owner |
| E-5 | NPM-AUDIT-DRIFT: the 7 remaining advisories | program `:493` (closed row; "the remaining 7 need Tailwind 4"), `:427` | no (closed row) → §2.5 | E-4 merged | blocked-on-PR |
| E-6 | W1-SMOKE: owner `/agents` runtime smoke | program `:487`; [W01 plan](../2026-09-27-W01-harness-agents-branch-a.md) Task 7 | yes → §2.6 | — | blocked-on-owner |
| E-7 | AUDIT-ORDER / AUDIT-DENIALS status reconciliation | [AUDIT-ORDER plan](../2026-10-09-AUDIT-ORDER.md) `:5`, `:467`; program `:488-489` | yes (executed) → §2.7 | — | ready (DOCS) |

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

### 2.3a E-3a — ruff cleanup (Q-RUFF), plan delta 2026-10-17

**Why this section exists:** PR #130 Task 0 stopped (check 1: no plan; plus three open points: ruleset, ruff version, unsafe fixes). This section is the plan. Measured on `chore/e-3a-ruff-cleanup` @ `8d72047` (= `origin/main` `5f46752` + claim), `~/venvs/asclexis-311/bin/ruff` **0.17.1**, `cd src/backend`.

**Ruleset (what the owner signed).** Q-RUFF (`owner-decisions:178`) answered **"Full default ruleset"**, consequence "needs a cleanup PR first, which touches many files". The only options the owner was shown are the W11a plan's: (a) hard errors `E9,F63,F7,F82`; (b) "a separate cleanup of all 561 findings first" (`2026-09-27-W11a-test-and-gate-hardening.md:1949`), and 561 is the **configured** set in `src/backend/pyproject.toml` (`select = ["F", "I", "W"]`, W11a `:210`). So the signed scope is **the configured F/I/W set**: 578 findings on 0.17.1. Ruff's built-in default (1873 findings, 52 codes incl. `UP045`, `B008`, `BLE001`) was never offered, and fixing it would exceed what was signed. It is out of scope. If the owner meant it, a follow-up item covers the extra rules; this cleanup does not conflict, because the built-in set also contains `F` and `I`. No `pyproject.toml` / `ruff.toml` change: the rule list stays as it is.

**Ruff version:** pin **0.17.1**. That is the version installed on the box (`importlib.metadata.version("ruff")` → `0.17.1` in `~/venvs/asclexis-311`); 0.15.10 is no longer installed. Every count below and every acceptance command uses this binary. E-3 Task 7 must pin the same version in CI (contracts I-23).

**Path scope:** every `*.py` under `src/backend/`, including `src/backend/scripts/`, minus the excluded files below. Repo-root `scripts/` is **out of scope**: it has no ruff config, and under F/I/W it has 1 finding (`scripts/docs_lint.py` I001), which the owner's set does not cover. The queue row's "`scripts/`" means `src/backend/scripts/`.

**Excluded files: never edited, findings listed for the owner (52 findings, 16 files).** These are the CLAUDE.md §1 ask-first modules, plus every file with auth or encryption logic (CLAUDE.md §1: "anything auth/encryption"). The second group was found by grepping the files that have findings for key derivation, sealing, Fernet/AES, `PRAGMA key`, password hashing and token creation:

| File | Findings | Why excluded |
|---|---|---|
| `modules/interpret_safety.py` | 2 (I001, F541) | ask-first |
| `modules/redaction.py` | 2 (I001, F401) | ask-first |
| `modules/faithfulness.py` | 2 (I001, F841) | ask-first |
| `modules/verifier_agent.py` | 1 (I001) | ask-first |
| `core/auth.py` | 3 (I001, F401, F841) | auth |
| `core/security.py` | 10 (8 W293, I001, F401 `win32crypt` availability probe) | encryption |
| `core/profile_database.py` | 12 (10 F401, 2 I001) | SQLCipher; `:410-416` F401s are **side-effect model registrations** (`models.document` … `models.model_settings`), so removing them would break the profile schema |
| `security/__init__.py` | 1 (I001) | security package |
| `core/database.py` | 1 (W293) | SQLCipher engine |
| `core/migrations.py` | 1 (F401) | `PRAGMA key` |
| `migrations/profile/env.py` | 1 (I001) | `PRAGMA key` |
| `api/profiles.py` | 3 (I001, 2 F401 of `core.auth` names) | login, unlock, recovery, change-password routes |
| `api/model_settings.py` | 7 (4 F401, 3 I001) | Fernet-encrypts API keys (`:749-750`) |
| `core/external_runner.py` | 3 (I001) | decrypts the API key; D12 redaction path |
| `modules/ingest.py` | 1 (I001) | document encrypt/decrypt (`:190`, `:226`) |
| `scripts/migrate.py` | 2 (I001, F401) | unseals the encryption key (`:37`, `:82`) |

**In scope: 526 findings in 174 files (92 product, 82 test).** By rule and fix safety: I001 235 (safe), F401 131 (safe), W293 116 (safe) + 14 (unsafe), F841 2 (safe) + 15 (unsafe), F811 7 (no auto-fix), F541 6 (safe).

**Unsafe-fix policy: `--unsafe-fixes` is never run on the tree.** Auto-fix uses ruff's safe fixes only, rule by rule, with the excluded files passed to `--extend-exclude`. Each remaining finding is handled by hand:

1. **W293 unsafe (14):** all 14 are inside docstrings (`modules/analytics.py:64,82,85,163,207,243`, `modules/export.py:74,94,279,323`, `modules/extract.py:68`, `modules/normalize.py:135,259,262`). Before fixing, confirm each one is a docstring, not a prompt, SQL or expected-output literal. Then run `--unsafe-fixes --select W293` on those four files only. The W293 commit must be whitespace-only: `git diff -w HEAD~1 HEAD` is empty.
2. **F401 (131, all ruff-safe):** an unused import can still matter, either as a side effect (model registration, as in `core/profile_database.py`) or as a re-export. Before the fix, run the AST scan below. It lists every `from X import name` in the repo where `X.name` is a flagged unused import, plus a `git grep` for the dotted `X.name` (`mock.patch` strings). On `8d72047` it finds **0 hits**, and none of the 131 sits in an `__init__.py`, a `conftest.py`, a `try/except ImportError` block, or a `models`/`migrations` registration. If main moved and the scan finds a hit, keep that import with `# noqa: F401  # re-exported by <file>`. Never delete it.
3. **F841 (17), by hand, never via `--unsafe-fixes`.** Drop the binding and **keep any call on the right-hand side**: `result = await self._notification_service.send(payload)` → `await …send(payload)` (`modules/notification_scheduler.py:599`); `list_parser = subparsers.add_parser(...)` → the bare call (`scripts/model_manager.py:246`); `except Exception as e` → `except Exception` (`api/assistant.py:1017`, `modules/embeddings.py:66`). Pure dead locals are deleted: `modules/notification_scheduler.py:470` `window_start_minutes`, `modules/agent/tools/retrieve_chunks.py:98` `query_lower`. Both of those are listed in the PR body as **possible latent bugs**: a value was computed and never used. Behaviour stays unchanged, and the cleanup does not fix them. The 11 test F841s (`tests/agent/test_s2_loop.py:125`, `tests/security/test_input_validator.py:178`, `tests/security/test_security_remediation.py:346`, `tests/test_chat_sessions.py:498,540,570`, `tests/test_llm_provider_layer.py:489`, `tests/test_rag_category_filter.py:201,227`, `tests/test_rl_feedback.py:226,680`) get the same treatment: keep the call, drop the name, **add no assertion** (an assertion changes what the test proves). Each one goes in the PR body as "possible missing assertion".
4. **F811 (7):** the pytest fixture-import pattern. `from tests.test_medications_routes_http import ..., profile_db  # noqa: F401`, and then `profile_db` used as a test parameter (`tests/test_adherence_patterns_tz_http.py:46,64,81,93,106,113`, `tests/test_notification_routes_http.py:18`). Removing the import breaks fixture lookup. Fix: add `# noqa: F811` on each of the 7 parameter lines. Do not change `per-file-ignores`.

**Commits** (one rule family each, so each diff can be reviewed by its own check):

| # | Message | Command (cwd `src/backend`, `R=~/venvs/asclexis-311/bin/ruff`, `X=<the 16 excluded paths, comma-joined>`) | Commit check |
|---|---|---|---|
| 1 | `chore(lint): strip whitespace-only blank lines (ruff W293)` | `$R check . --no-cache --fix --select W293 --extend-exclude "$X"`, then the 4-file `--unsafe-fixes` run (policy 1) | `git diff -w HEAD~1 HEAD` empty |
| 2 | `chore(lint): sort imports and drop placeholder-less f-strings (ruff I001, F541)` | `$R check . --no-cache --fix --select I001,F541 --extend-exclude "$X"` | `$R check . --select I001,F541 --extend-exclude "$X"` passes |
| 3 | `chore(lint): remove unused imports (ruff F401)` | AST scan (below) = 0 hits, then `$R check . --no-cache --fix --select F401 --extend-exclude "$X"` | `python -c "import main"` exit 0 |
| 4 | `chore(lint): unused locals and fixture-import redefinitions (ruff F841, F811)` | by hand, policies 3–4 | `$R check . --select F841,F811 --extend-exclude "$X"` passes |

`X` literally: `modules/interpret_safety.py,modules/redaction.py,modules/faithfulness.py,modules/verifier_agent.py,core/auth.py,core/security.py,core/profile_database.py,security/__init__.py,core/database.py,core/migrations.py,migrations/profile/env.py,api/profiles.py,api/model_settings.py,core/external_runner.py,modules/ingest.py,scripts/migrate.py`. Check: `$R check . --no-cache --extend-exclude "$X" --statistics` → `Found 526 errors.` on `8d72047`.

AST re-export scan (run in commit 3, from the worktree root; `f401.json` = `$R check . --no-cache --select F401 --output-format json` in `src/backend`): for each finding, map the file to its dotted module and the import to its last name. Then `ast.walk` every `git ls-files '*.py'` and print any `ImportFrom` where `module == <that module>` and an alias name matches, plus `git grep -nE '<module>\.<name>\b'`. Paste the output (expected: none) into the PR body.

**Tests:** **no new test ids.** The cleanup is behaviour-neutral, and its RED/GREEN check is the ruff command itself (RED today: 526 in-scope findings). CI gating is E-3 Task 7's job, not a pytest. **Expected collected delta: 0.** A non-zero delta means the cleanup has deleted or shadowed a test (an F811/F401 fixture slip), so stop and fix it.

**Acceptance** (paste each command and its output into the PR body):

1. `$R --version` → `ruff 0.17.1`; `$R check . --no-cache --output-format concise` → every finding path is in the excluded table, and the count equals the excluded findings re-measured at the final merge of main (52 at `8d72047`). In-scope findings: 0.
2. `$R check . --no-cache --select E9,F63,F7,F82` → `All checks passed!`.
3. `git diff --name-only origin/main...HEAD` lists only `src/backend/**/*.py` files and no excluded file (`grep -xFf` against the excluded list is empty). No `pyproject.toml`, `ruff.toml`, `requirements*.txt` or non-Python file.
4. Collected count through `scripts/pyslot.sh … --collect-only -q` equals the Task 0 start count (1721 at Task 0, `issuecomment-6243032805`; re-measure after merging main).
5. The full backend suite has the **same failure set** as the start tree: run it once at Task 0 and once at the end. Only the environmental `test_api_rag_index_002b` may fail, and only if it also fails at the start.
6. `python -m compileall -q src/backend` exit 0, and `cd src/backend && python -c "import main"` exit 0 (catches a removed import that some code path still needs at import time).
7. `git diff origin/main...HEAD -- src/backend/migrations` contains only I001 reorderings (the Alembic chains are unchanged; `migrations/profile/env.py` is excluded).
8. CI green on all jobs, including `agent-evals` (golden set unchanged).

**What these checks would not notice:** an import used only through `importlib`/`getattr` with a computed name. The AST scan and the grep cover literal names. The suite and `import main` cover the import graph. A computed-name use is not covered; the PR body says so.

**PR body also lists:** the 52 residual findings by file (the table above, re-measured), the 2 possible latent bugs, and the 11 possible missing assertions.

**Runs alone** (queue): no other code item runs at the same time, because the diff touches 174 files. Before pushing, merge `origin/main` and re-run acceptance 1–4. If main moved, re-run the cleanup commands rather than resolving lint conflicts by hand.

**Consequence for E-3 Task 7 (not this item):** under Q-RUFF, Task 7 gates on the configured F/I/W set with ruff 0.17.1, not on `E9,F63,F7,F82` with 0.15.10 (§3 item 2 predates the answer). The 52 residual findings in excluded files would fail that gate. Task 7 therefore waits on owner question **Q-RUFF-RESIDUAL** (§6).

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
| Q-RUFF | E-3a, E-3 Task 7 | **answered** 2026-10-15 "Full default ruleset" = cleanup first (option (b)); read as the configured F/I/W set (§2.3a). E-3a ready; Task 7 also waits on Q-RUFF-RESIDUAL |
| Q-COV | E-3 | unsigned; only a threshold needs it; report-only proceeds |
| CI-SEED (W-11a OG-3) | E-3 Task 8 Step 4 | unsigned; W4-CI-SEED (`:106`) does not cover it |
| TW4-SHOTS + #74 merge | E-4 | owner compares screenshots (`:140`); owner merges |
| NPM-AUDIT-CI (new) | E-5 | unasked; default do not add |
| W1-SMOKE-RUN (new) | E-6 | unasked; default owner runs W-1 Task 7 |

## 6. Open questions

1. **Q-E1 (E-3 order):** the lane drops the `W-4 → W-11a PR-3` ordering (§2.3) because the `ci.yml` hunks are disjoint and #72 waits on an owner model-host run. The orchestrator records this in program `:142`, or says no and PR-3 waits for #72.
2. **Q-E2 (E-2):** should HC-PGUARD's denial-row assertion live in PR-1, or stay with `test_denial_audit.py`? Default: in PR-1, because it is the HTTP proof that `require_profile_access` writes the row.
3. **Q-E3 (GATE-12):** #78 made every cross-profile 403 on a `require_profile_access` route write through `core.database.async_session_maker`. A route test that forgets the patch writes to `src/backend/data/asclexis.db` if it exists. A conftest-level autouse patch would close this for all tests, but `tests/conftest.py` is read-only for W-11a (plan §1). Register as a GATE-12 follow-up?
4. **Q-E4 (E-5):** if `npm audit` on merged main is still > 0, does each remaining advisory need its own owner row (FE-SEQ reading), or one row for the batch?
5. **Q-E5 (E-6):** may an L1 in a fresh Claude Code session inside the smoke worktree run W-1 Task 7 instead of the owner (W1-SMOKE-RUN)?
6. **Q-RUFF-RESIDUAL (E-3 Task 7, after E-3a):** after E-3a, 52 F/I/W findings remain in 16 ask-first, auth or encryption files (§2.3a table). Should the CI ruff gate (i) exclude those 16 files until a per-file approved cleanup, (ii) wait for that cleanup, or (iii) gate on hard errors (`E9,F63,F7,F82`) and keep F/I/W advisory? Asked by L0. It does not block E-3a.

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
