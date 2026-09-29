# 3b fork — number/citation audit: W07, W08, W10, W11a, W11b, S01, P04, P08

Verdict: 0 BLOCKER, 0 MAJOR, 4 MINOR. 96 checks: 92 MATCH, 4 MISMATCH (all minor). Every test-count delta in these 8 plans equals the tests the plan writes.
Refs: main=40f590e, A=origin/claude/asclexis-repo-audit-349pjq@692fdf3, B=origin/claude/healthcentral-agentic-research-r1n54x@7b2ff1f. Helper: `s(){ git show $1:$2 | sed -n "$3"; }`.

## MINOR findings

| # | Where | Claim | Measured | Command |
|---|---|---|---|---|
| m1 | W11b:325, :1841 | model size "11 files, 91,578,415 bytes … per W-8 (`:17-22`)" | The figure sits at W08 `:34` and `:103`, not `:17-22` (W08 r4 shifted lines). Value agrees | `grep -n '91,578,415' docs/plans/2026-09-27-W08-*.md` → 34, 103, 778 |
| m2 | W11b Task C3b.3 (:1695-1722) vs W11a Task 11 (:1776-1863) | W11b adds Playwright `E2E-HEALTH-001` (new file `e2e/health-smoke.spec.ts`); W11a Task 11 writes the measured Playwright count into docs | Neither plan references the other; the count moves 28→29 (main) / 30→31 (A+B) if W11b lands after W11a Task 11, so W11a's replacement figure goes stale. Also W11b states no Playwright/vitest delta | `grep -nE 'W-11b\|health-smoke\|E2E-HEALTH' W11a` → 0; `grep -nE 'W-11a\|Playwright count' W11b` → 0 |
| m3 | ledger "P04: 30 tasks" | 30 tasks | 25 `## Task` headings; 33 task units (0,1,2,3,4,5R,6,7,8,9,11,13,14,10,12,15,N1–N10,F1–F6,16). No command recorded for "30" | `grep -cE '^#+ Task' P04` → 25 |
| m4 | W08:141 | test file row "create (HC-EMB-001..004c)" | the same file also gets HC-EMB-004d, 004e (:614, :630). Arithmetic (+13) still right | `grep -n 'def test_hc_emb_004' W08` |

Not a defect, but label it: S01:110 "`4/1271 tests collected`" is a scratch extract of **B** (`git archive 7b2ff1f src/backend`, Win Py3.13.7, 4 collection errors from missing repo-root scripts). It is not comparable to B's 1288 and must never be quoted as a baseline. S01 already labels it "context, not targets".

## 1. Test-count arithmetic (all MATCH)

| Plan | Claim | Tests written in plan code blocks | Result |
|---|---|---|---|
| W07 :911 | C1 = START+16 (9 HC-INT module + 7 HC-LLMB) | LLMB 001 + 001b×4 (parametrize :318) + 001c + 002 = 7; INT 011, 012, 013×3 (:559), 014, 015, 016, 017 = 9 | MATCH |
| W07 :1198, :1355 | END = START+23 | + route INT 001, 002, 003, 004×3 (:1036), 005 = 7 → 23 | MATCH |
| W08 :1250, :1337 | START+13, +14 with Task 7 | 001, 003, 004a–e (5), 002, 005, 006a, 006b, 006c, 007 = 13; 008 (Task 7) = 14 | MATCH |
| W11a :1735-1745, :1863 | PR-1 15 (+6, or +7 with HC-PAUD-006); PR-2 7; PR-3 5 | PGUARD 001×5 (GUARDED :494) + 002 + 003×2 + 004 + 005×5 (BYPASS_EXPECT :631) + 006 = 15; PAUD 001–007 = 7; KEYCT 001–004 + 005×3 = 7; MIGHEAD 001×2 + 002 + 003×2 = 5 | MATCH |
| W11b :1036, :1890 | C1 = START+16 | EXPA 001×3 + 002 + 003×3 + 004×3 + 005–010 (6) = 16 | MATCH |
| W11b :1900 | C3a = START+5 | EXTR 001 + 002×3 (FIELDS :1273) + 003 = 5 | MATCH |
| W11b :1902 | C3b = START+4 | OBSV 001, 002, 003, 004 = 4 | MATCH |
| W11b :300 | "9 tests must change mechanism" | HC-PKT-010, 012–016 (6) + HC-FHIR-102–104 (3) = 9 | MATCH |
| S01 :1008, :1052 | N0+4 (N0+3 without S1-B) | sqlecho 001, 002, 003 (S1-A) + 004 (S1-B) | MATCH |
| P08 :601 | end = start + 0 | docs only | MATCH |
| W10 :1005 | collected unchanged | docs only; W10-A1…A9 are script assertions, not pytest | MATCH |

