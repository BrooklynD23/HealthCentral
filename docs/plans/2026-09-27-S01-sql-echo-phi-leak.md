# S-1 SQL Echo PHI Leak — Implementation Plan

**Last Updated:** 2026-09-27
**Owner:** repository owner
**Refresh Trigger:** any of these before this plan runs:
- a change to `src/backend/core/config.py`, `src/backend/core/database.py`, `src/backend/core/profile_database.py`, `config/.env.example` or `src/backend/tests/support/routes.py`;
- P6 (FK pragma listeners) landing before this plan;
- an owner answer on sign-off S1-A or S1-B below.

**Prerequisites:** P0-B and P1 merged to `origin/main`; the D9 venv exists; **the 2026-09-27 plan set (including this file) is committed to main via an owner-approved docs commit**. P0-B's approved text covers only `audit/`, `docs/capstone-report/` and `docs/INDEX.md`, not `docs/plans/2026-09-27-*.md`, so that docs commit needs its own owner approval. Task 0's ancestry check failing before P1 lands is the **intended STOP**, not a defect.

**Status:** PROPOSED — not executed. Nothing in this plan is implemented, wired or tested on any branch.
- S-1 is a **new HIGH security finding** with **no owner decision yet**.
- The whole plan is **owner-gated**: sign-offs S1-A (Task 2) and S1-B (Task 3) are **unsigned**. Program register: both sit under canonical gate **SQL-ECHO** (with P08 S-3, answered by "yes → S-1"; 3a §3.2). S1-A includes the one-line edit in the ask-first `core/profile_database.py`; no agent may sign it.
- Review status: 3 Codex rounds; round 3 = PASS, no findings (`audit/2026-09-25/swarm-2026-09-27/reviews/S01-r3-response.md`).
- Task 1 (write the failing tests, observe RED) may run before the gate. Nothing is committed before the gate.

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In the default development config, no bound SQL parameter reaches any log sink. This covers lab values, chat text, document text, display names, bcrypt hashes and notes.

**Architecture:** Two independent layers, each a one-line change per engine.
- **A.** A new setting, `sql_echo: bool = False` (env `SQL_ECHO`). Both runtime engines use `echo=settings.sql_echo` instead of `echo=settings.debug`. `DEBUG=true` stops turning on SQL logging.
- **B.** Both runtime engines get `hide_parameters=True`. Even an opted-in echo, or any INFO-level `sqlalchemy.engine` logging, prints `[SQL parameters hidden due to hide_parameters=True]` instead of the values.
- **Recommended: A + B.** A removes the default exposure. B covers the opt-in and any logging reconfiguration.

**Tech Stack:** Python 3.11 (D9 venv), SQLAlchemy 2.x async engines (`create_async_engine`, `hide_parameters`), pydantic-settings, pytest + pytest-asyncio (strict mode, `@pytest.mark.asyncio`), FastAPI `TestClient` via `tests/support/routes.py::route_client`.

**Spec:** no spec document exists. The requirement is:
- contract **C-REDACT-3** ("Logs and audit rows MUST NOT contain PHI");
- contract **C-KEY-1** ("Plaintext DEK material MUST NOT be written to disk or logs");
- matrix **PRIV-06**.

