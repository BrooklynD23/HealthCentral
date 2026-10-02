# Wave 2: L1-B (W-6 external runner hardening)

**PR:** https://github.com/BrooklynD23/HealthCentral/pull/32 is open and ready for review. It is not merged. It goes 2nd in the merge order, after S-1.
**Branch:** `fix/w6-external-runner-hardening`, worktree `../hc-w6`. Head is `487a494`. origin/main `2e85487` is merged in (`1b3421d`).
**CI at open:** `gh pr checks 32` showed 5 jobs pending: Agent Eval Gate, Backend Tests, Documentation Lint, Frontend Tests, Security Scan.

## Commits
| sha | subject |
|---|---|
| 98a5113 | fix(external-runner): make strict redaction unconditional outside break-glass (D12). Slots 1296→1300 |
| 46a8e9b | fix(external-runner): audit break-glass before dispatch and fail closed (D12). Slots →1308 |
| c093bc6 | feat(model-settings): report break-glass redaction state to the UI (D12). Slots →1313 |
| 1b3421d | Merge origin/main (2e85487, docs only) |
| a00f934 | feat(settings): warn when break-glass weakens external API redaction (D12) |
| 6a56d14 | feat(assistant): show break-glass warning on the chat page (D12, Q3) |
| 487a494 | test(assistant): make HC-EXT-005d wait for the external-api query (review) |

## Gates used
Each gate is copied verbatim from owner-decisions:
- **D12:** "Keep the opt-in feature as a documented ModelRunner exception, but make strict redaction unconditional (remove the dev bypass; keep break-glass only with audit + UI warning). Amend CLAUDE.md to name the exception." The CLAUDE.md amendment is W-10's job and is not in this PR.
- **W6-Q4 = Covered:** this gate licenses the `core/external_runner.py` edits, the one-test change to `test_redaction.py`, and the field plus import in `model_settings.py`. The encryption handler is untouched.
- **BG-REACH:** keep the current meaning.
- **SLOT-RULE**, signed.
- **D9-SRC:** venv 3.11.16.

**Q3 / Q5 status (owner, 2026-10-01, via L0):**
- **Q3 = "Settings + chat page".** This differs from the plan default. It was applied as a recorded plan amendment, Task 4b (6a56d14).
  - The file list widened by exactly 2 paths: `src/frontend/src/pages/ExplainAssistant.tsx` and `src/frontend/src/__tests__/ExplainAssistant.test.tsx`.
  - The chat warning renders only when `use_external_api === true && redaction_break_glass === true`.
  - Tests: HC-EXT-005/005b/005c/005d.
  - I did not fill in the plan §11 sign-off lines.
- **Q5 = "As written".** The copy is unchanged from the plan.

GOV-BG is untouched (it belongs to W-10).

## Task 0 (re-derivation)
1. Ancestry: `post-P1-ok`. Base was `8064244`, status was clean, and the last commit to `external_runner.py` was `4eab43c`. `~/venvs/asclexis-311/bin/python --version` → `Python 3.11.16`.
2. Anchors:
   - `external_runner.py:201` and `:236`, `model_settings.py:208`, and `modelSettings.ts` are all byte-identical to B@7b2ff1f (`git diff --stat 7b2ff1f HEAD` was empty).
   - `SettingsPage.tsx` moved +1 line because of `RecoveryCodeCard`.
   - There were 0 HC-EXT IDs.
3. Codex plan review r4 was **not** run, because re-derivation did not change any step.
4. W-10 is a soft dependency (plan §5). W-6 code can merge without it. D12 and LOCAL-04 are not reported closed until W-10 lands. **No STOP.**

## Commands and outputs
All runs used the worktree and `HF_HUB_OFFLINE=1`.
| Check | START (8064244) | END (487a494) |
|---|---|---|
| `pytest tests/ --collect-only -q -p no:cacheprovider` | `1296 tests collected`, exit 0 | `1313 tests collected in 8.44s`, exit 0 |
| `flock … pytest tests/ -p no:cacheprovider -q` | `1296 passed`, exit 0 | `1313 passed, 54 warnings in 110.05s`, exit 0 (END ran after the merge, before 487a494, which is frontend-only) |
| targeted backend (8 files) | 63 passed (4 files) | `114 passed` |
| `python -B -c "from main import app"` | — | `ok` |
| Windows `npx tsc --noEmit` | exit 0 | exit 0 |
| Windows `npx vitest run` | run 1: `1 failed / 178 passed (179)`, failing name not captured; run 2: `31 files, 179 passed` | `32 files, 186 passed`, exit 0 (before 487a494); after 487a494, the 2 targeted files gave `28 passed` and tsc exit 0 |
| `scripts/docs_lint.py` / `generate_docs_index.py --check` | — | `Docs lint passed.` / `fresh` |
| scope: read-only paths diff | — | `0` lines |
| scope: new network lines | — | `0` |
| `test_redaction.py` removed lines | — | `1` (the expected re-added `with` line) |
| `external_runner.py` hunks | — | `-94,0 +95,52`; `-199,0 +252,7`; `-236 +295`; `-237,0 +297,21`. None fall in the encryption helpers or in `get_runner_for_request` |

**Collected count:** START 1296 → END 1313 (+17, as the plan predicts). The CLAUDE.md:30,35 and AGENT.md:76 slots read 1313.

