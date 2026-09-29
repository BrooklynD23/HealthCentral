# Wave 3 · 3b — Evidence and numbers

Verdict: **0 BLOCKER · 10 MAJOR · 12 MINOR.** All 5 named conflicts are settled: 4 by measurement, and the HC-* prefix check finds no collision that needs a rename (4 substring pairs, all selector-safe). 42 of 47 numbers re-measured here agree, 5 differ (§1.2 rows 4, 28, 29, 32, 33) and 1 is incomplete (row 31). The matrix lacks rows for 9 verified findings; §3 proposes 11 rows to cover them.

- **Auditor:** Wave 3 integration auditor (b). Worked READ-ONLY on the repo. Every run happened in scratch `git archive` trees under `scratchpad/wave3/`.
- **Refs:**
  - main `40f590e`
  - A `origin/claude/asclexis-repo-audit-349pjq` `692fdf3`
  - B `origin/claude/healthcentral-agentic-research-r1n54x` `7b2ff1f`
  - A+B merge-tree `86606d0` (5 doc conflicts left in)
- **Interpreter** for the collect and gate runs: `/mnt/c/Python313/python.exe` 3.13.7 on Windows, run via WSL interop.
- **Env:** `HF_HUB_OFFLINE=1` and `PYTHONDONTWRITEBYTECODE=1`, passed with `WSLENV`. No 3.11 venv exists, so D9 is still unmet.
- **Documents audited** (sha256 prefix, read 20:45–21:00 PDT):
  - Plans: P04 `0b92ebdf64dc` · P08 `122a13878aa2` · S01 `e7f9aab192b9` · W01 `a586864057cf` · W02 `c357de07ae7f` · W03 `9254483c1733` · W04 `2a6697d12ff1` · W05 `3df33e605b46` · W06 `92cab3a9d8a0` · W07 `df76de6aa8f4` · W08 `f4fffd8f3a00` · W10 `201e4bc77887` · W11a `4a4083851895` · W11b `f041ea8250c7`
  - Capstone docs: program `e9a1e2c75604` · contract `5f1c08565c31` · matrix `2df31a36f993` · owner-decisions `b49fc565f656` · overview `1a3f73e44b3d` · claims-ledger `5ca81e6da1e3`
  - Handoff `6cdd140269e9`
  - `owner-decisions` changed during the audit, at 20:50:35 when the D8-delivery row was added. Four plans also changed at 20:48–20:49: P04, S01, W03 and W11b.
- **Two fork reports back this file.** Their summaries are folded in below, and I spot-checked the numbers I rely on:
  - `wave3/3b-fork-W01-W06.md`: 111 checks, 107 match.
  - `wave3/3b-fork-W07-S01.md`: 96 checks, 92 match.
- **Out of scope but present:** `docs/plans/2026-09-27-nightly-doc-drift-routine-spec.md` is not one of the 14 plans. It also cites `CLAUDE.md:30` and B `AGENT.md:76`.

---

## 0. Findings

### MAJOR (10)

