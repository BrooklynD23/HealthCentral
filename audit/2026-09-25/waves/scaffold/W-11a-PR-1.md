**BLOCKED** — hard dependencies P5 and P7 are not merged on `origin/main` (P7 waits on P6, which waits on P5).

# W-11a PR-1 — G-B1 profile-route guards + audit · readiness pack (sections 1-3 only)

**Written:** 2026-10-07 · **Measured on:** worktree `hc-scaffold` @ `8d6f02e`, `origin/main` = `6b4dd84` · **Plan:** [`docs/plans/2026-09-27-W11a-test-and-gate-hardening.md`](../../../../docs/plans/2026-09-27-W11a-test-and-gate-hardening.md) (Task 0, Tasks 1-2, Task 10) · **Status:** scaffold only. Nothing here is implemented, signed or approved. Work stops at the blocker; sections 4-7 are not written.

## 1. Readiness verdict

| Dependency / gate | State |
|---|---|
| D9 venv | present |
| **P5** (`api/profiles.py` hunks first) | **NOT merged** → BLOCKED |
| **P7** (`_SYNTHETIC_RESET_MODELS`, `route_client(profile_name=, profile_db=)`) | **NOT merged** → BLOCKED |
| OG-1 (audit calls in `api/profiles.py`) | **UNSIGNED** |
| Q-AUD-LIST (audit `GET /profiles/` or exempt it) | **UNSIGNED** |

Not architectural (orchestration §5). security-reviewer applies (auth file, audit rows).

## 2. Task 0 evidence (measured)

| Check | Command | Output |
|---|---|---|
| base | `git rev-parse --short origin/main` | `6b4dd84` |
| D9 venv | `~/venvs/asclexis-311/bin/python --version` | `Python 3.11.16` |
| **P5 missing** | `git ls-tree --name-only origin/main scripts/ \| grep -c time_source_lint` | `0` |
| **P5 missing** | `git grep -n 'datetime.utcnow' origin/main -- src/backend/api/profiles.py \| wc -l` | `6` (`:311-313`, `:391`, `:1052`, `:1153`) |
| **P7 missing** | `git grep -n '_SYNTHETIC_RESET_MODELS' origin/main -- src/backend/api/profiles.py \| wc -l` | `0` |
| **P7 missing** | `grep -n "profile_name=\|profile_db=\|real_auth\|def route_client" src/backend/tests/support/routes.py` | `27:def route_client(` and `46: profile_name="T",` only: the name is hardcoded, no `profile_db` or `real_auth` parameter |
| PR-1 not started | `git branch -r \| grep -iE 'w11a\|gb1'` | only `origin/docs/w11a-pr4-frontend-counts`, `origin/test/w11a-pr2-vault-ciphertext` (PR-4, PR-2: merged) |
| plan tracked | `git ls-files docs/plans/2026-09-27-W11a-test-and-gate-hardening.md` | path printed; also on `origin/main` |

**Owner gates**

| Gate | Row | State |
|---|---|---|
| D9 / D9-SRC | `docs/capstone-report/owner-decisions-2026-09-27.md:12`, `:29` | signed |
| SLOT-RULE | `owner-decisions-2026-09-27.md:31` | signed |
| OG-1 | `grep -n "OG-1\b" owner-decisions-2026-09-27.md` → 0 rows; plan §11 line `:1935` has no name or date | **UNSIGNED** |
| Q-AUD-LIST | 0 rows; plan `:1941` | **UNSIGNED** |
| OG-2 (`:41`) | signed, but it is PR-2's gate, not PR-1's | n/a |

Plan §1 (`:68`): "No owner option text licenses W-11a's scope directly." Task 1 (tests only) may run without OG-1; Task 2 may not.

## 3. Owner questions still to ask (after P7 merges)

**Q1 — OG-1 (ask-first `api/profiles.py`; plan `:1935`, wording kept).**
"I approve adding audit calls to `src/backend/api/profiles.py`: `GET /me` and `GET /{profile_id}` → `profile.view`; `POST /test/reset` → `profile.test_reset`, written after the vault commit, plus a master `get_db` dependency on that route; using the existing `core/audit.py` helpers unchanged."

| Option | Effect |
|---|---|
| **(a) Sign as written** — recommended | PR-1 ships Tasks 1 + 2; AUD-02 can move to tested. |
| (b) Sign for `GET /me` and `GET /{profile_id}` only | The reset-route row is left to P7 (see Q3). |
| (c) Do not sign | PR-1 ships Task 1 only (tests); AUD-02 stays partial. |

