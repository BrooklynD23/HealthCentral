# MVP rows 2026-10-22 — plans for the MVP pass, owner prompts 40-41 and the bug-fixer follow-ups

**Last Updated:** 2026-10-30 (Opus planner on `144b5d48`: RAPIDOCR-BUNDLE [delta 2026-10-30](#delta-2026-10-30-to-rapidocr-bundle-plan-from-rapidocr-research-323) from RAPIDOCR-RESEARCH (#323) and OCR-SIZE "Accept 271 MB": no `ocr` fetch (models ship in the wheel), Tasks 1-5 ready, Task 6 waits on OCR-DEFAULT-ON; Owner gates item 7 redrafted with the numbers); 2026-10-27 (RAG-TIMEOUT-GROUNDED answered "Keep the sentence, label it", Owner gates item 8; the delta's owner gate and order lines updated; post-merge batch 2026-10-27); 2026-10-27 (Opus planner on `e0a995fc`, merged with `018bd094`; review round 2: question rewritten for neutrality, option 3 guarded with `not strict`: RAG-TIMEOUT-ANSWER delta for the grounded path with new owner gate RAG-TIMEOUT-GROUNDED (Owner gates item 8); KV-NUMCTX-VERIFY planned); 2026-10-22 (review round 4: NORMALIZE-COMMA-NAMES urine qualifier dropped, quote, cites, stale statuses; review round 3: fallback test citation, OCR opt-in files, analogy; review round 2: plain-header check only with SQLCipher present, OCR switch facts and gate rewrite, both launcher log matches; review round 1: SQLCipher old-vault handling and new gate SQLC-OLD-VAULTS, CI import path, launcher checks, CPU-only model preference, OCR default gate OCR-DEFAULT-ON, #295/#297/#301 merged)
**Owner:** repository owner
**Status:** PROPOSED (Opus planner). Docs only. **No owner approval is recorded here.** Every gate keeps its state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md). Answers cited below come from owner prompts 40-41 (L0 AskUserQuestion, 2026-10-22, record `/tmp/claude-1000/prompts-40-41.json`); their owner-decisions rows land in L0's PR #301 (branch `docs/owner-rows-prompts40-41`), not here.
**Base measured:** `origin/main` @ `0e2799b` (2026-10-22, after #294 EXTRACT-UNIT-MGL + EXTRACT-DOB-DATE merged); review round 1 re-read the files #295 (`531c712`) and #297 (`afbe1af`) changed on `531c712`, where both had merged. Every `file:line` below was re-read by the planner.
**Refresh Trigger:** any owner answer to a gate in [Owner gates](#owner-gates); a merge of #300, #304, #305 or #264; any edit to `src/backend/modules/extract.py`, `dev.ps1`, `dev.sh` or `src/backend/requirements.txt` before the rows below are built.

Queue rows: [queue.md, "Planned 2026-10-22, MVP rows"](2026-10-15-build-program/queue.md#planned-2026-10-22-mvp-rows). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Path shorthand as in the queue: `be/` = `src/backend/`, `fe/` = `src/frontend/src/`.

**Sources.** (1) The MVP readiness pass `/tmp/claude-1000/mvp-pass-1022.md` (facts at `d2843e8`; research merged in #299 as [docs/research/2026-10-22-mvp/](../research/2026-10-22-mvp/00-README.md)); its 20 proposed rows are planned here, re-verified at `0e2799b`. Its other bug-table items (FE-A11Y-DIALOGS, RECOVER-ORDER, AUTO-LOCK-UNUSED, FALLBACK-COUNT-50, CHAT-SESSIONS-N1, TEST-RESET-ROUTE, BACKUP-RESTORE-JOURNAL, TEST-PLACEHOLDERS, IMPORT-FAILED-REASON) are listed as "not yet planned" bullets in the queue. (2) Owner prompts 40-41. (3) Follow-ups from the bug-fix agent (#294, #295, #297, #300), the KV measurement ([#298](../reviews/2026-10-22/kv-prefix-measure.md), "Other findings" items 1-2) and #290's review (round 2 MINORs).

**MVP priority** (showcase 2026-10-31): **P0** = blocks a stakeholder running the app on their own laptop, or makes a privacy or lab-value claim false; **P1** = visible on the demo path, fix before 2026-10-31 if a slot is free; **P2** = after the MVP.

**Ask-first files (CLAUDE.md §1).** Edited only behind a named gate: `be/core/database.py`, `be/core/migrations.py`, `be/core/profile_database.py`, `be/migrations/profile/env.py` (encryption; SQLCIPHER-WHEEL, gates SQLC-OLD-VAULTS and SQLC-WHEEL-DIFF; `be/core/sqlcipher_driver.py` not edited); `be/core/auth.py` (SESSION-REENTRY Task 2, gate SESSION-AUTH-DIFF); `be/api/profiles.py` call sites (EXPORT-STORE-PURGE, treated as auth-adjacent, gate EXPORT-PURGE-DIFF). `modules/interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py`: none edited by any row.

**Overlaps with open PRs** (`gh pr list --state open`, 2026-10-22, after review round 1): #295 (frontend bundle) and #297 (llama provider) **merged** (`531c712`, `afbe1af`), as did #301 (owner rows); rows that waited on them are ready. #300 (`f588571`), #304 (`64b92eb`), #284 (`08ad842`), #308 (`3102dd1`) and #305 JUDGE-THINK (`2434209`) also **merged**. Still open: #264 and #239 (parked drafts; hold no file, contracts §b rule 2, but rows that must follow #264 say so). Each row's `depends_on` names the PR it follows.

---

## Packaging and launcher (MVP-PACKAGING (a) now, (c) later)

Owner: **MVP-PACKAGING answered "Option A then work on C installer"** (free text; L0 reading "(a) for the MVP, then (c) an installer after the MVP"; owner prompts 40-41, owner-decisions row MVP-PACKAGING, L0 PR #301). **CODE-SIGNING answered (a) "No signing yet"** (prompt 41, row CODE-SIGNING).

**Suggested L0 bundle (L0 rules; not assumed):** DEV-PS1-FIRSTRUN, LLAMA-WHEEL-INDEX and DEV-EMB-FETCH all edit `dev.ps1` (and the last two `dev.sh`). Built one after the other, each must merge `origin/main`; as one PR the same-file order is inside it (the #289 bundle pattern). SQLCIPHER-WHEEL also edits `dev.ps1` and `dev.sh` and stays its own PR because it is merge-gated. **Order on the launcher files (no shared file, queue rule 2):** the launcher rows (or their bundle) first, then SQLCIPHER-WHEEL. contracts §b rule 2 (a parked draft holds no file) is not assumed for SQLCIPHER-WHEEL: today it applies only to B-3, and only L0 can extend it (owner may veto). If L0 extends it once SQLCIPHER-WHEEL is a finished draft waiting only on SQLC-WHEEL-DIFF, the launcher rows may land beside it and it rebases.

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

**Files:** `dev.ps1` (STEP 8 `:797-802`, STEP 9 `:824-857`, STEP 10 backend branch `:898-911` only). **Expected collected delta:** 0 (no pytest). **Est:** 1.5 h. **Runtime:** claude (or the `windows-bootstrap-engineer` agent, whose scope is `dev.ps1` + `dev.bat`); checks DPF-1…3 are an owner-box run (Windows), pasted into the PR. **Acceptance:** DPF-1…4 output pasted. **Owner gates:** MVP-PACKAGING (a) (above). **Order:** ready; never beside another `dev.ps1` PR (LLAMA-WHEEL-INDEX, DEV-EMB-FETCH, SQLCIPHER-WHEEL), or bundled (above); first on the launcher files. **MVP:** P0.

### LLAMA-WHEEL-INDEX — a clean Windows or Mac without a C++ toolchain cannot install llama-cpp-python

**Facts:**
1. `be/requirements.txt:72` pins `llama-cpp-python==0.3.35`. PyPI publishes only the sdist for it (MVP pass, re-checked there); pip compiles it from source.
2. The upstream maintainer's CPU wheel index lists `llama_cpp_python-0.3.35-py3-none-win_amd64.whl`, `-macosx_11_0_arm64.whl` and `-manylinux2014_x86_64…whl` (planner, `curl -s https://abetlen.github.io/llama-cpp-python/whl/cpu/llama-cpp-python/`, 2026-10-22). **No macOS x86_64 (Intel) wheel** is listed for 0.3.35.
3. `dev.ps1` STEP 3 (`:466-507`) has no compiler check; `dev.sh:93-130` checks for a C compiler and dies unless `LLM_PROVIDER=ollama`.

**Design:** before the main `pip install -r requirements.txt`, both launchers run one extra step: read the exact `llama-cpp-python==X` pin from `requirements.txt` (single source, so the two can never drift) and run `pip install --only-binary=llama-cpp-python --index-url https://abetlen.github.io/llama-cpp-python/whl/cpu "llama-cpp-python==X" --no-deps`, then the normal install (which finds it already satisfied and installs its PyPI dependencies). `--index-url` + `--no-deps` for this one package, not `--extra-index-url` for everything, so no other package can resolve from the second index (dependency-confusion guard). The wheel step is **skipped when `CMAKE_ARGS` is set** (a user building a GPU wheel, e.g. `-DGGML_CUDA=on` for #297's `LLM_N_GPU_LAYERS`), so the source build runs as today. If the wheel step fails (no wheel for the platform, e.g. Intel Mac): `dev.sh` keeps today's compiler check; `dev.ps1` gains the same check (`cl.exe` / `where.exe cl`, or `LLM_PROVIDER=ollama` skips it) and stops with the Visual Studio Build Tools link instead of a long compile error. Install-time network only; nothing changes at runtime. README install section: one sentence naming the wheel index.

**Test-first:**

| Id | Check | RED today? |
|---|---|---|
| LWI-1 | Windows box, fresh venv, no VS Build Tools on PATH: launcher STEP 3 installs `llama-cpp-python 0.3.35` from the wheel in under 2 min (`pip show llama-cpp-python`) | yes (source build fails) |
| LWI-2 | Linux, `bash -n dev.sh` and a scratch run of the new step in a throw-away venv: the installed wheel's `RECORD` shows a prebuilt `.so`, no build directory | yes (builds from source) |
| LWI-3 | `grep -c 'extra-index-url' dev.ps1 dev.sh` prints 0 for both (pin against the broad flag) | GREEN (pin) |
| LWI-4 | `CMAKE_ARGS=-DGGML_CUDA=on` set: the launcher prints that the wheel step is skipped and pip builds from source (log line pasted; the build itself may be interrupted) | yes (step does not exist) |

**Files:** `dev.ps1` (STEP 3 only), `dev.sh` (STEP 3 only), `README.md` (install section, one sentence). `requirements.txt` not edited. **Delta:** 0. **Est:** 1 h. **Acceptance:** LWI-1 on the owner box, LWI-2…4 pasted. **Owner gates:** MVP-PACKAGING (a). **Order:** after DEV-PS1-FIRSTRUN (same file) or in its bundle; #297 does not change the pin (its file list has no `requirements.txt`), so it does not wait for #297. **MVP:** P0.

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
4. Startup: `be/core/database.py:71-79` raises `RuntimeError` when encryption is required and `is_sqlcipher_available()` is false, but only logs `verify_cipher_version()`; `be/core/migrations.py:213-217` and `be/migrations/profile/env.py:127-131` check availability only; `be/core/profile_database.py:337-346` checks `PRAGMA cipher_version` per connection and raises `ProfileDatabaseEncryptionError` when required. `be/core/config.py:44` defaults `database_encryption_required = True`; `config/.env.example:48` sets it `true`.
5. Hint text names only `sqlcipher3-binary`: `database.py:75`, `migrations.py:216`, `migrations/profile/env.py:130`, `modules/environment_diagnostics.py:159-196` (the Windows text says the wheel is Linux-only; the non-Windows branch `:190-195` says `pip install sqlcipher3-binary`, which macOS would show).
6. **Existing plaintext vaults stop opening** (review round 1): `be/core/profile_database.py:337-366` applies `PRAGMA key` whenever `cipher_version` is non-empty and never reads `database_encryption_required` there, so once SQLCipher is installed on a Windows or macOS machine that ran the launcher before, every vault written there as plain SQLite fails with "file is not a database", whatever `.env` says. The owner's Windows demo box has run `dev.ps1` before, so it very likely has such vaults.
7. Prior art: `be/tests/security/test_vault_ciphertext.py` is the existing on-disk ciphertext proof (Linux CI). HC-SQLC-001 cites it and does not duplicate its fixtures.

**Design (the exact diff goes to the owner, SQLC-WHEEL-DIFF):**
1. `requirements.txt:32` becomes two lines with environment markers:
   `sqlcipher3-binary>=0.5.0; sys_platform == "linux"` and `sqlcipher3>=0.6.4; sys_platform == "win32" or sys_platform == "darwin"`. Linux (incl. the GPU box and CI) keeps exactly today's package. Known gap, stated in the gate: `sqlcipher3-binary` has no Linux aarch64 wheel; that platform is unchanged (it fails as today).
2. Launchers never disable encryption silently. `dev.ps1` STEP 3 and `dev.sh` STEP 3: a SQLCipher install failure **stops** the launcher with pip's error lines and the fix, and leaves `.env` unchanged. Only an explicit `HC_ALLOW_UNENCRYPTED=1` (new, development only) keeps today's fallback, and then the launcher prints a multi-line red banner "Your health data will NOT be encrypted on this computer" and writes `DATABASE_ENCRYPTION_REQUIRED=false`. The default `.env` written when there is no template (`dev.ps1:570-581` and `dev.sh:175`) uses `true`. The whole-log matches `dev.ps1:483` and `dev.sh:137` (`grep -qi sqlcipher`) are both narrowed to pip's error lines that name the SQLCipher package, and `:495-500` checks `$LASTEXITCODE`.
3. Startup check (`core/database.py:71-79`, ask-first): when encryption is required, also refuse when `verify_cipher_version()` returns `None` or an empty string (a module that imports but is not SQLCipher). When encryption is **not** required and SQLCipher is unavailable, log one `CRITICAL` line at startup, not a `warning`. Hint strings in `database.py`, `migrations.py`, `migrations/profile/env.py` and `environment_diagnostics.py` name the per-platform package.
4. **Old plaintext vaults (execution gate SQLC-OLD-VAULTS, asked before the build):** only when SQLCipher is available (non-empty `cipher_version`, `:337-346`), `profile_database.py`'s open path detects a vault whose first 16 bytes are the plain SQLite header and raises `ProfileDatabaseEncryptionError("This profile was saved without encryption on this computer…")` with a fixed message, before any key is applied, before `run_profile_migration_async` (`:384`; `migrations/profile/env.py:162-180` also applies the key) and without touching the file (today the error is a generic "file is not a database"). When SQLCipher is unavailable and encryption is not required, plain vaults open exactly as today (`:340-354`: the `HC_ALLOW_UNENCRYPTED=1` dev fallback relies on it, and `tests/test_profile_migrations_sqlcipher_fallback.py:21-31` (migration path) runs with encryption not required and SQLCipher unavailable; HC-SQLC-009 is the `profile_database.py` pin). If the owner picks conversion, Task 2 adds a one-time conversion on the next successful login: copy the file to `<vault>.plain.bak`, `ATTACH` an encrypted copy with the profile key, `SELECT sqlcipher_export('encrypted')`, verify row counts per table, `os.replace` the encrypted file in, delete the backup only after verification (all inside `profile_database.py`, ask-first).
5. Not changed: key derivation, KDF settings, migrations, `sqlcipher_driver.py`.

**Test-first:**

| Id | File | Assertion | RED today? |
|---|---|---|---|
| HC-SQLC-001 | `be/tests/test_sqlcipher_platform.py` (new) | loads `core/sqlcipher_driver.py` **by file path** (`importlib.util.spec_from_file_location`; importing `core.sqlcipher_driver` runs `core/__init__.py`, which imports FastAPI), creates a DB via its module, `PRAGMA key = "x'<64 hex>'"`, one table, close: the first 16 bytes are not `b"SQLite format 3\x00"`, and stdlib `sqlite3` cannot read the table (`DatabaseError`) | GREEN on Linux; on Windows/macOS today the module is missing: the test asserts availability first, so it is RED there |
| HC-SQLC-002 | same | the driver reports available and `verify_cipher_version()` is a non-empty string starting with `4.` | as 001 |
| HC-SQLC-003 | same | evaluating the `requirements.txt` lines with `packaging.markers` for `sys_platform` in `win32`, `darwin`, `linux` selects exactly one SQLCipher requirement each (`sqlcipher3`, `sqlcipher3`, `sqlcipher3-binary`) | yes (one unmarked line) |
| HC-SQLC-004 | `be/tests/test_database_startup_cipher.py` (new) | `init_database()` with `database_encryption_required=True`, availability patched true and `verify_cipher_version` patched to return `None`: raises `RuntimeError` | yes |
| HC-SQLC-005 | same | required false + unavailable: one `CRITICAL` record naming encryption, no raise | yes (warning only) |
| HC-SQLC-006 | `be/tests/test_sqlcipher_platform.py` | a vault fixture `be/tests/fixtures/sqlcipher/vault_binary_060.db` (new, about 8 KB, created once on Linux with `sqlcipher3-binary` 0.6.0, raw hex test key, one synthetic row; creation script in the test docstring) opens with the platform's package and returns the row | GREEN on Linux; the point is Windows/macOS (vault moved by backup/restore) |
| HC-SQLC-007 | `be/tests/test_profile_vault_plaintext.py` (new) | a plain-SQLite file at a vault path: opening it gives `ProfileDatabaseEncryptionError` with the fixed message, and the file's bytes are unchanged (sha256 before/after) | yes (generic error) |
| HC-SQLC-009 | same | pin: SQLCipher unavailable (patched `cipher_version` empty) and encryption not required: a plain vault opens and returns its row, no error | GREEN (pin: the check must not reach the fallback) |
| HC-SQLC-008 (Task 2, only if SQLC-OLD-VAULTS = convert) | same | a plain vault with 3 tables converts on login: header no longer plain, row counts equal, `.plain.bak` removed; a forced failure mid-copy leaves the original readable as plain SQLite | yes |

**Launcher checks (pasted into the PR; Linux runs `dev.sh`, the owner box runs `dev.bat`):** pip honours `PIP_CONSTRAINT`, so a constraints file with `sqlcipher3-binary==0.0.1` (Linux) or `sqlcipher3==0.0.1` (Windows) forces a SQLCipher-only install failure without editing any tracked file.

| Id | Check | RED today? |
|---|---|---|
| SQLC-L1 | forced SQLCipher failure: launcher exits 1 with the pip error line and the fix; `.env` byte-identical before/after | yes (continues, flips `.env` to `false`) |
| SQLC-L2 | the same with `HC_ALLOW_UNENCRYPTED=1`: the red banner is printed and `.env` has `DATABASE_ENCRYPTION_REQUIRED=false` | yes (no banner) |
| SQLC-L3 | no `.env` and no template (scratch copy without `config/.env.example`): the written `.env` has `DATABASE_ENCRYPTION_REQUIRED=true` | yes (`false`) |
| SQLC-L4 | a constraint that breaks a package listed after the SQLCipher line (`requirements.txt:32`), e.g. `pdfplumber==0.0.1`, so pip's log already says "Collecting sqlcipher3…" before it fails: the launcher takes the generic failure path and does not call it a SQLCipher failure | yes on both launchers (the whole-log matches `dev.ps1:483`, `dev.sh:137`) |

**CI:** new workflow `.github/workflows/sqlcipher-platforms.yml` (matrix `windows-latest`, `macos-latest`, `ubuntu-latest`, Python 3.11; `pull_request` on `src/backend/requirements.txt`, `src/backend/core/sqlcipher_driver.py`, the test file; plus `workflow_dispatch`; `permissions: contents: read`): installs only the marker-selected SQLCipher line, `packaging` and `pytest`, then runs `pytest tests/test_sqlcipher_platform.py --noconftest`; this works because the test loads the driver file by path (HC-SQLC-001), not through the `core` package. `ci.yml` is not touched (CI-CACHE edits it). The owner merges CI files.

**Files:** `be/requirements.txt` (`:31-32` only), `dev.ps1` (STEP 3 `:466-507`, STEP 4 `:563-593` only), `dev.sh` (STEP 3 `:132-153`, STEP 4 `:168-185` only), `be/core/database.py` (`:71-79` only; ask-first), `be/core/migrations.py` (`:216` hint string only; ask-first), `be/migrations/profile/env.py` (`:130` hint string only; ask-first), `be/core/profile_database.py` (plain-header check before the key; Task 2 conversion only if chosen; ask-first), `be/modules/environment_diagnostics.py` (hint strings `:159-196` only), `be/tests/test_sqlcipher_platform.py` (new), `be/tests/test_database_startup_cipher.py` (new), `be/tests/test_profile_vault_plaintext.py` (new), `be/tests/fixtures/sqlcipher/vault_binary_060.db` (new), `.github/workflows/sqlcipher-platforms.yml` (new), slots. **Re-run, not edited:** `tests/test_profile_migrations_sqlcipher_fallback.py`, `tests/security/test_vault_ciphertext.py`, `tests/test_profile_recovery.py`, `tests/test_profile_deletion.py`. **Expected collected delta:** +8 on Linux (+1 with Task 2). **Est:** 4 h (+2 h Task 2) + owner-box run.
**Acceptance:** RED for 003-005 and 007 on Linux; SQLC-L1…L4 output; the CI matrix job green on all three runners (link in the PR); **Windows box run** (owner or L0): `.\dev.bat` on a fresh clone installs `sqlcipher3`, creates a profile, and `python -c "print(open('<vault>','rb').read(16))"` is not the SQLite header (pasted); on the same box, an existing pre-change profile gives the fixed SQLC-OLD-VAULTS message (or converts, if chosen); full suite; `from main import app`.
**Owner gates:** SQLCIPHER-WHEEL answered (above); **SQLC-OLD-VAULTS** (new, execution: block with a clear message, or convert; [Owner gates](#owner-gates) item 6; asked before the build); **SQLC-WHEEL-DIFF** (new, merge only: the exact diff to the owner, item 1). **Ask-first:** `core/database.py`, `core/migrations.py`, `migrations/profile/env.py`, `core/profile_database.py` (encryption), named by SQLC-WHEEL-DIFF. **Order:** after the launcher rows (DEV-PS1-FIRSTRUN, LLAMA-WHEEL-INDEX, DEV-EMB-FETCH, or their bundle) merge, because it shares `dev.ps1` / `dev.sh` (see the order note at the top of this part); then **build to draft; merge on owner yes.** It merges `origin/main` before SQLC-WHEEL-DIFF is asked, so the diff shown is final. KEY-08 row in `docs/capstone-report/specs-compliance-matrix.md` is updated by the post-merge batch, not this PR. **MVP:** P0.

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

**Design:** when the exact lookup misses, a second try with a normalised key: drop a trailing `, total` (`Cholesterol, Total` → `cholesterol`, an existing `total_cholesterol` synonym) or a trailing specimen qualifier from a fixed list (`, serum`, `, plasma`, `, blood`, `, whole blood` only; not `, urine`: canonical keys such as `glucose` are serum analytes, so stripping `, urine` would merge urine values into serum trends); then the existing lookup. Never fuzzy matching. `vitamin d, 25-hydroxy` is added as an explicit `vitamin_d` synonym (no rule reaches it). (Review round 1: reordering to `total cholesterol` would find nothing; the map holds `cholesterol`, `total chol`, `tc`.)

**Test-first** (`be/tests/test_normalize_comma_names.py`, new): HC-NCN-001 ×3 the three names map to `total_cholesterol`, `glucose`, `vitamin_d` (RED); HC-NCN-002 `Urine, Protein` stays unmapped (no qualifier strip at the front, pin); HC-NCN-003 every existing synonym maps as before (loop over `ANALYTE_SYNONYMS`, pin); HC-NCN-004 `Glucose, Urine`, `Creatinine, Urine` and `Albumin, Urine` stay unmapped (pin).
**Files:** `be/modules/normalize.py` (`normalize_analyte` + synonyms only), `be/tests/test_normalize_comma_names.py` (new), slots. **Delta:** +6. **Est:** 1 h. **Order:** ready (not `extract.py`). **MVP:** P1.

### FE-IMPORT-ERROR — any import failure shows nothing on screen

**Facts:** `fe/pages/DocumentInbox.tsx:83-94` `handleFileUpload` catches every error and only calls `console.error` (`:91-93`). A 413, a 400 "unsupported type" or a 500 leaves the page unchanged.

**Design:** an `importError` state set from `ApiError.message` (the server `detail`, `fe/services/api.ts:96-112`), shown in a dismissible `role="alert"` above the drop zone with the file name; cleared on the next successful import. Copy for 413: "This file is too large to import."

**Test-first** (`fe/__tests__/DocumentInbox.test.tsx`, extend): HC-FIE-001 a rejected mutation (400, detail "Unsupported file type") renders `role="alert"` with that text (RED); HC-FIE-002 413 shows the size copy (RED); HC-FIE-003 a later success clears it (RED).
**Files:** `fe/pages/DocumentInbox.tsx` (`handleFileUpload` + one alert block), `fe/__tests__/DocumentInbox.test.tsx`. **Delta:** +3 Vitest. **Est:** 0.75 h. **Order:** ready; before IMPORT-SCANNED-PAGE (same page). **MVP:** P0.

### FE-VERIFY-NUMERIC — editing a value to `7,5` saves and verifies 7

**Facts:** `fe/pages/VerificationWorkbench.tsx:157-169` `handleSaveEdit` uses `parseFloat(editValue)` (`:160`), so `7,5` → 7 and `7.5abc` → 7.5, then verifies. If the mutation fails, `mutateAsync` throws before `setEditingObservation(null)` (`:168`), so the dialog stays open with an unhandled promise rejection and no message (`:129-150` have no error path either). This is a medical value the patient confirms.

**Design:** strict parse: `^\s*-?\d+(?:\.\d+)?\s*$` → number; `^\s*-?\d+,\d+\s*$` → inline error "Use a dot for decimals, for example 7.5" (never silently converted); `<`/`>`-prefixed or other text → `value_text` as today; anything else non-empty and not matching → inline error. The dialog stays open on error or mutation failure and shows the server detail. Save is disabled while invalid.

**Test-first** (`fe/__tests__/VerificationWorkbenchEdit.test.tsx`, **new file**, so it never shares #295's `VerificationWorkbench.test.tsx`): HC-FVN-001 `7,5` shows the inline error and sends no request (RED); HC-FVN-002 `7.5abc` → error, no request (RED); HC-FVN-003 `7.5` sends `value: 7.5` (pin); HC-FVN-004 `<0.5` sends `value_text: "<0.5"` (pin); HC-FVN-005 a rejected mutation shows the server detail in the dialog and the rejection is handled (no unhandled rejection reported by Vitest) (RED).
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

**Superseded 2026-10-30:** the design, test sketch, file list and order below are replaced by the [delta 2026-10-30](#delta-2026-10-30-to-rapidocr-bundle-plan-from-rapidocr-research-323) (models ship inside the wheel, so there is no `ocr` fetch; Tasks 1-5 ready, Task 6 waits on OCR-DEFAULT-ON). They are kept for the record.

**Design (re-planned by the research if it changes anything):** new dependency **`rapidocr` + `onnxruntime`** (+ their transitive `opencv-python-headless`, `Shapely`, `pyclipper`, …) in `be/requirements.txt`, exact pins, licences listed in the PR. Model files are **not** fetched at runtime: `be/scripts/download_models.py` gains an `ocr` subcommand (pinned file list + sha256, exclusive `.partial` dir, same rules as `cmd_embedding` `:332-390`) into a gitignored `be/models/ocr/`; the launchers call it after DEV-EMB-FETCH. `be/modules/extract.py` `extract_from_scanned_pdf` / `extract_from_image` use RapidOCR when the bundle is present (pages rasterised with `pypdfium2`, no Poppler), with the RapidOCR config pointing at the local model paths only; Tesseract stays the fallback when installed. `be/core/config.py` `is_ocr_available()` / `compute_ocr_effective()` (`:297-330`) count RapidOCR as an engine (today both require Tesseract on PATH). **How OCR is switched today (review round 2):** `ocr_enabled` (`:136`, code default `False`) is a server-wide cap, not a default a patient can override: when it is off, `compute_ocr_effective` adds the blocker `disabled_by_admin` and the Settings toggle cannot turn OCR on; the per-profile preference already defaults on (`user_ocr_preference_enabled`, `:307-311`). Both launchers write `OCR_ENABLED=true` whenever Tesseract is on PATH and `false` otherwise (`dev.ps1:595-612`, `dev.sh:186-191`), so launcher users with Tesseract already have OCR on. **Launcher sync:** left as it is, the launchers would write `false` on every machine without Tesseract and switch the bundled reader off; the row changes that sync (and, for the opt-in option, the preference default) only as the new owner gate **OCR-DEFAULT-ON** says, asked with the research numbers ([item 7](#owner-gates)), never inferred from the "(b)" option text. The code default of `ocr_enabled` stays `False`. OCR observations keep base confidence 0.4 and need verification. IMPORT-SCANNED-PAGE's notice now also lists pages OCR could not read.
**Test-first sketch:** a socket-blocking test (`socket.socket` patched to raise) runs OCR on a generated image with the bundle present (GREEN only without network); a missing bundle gives `ocr_unavailable=True`, never a download; a synthetic scanned page gives the expected analytes; route test via `route_client` that a scanned import is parsed, not `pending_ocr`. Ids HC-OCR-001…005.
**Files (provisional):** `be/requirements.txt`, `be/scripts/download_models.py`, `be/modules/extract.py`, `be/core/config.py` (OCR availability; for the opt-in option only, the no-row preference default `:307-311`, plus `be/models/model_settings.py` (`ocr_preference_enabled` `default=True`, `:115-119`) and `be/api/model_settings.py` (response default `:178`), so new settings rows start off; existing profiles keep their current value, and no profile migration is added: `006_ocr_preference.py:27`: the column's `server_default='1'` stays; ORM inserts always send the model default, so no migration is needed), `dev.ps1` (the `ocr` fetch step + OCR sync `:595-612`), `dev.sh` (the fetch step + OCR sync `:186-191`), `.gitignore` (one line, `src/backend/models/ocr/`), `be/tests/test_ocr_rapid.py` (new), slots. **Est:** 5 h. **Owner gates:** OCR-FOR-MVP (b); the research must confirm no network at runtime; the default-on part waits on **OCR-DEFAULT-ON**. **Order:** blocked on RAPIDOCR-RESEARCH (merged) and the plan delta it triggers; after the extract chain (`extract.py`) and SQLCIPHER-WHEEL / the launcher rows (`requirements.txt`, `dev.ps1`, `dev.sh`). **MVP:** P1 if the research lands before 2026-10-27, else P2.

### Delta 2026-10-30 to RAPIDOCR-BUNDLE: plan from RAPIDOCR-RESEARCH (#323)

**Why a delta.** The queue row waited on "its plan delta" from [RAPIDOCR-RESEARCH](../research/2026-10-22-rapidocr/00-README.md) (#323, `4760e83`). The research changed three premises of the section above: the models ship inside the `rapidocr` wheel, `opencv-python-headless` redistributes FFmpeg under LGPL, and OCR values can be silently wrong. The owner answered **OCR-SIZE "Accept 271 MB"** (prompt 47, owner-decisions row OCR-SIZE `:414`, L0 evidence comment 6376450861 on PR #323: "Bundle RapidOCR as measured; ship the licence notices; OCR values always start unverified and must be checked by the patient"). **OCR-DEFAULT-ON is not answered** (no owner-decisions row on `144b5d48`), so this delta keeps the default-off path. This delta replaces the design, the test sketch, the file list and the order of the section above. Facts re-read by the Opus planner on `origin/main` @ `144b5d48` (2026-10-30). Markers as in #323: **[V]** read or run by the planner on 2026-10-30, **[R]** taken from #323 (measured there on rapidocr 3.10.0; the build re-checks it in Task 0), **[U]** not confirmed.

**Facts.**

1. **The extract chain is merged** [V]: EXTRACT-TABLE-VALUE (#322), EXTRACT-PAGE-MERGE (#336), IMPORT-SCANNED-PAGE (#347), EXTRACT-TEXT-FORMS (#353) and EXTRACT-DOB-FORMS (#358) are done in the queue. No other open row lists `be/modules/extract.py`, `be/core/config.py` or `be/api/documents.py`. Of the open PRs, only #316 (launcher bundle: `README.md`, `dev.ps1`, `dev.sh`, `be/tests/test_dev_sh_prereqs.py`) shares a file with the old file list, and Tasks 1-5 below no longer touch those files. SQLCIPHER-WHEEL (blocked) edits `be/requirements.txt` `:31-32` and `dev.ps1` STEP 4 `:563-593`, next to the OCR sync at `:595-612`.
2. **Today's OCR is Tesseract only** [V]. `extract_from_scanned_pdf` (`be/modules/extract.py:586-686`) rasterises with `pdf2image.convert_from_bytes` (`:642`, needs Poppler) and reads with `pytesseract.image_to_string` (`:648`). `extract_from_image` (`:688-769`) does the same at `:742`. Both return `ocr_unavailable=True` when OCR is not effective (`:602-610`, `:703-711`), when `is_ocr_available()` is false (`:612-620`, `:713-721`) or when the import fails (`:622-633`, `:723-734`). OCR rows get `confidence = min(confidence * 0.8, 0.7)` (`:654`, `:746`). The docstrings say "base confidence 0.4", but the code does not do that; this delta keeps the code rule. Both functions are `async` but call Tesseract synchronously, so the event loop is blocked for the whole OCR.
3. **The engine gate names Tesseract in four places** [V]. `Settings.validate_startup` switches `ocr_enabled` off when `shutil.which("tesseract")` is empty (`be/core/config.py:233-238`). `is_ocr_available()` is `settings.ocr_enabled and is_tesseract_on_path()` (`:297-304`). `compute_ocr_effective` emits the blockers `disabled_by_admin`, `tesseract_missing` and `user_disabled` (`:314-330`). `ocr_enabled` defaults to `False` (`:136`). The per-profile preference defaults on (`user_ocr_preference_enabled`, `:307-311`; `ocr_preference_enabled` `default=True`, `be/models/model_settings.py:115-119`; response default `be/api/model_settings.py:178`; migration `006_ocr_preference.py:27` `server_default="1"`).
4. **The pipeline** [V]. `_run_extraction_pipeline` (`be/api/documents.py:576-717`) sets `pending_ocr` for `lab_pdf_scanned` / `lab_image` when OCR is not effective (`:595-603`) or when the extractor reports `ocr_unavailable` (`:624-634`). A `lab_pdf` goes to `extract_from_pdf` with no OCR argument (`:609-610`). That is the mixed case from OCR-FOR-MVP's question: an image page inside a text PDF is only listed in `pages_without_text` (`extract.py:155-158`). Every extracted row is written with `user_verified=False` (`documents.py:665`).
5. **Launchers** [V]. `dev.ps1:595-612` and `dev.sh:186-191` write `OCR_ENABLED=true` only when Tesseract is on PATH, and `false` otherwise. #316 edits both files, so these line numbers move when it merges.
6. **Models are in the wheel** [R]. `rapidocr-3.10.0-py3-none-any.whl` carries `rapidocr/models/PP-OCRv6_det_small.onnx` (9,929,594 B), `PP-OCRv6_rec_small.onnx` (21,234,383 B) and `ch_ppocr_mobile_v2.0_cls_mobile.onnx` (585,532 B), 31.7 MB in total. Their SHA-256 values equal `default_models.yaml` and `MODEL_LICENSES.md` §6 (#323 §1). The provisional `download_models.py ocr` subcommand, the gitignored `be/models/ocr/` copy and the launcher fetch step would only duplicate 31.7 MB, so **they are dropped**. `be/scripts/download_models.py` (subcommands `:473-489`) and `.gitignore` are not edited.
7. **Where a network call could come from** [R]. The only network call is `requests.get` in `rapidocr/utils/download_file.py:70`, reached through `DownloadFile.run` (`inference_engine/onnxruntime/main.py:61`) when a model file is missing or its hash does not match. Pinning `Det.model_path`, `Rec.model_path` and `Cls.model_path` skips that branch (`onnxruntime/main.py:31`; #323 ran it under `unshare -rn`: "OK pinned model_path, boxes: 19"). `requests` is imported when `rapidocr` is imported (`download_file.py:10`), so it is installed but never called. `requests`, `urllib3`, `opencv-python-headless`, `onnxruntime`, `rapidocr`, `shapely`, `pyclipper`, `omegaconf`, `protobuf` and `flatbuffers` are absent from `~/venvs/asclexis-311` today [V] (`importlib.metadata`). `pypdfium2` 5.14.0 is present through `pdfplumber` 0.11.10, but `be/requirements.txt` does not declare it [V].
8. **Python 3.11 wheels** [V] (PyPI JSON, 2026-10-30). `onnxruntime` 1.31.0 (`requires_python >=3.11`) has cp311 wheels for `win_amd64`, `win_arm64`, `macosx_14_0_arm64`, `manylinux_2_28_x86_64` and `aarch64`. It has **no macOS x86_64 wheel**, and its macOS arm64 wheel needs macOS 14 or later. `opencv-python-headless` 5.0.0.93 is `cp37-abi3` (win_amd64, macOS arm64 and x86_64, manylinux). `shapely` 2.2.0 and `pyclipper` 1.4.0 have cp311 wheels for all three systems. `rapidocr` 3.10.0 is still the latest release. `onnxruntime` 1.31.1 is now out; this delta pins the measured 1.31.0. `rapidocr` does not depend on `onnxruntime` (`requires_dist`), so the engine must be listed on its own line.
9. **Licences** [R]. `rapidocr` and the three models are Apache-2.0. The models need a modification notice for converted files (`MODEL_LICENSES.md` §7). `onnxruntime` is MIT. The `opencv-python-headless` wheel says "FFmpeg is redistributed within all opencv-python packages" (`LICENSE-3RD-PARTY.txt:243`, LGPL), and its `opencv_python_headless.libs/` holds `libavcodec`, `libavformat`, `libavutil`, `libswscale` and `libswresample` as shared libraries. Under MVP-PACKAGING (a) (source + launcher, owner row MVP-PACKAGING `:396`), pip installs those wheels from PyPI with their own licence files in `*.dist-info`, so the repo redistributes nothing. It still ships a notices file that names them. The installer (c) would redistribute the libraries. INSTALLER-POST-MVP takes that obligation: ship the notices, keep FFmpeg dynamically linked and replaceable (PyInstaller one-file is **[U]** in #323), and pre-compile bytecode or set `PYTHONDONTWRITEBYTECODE` (#323 §2).
10. **Accuracy and cost** [R] (#323 §5, 10 synthetic pages). 117/140 analytes were found (grid 38/56, column 38/42, summary 41/42). One found value was wrong and the recogniser was fully confident: Chloride 98 read as 86 at score 1.0. Removing ruled lines first raised the grid pages to 49/56 with all values correct. The cost is 3.62 CPU s per page with 1 thread (3.25 s wall), against 36.5 CPU s with the default threads. The first call loads the models in 2.8 to 4.8 s, and peak RSS was about 600 MB. 300 dpi was no better than 200 dpi. Tesseract was not measured.

**Design (Tasks 1-5, buildable now; default-off unchanged).**

- **Dependencies** (`be/requirements.txt`, OCR block `:41-47` only). Add `rapidocr==3.10.0`, `onnxruntime==1.31.0; sys_platform != "darwin" or platform_machine == "arm64"` (an Intel Mac would otherwise fail the whole install, fact 8), `opencv-python-headless==5.0.0.93` (pins the LGPL carrier named in the notices) and `pypdfium2>=5.14.0` (now imported directly). The block comment changes to "RapidOCR bundled (models inside the wheel); Tesseract optional fallback". `pytesseract` and `pdf2image` stay. Shapely, pyclipper and the other transitive packages are left to the resolver; the PR pastes `pip freeze` before and after, and the added set must be the 20 packages of #323 §1 (or fewer).
- **Engine** (`be/modules/extract.py`, new helpers only, no new module; `rapidocr_ready()` is the one public name, used by `core/config.py` and the Task 6 launcher check). `_RAPIDOCR_MODEL_SHA256` holds the three file names and the hashes from the installed `default_models.yaml`, copied into the source. A cached `_rapidocr_engine()` (`functools.lru_cache(maxsize=1)`) returns `None` when `rapidocr` or `onnxruntime` cannot be imported, or when any of the three files under `importlib.resources.files("rapidocr") / "models"` is missing or has the wrong hash. In that case it logs the file name, never the document. Otherwise it builds `RapidOCR(params={...})` with the three absolute `model_path` values pinned and `EngineConfig.onnxruntime.intra_op_num_threads = inter_op_num_threads = 1`. The engine is never built on a path that can download. `rapidocr_ready() -> bool` is `_rapidocr_engine() is not None`.
- **Page reading.** One per-page function `_ocr_image_text(image) -> str`. With the engine present, it removes ruled lines (OpenCV morphological open, 120 px kernels, painted white; #323 `derule.py`), runs RapidOCR, and joins boxes into lines (cluster by y within half the median box height, order by x; #323 `ocr_pages.py:lines_from`). Without the engine and with Tesseract on PATH, it calls `pytesseract.image_to_string` as today. Callers run it with `await asyncio.to_thread(...)`, so the event loop is not blocked (fact 2). PDF pages are rasterised with `pypdfium2` at 200 dpi (`page.render(scale=200/72)`). `pdf2image` is used only on the Tesseract fallback path, unchanged. The rest of each caller stays as it is: `_extract_from_text`, the confidence rule at `:654` / `:746` and the date propagation. The recogniser scores never enter `confidence` (fact 10). No unit alias is added for OCR garbles such as `7p/6` (#323 §6.5: that would be guessing on medical data). A garbled row is missing, not wrong.
- **Mixed PDFs.** `extract_from_pdf` gains a keyword-only `ocr_pages: bool = False`. With it true, each page in `pages_without_text` is rasterised and read by `_ocr_image_text`. Its rows get `extraction_method="ocr_pdf"` and the OCR confidence rule, its text replaces the empty page text in `extracted_text`, and the page leaves `pages_without_text` only if OCR gave 20 or more non-space characters. So IMPORT-SCANNED-PAGE's notice still lists the pages OCR could not read. `_run_extraction_pipeline` passes `ocr_pages=ocr_effective` (`documents.py:609-610`, that call only). The default `False` keeps HC-ISP-001…003 unchanged.
- **Config** (`be/core/config.py`). An engine is available when `extract.rapidocr_ready()` (lazy import inside the function, as `extract.py` already imports `core.config` lazily) or `is_tesseract_on_path()`. `validate_startup` (`:233-238`) switches `ocr_enabled` off only when neither engine is available. `is_ocr_available()` (`:297-304`) is `settings.ocr_enabled and <engine available>`. `compute_ocr_effective` (`:314-330`) emits `tesseract_missing` only when no engine is available. The code name is kept, so the API, `SettingsPage.tsx:62-63` and `ModelSettingsService.test.tsx:152` stay as they are, and "Install Tesseract" is still the right advice in that case. **`ocr_enabled` keeps its code default `False`**, and the launchers are not edited in Tasks 1-5. So until Task 6, OCR runs only where `OCR_ENABLED=true` today: launcher machines with Tesseract, which now read with RapidOCR first, and hand-set `.env` files.
- **Notices** (`THIRD_PARTY_NOTICES.md`, new, repo root). One table: package, pinned version, licence, and where the full text is installed (`*.dist-info/`). It also carries the FFmpeg LGPL statement with the five `opencv_python_headless.libs` libraries, and the PaddleOCR model notice with the `MODEL_LICENSES.md` §7 modification line. It is linked from the `be/requirements.txt` OCR block comment.

**Task 6 (blocked: OCR-DEFAULT-ON; also after #316 and SQLCIPHER-WHEEL, the adjacent launcher hunks).** The change depends on the owner's option ([Owner gates](#owner-gates) item 7):

| OCR-DEFAULT-ON option | Change | Files |
|---|---|---|
| "On when reader installed" | The launcher sync writes `OCR_ENABLED=true` when Tesseract is on PATH **or** `python -c "from modules.extract import rapidocr_ready; raise SystemExit(0 if rapidocr_ready() else 1)"` succeeds in the backend venv. The messages name the engine found. `HC_SKIP_OCR_SETUP=1` keeps its meaning. | `dev.ps1` (OCR sync block), `dev.sh` (OCR sync block) |
| "On, patient opts in" | The launcher change above, plus new settings rows start off: `user_ocr_preference_enabled` no-row default (`config.py:307-311`), `ocr_preference_enabled` `default=False` (`models/model_settings.py:115-119`), response default (`api/model_settings.py:178`). No migration: `006_ocr_preference.py:27` keeps `server_default="1"`, because ORM inserts always send the model default. Task 0 for this option counts the profiles that have no `user_model_settings` row. Those profiles flip to off, and L0 tells the owner before the build. | the launcher files, plus `be/core/config.py`, `be/models/model_settings.py`, `be/api/model_settings.py` (those lines only) |
| "Keep today's rule" | none; Task 6 is closed as won't-do with the answer cited | — |

Task 6 is skipped and listed in the PR body (RUNBOOK §4.3) until the gate is answered and #316 and SQLCIPHER-WHEEL have merged. Then it is built on the same id, as a follow-up PR or on the draft if that is still open.

**Test-first** (`be/tests/test_ocr_rapid.py`, new, ids HC-OCR-001…013). Fixtures are generated in each test from seeded synthetic rows, with no real data. They are drawn with `PIL.ImageFont.load_default(size=28)` (no system font needed in CI), on the column and grid layouts of #323 `gen_pages.py`, with no noise. Routes go through HTTP (`tests/support/routes.py::route_client`). Tests that need the engine use `pytest.importorskip("rapidocr")` until Task 1 lands. Task 2 records each RED on main, before the deps are installed, as a skip or a failure with its reason. Per CLAUDE.md §4, a skip is not a pass: RED is captured again after Task 1 installs the deps.

| Id | Asserts | RED today? |
|---|---|---|
| HC-OCR-001 | **No network, end to end.** In a fresh interpreter (`subprocess`, as `test_embedding_no_network.py` HC-LHH-001), with the HC-LHH socket guard (patched `socket.socket.connect`, `connect_ex` and `socket.getaddrinfo`, which record every non-loopback attempt) and `HOME` / `XDG_CACHE_HOME` / `USERPROFILE` pointing at an empty temp dir, `extract_from_image` on a generated PNG with OCR effective and Tesseract absent (`shutil.which` → `None`) returns at least 1 observation. The recorded attempts are `[]`, and the temp home is still empty afterwards. | yes (Tesseract only today, so `ocr_unavailable`) |
| HC-OCR-002 | **The guard can see RapidOCR's download path** (positive control for 001). Same guard, `RapidOCR(params={"Global.model_root_dir": <empty tmp>})` with no `model_path` pin, one call: the guard records a `modelscope.cn` host, the call raises, and the empty dir stays empty. The PR shows once that 001 fails when the pins are removed. | n/a (control; GREEN once the deps are installed) |
| HC-OCR-003 | **Fails closed on a bad model file.** With the model dir resolver patched to a temp copy that has one flipped byte in the rec model, `rapidocr_ready()` is false, a scanned import gives `ocr_unavailable=True`, there are no guard attempts, and no exception is raised. | yes (helper does not exist) |
| HC-OCR-004 | A generated one-page **image-only PDF** (column layout, 6 analytes), with Tesseract absent and `pdf2image.convert_from_bytes` patched to raise, gives, through `extract_from_scanned_pdf`: every observation's `(analyte, value, unit)` in the truth set (**no wrong value**), found ≥ the floor Task 2 measures (written in the PR, never lowered after), `extraction_method == "ocr_pdf"` and `confidence <= 0.7`. | yes |
| HC-OCR-005 | Same as 004 for a PNG through `extract_from_image` (`ocr_image`). | yes |
| HC-OCR-006 | **Route** (`route_client`, `POST /documents/import`): a scanned PDF with `OCR_ENABLED` on and Tesseract absent is `parsed`, not `pending_ocr`. Every stored row has `user_verified is False`. The import audit row is written as today. | yes (`pending_ocr` today) |
| HC-OCR-007 | **Mixed PDF** (the IMPORT-SCANNED-PAGE fixture: text page plus an image page with HbA1c 9.1). With `ocr_pages=True`, page 2's HbA1c 9.1 is found with `ocr_pdf` and `pages_without_text == []`. With the default, the result is `[2]` and no page-2 row. A blank image page stays in `pages_without_text` with OCR on. | yes (first and third parts) |
| HC-OCR-008 | **Config with RapidOCR only.** `ocr_enabled=True`, RapidOCR ready, Tesseract absent: `validate_startup` keeps `ocr_enabled` and gives no OCR warning, `is_ocr_available()` is true, and `compute_ocr_effective(True) == (True, [])`. With neither engine: `tesseract_missing` and switched off, as today. | yes |
| HC-OCR-009 | **Default-off pin.** Code default `ocr_enabled=False` with RapidOCR ready: blockers contain `disabled_by_admin`, and a scanned import over HTTP stays `pending_ocr`. | no (pin; GREEN before and after) |
| HC-OCR-010 | **Engine order.** RapidOCR ready and Tesseract present: `pytesseract.image_to_string` is not called. RapidOCR not ready and Tesseract present (mocked): it is called once per page, with `pdf2image` as today. | yes (first part) |
| HC-OCR-011 | **Ruled grids.** On a generated grid page, the rows found with line removal are a superset of the rows found without it, and none has a wrong value (the #323 §5 direction, on this fixture). | yes (no de-ruling today) |
| HC-OCR-012 | **Event loop free.** With `_ocr_image_text` patched to `time.sleep(0.5)`, a concurrent `asyncio` ticker advances while `extract_from_image` runs. | yes (synchronous today) |
| HC-OCR-013 | **Notices.** `THIRD_PARTY_NOTICES.md` names every package in the `be/requirements.txt` OCR block with its pinned version and licence, the FFmpeg LGPL statement, and the PaddleOCR modification notice. | yes (no file) |

Existing pins that change setup, not assertions: `test_config_validation.py` `test_ocr_enabled_no_tesseract_warns_and_disables` (`:54-60`), `test_returns_false_when_no_tesseract` (`:112-122`) and `test_tesseract_missing_blocks` (`:160-167`) pin the case with no engine. With `rapidocr` installed in CI, each of them also patches `rapidocr_ready` to `False`. Their asserts do not change. Must stay GREEN untouched: HC-ISP-001…004, HC-EPM-001…003, `test_document_import_classification.py`, `test_ocr_bbox.py`, HC-LHH-001/002.

**What these tests would not notice** (CLAUDE.md §4): (1) a network call from a thread pool that outlives the subprocess, which is why 001 asserts after the extraction has returned and the guard is process-wide; (2) accuracy on real scans, because every fixture is synthetic and the 84% / 1-wrong figure is synthetic too. That is why rows stay unverified and the owner question says so. (3) Windows and macOS installs, which CI does not cover; LWI-style owner checks follow below.

**Tasks.**

1. **Task 0** as RUNBOOK §4. Quote OCR-FOR-MVP (b) and OCR-SIZE. State that OCR-DEFAULT-ON is open and that Task 6 is skipped. Re-read every line cited above on current main. In the worktree's own venv (never `~/venvs/asclexis-311` before the PR merges; #323 did not install there either), `pip install -r be/requirements.txt`, then paste `pip freeze` before and after and the installed size delta. Confirm facts 6 and 7 on the installed wheel (`sha256sum` of the three models against `default_models.yaml`, and `grep -n` of the three `download_file.py` / `onnxruntime/main.py` lines).
2. Write HC-OCR-001…013 and the three setup changes. Capture RED for each "yes" row and GREEN for 009 on main. Measure and record 004's floor.
3. Deps and notices: `be/requirements.txt`, `THIRD_PARTY_NOTICES.md` (013, 002 GREEN).
4. Engine, page reading, scanned PDF and image paths, mixed PDFs: `extract.py`, `documents.py:609-610` (001, 003-007, 010-012 GREEN).
5. Config: `config.py` (008 GREEN, 009 still GREEN). Re-run the pins listed above.
6. *(blocked: OCR-DEFAULT-ON, #316, SQLCIPHER-WHEEL)* Launcher sync and, for opt-in, the preference default, as in the table. Owner-box checks RDB-L1 (Windows `dev.ps1` on a box without Tesseract writes `OCR_ENABLED=true`, and a scanned import is parsed) and RDB-L2 (same with `dev.sh`).

**Files (Tasks 1-5, verified on `144b5d48`):** `be/requirements.txt` (OCR block `:41-47` only), `be/modules/extract.py` (`extract_from_pdf` signature and the no-text-page branch, `extract_from_scanned_pdf`, `extract_from_image`, new private helpers), `be/core/config.py` (`:233-238`, `:297-304`, `:314-330` only), `be/api/documents.py` (`:609-610` only), `be/tests/test_ocr_rapid.py` (new), `be/tests/test_config_validation.py` (setup of the three tests only), `THIRD_PARTY_NOTICES.md` (new), `docs/INDEX.md` and `docs/_link_graph.json` (regenerated if the docs index picks up the new file), slots. **Task 6** adds the files in its table. **Not edited:** `be/scripts/download_models.py`, `.gitignore`, `dev.ps1` / `dev.sh` (until Task 6), the migrations, the frontend, and the four ask-first modules. **Delta:** +13 backend. **Est:** 6 h for Tasks 1-5; Task 6 adds 1 h ("On when reader installed") or 1.5 h ("On, patient opts in").

**Acceptance** (in the worktree, after the final `git merge origin/main`; paste the output):

```bash
cd src/backend
P="$(git rev-parse --show-toplevel)/scripts/pyslot.sh"
V="$(git rev-parse --show-toplevel)/.venv-ocr"     # the Task 0 venv; never ~/venvs/asclexis-311 before merge
"$P" env HF_HUB_OFFLINE=1 "$V/bin/python" -m pytest -p no:cacheprovider -q tests/test_ocr_rapid.py tests/test_config_validation.py
"$P" env HF_HUB_OFFLINE=1 "$V/bin/python" -m pytest -p no:cacheprovider -q \
  tests/test_extraction_pipeline.py tests/test_documents_api.py tests/test_document_import_classification.py \
  tests/test_ocr_bbox.py tests/test_embedding_no_network.py
unshare -rn "$V/bin/python" -I -c "import sys; sys.path.insert(0, '.'); from modules.extract import rapidocr_ready; print(rapidocr_ready())"   # True with no network namespace
git diff --name-only origin/main...HEAD -- scripts/download_models.py ../../.gitignore ../../dev.ps1 ../../dev.sh modules/interpret_safety.py modules/redaction.py modules/faithfulness.py modules/verifier_agent.py migrations   # must print nothing (Tasks 1-5)
```

Then RUNBOOK §6 steps 2-6: the full suite (no new failures beyond the 5 environmental ones in CLAUDE.md §4), the collected count with its delta (+13), `python -c "from main import app"` and `git status --short`. CI's pip-audit and `security_gate.py` run on the new packages. Any finding is triaged there, never waived in this PR.

**Owner gates:** OCR-FOR-MVP (b) and OCR-SIZE ("Accept 271 MB") answered. **OCR-DEFAULT-ON** open: it gates Task 6 only, and its draft is redrafted with the #323 numbers in [Owner gates](#owner-gates) item 7. It can be asked now. **Order:** Tasks 1-5 are ready. This changes the section above, which put the whole row after SQLCIPHER-WHEEL and the launcher rows: Tasks 1-5 no longer touch `dev.ps1` or `dev.sh`, and on `be/requirements.txt` they edit a different hunk from SQLCIPHER-WHEEL (`:41-47` against `:31-32`). They keep that row's rule: never beside a non-draft PR on `be/requirements.txt` (SQLCIPHER-WHEEL, any dependency row). Task 6 waits on OCR-DEFAULT-ON, #316 and SQLCIPHER-WHEEL. **Medical data path:** say so in the PR. OCR rows are unverified like every imported row. With safety mode on they are not interpreted until checked (`api/interpretations.py:461`). With it off, the Interpret page can explain an unchecked value, as it already does for text-PDF rows; this row does not change that. **MVP:** P1 (unchanged).

**New bullet for L0 (not a row here): OCR-COPY-ENGINE.** Three patient-facing strings name Tesseract as the only reader and become wrong once RapidOCR ships: `fe/pages/SettingsPage.tsx:346` ("Extract text from scanned PDFs and lab images using Tesseract"), `fe/pages/DocumentInbox.tsx:433` (badge title "install Tesseract") and `fe/pages/VerificationWorkbench.tsx:54` ("ensure Tesseract is installed"). Those pages belong to the UI-PG-* rows (UI-PG-DOCUMENTS, UI-PG-REVIEW), so the copy change goes with them or in a small frontend row after this one merges. It is not added to this backend row, to avoid a file clash.

---

## Test tooling (TEST-DEV-DEPS (a))

Owner: **TEST-DEV-DEPS answered "(a) Add both (Recommended)"** (owner prompts 40-41, owner-decisions row TEST-DEV-DEPS, L0 PR #301). Both are dev-only (MPL-2.0), never shipped.

### HYPOTHESIS-EXTRACT — Hypothesis as a backend dev dependency, first property tests on the extractor

**Design:** `be/requirements.txt` "# Development" block (`:113-117`, beside `pytest`): `hypothesis==6.170.6` (the version the research read; the row re-reads PyPI and pins the latest at build time). New `be/tests/test_extract_properties.py` with `@settings(derandomize=True, database=None, max_examples=200, deadline=None)` so CI is deterministic and writes no `.hypothesis/` dir. Properties that hold **today** (so the row is not blocked on the fix rows): HC-PROP-001 `_parse_text_line` never raises on arbitrary text; HC-PROP-002 `_extract_dates` returns only ISO `YYYY-MM-DD` strings within `_date_is_plausible`; HC-PROP-003 a date directly after `DOB: ` is never returned (any plausible date, formats from the generic list); HC-PROP-004 `_extract_dates` on `label + spaces*n + date` stays under 1 s for n up to 20,000. (Review round 1 dropped a `ref_low <= ref_high` property: it fails today, `_parse_text_line('Glucose 105 mg/dL 99-70', 1)` gives 99/70; that is the not-yet-planned bullet RANGE-ORDER.) EXTRACT-TABLE-VALUE and EXTRACT-TEXT-FORMS may add properties once merged (not this row).
**Files:** `be/requirements.txt` (one line in the Development block), `be/tests/test_extract_properties.py` (new), slots. **Delta:** +4. **Est:** 1 h. **Order:** ready; never beside SQLCIPHER-WHEEL or RAPIDOCR-BUNDLE (`requirements.txt`, different hunks but the same file). If a property fails today, that is a found bug: stop and report it with the shrunk example, do not loosen the property. **MVP:** P2.

### AXE-E2E — @axe-core/playwright in the e2e suite

**Design:** `src/frontend/package.json` devDependency `@axe-core/playwright` (exact version, research read 4.14.0; re-read at build) + `package-lock.json`. New `src/frontend/e2e/accessibility.spec.ts`: for `/setup`, `/inbox`, `/verify`, `/trends`, `/explain`, `/settings` (authenticated via `e2e/support/auth.ts`), `new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa']).analyze()`; assert no violation of impact `critical` or `serious` except rule ids in a `KNOWN_A11Y` map, each entry naming the bullet that will fix it (FE-A11Y-DIALOGS) and the route. The first run's full violation list goes in the PR body. An entry may only be removed, never added later without a row. Runs in the existing CI e2e job (Playwright `testDir`), `ci.yml` not touched.
**Files:** `src/frontend/package.json`, `src/frontend/package-lock.json`, `src/frontend/e2e/accessibility.spec.ts` (new). **Delta:** 0 backend, +6 e2e. **Est:** 1.5 h. **Order:** ready; never beside another `package.json` PR. **MVP:** P2.

---

## Chat, interpretation and model rows

### FE-EXPLAIN-ERR — the chat's 401/403/501 messages never show, and the send button has no name

**Facts (re-read on `531c712`, after #295 merged):** `fe/pages/ExplainAssistant.tsx:414-428` `getErrorContent` tests `error.message.includes('501' | '401' | '403')`, but `ApiError.message` is the server `detail` (`fe/services/api.ts:96-112`), so the branches never match; `:803-822` the question input and the icon-only send button have no accessible name.

**Design:** branch on `error instanceof ApiError && error.status === 501 | 401 | 403`; keep the network branch; `aria-label="Your question"` on the input and `aria-label="Send question"` on the button.
**Test-first** (`fe/__tests__/ExplainAssistant.test.tsx`, extend after #295): HC-FEE-001 `ApiError(403, …, "Profile database not available…")` shows the session message (RED); HC-FEE-002 `ApiError(501, …)` shows the no-model message and sets `modelUnavailable` (RED); HC-FEE-003 `getByRole('button', { name: 'Send question' })` exists (RED).
**Files:** `fe/pages/ExplainAssistant.tsx` (`getErrorContent` + two attributes), `fe/__tests__/ExplainAssistant.test.tsx`. **Delta:** +3 Vitest. **Est:** 0.5 h. **Order:** ready (#295 merged `531c712`); never beside BADGE-TICK (same two files). **MVP:** P1.

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

**Superseded 2026-10-27 in part:** the chat half is already fixed by G-B5 (L0 ruling on #317), and the design, tests and files below are replaced by the [delta](#delta-2026-10-27-to-rag-timeout-answer-the-grounded-path-rag-timeout-grounded) that follows this section.

**Facts:** `be/modules/rag.py:1458-1461` (`_generate_with_runner`) and `:854-858` (`generate_response`) return a canned `"UNCERTAINTIES: I was unable to fully process your question within the time limit…"` string when `finish_reason == "timeout"`; it is validated and persisted as an assistant turn.

**Design:** on timeout raise a dedicated `GenerationTimeoutError(RuntimeError)` (no provider text). Both timeout branches sit inside `try:` blocks whose `except Exception` (`:863`, `:1472`) re-wraps everything as `RuntimeError`, so each gets an `except GenerationTimeoutError: raise` **before** the generic `except`. `query()` has no abstain path today: it catches `GenerationTimeoutError` and returns its normal result shape with one `uncertainty` segment holding `ABSTAIN_TEMPLATE` (imported from `be/modules/agent/guardrails/templates.py`, as `be/api/assistant.py:43` does), `is_valid=False`, `insufficient_context=True`, `insufficient_reasons=["generation_timeout"]`, so the route serves the abstain message and the turn is stored as an abstention, not an answer.
**Test-first** (`be/tests/test_rag_timeout_answer.py`, new; HTTP via `route_client` on `/assistant/chat`, agent off): HC-RTA-001 runner returns `finish_reason="timeout"` → response is the abstain text (RED); HC-RTA-002 the persisted turn is marked as not valid / abstained (RED); HC-RTA-003 a normal answer unchanged (pin).
**Files:** `be/modules/rag.py` (the two timeout branches + `query()` catch only), `be/tests/test_rag_timeout_answer.py` (new), slots. **Delta:** +3. **Est:** 1 h. **Order:** ready (#297 merged `afbe1af`; re-read the timeout branches on current main first). #264 (parked) also edits `rag.py`; never beside RUNNER-EXC-INTERP (same two `except` blocks). **MVP:** P1.

### Delta 2026-10-27 to RAG-TIMEOUT-ANSWER: the grounded path (RAG-TIMEOUT-GROUNDED)

**Why a delta.** #317 stopped at Task 0 on 2026-10-23 (comment 6371533697): the planned RED tests were already GREEN on the chat route, and the "raise" design broke two pins outside the row. L0 ruled (comment 6374422151): "Option **(c)** for the chat route, plus a plan delta for the rest. **No code in this PR.**" and "Whether to abstain here (and persist) is a design question. It goes to the planner as a plan delta, not to this row." This delta replaces the design, tests and file list above. #317 has no code (`gh pr diff 317 --name-only` is empty; one claim commit `527a1a59`). Facts re-read on `origin/main` @ `e0a995fc` (2026-10-27); unchanged at `018bd094`, where no `src/` file differs from `e0a995fc`.

**Facts.**

1. **Chat is already fixed (G-B5), and it stays as it is.** `_generate_with_runner` returns a canned text on `finish_reason == "timeout"` (`be/modules/rag.py:1461-1463`). The verifier fails that text, so `query()` returns `is_valid=False` with `["2 claim(s) could not be verified", "Low faithfulness score: 0.00"]` (pinned in `be/tests/legacy_eval/test_legacy_eval_gate.py:73`). `/assistant/chat` then serves `ABSTAIN_TEMPLATE` (`_legacy_serve_or_abstain`, `be/api/assistant.py:267-287`, called at `:1202`). Owner answers OQ-1 (**ABSTAIN_TEMPLATE**, which names timeouts) and W4-OQ-2 (**A: keep G-B5 + 20-q count**) cover this. The pins at `test_legacy_eval_gate.py:73` and `:90-92` stay unchanged.
2. **`generate_response`'s timeout branch (`rag.py:855-859`) has no production caller.** `git grep "generate_response("` under `be/api`, `be/modules` and `be/core` finds only its definition (`rag.py:821`). `be/tests/test_rag_pipeline.py:1391-1415` pins it. This delta does not touch it.
3. **The grounded route serves the canned text.** `POST /interpretations/observations/{id}/interpret-grounded` (`be/api/interpretations.py:496-688`) calls `rag.query` at `:583-592`. On a timeout, `query()` returns the canned text parsed into segments with `is_valid=False` and the two failed claim checks above. With safety mode **off**, nothing replaces it. `full_response` carries it (`:630-633`), and `verification` reports the failed claims (`:635-644`). With safety mode **on**, the SAFETY-MODE-STRICT branch already serves `ABSTAIN_TEMPLATE` and writes an `interpretation.strict_abstained` audit row (`:663-677`).
4. **Nothing is persisted on this path.** The grounded answer is never written (`interpretations.py:649-650`: "The grounded answer is not persisted anywhere"; no write after `rag.query`). The persisted `Interpretation` is the template interpretation written by `interpret_module.interpret_observation` before `rag.query` (`:538-549`). The "(and persist)" half of L0's question therefore has no subject on this route.
5. **What the patient sees today.** `LabInterpreter.tsx:95-101` shows `full_response` in the "Grounded explanation" card and a caution badge "Grounded faithfulness: 0%" (`:188-191`, `is_valid` false, score 0.00). The page has no error state for this request. `generateInterpretation` is used only for `isPending` (`:255`, `:273`, `:276`), so a 503 shows nothing at all.
6. **Withholding on this route is unsigned.** The owner answered GC5-OL-2 with this caveat in the question: "on /interpretations/.../interpret-grounded the answer is still served with every claim marked failed. That route has no withhold, and adding one is a separate gate." [GC5 plan](2026-10-18-GC5-hc-m11-nli-flag-off.md) `:163` adds: "withholding on that route is still unsigned". SAFETY-MODE-BEHAVIOUR's "Stricter checks" covers strict mode only, and fact 3 shows it already applies there.
7. **Ask-first files.** No option below edits `modules/interpret_safety.py`, `redaction.py`, `faithfulness.py` or `verifier_agent.py`. `validate_response` calls them; the shared core below skips `validate_response` only for the fixed timeout constant, which contains no model text. Every other response still goes through it (HC-RTA-004). If a build finds it needs an edit to one of those four files, it stops and L0 **asks the owner first**.

**Owner gate.** The patient-visible choice was an open owner question, now answered: **RAG-TIMEOUT-GROUNDED**, option 1 "Keep the sentence, label it" (2026-10-27; [Owner gates](#owner-gates) item 8; owner-decisions row RAG-TIMEOUT-GROUNDED). The planner did not decide it. The design below has a shared core and one branch per option; option 1 needs the shared core only.

**Design: shared core (options 1, 2 and 3).**

- `be/modules/rag.py`: move the timeout literal of `_generate_with_runner` (`:1462-1463`) into a module constant `GENERATION_TIMEOUT_TEXT`, byte-identical. Add `GENERATION_TIMEOUT_ERROR = "Generation timed out"`. `generate_response` (`:855-859`) is not touched.
- `query()` (`:1351-1358`): when `response == GENERATION_TIMEOUT_TEXT`, return `ValidatedResponse(segments=self._parse_response_segments(response), is_valid=False, validation_errors=[GENERATION_TIMEOUT_ERROR])` without calling `validate_response`. The segments are exactly today's, so the visible text is unchanged; only the claim checks on a sentence the model never wrote go away. `verification` falls back to `VerificationMetadata()`, so the grounded response's `verification.enabled` becomes false, `total_claims` 0, `issues` empty, `summary` empty and `faithfulness_score` 0.0. The Lab Interpreter badge therefore still shows 0%: the owner question states this. `insufficient_context` stays `False`, because chat shows a "Limited Context Available" banner when it is true (`ExplainAssistant.tsx:547-556`).
- No exception is added and no signature changes. HC-LEG-005 calls `_generate_with_runner` and `validate_response` directly (`test_legacy_eval_gate.py:87-94`), so its pins hold. On chat, HC-LEG-003 still sees `is_valid=False`, so G-B5 still abstains. The only chat change is the payload's `validation_errors`, which is now `["Generation timed out"]`; that field is not persisted.
- Known edge: a model answer that is byte-for-byte the timeout constant is also treated as a timeout. That answer is already `is_valid=False` today, so nothing is served that was not served before.

**Design: per option.**

| Option (owner's choice) | Extra change | Patient sees |
|---|---|---|
| 1 "Keep the sentence, label it" | none (shared core only) | same sentence and badge as today |
| 2 "Standard message, as chat" | `be/api/interpretations.py`: one `elif GENERATION_TIMEOUT_ERROR in rag_result.validation_errors:` after the strict branch (`:663-677`), shaped like it. Segments become `[uncertainty: ABSTAIN_TEMPLATE]`, `full_response = ABSTAIN_TEMPLATE` (recurring-failures #2: no canned text left in `full_response`), `verification = GroundedVerificationResponse()`, and an audit row `timeout_abstained` with `details={"reason": "generation_timeout", "decision": "abstain"}` | `ABSTAIN_TEMPLATE` (as chat, and as strict mode already shows) |
| 3 "Error, try again" | `be/api/interpretations.py`: one `elif not strict and GENERATION_TIMEOUT_ERROR in rag_result.validation_errors:` after the strict branch (`:663-677`), so safety mode on keeps serving `ABSTAIN_TEMPLATE` with its `strict_abstained` row (HC-RTA-005), and it raises the existing 503 with the I-16 detail "The explanation could not be generated right now. Please try again." (same as `:598-606`; the `interpretation.grounded` row at `:553-557` is already written). Frontend: an error message for a failed grounded request, in `fe/pages/LabInterpreter.tsx` before UI-PG-RESULTS merges, or in `fe/pages/ResultsPage.tsx` after it (UI-PG-RESULTS deletes `LabInterpreter.tsx`; never beside it) | the retry message |
| 4 "No change" | none | L0 closes #317 and the row (`won't-do`, citing the answer) |

**Test-first** (`be/tests/test_rag_timeout_answer.py`, new). The runner is `tests/legacy_eval/harness.py::FakeRunner(text="", finish_reason="timeout")`, so the real `_generate_with_runner` timeout branch runs. Routes go through HTTP: chat via `harness.legacy_chat_client`, grounded via `tests/test_safe_interp_grounded.py::_call` (`route_client`) with `I.get_rag_module` patched to a `RAGModule(enable_verification=True)` whose `retrieve_context` is an `AsyncMock` (the `test_empty_answer.py:53-71` pattern), and `core.external_runner.get_runner_for_request` patched to return the `FakeRunner`.

- **HC-RTA-001** (RED; options 1-3): `RAGModule.query` with the timeout runner returns `is_valid is False` and `validation_errors == ["Generation timed out"]`, and `rag.GENERATION_TIMEOUT_TEXT` equals main's literal. Today the errors are the two claim checks, and the constant does not exist.
- **HC-RTA-002** (RED; options 1-3): `interpret-grounded`, safety mode off, timeout runner: `validation_errors == ["Generation timed out"]`, and `verification` has `enabled` false, `total_claims == 0` (today 2) and `issues == []`. The rest is per option:
  - option 1: 201, and `full_response` equals the value Task 1 measures on main (a pin, written before the fix).
  - option 2: 201, `full_response == ABSTAIN_TEMPLATE`, the canned sentence is not in `resp.text`, and the audit rows are `["interpretation.grounded", "interpretation.timeout_abstained"]` with no question or answer text in any row (the `test_safe_interp_grounded._row_blob` check).
  - option 3: 503 with the I-16 detail, and the audit rows are `["interpretation.grounded"]`.
- **HC-RTA-003** (pin, GREEN before and after): `/assistant/chat` with the timeout runner still serves and persists `ABSTAIN_TEMPLATE` (OQ-1, W4-OQ-2).
- **HC-RTA-004** (pin): a non-timeout answer (`test_safe_interp_grounded.CLEAN_ANSWER`) through `interpret-grounded` keeps its main verdict (`MEASURED_CLEAN_IS_VALID` as in `test_empty_answer.py:28`), and `"Generation timed out"` is not in its errors. This guards against a short-circuit that fires on every answer.
- **HC-RTA-005** (pin): safety mode on plus the timeout runner still serves `ABSTAIN_TEMPLATE` with exactly one `interpretation.strict_abstained` row (fixture as `test_safety_mode_strict.py`, with a **user-verified** observation, or `_refuse_unverified` at `interpretations.py:529` fires first), so option 2 never writes a second decision row.
- **Option 3 only:** HC-RTA-006 (vitest, `fe/__tests__/lab-interpreter-error.test.tsx` new, or the ResultsPage test if UI-PG-RESULTS has merged): a rejected grounded mutation renders the error text.

**Tasks.**

1. Task 0 as RUNBOOK §4. Quote the RAG-TIMEOUT-GROUNDED answer; with option 4 stop, and L0 closes #317. Re-read the lines above on current main. Measure today's grounded response for the timeout runner and paste `full_response` (option 1's pin), `validation_errors` and `verification.total_claims`. The "two failed checks" in the plan and in the owner question come from the chat golden case (`test_legacy_eval_gate.py:73`, same `validate_response`), not from this route; if the measurement differs, L0 corrects the question before asking.
2. Write HC-RTA-001…005 (and 006 for option 3). Capture RED for 001 and 002 and GREEN for 003-005 on main.
3. Shared core in `rag.py`. Then the option's route branch (option 2 or 3) and the frontend change (option 3).
4. Re-run the pins: HC-LEG-003, HC-LEG-005, `test_generate_response_handles_timeout`, HC-LCPH-019, HC-EAS-003/004, `test_safe_interp_grounded.py`, `test_safety_mode_strict.py`.

**Files** (by option):

- Options 1-3: `be/modules/rag.py` (one constant pair, the `_generate_with_runner` timeout `return`, and the `query()` short-circuit only), `be/tests/test_rag_timeout_answer.py` (new), slots.
- Options 2 and 3 add `be/api/interpretations.py` (the one branch above only).
- Option 3 adds `fe/pages/LabInterpreter.tsx` or `fe/pages/ResultsPage.tsx`, plus the vitest file.
- **Not edited:** `be/tests/legacy_eval/*`, `be/tests/test_rag_pipeline.py`, `be/api/assistant.py`, and the four ask-first modules.
- **Delta:** +5 backend (option 3: +5 backend, +1 vitest). **Est:** option 1 1 h, option 2 1.5 h, option 3 2.5 h. **Contracts:** option 3 widens I-16's trigger (503 on a timeout as well as on `RuntimeError`); L0 notes it on the I-16 row in the post-merge batch. Options 1 and 2 leave I-16 unchanged.

**Acceptance** (in the worktree, after the final `git merge origin/main`; paste the output):

```bash
cd src/backend
P="$(git rev-parse --show-toplevel)/scripts/pyslot.sh"
"$P" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest -p no:cacheprovider -q tests/test_rag_timeout_answer.py
"$P" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest -p no:cacheprovider -q \
  tests/legacy_eval/test_legacy_eval_gate.py tests/test_rag_pipeline.py tests/test_rag_headerless.py \
  tests/test_empty_answer.py tests/test_safe_interp_grounded.py tests/test_safety_mode_strict.py
git diff --name-only origin/main...HEAD -- modules/interpret_safety.py modules/redaction.py modules/faithfulness.py modules/verifier_agent.py tests/legacy_eval   # must print nothing
git diff origin/main...HEAD -- modules/rag.py | grep -c '^-.*I was unable to fully process'   # 1: only the _generate_with_runner literal moved
```

Then RUNBOOK §6 steps 2-6: the full suite (no new failures beyond the 5 environmental ones in CLAUDE.md §4), the collected count with its delta, `python -c "from main import app"`, and `git status --short`. Option 3 also runs `cd src/frontend && npx tsc --noEmit`, with vitest on Windows or CI.

**Order:** RAG-TIMEOUT-GROUNDED answered 2026-10-27 (option 1). L0 posted the `L0 ruling:` comment on #317 naming option 1 (comment 6460409318, 2026-10-28T04:07Z) and resumed build-item `{id: "RAG-TIMEOUT-ANSWER", resume_pr: 317}`. Rules for parallel work:

- Options 2 and 3: never beside another row whose file list includes `be/api/interpretations.py` (no open or ready row lists it on `e0a995fc`; B-5 is blocked).
- With option 3, never beside UI-PG-RESULTS.
- #264 (B-3, parked) also edits `rag.py` and rebases onto this row.

**MVP:** P1 (unchanged; the chat demo path is already safe).

### RUNNER-EXC-INTERP — five log lines and two exception messages interpolate the provider exception text

**Facts:** `be/modules/rag.py:863-865` and `:1472-1474`: `self._logger.error(f"LLM generation failed: {e}")` and `raise RuntimeError(f"Failed to generate response: {e}")`; `be/modules/interpret.py:783-784` `logger.error(f"LLM interpretation failed: {e}, …")`; `be/api/interpretations.py:883` `logger.error(f"Batch interpretation error for {obs_id}: {e}")`; `be/modules/extract_visit_notes.py:503-504` `logger.warning("llm_assist_visit_entities: inference failed: %s", exc)` (same shape, review round 1). Provider text can carry prompt (PHI) fragments; RUNNER-EXC-LOG (#285) and RUNNER-EXC-CHAIN (#300) fixed the runner and two route handlers, not these.

**Design:** log `type(e).__name__` only; the `RuntimeError` message becomes the fixed `"Failed to generate response"` with `from e` kept (the chain is never printed by these handlers after #300).
**Test-first** (`be/tests/test_runner_exc_interp_logs.py`, new): HC-REI-001 a provider raising `RuntimeError("SECRET-PHI-123")` through `RAGModule._generate_with_runner`: no log record and no `str()` of the raised error contains the token (RED); HC-REI-002 same for `generate_response`; HC-REI-003 `InterpretModule` LLM path; HC-REI-005 `llm_assist_visit_entities` with a raising runner logs no token; HC-REI-004 `POST /interpretations/batch` (`api/interpretations.py:801-802`) via `route_client` (each RED).
**Files:** `be/modules/rag.py` (the two `except` blocks only), `be/modules/interpret.py` (`:783-784` only), `be/api/interpretations.py` (`:883` only), `be/modules/extract_visit_notes.py` (`:503-504` only), `be/tests/test_runner_exc_interp_logs.py` (new), slots. **Delta:** +5. **Est:** 0.75 h. **Order:** ready (#300 `f588571` and #304 `64b92eb` merged); never beside INTERP-SAFETY-ENFORCE or INTERP-REGEN-500 (`interpret.py`), RAG-TIMEOUT-ANSWER (`rag.py`) or VISIT-ASSIST-THINK (`extract_visit_notes.py`). **MVP:** P1.

### LLAMA-UNLOAD-LOOP — switching provider blocks the event loop while a generation runs

**Facts (on `531c712`):** `be/api/model_settings.py:887-910` `async def set_llm_provider` calls `reset_provider()` synchronously (`:910`); `be/core/llm/factory.py:77-85` calls `_active_provider.unload()`. Since #297 (merged), `LlamaCppProvider.unload()` (`be/core/llm/llama_cpp_provider.py:382`) takes the model lock and the init lock (`with self._model_lock, self._init_lock`), so a switch during a generation blocks the whole event loop (every request) until the generation ends or times out. No other async caller of `reset_provider` / `unload` (grep).

**Design:** `await asyncio.to_thread(reset_provider)`; nothing else.
**Test-first** (`be/tests/test_provider_switch_nonblocking.py`, new, `route_client` + a fake provider whose `unload` blocks on an `Event`): HC-LUL-001 while `PUT /settings/model/provider` waits in `unload`, a concurrent request to another route on the same app answers within 1 s (RED: the loop is blocked); HC-LUL-002 the switch completes after the event is set (pin).
**Files:** `be/api/model_settings.py` (`:910` only), `be/tests/test_provider_switch_nonblocking.py` (new), slots. **Delta:** +2. **Est:** 0.75 h. **Order:** ready (#297, #295 merged). **MVP:** P1.

### BADGE-TICK — the chat badge flashes a tier label, and names `phi-3-mini` for an auto-detected GGUF

**Facts (on `531c712`):** #295's `activeModelSummary` (`fe/pages/ExplainAssistant.tsx:285-305`) falls back to the tier label (`modelSettings.tier_availability[tier].model`, e.g. "BioMistral-7B") while `useProviderInfo()` is still loading, so the wrong name shows for one render. `be/core/llm/llama_cpp_provider.py:221-224` `capabilities()` reports `settings.default_chat_model` ("phi-3-mini", `core/config.py:92`) until a model has been loaded, although `_find_model_path` (`:98-128`) would pick another GGUF (gemma4, …); with `probe=false` (#295) no load happens, so the badge names a model that is not the one that will answer.

**Design:** frontend: while provider info is loading, show "Local model" (no tier fallback). Backend: `capabilities()` uses `Path(self._model_path or self._find_model_path()).stem` when a file is found (glob only, no load), else `default_chat_model`.
**Test-first:** HC-BTK-001 (`fe/__tests__/ExplainAssistant.test.tsx`) provider info pending → badge "Local model", never the tier name (RED); HC-BTK-002 (`be/tests/test_llama_capabilities_name.py`, new) a temp models dir with only `gemma-4-e4b-it-Q4_K_M.gguf` → `capabilities().model_name == "gemma-4-e4b-it-Q4_K_M"` and no `Llama` constructed (RED).
**Files:** `fe/pages/ExplainAssistant.tsx` (`activeModelSummary` only), `fe/__tests__/ExplainAssistant.test.tsx`, `be/core/llm/llama_cpp_provider.py` (`capabilities` only), `be/tests/test_llama_capabilities_name.py` (new), slots. **Delta:** +1 backend, +1 Vitest. **Est:** 0.75 h. **Order:** ready (#295, #297 merged); never beside FE-EXPLAIN-ERR (same two frontend files) or CPU-DEFAULT-PHI4 (`llama_cpp_provider.py`). **MVP:** P2.

### CPU-DEFAULT-PHI4 — Phi-4-mini is the default chat model on CPU-only machines

Owner: **CPU-DEFAULT-MODEL answered "A and B"** (free text; L0 reading: Phi-4-mini is the default now; Qwen3-4B is added as a measured option once JUDGE-THINK lands; which becomes the long-term default is decided on the measurement; owner prompts 40-41, owner-decisions row CPU-DEFAULT-MODEL, L0 PR #301). This row is part A; QWEN3-4B-TIER is part B; gate CPU-MODEL-FINAL decides after.

**Facts (`0e2799b`):**
1. `be/modules/hardware_detection.py:40` `TIER_ORDER = ["high", "gemma4-12b", "mid", …]` and `:339-357` pick the first tier whose RAM/disk fit; a 16-31 GB CPU-only laptop gets `gemma4-12b` (7-8 GB Q4, a thinking model, no GPU), 32 GB+ gets `high` (BioMistral-7B, 4K context).
2. `be/modules/model_selector.py:85-111` `"mid"` is Phi-4-mini (bartowski Q4_K_M, 16K context, MIT); `be/scripts/download_models.py:100-104` labels it "Tier: mid (Phi-4-mini)"; but `hardware_detection.py:376-379` `get_tier_display_info["mid"]["model"]` still says "Phi-3-mini-4k-instruct".
3. The chat provider picks a file by glob, not by tier (on `531c712`, after #297): `be/core/llm/llama_cpp_provider.py:108-117` tries `f"{default_chat_model}*.gguf"` first (`core/config.py:92` `"phi-3-mini"`), then `gemma4*`, `gemma-4*`, `phi-3*`, … `*.gguf`; a downloaded Phi-4-mini file (`microsoft_Phi-4-mini-instruct-Q4_K_M.gguf`, the selector's `filename_pattern` `q4_k_m`) matches only the last `*.gguf`, after any gemma4 file. The provider's own GPU signal is `self._n_gpu_layers` (`:72-79`), set from `settings.llm_n_gpu_layers` (#297, `core/config.py:112-114`, `0` = CPU only, the default).

**Design (scope: machines without GPU offload configured, `LLM_N_GPU_LAYERS` = 0, the default (`core/config.py:114`); this includes a GPU machine that never set it, which also gets Phi-4-mini first; machines with offload set are unchanged; review rounds 1-2):**
1. `get_recommended_tier_from_hardware`: when the GPU boost does not apply (`gpu_vram_gb` is `None` or below `GPU_VRAM_BUMP_MIN_GB`), skip `gemma4-12b`, so 16-31 GB CPU laptops get `mid` (Phi-4-mini). **`high` on 32 GB+ CPU machines is unchanged in this row** (the existing `test_ram_only_high` pin stays as is); whether it should also become Phi-4-mini is part of CPU-MODEL-FINAL.
2. `LlamaCppProvider._find_model_path`: **only when `self._n_gpu_layers == 0`** (CPU inference), a `*Phi-4-mini*.gguf` pattern is tried right after the `default_chat_model` pattern and before the gemma4 patterns. With GPU offload set, the order is exactly today's. `default_chat_model` and `config/.env.example` are not changed (changing them would move every machine, which the owner was not asked).
3. `get_tier_display_info["mid"]` label → "Phi-4-mini-instruct".
**Test-first** (`be/tests/test_cpu_default_model.py`, new): HC-CPU-001 `get_recommended_tier_from_hardware(16.0, 100.0, None) == "mid"` and `(24.0, 100.0, None) == "mid"` (RED: `gemma4-12b`); HC-CPU-002 `(24.0, 100.0, 16.0) == "high"` (GPU path unchanged, pin); HC-CPU-003 a temp models dir with a gemma4 file and the Phi-4-mini file, `n_gpu_layers=0` → `_find_model_path()` returns the Phi-4-mini file (RED); HC-CPU-004 the same dir with `n_gpu_layers=35` → the gemma4 file (pin: GPU order unchanged); HC-CPU-005 display label (RED). Re-run, not edited: `tests/test_hardware_detection.py` (its `in ("mid", "gemma4-12b")` assertion accepts both), `tests/test_llama_cpp_provider_fixes.py`, `tests/test_llm_provider_layer.py`.
**Files:** `be/modules/hardware_detection.py` (`get_recommended_tier_from_hardware` + the `mid` display entry only), `be/core/llm/llama_cpp_provider.py` (`_find_model_path` patterns only), `be/tests/test_cpu_default_model.py` (new), slots. **Delta:** +5. **Est:** 1 h. **Order:** ready (#297 merged); never beside BADGE-TICK (`llama_cpp_provider.py`). **MVP:** P0 (stakeholder laptops have no GPU).

### QWEN3-4B-TIER — measure Qwen3-4B on CPU as the candidate long-term default (no product code)

**Steps (GPU box, CPU-only mode `CUDA_VISIBLE_DEVICES=` / `n_gpu_layers=0`, scratch dir):** fetch `Qwen3-4B` Q4_K_M (Apache-2.0; record repo, file, sha256, size) and Phi-4-mini Q4_K_M; for each: (1) `llama-bench` prompt-processing and generation tokens/s on 4 and 8 threads; (2) the judge preview (`gpu-1022/judge_preview.py` shape, 40 texts) with **thinking off** as JUDGE-THINK provides (`/no_think` or the chat-template switch on llama.cpp, `think=false` on Ollama), ALLOW/BLOCK/UNAVAILABLE counts; (3) the MM-4 chat subset (verified-data questions) answer length, citation validity and `finish_reason`; (4) peak RSS. One table, both models, same machine, same day. Evidence file only; it feeds **CPU-MODEL-FINAL**.
**Files:** `docs/reviews/<run date>/qwen3-4b-tier.md` (new), `docs/INDEX.md`, `docs/_link_graph.json`. **Est:** 3 h. **Runtime:** L0 or claude on the GPU box (model host; never beside another model-host run or a pytest run). **Order:** blocked on JUDGE-THINK (#305) merged. **MVP:** P2.

### VISIT-ASSIST-THINK — the gemma4 visit-note assist returns nothing because it thinks through its whole budget

**Facts:** KV evidence ([#298, "Other findings" 1](../reviews/2026-10-22/kv-prefix-measure.md)): with `gemma4:e4b` the visit-note assist answer was empty in 11 of 11 runs (`num_predict` 512, `eval_count` 512, `done_reason: length`); Ollama returned the tokens in `thinking`. `be/modules/extract_visit_notes.py:477-504` calls `runner.generate_async(…, InferenceConfig(max_tokens=512, temperature=0.0))`. JUDGE-THINK (#305, in flight) adds `InferenceConfig.think` and sends it only when set; the owner's JUDGE-THINK (a) was **judge only**, so using it here needs its own answer.

**Design (if VISIT-THINK says yes):** `InferenceConfig(max_tokens=512, temperature=0.0, think=False)` in `llm_assist_visit_entities` only. The hard validation of proposals (`:478-490` docstring) is unchanged.
**Test-first** (`be/tests/test_visit_assist_think.py`, new): HC-VAT-001 the config passed to a recording runner has `think is False` (RED); HC-VAT-002 an `OllamaProvider` body built from it has `"think": false` (RED); HC-VAT-003 the chat and interpretation configs still have no `think` (pin). Model-host check (L0): 11 visit-note runs on `gemma4:e4b` give non-empty answers.
**Files:** `be/modules/extract_visit_notes.py` (`:499-502` only), `be/tests/test_visit_assist_think.py` (new), slots. **Delta:** +3. **Est:** 0.5 h. **Owner gates:** **VISIT-THINK** (new, execution gate, [item 4](#owner-gates)). **Order:** blocked on JUDGE-THINK (#305) merged and VISIT-THINK; never beside RUNNER-EXC-INTERP (`extract_visit_notes.py`). **MVP:** P1 (the visit-note assist is opt-in, default off).

### INTERP-REGEN-500 — regenerating an existing interpretation fails with a UNIQUE constraint error

**Facts:** KV evidence ("Other findings" 2): `POST /interpretations/observations/{id}/interpret-grounded?force_regenerate=true` on an observation that already has an interpretation → 500 `UNIQUE constraint failed: lab_interpretations.observation_id`. `be/models/interpretation.py:50-56` `observation_id` is `unique=True`. `be/modules/interpret.py:272-279` (template path) and `:1028-1034` (LLM path) call `profile_db.delete(existing_interp)` then `profile_db.add(interpretation)` and commit once; SQLAlchemy's unit of work emits the INSERT before the DELETE, so the new row collides. `previous_interpretation_id` (`:107`) is not a foreign key. Existing route tests use a fake interpret module (`tests/test_audit_order.py:453`), so they cannot see it.

**Design:** `await profile_db.delete(existing_interp)` followed by `await profile_db.flush()` before `add`, at both sites; nothing else.
**Test-first** (`be/tests/test_interpret_regenerate.py`, new, `route_client`, real `InterpretModule`, template path, in-memory profile DB with the real unique constraint): HC-IRG-001 `POST …/interpret?force_regenerate=true` twice → both 201, `regeneration_count == 1`, `previous_interpretation_id` = the first id (RED: second is 500); HC-IRG-002 same through `interpret-grounded` with the RAG step stubbed (RED); HC-IRG-003 exactly one row remains (pin).
**Files:** `be/modules/interpret.py` (`:276` and `:1031` + one `flush` each), `be/tests/test_interpret_regenerate.py` (new), slots. **Delta:** +3. **Est:** 0.75 h. **Order:** ready (#304 INTERP-SAFETY-META `64b92eb` merged); never beside INTERP-SAFETY-ENFORCE, RUNNER-EXC-INTERP or B-5. **MVP:** P1 ("Regenerate" on the lab card).

### GAUGE-ZERO-WIDTH — the reference gauge divides by zero when low = high = value

**Facts (on `531c712`):** `fe/components/lab-interpreter/ReferenceRangeComparison.tsx:20-30`: `range = refHigh - refLow`, `padding = range * 0.3`; with #295's axis change (`:22-25`), `refLow == refHigh == value` gives `displayMin == displayMax`, `displayRange = 0`, and the percentages are `NaN` (also `0/0` when all are 0).
**Design:** when `range <= 0`, `padding = Math.max(Math.abs(refHigh) * 0.3, 1)`; if `displayRange` is still not a positive finite number, render the text row only (no gauge).
**Test-first** (`fe/__tests__/ReferenceRangeComparison.test.tsx`, new): HC-GZW-001 `value=5, refLow=5, refHigh=5` renders no `NaN` in any `style` (RED); HC-GZW-002 all zero (RED); HC-GZW-003 a normal range unchanged (pin).
**Files:** `fe/components/lab-interpreter/ReferenceRangeComparison.tsx` (`:20-30` only), the new test. **Delta:** +3 Vitest. **Est:** 0.5 h. **Order:** ready (#295 merged). **MVP:** P2.

### CACHE-DATE-TEST — no test covers the date-entity rows in the agent cache key's `e:` part

**Facts:** #290 review round 2 MINORs: `be/api/assistant.py:780-796` hashes `event_rows + date_rows` into the `e:` part; mutating it to `_digest(event_rows)` leaves all HC-CACHE-VER tests green. `be/tests/test_assistant_cache_version.py:231` calls an in-place `entity_value` edit "a reprocess", but a reprocess deletes and recreates entities under new ids (`api/documents.py:1203`).
**Design:** test only: HC-CACHE-VER-014 (new test in the same file) adds a `visit_date` `DocumentEntity` to a document with no `collection_date` and asserts the version changes (RED under the mutation, which the PR shows by running it once against a scratch copy); fix the `:231` comment to "same row count, different content (an in-place value edit): only the m: hash sees it". `api/assistant.py` not edited.
**Files:** `be/tests/test_assistant_cache_version.py` (one test + one comment), slots. **Delta:** +1. **Est:** 0.3 h. **Order:** ready. **MVP:** P2.

### Delta to existing rows: OLLAMA-NUM-CTX and KV-PREFIX-MEASURE (OQ-KV-LOCK (a))

1. **KV-PREFIX-MEASURE** is done: evidence merged in #298 ([kv-prefix-measure.md](../reviews/2026-10-22/kv-prefix-measure.md)).
2. **OLLAMA-NUM-CTX** is ready with **value 8192** (evidence item 3: the smallest size that holds the largest case plus its output, 4350 + 1024 = 5374 tokens, 100% GPU, about +0.3 GiB VRAM over 4096, at or below every `capabilities().context_len`). The lane A plan's `_OLLAMA_NUM_CTX` constant is `8192`. HC-ONC-001 as planned (lane A) uses `llama3.1:8b` (`context_len` 8192) and asserts `min(_OLLAMA_NUM_CTX, 8192)`, which a constant of 16384 would also pass, so the row **adds HC-ONC-003**: `OllamaProvider(model="gemma4:e4b")` (`context_len` 262144) body has `options.num_ctx == 8192` (RED today: no `num_ctx`); delta +1 over the lane A plan. It still never runs beside JUDGE-THINK (#305, same `_build_request_body`); whichever lands second merges `origin/main` and re-runs both test files.
3. **OQ-KV-LOCK answered "(a) Accept the window"** (owner prompts 40-41, owner-decisions row OQ-KV-LOCK, L0 PR #301): after a lock or logout, the last prompt's state may stay in local Ollama memory until `keep_alive` expires (5 min; measured 55 s+ after lock in #298 run 2). No code: no `OllamaProvider.unload`, no `keep_alive` change, no lock hook. OLLAMA-NUM-CTX must not add a `keep_alive` field.

### KV-NUMCTX-VERIFY: show that Ollama really runs the app's requests at `num_ctx` 8192 (model host; no code)

**Source.** Bullet KV-NUMCTX-VERIFY (queue, "found 2026-10-23, #318 PR body"). #318 (OLLAMA-NUM-CTX, merged `1aee199`) lists this under "Not run", quoted: "re-run KV-PREFIX-MEASURE step 3 for its largest case through the provider, under the flock wrapper. The pass condition is a `prompt_eval_count` equal to the 32768 run and no `truncat` line in the journal. Reason: it needs the GPU, the local Ollama model and the journal, so RUNBOOK §10.1 routes it to L0 after the PR. The unit tests cannot show that Ollama honours `options.num_ctx`."

**Facts** (re-read on `origin/main` @ `e0a995fc`, 2026-10-27; unchanged at `018bd094`, where no `src/` file differs).

1. `be/core/llm/ollama_provider.py:42` `_OLLAMA_NUM_CTX = 8192`, and `:143` sends `"num_ctx": min(_OLLAMA_NUM_CTX, self.capabilities().context_len)` in `_build_request_body` (`:135-149`).
2. HC-ONC-001…003 (`be/tests/test_ollama_num_ctx.py`) assert the request body only. Nothing in the repo shows that the Ollama server loads the model at that size.
3. The 2026-10-22 baseline is [kv-prefix-measure.md](../reviews/2026-10-22/kv-prefix-measure.md):
   - Box and model: Ollama 0.40.5, `gemma4:e4b`, RTX 3080 10 GiB, tree `5f7c67c`.
   - Server default context: 4096 (`ollama ps` `CONTEXT` 4096).
   - Case d (largest legacy chat): 2051 tokens at the default with the journal line `truncating input prompt limit=2051 prompt=4350`, and 4350 tokens at `num_ctx` 32768.
   - Case c (typical legacy chat): 3585 tokens; at 4096 the output was cut after 510 tokens (`n_tokens = 4095, truncated = 1`).
   - That run POSTed captured bodies straight to `/api/chat` ("step 3", `:94-145`), and those bodies predate `num_ctx`.
4. The scripts are in the evidence file's appendix, not in the repo: `prompts.py` (`:457-693`), `mlib.py` (`:695-736`) and `step3.py` (`:738-764`). `prompts.py` builds each body with the real `OllamaProvider._build_request_body` (`:592`), so on current main the captured bodies carry `options.num_ctx` 8192 by construction. `/tmp/claude-1000/kv-1022/` may be gone after a restart; recreate the scripts from the appendix.

**Owner answers used.** KV-CACHE-NEXT: **Measure first (Recommended)**. OQ-KV-LOCK: **(a) Accept the window**, so the run adds no `keep_alive` to product code; the scratch `unload()` helper's `keep_alive: 0` call is measurement only, as in 2026-10-22. No new gate. A failed check is a finding for L0, not a decision.

**Isolation (model-host rules).**

- One model-host run at a time: never beside QWEN3-4B-TIER, AUDIT-DB-LOCKED Task 1, JUDGE-LAYA-FT, JUDGE-NLI-TUNE or MM-2.
- No pytest beside it: every model call runs under `bash /tmp/claude-1000/hold_slots.sh <cmd>`, which holds pyslot locks 1–8. Recreate the script from the [2026-10-26 handoff](2026-10-26-session-handoff.md) appendix if `/tmp` was wiped.
- Never during a UI-SHELL stillness run. Before starting, and before each step, wait while `/tmp/claude-1000/quiet-box.lock` exists or `pgrep -f "playwright|vitest"` matches. A `pgrep -f` on the row's own script name matches the agents' own shells, so check the load instead (handoff §4).

**Steps** (scratch dir `/tmp/claude-1000/kvv-<date>/`, scratch worktree at `origin/main`; product code is not edited):

1. **Setup record.** Record the following:
   - `ollama -v`
   - `systemctl show ollama -p Environment` (`OLLAMA_CONTEXT_LENGTH` set or unset; if set, record the value: the request's `num_ctx` should override it, and the run shows whether it does)
   - `ollama list | grep gemma4:e4b`
   - `nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv`
   - `ollama ps` (empty)
   - the worktree SHA
   - `git grep -n "_OLLAMA_NUM_CTX = 8192" -- src/backend/core/llm/ollama_provider.py`

   The embedding bundle must be present in the worktree (`python scripts/download_models.py embedding`, or copy it as the handoff setup does).
2. **Capture.** Run `prompts.py` from the appendix with `OUT` pointed at the scratch dir. Record:
   - each case's total characters against the 2026-10-22 table (main has moved since `5f7c67c`, so the prompts may differ; report the difference, do not adjust it);
   - `body["options"]["num_ctx"]` for cases c and d, which must be 8192.

   If the script no longer runs on current main, fix the scratch copy only and paste the diff.
3. **Through the app's runner.** Run under `hold_slots.sh`, model unloaded first. Call `get_model_runner()` with `LLM_PROVIDER=ollama LLM_MODEL=gemma4:e4b`, then `generate_async(prompt_d, config_d)`. `prompt_d` is case d's captured `prompt`. `config_d` is an `InferenceConfig` matching the captured body: `max_tokens`, temperature, top_p, and the cite schema if the body has `format`. Raise `timeout_seconds` to 300 so a cold load cannot time out. Then record `ollama ps`. Pass: `CONTEXT` 8192 and `PROCESSOR` 100% GPU.
4. **Token counts.** For cases d and c, with the model unloaded before each request, POST the captured body unchanged (provider-built, `num_ctx` 8192), then the same body with `options.num_ctx` = 32768 (the 2026-10-22 reference). Record `prompt_eval_count`, `eval_count`, `done_reason`, `ollama ps` after each request, and each request's start and end time (`date -Is` before and after), so journal lines can be attributed to one request.
5. **Journal.** Run `journalctl -u ollama --since "<step 3 start>" --no-pager | grep -i truncat` and paste every hit, each tagged with the request whose start-end window contains its timestamp.

**Pass conditions** (all of them; written down before the run):

- (i) step 2: `num_ctx` is 8192 in both bodies;
- (ii) step 3: `CONTEXT` is 8192 and `PROCESSOR` is 100% GPU;
- (iii) step 4: for case d, `prompt_eval_count` at 8192 equals the 32768 run's count;
- (iv) step 5: no `truncating input prompt` line, and no `truncated = 1` slot line, inside the start-end window of any 8192 request;
- (v) step 4: case c at 8192 is not stopped near `n_tokens` 4095. Its `eval_count` reaches 1024 or it ends with `stop`.

If any check fails, the evidence file says so, quotes the raw lines, and adds a new follow-up bullet to the queue. The row changes no code and does not re-open OLLAMA-NUM-CTX by itself; L0 decides.

**Files:** `docs/reviews/<run date>/kv-numctx-verify.md` (new; setup, raw outputs, pass table, the scratch scripts or their diff from the 2026-10-22 appendix), `docs/INDEX.md`, `docs/_link_graph.json`. No `src/` file, no pytest, no slot change. **Est:** 1 h. **Runtime:** claude or L0 on the GPU box (model host). It holds no code slot, and its PR is docs only.

**Acceptance:** the evidence file has every raw output above and a pass/fail line for each of (i)-(v). Then run `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph && python3 scripts/docs_lint.py`. `git diff --name-only origin/main...HEAD` lists only the three files.

**Order:** ready (OLLAMA-NUM-CTX done, #318 `1aee199`). Run it between other model-host rows, with the box quiet. **MVP:** P2. It is evidence for a fix already shipped: the demo's legacy chat fallback (cases c and d) depends on it, and the agent path does not (cases a and b fit at 4096).

---

## CI and e2e

### CI-CACHE — CI reinstalls torch and the requirements in four jobs with no pip, HF or Playwright cache

**Facts:** `.github/workflows/ci.yml` installs `torch` + `requirements.txt` in backend-tests (`:54-55`), agent-evals (`:215-216`), legacy-evals (`:237-238`) and e2e (`:273-274`), and `requirements.txt` without torch in security-scan (`:164`); only the npm cache is set (`:104`, `:254`). MVP pass: about 14.5 min critical path (run 39843670560).
**Design:** `actions/setup-python` `cache: pip` with `cache-dependency-path: src/backend/requirements.txt` in those five jobs; `actions/cache` for `~/.cache/ms-playwright` keyed on the Playwright version in `package-lock.json`. No HF cache (no job downloads models today). No job removed, no step skipped.
**Acceptance:** two runs on the PR: the second run's "Install dependencies" step durations against the first, pasted per job; all jobs green. **Files:** `.github/workflows/ci.yml` (setup steps only). **Est:** 1 h. **Runtime:** claude (no slot; owner merges CI files). **Order:** ready; never beside another `ci.yml` PR (SQLCIPHER-WHEEL uses its own workflow file). **MVP:** P2.

### E2E-UIFULL-CI — the real-backend UI suite never runs in CI, and the upload test passes on the file name

**Facts:** `src/frontend/e2e/ui-full-verification.spec.ts:15-49`: the whole suite (routes, chat, settings and the PDF flow) is skipped unless `HC_E2E_REAL_PDF` points at a file (Windows default `F:\…`); CI never sets it. `src/frontend/e2e/document-import.spec.ts:54-57` (E2E-DOC-002) passes on `/test-report\.pdf|pending|needs review|parsed/i`, which the filename echo satisfies even when the backend rejects the file.
**Design:** split the non-PDF part (sidebar routes, chat, settings) into `ui-routes-verification.spec.ts` that always runs; the PDF part uses a committed synthetic text-lab PDF fixture (`src/frontend/e2e/fixtures/synthetic-lab.pdf`, generated by a script in the spec's header comment; no real data) when `HC_E2E_REAL_PDF` is unset. E2E-DOC-002 asserts a document row whose backend status is `parsed` or `needs review` from the documents API (not the toast text).
**Test-first:** E2E-DOC-002 fails against a backend stubbed to reject the upload (shown once in the PR); the new routes spec runs in CI (job log line).
**Files:** `src/frontend/e2e/ui-full-verification.spec.ts`, `src/frontend/e2e/ui-routes-verification.spec.ts` (new), `src/frontend/e2e/document-import.spec.ts` (E2E-DOC-002 only), `src/frontend/e2e/fixtures/synthetic-lab.pdf` (new). **Delta:** 0 backend; e2e count in the PR. **Est:** 2 h. **Order:** ready; never beside SESSION-REENTRY's e2e file (different files; disjoint) or AXE-E2E (disjoint). **MVP:** P1.

---

## Owner gates

Item 8 (RAG-TIMEOUT-GROUNDED, 2026-10-27) and item 5 (EXPORT-PURGE-DIFF, 2026-10-24) are answered, with their rows in owner-decisions; the other items are still open. Each is asked by L0 only when its trigger exists; no answer is inferred. Wording is a draft; L0 asks it, the owner's words are recorded verbatim in owner-decisions.

1. **SQLC-WHEEL-DIFF** (SQLCIPHER-WHEEL; merge only; asked with the draft PR's final diff).
   - Question: "Here is the exact change that turns encryption on for Windows and Mac. Linux keeps the package it uses today; Windows and Mac get `sqlcipher3`, which has the encryption built in. The setup script now stops instead of quietly turning encryption off, and the app refuses to start without real encryption. You wrote 'for window'; this also covers Mac. May it merge?"
   - Options: "Merge as shown" (Windows and Mac get encrypted profiles; tested on the Windows box and in CI on all three systems). "Windows only, not Mac" (Mac stays unencrypted until someone tests it on a Mac). "Merge, no unencrypted fallback" (as shown, but without the developer switch that lets a failed install save data unencrypted). "Do not merge" (profiles on Windows and Mac stay unencrypted).
   - Tradeoffs: a failed install now stops the first run instead of carrying on unencrypted; profiles already saved unencrypted on a Windows or Mac machine stop opening once encryption is installed, and they are handled as you chose in SQLC-OLD-VAULTS (item 6); Linux on ARM is still unsupported.
   - Analogy: fitting the lock to the back door, and making the door refuse to close without it.
2. **SESSION-AUTH-DIFF** (SESSION-REENTRY Task 2; execution gate for that task only; ask-first `core/auth.py`).
   - Question: "After the app restarts, your sign-in token still looks valid but the profile is closed, so every page shows an error instead of the unlock screen. One status code in the sign-in code (`core/auth.py`, 403 → 401) would send you straight to the unlock screen. Change it?"
   - Options: "Change to 401" (a restart sends you to the unlock screen; the only change is that number). "Leave it as 403" (after a restart you see errors until the token expires, at most 60 minutes, then the unlock screen).
   - Tradeoffs: 401 means "sign in again", which is true here; any other client relying on 403 would see 401 (none in this repo).
   - Analogy: the door telling you "use your key" instead of "access denied".
3. **CPU-MODEL-FINAL** (after QWEN3-4B-TIER; open, not asked; no recommendation until the measurement exists).
   - Question: "On laptops without a graphics card, which local model should be the default for good? Here are the measured speed, safety-check and answer numbers for Phi-4-mini (today's default) and Qwen3-4B on the same machine."
   - Options: "Keep Phi-4-mini" (no change; 32 GB laptops still get BioMistral-7B, as today). "Phi-4-mini on every laptop" (32 GB laptops without a graphics card also get Phi-4-mini instead of BioMistral-7B). "Switch to Qwen3-4B" (the newer model becomes the default; it only works while 'thinking' stays off wherever it is used). "Measure again" (no change now; run the comparison on a stakeholder-class laptop first).
   - Tradeoffs: Phi-4-mini is the one already measured with the safety judge; Qwen3-4B may answer better but depends on the thinking switch; BioMistral-7B is medical-tuned but has a small 4K window; a computer with a graphics card that was never set up to use it also gets Phi-4-mini first.
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

6. **SQLC-OLD-VAULTS** (SQLCIPHER-WHEEL; execution gate; ask now, before the build).
   - Question: "Once encryption is switched on for Windows and Mac, profiles that were saved there without encryption (your Windows demo box probably has some) can no longer be opened as they are. What should happen to them?"
   - Options: "Convert them on next login" (on the next correct password the app makes an encrypted copy, checks it, and only then replaces the old file; a backup stays until the check passes). "Block with a clear message" (the app says the profile was saved unencrypted; the file stays on disk untouched, but the app cannot open it until it is converted). "Decide after seeing the diff" (build the clear message now, ask about conversion with the draft).
   - Tradeoffs: converting is more code in the encryption path and needs its own failure tests; blocking is safer code, but the profile's data cannot be reached in the app until a later conversion, unless it was exported before the upgrade.
   - Analogy: moving the contents of an unlocked drawer into the new safe, or putting a sign on the drawer saying "move these yourself".
7. **OCR-DEFAULT-ON** (RAPIDOCR-BUNDLE Task 6; execution gate for Task 6 only; **redrafted 2026-10-30** by the Opus planner with RAPIDOCR-RESEARCH's numbers (#323) and OCR-SIZE's answer, [delta 2026-10-30](#delta-2026-10-30-to-rapidocr-bundle-plan-from-rapidocr-research-323); can be asked now; no recommendation: the planner does not decide it).
   - Question: "Scanned lab pages can now be read by a reader that comes with the app (RapidOCR; the 271 MB you accepted). It reads on this computer only and needs no internet. Today the app reads scans only on computers where the setup script finds Tesseract; everywhere else reading is switched off for the whole app, and the Settings switch cannot turn it on. Should reading be on where the new reader is installed? On 10 made-up test lab pages it found 117 of 140 values (84%). Rows it could not read are left out, not guessed. One value it found was wrong (Chloride 98 read as 86, which moves an in-range result below range), and the reader was fully sure of it. Every value read from a scan starts unverified, like every imported value, and is listed under Review values for you to check. With safety mode on, unchecked values are not explained; with it off, the Interpret page can explain a value you have not checked yet, as it can today for text PDFs. Reading takes about 3 seconds per page, plus 3 to 5 seconds for the first page after the app starts, and up to about 600 MB of memory while it reads. The old Tesseract reader was not measured, so we cannot say which is more accurate."
   - Options: "On when reader installed" (the setup script switches reading on whenever the new reader or Tesseract is there, as it does for Tesseract today; each patient can still switch it off in Settings, where it starts on). "On, patient opts in" (reading is allowed, but the Settings switch starts off for new profiles, so scans wait until the patient turns it on; profiles that never saved their settings also start off). "Keep today's rule" (reading only where Tesseract is installed; the new reader then does the reading on those computers only).
   - Tradeoffs: on means more values to check, and some may hold reading mistakes (they still go through Review values); opt-in means a patient with scanned reports sees no values until they find the setting; today's rule leaves most Windows laptops without scan reading. With every option, a page the reader cannot read is still named in the import notice.
   - Analogy: a reading assistant who starts reading every photo you hand over, one who waits until you ask, or one who reads only for people who brought their own glasses (Tesseract).

8. **RAG-TIMEOUT-GROUNDED** (RAG-TIMEOUT-ANSWER [delta 2026-10-27](#delta-2026-10-27-to-rag-timeout-answer-the-grounded-path-rag-timeout-grounded); execution gate). Drafted 2026-10-27 by the Opus planner. **Answered 2026-10-27** by L0 AskUserQuestion: "Keep the sentence, label it" (owner-decisions row RAG-TIMEOUT-GROUNDED).
   - Question: "When the local model runs out of time (60 seconds) while writing the explanation for one lab result on the Interpret page (heading 'Lab Interpreter'), with safety mode off, what should you see? Today you see the app's own sentence, 'I was unable to fully process your question within the time limit. Please try asking a more specific question about your results.', with the amber 'Grounded faithfulness: 0%' badge. Behind the scenes, the response marks that sentence's claims as failed checks. Chat already shows the standard 'not enough verified information' message for a timeout (your OQ-1 and W4-OQ-2 answers), and with safety mode on this page already shows it too (for a value you have checked). The explanation text itself is never saved, whichever option you pick (the basic interpretation and the activity-log entry are saved as today). Related earlier answers: when you answered GC5-OL-2 (fail closed), the question noted that this page has no way to hide an answer whose checks failed and that adding one would be a separate decision; this is that decision. GC5-PFC-DIFF: when the checker itself fails, every claim is marked failed and the answer is still shown under the caution badge. EMPTY-ANS-SCOPE: an empty model answer is treated as failed; chat shows the standard 'not enough verified information' message, and this page shows the caution badge with no text. SAFE-INTERP-GROUNDED: this page already replaces an answer containing medical advice with a fixed safety message. RR500-MAP: when the explanation cannot be generated, you chose 'The explanation could not be generated right now. Please try again.' SAFETY-MODE-BEHAVIOUR: safety mode was built so that 'off' kept today's behaviour; options 2 and 3 change this page with safety mode off."
   - Options:
     - "Keep the sentence, label it": same sentence and badge on screen; the data behind the page says 'Generation timed out' instead of failed checks on a sentence the model never wrote. Chat looks the same. About 1 h.
     - "Standard message, as chat": the page shows 'There isn't enough verified information in your record to explain this yet. If the relevant document is imported but not verified, verifying it will let Asclexis explain the values it contains.' and adds a privacy-safe entry to the activity log, as safety mode on does today. The amber 'Grounded faithfulness: 0%' badge still shows above it, as it does in safety mode today. About 1.5 h.
     - "Error, try again": the page shows 'The explanation could not be generated right now. Please try again.', the same 'try again' message the page uses when the model fails outright. Today this page shows nothing at all when that request fails, so this also needs a small screen change, which the coming rebuild of the results pages must carry over. About 2.5 h.
     - "No change": today's sentence and badge stay, and this fix is dropped.
   - Tradeoffs:
     - The first option changes nothing you see. The sentence still asks you to 'ask a more specific question', but this page has no question box: you press 'Generate Interpretation' and the app writes the question.
     - Options 1 and 2 both keep the amber 'Grounded faithfulness: 0%' badge, although no check runs on the text shown. In chat you had a similar footer cleared for that reason (W4-OQ-5: "no footer claiming a check on text the patient doesn't see"). Removing the badge would be a separate screen change under either option.
     - The second option's first sentence is not strictly true for a timeout, and its second sentence suggests verifying a document, which does not help with a timeout. It is the same downside you accepted for chat in OQ-1: "its 'not enough verified information' sentence is not strictly true for a timeout".
     - The third option is the most accurate message. But if the computer was too slow once, trying again may time out again after another 60 seconds. It is the most work, and it touches a page that is about to be rebuilt.
     - The last option keeps today's sentence and the 0% badge. The data behind the page (which you do not see) keeps saying the sentence's claims 'could not be verified', about a sentence the model never wrote.
   - No recommendation. Every option leaves something imperfect on this page. The first is the smallest change and hides nothing; the second matches chat and safety mode; the third gives the most accurate message, at the most cost.
   - Analogy: the kitchen ran out of time on one dish. You can hand the diner the kitchen's own note asking them to order something more specific (option 1, as today, with the ticket relabelled 'ran out of time'), hand them the standard 'we can't serve this' card, which also suggests checking their order (option 2), tell them the dish could not be made in time and to order again (option 3), or change nothing (option 4).
   - Reviewer notes for L0 (not part of the question): option labels map to the delta's options 1-4; "close the row" for option 4 means L0 closes #317 and marks RAG-TIMEOUT-ANSWER won't-do.

**Not gates:** LEGACY-ADVICE-GATE (L0 tells the owner: stricter, never looser); AGENT-DATEONLY-TZ (L0 tells the owner the midnight tradeoff); RAPIDOCR-RESEARCH (a failed premise goes back to the owner as a new question with the numbers).

Back to: [queue](2026-10-15-build-program/queue.md) · [RUNBOOK](2026-10-15-build-program/RUNBOOK.md)
