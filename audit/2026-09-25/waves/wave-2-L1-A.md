# Wave 2 — L1-A report (S-1, P2), 2026-10-01

Both PRs are open. Merge order: **S-1 (#29), then P2 (#31)**. #31 is a **draft**: owner gate **P2-INFLIGHT** must be answered before it merges.

| Phase | PR | Head | Collected START→END | Verdict |
|---|---|---|---|---|
| S-1 | https://github.com/BrooklynD23/HealthCentral/pull/29 | `d9f1820` (origin/main 2e85487 merged in) | 1296 → **1300** (+4) | ready; code-review APPROVE, security APPROVE, Codex approve |
| P2 | https://github.com/BrooklynD23/HealthCentral/pull/31 (draft) | `85dae5c` (origin/main 2e85487 merged in) | 1296 → **1306** (+10) | code-review APPROVE; security CHANGES (F1 needs owner gate) |

Base: START measured on origin/main `8064244` in both worktrees: `1296 tests collected` (hc-s1 27.81s, hc-p2 20.26s). After the host OOM (2026-10-01), both worktrees had no uncommitted changes and no `*.db` files. Work resumed from the surviving commits.

Environment for every figure: WSL2, `~/venvs/asclexis-311/bin/python` 3.11.16, sqlcipher3 present, `HF_HUB_OFFLINE=1`. Full suites ran under `flock /tmp/claude-1000/hc-pytest.lock`, one at a time, once per phase.

---

## S-1 — SQL echo PHI leak (#29)

**Plan:** `docs/plans/2026-09-27-S01-sql-echo-phi-leak.md`, Tasks 0-5. The execution record is committed in the plan.

**Gates used (verbatim from owner-decisions):**
- SQL-ECHO = S1-A + S1-B: "A: new sql_echo flag default False (decoupled from debug). B: hide_parameters=True so even when echo is on, values are masked."
- SLOT-RULE.
- D9-SRC.

The plan's sign-off checkboxes are left unticked on purpose (agents do not record approvals).

**Task 0 re-derivation:** the anchors are byte-identical to the plan:
- `config.py:28`, `database.py:46`, `profile_database.py:308`, key hook at `:315`, `.env.example:14`;
- `post-P1-ok`, `no-collision`, `file-free`.

So **no Codex r4 plan review** was run. The Codex diff review ran (mandatory).

**Commits:**

| sha | Subject | Collected slots |
|---|---|---|
| 016e672 | fix(db): decouple SQL echo from DEBUG so dev mode stops printing PHI (S-1) | 1296→1299 |
| f1ab1b5 | fix(db): hide bound SQL parameters on both runtime engines (S-1) | 1299→1300 |
| 60d578e | docs(plans): record S-1 execution evidence | — |
| d9f1820 | merge origin/main 2e85487 (L0 request) | 1300 |

**Commands and outputs (L1-run):**
```
$ pytest tests/ --collect-only -q -p no:cacheprovider     (at f1ab1b5)
1300 tests collected in 29.48s
$ flock … pytest tests/ -p no:cacheprovider -q -rfE        (at f1ab1b5)
1300 passed, 54 warnings in 275.00s (0:04:34)
pytest-exit=0
$ (after merging origin/main into d9f1820) generate_docs_index.py --check
docs/INDEX.md and docs/_link_graph.json are fresh.
$ pytest --collect-only → 1300 tests collected in 10.47s
$ pytest tests/security/test_sql_echo_phi.py tests/test_docs_lint.py → 11 passed, 5 warnings in 46.69s
$ python -c "from main import app" → boot-ok
$ python3 scripts/docs_lint.py → Docs lint passed.
$ grep -rn "echo=settings.debug" src/backend --include=*.py
src/backend/tests/security/test_sql_echo_phi.py:4  (docstring only; 0 product hits)
$ grep -n "hide_parameters=True" core/database.py core/profile_database.py → :47, :309
$ master DB check → 4 passed; master-untouched (absent)
$ param-parser grep → no-param-parsers; read-only files → read-only-unchanged
```

**Whole-app probe** (`~/s01-probe`, outside the repo):

| Run | Marks | Sentinels | Hidden | Engine lines |
|---|---|---|---|---|
| start | debug=True sql_echo=ABSENT, vault echo=True hide=False, create=201 verify=200 | NAME=1 `$2b$`=1 ANALYTE=1 731.0419=2 NOTE=1 | 0 | 156 |
| end, default | sql_echo=False, vault echo=False hide=True | all 0 | 0 | 0 |
| end, SQL_ECHO=true | vault echo=True hide=True | all 0 | 69 | 156 |

**Break-its** (disposable `~/s01-break`, since removed; each sed checked with `grep -n` first):

| # | Break | Result |
|---|---|---|
| BI-1 | sql_echo default True | 2 failed: 001, 003 `assert True is False` |
| BI-2 | vault without hide_parameters | 004: PHI list `['S1ECHO_ANALYTE_hba1c', '731.0419', 'S1ECHO_DOCTEXT HIV-1 RNA detected', 'S1ECHO_CHAT is my result dangerous']` |
| BI-3 | master without hide_parameters | 004 `assert False is True` |
| BI-4 | master echo=settings.debug | 003 `assert True is False` |
| BI-5 | vault echo=settings.debug | 001 `assert True is False` |
| BI-6 | 3 product files at origin/main | 4 failed: PHI lists including `['S1ECHO_NAME Jane Doe', '$2b$', 'S1ECHO_NOTE_VIA_HTTP']`, plus AttributeError sql_echo |
| BI-7 | DEBUG=false | 002 precondition AssertionError |

All 7 are red. F0 (the start full-suite failures) was lost in the OOM. That does not matter, because END has 0 failures.

**Reviews:**
- code-reviewer (opus): APPROVE, 3 MINOR.
- security-reviewer (opus): APPROVE, 4 LOW.
- Codex adversarial diff review: "Verdict: approve … No material findings."

**Open findings (none blocks the merge):**
1. `config.py`: the whitespace-only blank line became a clean blank line, so the diff is −1/+5 instead of the plan's +4.
2. The pass-count slots are stale and left unchanged by plan rule: `CLAUDE.md:31` "all 1288 pass", `AGENT.md:76` "1269 pass in CI, 1268 without". Measured here: 1300/1300 (owner item AGENT-PASS-LINE).
3. 001, 002 and 003 fail loudly if a developer's `.env` sets `SQL_ECHO=true` or `DEBUG=false`.
4. The 8 migration engines lack `hide_parameters`. They bind no PHI today (follow-up candidate).
5. No production force-off for SQL_ECHO (plan scope item 5). PRIV-06 stays partial.

CI at PR open: Documentation Lint pass, Agent Eval Gate pass, Frontend Tests pass; Backend Tests and Security Scan pending.

---

## P2 — Notification scheduler wiring (#31, DRAFT)

**Plan:** `audit/2026-09-25/plans/02-notification-scheduler.md`, Tasks 1-7.

**Dependency check:** the plan has no Task 0 and no Dependencies section. The file overlap with S-1 is only the CLAUDE.md/AGENT.md slots. So L1 built it in parallel; it merges after S-1. Security F2 (below) also relies on S-1's `hide_parameters`.

**Gates used (verbatim):**
- D6: "Two small hooks in open/close_profile_database_on_login/logout; session-scoped reminders only (fire only while a vault is unlocked); records skipped_locked. Quiet hours stay unenforced."
- audit §21 Q1 "Wire the notification scheduler" (agent-recorded).
- SLOT-RULE: applied per commit, which overrides the plan's single Task 6 slot update.
- D9-SRC.

**Commits:**

| sha | Subject | Slots |
|---|---|---|
| a7fdd59 | feat(notifications): register profile vault sessions on unlock/lock | 1300 |
| f71a45a | feat(notifications): record skipped_locked outcomes per scheduler pass | 1302 |
| 124bd29 | feat(notifications): start reminder scheduler in app lifespan | 1303 |
| 86bb5dc | fix(notifications): drop medication name from reminder log line | 1304 |
| b83da8f | test(notifications): end-to-end delivery, dedup, and PHI-boundary coverage | 1306 |
| 4aa8e03 | docs: reconcile notification-scheduler claims with wired reality | 1306 |
| aae90ec | docs: correct notification-scheduler session-note and features-index wording (code-review MINOR 1-2) | 1306 |
| 85dae5c | merge origin/main 2e85487 (TASK_LIST.md conflict: both session notes kept, P2 first) | 1306 |

**Commands and outputs (L1-run):**
```
$ pytest tests/ --collect-only (at 4aa8e03) → 1306 tests collected in 26.47s
$ flock … pytest tests/ -p no:cacheprovider -q -rfE (at 4aa8e03)
1306 passed, 47 warnings in 216.66s (0:03:36)
pytest-exit=0
$ python -c "from main import app; print(app.title)" → Asclexis API
$ pytest tests/test_notification_scheduler_wiring.py → 10 passed
$ pytest tests/test_profile_recovery.py tests/test_notification_scheduler_wiring.py → 37 passed
$ pytest tests/test_phase3_notifications.py → 34 passed
$ (at 85dae5c) collect → 1306; wiring + test_docs_lint → 17 passed; index fresh; Docs lint passed.
```

The full suite was not re-run after aae90ec and 85dae5c. Both are docs-only, plus a main merge that brought in docs and `scripts/docs_lint.py`, and the targeted docs-lint test passes.

**Break-its** (disposable `~/p2-break`, removed; each with `grep -n` and a line-number edit):

| Break | Red test |
|---|---|
| remove register hook | HC-NSW-001 |
| remove unregister hook | HC-NSW-002 |
| locked counted as "error" | HC-NSW-004 |
| status skipped_locked=0 | HC-NSW-005 |
| lifespan does not start | HC-NSW-006 |
| medication_name back in log | HC-NSW-009 (`'Metformin' is contained here`), run after test_profile_recovery.py |

Frontend (Task 7 Step 3) was SKIPPED: no frontend file changed, and vitest stalls under WSL. Manual smoke was SKIPPED.

**Reviews:**
- code-reviewer (opus): APPROVE, 7 MINOR. 1-2 (docs wording) fixed in aae90ec.
- security-reviewer (opus): CHANGES, 2 MEDIUM, 3 LOW.
- Codex was not run: P2 is not architectural per orchestration.md §5.

### STOPPED sub-task — owner gate needed: P2-INFLIGHT (security F1, MEDIUM)

**Defect:** a reminder pass in flight during lock, delete or restore can reopen the vault.
- `unregister_profile_session` only pops the dict entry.
- `close_profile_database` then disposes the engine.
- On its next query, the in-flight session checks out a fresh connection. That fires the `connect` listener, which re-runs `PRAGMA key` with the captured hex key.

**L1 reproduction** (`scratchpad/race.py`, aiosqlite, SQLAlchemy 2.0.54): session open, then `engine.dispose()`, then `os.remove(vault)`, then a query on the same session. Output: `connects before close 1`, `connects after close 2 file recreated: True`.

**Fix proposal:** a per-profile `asyncio.Lock` held for the whole pass, plus an async `unregister_profile_session_and_wait`, **awaited from the close hook in `core/auth.py`**, plus an HTTP-level test.

**Why STOP:** this changes the D6 hook in ask-first `core/auth.py` beyond plan 02's exact text. The brief says that STOPS.

**Question for the owner:** "Approve changing the D6 close hook to await the scheduler's in-flight pass (per-profile lock) before `close_profile_database`, plus the scheduler change and a test, inside P2?" The alternative is to accept the risk and merge as is.

### Other open findings (not fixed)
1. **F2, MEDIUM:** `notification_scheduler.py:275` `logger.error(f"…{e}")` would print SQLAlchemy `[parameters: …]`, which include the reminder text. S-1's `hide_parameters=True` on the vault engine closes this. So P2 must merge after S-1.
2. **LOW:** `/notifications/scheduler/status` reports global `registered_profiles` / `skipped_locked`, so it reveals how many other profiles are unlocked.
3. **LOW (pre-existing):** auto-lock is not enforced on the server. After JWT expiry the vault stays open and reminders keep firing.
4. **LOW (report only):** medication names appear in OS toasts and on the lock screen. Owner decision: a "private reminders" mode?
5. **Later (code-review MINOR):**
   - `_last_pass_results` is not reset on the rate-limited early return.
   - A lock mid-pass is recorded as "error".
   - `_factory` return annotation.
   - CLAUDE.md "Eight failure modes" is now 10 (CLAUDE-FAILURE-COUNT).
   - Stale pass slots (AGENT-PASS-LINE).

CI at PR open: all 5 checks pending.

---

## Merge order requested
1. **#29 S-1**: ready now.
2. **#31 P2**: after #29 merges, AND after the owner answers P2-INFLIGHT. If approved, an L1 resumes P2 to implement the fix (one implementer, then a security re-review). Before that merge, merge origin/main again; the CLAUDE.md/AGENT.md slots will conflict (1300 vs 1306). Re-measure the collected count (expected 1310 = 1296 + 4 + 10) and rewrite the slots.

## Worktrees
`../hc-s1` and `../hc-p2` are clean (`git status --short` empty, no `*.db`). `~/s01-break` and `~/p2-break` were removed. The probe files are left in `~/s01-probe` (outside the repo).

---

## Update 2026-10-01 — P2-INFLIGHT fixed in #31 (still draft)

The owner answered **P2-INFLIGHT** (relayed by L0): "Approve fix in P2 (Recommended)", i.e. "Per-profile asyncio.Lock + async unregister-and-wait awaited by the close hook in core/auth.py; plus a regression test." L0 records it in owner-decisions.

**Commit:** `4775e59` fix(notifications): wait for in-flight reminder pass before closing a vault (P2-INFLIGHT). Pushed; #31 head is 4775e59 and the PR is still a draft. origin/main is **not** merged yet, as L0 asked.

**Files (5):**
- `core/auth.py`: only the close hook changed. It now awaits `unregister_profile_session_and_wait` (plus a comment).
- `modules/notification_scheduler.py`: a per-profile lock held for the whole pass, and `unregister_profile_session_and_wait`.
- `tests/test_notification_scheduler_wiring.py`: adds HC-NSW-010.
- `CLAUDE.md`, `AGENT.md`: slots 1306 → **1307**.

**RED → GREEN:**
- RED before the fix: `E AssertionError: vault file recreated after close + erase`, `1 failed`.
- Implementer deviation: the test's fake pass adds a `commit()` after its first query, so the connection goes back to the pool. Without it the defect does not reproduce. No assertion was changed.
- GREEN: wiring file `11 passed`; wiring + phase3 + profile_recovery `72 passed`.

**Break-its (L1, run in a disposable worktree):**

| Break | Result |
|---|---|
| B7: close hook unregisters without waiting | HC-NSW-010 red: `vault file recreated after close + erase` |
| B8: pass does not hold the lock | HC-NSW-010 red, same message |

**END (L1, under flock, at 4775e59):**
```
1307 tests collected in 23.09s
1307 passed, 51 warnings in 271.12s (0:04:31)   pytest-exit=0
Asclexis API      Docs lint passed.      git status clean, no *.db
```

**security-reviewer re-review (opus): APPROVE, F1 CLOSED.**
- Every close path (logout, lock, delete, restore) goes through the hook. `close_all` runs only at shutdown, after the scheduler has stopped.
- No deadlock found.
- 3 LOW:
  1. The drain has no upper bound. Any future timeout must not lead to disposing the engine.
  2. One `asyncio.Lock` per drained profile can be re-created by a later pass. This is bounded and trivial.
  3. A `CancelledError` at the new await would skip the close. No `BaseHTTPMiddleware` is present, so this is not reachable today.

**P2 collected:** START 1296 → END **1307** (+11).

**Merge plan for #31:**
1. After #29 merges, merge origin/main.
2. The slots will conflict: 1300 on main vs 1307 here. Re-measure (expected 1311 = 1296 + 4 + 11) and rewrite the slots.
3. Run the targeted tests, then mark the PR ready.

## Status at hand-back (2026-10-01)
- #29 S-1 is **merged** (main 040cf8c, per L0).
- #31 P2 is **held as a draft** at 4775e59, by L0's instruction. It merges 6th, after #32 W-6, #33 W-11a PR-2, #34 W-5 and #35 W-1.
- When it is P2's turn:
  1. Merge origin/main.
  2. Re-measure collected (1296 + 4 + 11 = 1311 plus whatever #32-#35 add).
  3. Rewrite the CLAUDE.md/AGENT.md slots.
  4. Run the targeted tests, then the full suite under flock.
  5. Mark the PR ready and report.

## P2 refresh for merge (2026-10-02)
#31 is **ready for review**. Head `116dd4d` merges origin/main `cbabed1` (#35) into the branch. CI is 6/6 green.
- **Merge:** CLAUDE.md and AGENT.md conflicted only on the count slots. I took main's text, then rewrote the 3 slots to the measured count, 1335 → **1346** (= 1335 + 11). TASK_LIST.md merged without a conflict.
- **Collect:** `1346 tests collected in 18.75s`.
- **Gates:**
  - `generate_docs_index.py --check`: `docs/INDEX.md and docs/_link_graph.json are fresh.` (rc 0)
  - `docs_lint.py`: `Docs lint passed.`
  - `harness_drift_check.py`: `Harness drift check passed.` (rc 0)
- **Targeted tests** (wiring + phase3 + profile_recovery): `72 passed, 2 warnings in 14.88s`.
- **Full suite** (flock): `1346 passed, 54 warnings in 160.95s (0:02:40)`, exit 0.
- **Boot:** `Asclexis API`. `git status` is clean and there are no `*.db` files.
- **`gh pr checks 31`:** Agent Eval Gate pass, Backend Tests pass, Documentation Lint pass, E2E Smoke Tests pass, Frontend Tests pass, Security Scan pass.