**L1 break-it checks (my own runs):**
- Replaced `if not bypass:` at line 255 with `if False:` → `4 failed` on HC-EXT-001 (`'John Doe' left the device`).
- Injected a raise before the audit call → `5 failed, 3 passed` on hc_ext_002. HC-EXT-002 ×4 and 002d failed. HC-EXT-002b and 002c stayed green, as designed.
- Both were reverted with `git checkout`.

**Implementer RED/GREEN and break-it, as reported:**
- HC-EXT-003: RED was an unresolved import. Break-it gave `role "alert"` not found.
- HC-EXT-005: RED was 1 failed. Break-it on the guard was red.
- HC-EXT-005d after the fix: removing the `use_external_api` guard gave red.

## Reviews
- **code-reviewer (opus): APPROVE.** 0 BLOCKER, 0 MAJOR, 3 MINOR.
  - The HC-EXT-005d race (it could pass before the external-api query resolved) was verified and fixed in 487a494. A break-it proves the fix.
  - The other 2 minors asked for evidence, which is now in the PR body.
- **security-reviewer (opus): APPROVE.** 0 CRITICAL/HIGH/MEDIUM, 3 LOW (open, listed below).
- **Codex adversarial diff:** `needs-attention`, 1 [high] finding (below). Full output: scratchpad `codex-diff.txt` (session 5d93a1ca). It is not stored under `audit/…/reviews`, because that path is outside this phase's file list. L0 may copy it there.

## Open findings (not fixed)
1. **Codex [high], same as security LOW-3:** an unknown or stale `redaction_break_glass` flag hides the warning.
   - Cases: a query error, an older backend without the field, or the 30 s `staleTime`.
   - Codex recommends blocking external chat sends until the status is confirmed.
   - **Not applied.** Blocking sends changes chat send behaviour, which is beyond plan §1. The plan's HC-EXT-003c deliberately pins "absent → no warning".
   - Mitigations:
     - The flag changes only on an env change plus a restart.
     - Frontend and backend ship together.
     - Server-side audit and fail-closed behaviour do not depend on the UI.
   - **Owner decision needed:** keep as is, or open a follow-up to block or warn on unknown status.
2. **Security LOW-1:** the `SECURITY_AUDIT` WARNING line is logged before the audit write. When the write fails, a "blocked" error line follows it. This is the plan text verbatim.
3. **Security LOW-2:** no test covers the case where the real helper's `commit()` raises. 002b patches the whole helper.
4. **UNMEASURED:**
   - The manual visual check (Task 4 Step 6).
   - An audit row on a real user install (§8).
5. **Pre-existing, from the security review:** `api/assistant.py:755-758` silently swallows runner errors (privacy-safe). CLAUDE.md says "all 1288 pass" while AGENT.md says "1269 pass in CI" (AGENT-PASS-LINE, already an owner item).

## Merge notes
- Merge order: **S-1 first, then W-6.** When L0 signals, run these in `../hc-w6`:
  1. `git fetch origin && git merge origin/main`
  2. Re-run collect (with `flock` for any full run).
  3. Rewrite CLAUDE.md:30,35 and AGENT.md:76 to the new collected count (1313 + S-1's delta) in the merge or a follow-up commit.
  4. `generate_docs_index.py --check`, then push.
- Expected conflicts with S-1: none in code (S-1 owns `core/config.py`, `database.py` and `profile_database.py`). The collected-count slot lines in CLAUDE.md/AGENT.md will conflict.
- After merge, the program should record:
  - LOCAL-04 moves to tested only after W-10 (GOV-BG).
  - P5 shares `api/model_settings.py` (it goes after W-6).
  - W-2 goes after W-6 for `test_redaction.py`.
- Resource rules were followed:
  - One full backend run at END, under `flock`.
  - Implementers ran targeted tests only.
  - One L2 agent at a time after the resume.
- `git status --short` in `../hc-w6`: empty, with no `*.db` files.

Next action: owner merges S-1 (#?), then L0 messages L1-B to merge origin/main into #32 and re-measure the slots.

## Update: post-S-1 merge (2026-10-01)
1. Merged origin/main `040cf8c` (S-1) into the branch. The merge commit is **`31e5b22`**, now the PR head.
2. The CLAUDE.md and AGENT.md count-slot conflicts were resolved by measuring. The collect run printed `1317 tests collected in 17.85s`, exit 0. Slots CLAUDE.md:30, :35 and AGENT.md:76 now read 1317.
3. Docs gates:
   - `generate_docs_index.py --check`: `docs/INDEX.md and docs/_link_graph.json are fresh.`, exit 0.
   - `docs_lint.py`: `Docs lint passed.`, exit 0.
4. Full suite under flock: `1317 passed, 49 warnings in 199.30s (0:03:19)`, exit 0. Afterwards `git status --short` was empty.
5. Pushed with a normal push (`487a494..31e5b22`).
6. Added the owner decision **"Keep plan, register item"** to the PR body. It covers open finding 1, registered as **BG-WARN-STALE**.
   - `gh pr edit` failed on the Projects-classic GraphQL error, so the body was updated with `gh api -X PATCH`.
7. `gh pr checks 32`: 6/6 pass.
   - Agent Eval Gate 8m30s
   - Backend Tests 9m50s
   - Documentation Lint 9s
   - E2E Smoke Tests 10m52s
   - Frontend Tests 1m26s
   - Security Scan 9m29s