### Frontend counts (W11a :217-218) — corroborated statically
- Vitest: `git ls-tree` test files main 28, A 30, B 29 → A+B 31 ✓. Static `it(`/`test(` declarations: main **165** ✓, A 174 (+9), B 170 (+5) → A+B **179** ✓.
- Playwright (chromium project; `playwright.config.ts:72` `testIgnore: ['**/ui-full-verification.spec.ts']`): 5 files main ✓; declared tests 11+5+5+3+4 = **28** ✓; A adds `recovery-code.spec.ts` with 2 → **30 / 6 files** ✓.
- W11a labels these "listed (Linux, not Windows)" — i.e. measured by listing, not by running. Pass counts remain unmeasured. The old "155 / 25" came from `TASK_LIST.md:794` ("vitest 155/155; Playwright 25 passed / 3 conditional skips") and `audit/repository-audit-dashboard.html:255` — confirmed. 25 was a pass count (28 − 3 conditional skips).
- ruff re-measured on main working tree: `~/.local/bin/ruff check . --no-cache --statistics` (0.15.10, src/backend) → `Found 555 errors.` ✓ (W11a :210 main 555).

## 2. Line-number citations (sample, all at the ref the plan names)

### W07 (21 checks, all MATCH)
| Citation | Actual |
|---|---|
| main `modules/model_selector.py:438`, B `:456` | `from llama_cpp import Llama` at 438 (main), 456 (B) |
| main `modules/interpret.py:877` | `async def interpret_with_model(`; 0 non-test callers (`git grep -n interpret_with_model main -- src/backend`) |
| main `interpret.py:903` | `get_model_for_inference(` call |
| main `interpret.py:761` | `run_inference(` |
| main `interpret.py:783-785` | `except` → "falling back to template" → `_generate_interpretation` |
| main `interpret.py:1019-1021` | `model_id=`, `model_tier=active_tier`, `confidence_score=…` |
| main `models/interpretation.py:50-54` | `observation_id … unique=True` |
| main `interpret_safety.py:101/:127/:247` | `validate_interpretation(` / `prohibited_{violation_type}` / `add_required_disclaimers(` |
| main `core/model_runner.py:31-38, :174` | `@dataclass` InferenceConfig; `async def generate_async(` |
| B `core/audit.py:70/:102/:338/:474` | `"action"` / `"llm_assist"` / `log_observation_event` / `audit_and_commit` |
| main `api/__init__.py:42` | interpretations router at `/interpretations` |
| main `api/interpretations.py` 7 routes, 0 audit | `grep -cE '@router\.'` → 7; `grep -c audit` → 0 |
| B `model_selector.py:206-211`, `:437` | `_loaded_model`, `_current_tier`, `_load_lock`; `def load_model` |
| main `llama_cpp_provider.py:36`; B `:136` | lazy `from llama_cpp import Llama`; `verbose=self._settings.debug` |
| main `tests/support/routes.py:26` | `@contextmanager` for `route_client` |

