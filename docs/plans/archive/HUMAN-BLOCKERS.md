# Human blockers — Asclexis (HealthCentral)

Owner-only items that L0 deferred. L0 keeps this file updated as new blockers appear. Each item says **why it needs you**, **what unblocks it**, and **the exact command/steps**.

Last updated: 2026-11-11 (L0 session after the HANDOFF-2026-11-11 handoff)

Repo path below = `/mnt/e/Programming/Github Repo/HealthCentral`. Run `gh` from anywhere inside it.

---

## Priority for the investor demo

### B1. SQLCIPHER-WHEEL: the "encrypted vault" claim is false on Windows (MVP P0)
- **Why you:** encryption change plus security review, and three owner gates are open. SQLC-OLD-VAULTS was answered 2026-11-05. SQLC-WHEEL-DIFF is a merge gate: you see the exact diff before it merges.
- **Blocked by:** B2 (#316 must merge first, because it shares `dev.ps1`/`dev.sh`).
- **Your answer already recorded:** "switch to sqlcipher3 for windows + keep whatever works on Linux on Linux".
- **To unblock:** finish B2, then tell L0 "build SQLCIPHER-WHEEL". L0 will bring you the SQLC-WHEEL-DIFF question with the diff.
- **Demo workaround (until fixed):** demo on Linux/WSL, or do not claim on-disk encryption when demoing on Windows.

### B2. DONE 2026-11-13 (owner ran #316 on Windows, marked ready) — PR #316: Windows fresh-laptop launcher (DEV-PS1-FIRSTRUN, LLAMA-WHEEL-INDEX, DEV-EMB-FETCH)
- **Why you:** it needs a real Windows session to verify; agents cannot drive one.
- **Steps (on Windows, in a fresh clone):**
  ```powershell
  git fetch origin; git checkout fix/dev-ps1-firstrun-launcher-backend-health
  .\dev.bat        # first run: should install, fetch the embedding model, start backend + frontend
  # confirm http://localhost:3000 loads and backend /health is OK
  ```
- **Then:** comment the result on #316. If it works: `gh pr ready 316`, and tell L0 to merge it when green.

### B3. DONE 2026-11-12 (owner ran it; G3 now required) — Make G3 a required check
- **Wait for:** the MEDS-G-FLAKE fix to merge (see B7).
- **Command (classic branch protection):**
  ```bash
  gh api -X POST repos/BrooklynD23/HealthCentral/branches/main/protection/required_status_checks/contexts -f 'contexts[]=G3 on Production Build'
  ```

---

## Owner-parked PRs (L0 will not touch)
| PR | Row | What it needs from you |
|---|---|---|
| #264 | B-3 local advice judge | Your call on JUDGE-SWAP-ADOPT timing. It holds `api/assistant.py`, `rag.py` and `interpretations.py`, which blocks INTERP-QUESTION-SCRUB |
| #239 | RSI1-DONATE pr2 | Labelled `[blocked:claude]`. It holds `config.py`/`feedback.py`, which blocks OCR-BOOT-COST. Decide: resume, or close so OCR-BOOT-COST can build |
| #316 | launcher | See B2 |

## Ask-first rows awaiting an owner decision
| Row | Question for you | Source |
|---|---|---|
| AUTO-LOCK-UNUSED (auth) | `core/config.py:54` `auto_lock_timeout_minutes` has no reader. Implement auto-lock, or delete the setting? | queue.md:552 |
| BACKUP-RESTORE-JOURNAL (sealed keys) | `scripts/backup.py:513` manifest write is not atomic, and `:718-723` restore leaves a hot `-journal`. Approve a fix (atomic write plus a journal checkpoint)? | queue.md:553 |
| MED-NAME-LIST | Held "Hold for RxNorm". Supply a real RxNorm extract (or approve a download source), and L0 will swap out the model-written 461-name list | owner-decisions, 2026-11-10 |
| Gemma model URLs | `model_selector.py:60` has PLACEHOLDER URLs (CLI only). Provide the real repo URLs, or approve removing the option | demo scan 2026-11-11 |

## Housekeeping decisions (no demo impact)
**Origin branches with unmerged commits.** Keep or delete each one:
```
chore/e-3a-ruff-cleanup
docs/post-merge-batch-2026-10-17-5
docs/w4-plan-amend
fix/audit-db-locked-settings-lock-repro
test/para-round2-measure
test/uig006-pass3-flake-pass3-fetch-timing   # holds the older UIG006-PASS3-FLAKE attempt; keep until that row is built
docs/batch-1111c                             # merged; safe to delete
```
Delete with: `git push origin --delete <branch>`

**Local worktrees with unmerged work:** `hc-audit-db-locked` (won't-fix row), `hc-uig006-pass3-flake`, `hc-stillness-probe` (uncommitted), `.claude/worktrees/wf_8f5626a3-087-4`.
- See: `git -C "<repo>" worktree list`
- Remove: `git worktree remove <path>` (add `--force` only if you are sure the uncommitted work can go)

Restore lists from the earlier cleanup: `~/hc-quiet-logs/branch-cleanup-2026-11-11.tsv` and `~/hc-quiet-logs/local-cleanup-2026-11-11.tsv`.

## Tooling limits that need you
- **`gh pr ready` on a PR that is not green** is refused by the auto-mode classifier. L0 only runs it once checks are green. If you want a PR readied earlier, run `gh pr ready <N>` yourself.
- **Unchanged from earlier handoffs:** the B-4 sealed set, the OpenWiki generation call, the rework analysis, and C-P7's reset guard.

## New since creation

### B4. Codex workspace is out of credits
- **Seen:** 2026-11-11, during the senior-report fact-check ("Your workspace is out of credits"). L0 has paused Codex use until credits return.
- **To unblock:** top up or reset the ChatGPT/Codex workspace, then tell L0 "Codex is back". The pending job is a Codex fact-check pass over PR #614.
- **Check it works:** `codex exec -s read-only --skip-git-repo-check -m gpt-5.6-sol "say ok"`

### B5. Review the senior report Phase 1 draft (PR #614)
- **Why you:** it is your report. The draft is about 13k words, with an 18-slide outline and 26 evidence gaps in `docs/capstone-report/phase1/evidence-index.md` section 2.
- **Read it:**
  ```bash
  gh pr checkout 614   # or open https://github.com/BrooklynD23/HealthCentral/pull/614
  ```
  Files: `docs/capstone-report/phase1/report-draft.md`, `presentation-outline.md`, `evidence-index.md`.
- **Gaps only you can fill:**
  - GAP 1 (user study), GAP 9 (dollar costs), GAP 16 (Supabase, Vercel, Tavily MCP and Stitch use in the May report), GAP 18 (why the audit file is named "Devin"), GAP 23 (your hours per era).
  - The material from your other projects (Phase 2 placeholders).
- **Finding to confirm:** `research/04-papers-evals.md:220` says the repo was "largely built with Devin". Git shows 1 Devin-authored commit and 3 Devin trailers, against 2563 Claude trailers (L0 re-checked these numbers). The draft says so in section 4.4. Is that the framing you want?
- **Then:** comment on #614, or tell L0 what to change. L0 keeps it a draft until you approve.

### B6. ANSWERED 2026-11-12 ("617 is merged yeah") — CONFIRM: PR #617 (K/Na seeded text) was merged 2026-11-11 22:27 PST — was that you?
- **What happened:** #617 was marked ready and merged 31 s later under the BrooklynD23 account (merge `3e7ee3d7`). No L0 tool or agent ran a ready or merge on #617 (L0 searched the session logs). If you merged it from the GitHub page, that is your KB-CONTENT-YES-2 sign-off; reply "B6: yes, I merged it". If you did NOT, say so at once and L0 will treat it as an unexpected merge and prepare a revert PR for you to approve.

#### Original B6 text (gate KB-CONTENT-YES-2)
- **Why you:** you approved adding the rows on the condition that you review the exact values and text in the diff. The thresholds equal the app's existing default table (K 2.5/6.5, Na 120/160 mmol/L), so no alarm boundary moves. The descriptions and interpretation sentences were written by the agent.
- **Status: READY FOR YOU** (head 3529f6f9). The Fable fixes are applied and L0 has reviewed them; the full suite is green apart from the 5 known env failures. The source is no longer typed as a clinical guideline.
- **Decide in the PR body's "Owner review required at merge" section:**
  1. Every seeded sentence: approve or edit.
  2. "should be reviewed promptly by a healthcare provider" vs the reviewer's softer "are usually reviewed by".
  3. Source wording: the app's own default table is cited as the source. Approve "Asclexis default critical-value table", or name a real laboratory critical-values reference.
- **Then:** comment "approve as built" (or your edits) on #617.
  ```bash
  gh pr view 617 --web
  ```

### B7. ANSWERED 2026-11-12 ("Merge #621") — MEDS-G-X1: choose the fix for the /medications G3 flake (unblocks B3)
- **Diagnosed:** `~/hc-quiet-logs/staging-1111c/meds-g-diagnosis.md`. It is a harness timing issue, not a product one, and not ICU.
  - On the Reminders tab, the tab-switch render delays the stillness sampler's 20 ms timer. The largest gap has a median of 30 ms against the 40 ms bound, and CI's 41-44 ms readings are the tail.
  - In dark mode, axe runs while the theme colours are still transitioning.
- **Option A is built as draft PR #621** (`src/frontend/e2e/support/gates.ts` and `ui-dark-primitives.spec.ts` only; no product code, no bound change). Measured on the Reminders route, CI production mode:
  - x1: largest gap p50 31 → 17 ms, max 40 → 27 ms.
  - x2: 2 failures (51 and 43 ms) → 0 in 40 runs.
  - Negative control: a real 60 ms main-thread block still fails (gaps 63-67 ms, 7/7), and a 45 ms block fails before and after.
  - Every other gate spec was re-run. The remaining failures are pre-existing (they fail the same way on main) or backend-leg ECONNREFUSED.
- **Read before you approve:**
  - The fix also changes `analyse()`: the route-fade clock keeps its timer origin, which was needed to keep the existing self-test HC-UIG-007 (c) passing. So a stillness check is not strictly unchanged.
  - Sampling on every frame can hide 20-40 ms blocks that the timer alone would catch. The 45 ms and 60 ms blocks are still caught. The timer-only gap is still reported, just not gated.
  - One unexplained run: an axe `SyntaxError` in 1 of 80 dark runs. Also one new "matched no [data-t0]" failure (n=6, too few runs to call).
- **Options:**
  1. **Harness: rAF samples + theme settle (Recommended).** Measured 1/40 → 0/40 and 10/20 → 0/20. It changes the shared G1/G10 measurement for every UI gate.
  2. Count the tab switch as a page change, using the 70 ms bound.
  3. Product: `startTransition` on the tab switch (unmeasured).
  4. Known flake, re-run on red. G3 then cannot be required.
- **Then:** comment your choice on the PR. Once it merges, do B3.

### B8. Wave 1111G: four owner gates (5 rows wait on them)
- **Full text with options:** `~/hc-quiet-logs/staging-1111g/owner-gates-1111g.md`. Plan: `~/hc-quiet-logs/staging-1111g/2026-11-11-batch-1111g-plan.md`. Each row has a measured failing test on main.
- **Recommended answers, if you want to take them all:**
  1. **AVA-OLD-ROWS** (AUDIT-VIEW-ANALYTE): opening a trend or panel stores the test name (e.g. `hiv_viral_load`) in the unencrypted master DB. Recommended: **(a) stop writing it from now on; leave old rows.** Option (b) also scrubs old rows with a migration.
  2. **VERIFY-NOOP** (DOC-VERIFY-ALL-KEEPS, VERIFY-UNDO-NOOP): "Verify all" re-stamps rows you already checked, and an empty Undo still writes. Recommended: **(a) skip rows already done; refuse an empty undo with 409.**
  3. **MEM-PURGE** (PROFILE-MEMORY-PURGE): decrypted page images and cached assistant answers survive lock and logout. Recommended: **(a) clear both at lock, logout, delete and restore.**
  4. **LEGEND-LIST** (EXTRACT-LEGEND-LINES): lines such as "Target: 100 mg/dL" become fake result rows. Recommended: **(a) skip lines whose whole name is a fixed label word** (target, goal, optimal, desirable, recommended, reference, reference range, normal, normal range, therapeutic range).
- **How to answer:** tell L0, for example "1111G gates: all Recommended" or "1a 2a 3b 4a". L0 records the answers in a docs batch, then builds.
- **Already building without a gate:** FLAG-OLD-ON-REWRITE and EXPORT-COPY-QUESTIONS.

### B9. ANSWERED 2026-11-12 (all approved except K; E and M to re-confirm, see HANDOFF-2026-11-12 UPDATE 1) — Workflow optimization: 8 questions (quiet box, CI, runners)
- **Report:** `~/hc-quiet-logs/staging-1111g/workflow-optimization-quiet-box.md` (Fable PM consultant, read-only). L0 re-checked these facts: the box is 24 CPUs / 37 GiB, not the 6 vCPU / 22 GiB the slot rules assume; `ci.yml` has no `concurrency` group.
- **Already applied without a gate:** ruff before push, a diagnosis run budget (60 run-minutes), GPU windows (builder brief ADDENDUM 1111H).
- **Questions:**
  1. Is the box permanently 24 CPUs / 37 GiB? If so, may L0 raise `PYSLOTS` (3 → 6-8) and the build ceiling?
  2. May timing batches move to a fixed overnight window, with a 30-min cap on daytime quiet runs?
  3. Approve a `ci.yml` PR for E2E sharding (4 shards) plus cancelling superseded PR runs, reviewed as a diff? Estimated CI cycle 41 → about 24 min.
  4. MEDS-G-X1: the harness fix (option A)? This is the same question as B7.
  5. Should per-PR timing gates be judged in CI, with a nightly repeat job for the flake rate?
  6. Is a second runner worth paying for before the presentation? Warning: the repo is public, so do not self-host on this machine.
  7. May the local full suite be skipped on backend rows when CI runs it?
  8. **What is the stakeholder presentation date?** The roadmap split depends on it.
- **How to answer:** for example "B9: 1 yes, 2 yes, 3 yes, 5 later, 6 no, 7 no, date Dec 5".

### B10. ANSWERED 2026-11-12 (1 leave, 2 leave, 3 close, 4 fix the guard) — Wave 1111I: four owner gates (recommended answers close two without a build)
- **Full text:** `~/hc-quiet-logs/staging-1111i/owner-gates-1111i.md`. Plan: `~/hc-quiet-logs/staging-1111i/2026-11-11-batch-1111i-plan.md`. Each one has a measured failing test.
- **Recommended answers:**
  1. **RESTORE-FAIL-PURGE:** a failed or partial restore closes the vault but leaves the decrypted page images and cached answers in memory. Recommended: **(a) clear as soon as the vault closes, for every restore outcome.**
  2. **RECOVER-AUDIT-WORDING:** the "recovered" audit row claims the recovery code was rotated before the rotation happens. Recommended: **(a) drop that claim from the first row; the second row records the rotation.**
  3. **TEST-RESET-ORDER:** the synthetic test-reset route can delete files and then roll back. Recommended: **(a) leave it, close as accepted.** It is test-only, and a retry completes it.
  4. **DISCLAIMER-APPEND:** the disclaimer guard skips its disclaimer when text already mentions a healthcare provider, then withholds the card. This fails safe and no built-in text triggers it. Recommended: **(a) leave it, close as known.** This is the medical-safety module, so no edit.
- **How to answer:** for example "1111I gates: all Recommended".
- **Already building without a gate:** EXTRACT-DOB-MINORS, MEM-PURGE-RACE (L0 ruling R15) and EXPORT-DOWNLOAD-QUESTIONS, each once its predecessor PR merges.
- **Held behind parked PRs:** AUDIT-READ-ROUTES task 3. `set_llm_provider` writes no audit row, and the fix needs `test_audit_order_guard.py`, which #264 and #239 hold.

---

## Log of additions
- 2026-11-12: B6, B7, B9, B10 answered; verbatim in staging-1111e/owner-answers-1112.md. Next orchestrator records them in BATCH-1112A.
- 2026-11-11: B6 changed to CONFIRM (#617 merged outside L0 tooling).
- 2026-11-11: B10 (wave 1111I gates) added.
- 2026-11-11: B7 updated with PR #621 evidence.
- 2026-11-11: B9 (workflow optimization questions) added.
- 2026-11-11: B8 (wave 1111G owner gates) added.
- 2026-11-11: B7 (MEDS-G-X1 fix choice) added.
- 2026-11-11: B6 (K/Na seeded text review, #617) added.
- 2026-11-11: B4 (Codex credits) and B5 (senior report review) added.
- 2026-11-11: file created (B1-B3, parked PRs, 4 ask-first rows, housekeeping).
