# Wave 2: L1-C report (W-11a PR-2, W-5, W-1), 2026-10-01

All 3 PRs are open and none is merged. Base was `origin/main` `8064244`. Each branch then merged `2e85487` (PR #27, docs only) before its END run. **No branch contains S-1 yet.**

| Phase | PR | Head | Collected START → END | END full run | CI (`gh pr checks`, at report time) |
|---|---|---|---|---|---|
| W-11a PR-2 | https://github.com/BrooklynD23/HealthCentral/pull/33 | `44df7e8` | 1296 → **1303** (+7) | 1303 passed, suite_exit=0 | 6/6 pass |
| W-5 | https://github.com/BrooklynD23/HealthCentral/pull/34 | `095cd35` | 1296 → **1299** (+3) | 1299 passed, suite_exit=0 | 5 pass, E2E pending |
| W-1 | https://github.com/BrooklynD23/HealthCentral/pull/35 | `13d84d3` | 1296 → **1304** (+8) | 1304 passed, suite_exit=0 | docs-lint pass, 4 pending |

**Environment for every END run:**
- WSL with the D9 venv `~/venvs/asclexis-311/bin/python` (3.11.16, sqlcipher 4.12.0), `HF_HUB_OFFLINE=1`, an embedding model in the local HF cache, and `flock /tmp/claude-1000/hc-pytest.lock`.
- START 1296/1296 passed was measured at `8064244` by W-5's first implementer, before the OOM crash.

**Crash note:** the host OOM killed the first 3 implementers. Their commits survived. Evidence that was lost was re-derived (W-1 RED proofs) or re-run by L1 (W-11a Steps 2–4, W-5 break-it 2/3).

## Merge order among my 3 (after S-1 and W-6)
1. **W-11a PR-2 (#33).** Tests only, no product code. CI is already 6/6 green, which proves `sqlcipher3` imports in CI, because HC-KEYCT-001 fails rather than skips there.
2. **W-5 (#34).** One `rag.py` prompt constant plus docs. The file order W-5 → W-3 → W-8 wants it in early.
3. **W-1 (#35).** Largest docs surface, plus an owner manual smoke step (Task 7 Steps 2–5).

**Every one of these collides on the CLAUDE.md:30,35 / AGENT.md:76 collected slots.** Before each merge:
1. `git merge origin/main`
2. `pytest --collect-only`
3. Rewrite the 3 slots to the measured number. The expected number is main's count plus +7, +3 or +8.
4. Run `generate_docs_index.py --check`.

S-1 (#29, +4 → 1300) lands first, so after S-1 the targets are 1307 / 1303 / 1308 if merged alone. They stack if more than one lands.

---

## W-11a PR-2: #33
**Plan:** `docs/plans/2026-09-27-W11a-test-and-gate-hardening.md`, Task 3 only.

**Gates used:**
- OG-2 = Approve: "Task 3 runs in W-11a PR-2 (Wave 2): tests only, no encryption code touched. …"
- SLOT-RULE
- D9-SRC

**Commits:**
- `d67cd71` test + slots
- `0baecf9` review fix
- `44df7e8` merge of `2e85487`

**Files:** `src/backend/tests/security/test_vault_ciphertext.py` (new; the plan block verbatim, plus 1 line), `CLAUDE.md`, `AGENT.md`.

**Commands and output (L1):**
1. `HC_REQUIRE_SQLCIPHER=1 pytest tests/security/test_vault_ciphertext.py -v -rs -k hc_keyct_` gave `7 passed`, 0 skipped.
2. Break-it, line 51 changed to `!= b"x"`, then `-k hc_keyct_003`: `1 failed`, with "Regex pattern did not match … canary found in plaintext in vault.db".
   - **This differs from the plan's predicted `DID NOT RAISE`.** The canary check catches it first. The test is RED either way, and the reviewer accepted it.
3. Windows `python.exe` 3.13 (no sqlcipher3) with `CI=true WSLENV=CI`: `2 failed` with the KEY-02 message.
   - Without `WSLENV`, the variable never reaches the Windows process and the result is `2 skipped`. That is an environment trap; it is recorded in the PR.
4. Same Windows run without CI: `2 skipped`, with the reason "Set HC_REQUIRE_SQLCIPHER=1 …".
5. Fix `0baecf9`. The leak probe printed `False sqlcipher3` before and `True sqlite3` after.
6. END: `1303 tests collected`, collect_exit=0; `1303 passed, 61 warnings in 141.55s`, suite_exit=0; `boot ok`; `Docs lint passed.`; index fresh; `Harness drift check passed.`; `git status` clean; no `*.db`.

**Reviews:**
- code-reviewer: CHANGES, 1 MAJOR, verified and fixed. `open_profile_database` sets `aiosqlite.core.sqlite3 = sqlcipher3` process-wide (`core/profile_database.py:296-298`), so the fixture now restores it at teardown.
- security-reviewer: APPROVE, 0 CRITICAL / 0 HIGH.

**Skipped / deferred:** Task 10 docs commit (matrix KEY-02, contract C-KEY-1, TASK_LIST note). The proposed row text is in the PR body.

**Open findings:**
1. MEDIUM: the vault uses `journal_mode=delete`, so the `vault.db*` sidecar canary scan only ever sees `vault.db`.
2. MINOR: the canary check and the stdlib "not a database" check have no negative control of their own.
3. MINOR: `vaults/<id>/docs/` is not covered.
4. MINOR: the plan text predicts the wrong RED message.

---

## W-5: #34
**Plan:** `docs/plans/2026-09-27-W05-citation-marker-prompt.md`, Tasks 0–3.

**Gates used:**
- D11: "Keep [cite:N] as the validated marker; document [YOUR_RESULTS:N]/[REFERENCE:N] as context labels; remove the contradictory prompt line. … no validator edit."
- SLOT-RULE
- D9-SRC

**Not done:** the §12 clause is unsigned. GOV-D11 (`CLAUDE.md:62`) is W-10's and was not touched.

**Commits:**
- `52278f5` `fix(rag)` (rag.py :128/:133/:134, test, slots)
- `6a9ecb0` docs (4 sections + §15)
- merge of `2e85487`
- `095cd35` §15 log update (L1)

**Commands and output:**
1. HC-CIT RED before the fix: `3 failed` ("found 4", "carries 4", `['[REFERENCE:1]', '[YOUR_RESULTS:1]']`).
2. Break-it 1/3: `3 failed`.
3. Break-it 2/3: the in-worktree edit was denied by the harness classifier, so L1 ran it in a scratch `git archive` copy: `1 failed, 2 passed`, "carries 2 citation-format instructions". The reviewer reproduced it.
4. Break-it 3/3: 003 RED `['[cite:1]']`.
5. END:
   - Collected and run: `1299 tests collected`; `1299 passed, 50 warnings in 106.93s`, suite_exit=0; boots.
   - `agent_eval_gate.py`: `Agent eval gate: PASS`, exit 0 (START exit 0).
   - Docs gates: lint passed; index fresh; drift passed.
   - Scope vs origin/main: exactly the 9 owned files. The ask-first / claim_extractor / frontend / capstone diff is empty. `rag.py` has 2 hunks. 0 `cite these in` hits.

**Review:** code-reviewer APPROVE, 0 blocker, 0 major, 1 minor (the §15 log cell), fixed in `095cd35`.

**Open findings:**
1. Live-model compliance is UNMEASURED (plan §4.1).
2. F-3: the chip numbering differs from the text `[N]` (pre-existing).
3. Frontend tsc/vitest UNMEASURED (no frontend change; WSL stalls).
4. Hand-off: C-SAFE-5 "Enforced at" changes from none to `test_rag_citation_prompt.py`. SAFE-08 stays partial until W-10 and the P4 rows land.

---

## W-1: #35
**Plan:** `docs/plans/2026-09-27-W01-harness-agents-branch-a.md`, Tasks 0–6, Task 7 Steps 1/1b/6, Task 8 Steps 2–4, and Task 9.

**Gates used:**
- D1 = A
- D1-scope = "Author all five named in harness.md, including windows-bootstrap-engineer (bounded write) and agentic-roadmap-researcher."
- P1-DRIFT
- OG-3 = Approve Task 9
- SLOT-RULE
- D9-SRC

**Commits:**
- `9345cc3` C1: 5 agents, `.gitignore`, HC-AGENTS-001..007, slots 1303
- `7643c94` C2: harness/roadmap
- `dde5ea4` C3: CS4610 README, ledger H5/H6
- `54ea75f` C4: HC-AGENTS-008, slots 1304
- `5ae6434` execution record
- `108362f` review fixes
- `13d84d3` merge of `2e85487`

**Commands and output:**
1. RED proofs, re-derived in a scratch `git archive` + `git init` copy after the crash:
   - 001, gitignore line removed: "still ignored …"
   - 002, `!.claude/*`: "un-ignore is too wide"
   - 003, extra file
   - 004, BOM
   - 005, `Write` on a scanner
   - 006, write_scope widened
   - 007, ask-first list removed
   - 008 gate: `unnamed=1`, `drift=1`
   - 008 test in the disposable `hc-w1-break` worktree: `1 failed, 7 deselected`, "does not name by full path: ['verification-engineer']"
2. phi_gate:
   - `phi_gate_exit=0`
   - 7 planted patterns, each `exit=1`
   - `after_cleanup_exit=0`
   - `find_error_exit=1`
   - smoke worktree removed
3. Task 0 Step 6: dev.ps1 AST parse gives `0`.
4. END:
   - Collected and run: `1304 tests collected`; `1304 passed, 50 warnings in 109.37s`, suite_exit=0; boot ok.
   - Docs gates: lint passed; index fresh; drift passed; `Repo hygiene passed.`
   - `git ls-files .claude/agents` gives 5. The diff vs origin/main is 14 files, all from the plan's list.

**Reviews:**
- code-reviewer round 1: CHANGES, 2 MAJOR, both verified:
  1. Ledger H5 went stale after C4.
  2. `git diff --name-only` cannot see files the agent creates. Fixed by changing to `git status --porcelain --untracked-files=all` in harness.md:28, the agent body and the docstring.
- Round 2: APPROVE.

**Skipped:**
- W-1's own OG-1 (hook), OG-2 (Bash for verification-engineer; this is not the owner-decisions OG-2 row), OG-4 and OG-5 are unsigned and listed in the PR.
- Task 6 Step 3 matrix/contract edits were not applied, because a concurrent editor (L0's Wave-1 close) was working on them. The proposed text is in the PR.
- Task 7 Steps 2–5 need an interactive `/agents` session, so they are UNMEASURED and left as an owner manual step.
- Task 8 Step 6 runs post-merge.

**Open findings:**
1. **"Cannot create files" is unverified.** `Edit` may create a file when `old_string` is empty. This is open until the Task 7 Step 4 smoke runs.
2. Task 0 Step 5: the F3/F5 quoted wording is no longer on the Claude Code docs page, but the substance holds. The page now points to `permissions.deny`, which bears on OG-5. I judged this not a STOP; L0/owner may re-read.
3. HC-AGENTS-001/002 give a misleading message when git exits 128. The tests still fail.
4. Matrix GATE-09 (`specs-compliance-matrix.md:153`) still says "absent".
5. The plan's code blocks still say `git diff --name-only`. That deviation is logged in the PR body.

---

## Cross-phase
- **Pass-count wording (all 3 PRs):** `CLAUDE.md` "all 1288 pass" and `AGENT.md` "1269 pass in CI, 1268 without" were left untouched under SLOT-RULE. They contradict each other and the measured 1296–1304 full passes. This is the existing owner item AGENT-PASS-LINE.
- **No ask-first file edited in any phase.** No gate was signed. Nothing was merged.
- **Worktrees** `../hc-w1`, `../hc-w5` and `../hc-w11a-pr2` are clean (`git status --short` empty). The PR body drafts are at `../w1-pr-body.md`, `../w5-pr-body.md` and `../w11a-pr2-pr-body.md` (outside every repo).

**Next action:** after S-1 (#29) merges, run `git merge origin/main` in `../hc-w11a-pr2`, re-measure `--collect-only`, rewrite the 3 slots, and push.
