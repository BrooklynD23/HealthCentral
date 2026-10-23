# MVP rows 2026-10-22 — plans for the MVP pass, owner prompts 40-41 and the bug-fixer follow-ups

**Last Updated:** 2026-10-22
**Owner:** repository owner
**Status:** PROPOSED (Opus planner). Docs only. **No owner approval is recorded here.** Every gate keeps its state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md). Answers cited below come from owner prompts 40-41 (L0 AskUserQuestion, 2026-10-22, record `/tmp/claude-1000/prompts-40-41.json`); their owner-decisions rows land in L0's PR #301 (branch `docs/owner-rows-prompts40-41`), not here.
**Base measured:** `origin/main` @ `0e2799b` (2026-10-22, after #294 EXTRACT-UNIT-MGL + EXTRACT-DOB-DATE merged). Every `file:line` below was re-read on that SHA by the planner; lines in files that open PRs change are marked "re-read after #n".
**Refresh Trigger:** any owner answer to a gate in [Owner gates](#owner-gates); a merge of #295, #297, #300, #304, #305 or #264; any edit to `src/backend/modules/extract.py`, `dev.ps1`, `dev.sh` or `src/backend/requirements.txt` before the rows below are built.

Queue rows: [queue.md, "Planned 2026-10-22, MVP rows"](2026-10-15-build-program/queue.md#planned-2026-10-22-mvp-rows). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Path shorthand as in the queue: `be/` = `src/backend/`, `fe/` = `src/frontend/src/`.

**Sources.** (1) The MVP readiness pass `/tmp/claude-1000/mvp-pass-1022.md` (facts at `d2843e8`; research merged in #299 as [docs/research/2026-10-22-mvp/](../research/2026-10-22-mvp/00-README.md)); its 20 proposed rows are planned here, re-verified at `0e2799b`. Its other bug-table items (FE-A11Y-DIALOGS, RECOVER-ORDER, AUTO-LOCK-UNUSED, FALLBACK-COUNT-50, CHAT-SESSIONS-N1, TEST-RESET-ROUTE, BACKUP-RESTORE-JOURNAL, TEST-PLACEHOLDERS, IMPORT-FAILED-REASON) are listed as "not yet planned" bullets in the queue. (2) Owner prompts 40-41. (3) Follow-ups from the bug-fix agent (#294, #295, #297, #300), the KV measurement ([#298](../reviews/2026-10-22/kv-prefix-measure.md), "Other findings" items 1-2) and #290's review (round 2 MINORs).

**MVP priority** (showcase 2026-10-31): **P0** = blocks a stakeholder running the app on their own laptop, or makes a privacy or lab-value claim false; **P1** = visible on the demo path, fix before 2026-10-31 if a slot is free; **P2** = after the MVP.

**Ask-first files (CLAUDE.md §1).** Edited only behind a named gate: `be/core/database.py`, `be/core/migrations.py`, `be/core/profile_database.py`, `be/core/sqlcipher_driver.py` (encryption; SQLCIPHER-WHEEL, gate SQLC-WHEEL-DIFF); `be/core/auth.py` (SESSION-REENTRY Task 2, gate SESSION-AUTH-DIFF); `be/api/profiles.py` call sites (EXPORT-STORE-PURGE, treated as auth-adjacent, gate EXPORT-PURGE-DIFF). `modules/interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py`: none edited by any row.

**Overlaps with open PRs** (`gh pr list --state open`, 2026-10-22): #295 (frontend bundle: `ExplainAssistant.tsx`, `ReferenceRangeComparison.tsx`, `VerificationWorkbench.test.tsx`, `model_settings.py`), #297 (`llama_cpp_provider.py`, `factory.py`, `core/config.py`, `config/.env.example`), #300 (`api/assistant.py`, `api/interpretations.py`), #304 INTERP-SAFETY-META claim (`modules/interpret.py`), #305 JUDGE-THINK claim (`core/model_runner.py`, `ollama_provider.py`), #264 and #239 (parked drafts; hold no file, contracts §b rule 2, but rows that must follow #264 say so), #284 and #301 (docs). Each row's `depends_on` names the PR it follows.

---

## Packaging and launcher (MVP-PACKAGING (a) now, (c) later)

Owner: **MVP-PACKAGING answered "Option A then work on C installer"** (free text; L0 reading "(a) for the MVP, then (c) an installer after the MVP"; owner prompts 40-41, owner-decisions row MVP-PACKAGING, L0 PR #301). **CODE-SIGNING answered (a) "No signing yet"** (prompt 41, row CODE-SIGNING).

**Suggested L0 bundle (L0 rules; not assumed):** DEV-PS1-FIRSTRUN, LLAMA-WHEEL-INDEX and DEV-EMB-FETCH all edit `dev.ps1` (and the last two `dev.sh`). Built one after the other, each must merge `origin/main`; as one PR the same-file order is inside it (the #289 bundle pattern). SQLCIPHER-WHEEL also edits `dev.ps1` STEP 3/4 and stays its own draft PR because it is merge-gated.

### DEV-PS1-FIRSTRUN — the Windows launcher hides a dead backend and restarts it forever

**Facts (`0e2799b`):**
1. `dev.ps1:797-802` starts uvicorn with `Start-Process ... -WindowStyle Hidden -PassThru` and no output redirect, so an import error is never visible and no backend log exists (the frontend has `logs\dev-frontend.log`, `:795`).
2. `dev.ps1:827-857` STEP 9 polls only the frontend URL (`:845-846`) and prints "Servers are ready!" (`:848`) whether or not the backend is alive.
3. `dev.ps1:898-911` restarts a dead backend every 2 s with no cap and no log tail; the frontend branch beside it caps at 3 and calls `Write-LogTail` (`:912-923`).
4. `dev.sh` already does all three right (`dev.sh:235`, `:254` backend log, `:264-271` `/health` + frontend wait with exit checks, `:286-288` log tail on exit); it is the reference, not edited here.

**Design:** (1) `Start-Process` gets `-RedirectStandardOutput logs\dev-backend.log -RedirectStandardError logs\dev-backend.err.log` (PowerShell cannot send both to one file) and the launcher prints both paths. (2) STEP 9 waits up to 60 s for `http://127.0.0.1:<port>/health` (200) **and** the frontend; if `$backendProc.HasExited` it prints `Write-LogTail` of both backend logs and exits 1 (mirrors the frontend branch `:836-842`); "Servers are ready!" only when both answer. (3) STEP 10 backend restart: `$backendRestartCount`, log tail on each restart, stop after 3 (same as the frontend). No change to ports, STEP 1-7, or `dev.bat`.

**Test-first (no Pester in the repo; owner-box check, as the MVP pass proposed):**

| Id | Check | RED today? |
|---|---|---|
| DPF-1 | Windows box, `src/backend/main.py` with a deliberate `import nonexistent_module` (scratch, never committed): `.\dev.bat` prints the backend log tail and exits 1 within 60 s; no "Servers are ready!" | yes (prints ready, restarts forever) |
| DPF-2 | same box, clean tree: "Servers are ready!" appears only after `/health` answers; `logs\dev-backend.log` exists and has the uvicorn start line | yes (no log) |
| DPF-3 | kill the backend PID 4 times while running: 3 restarts with log tails, then the launcher stops with the log path | yes (uncapped) |
| DPF-4 | `pwsh -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('dev.ps1',[ref]$null,[ref]$e); $e.Count"` prints 0 (parse check; runs on Linux pwsh too if installed, else on the box) | GREEN (pin) |

**Files:** `dev.ps1` (STEP 8 `:797-802`, STEP 9 `:824-857`, STEP 10 backend branch `:898-911` only). **Expected collected delta:** 0 (no pytest). **Est:** 1.5 h. **Runtime:** claude (or the `windows-bootstrap-engineer` agent, whose scope is `dev.ps1` + `dev.bat`); checks DPF-1…3 are an owner-box run (Windows), pasted into the PR. **Acceptance:** DPF-1…4 output pasted. **Owner gates:** MVP-PACKAGING (a) (above). **Order:** ready; never beside another `dev.ps1` PR (LLAMA-WHEEL-INDEX, DEV-EMB-FETCH, SQLCIPHER-WHEEL), or bundled (above). **MVP:** P0.

### LLAMA-WHEEL-INDEX — a clean Windows or Mac without a C++ toolchain cannot install llama-cpp-python

**Facts:**
1. `be/requirements.txt:72` pins `llama-cpp-python==0.3.35`. PyPI publishes only the sdist for it (MVP pass, re-checked there); pip compiles it from source.
2. The upstream maintainer's CPU wheel index lists `llama_cpp_python-0.3.35-py3-none-win_amd64.whl`, `-macosx_11_0_arm64.whl` and `-manylinux2014_x86_64…whl` (planner, `curl -s https://abetlen.github.io/llama-cpp-python/whl/cpu/llama-cpp-python/`, 2026-10-22). **No macOS x86_64 (Intel) wheel** is listed for 0.3.35.
3. `dev.ps1` STEP 3 (`:466-507`) has no compiler check; `dev.sh:93-130` checks for a C compiler and dies unless `LLM_PROVIDER=ollama`.

**Design:** before the main `pip install -r requirements.txt`, both launchers run one extra step: read the exact `llama-cpp-python==X` pin from `requirements.txt` (single source, so the two can never drift) and run `pip install --only-binary=llama-cpp-python --index-url https://abetlen.github.io/llama-cpp-python/whl/cpu "llama-cpp-python==X" --no-deps`, then the normal install (which finds it already satisfied and installs its PyPI dependencies). `--index-url` + `--no-deps` for this one package, not `--extra-index-url` for everything, so no other package can resolve from the second index (dependency-confusion guard). If the wheel step fails (no wheel for the platform, e.g. Intel Mac): `dev.sh` keeps today's compiler check; `dev.ps1` gains the same check (`cl.exe` / `where.exe cl`, or `LLM_PROVIDER=ollama` skips it) and stops with the Visual Studio Build Tools link instead of a long compile error. Install-time network only; nothing changes at runtime. README install section: one sentence naming the wheel index.

**Test-first:**

| Id | Check | RED today? |
|---|---|---|
| LWI-1 | Windows box, fresh venv, no VS Build Tools on PATH: launcher STEP 3 installs `llama-cpp-python 0.3.35` from the wheel in under 2 min (`pip show llama-cpp-python`) | yes (source build fails) |
| LWI-2 | Linux, `bash -n dev.sh` and a scratch run of the new step in a throw-away venv: the installed wheel's `RECORD` shows a prebuilt `.so`, no build directory | yes (builds from source) |
| LWI-3 | `grep -c 'extra-index-url' dev.ps1 dev.sh` prints 0 for both (pin against the broad flag) | GREEN (pin) |

**Files:** `dev.ps1` (STEP 3 only), `dev.sh` (STEP 3 only), `README.md` (install section, one sentence). `requirements.txt` not edited. **Delta:** 0. **Est:** 1 h. **Acceptance:** LWI-1 on the owner box, LWI-2, LWI-3 pasted. **Owner gates:** MVP-PACKAGING (a). **Order:** after DEV-PS1-FIRSTRUN (same file) or in its bundle; #297 does not change the pin (its file list has no `requirements.txt`), so it does not wait for #297. **MVP:** P0.

### DEV-EMB-FETCH — the launchers never fetch the embedding model, so document chunks are silently empty

**Facts:** `git grep -n download_models -- dev.ps1 dev.sh` has no hit. `be/modules/embeddings.py:164-173` raises `EmbeddingModelUnavailableError` when the bundle is missing; `be/api/documents.py:675-687` catches it and only logs `Chunking failed` (warning), so an upload succeeds with 0 chunks and chat retrieval over documents is empty. `be/scripts/download_models.py:332-390` `cmd_embedding` is idempotent (returns when `_embedding_complete`) and verifies sha256.

**Design:** both launchers, after STEP 3: `(cd src/backend && <venv python> scripts/download_models.py embedding)`. Already complete: no network, prints the existing "already present" line. Failure: stop with the command to re-run and a one-line reason ("needs internet once, about 88 MB"). This is install-time network through the already-sanctioned fetch path (W-8); the backend still never downloads.

**Test-first:**

| Id | Check | RED today? |
|---|---|---|
| DEF-1 | fresh clone on the box (scratch dir, `HF_HOME` empty): launcher prints the fetch step and `src/backend/models/embedding/…` exists after it; then `pytest tests/test_embedding_bundle.py::test_hc_emb_002_fetched_model_loads_offline` passes (it fails before) | yes |
| DEF-2 | second launcher run with Wi-Fi off: no network, step reports present, launcher continues | GREEN after DEF-1 (pin) |

**Files:** `dev.ps1`, `dev.sh` (one new step each). **Delta:** 0. **Est:** 0.5 h. **Order:** after LLAMA-WHEEL-INDEX (same files) or in the bundle. **Owner gates:** MVP-PACKAGING (a). **MVP:** P0.

### INSTALLER-POST-MVP — plan the installer the owner chose for after the MVP (research only now)

**Scope:** docs only, no code, no build. Re-read the [packaging decision record](2026-10-01-packaging-decision.md) (S-C4-1…5 still unsigned) and [research 01](../research/2026-10-22-mvp/01-desktop-packaging.md), then write `docs/research/2026-10-22-installer/00-README.md`: (1) shell (Tauri v2 sidecar vs pywebview vs a portable PyInstaller onedir), with the CORS change Tauri needs (C-LOCAL-3) and the `StaticFiles` mount + per-user data directory (S-C4-2); (2) what is bundled vs fetched once (chat GGUF, embedding bundle, the RapidOCR models if RAPIDOCR-BUNDLE lands); (3) **unsigned delivery** per CODE-SIGNING (a): the exact Windows SmartScreen and macOS Gatekeeper steps a stakeholder sees, as a one-page "how to open it" card draft; (4) the open owner gates it would need (S-C4-1…5), drafted, not asked. Every licence and size read from the primary page, marked as in #299.

**Files:** `docs/research/2026-10-22-installer/00-README.md` (new), `docs/INDEX.md`, `docs/_link_graph.json`. **Est:** 3 h. **Runtime:** claude (no slot). **Owner gates:** MVP-PACKAGING (c) part, CODE-SIGNING (a). **Order:** ready; independent. **MVP:** P2.

---

## Encryption at rest (SQLCIPHER-WHEEL)

### SQLCIPHER-WHEEL — Windows and macOS vaults are not encrypted: per-platform SQLCipher package, a launcher that never disables encryption silently, a startup check

Owner: **SQLCIPHER-WHEEL answered in free text: "switch to sqlcipher3 for window + then keep whatever works on Linux on Linux? That way we can support different OS."** (owner prompts 40-41, owner-decisions row SQLCIPHER-WHEEL, L0 PR #301; L0 reading: sqlcipher3 on Windows and macOS, keep sqlcipher3-binary on Linux; the encryption-adjacent diff comes back to the owner). The owner wrote "window"; macOS is included because the recommended option (a) named it and L0's reading includes it; **the SQLC-WHEEL-DIFF question states this explicitly** so the owner can strike macOS.

**Facts (`0e2799b`):**
1. `be/requirements.txt:31-32`: `sqlcipher3-binary>=0.5.0`. PyPI `sqlcipher3-binary` 0.6.0 (latest) ships only `manylinux2014_x86_64` wheels (planner, PyPI JSON 2026-10-22). PyPI `sqlcipher3` 0.6.4 ships cp311 wheels for `win_amd64`, `win32`, `win_arm64`, `macosx_11_0_arm64`, `macosx_10_9_x86_64`, `universal2` and manylinux (planner, PyPI JSON; `win_amd64` 2,551,236 bytes). Its PyPI metadata has no licence field: the row reads `LICENSE` from the sdist and records it (the MVP pass says zlib-style; not taken on trust).
2. Both packages install the module `sqlcipher3`: `be/core/sqlcipher_driver.py:11-17` imports it and falls back to stdlib `sqlite3` with one warning.
3. `dev.ps1:471-500`: if the full install fails and the pip output mentions "sqlcipher" anywhere (`:483`, the regex runs over the whole log), it installs everything else (`:495-500`, `Out-Null`, no exit-code check) and `:585-593` rewrites `DATABASE_ENCRYPTION_REQUIRED=true` to `false` in `.env`. With no template, `:570-581` writes a default `.env` with `DATABASE_ENCRYPTION_REQUIRED=false`. `dev.sh:134-153` and `:170-185` do the same (`:175` writes `DATABASE_ENCRYPTION_REQUIRED=false` when there is no template).
4. Startup: `be/core/database.py:71-79` raises `RuntimeError` when encryption is required and `is_sqlcipher_available()` is false, but only logs `verify_cipher_version()`; `be/core/migrations.py:213-217` and `be/migrations/profile/env.py:127` check availability only; `be/core/profile_database.py:337-346` checks `PRAGMA cipher_version` per connection and raises `ProfileDatabaseEncryptionError` when required. `be/core/config.py:44` defaults `database_encryption_required = True`; `config/.env.example:48` sets it `true`.
5. Hint text names only `sqlcipher3-binary`: `database.py:75`, `migrations.py:216`, `modules/environment_diagnostics.py:162-186` (Windows text says the wheel is Linux-only).

**Design (the exact diff goes to the owner, SQLC-WHEEL-DIFF):**
1. `requirements.txt:32` becomes two lines with environment markers:
   `sqlcipher3-binary>=0.5.0; sys_platform == "linux"` and `sqlcipher3>=0.6.4; sys_platform == "win32" or sys_platform == "darwin"`. Linux (incl. the GPU box and CI) keeps exactly today's package. Known gap, stated in the gate: `sqlcipher3-binary` has no Linux aarch64 wheel; that platform is unchanged (it fails as today).
2. Launchers never disable encryption silently. `dev.ps1` STEP 3 and `dev.sh` STEP 3: a SQLCipher install failure **stops** the launcher with the pip error lines and the fix. Only an explicit `HC_ALLOW_UNENCRYPTED=1` (new, development only) keeps today's fallback, and then the launcher prints a multi-line red banner "Your health data will NOT be encrypted on this computer" and writes `DATABASE_ENCRYPTION_REQUIRED=false`. The default `.env` written at `dev.ps1:570-581` uses `true`. The `:483` match is narrowed to pip's error lines for the sqlcipher package and `:495-500` checks `$LASTEXITCODE`.
3. Startup check (`core/database.py:71-79`, ask-first): when encryption is required, also refuse when `verify_cipher_version()` returns `None` or an empty string (a module that imports but is not SQLCipher). When encryption is **not** required and SQLCipher is unavailable, log one `CRITICAL` line at startup, not a `warning`. Hint strings in `database.py`, `migrations.py` and `environment_diagnostics.py` name the per-platform package.
4. Not changed: `profile_database.py` per-connection check, key handling, KDF settings, migrations, `sqlcipher_driver.py`.

**Test-first:**

| Id | File | Assertion | RED today? |
|---|---|---|---|
| HC-SQLC-001 | `be/tests/test_sqlcipher_platform.py` (new; imports only `core.sqlcipher_driver`, runs with `--noconftest`) | create a DB via `get_sqlcipher_module().connect(tmp)`, `PRAGMA key = "x'<64 hex>'"`, one table, close: the first 16 bytes are not `b"SQLite format 3\x00"`, and stdlib `sqlite3` cannot read the table (`DatabaseError`) | GREEN on Linux; on Windows/macOS today `SQLCIPHER_AVAILABLE` is false: the test asserts availability first, so it is RED there |
| HC-SQLC-002 | same | `is_sqlcipher_available()` and `verify_cipher_version()` is a non-empty string starting with `4.` | as 001 |
| HC-SQLC-003 | same | evaluating the `requirements.txt` lines with `packaging.markers` for `sys_platform` in `win32`, `darwin`, `linux` selects exactly one SQLCipher requirement each (`sqlcipher3`, `sqlcipher3`, `sqlcipher3-binary`) | yes (one unmarked line) |
| HC-SQLC-004 | `be/tests/test_database_startup_cipher.py` (new) | `init_database()` with `database_encryption_required=True`, availability patched true and `verify_cipher_version` patched to return `None`: raises `RuntimeError` | yes |
| HC-SQLC-005 | same | required false + unavailable: one `CRITICAL` record naming encryption, no raise | yes (warning only) |
| HC-SQLC-006 | `be/tests/test_sqlcipher_platform.py` | a vault fixture `be/tests/fixtures/sqlcipher/vault_binary_060.db` (new, about 8 KB, created once on Linux with `sqlcipher3-binary` 0.6.0, raw hex test key, one synthetic row; creation script in the test docstring) opens with the platform's package and returns the row | GREEN on Linux; the point is Windows/macOS (vault moved by backup/restore) |

**CI:** new workflow `.github/workflows/sqlcipher-platforms.yml` (matrix `windows-latest`, `macos-latest`, `ubuntu-latest`, Python 3.11; `pull_request` on `src/backend/requirements.txt`, `src/backend/core/sqlcipher_driver.py`, the test file; plus `workflow_dispatch`; `permissions: contents: read`): installs only the marker-selected SQLCipher line, `packaging` and `pytest`, then runs `pytest tests/test_sqlcipher_platform.py --noconftest`. `ci.yml` is not touched (CI-CACHE edits it). The owner merges CI files.

**Files:** `be/requirements.txt` (`:31-32` only), `dev.ps1` (STEP 3 `:466-507`, STEP 4 `:563-593` only), `dev.sh` (STEP 3 `:132-153`, STEP 4 `:168-185` only), `be/core/database.py` (`:71-79` only; ask-first), `be/core/migrations.py` (`:216` hint string only; ask-first), `be/modules/environment_diagnostics.py` (hint strings `:159-186` only), `be/tests/test_sqlcipher_platform.py` (new), `be/tests/test_database_startup_cipher.py` (new), `be/tests/fixtures/sqlcipher/vault_binary_060.db` (new), `.github/workflows/sqlcipher-platforms.yml` (new), slots. **Re-run, not edited:** `tests/test_profile_migrations_sqlcipher_fallback.py`, `tests/test_environment_diagnostics*.py`, `tests/test_profile_database*.py`. **Expected collected delta:** +6 on Linux. **Est:** 3 h + owner-box run.
**Acceptance:** RED for 003-005 on Linux; the CI matrix job green on all three runners (link in the PR); **Windows box run** (owner or L0): `.\dev.bat` on a fresh clone installs `sqlcipher3`, creates a profile, and `python -c "open('<vault>','rb').read(16)"` is not the SQLite header (pasted); full suite; `from main import app`.
**Owner gates:** SQLCIPHER-WHEEL answered (above); **SQLC-WHEEL-DIFF** (new, merge only: the exact diff to the owner, [Owner gates](#owner-gates) item 1). **Ask-first:** `core/database.py`, `core/migrations.py` (encryption), named by SQLC-WHEEL-DIFF. **Order:** **build to draft now; merge on owner yes.** It merges `origin/main` (and DEV-PS1-FIRSTRUN / LLAMA-WHEEL-INDEX if they landed) before SQLC-WHEEL-DIFF is asked, so the diff shown is final. KEY-08 row in `docs/capstone-report/specs-compliance-matrix.md` is updated by the post-merge batch, not this PR. **MVP:** P0.

---

## Session re-entry (SESSION-REENTRY (a))

Owner: **SESSION-REENTRY answered "(a) Password unlock screen (Recommended)"** (owner prompts 40-41, owner-decisions row SESSION-REENTRY, L0 PR #301): "Add an unlock page using the existing login endpoint; fix the 401-means-logout handling. Frontend mostly; any core/auth.py change comes back to you as an exact diff."

### SESSION-REENTRY — after 60 minutes or a restart, only the recovery code gets a patient back in

**Facts (`0e2799b`):**
1. `be/core/security.py:39` `ACCESS_TOKEN_EXPIRE_MINUTES = 60`. `fe/components/auth/ProtectedRoute.tsx:12-18` sends an unauthenticated or expired session to `/setup`.
2. `fe/pages/ProfileSetup.tsx` (401 lines) is create-only; its only way back for an existing profile is the "Use your recovery code" link (`:325-330`) to `/recover`, which rotates the code.
3. `fe/services/profiles.ts:101` `useProfiles()` (list), `:139-155` `useLogin()` and `:157-180` `useUnlockProfile()` exist; `git grep -n "useLogin\|useUnlockProfile" -- 'src/frontend/src/**/*.tsx'` has no caller. Backend: `be/api/profiles.py:240-251` `GET /profiles/` (no auth, "entry point"), `:351` `POST /profiles/login`, rate-limited.
4. Restart case: the JWT stays valid but the per-profile connection is gone; `be/core/auth.py:301-312` `_get_required_profile_connection` raises **403** "Profile database not available. Please log in again." and `fe/services/api.ts:65-71` keeps the session on 403, so the user sees errors on every page instead of the unlock screen.

**Design:**
- **Task 1 (frontend, no gate):** `/setup` shows an "Unlock your profile" card above the create form when `useProfiles()` returns profiles: a profile picker (display name only), a password field and "Unlock", calling `useLogin()`; success navigates to `/inbox`; a 401 shows "Incorrect password" inline (the login endpoint's 401 cannot log the user out: there is no session yet, and `redirectToSessionRecovery` is a no-op on `/setup`, `api.ts:58`); 429 shows the retry message. The create form stays (collapsed when profiles exist). The recovery link stays.
- **Task 2 (`core/auth.py`, ask-first, gate SESSION-AUTH-DIFF):** `:305-310` 403 becomes **401** with the same detail, so a restart sends the user to the unlock screen. Only that status code changes. Not built until the owner answers; Task 1 does not depend on it. Without Task 2 the restart case still shows errors until the token expires (stated in the gate).

**Test-first:**

| Id | File | Assertion | RED today? |
|---|---|---|---|
| HC-SRE-001 | `fe/__tests__/ProfileSetup.test.tsx` (extend) | with `GET /profiles/` mocked to one profile, `/setup` renders "Unlock your profile", the name, a password field | yes |
| HC-SRE-002 | same | submitting calls `POST /profiles/login` with `{profile_id, password}` and navigates to `/inbox`; the auth store holds the new token | yes |
| HC-SRE-003 | same | a 401 shows "Incorrect password" with `role="alert"` and stays on `/setup` | yes |
| HC-SRE-004 | `src/frontend/e2e/session-reentry.spec.ts` (new) | create a profile, clear the token from the persisted auth store (simulated expiry), reload: `/setup` shows Unlock; unlock with the password lands on the Inbox; the recovery code was not used | yes |
| HC-SRE-005 (Task 2) | `be/tests/test_profile_connection_401.py` (new, `route_client`) | an authenticated request to a profile-data route with no open profile connection gives 401 with the same detail | yes |

**Files:** Task 1: `fe/pages/ProfileSetup.tsx`, `fe/__tests__/ProfileSetup.test.tsx`, `src/frontend/e2e/session-reentry.spec.ts` (new). Task 2: `be/core/auth.py` (`:305-310` only), `be/tests/test_profile_connection_401.py` (new), slots. **Delta:** Task 1: 0 backend, +3 Vitest, +1 e2e; Task 2: +1. **Est:** 2.5 h + 0.5 h. **Acceptance:** RED/GREEN per id; `npx tsc --noEmit`; Vitest from Windows or CI (RUNBOOK §6.5); e2e in CI. **Owner gates:** SESSION-REENTRY (a); Task 2 also **SESSION-AUTH-DIFF** (new, [item 2](#owner-gates)). **Order:** Task 1 ready; disjoint from MVP-REAUTH-401 (different files). **MVP:** P0.

### MVP-REAUTH-401 — a wrong password on Delete, Restore or Recovery code logs the user out

**Facts:** `be/api/profiles.py:608-611` (regenerate recovery code), `:826-831` (delete), `:1126-1130` (change password) and `be/api/backup.py:414-417` (restore) return 401 "Incorrect password" for a wrong re-auth password. `fe/services/api.ts:108-110` `handleResponse` calls `handleAuthError(status)` for every non-OK response, and `:65-69` clears auth and redirects to `/setup` on any 401. Callers: `fe/services/profiles.ts:65` (recovery code), `:97` (`apiDelete` profile), `fe/services/backup.ts:103-110` (restore). No frontend caller of change-password (grep).

**Design (frontend only; backend unchanged):** `apiPost` / `apiDelete` (and the shared `handleResponse`) accept an optional `{ reauth: true }`; with it, a 401 is thrown as `ApiError(401, …)` without `handleAuthError`. The three callers pass it. Every other 401 behaves as today.

**Test-first:**

| Id | File | Assertion | RED today? |
|---|---|---|---|
| HC-RA4-001 | `fe/__tests__/api.test.ts` (extend) | `apiDelete(url, body, { reauth: true })` on a 401 throws `ApiError` with status 401 and leaves `useAuthStore` token set, no `location.replace` | yes |
| HC-RA4-002 | same | `apiGet` on a 401 still clears auth and redirects (pin) | GREEN (pin) |
| HC-RA4-003 | `fe/__tests__/DangerZone.test.tsx` (extend) | delete with a wrong password shows "Incorrect password" and the auth store keeps the token | yes |
| HC-RA4-004 | `fe/__tests__/BackupRestoreFlow.test.tsx` (extend) | restore with a wrong password: same | yes |

**Files:** `fe/services/api.ts`, `fe/services/profiles.ts` (`:60-70`, `:95-98` only), `fe/services/backup.ts` (`:103-112` only), `fe/__tests__/api.test.ts`, `fe/__tests__/DangerZone.test.tsx`, `fe/__tests__/BackupRestoreFlow.test.tsx`. **Delta:** 0 backend, +4 Vitest. **Est:** 1 h. **Owner gates:** SESSION-REENTRY (a) ("fix the 401-means-logout handling"). **Order:** ready. **MVP:** P0.

### EXPORT-STORE-PURGE — doctor summaries, packets and FHIR bundles stay in process memory after delete or logout

**Facts:** `be/api/export.py:44-51` three module-level dicts; writes `:457` (summary, after strict redaction), `:821` (packet), `:1254` (FHIR); reads check `profile_id` (`:510-520`). Nothing removes entries: after a profile delete, logout or lock they stay until the process exits, unbounded.

**Design:** `api/export.py` gains `purge_profile_exports(profile_id) -> int` (removes every entry whose `profile_id` matches, in all three stores) and a 30-minute TTL checked at each write and read (entries carry `created_at`). `api/profiles.py` calls `purge_profile_exports` after a successful delete (`:772` route), logout (`:437`) and lock (`:992`), one line each, after the auth decision. The purge never touches the database.

**Test-first** (`be/tests/test_export_store_purge.py`, new, `route_client`): HC-ESP-001 generate a summary (`POST /export/doctor-summary`), `POST /profiles/logout`, `GET /export/doctor-summary/{id}/download` → 404; HC-ESP-002 same after lock; HC-ESP-003 after delete the stores hold no entry for the profile (direct dict check) and another profile's entry survives; HC-ESP-004 an entry older than 30 min (clock patched) → 404. All RED today.
**Files:** `be/api/export.py` (stores + one helper + TTL checks), `be/api/profiles.py` (three one-line calls only), `be/tests/test_export_store_purge.py` (new), slots. **Delta:** +4. **Est:** 1.5 h. **Owner gates:** **EXPORT-PURGE-DIFF** (new, merge only: `api/profiles.py` holds the login, unlock and delete routes, so the three call-site lines are treated as auth-adjacent and the exact diff goes to the owner; [item 5](#owner-gates)). **Order:** ready (build to draft); never beside SESSION-REENTRY Task 2 or TEST-RESET-ROUTE. **MVP:** P2.

---

## Lab import and extraction

`be/modules/extract.py` is one file for five rows. They run one after the other in the order listed (MVP impact first), or L0 bundles them. All follow #294 (merged `0e2799b`). Every row: new tests only in its named test file; **an existing golden or pipeline test that changes expectation stops the row** (CLAUDE.md §3; it may be right).

### EXTRACT-TABLE-VALUE — a table cell `1,234` is stored as 1.0, `<0.5` as 0.5 and `5.9 H` loses its flag

**Facts (`0e2799b`):** `be/modules/extract.py:283-295` takes the value with `VALUE_PATTERN.search(value_text)` (`:82-85`, `(\d+\.?\d*)`), so the first digits win: `1,234` → `1.0`, `<0.5` → `0.5`, `5.9 H` → `5.9`; the flag is read only from the flag column (`:315-321`); `:335` keeps `value_text` only when no number was found. The MVP pass reproduced all three on a ruled grid PDF (`[R]`). `api/documents.py:651` stores `is_abnormal = flag is not None`.

**Design:** a full-cell parse replaces `.search`: `^\s*(?P<cmp>[<>]=?|≤|≥)?\s*(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?P<unit>` + `_UNIT_ALT` + `)?\s*(?P<flag>\(?(?:HH|LL|H|L|A|HIGH|LOW|ABNORMAL|CRITICAL)\)?|\*)?\s*$` (case-insensitive, `fullmatch`). Thousands separators are removed before `float`. **A comparator (`<`, `>`, `<=`, `>=`) never becomes an exact number:** `value=None`, `value_text` = the cell text (the observation needs verification, as any `value_text` row). A flag in the cell sets `flag` when the flag column is empty; `*` maps to `A` (abnormal; the conservative direction, it asks for review). A cell that does not fully match keeps `value=None`, `value_text` = cell (today it would take the first digits). A leading `(H) 5.9` form: same pattern with the flag group allowed first.

**Test-first** (`be/tests/test_extraction_pipeline.py`, new tests, calling `_parse_table_row` and one PDF through `extract_from_pdf`):

| Id | Cell | Expected | RED today? |
|---|---|---|---|
| HC-ETV-001 | `1,234` | value 1234.0 | yes |
| HC-ETV-002 ×3 | `<0.5`, `>90`, `<=5` | value None, value_text the cell | yes |
| HC-ETV-003 ×3 | `5.9 H`, `(H) 5.9`, `5.9*` | value 5.9, flag `H` / `H` / `A` | yes |
| HC-ETV-004 | `12.5 (calc)` | value None, value_text `12.5 (calc)` | yes |
| HC-ETV-005 | `105` with flag column `H` and cell `105 L` | flag `H` (column wins) | yes |
| HC-ETV-006 | `4.2 mg/L` | value 4.2 (unit in cell still accepted) | GREEN (pin) |
| HC-ETV-007 | a generated ruled-grid PDF (reportlab or pdfplumber-readable fixture built in the test) with the four cells above, through `POST /documents/import` (`route_client`) | stored observations have the values/flags above | yes |

**Files:** `be/modules/extract.py` (`_parse_table_row` `:261-344` only), `be/tests/test_extraction_pipeline.py` (new tests only), slots. **Re-run, not edited:** `tests/test_extraction_golden.py`, `tests/test_documents_api.py`, `tests/test_source_spans.py`, `tests/test_unit_conversion.py`. **Delta:** +11. **Est:** 1.5 h. **Owner gates:** none (medical data path: say so in the PR). **Order:** first of the extract chain; ready. **MVP:** P0.

### EXTRACT-PAGE-MERGE — a page with any table skips the text pass, so a summary box hides the lab lines

**Facts:** `be/modules/extract.py:153-175`: a page whose tables gave at least one observation (`page_table_count`, `:159-165`) never runs `_extract_from_text` (`:168-174`). The MVP pass's `summary_table_plus_text.pdf` (3-row summary box + 6 analyte lines) gave 2 observations (`Overall`, `Reviewed`); Glucose and HbA1c were lost (`[R]`).

**Design:** on a page with tables, use `page.find_tables()` (bboxes) and run the text pass on `page.outside_bbox(bbox)` for each table (pdfplumber API), so table text is never parsed twice; keep the existing unit-required filter for text observations on table pages (`:172-173`); de-duplicate by `(analyte_raw.lower(), value)` per page as a backstop. A page without tables is unchanged.

**Test-first** (`be/tests/test_extraction_pipeline.py`): HC-EPM-001 a generated PDF with a 3-row non-lab box table and 6 analyte text lines gives the 6 analytes (RED); HC-EPM-002 a ruled lab grid page gives the same observations as today, no duplicates (GREEN pin); HC-EPM-003 a grid row repeated as text gives one observation (pin).
**Files:** `be/modules/extract.py` (`extract_from_pdf` page loop `:150-175` only), `be/tests/test_extraction_pipeline.py`, slots. **Delta:** +3. **Est:** 1.5 h. **Order:** after EXTRACT-TABLE-VALUE. **MVP:** P0.

### IMPORT-SCANNED-PAGE — a scanned page inside a text PDF loses its values with no warning

Owner: **OCR-FOR-MVP answered "(b) Bundle RapidOCR"** (owner prompts 40-41, owner-decisions row OCR-FOR-MVP, L0 PR #301). The no-text-page warning is built **regardless of OCR** (it is what a patient sees whenever a page is not read, including before RAPIDOCR-BUNDLE and when OCR is off).

**Facts:** `be/modules/ingest.py:146-155` classifies a PDF as `lab_pdf` when the **average** characters per page is at least 50 (`be/modules/extract.py:101-120`, `:119`), so one image page among text pages stays `lab_pdf`. `extract_from_pdf` (`:122-207`) reads each page's text and never reports a page with none; `ExtractionResult.notes` (`:59`) is never set. `be/api/documents.py:283-292` `DocumentImportResponse` has no field for it. The MVP pass: `text_then_scanned_page.pdf` (page 2 an image with HbA1c 9.1) gave 4 observations from page 1, status `parsed`, no warning (`[R]`).

**Design:** `ExtractionResult.pages_without_text: list[int]` (pages whose `extract_text()` has fewer than 20 non-space characters). `_run_extraction_pipeline` returns it; `DocumentImportResponse.pages_without_text: Optional[list[int]] = None` (also on the reprocess response, which reuses the model). `fe/pages/DocumentInbox.tsx` shows, on the last-import card, "Page 2 has no readable text, so its values were not read. Check the original report." (`role="status"`), plural form for several pages. No status change, no new DB column.

**Test-first:** HC-ISP-001 (`be/tests/test_extraction_pipeline.py`) a generated 2-page PDF (text page + image-only page) gives `pages_without_text == [2]` (RED); HC-ISP-002 (`be/tests/test_documents_api.py`, `route_client`) the import response carries `pages_without_text: [2]` (RED); HC-ISP-003 an all-text PDF gives `[]` / `null` (pin); HC-ISP-004 (`fe/__tests__/DocumentInbox.test.tsx`) the notice renders with the page number (RED).
**Files:** `be/modules/extract.py` (`ExtractionResult` + `extract_from_pdf` only), `be/api/documents.py` (`DocumentImportResponse` + the two pipeline return dicts + the response build only), `fe/pages/DocumentInbox.tsx` (last-import card only), `fe/services/documents.ts` (type field only), tests above, slots. **Delta:** +3 backend, +1 Vitest. **Est:** 1.5 h. **Order:** after EXTRACT-PAGE-MERGE (`extract.py`) and FE-IMPORT-ERROR (`DocumentInbox.tsx`). **MVP:** P0.

### EXTRACT-TEXT-FORMS — common Quest/LabCorp text lines give no observation

**Facts:** `be/modules/extract.py:67-70` `_UNIT_ALT` lacks `x10E3/uL`, `x10^3/uL`, `10*3/uL`, `x10E6/uL`, `mL/min/1.73m2`; the three line patterns (`:347-355`, `:358-366`, `:371-380`) accept no `<`/`>` before the value, no flag between value and unit in `LINE_PATTERN`/`ALT_LINE_PATTERN`, and no `>=` / `>OR=` range. Lines from the MVP pass (agent-measured; the row re-measures each): `WBC 5.9 H x10E3/uL 3.4-10.8`, `Creatinine <0.5 mg/dL 0.5-1.2`, `eGFR >90 mL/min/1.73m2 >OR=60`, `Glucose 105 mg/dL H 70-99`.

**Design:** add the units (longest first); an optional comparator before the value in all three patterns, which sets `value=None`, `value_text` = comparator + number (as EXTRACT-TABLE-VALUE); `COLUMN_LINE_PATTERN` range gains `>=`, `>OR=`, `<=`, `<OR=` (sets one bound). Linear-time check per pattern (HC-ETF-006 pins it).

**Test-first** (`be/tests/test_extraction_pipeline.py`): HC-ETF-001…004 one per line above with the expected value/value_text, unit, flag and range (RED); HC-ETF-005 every HC-EXU and existing column-line test unchanged (re-run); HC-ETF-006 `"WBC " + " " * 50000 + "x"` parses in under 1 s (pin).
**Files:** `be/modules/extract.py` (`_UNIT_ALT`, the three patterns, `_parse_text_line` comparator handling only), `be/tests/test_extraction_pipeline.py`, slots. **Delta:** +5. **Est:** 1.5 h. **Order:** after IMPORT-SCANNED-PAGE (`extract.py`). **MVP:** P1.

### EXTRACT-DOB-FORMS — three date-of-birth layouts still become the collection date

**Facts:** #294's `_BIRTH_LABEL_TAIL_RE` (`be/modules/extract.py:710-714`) requires the label to end within `\s{0,3}[:\-]?\s{0,3}$` of the date in a 32-character window (`:715-723`). Not caught (bug-fix agent follow-up, re-checked by reading the regex): `DOB (MM/DD/YYYY): 01/02/1960` (a parenthesised format hint between label and date), `DOB/Sex: 01/02/1960 F` (a combined label), and table layouts where the header row says `DOB` and the date is in the next text line (`Name  DOB  Collected` / `Jane  01/02/1960  03/04/2026`). With EXTRACT-DATE-PRIORITY (a) "keep earliest" (`api/documents.py:661-665` `min()`), each uncaught DOB becomes the document date.

**Design:** (1) the tail regex accepts an optional parenthesised hint of at most 14 characters (`(?:\([^()\n]{0,14}\))?`) and a combined label `dob\s*/\s*(?:sex|gender|age)`, still on the fixed window (stays linear); (2) column layout: when a text line contains a birth label as a whitespace-separated header token, the date in the **same column position** of the next line is skipped (token index match), no cross-page state. Never invent a date.

**Test-first** (`be/tests/test_date_extraction.py`): HC-EDF-001 `DOB (MM/DD/YYYY): 01/02/1960` + `Collected: 03/04/2026` → `['2026-03-04']`; HC-EDF-002 `DOB/Sex: 01/02/1960 F` → same; HC-EDF-003 the two-line header layout → same; HC-EDF-004 HC-DATE-009's 50,000-space pin with the new regex under 1 s; HC-EDF-005 a header `Collected` column date is kept (pin).
**Files:** `be/modules/extract.py` (`_BIRTH_LABEL_TAIL_RE` + `_extract_dates` only), `be/tests/test_date_extraction.py`, slots. **Delta:** +5. **Est:** 1.5 h. **Order:** after EXTRACT-TEXT-FORMS (`extract.py`). **MVP:** P1.

### NORMALIZE-COMMA-NAMES — `Cholesterol, Total` does not map to `total_cholesterol`, so trends split and units are not converted

**Facts:** `be/modules/normalize.py:278-292` `normalize_analyte` looks up `raw_name.lower().strip()` in `_synonym_to_canonical`; `:169` synonyms for `total_cholesterol` are `cholesterol`, `total chol`, `tc`. Quest/LabCorp print `Cholesterol, Total`, `Glucose, Serum`, `Vitamin D, 25-Hydroxy`.

**Design:** before the lookup, a second try with a normalised key: comma-reordering for `X, Total` → `total x`, and dropping a trailing specimen qualifier from a fixed list (`, serum`, `, plasma`, `, blood`, `, whole blood`, `, urine` only); then the existing lookup. Never fuzzy matching. Add the three display forms above as explicit synonyms where reordering is not enough (`vitamin d, 25-hydroxy`).

**Test-first** (`be/tests/test_normalize_comma_names.py`, new): HC-NCN-001 ×3 the three names map to `total_cholesterol`, `glucose`, `vitamin_d` (RED); HC-NCN-002 `Urine, Protein` stays unmapped (no qualifier strip at the front, pin); HC-NCN-003 every existing synonym maps as before (loop over `ANALYTE_SYNONYMS`, pin).
**Files:** `be/modules/normalize.py` (`normalize_analyte` + synonyms only), `be/tests/test_normalize_comma_names.py` (new), slots. **Delta:** +5. **Est:** 1 h. **Order:** ready (not `extract.py`). **MVP:** P1.

### FE-IMPORT-ERROR — any import failure shows nothing on screen

**Facts:** `fe/pages/DocumentInbox.tsx:83-94` `handleFileUpload` catches every error and only calls `console.error` (`:91-93`). A 413, a 400 "unsupported type" or a 500 leaves the page unchanged.

**Design:** an `importError` state set from `ApiError.message` (the server `detail`, `fe/services/api.ts:96-112`), shown in a dismissible `role="alert"` above the drop zone with the file name; cleared on the next successful import. Copy for 413: "This file is too large to import."

**Test-first** (`fe/__tests__/DocumentInbox.test.tsx`, extend): HC-FIE-001 a rejected mutation (400, detail "Unsupported file type") renders `role="alert"` with that text (RED); HC-FIE-002 413 shows the size copy (RED); HC-FIE-003 a later success clears it (RED).
**Files:** `fe/pages/DocumentInbox.tsx` (`handleFileUpload` + one alert block), `fe/__tests__/DocumentInbox.test.tsx`. **Delta:** +3 Vitest. **Est:** 0.75 h. **Order:** ready; before IMPORT-SCANNED-PAGE (same page). **MVP:** P0.

### FE-VERIFY-NUMERIC — editing a value to `7,5` saves and verifies 7

**Facts:** `fe/pages/VerificationWorkbench.tsx:157-169` `handleSaveEdit` uses `parseFloat(editValue)` (`:160`), so `7,5` → 7 and `7.5abc` → 7.5, then verifies; the dialog closes (`:168`) even if the mutation fails, and mutation errors are not shown (`:129-150` also have no error path). This is a medical value the patient confirms.

**Design:** strict parse: `^\s*-?\d+(?:\.\d+)?\s*$` → number; `^\s*-?\d+,\d+\s*$` → inline error "Use a dot for decimals, for example 7.5" (never silently converted); `<`/`>`-prefixed or other text → `value_text` as today; anything else non-empty and not matching → inline error. The dialog stays open on error or mutation failure and shows the server detail. Save is disabled while invalid.

**Test-first** (`fe/__tests__/VerificationWorkbenchEdit.test.tsx`, **new file**, so it never shares #295's `VerificationWorkbench.test.tsx`): HC-FVN-001 `7,5` shows the inline error and sends no request (RED); HC-FVN-002 `7.5abc` → error, no request (RED); HC-FVN-003 `7.5` sends `value: 7.5` (pin); HC-FVN-004 `<0.5` sends `value_text: "<0.5"` (pin); HC-FVN-005 a rejected mutation keeps the dialog open with the detail (RED).
**Files:** `fe/pages/VerificationWorkbench.tsx` (`handleSaveEdit` + edit dialog only), `fe/__tests__/VerificationWorkbenchEdit.test.tsx` (new). **Delta:** +5 Vitest. **Est:** 1 h. **Owner gates:** none (medical data path: say so in the PR). **Order:** ready; never beside a PR that edits `VerificationWorkbench.tsx` (#295 does not). **MVP:** P1.

### RAPIDOCR-RESEARCH — confirm RapidOCR's licence, offline behaviour, size and accuracy before bundling it

Owner: **OCR-FOR-MVP answered "(b) Bundle RapidOCR"** (prompt 40). The option text said "Apache-2.0, offline… accuracy on lab tables unmeasured"; this row checks those premises before code.

**Facts already read (planner, PyPI JSON 2026-10-22):** `rapidocr` 3.10.0, `license_expression` Apache-2.0, one wheel `rapidocr-3.10.0-py3-none-any.whl` 27,288,134 bytes; `requires_dist` includes `opencv-python-headless`, `Shapely`, `pyclipper`, `omegaconf`, `PyYAML`, `tqdm`, `colorlog` **and `requests`** (a network-capable dependency; whether it is used at runtime is what step 2 measures); `onnxruntime` is separate.

**Steps (scratch venv and scratch dir on the GPU box; nothing under `src/`):**
1. **Licences** of every package the install adds (`pip install rapidocr onnxruntime` into a scratch venv; `pip-licenses` or each `METADATA`), and of the bundled model files (PP-OCR detection/recognition/classifier: their licence and source, read from the model card or the package's config).
2. **No network at runtime:** run OCR on one image inside `unshare -n` (or with `socket.socket` patched to raise) after install; record whether it downloads models on first use, from where, and which config keeps it offline. Also: does it write to `~/.cache` or the package dir.
3. **Size:** installed size of the added packages (`du -sh` of site-packages delta), model files, per platform wheels for `onnxruntime` and `opencv-python-headless` (win_amd64, macOS arm64, manylinux) from PyPI JSON.
4. **Rasterising without Poppler:** `pypdfium2` is already installed (a `pdfplumber` 0.11.10 dependency, `importlib.metadata.requires('pdfplumber')`); measure page → image at 200 and 300 dpi.
5. **Accuracy:** 10 synthetic lab-report pages (the MVP pass layouts: ruled grid, column text, summary box), rendered to images with mild blur/rotation/JPEG noise; run RapidOCR → `_extract_from_text` on the OCR text; report per-page analytes found / correct value / correct unit against ground truth, and the same with Tesseract if installed. CPU time per page.
6. A recommendation (adopt as planned / adopt with changes / do not adopt) with the numbers; any premise that fails goes back to the owner.

**Files:** `docs/research/2026-10-22-rapidocr/00-README.md` (new), `docs/INDEX.md`, `docs/_link_graph.json`. **Est:** 4 h. **Runtime:** claude on the GPU box (network only to install into the scratch venv). **Owner gates:** OCR-FOR-MVP (b). **Order:** ready; never beside another model-host measurement. **If a premise fails** (licence, runtime network, size beyond about 150 MB added, or accuracy unusable): L0 asks the owner again with the numbers; RAPIDOCR-BUNDLE stays blocked. **MVP:** P1.

### RAPIDOCR-BUNDLE — read scanned pages locally with RapidOCR, models bundled like the embedding model

**Design (re-planned by the research if it changes anything):** new dependency **`rapidocr` + `onnxruntime`** (+ their transitive `opencv-python-headless`, `Shapely`, `pyclipper`, …) in `be/requirements.txt`, exact pins, licences listed in the PR. Model files are **not** fetched at runtime: `be/scripts/download_models.py` gains an `ocr` subcommand (pinned file list + sha256, exclusive `.partial` dir, same rules as `cmd_embedding` `:332-390`) into a gitignored `be/models/ocr/`; the launchers call it after DEV-EMB-FETCH. `be/modules/extract.py` `extract_from_scanned_pdf` / `extract_from_image` use RapidOCR when the bundle is present (pages rasterised with `pypdfium2`, no Poppler), with the RapidOCR config pointing at the local model paths only; Tesseract stays the fallback when installed. `be/core/config.py` `is_ocr_available()` / `compute_ocr_effective()` (`:295-326`) count RapidOCR as an engine; whether `ocr_enabled` (`:132`, default `False`) changes default is decided in the plan delta after the research, quoting the owner's "(b)" text. OCR observations keep base confidence 0.4 and need verification. IMPORT-SCANNED-PAGE's notice now also lists pages OCR could not read.
**Test-first sketch:** a socket-blocking test (`socket.socket` patched to raise) runs OCR on a generated image with the bundle present (GREEN only without network); a missing bundle gives `ocr_unavailable=True`, never a download; a synthetic scanned page gives the expected analytes; route test via `route_client` that a scanned import is parsed, not `pending_ocr`. Ids HC-OCR-001…005.
**Files (provisional):** `be/requirements.txt`, `be/scripts/download_models.py`, `be/modules/extract.py`, `be/core/config.py` (OCR availability only), `dev.ps1`, `dev.sh`, `.gitignore` (one line, `src/backend/models/ocr/`), `be/tests/test_ocr_rapid.py` (new), slots. **Est:** 5 h. **Owner gates:** OCR-FOR-MVP (b); the research must confirm no network at runtime. **Order:** blocked on RAPIDOCR-RESEARCH (merged) and the plan delta it triggers; after the extract chain (`extract.py`) and SQLCIPHER-WHEEL / the launcher rows (`requirements.txt`, `dev.ps1`, `dev.sh`). **MVP:** P1 if the research lands before 2026-10-27, else P2.

---

## Test tooling (TEST-DEV-DEPS (a))

Owner: **TEST-DEV-DEPS answered "(a) Add both (Recommended)"** (owner prompts 40-41, owner-decisions row TEST-DEV-DEPS, L0 PR #301). Both are dev-only (MPL-2.0), never shipped.

### HYPOTHESIS-EXTRACT — Hypothesis as a backend dev dependency, first property tests on the extractor

**Design:** `be/requirements.txt` "# Development" block (`:113-117`, beside `pytest`): `hypothesis==6.170.6` (the version the research read; the row re-reads PyPI and pins the latest at build time). New `be/tests/test_extract_properties.py` with `@settings(derandomize=True, database=None, max_examples=200, deadline=None)` so CI is deterministic and writes no `.hypothesis/` dir. Properties that hold **today** (so the row is not blocked on the fix rows): HC-PROP-001 `_parse_text_line` never raises on arbitrary text; HC-PROP-002 `_extract_dates` returns only ISO `YYYY-MM-DD` strings within `_date_is_plausible`; HC-PROP-003 a date directly after `DOB: ` is never returned (any plausible date, formats from the generic list); HC-PROP-004 a parsed range has `ref_low <= ref_high` when both are set; HC-PROP-005 `_extract_dates` on `label + spaces*n + date` stays under 1 s for n up to 20,000. EXTRACT-TABLE-VALUE and EXTRACT-TEXT-FORMS may add properties once merged (not this row).
**Files:** `be/requirements.txt` (one line in the Development block), `be/tests/test_extract_properties.py` (new), slots. **Delta:** +5. **Est:** 1 h. **Order:** ready; never beside SQLCIPHER-WHEEL or RAPIDOCR-BUNDLE (`requirements.txt`, different hunks but the same file). If a property fails today, that is a found bug: stop and report it with the shrunk example, do not loosen the property. **MVP:** P2.

### AXE-E2E — @axe-core/playwright in the e2e suite

**Design:** `src/frontend/package.json` devDependency `@axe-core/playwright` (exact version, research read 4.14.0; re-read at build) + `package-lock.json`. New `src/frontend/e2e/accessibility.spec.ts`: for `/setup`, `/inbox`, `/verify`, `/trends`, `/explain`, `/settings` (authenticated via `e2e/support/auth.ts`), `new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa']).analyze()`; assert no violation of impact `critical` or `serious` except rule ids in a `KNOWN_A11Y` map, each entry naming the bullet that will fix it (FE-A11Y-DIALOGS) and the route. The first run's full violation list goes in the PR body. An entry may only be removed, never added later without a row. Runs in the existing CI e2e job (Playwright `testDir`), `ci.yml` not touched.
**Files:** `src/frontend/package.json`, `src/frontend/package-lock.json`, `src/frontend/e2e/accessibility.spec.ts` (new). **Delta:** 0 backend, +6 e2e. **Est:** 1.5 h. **Order:** ready; never beside another `package.json` PR. **MVP:** P2.

---

## Chat, interpretation and model rows

### FE-EXPLAIN-ERR — the chat's 401/403/501 messages never show, and the send button has no name

**Facts (re-read after #295):** `fe/pages/ExplainAssistant.tsx:405-419` `getErrorContent` tests `error.message.includes('501' | '401' | '403')`, but `ApiError.message` is the server `detail` (`fe/services/api.ts:96-112`), so the branches never match; `:795-815` the question input and the icon-only send button have no accessible name.

**Design:** branch on `error instanceof ApiError && error.status === 501 | 401 | 403`; keep the network branch; `aria-label="Your question"` on the input and `aria-label="Send question"` on the button.
**Test-first** (`fe/__tests__/ExplainAssistant.test.tsx`, extend after #295): HC-FEE-001 `ApiError(403, …, "Profile database not available…")` shows the session message (RED); HC-FEE-002 `ApiError(501, …)` shows the no-model message and sets `modelUnavailable` (RED); HC-FEE-003 `getByRole('button', { name: 'Send question' })` exists (RED).
**Files:** `fe/pages/ExplainAssistant.tsx` (`getErrorContent` + two attributes), `fe/__tests__/ExplainAssistant.test.tsx`. **Delta:** +3 Vitest. **Est:** 0.5 h. **Order:** after #295 (same two files). **MVP:** P1.

### AGENT-DATEONLY-TZ — a date-only lab date is shown one day early in western time zones

**Facts:** `be/modules/agent/nodes/draft.py:93-99` `_local_date` converts every value with `to_local` (`be/core/time.py:66-70`, naive = UTC), so a lab dated `2026-03-02` (stored as naive midnight) prints "Mar 01, 2026" for `America/Los_Angeles`; used at `:125` and `:171`. The MVP pass found the no-model fallback prints Mar 02.

**Design:** a `datetime.date` (not `datetime`) or an ISO string of length 10, and a naive `datetime` at exactly `00:00:00.000000`, are formatted as the calendar date with no zone conversion; everything else as today. Tradeoff, stated in the PR and to the owner by L0: a real event stored at exactly midnight UTC would now show the UTC date; lab collection dates from extraction are date-only (`api/documents.py:661` `_parse_date_string`), so this matches what the report printed.
**Test-first** (`be/tests/test_assist_agent_dates_http.py`, extend; `route_client`): HC-ADT-001 profile tz `America/Los_Angeles`, verified observation collected `2026-03-02 00:00:00` → the agent answer says "Mar 02, 2026" (RED); HC-ADT-002 a timed value `2026-03-02T03:00:00` (UTC) still shows Mar 01 in LA (pin).
**Files:** `be/modules/agent/nodes/draft.py` (`_local_date` only), `be/tests/test_assist_agent_dates_http.py`, slots. **Delta:** +2. **Est:** 0.75 h. **Order:** ready. **MVP:** P1.

### LEGACY-ADVICE-GATE — with the agent off or failed, an advice question reaches the model

**Facts (`0e2799b`):** the pre-model `classify_advice` gate runs only inside the agent graph (`be/modules/agent/graph.py:169-173`). `be/api/assistant.py:1020-1055`: when the agent flag is off, or the agent raised (`:1036-1045`), the legacy `rag.query` runs (`:1054-1055`) with only the post-hoc prohibited-pattern check (`:1115-1124`).

**Design:** in `chat()`, before the legacy branch (`:1054`), call `classify_advice(request.question)`; when `is_advice_seeking`, serve `ESCALATE_TEMPLATE` exactly as the prohibited path does (same segment shape, same `assistant.prohibited_blocked`-style audit with reason `pre_model_advice`, no question text in the audit), and never call the runner. The agent path is unchanged. Safety semantics: **L0 tells the owner** (more questions are escalated on the legacy path; none fewer).
**Test-first** (`be/tests/test_legacy_advice_gate.py`, new, `route_client`): HC-LAG-001 agent flag off, "Should I stop taking metformin?" → `ESCALATE_TEMPLATE`, runner not called (RED); HC-LAG-002 agent raises → same (RED); HC-LAG-003 a factual question still reaches `rag.query` (pin); HC-LAG-004 the audit row has no question text (pin).
**Files:** `be/api/assistant.py` (`chat()` legacy branch only), `be/tests/test_legacy_advice_gate.py` (new), slots. **Delta:** +4. **Est:** 1.5 h. **Order:** after #264 (B-3, parked: it changes the same legacy branch's judge) and after #300 (same file). **MVP:** P1 (the demo runs with the agent on).

### RAG-TIMEOUT-ANSWER — a generation timeout is served and saved as a normal answer

**Facts:** `be/modules/rag.py:1458-1461` (`_generate_with_runner`) and `:854-858` (`generate_response`) return a canned `"UNCERTAINTIES: I was unable to fully process your question within the time limit…"` string when `finish_reason == "timeout"`; it is validated and persisted as an assistant turn.

**Design:** on timeout raise a dedicated `GenerationTimeoutError(RuntimeError)` (no provider text); `query()` catches it and returns the existing abstain path (`ABSTAIN_TEMPLATE` shape, `is_valid=False`, `insufficient_reasons=["generation_timeout"]`), so the route serves the abstain message and the turn is stored as an abstention, not an answer.
**Test-first** (`be/tests/test_rag_timeout_answer.py`, new; HTTP via `route_client` on `/assistant/chat`, agent off): HC-RTA-001 runner returns `finish_reason="timeout"` → response is the abstain text (RED); HC-RTA-002 the persisted turn is marked as not valid / abstained (RED); HC-RTA-003 a normal answer unchanged (pin).
**Files:** `be/modules/rag.py` (the two timeout branches + `query()` catch only), `be/tests/test_rag_timeout_answer.py` (new), slots. **Delta:** +3. **Est:** 1 h. **Order:** after #297 (the serialised llama path changes how timeouts surface; re-read then). #264 (parked) also edits `rag.py`. **MVP:** P1.

### RUNNER-EXC-INTERP — four log lines and one exception message interpolate the provider exception text

**Facts:** `be/modules/rag.py:863-865` and `:1472-1474`: `self._logger.error(f"LLM generation failed: {e}")` and `raise RuntimeError(f"Failed to generate response: {e}")`; `be/modules/interpret.py:783-784` `logger.error(f"LLM interpretation failed: {e}, …")`; `be/api/interpretations.py:881-882` `logger.error(f"Batch interpretation error for {obs_id}: {e}")`. Provider text can carry prompt (PHI) fragments; RUNNER-EXC-LOG (#285) and RUNNER-EXC-CHAIN (#300) fixed the runner and two route handlers, not these.

**Design:** log `type(e).__name__` only; the `RuntimeError` message becomes the fixed `"Failed to generate response"` with `from e` kept (the chain is never printed by these handlers after #300).
**Test-first** (`be/tests/test_runner_exc_interp_logs.py`, new): HC-REI-001 a provider raising `RuntimeError("SECRET-PHI-123")` through `RAGModule._generate_with_runner`: no log record and no `str()` of the raised error contains the token (RED); HC-REI-002 same for `generate_response`; HC-REI-003 `InterpretModule` LLM path; HC-REI-004 `POST /interpretations/batch` (`api/interpretations.py:801-802`) via `route_client` (each RED).
**Files:** `be/modules/rag.py` (the two `except` blocks only), `be/modules/interpret.py` (`:783-784` only), `be/api/interpretations.py` (`:881-882` only), `be/tests/test_runner_exc_interp_logs.py` (new), slots. **Delta:** +4. **Est:** 0.75 h. **Order:** after #300 (`api/interpretations.py`) and #304 (`modules/interpret.py`); never beside INTERP-SAFETY-ENFORCE or INTERP-REGEN-500 (`interpret.py`). **MVP:** P1.

### LLAMA-UNLOAD-LOOP — switching provider blocks the event loop while a generation runs

**Facts:** `be/api/model_settings.py:883-906` `async def set_llm_provider` calls `reset_provider()` synchronously (`:906`); `be/core/llm/factory.py:77-85` calls `_active_provider.unload()`. With #297, `LlamaCppProvider.unload()` takes the model lock and the init lock (`with self._model_lock, self._init_lock`), so a switch during a generation blocks the whole event loop (every request) until the generation ends or times out. No other async caller of `reset_provider` / `unload` (grep).

**Design:** `await asyncio.to_thread(reset_provider)`; nothing else.
**Test-first** (`be/tests/test_provider_switch_nonblocking.py`, new, `route_client` + a fake provider whose `unload` blocks on an `Event`): HC-LUL-001 while `PUT /settings/model/provider` waits in `unload`, a concurrent request to another route on the same app answers within 1 s (RED: the loop is blocked); HC-LUL-002 the switch completes after the event is set (pin).
**Files:** `be/api/model_settings.py` (`:906` only), `be/tests/test_provider_switch_nonblocking.py` (new), slots. **Delta:** +2. **Est:** 0.75 h. **Order:** after #297 (the lock) and #295 (same file, other hunk). **MVP:** P1.

### BADGE-TICK — the chat badge flashes a tier label, and names `phi-3-mini` for an auto-detected GGUF

**Facts (re-read after #295/#297):** #295's `activeModelSummary` falls back to the tier label (`modelSettings.tier_availability[tier].model`, e.g. "BioMistral-7B") while `useProviderInfo()` is still loading, so the wrong name shows for one render. `be/core/llm/llama_cpp_provider.py:180-183` `capabilities()` reports `settings.default_chat_model` ("phi-3-mini", `core/config.py:92`) until a model has been loaded, although `_find_model_path` (`:71-98`) would pick another GGUF (gemma4, …); with `probe=false` (#295) no load happens, so the badge names a model that is not the one that will answer.

**Design:** frontend: while provider info is loading, show "Local model" (no tier fallback). Backend: `capabilities()` uses `Path(self._model_path or self._find_model_path()).stem` when a file is found (glob only, no load), else `default_chat_model`.
**Test-first:** HC-BTK-001 (`fe/__tests__/ExplainAssistant.test.tsx`) provider info pending → badge "Local model", never the tier name (RED); HC-BTK-002 (`be/tests/test_llama_capabilities_name.py`, new) a temp models dir with only `gemma-4-e4b-it-Q4_K_M.gguf` → `capabilities().model_name == "gemma-4-e4b-it-Q4_K_M"` and no `Llama` constructed (RED).
**Files:** `fe/pages/ExplainAssistant.tsx` (`activeModelSummary` only), `fe/__tests__/ExplainAssistant.test.tsx`, `be/core/llm/llama_cpp_provider.py` (`capabilities` only), `be/tests/test_llama_capabilities_name.py` (new), slots. **Delta:** +1 backend, +1 Vitest. **Est:** 0.75 h. **Order:** after #295 and #297; never beside FE-EXPLAIN-ERR (same two frontend files) or CPU-DEFAULT-PHI4 (`llama_cpp_provider.py`). **MVP:** P2.

### CPU-DEFAULT-PHI4 — Phi-4-mini is the default chat model on CPU-only machines

Owner: **CPU-DEFAULT-MODEL answered "A and B"** (free text; L0 reading: Phi-4-mini is the default now; Qwen3-4B is added as a measured option once JUDGE-THINK lands; which becomes the long-term default is decided on the measurement; owner prompts 40-41, owner-decisions row CPU-DEFAULT-MODEL, L0 PR #301). This row is part A; QWEN3-4B-TIER is part B; gate CPU-MODEL-FINAL decides after.

**Facts (`0e2799b`):**
1. `be/modules/hardware_detection.py:40` `TIER_ORDER = ["high", "gemma4-12b", "mid", …]` and `:339-357` pick the first tier whose RAM/disk fit; a 16-31 GB CPU-only laptop gets `gemma4-12b` (7-8 GB Q4, a thinking model, no GPU), 32 GB+ gets `high` (BioMistral-7B, 4K context).
2. `be/modules/model_selector.py:85-111` `"mid"` is Phi-4-mini (bartowski Q4_K_M, 16K context, MIT); `be/scripts/download_models.py:100-104` labels it "Tier: mid (Phi-4-mini)"; but `hardware_detection.py:376-379` `get_tier_display_info["mid"]["model"]` still says "Phi-3-mini-4k-instruct".
3. The chat provider picks a file by glob, not by tier: `be/core/llm/llama_cpp_provider.py:81-91` tries `f"{default_chat_model}*.gguf"` first (`core/config.py:92` `"phi-3-mini"`, `config/.env.example:85`), then `gemma4*`, `gemma-4*`, `phi-3*`, … `*.gguf`; a downloaded Phi-4-mini file (`microsoft_Phi-4-mini-instruct-Q4_K_M.gguf`, the selector's `filename_pattern` `q4_k_m`) matches only the last `*.gguf`, after any gemma4 file.

**Design (scope: CPU-only machines; GPU machines unchanged):**
1. `get_recommended_tier_from_hardware`: when the GPU boost does not apply (`gpu_vram_gb` is `None` or below `GPU_VRAM_BUMP_MIN_GB`), skip `gemma4-12b`, so 16-31 GB CPU laptops get `mid` (Phi-4-mini). **`high` on 32 GB+ CPU machines is unchanged in this row** (the existing `test_ram_only_high` pin stays as is); whether it should also become Phi-4-mini is part of CPU-MODEL-FINAL.
2. `core/config.py:92` and `config/.env.example:85`: `default_chat_model` becomes `microsoft_Phi-4-mini-instruct`, so the provider prefers the Phi-4-mini file when present; other files still load as today when it is absent.
3. `get_tier_display_info["mid"]` label → "Phi-4-mini-instruct".
**Test-first** (`be/tests/test_cpu_default_model.py`, new): HC-CPU-001 `get_recommended_tier_from_hardware(16.0, 100.0, None) == "mid"` and `(24.0, 100.0, None) == "mid"` (RED: `gemma4-12b`); HC-CPU-002 `(24.0, 100.0, 16.0) == "high"` (GPU path unchanged, pin); HC-CPU-003 a temp models dir with a gemma4 file and the Phi-4-mini file → `_find_model_path()` returns the Phi-4-mini file (RED); HC-CPU-004 display label (RED). Re-run, not edited: `tests/test_hardware_detection.py` (its `in ("mid", "gemma4-12b")` assertion accepts both).
**Files:** `be/modules/hardware_detection.py` (`get_recommended_tier_from_hardware` + the `mid` display entry only), `be/core/config.py` (`default_chat_model` default only), `config/.env.example` (`DEFAULT_CHAT_MODEL` line only), `be/tests/test_cpu_default_model.py` (new), slots. **Delta:** +4. **Est:** 1 h. **Order:** after #297 (`core/config.py`, `config/.env.example`); never beside BADGE-TICK (provider file is read only here). **MVP:** P0 (stakeholder laptops have no GPU).

### QWEN3-4B-TIER — measure Qwen3-4B on CPU as the candidate long-term default (no product code)

**Steps (GPU box, CPU-only mode `CUDA_VISIBLE_DEVICES=` / `n_gpu_layers=0`, scratch dir):** fetch `Qwen3-4B` Q4_K_M (Apache-2.0; record repo, file, sha256, size) and Phi-4-mini Q4_K_M; for each: (1) `llama-bench` prompt-processing and generation tokens/s on 4 and 8 threads; (2) the judge preview (`gpu-1022/judge_preview.py` shape, 40 texts) with **thinking off** as JUDGE-THINK provides (`/no_think` or the chat-template switch on llama.cpp, `think=false` on Ollama), ALLOW/BLOCK/UNAVAILABLE counts; (3) the MM-4 chat subset (verified-data questions) answer length, citation validity and `finish_reason`; (4) peak RSS. One table, both models, same machine, same day. Evidence file only; it feeds **CPU-MODEL-FINAL**.
**Files:** `docs/reviews/<run date>/qwen3-4b-tier.md` (new), `docs/INDEX.md`, `docs/_link_graph.json`. **Est:** 3 h. **Runtime:** L0 or claude on the GPU box (model host; never beside another model-host run or a pytest run). **Order:** blocked on JUDGE-THINK (#305) merged. **MVP:** P2.

### VISIT-ASSIST-THINK — the gemma4 visit-note assist returns nothing because it thinks through its whole budget

**Facts:** KV evidence ([#298, "Other findings" 1](../reviews/2026-10-22/kv-prefix-measure.md)): with `gemma4:e4b` the visit-note assist answer was empty in 11 of 11 runs (`num_predict` 512, `eval_count` 512, `done_reason: length`); Ollama returned the tokens in `thinking`. `be/modules/extract_visit_notes.py:477-504` calls `runner.generate_async(…, InferenceConfig(max_tokens=512, temperature=0.0))`. JUDGE-THINK (#305, in flight) adds `InferenceConfig.think` and sends it only when set; the owner's JUDGE-THINK (a) was **judge only**, so using it here needs its own answer.

**Design (if VISIT-THINK says yes):** `InferenceConfig(max_tokens=512, temperature=0.0, think=False)` in `llm_assist_visit_entities` only. The hard validation of proposals (`:478-490` docstring) is unchanged.
**Test-first** (`be/tests/test_visit_assist_think.py`, new): HC-VAT-001 the config passed to a recording runner has `think is False` (RED); HC-VAT-002 an `OllamaProvider` body built from it has `"think": false` (RED); HC-VAT-003 the chat and interpretation configs still have no `think` (pin). Model-host check (L0): 11 visit-note runs on `gemma4:e4b` give non-empty answers.
**Files:** `be/modules/extract_visit_notes.py` (`:497-500` only), `be/tests/test_visit_assist_think.py` (new), slots. **Delta:** +3. **Est:** 0.5 h. **Owner gates:** **VISIT-THINK** (new, execution gate, [item 4](#owner-gates)). **Order:** blocked on JUDGE-THINK (#305) merged and VISIT-THINK. **MVP:** P1 (the visit-note assist is opt-in, default off).

### INTERP-REGEN-500 — regenerating an existing interpretation fails with a UNIQUE constraint error

**Facts:** KV evidence ("Other findings" 2): `POST /interpretations/observations/{id}/interpret-grounded?force_regenerate=true` on an observation that already has an interpretation → 500 `UNIQUE constraint failed: lab_interpretations.observation_id`. `be/models/interpretation.py:50-56` `observation_id` is `unique=True`. `be/modules/interpret.py:272-279` (template path) and `:1028-1034` (LLM path) call `profile_db.delete(existing_interp)` then `profile_db.add(interpretation)` and commit once; SQLAlchemy's unit of work emits the INSERT before the DELETE, so the new row collides. `previous_interpretation_id` (`:107`) is not a foreign key. Existing route tests use a fake interpret module (`tests/test_audit_order.py:453`), so they cannot see it.

**Design:** `await profile_db.delete(existing_interp)` followed by `await profile_db.flush()` before `add`, at both sites; nothing else.
**Test-first** (`be/tests/test_interpret_regenerate.py`, new, `route_client`, real `InterpretModule`, template path, in-memory profile DB with the real unique constraint): HC-IRG-001 `POST …/interpret?force_regenerate=true` twice → both 201, `regeneration_count == 1`, `previous_interpretation_id` = the first id (RED: second is 500); HC-IRG-002 same through `interpret-grounded` with the RAG step stubbed (RED); HC-IRG-003 exactly one row remains (pin).
**Files:** `be/modules/interpret.py` (`:276` and `:1031` + one `flush` each), `be/tests/test_interpret_regenerate.py` (new), slots. **Delta:** +3. **Est:** 0.75 h. **Order:** after #304 (INTERP-SAFETY-META, `interpret.py`); never beside INTERP-SAFETY-ENFORCE, RUNNER-EXC-INTERP or B-5. **MVP:** P1 ("Regenerate" on the lab card).

### GAUGE-ZERO-WIDTH — the reference gauge divides by zero when low = high = value

**Facts (re-read after #295):** `fe/components/lab-interpreter/ReferenceRangeComparison.tsx:20-29`: `range = refHigh - refLow`, `padding = range * 0.3`; with #295's axis change, `refLow == refHigh == value` gives `displayMin == displayMax`, `displayRange = 0`, and the percentages are `NaN` (also `0/0` when all are 0).
**Design:** when `range <= 0`, `padding = Math.max(Math.abs(refHigh) * 0.3, 1)`; if `displayRange` is still not a positive finite number, render the text row only (no gauge).
**Test-first** (`fe/__tests__/ReferenceRangeComparison.test.tsx`, new): HC-GZW-001 `value=5, refLow=5, refHigh=5` renders no `NaN` in any `style` (RED); HC-GZW-002 all zero (RED); HC-GZW-003 a normal range unchanged (pin).
**Files:** `fe/components/lab-interpreter/ReferenceRangeComparison.tsx` (`:20-29` only), the new test. **Delta:** +3 Vitest. **Est:** 0.5 h. **Order:** after #295. **MVP:** P2.

### CACHE-DATE-TEST — no test covers the date-entity rows in the agent cache key's `e:` part

**Facts:** #290 review round 2 MINORs: `be/api/assistant.py:780-796` hashes `event_rows + date_rows` into the `e:` part; mutating it to `_digest(event_rows)` leaves all HC-CACHE-VER tests green. `be/tests/test_assistant_cache_version.py:231` calls an in-place `entity_value` edit "a reprocess", but a reprocess deletes and recreates entities under new ids (`api/documents.py:1203`).
**Design:** test only: HC-CACHE-VER-014 (new test in the same file) adds a `visit_date` `DocumentEntity` to a document with no `collection_date` and asserts the version changes (RED under the mutation, which the PR shows by running it once against a scratch copy); fix the `:231` comment to "same row count, different content (an in-place value edit): only the m: hash sees it". `api/assistant.py` not edited.
**Files:** `be/tests/test_assistant_cache_version.py` (one test + one comment), slots. **Delta:** +1. **Est:** 0.3 h. **Order:** ready. **MVP:** P2.

### Delta to existing rows: OLLAMA-NUM-CTX and KV-PREFIX-MEASURE (OQ-KV-LOCK (a))

1. **KV-PREFIX-MEASURE** is done: evidence merged in #298 ([kv-prefix-measure.md](../reviews/2026-10-22/kv-prefix-measure.md)).
2. **OLLAMA-NUM-CTX** is ready with **value 8192** (evidence item 3: the smallest size that holds the largest case plus its output, 4350 + 1024 = 5374 tokens, 100% GPU, about +0.3 GiB VRAM over 4096, at or below every `capabilities().context_len`). The lane A plan's `_OLLAMA_NUM_CTX` constant is `8192`; HC-ONC tests assert 8192. It still never runs beside JUDGE-THINK (#305, same `_build_request_body`); whichever lands second merges `origin/main` and re-runs both test files.
3. **OQ-KV-LOCK answered "(a) Accept the window"** (owner prompts 40-41, owner-decisions row OQ-KV-LOCK, L0 PR #301): after a lock or logout, the last prompt's state may stay in local Ollama memory until `keep_alive` expires (5 min; measured 55 s+ after lock in #298 run 2). No code: no `OllamaProvider.unload`, no `keep_alive` change, no lock hook. OLLAMA-NUM-CTX must not add a `keep_alive` field.

---

## CI and e2e

### CI-CACHE — CI reinstalls torch and the requirements in four jobs with no pip, HF or Playwright cache

**Facts:** `.github/workflows/ci.yml` installs `torch` + `requirements.txt` in backend-tests (`:54-55`), agent-evals (`:215-216`), legacy-evals (`:237-238`) and e2e (`:273-274`); only the npm cache is set (`:104`, `:254`). MVP pass: about 14.5 min critical path (run 39843670560).
**Design:** `actions/setup-python` `cache: pip` with `cache-dependency-path: src/backend/requirements.txt` in those four jobs; `actions/cache` for `~/.cache/ms-playwright` keyed on the Playwright version in `package-lock.json`. No HF cache (no job downloads models today). No job removed, no step skipped.
**Acceptance:** two runs on the PR: the second run's "Install dependencies" step durations against the first, pasted per job; all jobs green. **Files:** `.github/workflows/ci.yml` (setup steps only). **Est:** 1 h. **Runtime:** claude (no slot; owner merges CI files). **Order:** ready; never beside another `ci.yml` PR (SQLCIPHER-WHEEL uses its own workflow file). **MVP:** P2.

### E2E-UIFULL-CI — the real-backend UI suite never runs in CI, and the upload test passes on the file name

**Facts:** `src/frontend/e2e/ui-full-verification.spec.ts:15-49`: the whole suite (routes, chat, settings and the PDF flow) is skipped unless `HC_E2E_REAL_PDF` points at a file (Windows default `F:\…`); CI never sets it. `src/frontend/e2e/document-import.spec.ts:54-57` (E2E-DOC-002) passes on `/test-report\.pdf|pending|needs review|parsed/i`, which the filename echo satisfies even when the backend rejects the file.
**Design:** split the non-PDF part (sidebar routes, chat, settings) into `ui-routes-verification.spec.ts` that always runs; the PDF part uses a committed synthetic text-lab PDF fixture (`src/frontend/e2e/fixtures/synthetic-lab.pdf`, generated by a script in the spec's header comment; no real data) when `HC_E2E_REAL_PDF` is unset. E2E-DOC-002 asserts a document row whose backend status is `parsed` or `needs review` from the documents API (not the toast text).
**Test-first:** E2E-DOC-002 fails against a backend stubbed to reject the upload (shown once in the PR); the new routes spec runs in CI (job log line).
**Files:** `src/frontend/e2e/ui-full-verification.spec.ts`, `src/frontend/e2e/ui-routes-verification.spec.ts` (new), `src/frontend/e2e/document-import.spec.ts` (E2E-DOC-002 only), `src/frontend/e2e/fixtures/synthetic-lab.pdf` (new). **Delta:** 0 backend; e2e count in the PR. **Est:** 2 h. **Order:** ready; never beside SESSION-REENTRY's e2e file (different files; disjoint) or AXE-E2E (disjoint). **MVP:** P1.

---

## Owner gates

None of these is answered. Each is asked by L0 only when its trigger exists; no answer is inferred. Wording is a draft; L0 asks it, the owner's words are recorded verbatim in owner-decisions.

1. **SQLC-WHEEL-DIFF** (SQLCIPHER-WHEEL; merge only; asked with the draft PR's final diff).
   - Question: "Here is the exact change that turns encryption on for Windows and Mac. Linux keeps the package it uses today; Windows and Mac get `sqlcipher3`, which has the encryption built in. The launchers now stop instead of quietly turning encryption off, and the app refuses to start a vault without real encryption. You wrote 'for window'; this also covers Mac. May it merge?"
   - Options: "Merge as shown" (Windows and Mac both get encrypted vaults; tested on the Windows box and in CI on all three systems). "Windows only, not Mac" (Mac stays as today, unencrypted, until a Mac is tested by hand). "Merge, no dev escape" (as shown but without the `HC_ALLOW_UNENCRYPTED=1` developer switch, so a failed install can never fall back to plaintext). "Do not merge" (vaults on Windows and Mac stay unencrypted).
   - Tradeoffs: a stricter launcher means a failed install now stops the first run instead of continuing unencrypted; Linux aarch64 is still unsupported; an existing unencrypted Windows vault is not converted (it stays readable only with encryption off).
   - Analogy: fitting the lock to the back door, and making the door refuse to close without it.
2. **SESSION-AUTH-DIFF** (SESSION-REENTRY Task 2; execution gate for that task only; ask-first `core/auth.py`).
   - Question: "After the app restarts, your sign-in token still looks valid but the profile is closed, so every page shows an error instead of the unlock screen. One status code in the sign-in code (`core/auth.py`, 403 → 401) would send you straight to the unlock screen. Change it?"
   - Options: "Change to 401" (a restart sends you to the unlock screen; the only change is that number). "Leave it as 403" (after a restart you see errors until the token expires, at most 60 minutes, then the unlock screen).
   - Tradeoffs: 401 means "sign in again", which is true here; any other client relying on 403 would see 401 (none in this repo).
   - Analogy: the door telling you "use your key" instead of "access denied".
3. **CPU-MODEL-FINAL** (after QWEN3-4B-TIER; open, not asked; no recommendation until the measurement exists).
   - Question: "On a laptop without a graphics card, which local model should be the default for good: Phi-4-mini (today's default) or Qwen3-4B? Here are the measured speed, judge and answer numbers for both on the same machine. Also: should 32 GB laptops use the same default?"
   - Options: "Keep Phi-4-mini" / "Switch to Qwen3-4B" / "Phi-4-mini, Qwen3 optional" (offered as a choice in Settings) / "Measure again".
   - Tradeoffs: Qwen3-4B depends on thinking staying off everywhere it is used; Phi-4-mini is the one already measured with the judge.
   - Analogy: choosing the car for good after both did the same test drive.
4. **VISIT-THINK** (VISIT-ASSIST-THINK; execution gate).
   - Question: "The visit-note helper (off by default) gets an empty answer from gemma4 every time, because the model spends all its words thinking. You allowed 'thinking off' only for the advice judge. Turn thinking off for the visit-note helper as well?"
   - Options: "Off for visit notes" (the helper starts proposing entities again; every proposal is still checked against the note's exact words). "Leave as is" (the helper stays empty with thinking models; it works with non-thinking models).
   - Tradeoffs: thinking off can make the proposals a little less careful; the strict quote check is unchanged either way.
   - Analogy: asking a note-taker to write the answer down instead of thinking aloud until the page runs out.
5. **EXPORT-PURGE-DIFF** (EXPORT-STORE-PURGE; merge only; the three call-site lines in `api/profiles.py`).
   - Question: "Doctor summaries, visit packets and FHIR exports are kept in the app's memory after you log out, lock or delete the profile, until the app restarts. This change clears them at those moments and after 30 minutes. It adds one line each to the logout, lock and delete routes. Merge?"
   - Options: "Merge as shown" (nothing stays in memory after you leave). "Only the 30-minute limit" (no edit to the sign-in file; exports may stay up to 30 minutes after logout). "Do not merge".
   - Tradeoffs: an export link opened after 30 minutes must be generated again.
   - Analogy: shredding the printouts when you leave the office, not at closing time.

**Not gates:** LEGACY-ADVICE-GATE (L0 tells the owner: stricter, never looser); AGENT-DATEONLY-TZ (L0 tells the owner the midnight tradeoff); RAPIDOCR-RESEARCH (a failed premise goes back to the owner as a new question with the numbers).

Back to: [queue](2026-10-15-build-program/queue.md) · [RUNBOOK](2026-10-15-build-program/RUNBOOK.md)