The finding and its evidence are in [Finding](#finding-verified-2026-09-27) below.

## Global Constraints

- **Target Python 3.11.** Do not use 3.12-only syntax. This plan adds no timestamps.
- **Ask-first surface.** `core/profile_database.py` is encryption-adjacent (CLAUDE.md §1).
  - The only permitted edit is inside the `create_async_engine(...)` call in `open_profile_database`: `B@7b2ff1f:306-310`.
  - The SQLCipher key hook `set_sqlite_pragma` (`B@7b2ff1f:314-356`), `_key_to_hex` and `_load_encryption_key` are **read-only**.
- **Do not change `debug`.** Its default (`True`), its production force-off (`core/config.py:155-156` B@7b2ff1f) and its other effects stay exactly as they are:
  - `/docs` (`main.py:93-94` B@7b2ff1f);
  - `--reload` (`main.py:173` B@7b2ff1f);
  - llama.cpp `verbose` (`core/llm/llama_cpp_provider.py:136` B@7b2ff1f).

  Option D (default `DEBUG=false`) is **not** proposed. SEC-006 (`tests/security/test_security_remediation.py:340-347` B@7b2ff1f) asserts `debug` stays `True` in development, and it must stay green.
- **Surgical edits only.** Touch only the owned files and hunks listed below.
- **Never relax a guard to make a test pass.** No test in this plan may use `caplog`.
  - Both Alembic `env.py` files call `logging.config.fileConfig(...)`: `migrations/master/env.py:38` and `migrations/profile/env.py:53` B@7b2ff1f.
  - `fileConfig` removes every root handler (caplog's included) and every handler on `sqlalchemy.engine`. A caplog assertion made after a migration ran can only pass.
- **Tests never touch a real master DB.**
  - The module-level master engine's relative sqlite path is made absolute by SQLAlchemy **at import time**. It therefore always points at `<cwd-at-import>/data/<name>.db`, measured below.
  - Tests must not do I/O through `core.database.engine` or `core.database.async_session_maker`.
- **Route tests go through HTTP** via `src/backend/tests/support/routes.py::route_client`.
- **Shell rules** (orchestrator, 2026-09-27):
  - Every bash block starts with `WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail`.
  - `$WT` is absolute. Every `cd` is to an absolute path. There are no relative `cd`s.
- **Baseline sentences (GLOBAL rule).** Any commit that changes the collected count updates **only the collected-count slots** in `CLAUDE.md` and `AGENT.md`, in **that same commit**.
  - Pass-count slots ("all N pass", "N pass in CI", "N−1 without an embedding model") change only with a pass count measured in a named environment. Otherwise they stay as they are and are flagged in the PR.
- **Break-it-on-purpose never edits the phase worktree.** Every deliberate break runs in the disposable detached worktree `BRK=$HOME/s01-break`, which is removed afterwards.
- **No frontend step and no PowerShell block.** This plan is backend-only.
- **Line numbers are labelled with their ref.** `core/database.py`, `core/profile_database.py`, `config/.env.example` and `dev.ps1` are byte-identical on `main@40f590e`, `B@7b2ff1f` and `A@692fdf3`. `core/config.py` differs: B removed one line at `:89`. The executor re-verifies every anchor on the post-P1 start tree (Task 0 Step 4).

## Review Focus

These are the five conditions most likely to bite. Each has a test or a check in the named task.

1. **A developer sets `SQL_ECHO=true` to debug a wrong value and sees `[SQL parameters hidden ...]`.** This is intended (B). The `.env.example` text says so (Task 3 Step 5), and HC-SQLECHO-004 pins it.
2. **SQLAlchemy exception text loses its `[parameters: ...]` part.** `hide_parameters` also applies to `StatementError` messages. This is intended, because those messages reach `logger.error(f"...{e}")` sites. A 2026-09-27 grep of product code at B@7b2ff1f for `[parameters`, `parameters:`, `.params`, `orig.args` and `in str(e` found **0** parsers. Task 4 Step 3 re-runs it.
3. **`DEBUG=false` in the environment.** HC-SQLECHO-002 fails loudly on its precondition by design (measured). 001, 003 and 004 do not depend on the env, because they set `debug` themselves or use `Settings(...)`.
4. **SQLCipher present.** CI and the D9 venv have `sqlcipher3-binary` (`requirements.txt:32` B@7b2ff1f). Then the key hook runs `PRAGMA key` on a raw DBAPI cursor, which SQLAlchemy does not log. HC-SQLECHO-001 asserts the hex key is absent. This is **UNMEASURED with SQLCipher present**: planning measured only without it. Task 1 records `sqlcipher3` availability.
5. **A test writing into a real master DB.** HC-SQLECHO-002 builds a tmp master engine carrying the product engine's logging flags. Task 4 Step 2 proves `src/backend/data/asclexis.db` is untouched.

---

## Finding (verified 2026-09-27)

A read-only security review produced the probe (`secprobe/src/backend/probe_echo.py`, `probe_stderr.txt`, `probe_marks.txt` in the orchestrator's scratchpad). The plan author re-verified every anchor.

| # | Fact | Evidence |
|---|---|---|
| 1 | `debug` defaults to `True` | `core/config.py:28` main@40f590e = B@7b2ff1f; `config/.env.example:14` `DEBUG=true`; `dev.ps1:573` writes `DEBUG=true` into a generated `.env` (all main@40f590e, unchanged in A/B) |
| 2 | Production forces `debug` off | `core/config.py:155-156` B@7b2ff1f (`:156-157` main@40f590e) |
| 3 | Both runtime engines echo when `debug` is on | `core/database.py:46` `echo=settings.debug` (master, module level); `core/profile_database.py:308` `echo=settings.debug` (vault, per open). Same on main, A, B |
| 4 | `hide_parameters` appears nowhere | `git grep hide_parameters` on 40f590e, 7b2ff1f, 692fdf3 → 0 hits |
| 5 | Migration engines do not echo | `core/migrations.py:134,255-257,368,406-408`, `migrations/profile/env.py:153-159` B@7b2ff1f: no `echo=` |
| 6 | Echo reaches **stderr**, not stdout | Echo overrides levels: SQLAlchemy `InstanceLogger` ignores logger levels. `fileConfig(..., disable_existing_loggers=False)` then does two things. (a) It replaces root handlers with `StreamHandler(sys.stderr)` (`alembic.ini:60-62` B@7b2ff1f). (b) It clears handlers on `sqlalchemy.engine`, and on its child `sqlalchemy.engine.Engine`, which removes SQLAlchemy's default stdout handler. The probe's stdout was 0 bytes; its stderr held 251 lines |
| 7 | What leaked (probe, B-tree copy, Windows Py 3.13.7, SQLCipher absent) | `probe_stderr.txt:190` display name + `$2b$12$…` bcrypt hash + salt; `:216` document source; `:220` chunk text (HIV result); `:222` analyte + value; `:224` chat turn; `:237` verify notes + original value JSON. `probe_marks.txt`: `engine.echo=True hide_parameters=False` |
| 8 | No disk sink by default | No product `FileHandler`; `log_file_path` is used only to `mkdir` (`core/database.py:87` B@7b2ff1f). `dev.ps1:718-722` starts the backend hidden **without** redirect. The frontend **is** redirected (`dev.ps1:285`, `:715`). Adding a backend redirect would write every echoed value to disk: latent risk |
| 9 | Nothing catches it today | HC-AUD-007 (`tests/test_audit_phi_minimization.py:317` B@7b2ff1f) uses caplog on `core.audit` only. SEC-006 (`tests/security/test_security_remediation.py:340-347`) asserts `debug` stays True in development |
| 10 | It contradicts docs | `docs/compliance/hipaa-controls.md:71` ("the plaintext app log does not become a second copy"); `docs/compliance/data-privacy.md:47` ("Log files … Contains event metadata, not PHI"). Same line numbers on main and A |
| 11 | **New (plan author):** the master engine's sqlite path is absolute from import | The engine is built at import (`core/database.py:44-48`). `settings.database_url` is relative (`sqlite+aiosqlite:///data\asclexis.db` on Windows), and the aiosqlite dialect resolved it at engine creation. A first draft of HC-SQLECHO-002 did `chdir(tmp)` and still tried to open `<backend>\data\asclexis.db` (`cargs` in the traceback; it failed only because the scratch tree had no `data/`). So a test that used `core.database.engine` would write into a developer's real master DB |

**Also found (out of S-1 scope; reported, not fixed here):**
- `api/profiles.py:328` B@7b2ff1f: `logger.info(f"Created profile: {profile_id} ({profile_data.display_name})")`. It is suppressed only because root is at WARN after Alembic's `fileConfig`.
- `core/llm/llama_cpp_provider.py:136` B@7b2ff1f: `verbose=self._settings.debug`. Whether llama.cpp verbose output includes prompt text is **UNMEASURED**.
- F-P8-3 in the [P08 amendment](2026-09-27-P08-gated-packet-hipaa-aligned-amendment.md) says vault echo was a "static reading; not measured". It is now measured (fact 7, and Task 1 below).

## Measured before writing (context, not targets)

Planning used a scratch extract of **B@7b2ff1f** (`git archive 7b2ff1f src/backend`) under Windows Python 3.13.7, with SQLCipher absent. **Nothing was measured on the post-P1 tree or with the 3.11 venv.** Task 0 and Task 1 re-measure there.

| Step | Result |
|---|---|
| RED: 4 tests on unmodified B | `4 failed`. 001: `AssertionError: PHI reached the SQL log: ['S1ECHO_ANALYTE_hba1c', '731.0419', 'S1ECHO_DOCTEXT HIV-1 RNA detected', 'S1ECHO_CHAT is my result dangerous']`. 002: `AssertionError: PHI reached the SQL log: ['S1ECHO_NAME Jane Doe', '$2b$', 'S1ECHO_NOTE_VIA_HTTP']`. 003: `AttributeError: 'Settings' object has no attribute 'sql_echo'`. 004: `AttributeError: Settings(...) has no attribute 'sql_echo'` |
| A only | `1 failed, 3 passed`. 004 fails with the same PHI list as 001: the true RED for B |
| A + B | `4 passed` |
| Break-its BI-1…BI-5, BI-7 | each red as tabulated in Task 4 |
| Neighbours with A + B | `tests/security tests/test_profile_recovery.py tests/test_profile_deletion.py tests/test_audit_phi_minimization.py` → `146 passed` |
| `-k sqlecho` | `4/1271 tests collected (1267 deselected)` in the scratch tree (4 unrelated collection errors from missing repo-root scripts). The selector matches only the new tests. **Selector check only — never a baseline:** 1271 is a broken scratch extract of B (B collects 1288), not comparable to any collected slot (3b minor 10) |
| Whole-app probe (Task 4 Step 4 script) | **unfixed:** NAME=1 `$2b$`=1 ANALYTE=1 `731.0419`=2 NOTE=1, `sqlalchemy.engine` lines=156. **fixed:** all 0, lines=0. **fixed + `SQL_ECHO=true`:** all 0, `parameters hidden`=69, lines=156 |
| ID collision | `git grep -i "sqlecho\|hc[-_]sql"` on 40f590e, 7b2ff1f, 692fdf3 → 0 hits; no `SQL_ECHO` anywhere |

---

## Approval scope

**There is no owner decision for S-1.** [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md) contains no row about SQL echo, `debug` or logging. The P08 amendment explicitly excludes it: "8. Fixing the debug SQL-echo finding (F-P8-3 below). Report it; do not fix it in this phase."

**Proposed change, for the owner to approve verbatim (sign-offs S1-A and S1-B below):**

> **S1-A.** "In `src/backend/core/config.py`, add `sql_echo: bool = False` (env `SQL_ECHO`) directly below `debug`. In `src/backend/core/database.py` (master engine) and in `src/backend/core/profile_database.py` (vault engine: only inside the `create_async_engine(...)` call in `open_profile_database`, not the SQLCipher key hook), change `echo=settings.debug` to `echo=settings.sql_echo`. Document `SQL_ECHO=false` in `config/.env.example`. Add `src/backend/tests/security/test_sql_echo_phi.py` (HC-SQLECHO-001…003) and update the collected-count slots in `CLAUDE.md` and `AGENT.md`. `DEBUG` keeps its default and every other effect."
>
> **S1-B.** "In the same two `create_async_engine(...)` calls, add `hide_parameters=True`. Add HC-SQLECHO-004. Extend the `config/.env.example` comment to say bound values are never printed. Update the collected-count slots."

**Neither line licenses:**
1. Changing `DEBUG`'s default, its production force-off, or `dev.ps1` / `.env.example` `DEBUG=` values (option D).
2. Any other line of `core/profile_database.py`: the key hook, `_key_to_hex`, key loading, the connection pool or `close()`.
3. The migration engines (`core/migrations.py`, `migrations/*/env.py`) or `alembic.ini` logging config, including removing or changing Alembic's `fileConfig`.
4. Adding a log file, a `FileHandler`, a logging config, or a `dev.ps1` stderr redirect for the backend.
5. Forcing `sql_echo` off in production. With B in place, an opted-in production echo prints statements without values; forcing it off is a separate choice.
6. Other PHI-in-log surfaces:
   - `api/profiles.py:328` (display name at INFO);
   - `modules/notification_scheduler.py` (≈:517-520, `medication_name`; plan 02);
   - `core/audit.py:257-264` B@7b2ff1f (P8 brief option D);
   - llama.cpp `verbose`.
7. Editing the contract, the matrix, `docs/compliance/*`, the P08 packet or `docs/features/TASK_LIST.md`. The orchestrator owns those (see [Docs that change truth value](#docs-that-change-truth-value-orchestrator-edits-them)).

## Traceability

| Kind | ID | Verified text (grep, 2026-09-27) | Effect of this plan |
|---|---|---|---|
| Contract | **C-REDACT-3 · PROPOSED** ([contract](../capstone-report/architecture-engineering-contract.md) `:196-202`) | "Logs and audit rows MUST NOT contain PHI (medication names, values, document text); use UUIDs." | Closes the SQL-echo surface. Adds `tests/security/test_sql_echo_phi.py` as enforcement |
| Contract | **C-KEY-1 · BINDING (ask-first)** (`:77-86`) | "Plaintext DEK material MUST NOT be written to disk or logs." | HC-SQLECHO-001 asserts the hex key never reaches the SQL log. The edit sits beside `core/profile_database.py:315-356` (ask-first) |
| Contract | **C-GATE-3 · BINDING** (`:360-366`) | "Staging MUST use explicit task-owned pathspecs…" | Commit plan |
| Matrix | **PRIV-06** ([matrix](../capstone-report/specs-compliance-matrix.md) `:89`) | "No PHI in logs or audit rows … **partial**: plan 02 reports `medication_name` at INFO…" | New evidence HC-SQLECHO-001…004. Status stays **partial** (plan 02 item and `api/profiles.py:328` remain) |
| Matrix | KEY-01 (`:58`) | "Each vault is SQLCipher-encrypted and fails closed" | Unchanged; the key hook is not touched |
| Handoff | [§5](../../audit/2026-09-25/handoff-2026-09-27-execution.md) | no W-row covers S-1 (W-1…W-11 checked) | New item; the orchestrator adds a row |
| Related | [P08 amendment](2026-09-27-P08-gated-packet-hipaa-aligned-amendment.md) F-P8-3, brief option D | "Stop plaintext echo surfaces: the `core/audit.py:257-264` echo and debug SQL echo (F-P8-3)" | S-1 delivers the SQL-echo half of option D |

## Files

| File | Action | Hunk | Task |
|---|---|---|---|
| `src/backend/tests/security/test_sql_echo_phi.py` | **create** | new; 001–003 in Task 1, 004 appended in Task 3 | 1, 3 |
| `src/backend/core/config.py` | modify | +4 lines after `debug: bool = True` (`:28` B@7b2ff1f) | 2 |
| `src/backend/core/database.py` | modify | `:46` echo flag (A); +1 line after it (B) | 2, 3 |
| `src/backend/core/profile_database.py` | modify (**ask-first**) | `:308` echo flag (A); +1 line after it (B); nothing else | 2, 3 |
| `config/.env.example` | modify | +4 lines after `DEBUG=true` (`:14`) (A); +1 comment line (B) | 2, 3 |
| `CLAUDE.md`, `AGENT.md` | modify | collected-count slots only | 2, 3 |
| `docs/plans/2026-09-27-S01-sql-echo-phi-leak.md` (this file) | modify | "Execution record" section only | 5 |

**Read-only, and asserted unchanged by `git diff --exit-code` in Task 4:**
- `src/backend/core/security.py`, `src/backend/core/auth.py`, `src/backend/core/migrations.py`, `src/backend/migrations/`, `src/backend/alembic.ini`;
- `src/backend/modules/redaction.py`, `interpret_safety.py`, `faithfulness.py`, `verifier_agent.py`;
- `src/backend/tests/support/routes.py`, `dev.ps1`.

### Shared-file ordering

| File | Order | Why |
|---|---|---|
| `core/config.py` | P1 (B −1 line at `:89`) → **S-1** → P4-core (N7 comment at `:108` B@7b2ff1f, comment-only; [P04 amendment](2026-09-27-P04-doc-drift-sweep-amendment.md)) → W-8 (adds `embedding_model_path` near `:111-112`) | S-1 inserts 4 lines at `:29`, so P4 and W-8 anchors shift by +4. Both re-anchor by grep. W-6 does not touch this file |
| `core/database.py` | P1 → **S-1** → P6 (`install_sqlite_foreign_keys` listener after `:48`; [plan 06](../../audit/2026-09-25/plans/06-sql-fk-audit.md) Task 3) | Adjacent hunks. P6's anchor moves +1 |
| `core/profile_database.py` | P1 → **S-1** → P6 (listener after `:356`, beside the key hook) | Both are ask-first. **S-1 must land before P6**, or wait until P6 merges and re-anchor; never concurrently |
| `config/.env.example` | P1 → **S-1** (`:15-19`) → P4-core Task 3 (`:92-99`) → W-8 (`:82-84`) | Different blocks; anchors below `:14` shift by +5 |
| `CLAUDE.md`, `AGENT.md` baseline slots | serialize with every phase that changes the collected count (P2, P5, P6, P7, W-*) | CLAUDE.md §4 "update it in the same commit" |

**Proposed position (plan author's recommendation):** **P1 → S-1 → P2 → …**. It runs as early as possible after P1, because it is a live PHI exposure in the default dev config, and certainly before P6.
- If the owner has not signed when P2 is ready, P2 goes first. S-1 then runs in the next gap where no other phase has its files open, and Task 0 re-measures.

## Dependencies

- **P0-B, P1:** post-P1 tree (ancestry check in Task 0).
- **D9:** the 3.11 venv `~/venvs/asclexis-311`.
- **Owner:** S1-A gates Task 2. S1-B gates Task 3. No D-decision covers S-1.
- No dependency on P2–P8 or W-*. Ordering constraints are in the table above.

---

## Task 0: Preconditions, owner gate and phase-start measurement

**Files:** none modified.

- [ ] **Step 1: Create the worktree and prove it is post-P1**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral fetch origin
git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree add "$WT" -b fix/s01-sql-echo-phi origin/main
cd "$WT"
git merge-base --is-ancestor 7b2ff1f HEAD && git merge-base --is-ancestor 692fdf3 HEAD && echo post-P1-ok
git rev-parse HEAD
"$PY" --version
"$PY" -c "import sqlcipher3; print('sqlcipher3 present')" || echo "sqlcipher3 absent"
```
Expected output:
- `post-P1-ok`;
- a SHA (record it as `START`);
- `Python 3.11.x`;
- `sqlcipher3 present` or `absent` (record it as `CIPHER0`).

**STOP** if any of these holds:
- `worktree add` fails (ask before removing anything);
- `post-P1-ok` is missing;
- the venv is missing.

- [ ] **Step 2: Owner gate**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
grep -nE '^- \[x\] \*\*S1-(A|B)' "$WT/docs/plans/2026-09-27-S01-sql-echo-phi-leak.md" || echo "S1 unsigned"
```
Expected: the signed lines, or `S1 unsigned`.
- `S1 unsigned`: you may do **Task 1 only**, without committing, then **STOP**.
- S1-A signed but not S1-B: do Tasks 1, 2, 4 and 5, and skip Task 3. Record "B not approved" in the PR.
- The plan file itself is missing from `$WT`: **STOP**. The owner-approved docs commit of the 2026-09-27 plan set has not landed on main (see Prerequisites). Do not commit the plan yourself.

- [ ] **Step 3: Confirm the IDs and the file name are free**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
git -C "$WT" grep -n -i -E "sqlecho|hc[-_]sql|SQL_ECHO|sql_echo|hide_parameters" -- src/ config/ || echo no-collision
test ! -e "$WT/src/backend/tests/security/test_sql_echo_phi.py" && echo file-free
```
Expected: `no-collision` and `file-free`.
- **STOP** on any hit. Someone may already have fixed or partly fixed S-1; re-plan from what is there.

- [ ] **Step 4: Re-verify the anchors on this tree** (record the actual line numbers)

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
grep -n "    debug: bool = True" "$WT/src/backend/core/config.py"
grep -n "echo=settings.debug" "$WT/src/backend/core/database.py" "$WT/src/backend/core/profile_database.py"
grep -n "def set_sqlite_pragma\|PRAGMA key" "$WT/src/backend/core/profile_database.py"
grep -n "^DEBUG=true" "$WT/config/.env.example"
grep -n "fileConfig(config.config_file_name" "$WT/src/backend/migrations/master/env.py" "$WT/src/backend/migrations/profile/env.py"
grep -n "def route_client\|master_db\|dependency_overrides" "$WT/src/backend/tests/support/routes.py"
grep -nE "[0-9]{4} backend tests collected|differs from|[0-9]{4} collected;" "$WT/CLAUDE.md" "$WT/AGENT.md"
```
Expected:
- `debug: bool = True` is found once in `core/config.py`.
- `echo=settings.debug` is found exactly **once in each** engine file.
- `set_sqlite_pragma` and `PRAGMA key` are found in `profile_database.py`, **below** the echo line.
- `DEBUG=true` is found once in `config/.env.example`.
- Both `fileConfig` lines are found.
- `route_client` takes `router, prefix, profile_id, master_db` and overrides only `require_auth` and `get_db`. If P7 changed the signature, adapt the *calls* in Task 1; never edit the helper.
- The count lines are located. Record the collected-count slots as `COLLECTED_SLOTS` ("**N backend tests collected.**", "differs from … N,", "(N collected;") and the pass-count slots as `PASS_SLOTS`.

**STOP** if any echo count ≠ 1 per file, or if the key hook now sits inside the `create_async_engine` call.

- [ ] **Step 5: Measure the start tree**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
find "$WT/src/backend" -name __pycache__ -type d -prune -exec rm -rf {} +
"$PY" -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1
"$PY" -m pytest tests/ -p no:cacheprovider -q -rfEsxX 2>&1 | tail -30; echo "pytest-exit=$?"
```
Record verbatim:
- interpreter, OS, `START` SHA, `CIPHER0`;
- **N0** = collected;
- **F0** = failing node IDs;
- **S0** = skipped;
- `pytest-exit`;
- **ENV0** = embedding model present or absent (`test_api_rag_index_002b` PASSED or FAILED).

If any figure in `COLLECTED_SLOTS` ≠ N0, **STOP**. An earlier phase left the baseline stale; report it and do not fix it here. (Program rule **SLOT-RULE**, proposed in 3a B-4: every collection-changing phase updates the slots in the same commit; a stale slot here names that phase's miss.) (At B@7b2ff1f, `AGENT.md:76` says 1269 while `CLAUDE.md:30` says 1288. P1 is expected to reconcile them.)

- [ ] **Step 6: Reproduce the leak on the start tree (whole app)**

Write the probe **outside the repo**:

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
mkdir -p "$HOME/s01-probe/out-start" "$HOME/s01-probe/out-end" "$HOME/s01-probe/out-end-echo"
cat > "$HOME/s01-probe/s01_probe.py" <<'EOF'
"""S-1 whole-app probe. Never committed. Usage: python s01_probe.py <backend_dir> <out_dir>"""
import os, sys, tempfile, uuid
backend, out = sys.argv[1], sys.argv[2]
os.environ.setdefault("DATABASE_ENCRYPTION_REQUIRED", "false")
os.environ["API_RATE_LIMIT_ENABLED"] = "false"
os.environ["AUTH_RATE_LIMIT_ENABLED"] = "false"
os.chdir(tempfile.mkdtemp(prefix="s01probe-"))  # app data lands here, never in a checkout
sys.path.insert(0, backend)
from datetime import datetime
from fastapi.testclient import TestClient
import main
from core.config import settings
from core.profile_database import get_profile_db_manager
from models.document import Document
from models.observation import Observation

marks = open(os.path.join(out, "probe_marks.txt"), "w")
marks.write(f"cwd={os.getcwd()} debug={settings.debug} sql_echo={getattr(settings, 'sql_echo', 'ABSENT')}\n")
with TestClient(main.app) as c:
    r = c.post("/api/v1/profiles/", json={"display_name": "S1PROBE_NAME Jane Doe", "password": "S1probe-Pass-123"})
    marks.write(f"create={r.status_code}\n")
    tok, pid = r.json()["access_token"], r.json()["profile_id"]
    conn = get_profile_db_manager().get_connection(pid)
    marks.write(f"vault echo={conn.engine.sync_engine.echo} hide_parameters={conn.engine.sync_engine.hide_parameters}\n")
    doc_id, obs_id = str(uuid.uuid4()), str(uuid.uuid4())
    async def seed():
        async with conn.session_maker() as s:
            s.add(Document(id=doc_id, profile_id=pid, path_hash="a" * 64, content_hash="b" * 64, doc_type="lab",
                           source="s1probe.pdf", status="parsed", imported_at=datetime(2026, 9, 27)))
            await s.flush()
            s.add(Observation(id=obs_id, profile_id=pid, doc_id=doc_id, analyte_canonical="hba1c",
                              analyte_raw="S1PROBE_ANALYTE", value=731.0419, unit="%", collected_at=datetime(2026, 9, 1)))
            await s.commit()
    c.portal.call(seed)
    r = c.post(f"/api/v1/observations/{obs_id}/verify", headers={"Authorization": f"Bearer {tok}"},
               json={"value": 7.77, "notes": "S1PROBE_NOTE"})
    marks.write(f"verify={r.status_code}\n")
marks.close()
EOF
cat > "$HOME/s01-probe/count.sh" <<'EOF'
#!/usr/bin/env bash
# Usage: count.sh <out_dir> — prints sentinel hit counts in that run's stderr
set -o pipefail
cat "$1/probe_marks.txt"
for s in S1PROBE_NAME '$2b$' S1PROBE_ANALYTE 731.0419 S1PROBE_NOTE 'parameters hidden'; do
  printf '%s=%s ' "$s" "$(grep -c -F -- "$s" "$1/stderr.txt")"
done
printf '\nengine-lines=%s\n' "$(grep -c 'sqlalchemy.engine' "$1/stderr.txt")"
EOF
chmod +x "$HOME/s01-probe/count.sh"
env -u SQL_ECHO -u DEBUG "$PY" "$HOME/s01-probe/s01_probe.py" "$WT/src/backend" "$HOME/s01-probe/out-start" 2> "$HOME/s01-probe/out-start/stderr.txt"; echo "probe-exit=$?"
"$HOME/s01-probe/count.sh" "$HOME/s01-probe/out-start"
git -C "$WT" status --porcelain
```
Expected, as measured on Windows 3.13.7 / B tree. Post-P1 3.11 is UNMEASURED until now.
- `probe-exit=0`.
- `debug=True sql_echo=ABSENT`, `create=201`, `vault echo=True hide_parameters=False`, `verify=200`.
- Every sentinel count ≥ 1 (measured: NAME=1, `$2b$`=1, ANALYTE=1, `731.0419`=2, NOTE=1); `parameters hidden=0`.
- `engine-lines` > 0 (measured 156).
- `git status --porcelain` is empty: the probe wrote nothing into the worktree.

**STOP** if any sentinel count is 0. The leak did not reproduce, so the premise is wrong on this tree; report and re-plan. If the probe crashes, record the error and **STOP**.

---

## Task 1: Write HC-SQLECHO-001…003 and observe RED (allowed before the gate; do not commit)

**Files:**
- Create: `src/backend/tests/security/test_sql_echo_phi.py`

**Interfaces:**
- Consumes:
  - `core.profile_database.get_profile_db_manager() -> PerProfileDatabaseManager`, with `open_profile_database(profile_id: str, password: str) -> ProfileDatabaseConnection`, `close_profile_database(profile_id)`, `get_connection(profile_id)` and `_key_to_hex(key: bytes) -> str`;
  - `ProfileDatabaseConnection.engine: AsyncEngine`, `.session_maker` and `._encryption_key`;
  - `core.security.seal_key_with_dpapi(key, fallback_password=..., force_password=True) -> (bytes, str)`;
  - `core.migrations.run_master_migrations() -> None`;
  - `tests.support.routes.route_client(router, prefix, profile_id="profile-a", master_db=None)`;
  - `core.auth.Session`, `core.auth.require_auth`.
- Produces:
  - the helpers `_Capture`, `_SqlLogTap`, `_assert_absent`, `_make_vault(root, profile_id)` and `async _seed_vault(conn, profile_id) -> obs_id: str`;
  - the fixture `data_root`.

  Task 3 appends HC-SQLECHO-004, which uses `_Capture`, `_make_vault`, `_seed_vault` and `data_root`.

**What each test would fail to notice** (answered before writing):

| Test | Blind spot | Covered by |
|---|---|---|
| 001 vault | the master engine; values logged by non-SQLAlchemy loggers; the key hook if SQLCipher is absent (the PRAGMA then never runs) | 002, 003 and 004 (master); out of scope (other loggers); CIPHER0 recorded, UNMEASURED without SQLCipher |
| 002 HTTP | it mirrors the product master engine's `echo` and `hide_parameters` onto a tmp engine, so a *new* logging kwarg on the product engine would not be mirrored | 003 and 004 assert the product engine's flags structurally |
| 003 config | behaviour (it is structural only) | 001 and 002 |
| any | a capture detached by `fileConfig` | every test asserts a canary, or a positive SQL line, before trusting an empty result |

- [ ] **Step 1: Write the test file**

```python
"""S-1 — SQL echo must never print bound PHI.

With the default development config (DEBUG=true) both runtime engines were
created with ``echo=settings.debug``. SQLAlchemy then logged every statement
**with its bound parameters**: lab values, chat text, document text, display
names and bcrypt hashes reached stderr.

Why not ``caplog``: both Alembic ``env.py`` files call
``logging.config.fileConfig``, which removes every root handler (caplog's
included) and every handler on ``sqlalchemy.engine``. A caplog assertion made
after a migration ran can only pass. These tests capture in ways fileConfig
cannot undo, and each proves its capture is still alive (a canary) before
trusting an empty result.

Test IDs: HC-SQLECHO-001..004.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import APIRouter

import core.database as core_db
from core.config import Settings, settings
from core.profile_database import get_profile_db_manager
from core.security import generate_encryption_key, seal_key_with_dpapi

PASSWORD = "S1echo-Pass-123!"
SENT_ANALYTE = "S1ECHO_ANALYTE_hba1c"
SENT_VALUE = 731.0419  # repr appears verbatim in echoed params
SENT_DOCTEXT = "S1ECHO_DOCTEXT HIV-1 RNA detected"
SENT_CHAT = "S1ECHO_CHAT is my result dangerous"
SENT_NAME = "S1ECHO_NAME Jane Doe"
SENT_NOTE = "S1ECHO_NOTE_VIA_HTTP"
CANARY = "S1ECHO_CANARY"


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


class _SqlLogTap:
    """Record every ``sqlalchemy.*`` record that reaches ``Logger.handle``.

    Patched on the Logger class, so a fileConfig run in the middle of a request
    (the vault open inside profile creation runs the profile migration) cannot
    detach it. Anything recorded here was on its way to a real sink.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.lines: list[str] = []
        original = logging.Logger.handle
        tap = self

        def handle(logger_self: logging.Logger, record: logging.LogRecord):
            if record.name.startswith("sqlalchemy") and not logger_self.disabled:
                tap.lines.append(record.getMessage())
            return original(logger_self, record)

        monkeypatch.setattr(logging.Logger, "handle", handle)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def _assert_absent(text: str, needles: list[str]) -> None:
    leaked = [n for n in needles if n in text]
    assert not leaked, f"PHI reached the SQL log: {leaked}"


def _make_vault(root: Path, profile_id: str) -> None:
    vault = root / "vaults" / profile_id
    vault.mkdir(parents=True)
    # Test fixture: password seal keeps the test deterministic on every OS.
    sealed, method = seal_key_with_dpapi(
        generate_encryption_key(), fallback_password=PASSWORD, force_password=True
    )
    (vault / "key.bin").write_bytes(sealed)
    (vault / "key.method").write_text(method)


async def _seed_vault(conn, profile_id: str) -> str:
    from models.chat_session import ChatSession, ChatTurn
    from models.chunk import Chunk
    from models.document import Document
    from models.observation import Observation

    doc_id, obs_id, sess_id = (str(uuid.uuid4()) for _ in range(3))
    async with conn.session_maker() as s:
        s.add(Document(id=doc_id, profile_id=profile_id, path_hash="a" * 64,
                       content_hash="b" * 64, doc_type="lab", source="s1echo.pdf",
                       status="parsed", imported_at=datetime(2026, 9, 27)))
        await s.flush()
        s.add(Chunk(id=str(uuid.uuid4()), doc_id=doc_id, chunk_index=0, text=SENT_DOCTEXT))
        s.add(Observation(id=obs_id, profile_id=profile_id, doc_id=doc_id,
                          analyte_canonical="hba1c", analyte_raw=SENT_ANALYTE,
                          value=SENT_VALUE, unit="%", collected_at=datetime(2026, 9, 1)))
        s.add(ChatSession(id=sess_id, profile_id=profile_id, title="t"))
        await s.flush()
        s.add(ChatTurn(id=str(uuid.uuid4()), session_id=sess_id, profile_id=profile_id,
                       turn_index=0, role="user", content=SENT_CHAT))
        await s.commit()
    return obs_id


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: root))
    return root


@pytest.mark.asyncio
async def test_hc_sqlecho_001_vault_writes_do_not_echo_phi(data_root, monkeypatch):
    """Default dev config (debug on): vault row values and the key never reach the SQL log."""
    monkeypatch.setattr(settings, "debug", True)  # the configuration that leaked
    mgr = get_profile_db_manager()
    pid = str(uuid.uuid4())
    _make_vault(data_root, pid)

    conn = await mgr.open_profile_database(pid, PASSWORD)  # runs fileConfig
    cap = _Capture()
    sa_logger = logging.getLogger("sqlalchemy.engine")
    sa_logger.addHandler(cap)  # attached AFTER the migration's fileConfig
    try:
        hex_key = mgr._key_to_hex(conn._encryption_key)
        await _seed_vault(conn, pid)
        await conn.engine.dispose()  # next query opens a new connection -> key hook
        async with conn.session_maker() as s:
            from sqlalchemy import text
            await s.execute(text("SELECT count(*) FROM observations"))
        logging.getLogger("sqlalchemy.engine.Engine").warning(CANARY)
    finally:
        sa_logger.removeHandler(cap)
        await mgr.close_profile_database(pid)

    assert CANARY in cap.text, "capture handler was detached; result would be vacuous"
    _assert_absent(cap.text, [SENT_ANALYTE, repr(SENT_VALUE), SENT_DOCTEXT, SENT_CHAT, hex_key])
    assert conn.engine.sync_engine.echo is False  # built from sql_echo, not debug


def test_hc_sqlecho_002_http_create_and_verify_do_not_echo_phi(data_root, monkeypatch):
    """Master + vault engines through HTTP: display name, bcrypt hash, notes stay out.

    The module-level master engine is NOT used for I/O: SQLAlchemy resolves its
    relative sqlite path to an absolute one at import time, so it always points
    at <cwd-at-import>/data/<name>.db, a developer's real master DB. A tmp
    engine is built with the product engine's own logging flags instead.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from api.observations import router as observations_router
    from api.profiles import router as profiles_router
    from core.auth import Session, require_auth
    from core.migrations import run_master_migrations
    from tests.support.routes import route_client

    assert settings.debug is True, (
        "precondition: this test proves the default dev config (DEBUG unset/true) "
        "does not leak; with DEBUG=false it would pass without testing anything"
    )
    run_master_migrations()  # tmp master DB via the patched app_data_path; runs fileConfig
    master_file = data_root / settings.master_db_filename
    assert master_file.exists()
    product = core_db.engine.sync_engine
    tmp_engine = create_async_engine(
        f"sqlite+aiosqlite:///{master_file}",
        echo=product.echo,
        hide_parameters=product.hide_parameters,
    )
    master_session = async_sessionmaker(tmp_engine, class_=AsyncSession,
                                        expire_on_commit=False)()
    tap = _SqlLogTap(monkeypatch)

    parent = APIRouter()
    parent.include_router(profiles_router, prefix="/profiles")
    parent.include_router(observations_router, prefix="/observations")
    mgr = get_profile_db_manager()
    pid = None

    with route_client(parent, "/api/v1", master_db=master_session) as client:
        try:
            r = client.post("/api/v1/profiles/",
                            json={"display_name": SENT_NAME, "password": PASSWORD})
            assert r.status_code == 201, r.text
            pid = r.json()["profile_id"]

            async def _auth() -> Session:
                return Session(profile_id=pid, profile_name="T",
                               expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                               token_jti="jti-test")

            client.app.dependency_overrides[require_auth] = _auth
            obs_id = client.portal.call(_seed_vault, mgr.get_connection(pid), pid)
            r = client.post(f"/api/v1/observations/{obs_id}/verify",
                            json={"value": 7.77, "notes": SENT_NOTE})
            assert r.status_code == 200, r.text
            logging.getLogger("sqlalchemy.engine.Engine").warning(CANARY)
        finally:
            client.portal.call(master_session.close)
            if pid is not None:
                client.portal.call(mgr.close_profile_database, pid)
            client.portal.call(tmp_engine.dispose)

    assert CANARY in tap.text, "log tap was detached; result would be vacuous"
    _assert_absent(tap.text, [SENT_NAME, "$2b$", SENT_NOTE])


def test_hc_sqlecho_003_sql_echo_is_decoupled_from_debug(monkeypatch):
    """SQL echo is its own opt-in; debug=True no longer turns it on."""
    monkeypatch.delenv("SQL_ECHO", raising=False)
    s = Settings(app_env="development", debug=True)
    assert s.debug is True
    assert s.sql_echo is False
    monkeypatch.setenv("SQL_ECHO", "true")
    assert Settings(app_env="development").sql_echo is True
    assert core_db.engine.sync_engine.echo is False  # master engine built from sql_echo
```

Why each design choice:
- **Handler after the vault opens (001).** The migration's `fileConfig` has already run, and nothing after it reconfigures logging. A canary proves the handler is still attached.
- **`Logger.handle` tap (002).** Profile creation opens the vault **inside the request**, which runs `fileConfig` mid-test and would strip any handler. The class-level patch cannot be stripped. monkeypatch restores it.
- **`debug` precondition (002).** CI does not set `DEBUG` (`scripts/run-backend-tests.sh`, `.github/workflows/ci.yml` B@7b2ff1f), so `settings.debug` is `True` there. A `DEBUG=false` environment fails loudly instead of passing vacuously (measured).
- **Tmp master engine (002).** See Global Constraints and Finding #11.

- [ ] **Step 2: Run and observe RED**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
env -u SQL_ECHO -u DEBUG "$PY" -m pytest tests/security/test_sql_echo_phi.py -p no:cacheprovider -q -k sqlecho 2>&1 | grep -E "^E   *(AssertionError|AttributeError)|^FAILED|passed|failed"
git -C "$WT" status --porcelain
```
Expected (measured on Windows 3.13.7 / B tree):
- `3 failed`;
- 001: `AssertionError: PHI reached the SQL log: ['S1ECHO_ANALYTE_hba1c', '731.0419', 'S1ECHO_DOCTEXT HIV-1 RNA detected', 'S1ECHO_CHAT is my result dangerous']`;
- 002: `AssertionError: PHI reached the SQL log: ['S1ECHO_NAME Jane Doe', '$2b$', 'S1ECHO_NOTE_VIA_HTTP']`;
- 003: `AttributeError: 'Settings' object has no attribute 'sql_echo'`;
- `git status` shows only `?? src/backend/tests/security/test_sql_echo_phi.py`.

Record the output as RED evidence. If `CIPHER0` = present and 001's list also contains a 64-hex key, record it: that would be a **new** key-exposure finding. **STOP** and report it before continuing.

**STOP** if:
- a test fails for a different reason (for example a fixture error, 500 or 403). Use `systematic-debugging`; never weaken an assertion;
- a test **passes**. The premise is wrong on this tree.

- [ ] **Step 3: Do not commit.** If S1-A is unsigned, **STOP** here and leave the file untracked in `$WT`.

---

## Task 2: Option A — `sql_echo` setting, both engines use it (GATED: S1-A)

**Files:**
- Modify: `src/backend/core/config.py` (after `debug: bool = True`, `:28` B@7b2ff1f)
- Modify: `src/backend/core/database.py:46`
- Modify: `src/backend/core/profile_database.py:308` (**ask-first**; this line only)
- Modify: `config/.env.example` (after `:14`)
- Modify: `CLAUDE.md`, `AGENT.md` (collected-count slots)
- Test: `src/backend/tests/security/test_sql_echo_phi.py` (from Task 1)

**Interfaces:**
- Produces: `Settings.sql_echo: bool = False` (env `SQL_ECHO`); both engines have `echo == settings.sql_echo`.

- [ ] **Step 1: Confirm S1-A is signed** (Task 0 Step 2). Otherwise **STOP**.

- [ ] **Step 2: Implement A**

`src/backend/core/config.py`: insert directly below `    debug: bool = True`:
```python
    # SQL statement logging. Separate from `debug` on purpose (S-1): echo printed
    # every bound parameter (lab values, chat text, names) to stderr. Opt in with
    # SQL_ECHO=true.
    sql_echo: bool = False
```

`src/backend/core/database.py`: in the module-level `create_async_engine(...)`:
```python
    echo=settings.sql_echo,
```
(replaces `    echo=settings.debug,`)

`src/backend/core/profile_database.py`: in `open_profile_database`'s `create_async_engine(...)` call only:
```python
                echo=settings.sql_echo,
```
(replaces `                echo=settings.debug,`)

`config/.env.example`: insert after the `DEBUG=true` line one empty line, then these 3 lines (no trailing spaces):
```
# SQL statement logging (default false). Separate from DEBUG since S-1:
# DEBUG=true no longer prints SQL.
SQL_ECHO=false
```

- [ ] **Step 3: Prove the diff is surgical**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
git diff -U0 -- src/backend/core/profile_database.py | grep -E '^[-+][^-+]'
git diff -U0 -- src/backend/core/database.py | grep -E '^[-+][^-+]'
git diff --stat
grep -rn "echo=settings.debug" "$WT/src/backend" --include=*.py || echo no-debug-echo
```
Expected:
- `profile_database.py`: exactly `-                echo=settings.debug,` and `+                echo=settings.sql_echo,`.
- `database.py`: exactly `-    echo=settings.debug,` and `+    echo=settings.sql_echo,`.
- `--stat` lists exactly 4 files: `config/.env.example`, `core/config.py`, `core/database.py`, `core/profile_database.py`. The test file is untracked.
- `no-debug-echo`.

**STOP** if `profile_database.py` shows any other changed line.

- [ ] **Step 4: Run GREEN**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
env -u SQL_ECHO -u DEBUG "$PY" -m pytest tests/security/test_sql_echo_phi.py tests/security/test_security_remediation.py -p no:cacheprovider -q 2>&1 | grep -E "^FAILED|passed|failed"
```
Expected: no `FAILED` line. The count is 3 new plus the SEC-006 file's count; record it. SEC-006 `test_development_debug_stays_on` must pass: `debug` is unchanged.

- [ ] **Step 5: Update the collected-count slots (+3)**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
N1=$("$PY" -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1 | grep -oE '^[0-9]+'); echo "N1=$N1"
"$PY" - "$WT" "<N0>" "$N1" <<'EOF'
import pathlib, re, sys
wt, old, new = sys.argv[1:]
assert int(new) == int(old) + 3, (old, new)
subs = {
    "CLAUDE.md": [(rf"\*\*{old} backend tests collected\.\*\*", f"**{new} backend tests collected.**"),
                  (rf"(differs from\s+){old},", rf"\g<1>{new},")],
    "AGENT.md": [(rf"\({old} collected;", f"({new} collected;")],
}
for name, pairs in subs.items():
    p = pathlib.Path(wt, name)
    s = p.read_text(encoding="utf-8")
    for pat, rep in pairs:
        s, n = re.subn(pat, rep, s)
        assert n == 1, (name, pat, n)
    p.write_text(s, encoding="utf-8")
print("collected slots", old, "->", new)
EOF
git -C "$WT" diff -U0 -- CLAUDE.md AGENT.md | grep -E '^[-+][^-+]'
```
Replace `<N0>` with the Task 0 figure.

Expected:
- `N1` = N0 + 3;
- `collected slots N0 -> N1`;
- the diff changes only collected-count slots.

**STOP** if:
- an `assert` fires (a slot's wording differs from Task 0 Step 4); fix the pattern to the recorded wording and never hand-edit a pass slot;
- N1 ≠ N0 + 3.

- [ ] **Step 6: Commit A** (explicit pathspecs; C-GATE-3)

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
git add -- src/backend/core/config.py src/backend/core/database.py src/backend/core/profile_database.py src/backend/tests/security/test_sql_echo_phi.py config/.env.example CLAUDE.md AGENT.md
git diff --cached --name-only
git commit -m "fix(db): decouple SQL echo from DEBUG so dev mode stops printing PHI (S-1)

Both runtime engines used echo=settings.debug, and debug defaults to true in
development, so every bound parameter (lab values, chat text, document text,
display names, bcrypt hashes) was logged to stderr. New SQL_ECHO setting,
default false. HC-SQLECHO-001..003. Owner sign-off S1-A."
```
Expected `--cached` list, exactly 7 paths: `AGENT.md`, `CLAUDE.md`, `config/.env.example`, `src/backend/core/config.py`, `src/backend/core/database.py`, `src/backend/core/profile_database.py`, `src/backend/tests/security/test_sql_echo_phi.py`. Any other path → unstage it (`git restore --staged -- <path>`) and **STOP**.

---

## Task 3: Option B — `hide_parameters=True` on both engines (GATED: S1-B)

**Files:**
- Modify: `src/backend/core/database.py` (+1 line after `echo=settings.sql_echo,`)
- Modify: `src/backend/core/profile_database.py` (+1 line after `echo=settings.sql_echo,`; **ask-first**)
- Modify: `config/.env.example` (+1 comment line)
- Modify: `CLAUDE.md`, `AGENT.md` (collected-count slots)
- Test: append HC-SQLECHO-004 to `src/backend/tests/security/test_sql_echo_phi.py`

**Interfaces:**
- Consumes: `_Capture`, `_make_vault`, `_seed_vault` and `data_root` (Task 1); `Settings.sql_echo` (Task 2).
- Produces: both engines have `hide_parameters is True`.

**What HC-SQLECHO-004 would fail to notice:** loggers outside `sqlalchemy.engine`, and the master engine's *behaviour* (it asserts the master's flag structurally, because that engine is built at import). 002 covers master behaviour for the default config.

- [ ] **Step 1: Confirm S1-B is signed.** Otherwise skip to Task 4 and record "B not approved".

- [ ] **Step 2: Append the failing test**

```python


@pytest.mark.asyncio
async def test_hc_sqlecho_004_opt_in_echo_still_hides_parameters(data_root, monkeypatch):
    """A developer who sets SQL_ECHO=true sees SQL text, never bound values."""
    monkeypatch.setattr(settings, "debug", True)
    monkeypatch.setattr(settings, "sql_echo", True)
    mgr = get_profile_db_manager()
    pid = str(uuid.uuid4())
    _make_vault(data_root, pid)

    conn = await mgr.open_profile_database(pid, PASSWORD)
    cap = _Capture()
    sa_logger = logging.getLogger("sqlalchemy.engine")
    sa_logger.addHandler(cap)
    try:
        await _seed_vault(conn, pid)
    finally:
        sa_logger.removeHandler(cap)
        await mgr.close_profile_database(pid)

    assert "INSERT INTO observations" in cap.text, "echo is off; this test proves nothing"
    _assert_absent(cap.text, [SENT_ANALYTE, repr(SENT_VALUE), SENT_DOCTEXT, SENT_CHAT])
    # The master engine is built at import; its flag is checked structurally.
    assert core_db.engine.sync_engine.hide_parameters is True
```

- [ ] **Step 3: Run RED**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
env -u SQL_ECHO -u DEBUG "$PY" -m pytest tests/security/test_sql_echo_phi.py -p no:cacheprovider -q -k sqlecho 2>&1 | grep -E "^E   *AssertionError|^FAILED|passed|failed"
```
Expected (measured):
- `1 failed, 3 passed`;
- 004: `AssertionError: PHI reached the SQL log: ['S1ECHO_ANALYTE_hba1c', '731.0419', 'S1ECHO_DOCTEXT HIV-1 RNA detected', 'S1ECHO_CHAT is my result dangerous']`.

The positive line `INSERT INTO observations` passing first proves echo is on and the capture works.

- [ ] **Step 4: Implement B**

`src/backend/core/database.py`, directly below `    echo=settings.sql_echo,`:
```python
    hide_parameters=True,  # never log bound values, even with SQL_ECHO=true (S-1)
```
`src/backend/core/profile_database.py`, directly below `                echo=settings.sql_echo,` (inside `create_async_engine(...)` only):
```python
                hide_parameters=True,  # never log bound values, even with SQL_ECHO=true (S-1)
```
`config/.env.example`, directly above `SQL_ECHO=false`:
```
# Bound values (lab results, names, notes) are never printed, even when true.
```

- [ ] **Step 5: Prove the diff is surgical, then GREEN**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
git diff -U0 -- src/backend/core/profile_database.py src/backend/core/database.py config/.env.example | grep -E '^[-+][^-+]'
cd "$WT/src/backend"
env -u SQL_ECHO -u DEBUG "$PY" -m pytest tests/security/test_sql_echo_phi.py -p no:cacheprovider -q -k sqlecho 2>&1 | grep -E "^FAILED|passed|failed"
```
Expected:
- exactly 3 `+` lines (the two `hide_parameters=True,` lines and the `.env.example` comment) and no `-` lines;
- `4 passed` (measured).

- [ ] **Step 6: Update the collected-count slots (+1)**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
N2=$("$PY" -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1 | grep -oE '^[0-9]+'); echo "N2=$N2"
"$PY" - "$WT" "<N1>" "$N2" <<'EOF'
import pathlib, re, sys
wt, old, new = sys.argv[1:]
assert int(new) == int(old) + 1, (old, new)
subs = {
    "CLAUDE.md": [(rf"\*\*{old} backend tests collected\.\*\*", f"**{new} backend tests collected.**"),
                  (rf"(differs from\s+){old},", rf"\g<1>{new},")],
    "AGENT.md": [(rf"\({old} collected;", f"({new} collected;")],
}
for name, pairs in subs.items():
    p = pathlib.Path(wt, name)
    s = p.read_text(encoding="utf-8")
    for pat, rep in pairs:
        s, n = re.subn(pat, rep, s)
        assert n == 1, (name, pat, n)
    p.write_text(s, encoding="utf-8")
print("collected slots", old, "->", new)
EOF
git -C "$WT" diff -U0 -- CLAUDE.md AGENT.md | grep -E '^[-+][^-+]'
```
Replace `<N1>` with the Task 2 figure.

Expected: `N2` = N0 + 4, and `collected slots N1 -> N2`. The same stop rules as Task 2 Step 5 apply: an `assert` fires, or N2 ≠ N1 + 1 → **STOP**.

- [ ] **Step 7: Commit B**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
git add -- src/backend/core/database.py src/backend/core/profile_database.py src/backend/tests/security/test_sql_echo_phi.py config/.env.example CLAUDE.md AGENT.md
git diff --cached --name-only
git commit -m "fix(db): hide bound SQL parameters on both runtime engines (S-1)

hide_parameters=True keeps values out of echo, INFO-level sqlalchemy.engine
logging and StatementError messages, so SQL_ECHO=true shows statements only.
HC-SQLECHO-004. Owner sign-off S1-B."
```
Expected `--cached` list, exactly 6 paths: `AGENT.md`, `CLAUDE.md`, `config/.env.example`, `src/backend/core/database.py`, `src/backend/core/profile_database.py`, `src/backend/tests/security/test_sql_echo_phi.py`.

---

## Task 4: Break it on purpose, re-walk the whole flow, end measurement

**Files:** none modified in `$WT`.

- [ ] **Step 1: Break-it table** (disposable worktree; recurring-failures #1)

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
BRK=$HOME/s01-break
B_APPROVED=yes   # set to "no" when S1-B was not signed and Task 3 was skipped
git -C "$WT" worktree add --detach "$BRK" HEAD
run() { echo "== $1"; (cd "$BRK/src/backend" && env -u SQL_ECHO -u DEBUG "$PY" -m pytest tests/security/test_sql_echo_phi.py -p no:cacheprovider -q -k sqlecho 2>&1 | grep -E "^E   *(AssertionError|assert)|^FAILED|passed|failed" | cut -c1-200); git -C "$BRK" checkout -q HEAD -- .; }
sed -i 's/    sql_echo: bool = False/    sql_echo: bool = True/' "$BRK/src/backend/core/config.py"; run "BI-1 default sql_echo=True"
if [ "$B_APPROVED" = yes ]; then
  sed -i '/hide_parameters=True/d' "$BRK/src/backend/core/profile_database.py"; run "BI-2 vault engine without hide_parameters"
  sed -i '/hide_parameters=True/d' "$BRK/src/backend/core/database.py"; run "BI-3 master engine without hide_parameters"
else
  echo "BI-2/BI-3 skipped: S1-B not signed"
fi
REV=HEAD~2; [ "$B_APPROVED" = yes ] || REV=HEAD~1
sed -i 's/    echo=settings.sql_echo,/    echo=settings.debug,/' "$BRK/src/backend/core/database.py"; run "BI-4 master echo=settings.debug"
sed -i 's/                echo=settings.sql_echo,/                echo=settings.debug,/' "$BRK/src/backend/core/profile_database.py"; run "BI-5 vault echo=settings.debug"
git -C "$BRK" checkout -q "$(git -C "$WT" rev-parse "$REV")" -- src/backend/core/config.py src/backend/core/database.py src/backend/core/profile_database.py; run "BI-6 whole fix reverted (tests kept)"
echo "== BI-7 DEBUG=false"; (cd "$BRK/src/backend" && DEBUG=false "$PY" -m pytest tests/security/test_sql_echo_phi.py -p no:cacheprovider -q -k sqlecho 2>&1 | grep -E "^E   *(AssertionError|assert)|^FAILED|passed|failed" | cut -c1-200)
git -C "$WT" worktree remove --force "$BRK"
git -C "$WT" status --porcelain
```
If Task 3 was skipped, set `B_APPROVED=no`. The script then skips BI-2 and BI-3 and reverts to `HEAD~1` for BI-6. Without B, BI-1 also turns 001 and 002 red (no parameter hiding), and 004 does not exist.

| # | Break | Expected red (measured on Win 3.13.7 / B tree unless noted) |
|---|---|---|
| BI-1 | `sql_echo` default `True` | 003 only: `assert True is False` (001 and 002 stay green because B hides values: defense in depth) |
| BI-2 | no `hide_parameters` on the vault engine | 004: PHI list (analyte, value, doc text, chat) |
| BI-3 | no `hide_parameters` on the master engine | 004: `assert False is True` |
| BI-4 | master `echo=settings.debug` | 003: `assert True is False` |
| BI-5 | vault `echo=settings.debug` | 001: `assert True is False` |
| BI-6 | all three product files at `START` | 001 and 002: PHI lists; 003 and 004: `AttributeError … sql_echo` (the Task 1 RED plus 004; BI-6 as a whole is UNMEASURED) |
| BI-7 | `DEBUG=false` in the env | 002: `AssertionError: precondition: …` |

Expected final line: empty `git status --porcelain` in `$WT`.

**STOP** if any **applicable** row stays green: all 7 with S1-B, or BI-1, BI-4, BI-5, BI-6 and BI-7 without it. The test that should catch it is vacuous; fix the test, never the expectation.

- [ ] **Step 2: The real master DB is untouched**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
before=$(stat -c '%s %Y' "$WT/src/backend/data/asclexis.db" 2>/dev/null || echo absent)
env -u SQL_ECHO -u DEBUG "$PY" -m pytest tests/security/test_sql_echo_phi.py -p no:cacheprovider -q -k sqlecho 2>&1 | tail -1
after=$(stat -c '%s %Y' "$WT/src/backend/data/asclexis.db" 2>/dev/null || echo absent)
[ "$before" = "$after" ] && echo "master-untouched ($after)"
```
Expected: `4 passed` (or `3 passed` without B), then `master-untouched (absent)`.

- [ ] **Step 3: Every other caller still believes the same thing** (recurring-failures #2)

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
git grep -n -E "\[parameters|parameters:|\.params\b|orig\.args|in str\(e" -- src/backend ':!src/backend/tests' || echo no-param-parsers
git grep -n -E "settings\.debug" -- src/backend ':!src/backend/tests'
git diff --exit-code --stat "$(git merge-base HEAD origin/main)" HEAD -- src/backend/core/security.py src/backend/core/auth.py src/backend/core/migrations.py src/backend/migrations src/backend/alembic.ini src/backend/modules/redaction.py src/backend/modules/interpret_safety.py src/backend/modules/faithfulness.py src/backend/modules/verifier_agent.py src/backend/tests/support/routes.py dev.ps1 && echo read-only-unchanged
```
Expected:
- `no-param-parsers`;
- `settings.debug` only at `core/config.py` (the production force-off), `core/llm/llama_cpp_provider.py`, and `main.py` (docs and reload): no engine;
- `read-only-unchanged`.

- [ ] **Step 4: Whole-app probe on the end tree** (the Task 0 Step 6 script)

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
env -u SQL_ECHO -u DEBUG "$PY" "$HOME/s01-probe/s01_probe.py" "$WT/src/backend" "$HOME/s01-probe/out-end" 2> "$HOME/s01-probe/out-end/stderr.txt"; echo "probe-exit=$?"
"$HOME/s01-probe/count.sh" "$HOME/s01-probe/out-end"
SQL_ECHO=true "$PY" "$HOME/s01-probe/s01_probe.py" "$WT/src/backend" "$HOME/s01-probe/out-end-echo" 2> "$HOME/s01-probe/out-end-echo/stderr.txt"; echo "probe-exit=$?"
"$HOME/s01-probe/count.sh" "$HOME/s01-probe/out-end-echo"
git -C "$WT" status --porcelain
```
Expected (measured on Win 3.13.7 / B tree):
- **default:** `debug=True sql_echo=False`, `vault echo=False hide_parameters=True`, `create=201`, `verify=200`; every sentinel = 0, `parameters hidden=0`, `engine-lines=0`.
- **`SQL_ECHO=true`, A+B:** `vault echo=True hide_parameters=True`; every sentinel = 0; `parameters hidden` > 0 (measured 69); `engine-lines` > 0 (measured 156). This proves the documented `.env.example` switch works (recurring-failures #6).
- **`SQL_ECHO=true`, A-only (S1-B declined):** `vault echo=True hide_parameters=False`; sentinels > 0; `parameters hidden` = 0. This is expected for a developer opt-in: record the counts in the PR as a known limitation. It is **not** a stop. The default-config run above must still show 0.
- Empty `git status --porcelain`.

- [ ] **Step 5: End measurement**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
find "$WT/src/backend" -name __pycache__ -type d -prune -exec rm -rf {} +
"$PY" -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1
"$PY" -m pytest tests/ -p no:cacheprovider -q -rfEsxX 2>&1 | tail -30; echo "pytest-exit=$?"
"$PY" -c "from main import app; print('boot-ok')"
cd "$WT" && python3 scripts/docs_lint.py
```
Expected:
- collected = N0 + 4 (N0 + 3 without B);
- failing node IDs ⊆ F0;
- `boot-ok`;
- `Docs lint passed.`

**STOP** on any new failure. Use `systematic-debugging`, and never relax the fix or the test.

---

## Task 5: Execution record and PR

**Files:**
- Modify: this plan's "Execution record" section only.

- [ ] **Step 1:** Fill in the execution record below with the recorded values: START, CIPHER0, N0, F0, ENV0, the RED output, the break-it table, the probe counts, and the end figures.

- [ ] **Step 2: Commit the record**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
git add -- docs/plans/2026-09-27-S01-sql-echo-phi-leak.md
git diff --cached --name-only
git commit -m "docs(plans): record S-1 execution evidence"
```
Expected `--cached` list: this plan file only.

- [ ] **Step 3: Push and open the PR**
  - `git push -u origin fix/s01-sql-echo-phi`.
  - The PR body follows handoff §6:
    1. start and end measurements;
    2. new tests with RED proof;
    3. C-REDACT-3, C-KEY-1 and PRIV-06, noting that PRIV-06 stays **partial**;
    4. the explicit file list and the owner stops reached;
    5. one next action.
  - List the unchanged `PASS_SLOTS`.
  - **STOP** for the owner to merge.

---

## Measured acceptance

| Check | Command | Expected |
|---|---|---|
| Collection | Task 4 Step 5 | N0 + 4 (N0 + 3 if S1-B declined) |
| No new failures | Task 4 Step 5 | failures ⊆ F0 |
| No engine reads `debug` | `grep -rn "echo=settings.debug" src/backend --include=*.py` | no output |
| B present | `grep -n "hide_parameters=True" src/backend/core/database.py src/backend/core/profile_database.py` | A+B: 1 hit per file. A-only: no output |
| RED then GREEN | A+B: Task 1 Step 2 → Task 2 Step 4 → Task 3 Step 3 → Task 3 Step 5. A-only: Task 1 Step 2 → Task 2 Step 4 | messages as listed. A-only ends at 3 passed (001–003); 004 does not exist |
| Break-its | Task 4 Step 1 | every applicable row red (BI-2/BI-3 excluded when S1-B is unsigned) |
| Whole app, default config (**the S-1 gate on both paths**) | Task 4 Step 4 | A+B and A-only: 0 sentinels, 0 engine lines |
| Whole app, `SQL_ECHO=true` (developer opt-in) | Task 4 Step 4 | A+B: 0 sentinels, `parameters hidden` > 0. A-only: sentinels > 0 and `parameters hidden` = 0. This is the expected opt-in leak: record it in the PR as a known limitation of declining S1-B. It is **not** a stop |
| Boot | `python -c "from main import app"` | `boot-ok` |

**UNMEASURED at planning time** (measured by Tasks 0–4):
- every figure on the post-P1 tree;
- every figure under Python 3.11;
- every figure with SQLCipher present;
- BI-6 as a whole;
- whether llama.cpp `verbose` leaks prompt text (out of scope).

## Stop gates

| # | Condition | Action |
|---|---|---|
| G1 | S1-A unsigned | Task 1 only (uncommitted), then stop |
| G2 | S1-B unsigned | skip Task 3; record it in the PR |
| G3 | not post-P1; venv missing; the plan file is not on main (the owner-approved docs commit of the plan set has not landed) | stop |
| G4 | ID or `sql_echo` / `hide_parameters` already present; anchor counts ≠ 1 | stop and re-plan |
| G5 | the start probe shows 0 sentinels, or RED fails for a different reason | stop; `systematic-debugging` |
| G6 | a 64-hex key appears in 001's leak list | stop; new key-exposure finding for the owner |
| G7 | any `profile_database.py` diff line outside the `create_async_engine(...)` call | stop; ask-first surface |
| G8 | any applicable break-it row stays green (BI-2/BI-3 are excluded when S1-B is unsigned) | stop; fix the test, not the expectation |
| G9 | a new failure outside F0; a collected-count mismatch | stop |
| G10 | anything seems to need an edit to `debug`, the key hook, migrations, `alembic.ini`, `dev.ps1` or a docs file owned by the orchestrator | stop; outside approval scope |

## Rollback

- **Before merge (PR open):** `gh pr close <n> --delete-branch`, then `git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree remove /mnt/c/Users/DangT/Documents/GitHub/HealthCentral-s01`. Main is untouched.
- **After merge**, revert on main:
- **B only:** `git revert <commit B>`. A still removes the default exposure, and the counts revert with the commit.
- **Everything:** `git revert <commit B> <commit A>`, newest first, on a branch from main, and open a PR for the owner to merge.
- There is no schema, migration or data change.
- A developer `.env` containing `SQL_ECHO=` stays harmless after a revert, because Settings uses `extra="ignore"` (`core/config.py:22` B@7b2ff1f).

## Owner sign-offs (unsigned)

- [ ] **S1-A** (canonical gate SQL-ECHO) — I approve the S1-A change exactly as quoted in [Approval scope](#approval-scope): a `sql_echo` setting (default false); both runtime engines use `echo=settings.sql_echo`; `.env.example` documents it; tests HC-SQLECHO-001…003; count slots. This includes the one-line edit inside `create_async_engine(...)` in the ask-first file `core/profile_database.py`. — Owner: ________ Date: ________
- [ ] **S1-B** (canonical gate SQL-ECHO) — I approve the S1-B change exactly as quoted: `hide_parameters=True` on both runtime engines; the `.env.example` comment; HC-SQLECHO-004; count slots. — Owner: ________ Date: ________
- [ ] **Merge** — owner merges the PR. — Owner: ________ Date: ________

## Commit plan

| # | Prefix and subject | Pathspecs (explicit; `git diff --cached --name-only` reviewed first) | Gate |
|---|---|---|---|
| 1 | `fix(db): decouple SQL echo from DEBUG so dev mode stops printing PHI (S-1)` | `src/backend/core/config.py src/backend/core/database.py src/backend/core/profile_database.py src/backend/tests/security/test_sql_echo_phi.py config/.env.example CLAUDE.md AGENT.md` | S1-A |
| 2 | `fix(db): hide bound SQL parameters on both runtime engines (S-1)` | `src/backend/core/database.py src/backend/core/profile_database.py src/backend/tests/security/test_sql_echo_phi.py config/.env.example CLAUDE.md AGENT.md` | S1-B |
| 3 | `docs(plans): record S-1 execution evidence` | `docs/plans/2026-09-27-S01-sql-echo-phi-leak.md` | — |

Rules for every commit:
- It is green on its own, and each collected-count change lands in the same commit as the tests that cause it.
- No `git add -A` or `git add .`.

## Recurring-failures recheck ([recurring-failures.md](../agentic/recurring-failures.md))

| # | Mode | Applies? | Concrete recheck in this plan |
|---|---|---|---|
| 1 | Green suite that could not fail | **yes** | No caplog (fileConfig strips it). Each test has a canary or a positive SQL line. 002 asserts the `debug` precondition. The Task 4 Step 1 break-it table has 7 rows |
| 2 | Fix creates the next bug one layer over | **yes** | `hide_parameters` also changes exception text (Task 4 Step 3 grep). `debug`'s other effects are unchanged (SEC-006 run in Task 2 Step 4). The whole-app round trip is create → seed → verify (Task 4 Step 4) |
| 3 | Figures asserted, not measured | yes | N0, N1 and N2 are measured, and the slot script asserts +3 and +1 |
| 4 | Environment-dependent results | **yes** | `DEBUG` in env (BI-7); SQLCipher present or absent (`CIPHER0`); Windows 3.13 planning figures versus 3.11 execution, all labelled |
| 5 | Contaminated tree | yes | Dedicated worktree; a disposable `$BRK` for breaks; the probe writes outside the repo; `git status --porcelain` is checked empty |
| 6 | Documented commands nobody ran | yes | The `SQL_ECHO=true` line in `.env.example` is exercised by the Task 4 Step 4 probe |
| 7 | SQL three-valued logic | no | No SQL filter is added or changed |
| 8 | Stale guidance reads as authority | **yes** | `hipaa-controls.md:71` and `data-privacy.md:47` claim no PHI in logs, and were false in dev mode. F-P8-3's "static reading; not measured" is now measured. `.env.example:13` "enables verbose logging" is left as is (DEBUG still enables llama.cpp verbose) |

## Docs that change truth value (orchestrator edits them)

| Doc line (ref) | Today | After S-1 (A+B) |
|---|---|---|
| `docs/compliance/hipaa-controls.md:71` (main, A) "the plaintext app log does not become a second copy" | **false** in dev mode: every non-audit INSERT/UPDATE echoed its values | true for the SQL-echo surface. Other INFO loggers (`api/profiles.py:328`) remain and are suppressed only by root WARN |
| `docs/compliance/data-privacy.md:47` (main, A) "Log files … Contains event metadata, not PHI" | **false** for dev-mode stderr; also there is no log file by default (P08 R2) | true for SQL echo. The "log files" framing still needs the P4/W-10 wording fix |
| contract C-REDACT-3 (`:196-202`) "Enforced at" / "Status today" | omits S-1 | add `tests/security/test_sql_echo_phi.py` (HC-SQLECHO-001…004) and "debug SQL echo closed (S-1)" |
| contract C-KEY-1 (`:77-86`) "Enforced at" | key hook only | add HC-SQLECHO-001 (the hex key is absent from the SQL log) |
| matrix PRIV-06 (`:89`) evidence | HC-AUD only | add HC-SQLECHO-001…004 (001–003 if S1-B declined); status stays **partial** |
| P08 amendment F-P8-3 and brief option D | "REPORTED"; vault "not measured" | "fixed by S-1 (commit …)"; vault leak measured |
| `CLAUDE.md` / `AGENT.md` collected-count slots | N0 | N0 + 4 (N0 + 3 if S1-B declined; this plan edits them) |

## Execution record

Executed 2026-10-01 by L1-A (Wave 2). Plan checkboxes under "Owner sign-offs" are intentionally unticked: agents do not record approvals.

### Setup and gate

| Item | Value |
|---|---|
| Worktree / branch | `../hc-s1`, `fix/s1-sql-echo-phi-leak` |
| START | `8064244` (origin/main) |
| Interpreter | `~/venvs/asclexis-311`, Python 3.11.16, WSL2 Linux |
| CIPHER0 | sqlcipher3 present |
| ENV0 | `HF_HUB_OFFLINE=1` |
| Gate | `owner-decisions-2026-09-27.md` SQL-ECHO = S1-A + S1-B (signed 2026-09-28): "A: new sql_echo flag default False (decoupled from debug). B: hide_parameters=True so even when echo is on, values are masked." |

### Baseline and end

| Item | Value |
|---|---|
| N0 (collected, start) | 1296 |
| F0 / S0 (full-suite start run) | not recorded: the run was lost when the host ran out of memory (2026-10-01); immaterial because END has 0 failures |
| N end (collected) | 1300 |
| Full suite END | `1300 passed, 54 warnings in 275.00s`, pytest-exit=0 |
| Embedding model | available in this env: `test_api_rag_index_002b` passed |
| Boot | `boot-ok` |
| Docs lint | passed |

### Commits

| SHA | Subject | Count slots |
|---|---|---|
| `016e672` | `fix(db): decouple SQL echo from DEBUG` (A) | 1296 -> 1299 |
| `f1ab1b5` | `fix(db): hide bound SQL parameters` (B) | 1299 -> 1300 |

### Whole-app probe counts

| Probe | debug / sql_echo | create | vault echo / hide_parameters | verify | sentinels | parameters hidden | engine-lines |
|---|---|---|---|---|---|---|---|
| start (`out-start`) | True / ABSENT | 201 | True / False | 200 | S1PROBE_NAME=1, `$2b$`=1, S1PROBE_ANALYTE=1, 731.0419=2, S1PROBE_NOTE=1 | 0 | 156 |
| end, default (`out-end`) | True / False | 201 | False / True | 200 | all 0 | 0 | 0 |
| end, `SQL_ECHO=true` (`out-end-echo`) | n/a | n/a | True / True | n/a | all 0 | 69 | 156 |

### Break-it table (disposable worktree `~/s01-break`, removed)

| Row | Break | Result |
|---|---|---|
| BI-1 | `sql_echo` default True | 001 and 003 red (`assert True is False`); 2 failed, 2 passed. 001 fails via its `engine.echo` assert, stronger than the plan's "003 only" |
| BI-2 | vault without `hide_parameters` | 004 red; PHI list `['S1ECHO_ANALYTE_hba1c', '731.0419', 'S1ECHO_DOCTEXT HIV-1 RNA detected', 'S1ECHO_CHAT is my result dangerous']` |
| BI-3 | master without `hide_parameters` | 004 red: `assert False is True` |
| BI-4 | master `echo=settings.debug` | 003 red: `assert True is False` |
| BI-5 | vault `echo=settings.debug` | 001 red: `assert True is False` |
| BI-6 | three product files at origin/main, tests kept | 4 failed: 001 and 002 PHI lists incl. `['S1ECHO_NAME Jane Doe', '$2b$', 'S1ECHO_NOTE_VIA_HTTP']`; 003 and 004 `AttributeError` on `sql_echo` |
| BI-7 | `DEBUG=false` | 002 precondition `AssertionError` |

All 7 rows red.

### Task 4 checks

| Step | Result |
|---|---|
| Step 2 | 4 passed; master-untouched (absent) |
| Step 3 | no-param-parsers; `settings.debug` only at `llama_cpp_provider.py:136`, `main.py:93`, `main.py:94`, `main.py:173`; read-only-unchanged |
| `grep echo=settings.debug` in product code | 0 hits (one hit in the new test's docstring only) |

### Reviews

| Reviewer | Verdict | Findings |
|---|---|---|
| code-reviewer (opus) | APPROVE; 0 blocker, 0 major | 3 minor: (1) `config.py` whitespace-only blank line replaced, so the plan's "+4 lines" is actually -1/+5; (2) stale pass-count slots `CLAUDE.md:31` "all 1288 pass" and `AGENT.md:76` "1269 pass in CI, 1268 without" left unchanged per plan; (3) 001/003 can fail loudly if a developer `.env` sets `SQL_ECHO=true` |
| security-reviewer (opus) | APPROVE | 4 LOW: (1) 8 migration engines lack `hide_parameters` but bind no PHI; (2) no production force-off of `SQL_ECHO`; (3) 002/003 env fragility; (4) 002 cannot see master `hide_parameters` removal, 004 covers it |
| Codex adversarial diff review | approve | no material findings |