### W08 (8 checks, all MATCH)
- B `ci.yml:33-51`: backend job = checkout, setup-python 3.11, `libsqlcipher-dev`, `pip install -r requirements.txt`, `run-backend-tests.sh -q`. `grep -niE 'model|embed|sentence|hugging|HF_'` on B and main ci.yml → **0 hits**. So "installed (CI)" in main `CLAUDE.md:30-31` and "passes in CI" in `AGENT.md:57,64` describe an implicit HF fetch (`requirements.txt:53` `sentence-transformers>=2.2.0`).
- main `modules/embeddings.py:56` `SentenceTransformer(self.config.model_name)` (no offline flag) ✓.
- main `tests/test_rag_pipeline.py:237` def 002b; `:270` `assert similarity > 0.7` ✓.
- A `api/documents.py:867-871`: `delete(Chunk)` at 867-868 **before** `embedder.embed_chunks` at 871 ✓ (reprocess data-loss finding).
- C-LOCAL-1 allow-list: contract grep → 7 files main; **8 on B** (adds `src/backend/scripts/download_models.py`) ✓ W08:1402.
- HF live-fetch evidence (W08:108, :1406; ledger LOCAL-03): `/mnt/c/Users/DangT/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/refs/main` mtime `2026-09-27 17:05:28.59 -0700`, content `1110a243…`; `snapshots/` mtime `17:05:28.58`. Wave-0 output `scratchpad/baseline-main.txt` mtime `17:05:46.09`, footer `4 failed, 1241 passed … in 90.95s` → run window ≈17:04:15–17:05:46. Fetch falls inside the run window. **Correlation, not proof of process** — keep it labelled as inference.
- Side fact: B removes `default_embeddings_model: str = "bge-small-en-v1.5"` at main `core/config.py:89` (`git diff main B -- src/backend/core/config.py`). Consistent with S01/P08 "+/-1 line at :89".

### W10 (5 checks, all MATCH)
- F-2: main `modules/rag.py:1256` `prompt = self.compose_prompt(question, chunks, history=history)`; `:1259-1264` memory section injected; `:1267-1268` `runner = model_runner or self._model_runner; await self._generate_with_runner(prompt, runner)`. The whole composed prompt (retrieved chunks + history + memory) goes to whichever runner, including `ExternalModelRunner`.
- main `data-privacy.md:196-197` "Only the specific query text is sent…" / "Full health records are never transmitted"; A `:213-214` same text ✓ (`grep -n "Only the specific query text"` → 196).
- F-3 main `api/backup.py:10-15` "Every other export path in this app passes through `modules/redaction.py`" ✓ (false for CSV/JSON/doctor summary).
- F-1 B `skills/asclexis-guardrails/SKILL.md:63` "bypass redaction for any reason" under `## Never` (:60) ✓.

