**GATED** — dependencies P0-B, P0-B2, P1 and W-1 Task 6 are on `origin/main`; sign-offs O-1…O-7 are unsigned, the plan has never been audited or Codex-reviewed, and its own refresh triggers have fired.

# SHOWCASE — CS4610 senior-report showcase update (short readiness pack)

**Measured:** 2026-10-07, worktree `hc-scaffold` @ `8d6f02e`, `origin/main` = `6b4dd84`.
**Plan:** `docs/plans/2026-09-27-senior-report-showcase-plan.md` (963 lines; tasks 0-10 at `:602-826`; sign-offs §13 `:857-867`).
**Kind:** DOCS + a rehearsed demo. No product code.

## 1. Readiness verdict

| Item | State |
|---|---|
| P0-B, P0-B2 | merged, PR #19 |
| P1 | merged |
| W-1 Task 6 (owns `CS4610_Report_Demo/README.md:20-23`; must precede the plan's Task 5) | merged: `dde5ea4` inside PR #35 |
| Sign-offs O-1…O-7 | UNSIGNED (`:861-867`) |
| Audit | none: "not audited in Wave 3a/3b" (program `:451`); P0-B2 included it "as-is (unaudited, labelled)" (`owner-decisions:28`) |
| Showcase date / `{FREEZE_DATE}` | not set (plan `:241`, `:254`, O-6) |

## 2. Task 0 evidence (measured)

| Check | Command | Output |
|---|---|---|
| post-P1 (plan Task 0 Step 1) | `git merge-base --is-ancestor 7b2ff1f origin/main; echo $?` / `… 692fdf3 …` | 0 / 0 |
| P0-B / P0-B2 | `git merge-base --is-ancestor 36b2ff2 origin/main; echo $?` | 0 |
| W-1 Task 6 | `git merge-base --is-ancestor dde5ea4 origin/main; echo $?` | 0 |
| W-1 Task 6, plan's own probe | `git show origin/main:CS4610_Report_Demo/README.md \| grep -c "written new"` | 1 (≥ 1 = landed) |
| Plan and inputs tracked | `git ls-files` for the plan, `audit/2026-09-25/asclexis-showcase.html`, `docs/capstone-report/claims-ledger.md` | all 3 present |
| Plan Task 0 Step 2 probe | `git log --oneline origin/main --grep="2026-09-27-W01"` (and W02, W03, W04, W06, W08, S01, W10, W11a) | **0 for all 9**, although W-1 (#35), W-6 (#32), S-1 (#29) and W-11a PR-2/PR-4 (#33, #39) are merged. Commit subjects say "(W-1 …)", not the plan file name |
| Start gates | `docs_lint.py`, `generate_docs_index.py --check` | pass, exit 0 |

Refresh triggers in the plan header (`:5`) that have fired since 2026-09-27:

| Trigger | Fired by |
|---|---|
| "P1 merges (re-verify every `main@40f590e` line below)" | PRs #21, #24 |
| "any of W-1, W-8 or W-11a edits `claims-ledger.md`" | `dde5ea4`, `108362f` (W-1), `6bd5dce`, `85f0948` (W-11a PR-4) |
| "any of P2, S-1, W-2, W-3, W-4, W-6 or W-8 merges (each upgrades a claim in §9)" | P2 (#31), S-1 (#29), W-6 (#32) |

So every `main@40f590e` line number, every measured figure (collected count is now 1370; vitest 195 / 34 files; Playwright 31 listed) and the §9 claim states in the plan are stale until re-measured. Not re-measured in this pack: UNMEASURED.

No 2026-10-07 owner row concerns SHOWCASE.

## 3. Owner questions still to ask

1. **SHOW-DATE.** "When is the showcase, and on what date do claims freeze?" Free answer; it sets `{FREEZE_DATE}` and O-6. Nothing in the plan can finish without it.
2. **SHOW-AUDIT.** "This plan was never audited and its figures predate Waves 1-3. Before anyone runs it:"
   - A. Refresh pass first: re-measure every cited line and figure at current main, then a Codex plan review (owner direction 2026-10-07 for large plans), then run. **(recommended)**
   - B. Run as written; the executor stops at each mismatch.
   - C. Defer the showcase work until W-2 / W-3 / W-4 land, so fewer claims are "not yet implemented".
3. **O-1, O-2, O-5 (publish scope).** "Approve: a new dated showcase copy at `docs/capstone-report/asclexis-showcase-{FREEZE_DATE}.html` with the 2026-09-25 page left byte-identical (O-1); the scope-note text in `CS4610_Report_Demo/README.md`, Edits 1-4 and 6 (O-2); outline §6a with the `CASE-STUDY` verdict only (O-5)?" A. All three **(plan default: yes)** · B. Choose per item.
4. **O-3, O-4, O-7.** "Demo machine: `DEBUG=false`, `HF_HUB_OFFLINE=1`, Wi-Fi off (O-3)? Package the review evidence: TSV only, or TSV + Codex outputs + script + prompt template (O-4; plan recommends the fuller set)? Add the submission-date inconsistency note (O-7; your call, no default)?" One answer per item.

Ask-first touches: none in `src/`. The plan edits `docs/capstone-report/claims-ledger.md` (shared with W-1, W-8, W-11a; serial) and `CS4610_Report_Demo/README.md`; submitted `.docx` files are never edited (capstone maintenance rule 6).

Plan defect to carry into the refresh: Task 0 Step 2's `--grep="<plan file name>"` prints 0 for merged phases; use the merge commits from `audit/2026-09-25/waves/wave-2.md` / `wave-3.md` with `git merge-base --is-ancestor` (the plan already says not to rely on the grep alone).

Next action: ask the owner SHOW-DATE and SHOW-AUDIT.
