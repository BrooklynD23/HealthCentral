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