### S01 (15 checks, all MATCH)
| Citation | Actual (main = B unless noted) |
|---|---|
| `core/config.py:28` | `debug: bool = True` |
| `config/.env.example:14` | `DEBUG=true` (the only `.env.example` in the tree is under `config/`; ledger's bare ".env.example:14" means this file) |
| `dev.ps1:573` | `"DEBUG=true",` |
| `core/database.py:46` | `echo=settings.debug,` (engine at :44-48, module level) |
| `core/profile_database.py:308` | `echo=settings.debug,` |
| config production force-off B `:155-156`, main `:156-157` | `if self.app_env == "production" and self.debug:` / `object.__setattr__(self, "debug", False)` |
| B `alembic.ini:45-46, 60-62` | `[logger_root] level = WARN`; `[handler_console] … args = (sys.stderr,)` |
| B `migrations/{master,profile}/env.py:38/:53` | `fileConfig(…, disable_existing_loggers=False)` |
| B `core/database.py:87` | `logs_dir.mkdir(...)` — only use of `log_file_path` |
| main `dev.ps1:285, :715, :718-722` | frontend `-RedirectStandardError`; `$frontendLog`; backend `Start-Process … -WindowStyle Hidden` with no redirect |
| B `tests/test_audit_phi_minimization.py:317-318` | HC-AUD-007 caplog on `core.audit` |
| main `hipaa-controls.md:71`, `data-privacy.md:47` | "plaintext app log does not become a second copy"; "Log files … not PHI" |
| B `api/profiles.py:328` | `logger.info(f"Created profile: {profile_id} ({profile_data.display_name})")` |
| `git grep hide_parameters` main/A/B | 0 (per plan; not re-run) |

### W11a (7 checks, all MATCH)
- main `dev.ps1:471-500`: on pip failure matching "sqlcipher", installs requirements minus sqlcipher and sets `$sqlcipherAvailable = $false` ✓.
- Windows Py3.13 has no sqlcipher3: `ls /mnt/c/Python313/Lib/site-packages | grep -i sqlcipher` → nothing ✓. Wave-0 "1241 passed" therefore ran vaults unencrypted (note: the suite also sets `DATABASE_ENCRYPTION_REQUIRED=false`, `tests/conftest.py:57`, so encryption is not asserted on any interpreter).
- `TASK_LIST.md:794`, `audit/repository-audit-dashboard.html:255`, `specs-compliance-matrix.md:165` ✓; vitest/Playwright/ruff numbers above ✓.

### W11b (20 checks, all MATCH)
| Citation | Actual (main) |
|---|---|
| PRIV-08 stores | `api/export.py:44 _summary_store`, `:47 _packet_store`, `:50 _fhir_store` (module-level dicts) |
| `api/pinboards.py:13`, `:495` | `from api.export import _compute_trends, _packet_store`; `_packet_store[packet["packet_id"]] = packet` |
| `api/feedback.py:64-67` | `_DEFAULT_EXPORT_DIR = … RL_EXPORT_DIR … parents[1] / "rl_exports"` |
| `rl_export` in `api/profiles.py` main/A/B | `grep -c` → 0, 0, 0 |
| `.gitignore` | main/A/B `:111 exports/` only; `git check-ignore -v --no-index src/backend/rl_exports/profile_x/dpo.jsonl` → exit 1 (not ignored; `exports/` does not match `rl_exports/`) |
| `api/profiles.py:799-800` | "the export routes stream downloads rather than writing files server-side" — false for `/feedback/export` |
| `data-privacy.md:108` | `rl_exports/profile_<full-profile-uuid>/` |
| `core/profile_database.py:134, :179-181, :367` | `vault.db`; `get_profile_vault_path` → `app_data_path/vaults/<id>`; `run_profile_migration_async` |
| `security/audit_middleware.py:75-78` | `logger.info("SECURITY_AUDIT: %s", …)` (INFO — suppressed under root WARN once fileConfig ran) |
| `tests/test_care_tasks.py:809, :825` | `== "012_pinboards"` (plan 06 head move breaks both) |
| `tests/test_visit_prep_packet.py:259` | `_packet_store,` import |
| `modules/extract.py:74-77` | hard-coded unit alternation in `VALUE_PATTERN` (no `ug/dL`, `mIU/L`) |
| B `core/config.py:159-163` | `app_data_path` → `Path("data")` in local mode |
| `main.py:101` | CORS `["http://localhost:3000", "http://127.0.0.1:3000"]` |
| `monitoring/health.py:23-30`, `e2e/support/auth.ts:3` | `{"status": "healthy", …}`; `E2E_API_URL` export |

### P04 (5 checks, all MATCH)
- core→modules imports (`git grep -nE "^\s*(from modules|import modules)" <ref> -- src/backend/core`): **5 on main, A and B** — `config.py:229` (B `:228`), `document_crypto.py:65`, `external_runner.py:202`, `llm/llama_cpp_provider.py:122`, `model_runner.py:117`. Overview `:185` lists 3 (missing document_crypto, llama_cpp_provider) ✓ P04:1206.
- Overview `:188` "P3 of the program" → should be P4 ✓.
- main `docs/architecture/ci-and-quality-gates.md:44` "~1160 passing" ✓.
- golden files: 74 on main and B ✓.

### P08 (10 checks, all MATCH)
- B `core/audit.py:257-264` INFO echo (main `:254-261`) ✓; B `:4`, `:215` "HIPAA-compliant"/"HIPAA compliance"; B `models/audit.py:4`, `:24` same ✓.
- B `core/config.py:79` `audit_security_events_to_db=False`; `:123 log_level`, `:124 log_file_path`, `:125 audit_log_enabled`; `:179-184 database_url` ✓. Reads outside config: `git grep -nE "\.log_level|audit_log_enabled" B -- src/backend | grep -v core/config.py` → none ✓ (both settings inert).
- `scripts/backup.py:203-205` master DB appended to backup set ✓.
- A `data-privacy.md:33` "Audit logs | Master DB + log file" (overstates; no file sink) ✓; A `:150-153` erase decision rejected full-retention ✓.
- B `scripts/security_gate.py:58, :84` catch → gate failure ✓.
- B `CLAUDE.md:30` "1288 backend tests collected" vs B `AGENT.md:76` "(1269 collected; 1269 pass in CI, 1268 without…)" ✓ — conflict is real; P1 must reconcile.

## 3. Other numbers

| Number | Source | Command given? | Agrees? |
|---|---|---|---|
| ruff 555 main / 561 B / 561 A+B | W11a:210 | yes | main re-measured 555 ✓ |
| eslint 0 errors / 5 warnings; build exit 0 | W11a table | yes (Linux copy) | not re-run |
| vitest 165/28 files, 179/31 | W11a:217 | yes (`vitest list`) | static count ✓ |
| Playwright 28/5, 30/6 | W11a:218 | yes (`--list`) | static count ✓ |
| 74 golden cases | P04:100, :278 | yes | ✓ main, B |
| 5 core→modules imports | P04:807, :1206 | yes | ✓ |
| C-LOCAL-1 allow-list 7 → 8 after P1 | W08:1402 | yes | ✓ |
| 7 routes / 0 audit calls in api/interpretations.py | W07 F-3 | yes | ✓ |
| model 11 files / 91,578,415 B | W08:34, :103 | yes (`find … du`) | not re-measured; cross-cite in W11b off (m1) |
| golden set 8 docs / 28 rows; P=1.00 R=0.93 | W11b:309 | prototype output | not re-run (scratch prototype) |
| probe: 156 engine lines, 69 "parameters hidden" | S01:111, :992 | yes (Task 4 probe) | not re-run |
| "30 tasks" P04 | ledger | no | ✗ 25 headings / 33 units (m3) |

## 4. Cross-plan test IDs

| Plan | Defines | References (owned elsewhere) |
|---|---|---|
| W07 | HC-INT-001…005, 011…017; HC-LLMB-001, 001b, 001c, 002 | — |
| W08 | HC-EMB-001, 002, 003, 004a–e, 005, 006a–c, 007, 008 | — |
| W10 | none (W10-A1…A9 script assertions) | HC-EXPR (W-2), HC-EXT (W-6), HC-VER (W-3), HC-BKUP-035/042 (existing), HC-BKUP-999 (deliberate NO-TEST probe) |
| W11a | HC-PGUARD-001…006, HC-PAUD-001…007, HC-KEYCT-001…005, HC-MIGHEAD-001…003 | — |
| W11b | HC-EXPA-001…010, HC-EXTR-001…003, HC-OBSV-001…004, E2E-HEALTH-001 | HC-PKT-010,012–016, HC-FHIR-102–104 (existing), HC-RESET-010 (plan 07), HC-EMB-002 (W-8) |
| S01 | HC-SQLECHO-001…004 | HC-AUD-007 (existing) |
| W06 (ref only) | — | HC-LLMB-001 (W-7), HC-AUD-010 (existing) |
| P04, P08 | none | — |

- No ID is defined by two plans.
- Zero hits on main/A/B for `HC[-_](EXPA|EXTR|OBSV|PGUARD|PAUD|KEYCT|MIGHEAD|SQLECHO|INT[-_]0|LLMB|EMB)` and `E2E-HEALTH` (`git grep -niE … <ref> -- src | wc -l` → 0, 0, 0).
- Substring hazards (selectors in these plans are safe as written):
  - `HC-INT` ⊂ existing `test_HC_INTERP_001…005` (main/A/B `tests/test_interpret_history_units.py`). W07 selects with `-k "HC_INT_0"` and warns (:98, :210) ✓.
  - `HC-EXT` (W-6) ⊂ `HC-EXTR` (W-11b): a bare `git grep HC-EXT` would hit W-11b tests; W06 `-k hc_ext_` (trailing `_`) does not match `hc_extr_`; W10:377 greps `HC-EXT-001` ✓.
  - `HC-OBS` (existing `HC-OBS-AUDIT`) ⊂ `HC-OBSV`: only a bare `HC-OBS` grep is affected; W11b selects `-k hc_obsv` ✓.
  - `paud` ⊂ "pipaudit" (W11a:137 already warns; uses `-k hc_paud_`) ✓.
