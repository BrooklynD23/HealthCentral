# Wave 1 Report (L1)

**Status (2026-09-29):** PR #1 (#21) MERGED 16:22:50Z as `9b9958c`; L0 docs PR #22 merged → `origin/main` @ `77aaf20`. S-CACHE PR #23 open (head `3c53510`): 5 required checks pass; E2E Smoke fails on CI-DISK (`[Errno 28] No space left on device` in "Install backend dependencies", job 109523705510). Awaiting owner merge. PR #2 not started. L1 handed back at 10:4x before #23 merged.
**Merge order:** PR #1 (#21) → S-CACHE → PR #2.
**Base:** `origin/main` @ `36b2ff2` (unchanged at fetch time).

---

## Phase 1 — P1 PR #1 (branch B)

| Item | Value |
|---|---|
| PR | https://github.com/BrooklynD23/HealthCentral/pull/21 |
| Branch / head | `merge/healthcentral-agentic-research-r1n54x` @ `14f7812` |
| Worktree | `/mnt/c/Users/DangT/Documents/GitHub/hc-p1-b` |
| Plan | `audit/2026-09-25/plans/01-merge-branches.md` Task 1–2, banner items 1–6 |
| Gates used | "Merge both branches as-is"; P1-PR1-MERGE; P1-SLOTS |
| Collected | main 1245 (L0) → B tip START **1288** → B+main END **1288** (delta vs main +43) |

### Task 1 checks
```
git rev-parse origin/main A B        -> 36b2ff2… / 692fdf3… / 7b2ff1f…
git merge-base origin/main A|B       -> 40f590e (both)
git rev-list --count main..B / ..A   -> 19 / 5
git rev-list --count B..origin/main  -> 10 (main moved: PR #19 docs + PR #20 pin)
gh auth status                       -> BrooklynD23, scopes repo, workflow
git merge-tree --write-tree origin/main B -> conflicts: docs/INDEX.md, docs/_link_graph.json only
code diff 40f590e..B                 -> 28 files, all in plan inventory; no core/external_runner.py, no migrations
```

### Commits on top of B
| Commit | What |
|---|---|
| `f9f8f69` | `git merge origin/main`; `docs/INDEX.md` + `docs/_link_graph.json` regenerated (`generate_docs_index.py` → 1281 lines; `docs_lint.py --link-graph`); `--check` → fresh |
| `14f7812` | `AGENT.md:76` "1269 collected" → "1288 collected". `CLAUDE.md:30,35` already 1288 |