Covered by a signed row: **no.** D13 covers the `utcnow` swap only (plan `:77`, `:94`).

**Q2 — Q-AUD-LIST (plan `:1941`).**
"The unauthenticated `GET /profiles/` returns display names and writes no audit row."

| Option | Effect |
|---|---|
| **(a) Audit every call, `profile_id` NULL, `details={"count": n}`** — the plan's recommendation | One master row per profile-selector load; retention is unbounded (AUD-03). Adds HC-PAUD-006. |
| (b) Exempt it and document the exemption in C-AUDIT-1 / AUD-02 | No route edit for `list_profiles`. |

**Q3 — duplicate audit row on `/profiles/test/reset` (new; cross-plan).**
"Plan 07 Task 2 Step 3 already adds an audit event `synthetic_test_reset` and a `get_db` dependency to the reset route. W-11a Task 2 adds `profile.test_reset` to the same route, and HC-PAUD-003 asserts exactly `[("profile.test_reset", OWN, "profile", OWN)]` (plan `:899`). If P7 lands as written, HC-PAUD-003 sees a different name or two rows."

| Option | Effect |
|---|---|
| **(a) P7 leaves the audit row out; W-11a PR-1 adds it under OG-1** — recommended | One writer; W-11a's test stays as written. Same answer as P7 pack Q2 (a). |
| (b) P7 writes it; W-11a Task 2 covers only `GET /me`, `GET /{profile_id}` (+ `GET /`) | Amend W-11a: drop the reset-route edit, keep HC-PAUD-003 as a regression test with P7's name. |

**Q4 — AUDIT-ORDER interaction.** "OG-1's text says the reset row is 'written after the vault commit'. That is the ordering AUDIT-ORDER flags (a failed audit commit leaves a change with no row), and the owner answered AUDIT-ORDER 'Plan only' on 2026-10-07 (`owner-decisions:63`). Should PR-1 wait for the AUDIT-ORDER plan?" Options: **(a) no, ship with the existing ordering and list the 3 new sites for the AUDIT-ORDER plan — recommended** (consistent with every other write route today); (b) wait; (c) audit-first on these routes only (a new pattern; not licensed).

**Q5 — unowned items 3b proposed for W-11a (not in the plan).** GATE-12 (no general guard stops tests opening the developer's real master DB) and GATE-14 (`agent_eval_gate.py` prints PASS and does not exit). "Add either to W-11a, or keep them as owner items?" Options: **(a) keep as owner items; PR-1's new `tests/support/master_db.py` is file-backed and scoped to its own tests — recommended**; (b) add GATE-12 to PR-1 (touches `tests/conftest.py`, which the plan lists as not licensed, `:100`); (c) add GATE-14 to PR-3.

**Ask-first edits in PR-1**

| File | Edit | Covered? |
|---|---|---|
| `src/backend/api/profiles.py` — `get_current_profile`, `get_profile`, `reset_synthetic_test_profile` (+ `db` dependency), `list_profiles` | audit calls | OG-1 / Q-AUD-LIST, **unsigned** |
| `core/auth.py` (`require_profile_access`), `core/audit.py` (incl. `ALLOWED_ACTIONS`), `core/profile_database.py`, `core/security.py`, `tests/conftest.py` | none; read-only by plan `:100`, `:165-170` | n/a |
| `src/backend/tests/support/routes.py` | opt-in `real_auth: bool = False` | test harness; only after P7 merges (plan `:151`, `:179`: "If P7 has not merged, STOP") |

**Carry into the drift check once unblocked:** the plan cites the route decorators at `:241`, `:416`, `:477`, `:943` on `main@40f590e`; all four MATCH today (`sed -n '241p;416p;477p;943p'` prints the four `@router` lines). P5 (if it removes `:13`) and P7 will move them (plan Task 0 Step 7 re-verifies). `core/audit.py` line refs are against `B@7b2ff1f`. The plan's Task 0 commands create the worktree under `hc-w11a-gb1` on branch `fix/w11a-gb1-profile-guards`.

**Next action:** after P7 merges, ask Q1-Q3 in one prompt, then re-run `git grep -n '_SYNTHETIC_RESET_MODELS' origin/main -- src/backend/api/profiles.py | wc -l` (expect ≥ 1) and write sections 4-7.