| # | Where | Claim | Measured | Evidence |
|---|---|---|---|---|
| M1 | B `AGENT.md:76` | "1269 collected; 1269 pass in CI" | **1288 collected** on B. B `CLAUDE.md:30` (1288) is correct | `git show $B:AGENT.md \| sed -n 76p`; collect on `wave3/btree` → `1288 tests collected in 25.81s` |
| M2 | main `CLAUDE.md:30-31`, `AGENT.md:57`, `AGENT.md:64` | CI has "a real embedding model installed", so `002b` passes in CI and "fails locally" | CI installs **no** model. `ci.yml:30-48` has no model, HF or embed step. CI's `002b` pass, and this machine's, come from the **implicit HF fetch** (LOCAL-03). On 2026-09-27 at 17:05:28–33 the Windows HF cache gained snapshot `1110a243…`: 11 files, 91,578,415 bytes, `model.safetensors` 90,868,376 B. That fell inside the Wave-0 full-suite window, whose output file was written at 17:05:46 after 90.95 s. `002b` is not in that run's 4 failures. "1245 pass in CI" rests only on the `fd8984e` commit message ("CI on 7897e47 reported '1245 passed'"); the log is not in the repo | `git show main:.github/workflows/ci.yml \| sed -n 30,48p`; `ls -la --time-style=full-iso /mnt/c/Users/DangT/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/{refs,snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41}`; `find <snapshot> -type f -printf '%s\n' \| awk '{s+=$1}END{print s}'` → `91578415` |
| M3 | claims-ledger `:42` (H2); matrix `:137` (GATE-03), `:140` (GATE-06); overview `:211`; program `:287` (G-B6) | 155 vitest / 25 e2e | **Vitest 165 tests / 28 files on main.** The static count of `it(`/`test(` gives 165/28, and W-11a lists the same with `npx vitest list` (Linux). A+B has 179/31. **Playwright chromium lists 28 / 5 files** on main and 30/6 on A+B (W-11a `:218`, fork-confirmed via the `playwright.config.ts:72` exclude). "25" was a **pass** count (`TASK_LIST.md:794`: "Playwright 25 passed / 3 conditional skips") | `git grep -hE '^\s*(it\|test)(\.(each\|skip\|only\|todo)[^(]*)?\(' <ref> -- 'src/frontend/src/*.test.ts' 'src/frontend/src/*.test.tsx' \| wc -l` → main 165, A 174, B 170 |
| M4 | matrix `:91` PRIV-08; overview `:84` | "module-level dicts (REPORTED)"; status `unknown` | **gap.** 3 process-memory stores exist: `api/export.py:44` `_summary_store`, `:47` `_packet_store`, `:50` `_fhir_store`. `api/pinboards.py:13` imports `_packet_store` and `:495` writes to it. W-11b measured a 404 after restart. Nothing persists them | `git show main:src/backend/api/export.py \| grep -nE '^_[a-z_]+: dict'` |
| M5 | matrix `:89` PRIV-06 (`partial`, "REPORTED") | no PHI in logs | **contradicted.** (1) `echo=settings.debug` on the master engine (`core/database.py:46`) and the vault engine (`core/profile_database.py:308`). `debug: bool = True` (`core/config.py:28`), `config/.env.example:14` `DEBUG=true`, `dev.ps1:573` `DEBUG=true`. `hide_parameters` has 0 hits at main, A or B. Bound values reach stderr; S-01 measured this on B. (2) `modules/notification_scheduler.py:517-520` puts `medication_name` in an f-string at INFO; this is now VERIFIED. (3) `api/profiles.py:328` puts `display_name` at INFO (main = B). (2) and (3) are hidden only because root is WARN after Alembic's `fileConfig` | `git grep -c hide_parameters main $A $B -- src` → no output; sed of the lines cited |
| M6 | matrix `:71`, `:77`, `:98`; contract `:169`, `:211`; handoff `:140`, `:142`, `:144`; overview `:111`, `:130`, `:185`, `:188`; claims `:27`, `:51` | stale code citations | `rag.py:120-132` → **`:123-140`**; the contradictory lines are `:128`, `:133`, `:134`. `rag.py:322-328` → **`:323-331`** (`:322` is `try:`). The overview's 3 `core→modules` imports are actually **5**. Overview `:188` "P3" should read **P4**. `model_selector.py:438` is correct at main but becomes **`:456`** after P1 | `git show main:src/backend/modules/rag.py \| grep -n 'SYSTEM_PROMPT = \|YOUR_RESULTS:N\|REFERENCE:N'` → `123`, `128`, `133`, `134`; `git grep -nE '^\s*(from modules\|import modules)' main -- src/backend/core` → 5 hits |
| M7 | W05 `:567`, `:587`; W07 `:916`, `:1203` vs W01 `:148`, W02 `:47`, W03 `:1267`, W04 `:175`, W08 `:41`, S01 `:59` | pass-count slot rule | The plans disagree. **W-5 derives** the "N pass in CI / N−1 without" figures as START+3, and **W-7 carries them forward** as NEW. The other 6 plans forbid touching pass slots without a measured pass count. The slot's premise, a model installed in CI, is false (M2). All 8 plans edit the same 2 lines serially | `sed -n 560,590p` W05; `sed -n 908,920p` W07; `sed -n 170,180p` W04 |
| M8 | handoff `:138`, `:139`, `:143` | W-1 acceptance "drift check exits 0"; W-2 "3 new tests"; W-6 "3 tests" | **The drift check exits 1** on the A+B merge-tree: `docs/agentic/recurring-failures.md:33: missing path '/profiles/'` (A's line). It exits 0 on B alone. W-2 adds **+8** collected (fork). W-6 adds **+17** backend and **+3** vitest (4+4+1+2+1+4+1 = 17) | `cd wave3/mtree && python3 scripts/harness_drift_check.py; echo $?` → `…failed with 1 error(s).` `1` |
| M9 | program `:132` (P1 step 6); contract `:137`, `:146` (C-SAFE-1/2 Verify) | `python3 scripts/agent_eval_gate.py` returns its gate exit code | **It prints PASS and then does not exit.** In a scratch main tree on Win Py 3.13.7 with HF offline, "All 74 golden cases passed. / Agent eval gate: PASS" had printed by 20:52:45; `timeout 420` then killed it with `rc=124` (the script recorded elapsed=409s). Linux/3.11 is UNMEASURED. No plan owns this | `wave3/evalgate.out` |
| M10 | matrix scorecard `:31` (62 rows) | coverage of the requirement set | **9 verified findings have no row** (§3): SQL echo, `rl_exports` erase/ignore, dropped INFO audit lines, 0-audit interpretation routes, unencrypted Windows dev vaults, the implicit fetch during tests, external-runner payload scope, the eval-gate hang, and the latent real-master-DB hazard. `rl_exports` (F-1) and interpretations audit (W-7 OG-3) are **unowned** | §3 |

### MINOR (12)

1. **Matrix TIME-01 hides the aware datetimes.** Product code has 7 aware `datetime.now(timezone.utc)` sites in 6 files: `core/auth.py:73,144`, `core/security.py:136`, `core/token_revocation.py:51`, `api/export.py:949,1005`, `api/model_settings.py:332`. None was found writing to a naive column; that was checked by reading each site, not by any test. The ledger named only `auth.py:73`.
2. **W02 `:96-97` uses status words the matrix does not define:** "tested for labelled PHI shapes" and "documented exception, tested byte-stable". The matrix `:18-27` values are the only allowed ones.
3. **W07 `:67`, `:1319` propose LLM-02 → `enforced`.** HC-LLMB runs inside `backend-tests`, and the matrix `:20-21` definition makes a suite test `tested`. `enforced` needs a dedicated gate.
4. **W05 `:848` says `git grep -n "HC-CIT"` returns 11 hits.** It returns 2. The 11 come from `-ni "HC-CIT\|hc_cit"`. The conclusion stands (fork 1).
5. **W01 `:743`** cites `dev.bat:16`; the line is `:17`. **W01 `:64`** cites program `:180`; the line is `:181` (fork 1).
6. **W11b cites W08 `:17-22` for the model size.** The figure is at W08 `:34` and `:103` (fork 2).
7. **Unsequenced Playwright count.** W11b C3b adds `E2E-HEALTH-001` (Playwright +1), and W11a Task 11 writes the Playwright count. Neither plan mentions the other. The count moves from 28 to 29 (main) or from 30 to 31 (A+B) (fork 2).
8. **The ledger's "P04: 30 tasks" has no command.** `grep -cE '^#+ Task' P04` gives 25 headings, which contain 33 task units (fork 2).
9. **W08 `:141` file row reads "HC-EMB-001..004c".** The file also gets 004d and 004e; the +13 total still holds (fork 2).
10. **S01 `:110` "4/1271 tests collected" is a scratch archive of B with 4 collection errors.** It must never be used as a baseline.
11. **H9 depends on method.** The claims-ledger (`:49`) gives 16 refs in 6 test files, which is right by AST. `git grep` gives **18 lines in 7 files**, because it also counts the string literal in `tests/test_profile_recovery.py:344,350`. Name the method beside the number.
12. **`owner-decisions-2026-09-27.md:46` still says "size not measured".** It was measured at 11 files, 91,578,415 bytes (W08 `:103`; re-measured here).

---

## 1. Number audit

### 1.1 Named conflicts, settled

| Conflict | Settlement | Command → output |
|---|---|---|
| B `CLAUDE.md:30` 1288 vs B `AGENT.md:76` 1269 | **1288 is right; `AGENT.md:76` is stale.** P1's conflict resolution (plan 01) writes one measured merged figure into both. The merge-tree collects 1291 | `wave3/btree`: `1288 tests collected in 25.81s`; `wave3/mtree`: `1291 tests collected in 15.60s` |
| Handoff/CLAUDE "1245 pass in CI" vs W-8 "no model step in CI" | **Both hold; the explanation is wrong.** The pass record is REPORTED (commit message `fd8984e`, CI run on `7897e47`, 2026-08-03). "Installed" is false: CI fetches the model from HF at test time, which is the LOCAL-03 gap running in CI. The handoff itself does not say "1245 pass in CI" (`grep` over `audit/2026-09-25/*.md` → 0 hits); the sentence lives in `CLAUDE.md:31` and `AGENT.md:57` | `git show fd8984e --format=%b`; `git show main:.github/workflows/ci.yml \| sed -n 30,48p` |
| "155 vitest / 25 Playwright" vs W-11a 165/28 (main), 179/30 (A+B) | **W-11a is right.** The static count agrees with its listing: 165/28 on main, 179/31 on A+B. 25 was a pass count | M3 |
| PRIV-08 `unknown` vs W-11b's measured 404 | **`gap`.** Static evidence (M4) plus W-11b's measurement | M4 |
| HC-* prefix collisions | **No ID is defined by two plans, and no new ID exists at main, A or B.** 4 prefixes are substrings of others; every selector the plans write is safe (§1.4) | §1.4 |

### 1.2 Re-measured sample (47 numbers; 43 agree)

| # | Number (where asserted) | Ref / env | Command | Measured | Verdict |
|---|---|---|---|---|---|
| 1 | 1245 collected (program `:21`; matrix GATE-02; contract `:347`) | main archive, Win Py 3.13.7 | `pytest tests/ --collect-only -q -p no:cacheprovider` | 1245 | ✓ |
| 2 | 1248 collected (program `:22`) | A archive | same | 1248 | ✓ |
| 3 | 1288 collected (program `:23`; B `CLAUDE.md:30`) | B archive | same | 1288 | ✓ |
| 4 | 1269 collected (B `AGENT.md:76`) | B | same | 1288 | **✗ M1** |
| 5 | 1291 merge-tree (program `:24`) | `86606d0` | same | 1291 | ✓ |
| 6 | A 5 / B 19 ahead, 0 behind (handoff `:64-65`) | origin | `git rev-list --count` | 5/19, 0/0 | ✓ |
| 7 | 5 conflict files (handoff `:66`) | A onto B | `git merge-tree --write-tree --name-only $B $A` | the 5 named files | ✓ |
| 8 | A 21 files, B 120 files (program `:118`) | main... | `git diff --name-only main...<ref> \| wc -l` | 21 / 120 | ✓ |
| 9 | 74 golden cases (matrix SAFE-03, GATE-05) | main | `git ls-tree` count; gate output "total cases: 74" | 74 / 74 | ✓ |
| 10 | 6 CI jobs (claims H3) | main | `grep -nE '^  [a-z0-9_-]+:' ci.yml` | 6 (docs-lint, backend, frontend, security, agent-evals, e2e) | ✓ |
| 11 | `\|\| true` at `ci.yml:92,95` (GATE-04) | main | `grep -n '\|\| true'` | 92, 95 | ✓ |
| 12 | `security_gate.py:49-51,76-78` fail open | main | `sed -n 45,52p;74,79p` | `return []` at 51, 78 | ✓ |
| 13 | 101 product `datetime.utcnow` lines / 30 files (TIME-01, C-TIME-1, program `:216`) | main | `git grep -nE 'datetime\.utcnow' main -- 'src/backend/*.py' ':!src/backend/tests' \| wc -l` | 101 / 30 | ✓ |
| 14 | 109 references by AST | main | `ast.walk` over product `.py` | 109 / 30 files | ✓ |
| 15 | 16 refs / 6 test files (claims H9) | main | AST over `tests/` | 16 / 6 (grep: 18 / 7) | ✓ (MINOR 11) |
| 16 | master 2 / profile 12 revisions (MIG-01, H8) | main, B | `git ls-tree` count | 2 / 12 at both | ✓ |
| 17 | profile routes 13, audited 9; unaudited at `:241,:416,:477,:943` (AUD-02, C-AUDIT-1) | main | AST over routes + audit-call regex | 13 / 9; decorators at 241, 416, 477, 943 | ✓ |
| 18 | `require_profile_access` used 5× in `api/profiles.py` (ISO-02) | main | `grep -c` = 6 (1 import) | 5 | ✓ |
| 19 | documents 13, observations 6 routes (AUD-01) | main | `grep -cE '^@router\.'` | 13 / 6 | ✓ |
| 20 | `api/interpretations.py` 7 routes, 0 audit (W07 F-3) | main | `grep -cE '^@router\.'`; `grep -ci audit` | 7 / 0 | ✓ |
| 21 | network-import allow-list: 7 files (C-LOCAL-1 `:38`) | main; B | contract `:38` grep | 7 at main; **8 at B** (`scripts/download_models.py:53` `huggingface_hub`) | ✓ (becomes 8 after P1) |
| 22 | 239/355 commits by "Claude"; 326 non-merge (claims H1) | main | `git log --format=%an` | 239 / 355 / 326 | ✓ |
| 23 | 33 user-level agents (claims H5) | `~/.claude/agents` | `ls *.md \| wc -l` | 33 | ✓ |
| 24 | 14 check functions (GATE-01) | main | `grep -cE '^def (check\|_check)' scripts/docs_lint.py` | 14 | ✓ |
| 25 | scorecard 62 rows: 4/18/4/16/13/3/2/2 (matrix `:31`) | working tree | regex over the Status cells | 62 · 4/18/4/16/13/3/2/2 | ✓ |
| 26 | handoff §4 tasks / checkbox steps per plan (`:112-119`) | working tree | `grep -cE '^#+ Task [0-9]+'`; `grep -cE '^\s*- \[ \]'` | 8/43, 7/37, 0/11, 16/54, 15/61, 5/37, 3/14, 7/33 | ✓ |
| 27 | `model_selector.py:438` (LLM-02 and others) | main; B | `git grep -nE 'import llama_cpp\|from llama_cpp'` | main `:438`; **B `:456`** | ✓ now, stale after P1 |
| 28 | `rag.py:120-132` prompt (SAFE-08, C-SAFE-5, handoff W-5) | main | `grep -n 'SYSTEM_PROMPT = '` | `:123-140` | **✗ M6** |
| 29 | `rag.py:322-328` legacy select (SAFE-02, handoff W-3) | main | `sed -n 318,335p` | `:323-331` | **✗ M6** (off by one to three) |
| 30 | 0.6 threshold at `rag.py:862` (SAFE-07) | main | `grep -n '< 0.6'` | 862 | ✓ |
| 31 | faithfulness is the trigger (SAFE-04, C-SAFE-2) | main | `grep -n 'errors.append'` | **5 triggers**: `:826`, `:833`, `:838`, `:858`, `:863`; `is_valid` at `:869` | partial ✓ (row text incomplete) |
| 32 | 3 `core→modules` imports (overview `:185`) | main, B | `git grep -nE '^\s*(from modules\|import modules)'` | **5** | **✗ M6** |
| 33 | vitest 155 (H2, GATE-03) | main | static `it`/`test` count | **165 / 28 files** | **✗ M3** |
| 34 | vitest 165/28 main, 179/31 A+B (W11a `:217`) | main, A, B | static count | 165; A +9, B +5 → 179; files 28 +2 +1 = 31 | ✓ |
| 35 | medication name at INFO `≈:517-520` (PRIV-06, C-REDACT-3, "REPORTED") | main | `sed -n 512,522p` | `logger.info` at 517; name at 519 | ✓ (now VERIFIED) |
| 36 | audit echo `core/audit.py:254-261` (AUD-04) | main; B | `grep -n logger.info` | main 254; B 257 | ✓ |
| 37 | master DB unencrypted `core/config.py:180-184` (AUD-04) | main | `sed -n 178,185p` | `database_url` at 181-185 | ✓ |
| 38 | `user_verified = True` at exactly 2 sites (C-VERIFY-1) | main | `git grep -nE "user_verified\s*=\s*True"` | `documents.py:1274`, `observations.py:458` | ✓ |
| 39 | `external_runner.py:172` (break-glass) and `:201` (dev bypass) | main (= B, fork) | `sed -n 170,173p;199,203p` | 172, 201 | ✓ |
| 40 | `conftest.py:57` sets `DATABASE_ENCRYPTION_REQUIRED=false` (KEY-02) | main | `sed -n 57p` | ✓ | ✓ |
| 41 | `.gitignore:44` `.claude/*` (GATE-09) | main, A, B | `grep -n '\.claude'` | 44 (+ `:45 !.claude/skills/`); 0 files under `.claude/agents/` at every ref | ✓ |
| 42 | export dicts in `api/export.py` (PRIV-08) | main | M4 | 3 dicts | ✓ (status changes) |
| 43 | `ollama_base_url` pins the factory (LOCAL-02 cites `factory.py:51`) | main | `sed -n 45,55p factory.py`; `git grep ollama_base_url` | `OllamaProvider(model=model)`; the setting is read only in `api/model_settings.py:768,806,831` | ✓ (the pin is the provider default, not the setting) |
| 44 | embedding model 11 files, 91,578,415 B (W08 `:34`, `:103`) | Windows HF cache | `find … -type f -printf '%s\n'` sum | 11 / 91,578,415 | ✓ |
| 45 | `test_care_tasks.py:809,825` hard-code head `012_pinboards` (W11b F-4) | main | `sed -n 807,826p` | both `== "012_pinboards"` | ✓ |
| 46 | no product FileHandler; `log_file_path` only `mkdir`ed; `log_level` / `audit_log_enabled` never read (P08, AUD-04) | main | `git grep 'settings\.log_level\|settings\.audit_log_enabled\|log_file_path'` | only `config.py:125` and `database.py:87` (mkdir) | ✓ |
| 47 | `data-privacy.md` lines 33 / 47 / 144 / 173 / 196 (P08, S01, W10) | main; A | `grep -n` | main 33 / 47 / 144 / 173 / **196**; A has 196 → **213** | ✓ |

**Measured here, not asserted anywhere before:**
- The agent eval gate hang (M9).
- The A+B drift-check exit 1 (M8).
- `src/backend/data/` is **absent** in the checkout after the Wave-0 full run (`ls` → no such directory). The ledger's "did my Wave-0 run write to `data/asclexis.db`?" is therefore answered **no persisted write**.
- `pip download sqlcipher3-binary --only-binary=:all:` with Win Py 3.13.7 → `ERROR: No matching distribution found for sqlcipher3-binary`. That is a network query to PyPI; nothing was installed. It holds for cp313 `win_amd64` only; other Windows Python versions are UNMEASURED.

**Not re-measurable read-only, left as stated:**
- W04's faithfulness probe values (0.831 / 0.814).
- W05's "167 passed" context.
- W-11b's 404-after-restart run.
- S-01's stderr probe contents. The config lines it relies on are verified above.
- Any pass count in a 3.11 venv (D9 unbuilt).

### 1.3 Per-plan test-count arithmetic (forks; spot-checked W06 and W07)

| Plan | Delta claimed | Tests written | OK |
|---|---|---|---|
| W01 | +7 (+8 with Task 9) | 7 functions; 008 in Task 9 | ✓ |
| W02 | N0+2, then N0+8 | 002 ×2; 001 ×3 + real-pdf + xfail + 003 | ✓ |
| W03 | backend +5; vitest +8 (+6 if Task 6 vetoed) | FE-001 ×3, FE-002 ×3, FE-003 ×2 | ✓ |
| W04 | +5 | HC-LEG-001…005 | ✓ |
| W05 | +3 | 3 functions | ✓ |
| W06 | +17 backend, +3 vitest | 4+4+1+2+1+4+1 (re-added here) | ✓ |
| W07 | +16 then +23 | LLMB 001 + 001b ×4 + 001c + 002 = 7; INT 011, 012, 013 ×3, 014–017 = 9; routes 001–003, 004 ×3, 005 = 7 (re-counted here from W07 `:310-1053`) | ✓ |
| W08 | +13 (+14 with Task 7) | 001, 002, 003, 004a–e, 005, 006a–c, 007 | ✓ |
| W11a | PR-1 15 (+6/+7 PAUD) · PR-2 7 · PR-3 5 | per fork 2 | ✓ |
| W11b | C1 +16 · C3a +5 · C3b +4 (+1 Playwright, unsequenced) | per fork 2 | ✓ (MINOR 7) |
| S01 | +4 (+3 without S1-B) | HC-SQLECHO-001/002/004 plus 1 | ✓ |
| P04, P08, W10 | +0 | docs only | ✓ |

**Handoff §5 figures superseded by these:** W-2 "3 tests" → +8; W-6 "3 tests" → +17/+3; W-1 "(3) drift exits 0" → false on the merged tree (M8).

### 1.4 Test-ID registry (all 14 plans + audit plans 01–08 + main/A/B)

The 41 existing prefixes at main ∪ A ∪ B were extracted with `git grep -hoiE 'HC[-_][A-Za-z0-9]+([-_][A-Za-z]+)*[-_][0-9]{2,4}' <ref> -- src/ scripts/` and are stored in `wave3/prefix_*.txt`.

| Prefix | Defined by | Exact hits at main/A/B | Substring relation | Selector safe? |
|---|---|---|---|---|
| HC-AGENTS | W01 | 0 | — | `-k hc_agents_` ✓ |
| HC-EXPR | W02 (W10 refs) | 0 | — | `-k "hc_expr_` ✓ |
| HC-VER / HC-VER-FE | W03 (W10 refs) | 0 | `HC-VER` ⊂ `HC-VERIFY` (B `test_verify_model_repos.py`) | `-k hc_ver_` ✓ (does not match `hc_verify_`) |
| HC-LEG | W04 | 0 | — | ✓ |
| HC-CIT | W05 | 0 (`HC-CIT-0`) | `HC-CIT` ⊂ `HC-CITE` (main `test_citation_source_links.py`) | W05 selects by file ✓; W05 `:242` warns; `-k hc_cit` is unsafe |
| HC-EXT | W06 (W10 refs) | 0 | `HC-EXT` ⊂ `HC-EXTR` (W11b) | `-k hc_ext_` ✓; bare `grep HC-EXT` ✗ |
| HC-LLMB | W07 (W06 refs `:173`) | 0 | — | ✓ |
| HC-INT | W07 | 0 (`HC_INT_0`) | `HC-INT` ⊂ `HC_INTERP_*` (5 tests, `test_interpret_history_units.py`) | W07 uses `-k "HC_INT_0"` ✓; `:98` and `:210` warn |
| HC-EMB | W08 (W11b refs 002) | 0 | — | `-k test_hc_emb_` ✓ |
| HC-PGUARD, HC-PAUD, HC-KEYCT, HC-MIGHEAD | W11a | 0 | `paud` ⊂ "pipaudit" (W11a warns) | `-k hc_paud_` ✓ |
| HC-EXPA, HC-EXTR, HC-OBSV | W11b | 0 | `HC-OBS` (existing `HC-OBS-AUDIT`) ⊂ `HC-OBSV` | `-k hc_obsv` ✓ (does not match `hc_obs_audit`) |
| HC-SQLECHO | S01 | 0 | — | `-k sqlecho` ✓ |
| HC-NSW, HC-TIME, HC-FKA, HC-RESET | plans 02, 05, 06, 07 | 0 | — | ✓ |

**Existing IDs referenced and not redefined:** HC-AUD-007 and HC-AUD-010 (S01, W06); HC-PKT-004…016 (W02, W11b); HC-FHIR-102…104 (W11b); HC-BKUP-035, -042 (W10); HC-RESET-010 (plan 07, referenced by W11b).
**Not an ID collision:** W10's `HC-BKUP-999` is a deliberate non-existent probe in its `rc_check.py` harness (W10 `:407`).

---

## 2. Matrix and contract deltas (replacement text)

Rules for everything proposed below:
- Status values are the matrix's own (`:18-27`).
- A plan never makes a row `implemented`. Only the Status column changes today, and it changes only where evidence changed. The value a plan would earn *after* it merges is given under "after merge".
- **Proposed new column:** `Planned by` (plan path). Paths are relative to `docs/plans/` unless shown.

### 2.1 Matrix rows touched

```
| LOCAL-01 | No network calls in product code paths | `CLAUDE.md:59`; PRD `:7` | Network-capable imports in 7 product files @main, 8 @B (+ `scripts/download_models.py:53` `huggingface_hub`); `httpx` only in `core/llm/ollama_provider.py` and `core/external_runner.py`; implicit HF fetch at `modules/embeddings.py:56` observed 2026-09-27 (LOCAL-03) | agent loop only: `tests/agent/test_s4_phi_gate.py::test_s4_2_offline_loop_completes`. It FAILED in the Wave-0 run (Win Py 3.13.7 @main, 2026-09-27); cause UNMEASURED | none (no import ban) | **partial** | — | 2026-09-27-W08-bundled-embedding-model.md; 2026-09-27-W06-external-runner-hardening.md; 2026-09-27-W07-tiered-interpretation-via-modelrunner.md (HC-LLMB: `llama_cpp` only) |
| LOCAL-02 | Ollama is localhost-only | `CLAUDE.md:59` | `_assert_localhost` (`core/llm/ollama_provider.py:34-54`, called `:73`; `api/model_settings.py:799-808`). The factory builds `OllamaProvider(model=model)` (`core/llm/factory.py:51`) without `settings.ollama_base_url` (`core/config.py:110`), which only `api/model_settings.py:768,806,831` read. The comment at `core/config.py:109` claims startup rejection, and `validate_startup` has none | `tests/test_llm_provider_layer.py::TestOllamaProvider::test_refuses_non_local_url`, `::test_accepts_localhost` (direct-call) | pytest only | **tested** | P04 OG-3 (base-URL wiring) | 2026-09-27-P04-doc-drift-sweep-amendment.md (Task N7: comment) |
| LOCAL-03 | Model fetches happen only through user-triggered downloads | `00-original-goal.md`; owner D8 "bundle" + D8-delivery "script + offline load" (`owner-decisions-2026-09-27.md:26`) | `SentenceTransformer(self.config.model_name)` at `modules/embeddings.py:56` @main, no offline or local path. **Observed 2026-09-27:** Windows HF cache `refs/main` → `1110a243…` at 17:05:28 -0700, 11 files / 91,578,415 B, inside the Wave-0 suite window (output 17:05:46). CI `backend-tests` (`ci.yml:30-48` @main) has no model step, so CI's `002b` pass depends on the same fetch | none | none | **gap** (demonstrated) | W-8 Q-FC, Q-HASH, Q-OFFLINE open | 2026-09-27-W08-bundled-embedding-model.md |
| LOCAL-04 | The opt-in external LLM is off by default and redacted | `skills/asclexis-guardrails`; `CLAUDE.md:60`; owner D12 (keep, harden) | `use_external_api` default False (`models/model_settings.py:78-81`); strict redaction (`core/external_runner.py:166-236`); the runner receives the **whole composed prompt**: question, retrieved chunks, history, memory (`modules/rag.py:1256-1268` @main) | `tests/test_redaction.py::TestExternalRunnerIntegration`; `tests/test_config_validation.py` | pytest only | **partial**: dev bypass `core/external_runner.py:201` (`if redaction_enabled:`); production break-glass `:172` (main = B) | D12 decided; W-6 Q1–Q4 open | 2026-09-27-W06-external-runner-hardening.md (code); 2026-09-27-W10-governance-invariant-amendments.md (CLAUDE.md exception) |
| LLM-01 | Live local inference goes through `ModelRunner`; the opt-in `ExternalModelRunner` (`core/external_runner.py:95`) is an owner-approved exception (D12), effective when W-10 names it in CLAUDE.md | `CLAUDE.md:25`; D12 | `modules/rag.py:1267-1291` → `core/model_runner.py:85-90` → `core/llm/factory.py` | provider-layer tests | pytest only | **tested** | — | 2026-09-27-W10-governance-invariant-amendments.md; 2026-09-27-W06-external-runner-hardening.md |
| LLM-02 | No `llama_cpp` import in feature code | `CLAUDE.md:25`; D7 (route via ModelRunner) | dormant `from llama_cpp import Llama` at `modules/model_selector.py:438` @main (`:456` @B, i.e. after P1), reachable only via `interpret_with_model` (`modules/interpret.py:877`, 0 callers) | none | none | **partial** (after W-7 merge: `tested`; HC-LLMB runs inside `backend-tests`, not a dedicated gate) | — (D7 decided) | 2026-09-27-W07-tiered-interpretation-via-modelrunner.md |
| LLM-03 | The boundary is checked automatically | C-LLM-2 | none; ruff selects F, I, W and is not run in CI | — | none | **gap** (after W-7: `partial`, `llama_cpp` only; HTTP clients unchecked) | — | 2026-09-27-W07-…md; 2026-09-27-W11a-test-and-gate-hardening.md (ruff in CI) |
| SAFE-02 | Downstream consumers use verified data | `docs/architecture/pipelines.md:53-56`; PRD `:50`; D4 (trends label, legacy RAG verified-only) | Verified-only: agent tools, FHIR, visit-prep, pinboards, medications. **Not:** trends (`api/observations.py:529-535`); legacy RAG select `modules/rag.py:323-331` (no `user_verified` filter; `_get_observation_chunks` swallows errors `:450-451`); `api/export.py:128-150` `_fetch_observations` → CSV/JSON and doctor summary (text built inline `:551-604`) | agent golden `abstain-unverified-*`; `test_hc_fhir_031` | `agent-evals` (agent path only) | **partial** | exports with unverified rows are **not covered by D4** (owner item; W-2 fact, P04 OG-2) | 2026-09-27-W03-verified-only-rag-and-trend-labels.md; 2026-09-27-W10-…md (data-privacy D4 wording); 2026-09-27-P04-…md (pipelines.md N1) |
| SAFE-04 | Legacy RAG path is validated and gated; `is_valid=False` abstains | `CLAUDE.md:62`; `AGENT.md` flow 2; G-B5 | `validate_response` `modules/rag.py:793-872` raises 5 triggers (`:826` bad citation IDs, `:833` report facts missing citations, `:838` prohibited advice, `:858` unverified claims, `:863` faithfulness < 0.6 at `:862`); `is_valid` `:869`; the answer is still served (`api/assistant.py:772-811`); the path runs on any agent exception (`:743-755`) | `tests/test_biomarker_assistant.py` and others | **no CI eval gate** | **partial**: low-validity answers reach the patient | G-B5 decided; W-4 OQ-1 (template) blocks Task 2; abstention rate UNMEASURED | 2026-09-27-W04-legacy-abstain-and-eval-gate.md |
| SAFE-08 | One citation-marker vocabulary | `CLAUDE.md:62`; D11 (docs match code) | validator `[cite:N]` (`modules/rag.py:819`); `SYSTEM_PROMPT` `:123-140` instructs `[cite:N]` (`:126`) and also `[YOUR_RESULTS:N]`/`[REFERENCE:N]` (`:128`, `:133`, `:134`) | — | none | **partial** | W-10 Q1 (CLAUDE.md:62 hunk C-3); if unsigned, `:62` stays an owner item | 2026-09-27-W05-citation-marker-prompt.md; 2026-09-27-W10-…md; 2026-09-27-P04-…md (N8) |
| PRIV-04 | Every non-backup export is redacted, except the named D3 exceptions | `data-privacy.md:173-174`; `CLAUDE.md:60`; D3 | no `RedactionEngine` in CSV/JSON (`api/export.py:904,960` → `modules/export.py:223,267`), doctor summary (`api/export.py:379,482` → `modules/export.py:82,290,358`; text built inline `api/export.py:551-604`) or `/export/questions` (`api/export.py:607`) | none | none | **contradicted** (after W-10 + W-2: doctor summary `tested`, CSV/JSON a documented exception; `/export/questions` still open) | D3 decided; W-2 O-2 (date format) blocks Task 3; O-3, O-4 | 2026-09-27-W02-doctor-summary-redaction.md; 2026-09-27-W10-…md |
| PRIV-06 | No PHI in logs or audit rows | `hipaa-controls.md:47-53,71`; `data-privacy.md:47` | UUID-only audit helpers (`core/audit.py`). **Violations:** `echo=settings.debug` on master (`core/database.py:46`) and vault (`core/profile_database.py:308`) with `debug=True` default (`core/config.py:28`, `config/.env.example:14`, `dev.ps1:573`); no `hide_parameters` anywhere; `medication_name` f-string at INFO (`modules/notification_scheduler.py:517-520`; module unwired); `display_name` at INFO (`api/profiles.py:328`, main = B). The last two are masked only by root WARN after Alembic `fileConfig` | `tests/test_audit_phi_minimization.py` (HC-AUD-001…010b; caplog on `core.audit` only) | pytest only | **contradicted** (bound values echoed to stderr in the default dev config; measured by S-01) | S1-A / S1-B (S-01); `profiles.py:328` unowned → propose S-01 addendum (ask-first) | 2026-09-27-S01-sql-echo-phi-leak.md; audit plan 02 (medication name) |
| PRIV-08 | Export artifacts survive a restart | audit §11 P1-3 | process-memory dicts `api/export.py:44,47,50` (`_summary_store`, `_packet_store`, `_fhir_store`); `api/pinboards.py:13,495` also writes `_packet_store` | — | — | **gap** (W-11b measured 404 after restart) | S-C1-1 (G-C1 go) | 2026-09-27-W11b-roadmap-items-gc1-gc4.md |
| AUD-02 | Profile routes are audited | `CLAUDE.md:61` | 9/13 (re-measured). Missing: `GET /` (`api/profiles.py:241`), `GET /me` (`:416`), `POST /test/reset` (`:477`), `GET /{profile_id}` (`:943`) | — | none | **partial** | W-11a OG-1 (edits to `api/profiles.py`) | 2026-09-27-W11a-test-and-gate-hardening.md |
| AUD-03 | Audit retention policy | audit §21 Q6; D10 (HIPAA-aligned design posture) | none; retention unbounded; the 2026-07-27 purge-on-erase decision (`data-privacy.md:144-156`, rejection sentence `:150-153`) conflicts with a 6-year hold | — | — | **owner-gated** (brief 4 unsigned; Q4b) | yes | 2026-09-27-P08-gated-packet-hipaa-aligned-amendment.md |
| AUD-04 | Audit data is protected at rest | `hipaa-controls.md:47-53`; `data-privacy.md:33` | master DB unencrypted (`core/config.py:180-185` @main, `:179-184` @B); `core/audit.py:254-261` @main (`:257-264` @B) echoes each row at INFO, but after startup root is WARN (`alembic.ini:45-47,60-62`; `fileConfig` at `migrations/master/env.py:38`, `migrations/profile/env.py:53`), so the echo is dropped; no product `FileHandler`; `log_file_path` only `mkdir`ed (`core/database.py:87`); `log_level` / `audit_log_enabled` (`core/config.py:124,126`) never read; profile-scoped backups carry a plaintext master copy with this profile's audit rows (`scripts/backup.py:203-205,243-290`) | — | — | **partial** (rows minimized; stores plaintext; operator log sink absent) | brief 4; W-11b O-C3-4 | 2026-09-27-P08-…md; 2026-09-27-W11b-…md (C3b / F-2) |
| ISO-02 | Cross-profile access is refused over HTTP | `CLAUDE.md` §4 | `require_profile_access` (`core/auth.py:251-289`), used 5× in `api/profiles.py`; direct-call status assertions also in HC-PKT-014/015 and HC-FHIR-103/104 (W-11b F-6) | none over HTTP for profile guards | none | **gap** | — | 2026-09-27-W11a-…md (HC-PGUARD, 15 tests) |
| KEY-02 | On-disk ciphertext is proven by tests | KEY-01 | — | the suite sets `DATABASE_ENCRYPTION_REQUIRED=false` (`tests/conftest.py:57`); without `sqlcipher3` (Win Py 3.13.7: `ModuleNotFoundError`) the Wave-0 run (1241 passed) used plaintext vaults | none | **gap** | W-11a OG-2 (encryption, ask-first) | 2026-09-27-W11a-…md (HC-KEYCT, 7 tests) |
| MIG-02 | One head per chain is asserted | C-MIG-2 | — ; `tests/test_care_tasks.py:809,825` hard-code `012_pinboards` and break on migration 013 (P6) and 014 (W-11b) | — | — | **gap** | — | 2026-09-27-W11a-…md (HC-MIGHEAD, 5 tests); audit plan 06 must update `test_care_tasks.py` |
| GATE-02 | Backend suite; measured baseline | `CLAUDE.md` §4; `AGENT.md` DoD | `scripts/run-backend-tests.sh` | CI `backend-tests` | **tested**. Collected on 2026-09-27 (Win Py 3.13.7): main 1245 · A 1248 · B 1288 · merge-tree 1291. Pass: main 1241 passed / 4 failed (`test_s4_2_offline_loop_completes`, `test_hc_bkup_039`, `_039b`, `test_docs_index_check_passes_on_real_repo`), with unencrypted vaults and `002b` passing only through the implicit HF fetch. CI "1245 passed" (`7897e47`, 2026-08-03) is REPORTED via `fd8984e`. No 3.11 run (D9) | — | 2026-09-27-W08-…md (baseline wording) |
| GATE-03 | Frontend type-check and unit tests | `AGENT.md` DoD | `tsc --noEmit`, `vitest run` | CI `frontend-tests` | **partial**: no `npm run build`, no eslint in CI. Vitest **165 tests / 28 files** listed @main (179 / 31 A+B; W-11a listing, static count agrees) | — | 2026-09-27-W11a-…md (G-B4 build/eslint, G-B6 counts) |
| GATE-05 | Agent behavioural eval gate | `skills/asclexis-evals` | `scripts/agent_eval_gate.py`, 74 cases; docstring `:6-8` still calls CI "future" (CI job at `ci.yml:112`) | CI `agent-evals` | **tested** (agent path only). The script prints PASS and did not exit within 420 s on Win Py 3.13.7 (2026-09-27, `rc=124`); Linux UNMEASURED | — | 2026-09-27-W04-…md (legacy gate, docstring); hang unowned → propose W-11a |
| GATE-06 | E2E critical flows | `AGENT.md` | Playwright chromium; `HC_E2E_CHROMIUM_PATH` locally | CI `e2e-tests` | **partial**: **28 tests / 5 files** listed @main (30 / 6 A+B); "25" was a pass count (`TASK_LIST.md:794`); not run | — | 2026-09-27-W11a-…md (G-B6); W-11b C3b adds 1 (sequence it) |
| GATE-07 | Lint, type and coverage gates | audit §13 | ruff/black/mypy/eslint configured, not in CI; ruff `check .` → 555 findings @main (561 @B, W-11a; 555 re-measured by fork 2) | none | **gap** | W-11a Q-RUFF, Q-COV | 2026-09-27-W11a-…md |
| GATE-09 | Agent/hook harness claims match committed artifacts | `docs/agentic/harness.md:25-28`; D1 (A, all 5 agents) | `.claude/agents/` absent at main/A/B, and `git log --all -- .claude/agents` is empty; `.gitignore:44` `.claude/*` (`:45 !.claude/skills/`); `harness_drift_check.py` (B) exits 0 on B and **1 on the A+B merge-tree** (`recurring-failures.md:33` `/profiles/`) | none on main | **contradicted** | D1 decided; W-1 OG-1…OG-5 open | 2026-09-27-W01-harness-agents-branch-a.md; P1 (drift-check fix) |
| TIME-01 | Timestamps come only from `core.time.utcnow` (naive UTC) | `CLAUDE.md:57` | helper `core/time.py:9-11`; **101 product lines / 109 AST refs / 30 files** call `datetime.utcnow`; plus **7 aware** `datetime.now(timezone.utc)` sites in 6 files (`core/auth.py:73,144`; `core/security.py:136`; `core/token_revocation.py:51`; `api/export.py:949,1005`; `api/model_settings.py:332`) | `test_hc_recov_025` | none | **gap** (systemic) | aware sites in `core/auth.py` / `core/security.py` are ask-first | audit plan 05 (utcnow only); aware sites unowned (see TIME-03) |
| GATED-06 | `.claude/agents/` + hooks | **D1 decided 2026-09-27: A, all 5 agents** (hooks not licensed) | absent at every level | — | W-1 plan |
```

### 2.2 Contract bullets (replacement text)

**C-LOCAL-1:**
- **Verify:** "… That is **7 files at main, 8 after P1** (B adds `src/backend/scripts/download_models.py:53` `huggingface_hub`)."
- **Status today:** "partial. `modules/embeddings.py:56` fetches from Hugging Face implicitly. Observed 2026-09-27 17:05 PDT during a local full-suite run (11 files, 91,578,415 B), and relied on by CI (`ci.yml:30-48` has no model step) (matrix LOCAL-03)."
- **Planned by:** W-8, W-6.

**C-LOCAL-2:**
- **Class:** "PROPOSED; owner-approved D8 + D8-delivery (`owner-decisions-2026-09-27.md:26`), not yet in CLAUDE.md."
- **Rule:** add "…the model is fetched once by `src/backend/scripts/download_models.py` into a local models dir; runtime loads that path with HF offline and fails closed if it is absent."
- **Verify:** "W-8 HC-EMB-001/002 with sockets blocked and an empty `HF_HOME`."
- **Planned by:** W-8.

**C-REDACT-1:**
- **Status today:** "contradicted for the doctor summary (`api/export.py:379,482`; text built inline `:551-604`; `modules/export.py:82,290,358`) and `/export/questions` (`api/export.py:607`). CSV/JSON (`modules/export.py:223,267`) become owner-approved named exceptions (D3) once W-10 amends `CLAUDE.md:60` and `data-privacy.md:173-174`."
- **On violation:** replace "(program D3)… Until D3 is answered" with "D3 is decided (2026-09-27)".
- **Planned by:** W-2, W-10.

**C-REDACT-2:**
- **Status today:** "partial. Bypasses at `core/external_runner.py:201` (dev) and `:172` (production break-glass), main = B. The payload is the whole composed prompt (`modules/rag.py:1256-1268`), not only the question (`data-privacy.md:196-197` @main is false)."
- **Owner:** "D12 decided: unconditional strict; break-glass only with audit + UI warning."
- **Planned by:** W-6, W-10.

**C-REDACT-3:**
- **Status today:** "**violated in the default dev config.** Both engines set `echo=settings.debug` (`core/database.py:46`, `core/profile_database.py:308`) with `debug=True` (`core/config.py:28`), and no `hide_parameters`, so bound PHI goes to stderr (S-01 probe). `medication_name` at INFO (`modules/notification_scheduler.py:517-520`, VERIFIED) and `display_name` at INFO (`api/profiles.py:328`) are masked only by root WARN."
- **Enforced at:** add "none for SQLAlchemy loggers (HC-AUD-007 caplogs `core.audit` only)."
- **Planned by:** S-01, audit plan 02.

**C-SAFE-2:**
- **Enforced at (legacy):** "`validate_response` `modules/rag.py:793-872` sets `is_valid=False` (`:869`) on any of 5 triggers (`:826`, `:833`, `:838`, `:858`, `:863`); faithfulness < 0.6 (`:862`) is one of them. None blocks: `api/assistant.py:772-811` serves the segments."
- **Planned by:** W-4 (G-B5 decided).

**C-SAFE-5:**
- **Class:** "PROPOSED; decided D11 (docs match code)."
- Replace "(`modules/rag.py:120-132`)" with "(`modules/rag.py:123-140`; contradictory lines `:128`, `:133`, `:134`)."
- **Owner:** "D11 decided. `CLAUDE.md:62` changes only if W-10 Q1 is signed."
- **Planned by:** W-5, W-10, P04 N8.

**C-VERIFY-2:**
- **Class:** "PROPOSED (owner decision D4, 2026-09-27; becomes a repo rule when W-10 amends `data-privacy.md`)."
- **Rule:** "Legacy RAG MUST cite verified observations only. Trends MAY show unverified points only when visibly labelled. Exports carrying unverified rows (CSV/JSON/doctor summary, `api/export.py:128-150`) are **not decided** (owner item)."
- Fix the citation: `modules/rag.py:322-328` → `:323-331`.
- **Planned by:** W-3, W-10, P04 N1.

**C-LLM-1:**
- **Status today:**
  1. "Dormant: `modules/model_selector.py:438` @main (`:456` after P1)."
  2. "External runner: owner-approved exception (D12), pending W-10's CLAUDE.md amendment."
- **Verify:** add `--include=*.py` and the `import llama_cpp` form (W-7 F-2).
- **Planned by:** W-7, W-6, W-10.

**C-LLM-2:**
- **Enforced at:** "none (after W-7: HC-LLMB in `backend-tests`, `llama_cpp` only; that is a suite test, so matrix LLM-02 → `tested`, not `enforced`)."
- **Planned by:** W-7, W-11a (ruff).

**C-AUDIT-1:**
- **Status today:** "documents 13/13, observations 6/6, profiles 9/13 (`api/profiles.py:241,416,477,943` unaudited), **interpretations 0/7** (`api/interpretations.py:323,383,508,565,615,640,673`; 6 read or write observation-derived data, W-7 F-3)."
- **Planned by:** W-11a (profiles); interpretations are **unowned** → W-7 if OG-3 is signed, else W-11a.

**C-AUDIT-2:**
- **Class:** "OWNER-GATED. D10 frames it (HIPAA-aligned design posture, not legal status)."
- **Rule note:** "No product code configures a log sink, and INFO audit echoes are dropped after startup (root WARN via `alembic.ini:45-47`). The `logs/asclexis.log` claim (`data-privacy.md:33`) is false, not UNVERIFIED."
- **Planned by:** P08 (brief 4); W-11b O-C3-4 for sink visibility.

**C-TIME-1** (the ledger calls it "C-TIME"; the contract ID is C-TIME-1):
- **Status today:** add "7 aware `datetime.now(timezone.utc)` sites in 6 product files (`core/auth.py:73,144`, `core/security.py:136`, `core/token_revocation.py:51`, `api/export.py:949,1005`, `api/model_settings.py:332`). None was found persisting to a naive column (by reading, not by test). `Session.is_expired` must keep comparing aware-to-aware: swapping in `core.time.utcnow` there would raise TypeError against `expires_at` (`core/auth.py:144,207`)."
- **Owner:** auth/security sites are ask-first.

**C-KEY-1:**
- **Status today:** add "**Native Windows dev vaults are unencrypted.** `sqlcipher3-binary` has no cp313 `win_amd64` wheel (`pip download … --only-binary=:all:` → 'No matching distribution'), so `dev.ps1:471-500` installs without it and `:586-593` flips `DATABASE_ENCRYPTION_REQUIRED=false`. `dev.ps1:578` writes `=false` in the fallback `.env` even when SQLCipher is present."
- **Planned by:** W-11a (KEY-02 test); the Windows posture is unowned → owner item (G-C4 packaging must ship SQLCipher).

**C-ISO-2:**
- **Status today:** "review only. Known direct-call status assertions: `test_profile_deletion.py` HC-PDEL-001…018; HC-PKT-014/015 (`tests/test_visit_prep_packet.py:403-432`); HC-FHIR-103/104 (W-11b F-6). `api/profiles.py` guards have no HTTP test (ISO-02)."
- **Planned by:** W-11a (profiles); W-11b keeps F-6 as direct-call (documented).

**C-GATE-1:**
- **Verify:** add "Measured 2026-09-27 (Win Py 3.13.7, scratch archives): main 1245 · A 1248 · B 1288 · A+B merge-tree 1291. B `AGENT.md:76` (1269) is stale."
- **Rule:** add "A pass-count sentence changes only with a pass count measured in a named environment. It is never derived."

---

## 3. New rows (verified unless marked)

| ID (proposed) | Requirement | Source | Evidence (path:line @ref, command) | Status | Owner gate | Planned by |
|---|---|---|---|---|---|---|
| PRIV-09 | DB engines never log bound parameter values | C-REDACT-3; `hipaa-controls.md:71`; `data-privacy.md:47` | `core/database.py:46`, `core/profile_database.py:308` `echo=settings.debug`; `core/config.py:28` `debug: bool = True`; `config/.env.example:14`; `dev.ps1:573`; `hide_parameters` 0 hits (main/A/B); production forces debug off (`core/config.py:156` @main, `:155` @B). Stderr contents measured by the S-01 probe (B tree) | **contradicted** | S1-A, S1-B (1 line in ask-first `core/profile_database.py`) | 2026-09-27-S01-sql-echo-phi-leak.md |
| PRIV-10 | RL export files are erased with the profile and never committable | C-KEY-2 (crypto-erase); `api/profiles.py:799-803` docstring | `api/feedback.py:63-67` default dir `src/backend/rl_exports`, per-profile subdir `:341`; `api/profiles.py` has 0 `rl_export` refs (main/A/B); `git check-ignore -v --no-index src/backend/rl_exports/x.jsonl` → not ignored (only `data/rl_exports` matches `.gitignore:74`); the docstring "export routes stream downloads rather than writing files server-side" (`api/profiles.py:799-803`) is false. Content is strict-redacted (PRIV-01) | **gap** | yes: the delete-path edit is crypto-erase (C-KEY-2, ask-first) | **unowned** → propose a new small plan; W-11b sign-off `:1950` only opens it |
| AUD-05 | Audit / security INFO lines reach an operator-visible sink, or docs stop claiming one | `data-privacy.md:33` ("Master DB + log file"), `:35` ("Security events \| Log file") | `alembic.ini:45-47` root WARN, `:60-62` stderr; `fileConfig` at `migrations/master/env.py:38`, `migrations/profile/env.py:53` (every vault open); `core/audit.py:254` and `security/audit_middleware.py:75` log at INFO → dropped; no `basicConfig`/`dictConfig` in product code (only `scripts/*`) | **contradicted** (doc vs code) | W-11b O-C3-4 | 2026-09-27-P08-…md (brief 4 facts); 2026-09-27-W11b-…md (C3b); `data-privacy.md:33` fix → P08 |
| AUD-06 | Interpretation routes write audit rows | `CLAUDE.md:61` | `api/interpretations.py` 7 routes (`:323,383,508,565,615,640,673`), `grep -ci audit` → 0 | **gap** | W-7 OG-3 | **unowned** → W-7 if OG-3 is signed, else W-11a |
| TIME-03 | Aware datetimes stay out of naive storage (and are named) | `CLAUDE.md:57`; C-TIME-1 | 7 aware sites / 6 files (TIME-01 row). `core/auth.py:73` compares against the aware `expires_at` from `:144` / `:207` | **partial** (no persisted aware value found; unenforced) | auth/security sites ask-first | **unowned** → note in P5 (plan 05) scope, owner decides |
| KEY-08 | Native Windows dev vaults are SQLCipher-encrypted (or the posture is documented) | KEY-01; `CLAUDE.md:58` | `pip download sqlcipher3-binary --only-binary=:all:` (Win Py 3.13.7) → "No matching distribution found"; `dev.ps1:471-500` (install without), `:586-593` (REQUIRED=false), `:578` (fallback `.env` REQUIRED=false) | **gap** (cp313 only; other Windows Pythons UNMEASURED) | yes (encryption) | **unowned** → owner item; G-C4 (W-11b) packaging must carry SQLCipher |
| GATE-12 | Tests never open the developer's real master DB | recurring-failures #1-adjacent (isolation) | `core/database.py:44-48` builds the engine at import from `sqlite+aiosqlite:///data/asclexis.db`, resolved against the import-time cwd (`core/config.py:160-185`); S-01 fact 11. Today 0 test files import `engine`/`async_session_maker` (3 import `get_db`; `tests/support/routes.py` overrides it); `src/backend/data/` is **absent** after the 2026-09-27 full run → no write observed | **gap** (latent; no guard) | — | 2026-09-27-S01-…md (HC-SQLECHO-002 + Task 4 Step 2, own tests only); a general guard is unowned → W-11a |
| LOCAL-06 | A test run makes no network fetch; an env-dependent pass must not hide one | recurring-failures #4 candidate; C-LOCAL-1 | HF snapshot `1110a243…` created 17:05:28–33 PDT, inside the Wave-0 run window (output 17:05:46, 90.95 s). The attribution to `test_api_rag_index_002b` is **inferred** (timing correlation, not process capture) | **gap** (observed) | — | 2026-09-27-W08-…md (socket-blocked HC-EMB tests); add to `recurring-failures.md` (W-8 or P04) |
| LOCAL-07 | Docs state exactly what the external runner sends | `data-privacy.md:196-197` @main (`:213-214` @A) | `modules/rag.py:1256` `compose_prompt(question, chunks, history)`, `:1259-1264` memory, `:1267-1268` → runner. The whole prompt is sent, redacted | **contradicted** (doc) | — | W-10 F-2 → P04 addendum (ledger); propose P04 own it |
| GATE-13 | `core/` does not import `modules/` (or the doc lists the exceptions) | `docs/architecture/backend.md:93` | 5 imports: `core/config.py:229` (B `:228`), `core/document_crypto.py:65`, `core/external_runner.py:202`, `core/llm/llama_cpp_provider.py:122`, `core/model_runner.py:117` | **contradicted** (doc) | — | 2026-09-27-P04-…md (N5) |
| GATE-14 | `agent_eval_gate.py` exits with its gate code | C-GATE-2 (fail closed; a hang is neither) | Prints "Agent eval gate: PASS" and then does not exit: `timeout 420` → `rc=124` (Win Py 3.13.7, HF offline, scratch main archive, 2026-09-27 20:50–20:57). W-3 saw the same (>300 s). Linux/3.11 UNMEASURED | **gap** (Windows) | — | **unowned** → propose W-11a |

**Recount if all 11 are added:** 73 rows · 4 enforced · 18 tested · 4 implemented · 16 partial · 20 gap · 8 contradicted · 2 owner-gated · 1 unknown.
- This assumes the §2.1 status changes are adopted: PRIV-06 partial → contradicted; PRIV-08 unknown → gap.
- AUD-03 and KEY-06 stay owner-gated. New rows: 3 contradicted-doc/code (AUD-05, LOCAL-07, GATE-13) + PRIV-09 contradicted; 6 gap (PRIV-10, AUD-06, KEY-08, GATE-12, LOCAL-06, GATE-14); 1 partial (TIME-03).
- Arithmetic: 4+18+4+16+20+8+2+1 = 73 = 62 + 11. Recount by script before publishing.

---

## 4. Doc claims shown false, and who fixes them

| # | path:line @ref | Claim | Why false (evidence) | Owner |
|---|---|---|---|---|
| 1 | `CLAUDE.md:30-31` @main (= B) | "Where a real embedding model is installed (CI) all N pass" | CI installs none (`ci.yml:30-48`); the pass comes from the implicit fetch (M2) | W-8 (baseline sentences, W08 `:143`, `:1401`) |
| 2 | `AGENT.md:57` @main; B `:76` | "1245 pass in CI, 1244 without an embedding model"; B "1269 collected" | CI clause as #1; B count stale (1288) | P1 (plan 01 conflict resolution) for the count; W-8 for the clause |
| 3 | `AGENT.md:64` @main | `002b` "fails locally and passes in CI" | It passed locally on 2026-09-27 after an implicit fetch (Wave-0: not among the 4 failures) | W-8 |
| 4 | `docs/architecture/ci-and-quality-gates.md:44` | "Baseline is ~1160 passing" | 1245 collected @main; no measured pass count in any named env | P04 N6 |
| 5 | same `:19` (and `:45`) | frontend job runs "build" | `ci.yml:50-73` runs `tsc` + `vitest` only | P04 N6 (true after W-11a G-B4) |
| 6 | `docs/architecture/README.md:50` | ModelRunner "the only LLM entry point" | `model_selector.py:438`; `core/external_runner.py:95` | P04 N4 / F3 |
| 7 | `docs/architecture/README.md:94-97` | HF is the "only" outbound connection and "never on a request path" | implicit fetch at `modules/embeddings.py:56` on first embedding use; opt-in cloud runner | P04 N4 |
| 8 | `docs/architecture/backend.md:93` | "`core/` never imports from `modules/`" | 5 imports (GATE-13) | P04 N5 |
| 9 | `docs/architecture/pipelines.md:41-46,53-56` | trends and all exports consume the verified set | `api/observations.py:529-535`; `modules/rag.py:323-331`; `api/export.py:128-150` | P04 N1 (after W-3 / W-10) |
| 10 | `docs/architecture/pipelines.md:111` | cited answer `[REFERENCE:N] / [YOUR_RESULTS:N]` | validated marker is `[cite:N]` (`rag.py:819`) | P04 N8 (after W-5) |
| 11 | `docs/compliance/data-privacy.md:33` (main = A) | audit logs in "Master DB + log file" | no product file sink; INFO echo dropped (AUD-05) | P08 (cited at P08 facts) |
| 12 | `data-privacy.md:47` | log files contain "event metadata, not PHI" | SQL echo to stderr (PRIV-09); no file today, but any redirect would capture it | S-01 |
| 13 | `data-privacy.md:173-174` | every other export path is redacted | CSV/JSON/doctor summary/questions unredacted | W-10 (D3 wording) + W-2 (code). **Program `:195` still assigns this to P4, and program `:69` still orders data-privacy.md P1 → P4 → G-A1; both are superseded** → program owner (orchestrator) |
| 14 | `data-privacy.md:196-197` @main (`:213-214` @A) | "Only the specific query text is sent" | the whole composed prompt is sent (LOCAL-07) | P04 addendum (per W-10 F-2); propose P04 |
| 15 | `docs/compliance/hipaa-controls.md:71` | "the plaintext app log does not become a second copy" | SQL echo writes bound values (PRIV-09) | S-01 |
| 16 | `hipaa-controls.md:169` | key rotation "Manual via password change" | re-seal, not rotation (KEY-05) | P04 N9 (after P08 brief 2) |
| 17 | `api/profiles.py:799-803` docstring | exports "stream downloads rather than writing files server-side" | RL export writes `src/backend/rl_exports/profile_<id>/` (PRIV-10) | W-11b S-C1-2 (docstring only); erase fix unowned |
| 18 | `api/backup.py:10-15` docstring | "Every other export path … passes through `modules/redaction.py`" | same as #13 | W-10 (F-3 routed to the W-2 PR) |
| 19 | `core/audit.py:4,212` @main (`:4,215` @B); `models/audit.py:4,24` (+2 migrations per P08) | "HIPAA-compliant audit trail" | D10 forbids asserting compliance (`owner-decisions-2026-09-27.md:47`, Consequence 5) | P08 (lists them); an edit owner is not named → propose P04 addendum |
| 20 | `scripts/agent_eval_gate.py:6-8` | a CI step is "future … NOT part of this change" | `ci.yml:112` `agent-evals` exists | W-4 |
| 21 | `skills/asclexis-evals/SKILL.md:41` | abstention "≥ 95%" | the gate bar is == 1.0 | W-4 |
| 22 | `skills/asclexis-guardrails/SKILL.md:63` | "bypass redaction for any reason" is forbidden | the break-glass exception (D12) | P04 N10 (after W-6) |
| 23 | `docs/capstone-report/architecture-overview.md:185`, `:188` | 3 imports; "P3 of the program" | 5; P4 | P04 (§14 finding 1–2) or the orchestrator's capstone edit |
| 24 | overview `:84`, `:111`, `:130`, `:211`; matrix `:71`, `:77`, `:89`, `:91`, `:98`, `:137`, `:140`; contract `:169`, `:211`; claims `:27`, `:42`, `:51`; handoff `:138`, `:139`, `:140`, `:142`, `:143`, `:144` | stale cites and counts (M3–M6, M8) | §1.2 rows 27–33 | **unowned** → orchestrator's integrated capstone edit (W-8 already edits matrix/contract/overview LOCAL-03 rows; serialize with it) |
| 25 | `docs/capstone-report/owner-decisions-2026-09-27.md:46` | model "size not measured" | 11 files, 91,578,415 B | orchestrator |
| 26 | `docs/agentic/recurring-failures.md:33` @A | `GET /profiles/` path token | trips B's drift check on the merged tree (exit 1) | P1 conflict resolution (plan 01 banner) |
| 27 | `docs/architecture/pipelines.md:44-45` | highlights, care-task candidates and med reconciliation read only verified data | they read unreviewed entities and drop rejected ones (P04 finding 9; not re-verified here: **UNVERIFIED** by 3b) | P04 N1 |
| 28 | `2026-06-30` survey `:152` | MIT license for all-MiniLM-L6-v2 | W-8 says Apache-2.0; **UNVERIFIED** by 3b | W-8 |

---

## 5. Commands appendix (run 2026-09-27, 20:45–21:00 PDT)

```bash
W=scratchpad/wave3
git archive main | tar -x -C $W/maintree        # likewise A → atree, B → btree, merge-tree 86606d0 → mtree
export HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 WSLENV=HF_HUB_OFFLINE/u:PYTHONDONTWRITEBYTECODE/u
(cd $W/<tree>/src/backend && /mnt/c/Python313/python.exe -B -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1)
#   maintree 1245 · atree 1248 · btree 1288 · mtree 1291
(cd $W/maintree && timeout 420 /mnt/c/Python313/python.exe -B scripts/agent_eval_gate.py)   # PASS printed, rc=124
(cd $W/btree && python3 scripts/harness_drift_check.py; echo $?)   # passed, 0
(cd $W/mtree && python3 scripts/harness_drift_check.py; echo $?)   # recurring-failures.md:33 missing path '/profiles/', 1
git check-ignore -v --no-index src/backend/rl_exports/x.jsonl data/rl_exports/x.jsonl rl_exports/x.jsonl
#   only data/rl_exports matched (.gitignore:74)
/mnt/c/Python313/python.exe -c "import sqlcipher3"   # ModuleNotFoundError
/mnt/c/Python313/python.exe -m pip download sqlcipher3-binary --no-deps --only-binary=:all: -d <scratch>
#   No matching distribution
```

**Next action:** apply §2.1 (the 27 rows plus the new `Planned by` column) and §3 (the 11 new rows) to the matrix in one orchestrator edit. Then re-run the scorecard script; §1.2 row 25 has the regex.