### Measured acceptance (L1 ran; venv Py 3.11.16, `HF_HUB_OFFLINE=1`, `__pycache__` cleared)
| Check | Output |
|---|---|
| `pytest tests/ --collect-only -q` (B tip) | `1288 tests collected in 11.62s` |
| same (B+main) | `1288 tests collected in 11.93s` |
| `pytest tests/ -p no:cacheprovider -q` | `1288 passed, 56 warnings in 210.86s (0:03:30)`, rc=0 |
| targeted: security_gate, memory_audit, medication_correlations, assistant_cache_version, hc_a1, s5_cutover_cache (no `-k`) | `35 passed, 2 warnings in 11.03s` |
| `python -c "from main import app"` | rc=0 |
| `git status --short` after suite | empty |
| `find . -name "*.db" -newer CLAUDE.md -not -path "*/node_modules/*"` | empty |
| `sed -n 27p requirements.txt` / `:72` | `sqlalchemy[asyncio]>=2.0.25,<2.1` / `llama-cpp-python==0.3.35` (venv: 0.3.35, SQLAlchemy 2.0.54, greenlet 3.5.6) |
| security_gate missing reports | `ERROR: Could not parse bandit report …` exit=2 |
| security_gate malformed JSON | exit=2 |
| security_gate clean control | `Security gate: PASS (no unwaived high/critical findings)` exit=0 |
| `timeout 600 python3 scripts/agent_eval_gate.py` (system 3.12.3) | rc=2 `could not import scorer: No module named 'sqlalchemy'` |
| same with `~/venvs/asclexis-311/bin/python` | `All 74 golden cases passed.` / `Agent eval gate: PASS`, **rc=0** (GATE-14 hang not reproduced on Linux/3.11) |
| docs_lint / generate_docs_index --check / feature_list_lint / repo_hygiene_check | 0 / 0 / 0 / 0 |
| harness_drift_check | **1**: `ERROR: docs/agentic/orchestration.md:63: missing path 'reviews/W04-r1-prompt.md'` (text from main/PR #19; L0 rewording it in the docs PR) |
| Frontend on Windows: `npm ci; npx tsc --noEmit; npx vitest run` | npm ci rc=0; tsc rc=0; `Test Files 29 passed (29)`, `Tests 170 passed (170)`, vitest rc=0 |
| `gh pr checks 21` at open | 5 jobs pending |
| `gh pr checks 21` final | Agent Eval Gate pass 7m58s; Backend Tests pass 10m21s; Documentation Lint pass 13s; Frontend Tests pass 1m20s; Security Scan pass 9m14s; E2E Smoke pending when merged (CI-DISK known) |

### Reviews
| Reviewer | Verdict | Key lines |
|---|---|---|
| code-reviewer (opus) | APPROVE | 7/7 spec checks OK; mutation check: reverting each B product file turns its tests red (security_gate 7/7, memory_audit 6/6, assistant 4/6) |
| security-reviewer (opus) | APPROVE | no unscheduled CRITICAL/HIGH; cache + category confirmed (scheduled S-CACHE) |
| Codex adversarial-review | needs-attention | [high] memory `category` → master DB (scheduled S-CACHE); [high] `security_gate.py:61,88` accepts `{}` as clean (L1 reproduced: exit 0) |

### Open findings (not fixed; B merges as-is)
**Needs an owner decision**
1. `scripts/security_gate.py:61,88` — valid JSON without `results`/`dependencies` → PASS. Also bandit `errors[]` and pip-audit `skip_reason` are ignored. Not a regression (main passed even missing files). Fix needs a gate (GATE-SCHEMA?).
2. `docs/agentic/orchestration.md:63` drift — L0 is fixing in the docs PR.

**Follow-ups**
1. `AGENT.md:76` pass clause "1269 pass in CI, 1268 without" vs `CLAUDE.md:31` "all 1288 pass" — left per banner item 2 (W-8).
2. Cache fingerprint ignores CarePlanTask / DocumentEntity / timeline (`api/assistant.py:553-596`) → stale answers within one profile.
3. Mid tier `bartowski/microsoft_Phi-4-mini-instruct-GGUF` at `revision="main"`, no sha256 (`model_selector.py:102,650`); `config/model_manifest.json:12` still names Phi-3; `core/config.py:88` default glob `phi-3-mini` does not match Phi-4 files.
4. `api/memory.py:135,250` — `value_length` and `fields` are not in `ALLOWED_DETAIL_KEYS`, so they are scrubbed (`_scrubbed: 1`). S02's "keep value_length" is moot.
5. `test_hc_a1_agent_verification.py:163` (`verify_003`) passes on main too; hard-coded fingerprint literal at `:71`. Cache hits write no audit row (`assistant.py:699-702`).

---

## Phase 2 — S-CACHE

| Item | Value |
|---|---|
| Plan | `docs/plans/2026-09-29-S02-agent-cache-profile-isolation.md` (Codex r1 amendments, on main via #22) |
| Branch / worktree | `fix/s-cache-profile-isolation` from `origin/main` @ `77aaf20`; `/mnt/c/Users/DangT/Documents/GitHub/hc-s-cache` |
| Gates used | S-CACHE, MEM-AUDIT-CAT, SLOT-RULE |

### Task 0 (L1 ran)
```
git ls-files docs/plans/2026-09-29-S02-agent-cache-profile-isolation.md  -> present on origin/main 77aaf20
git merge-base --is-ancestor B origin/main                               -> B on main
~/venvs/asclexis-311/bin/python --version                                -> Python 3.11.16 (WSL2 Linux 6.6.87.2)
pytest tests/ --collect-only -q (pipefail)                               -> rc=0, 1288 tests collected in 11.04s   (START)
pytest tests/ -p no:cacheprovider -q -rf                                 -> rc=0, 1288 passed, 50 warnings in 119.07s; FAILED list empty
git status --short ; find . -name "*.db" -newer CLAUDE.md                -> both empty
```

| Item | Value |
|---|---|
| PR | https://github.com/BrooklynD23/HealthCentral/pull/23 |
| Head | `3c53510` |
| Collected | START 1288 → 1290 (`14df9e7`) → END **1292** (`7435def`); delta +4 |

### Commits
| sha | subject | slots |
|---|---|---|
| `14df9e7` | fix(agent): scope answer-cache key by profile | 1290 |
| `7435def` | fix(memory): keep user-typed category out of memory audit details | 1292 |
| `56a45b0` | docs: record shared-cache-without-tenant in recurring failures | — |
| `3c53510` | test(memory): assert PHI-like category absent from every audit column (review loop 1) | — |

### RED before GREEN (implementer)
- ISO-001: `AssertionError: answer-for-<A>` (B got A's cached text; stub ran once). ISO-002: `AssertionError: assert CacheKey(...) != CacheKey(...)`.
- MEM-AUDIT-007/008: `2 failed, 6 passed` (`{"category": "HIV", "_scrubbed": 1}`, `{"count": 0, "category": "HIV"}`); after fix `8 passed`.
- Break-it: dropping `profile_id=` at the call site → ISO-001 red. Reviewer mutation copies: all 4 new tests fail on main code.

### Task 6 (L1 ran; pipefail)
| Check | Output |
|---|---|
| `pytest tests/ -p no:cacheprovider -q -rf` | rc=0, `1292 passed, 52 warnings in 117.50s (0:01:57)`; FAILED list empty (⊆ START empty) |
| `python -c "from main import app"` | boot rc=0 |
| `git status --short`; `find $W -name "*.db" -newer $W/CLAUDE.md` | both empty |
| docs_lint && generate_docs_index --check && harness_drift_check | `Docs lint passed.` / fresh / `Harness drift check passed.` rc=0 |
| agent_eval_gate (venv) | `All 74 golden cases passed.` / PASS rc=0 |
| Frontend | SKIPPED (no frontend files in diff) |
| `gh pr checks 23` at open | 5 pending |
| `gh pr checks 23` final | Agent Eval Gate, Backend Tests, Documentation Lint, Frontend Tests, Security Scan: pass. E2E Smoke Tests: fail, CI-DISK (known, non-blocking) |

### Reviews
| Reviewer | Verdict | Notes |
|---|---|---|
| code-reviewer (opus) | APPROVE | 2 MINORs (full-row HIV check; unused import) fixed in `3c53510`; CLAUDE.md:31 pass clause → owner |
| security-reviewer (opus) | APPROVE | profile_id from `RequireAuth` (`assistant.py:793`); no other CacheKey site; no other user text in memory audit |
| Codex adversarial-review | approve | "No material findings." |

### Open findings
1. `CLAUDE.md:31` "all 1288 pass" beside 1292 collected; `AGENT.md:76` pass clause — owner item AGENT-PASS-LINE should name CLAUDE.md:31 too.
2. Out of scope per plan: CACHE-STALE, eviction on profile delete, category values already in a dev master DB.

## Phase 3 — P1 PR #2 (branch A)
Not started (needs #23 merged). Preview only, read-only: `git merge-tree --write-tree origin/main(77aaf20) A` gives 5 conflicts: `AGENT.md`, `CLAUDE.md`, `docs/INDEX.md`, `docs/_link_graph.json`, `docs/agentic/recurring-failures.md`. `SettingsPage.tsx` auto-merges. This matches the plan's conflict map. Re-run it after #23 merges.

**RESUME POINT (for the next L1):**
1. Check `gh pr view 23 --json state` shows MERGED, then `git fetch origin`.
2. Create worktree `../hc-p1-a` on branch `merge/asclexis-repo-audit-349pjq` from `origin/claude/asclexis-repo-audit-349pjq`. Run `git merge --no-commit origin/main`.
3. Resolve the files per plan 01 Task 3 plus banner 6(b). Apply the P1-DRIFT reword of `GET /profiles/` at recurring-failures.md:33. Keep the S-CACHE §1 entry.
4. Add the P1-CAREQ-HTTP `route_client` DELETE test. Measure collected, then write it into both slots in the merge commit. Expected is about 1292 + 3 + 1, but only the measured count goes in.
5. Run Task 6 without `-k`, then the reviews, then Codex, then open PR #2.

---

## Phase 3 — P1 PR #2 (branch A), L1 run 2026-09-29

**Status:** PR #24 is OPEN at head `d116931`. The 5 required checks pass. E2E Smoke fails on CI-DISK. I polled for 3 h (11:42 → 14:52) and it was **not merged**, so Task 7 and Task 8 Steps 1-4 have **not run**.

| Item | Value |
|---|---|
| PR | https://github.com/BrooklynD23/HealthCentral/pull/24 |
| Branch / head | `merge/asclexis-repo-audit-349pjq` @ `d116931` (from A `692fdf3` + `git merge --no-commit origin/main`) |
| Base | `origin/main` @ `b50a7da` (= `77aaf20` + #23 merge; #23 merged 17:58:47Z) |
| Worktree | `/mnt/c/Users/DangT/Documents/GitHub/hc-p1-a` (clean) |
| Plan | `audit/2026-09-25/plans/01-merge-branches.md`: Tasks 3-6, banner items 1-6 |
| Gates used | Merge-as-is (§21 Q3); P1-DRIFT; SLOT-RULE; P1-SLOTS; P1-CAREQ-HTTP; D9-SRC |
| Collected | main START **1292** → resolved merge **1295** → END **1296** (delta +4 = CAREQ-001..003 + 004) |

### Pre-checks
```
gh pr view 23 --json state                  -> MERGED (poll 10:43 → 11:02)
git rev-parse origin/main                   -> b50a7da6ee98a1df4d83b4e9fdb83a0296e16e96
merge-base --is-ancestor 3c53510|14f7812|9b9958c origin/main -> all on main
origin/claude/asclexis-repo-audit-349pjq    -> 692fdf3; merge-base with main 40f590e
gh auth status                              -> BrooklynD23, scopes repo, workflow
../hc-p1-a, branch merge/asclexis-*         -> none existed beforehand (nothing stale)
git merge --no-commit origin/main           -> CONFLICT: AGENT.md, CLAUDE.md, docs/INDEX.md, docs/_link_graph.json, docs/agentic/recurring-failures.md; SettingsPage.tsx auto-merged
```

### START (main b50a7da; detached scratch worktree, since removed)
| Check | Output |
|---|---|
| `pytest tests/ --collect-only -q` | `1292 tests collected in 2.84s` rc=0 |
| `pytest tests/ -p no:cacheprovider -q -rf` | `1292 passed, 65 warnings in 76.17s` rc=0; FAILED list empty |
| `git status --short`; `find -name "*.db" -newer CLAUDE.md` | both empty |

### Resolution (merge commit `f5750b9`)
1. `CLAUDE.md` / `AGENT.md`: took `--theirs` (main). Slots 1292 → **1295**, measured on the resolved tree before the commit. Pass sentences unchanged (AGENT-PASS-LINE).
2. `recurring-failures.md`: union.
   - Mode 1 recheck = main's S-CACHE seed sentence + A's mock sentence.
   - Mode 8 = A's INGEST-FHIR "third instance" + main's memory-sanitize near-miss, with the rechecks combined.
   - A's §9 kept.
   - P1-DRIFT: `(`GET /profiles/`)` → `(the list route, `GET /profiles`)`.
   - Paragraph check: every paragraph of main and A is present verbatim except the 3 intentionally combined or reworded ones.
3. `INDEX.md` / `_link_graph.json`: `--theirs`, then `generate_docs_index.py` (1305 lines) + `docs_lint.py --link-graph`; `--check` → fresh.
4. `SettingsPage.tsx`: `RecoveryCodeCard` import :31, mount :884; `TierCapabilities` import :33, mount :533.
5. `requirements.txt:27` `sqlalchemy[asyncio]>=2.0.25,<2.1`; `:72` `llama-cpp-python==0.3.35`.

### Commits
| sha | subject | slots |
|---|---|---|
| `f5750b9` | Merge origin/main into claude/asclexis-repo-audit-349pjq | 1295 |
| `91fccd0` | test(documents): prove CARE-QUOTE-001 over HTTP with a route_client DELETE | 1296 |
| `d116931` | test(documents): assert HC-CAREQ-004 audit row is committed (review loop 1) | — |

### HC-CAREQ-004 (implementer sonnet; RED before GREEN)
- Loop 0, mutation "CARE-QUOTE-001 block removed" → `AssertionError: assert '<doc-id>' is None` → restored → `1 passed`.
- Loop 1, mutation "`master_db.commit()` removed" → `expected exactly one master DB commit, got []` → restored → PASS. `api/documents.py` ends unchanged.
- Reviewer mutations at `d116931`, all correct:
  - These go red: M1 (no CARE-QUOTE block), M2 (no audit call), M3 (no commit), M5 (`Depends(get_db)`), M6 (commit moved before the audit add).
  - These stay green, as they should: M4 (`synchronize_session=False`), M7 (filename scrubbed by `_scrub_details`).

### END measured acceptance (L1 ran in hc-p1-a at d116931; pipefail)
| Check | Output |
|---|---|
| `pytest tests/ --collect-only -q` | `1296 tests collected in 12.70s` rc=0 |
| `pytest tests/ -p no:cacheprovider -q -rf` | `1296 passed, 46 warnings in 116.23s (0:01:56)` rc=0; FAILED list empty (⊆ START empty) |
| `python -c "from main import app"` | rc=0 |
| `test_documents_api.py -k "CAREQ or ENT_03"` | `6 passed, 9 deselected` |
| `test_security_gate.py test_memory_audit.py test_medication_correlations.py` (no `-k`) | `26 passed` |
| security_gate: missing / malformed / clean | `ERROR: Could not parse bandit report …` exit=2 / exit=2 / `Security gate: PASS …` exit=0; `no report files modified` |
| `timeout 600 venv agent_eval_gate.py` (at 91fccd0; only the test file changed after) | `All 74 golden cases passed.` / `Agent eval gate: PASS` rc=0 |
| docs_lint / index --check / feature_list / hygiene / drift (no pipes) | 0 / 0 / 0 / 0 / **0** (`Harness drift check passed.`) |
| Frontend on Windows: `npm ci; npx tsc --noEmit; npx vitest run` | rc 0 / 0 / 0; `Test Files 31 passed (31)`, `Tests 179 passed (179)` |
| `git status --short`; `find $W -name "*.db" -newer $W/CLAUDE.md` | both empty after every run |
| `gh pr checks 24` at open | 5 pending |
| `gh pr checks 24` at 14:52 | Agent Eval Gate pass 9m25s; Backend Tests pass 10m16s; Documentation Lint pass 6s; Frontend Tests pass 1m23s; Security Scan pass 8m51s; E2E Smoke fail 9m6s: `[Errno 28] No space left on device` in "Install backend dependencies" (CI-DISK, job 109566187890) |

### Reviews
| Reviewer | Verdict | Notes |
|---|---|---|
| code-reviewer (opus) | APPROVE (loop 1) | Same 21 files as a plain A+main merge; only the 5 conflicted files differ from merge-tree; union lossless; SLOT-RULE met |
| security-reviewer (opus) | CHANGES, 1 MAJOR (doc, out of scope) | CARE-QUOTE UPDATE is scoped to the profile DB and to this document; audit kept; recovery code is state-only, no storage/URL/log writes |
| Codex adversarial-review | needs-attention, 2 medium | (1) CAREQ-004 audit commit not proven → **fixed** `d116931`; (2) recovery-code mutation cache → flagged |

### Open findings (not fixed; outside P1 file scope; all flagged in the PR body)
**Needs an owner decision**
1. **[MAJOR] `docs/compliance/data-privacy.md:185`** (A text) says "Observations and chunks are removed with it (ORM cascade)".
   - Cause: `Observation.interpretation` has no cascade (`models/observation.py:106-108`), and `lab_interpretations.observation_id` is NOT NULL (`models/interpretation.py:50-55`). Deleting a document with an interpreted observation therefore raises an IntegrityError / 500.
   - Effect: `doc_path.unlink()` (`api/documents.py:1874-1875`) runs before the commit. The file is destroyed, but the row, the entity quotes and the care-task quote survive, and no audit row is written. The reviewer reproduced this; L1 confirmed the model and column definitions.
   - This bug predates the branch. `docs/plans/2026-09-08-sql-fk-001-foreign-key-audit.md:59` has the same wrong claim.
   - Needs: a doc gate, plus a ticket for the cascade fix and for moving the unlink after the commit.
2. AGENT-PASS-LINE: `CLAUDE.md:31` "all 1288 pass" and `AGENT.md:76` "1269 pass in CI, 1268 without", next to 1296 collected.
3. `CLAUDE.md:50` "Eight failure modes", but recurring-failures.md now has 9 sections. Needs a governance-text gate.
4. `RecoveryCodeCard.tsx:48-52` + `services/profiles.ts:264-273`: TanStack mutation cache holds `{profileId, password}` and `recovery_code` in memory until gcTime (5 min). No persister exists. The component comment says otherwise. Fix: `gcTime: 0` or `reset()`.

**Follow-ups (MINOR)**
1. `MedicationDetail.tsx:366`: false "No lab results" while loading or on error.
2. `RecoveryCodeCard.tsx:43`: the replace warning is hidden while `useProfiles` loads. Also, a wrong-password 401 logs the user out (`services/api.ts:66-68`).
3. `types.ts:614`: `CorrelationContext` is dead.
4. `e2e/recovery-code.spec.ts:35-39`: no storage assertion.
5. The data-privacy "Known gap" paragraph leaves out FTS `search_records`, the page-image cache (300 s) and `chat_turns`.

### Post-merge (Task 7 + Task 8 Steps 1-4)
**NOT RUN.** PR #24 was still OPEN when the 3 h poll ended (last check 14:52:58, `{"mergedAt":null,"state":"OPEN"}`). `../hc-p1-post` was not created.

**RESUME POINT (next L1):**
1. `gh pr view 24 --json state` → MERGED, then `git fetch origin`.
2. `git worktree add --detach ../hc-p1-post origin/main`.
3. Run plan 01 Task 7 Steps 1-3 and Task 8 Steps 1-4 there:
   - Use the venv and `HF_HUB_OFFLINE=1`.
   - Expect `1296 tests collected` and both slots at 1296.
   - Expect poison proofs 2/2/0 and drift 0.
   - Frontend: `RecoveryCodeCard.test.tsx` on Windows.
4. Task 8 Step 5 is for L0.

---

## Phase 4 — CI-DISK (L1 run 2026-09-30)

| Item | Value |
|---|---|
| PR | https://github.com/BrooklynD23/HealthCentral/pull/25 |
| Branch / head | `ci/cpu-torch-ci-disk` @ `1abb4ef` (base `origin/main` `b50a7da`) |
| Worktree | `/mnt/c/Users/DangT/Documents/GitHub/hc-ci-disk` |
| Plan | `docs/plans/2026-09-30-CI01-cpu-torch-ci-disk.md` (brought in from `origin/docs/exec-wave1-ledger-2`) |
| Gate used | CI-DISK-FIX + L0 scope note (security job `ci.yml:115` unchanged) |
| Collected delta | 0 (no tests, no product code) |

### Commits
| Commit | What |
|---|---|
| `973e9fc` | plan + regenerated `docs/INDEX.md` (1297 lines) + `docs/_link_graph.json` |
| `1abb4ef` | `ci.yml`: `pip install torch --index-url https://download.pytorch.org/whl/cpu` before `pip install -r` in backend-tests (`:48`), agent-evals (`:165`), e2e-tests (`:200`). `:115` untouched |

### Task 2 local proof (scratch venv in scratchpad, CPython 3.11.16)
```
uv pip install torch --index-url https://download.pytorch.org/whl/cpu   -> + torch==2.14.1+cpu
uv pip install -r src/backend/requirements.txt                          -> OK (tail: + zopfli==0.4.3)
uv pip list | grep -ci nvidia                                           -> 0
python -c "import torch, sentence_transformers; print(torch.__version__)" -> 2.14.1+cpu
```
Docs gates: `docs_lint.py` → `Docs lint passed.` (rc 0); `generate_docs_index.py --check` → `docs/INDEX.md and docs/_link_graph.json are fresh.` (rc 0). `yaml.safe_load(ci.yml)` OK. `git diff --stat origin/main..HEAD` → 4 files (ci.yml, INDEX.md, _link_graph.json, plan).

### Review
code-reviewer (opus): **APPROVE**, 0 CRITICAL/HIGH/MEDIUM, 2 LOW (not fixed, out of plan scope):
1. LOW `ci.yml:49,168,204`: torch is unpinned and nothing checks after install that the `+cpu` build survived. A future dependency upper bound on torch could bring the CUDA wheel back without warning. Optional follow-up needs an owner answer: add `python -c "import torch,sys; sys.exit(0 if '+cpu' in torch.__version__ else 1)"` after the requirements install.
2. LOW plan line refs are pre-change (`:48/:165/:200/:115` are now `:50/:169/:205/:117`). Record only.

### PR CI (run 36781121769, head `1abb4ef`) — `gh pr checks 25`
```
Agent Eval Gate      pass  6m40s  job 110111341389
Backend Tests        pass  7m17s  job 110111341271
Documentation Lint   pass  7s     job 110111340883
E2E Smoke Tests      pass  7m51s  job 110113890519
Frontend Tests       pass  47s    job 110111341320
Security Scan        pass  8m21s  job 110111341220
```
E2E Smoke evidence (`gh api repos/BrooklynD23/HealthCentral/actions/jobs/110113890519/logs`, 3897 lines, `grep -c nvidia` → 0):
```
L521  Downloading torch-2.14.1%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl (196.2 MB)
L536  Successfully installed ... torch-2.14.1+cpu typing-extensions-4.16.0
L654  Requirement already satisfied: torch>=2.2 in ... (from sentence-transformers>=2.2.0->-r src/backend/requirements.txt (line 73)) (2.14.1+cpu)
L899  Successfully installed Mako-1.4.3 PyJWT-2.15.1 ...        (Install backend dependencies done; no Errno 28)
L900  ##[group]Run npx playwright test --project chromium
L1173 Running 28 tests using 1 worker
L3873   3 skipped
L3874   25 passed (1.2m)
```
Main's specs pass under Playwright (28 run: 25 pass, 3 skipped). The dot reporter does not name the 3 skipped specs. This is the baseline for #24's E2E.

**Merged:** #25 MERGED 2026-09-30T22:14:10Z → `origin/main` @ `19f85b0` (verified with `gh pr view 25 --json state,mergedAt,mergeCommit`).

---

## Phase 5 — refresh P1 PR #2 (#24) onto CI-DISK main (L1 run 2026-09-30)

| Item | Value |
|---|---|
| PR | https://github.com/BrooklynD23/HealthCentral/pull/24 |
| Branch / head | `merge/asclexis-repo-audit-349pjq`: `d116931` → **`31574fb`** (normal push, no force) |
| Worktree | `/mnt/c/Users/DangT/Documents/GitHub/hc-p1-a` |
| Incoming | `973e9fc`, `1abb4ef`, `19f85b0` (CI-DISK only) |

### Step 1 — merge (not rebase)
```
git merge-tree --write-tree --name-only HEAD origin/main -> 5f375f6…, rc 0, no conflicted files
git merge --no-edit origin/main                          -> 31574fb; 4 files (ci.yml, INDEX.md, _link_graph.json, CI01 plan), no conflicts
generate_docs_index.py --check                           -> docs/INDEX.md and docs/_link_graph.json are fresh.  (no regeneration needed)
```

### Step 2 — measured (venv Py 3.11.16, `HF_HUB_OFFLINE=1`, `__pycache__` cleared, pipefail)
| Check | Output |
|---|---|
| `pytest tests/ --collect-only -q` | `1296 tests collected in 77.03s (0:01:17)` |
| `pytest tests/ -q -rf` | `1296 passed, 58 warnings in 283.99s (0:04:43)`; rc 0; FAILED list empty |
| `git status --short` | empty (0 lines) |
| new `*.db` (untracked or ignored) | none |
| `docs_lint.py` | `Docs lint passed.` rc 0 |
| `generate_docs_index.py --check` | fresh, rc 0 |
| `harness_drift_check.py` | `Harness drift check passed.` rc 0 |

### Step 3 — PR CI (run 36785890938, head_sha `31574fb…`) — `gh pr checks 24`
```
Agent Eval Gate      pass  8m15s   job 110127076591
Backend Tests        pass  9m2s    job 110127076558
Documentation Lint   pass  8s      job 110127076592
E2E Smoke Tests      pass  11m15s  job 110129907034
Frontend Tests       pass  1m23s   job 110127076552
Security Scan        pass  9m8s    job 110127076229
```
E2E Smoke evidence (`gh api …/actions/jobs/110129907034/logs`, 4233 lines, `grep -c nvidia` → 0):
```
L572  Successfully installed ... torch-2.14.1+cpu typing-extensions-4.16.0
L937  Successfully installed Mako-1.4.3 PyJWT-2.15.1 ...        (no Errno 28)
L938  ##[group]Run npx playwright test --project chromium
L1211 Running 30 tests using 1 worker
L4209   3 skipped
L4210   27 passed (1.8m)
```
Compared with main's baseline (#25 run: 28 tests, 25 pass, 3 skip), #24 adds 2 Playwright tests and both pass. There are 0 failing specs, so no systematic-debugging was needed.

### Step 4 — merge wait (timed out, NOT merged)
- Polled `gh pr view 24 --json state,mergedAt` every ~9 min from 22:50Z. Every poll returned `OPEN`. The last two polls returned at 00:36:03Z and then 03:35:53Z: the host likely suspended between them.
- Final check 03:39:12Z: `OPEN - 31574fb…`; `origin/main` still `19f85b0`; `hc-p1-a` tree clean (0 lines).
- The 3 h window has passed, so **plan 01 Task 7 Steps 1-3 and Task 8 Steps 1-4 were NOT run**, and `../hc-p1-post` was not created.

### RESUME POINT (Phase 5)
1. Owner merges #24 (head `31574fb`; 6/6 checks green; E2E 30 run, 27 pass, 3 skip).
2. Then `git fetch origin && git worktree add --detach ../hc-p1-post origin/main` and run plan 01 Task 7 Steps 1-3 and Task 8 Steps 1-4 with `~/venvs/asclexis-311` and `HF_HUB_OFFLINE=1`. Expect 1296 collected in both slots, poison proofs 2/2/0, drift 0. Run the frontend `RecoveryCodeCard.test.tsx` through `powershell.exe`. Task 8 Step 5 is for L0.

### Open findings (not fixed)
1. LOW (#25 review): CI torch is unpinned, with no `+cpu` assertion after install. A future dependency bound could bring the CUDA wheel back without warning. Needs an owner answer.
2. Record: the CI01 plan's line refs are pre-change (`:48/:165/:200/:115` → `:50/:169/:205/:117`).
3. Record: main and #24 each skip 3 Playwright specs. The dot reporter does not name them. They are the same count on both sides, so they are not introduced by #24.
