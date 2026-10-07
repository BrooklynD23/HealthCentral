**BLOCKED** — hard dependency W-4 is not merged (no PR exists). `docs/agentic/evals.md` is ordered P4 → W-4 → G-C3a. Sections 1-3 only.

# G-C3a — HC-M06 extraction eval card (readiness pack)

**Measured:** 2026-10-07, worktree `hc-scaffold` @ `8d6f02e`, `origin/main` = `6b4dd84`.
**Plan:** `docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md`, Group G-C3a (`:1214-1525`), files `:220-226`, proposals M06-1…M06-6 `:1222-1229`, sign-offs `:1949-1950`.
**Kind:** PRODUCT (tests + one doc). Expected collected delta: +5 (plan `:1905`). Not in the orchestration §5 Codex table.

## 1. Readiness verdict

| Item | State |
|---|---|
| P1 | merged |
| P4 (`docs/agentic/evals.md` Task 1) | merged, PR #40 |
| **W-4** (legacy abstain + eval gate; edits `evals.md`) | **not merged, no PR** → BLOCKED |
| S-C3-1 (go, minimal scope) | SIGNED 2026-10-04: `owner-decisions-2026-09-27.md:48`; plan box ticked at `W11b:1949`. Both exist **only in this worktree**; on `origin/main` the row is absent and the box reads `- [ ]` |
| S-C3-2 (threshold rule) | UNSIGNED (`W11b:1950`); bites at Task C3a.2 Step 3 |

W-4's own dependency P5 is also not merged, so G-C3a sits at least two PRs away.

## 2. Task 0 evidence (measured)

| Check | Command | Output |
|---|---|---|
| P1 | `git merge-base --is-ancestor 7b2ff1f origin/main; echo $?` / `… 692fdf3 …` | 0 / 0 |
| P4-core | `git merge-base --is-ancestor 6b4dd84 origin/main; echo $?` | 0 |
| W-4 landed? | `grep -n "legacy-evals" .github/workflows/ci.yml` | 0 hits |
| W-4 PR | `gh pr list --state merged --limit 40`; `--state open` | none |
| Plan tracked | `git ls-files docs/plans/2026-09-27-W11b-*.md` | 1 file |
| S-C3-1 row on main | `git show origin/main:docs/capstone-report/owner-decisions-2026-09-27.md \| grep -c S-C3-1` | **0** (worktree: 2) |
| S-C3-1 box on main | `git show origin/main:docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md \| sed -n 1949p` | `- [ ] **S-C3-1** … Signed: ________ Date: ______` |
| S-C3-1 box, worktree | `git diff origin/main -- docs/plans/2026-09-27-W11b-…md` | `-[ ]` → `+[x]` for S-C3-1 and S-C3-3 (from `docs/wave3-close`, PR #49) |
| No-collision (Task C3a.0) | `git grep -n -i "hc_extr\|HC-EXTR\|extraction_golden\|eval-cards/extraction" -- src docs/agentic` | 0 hits |
| `docs/agentic/eval-cards/` | `ls docs/agentic/eval-cards` | does not exist |
| `evals.md` "Concrete evals" | `grep -n '^[0-9]\+\. ' docs/agentic/evals.md` | items 1-7 at `:20-26`; the plan appends item 8 (W-4 also appends one) |
| HC-M06 ledger | `feature_list.json:67-77` | `"status": "pending"`; verification steps at `:72-73` match the plan's quote |
| Collected | collect-only, D9 venv, `HF_HUB_OFFLINE=1` | `1370 tests collected in 19.88s` |

Facts measured now for the future Task 0 (they will move when P5 and W-4 land):

| Plan citation | Now | Result |
|---|---|---|
| `ExtractModule` API used by the tests: `extract_from_pdf`, `parser_version`, `_normalize_date_str`, `_extract_from_table` | `modules/extract.py:114`, `:91` (`"0.1.0"`), `:662` (staticmethod), `:195` | MATCH |
| Result fields `analyte_raw`, `collected_at` | `modules/extract.py:35`, `:44` | MATCH |
| Precedent `tests/test_visit_note_extraction.py:7-21` ("set beneath those measured numbers … never be lowered") | `:7-21` | MATCH |
| `ci.yml` B@`7b2ff1f` `:50-51` runs `scripts/run-backend-tests.sh` | `:53` | MOVED |
| `feature_list.json:71-74` verification steps | `:71-74` | MATCH |
| `tests/support/minimal_pdf.py` (to create) | `tests/support/` holds `__init__.py`, `routes.py` | free |
| Worktree name `HealthCentral-gc3a` | caller convention `../hc-gc3a` | amend at dispatch |

Prototype numbers in the plan (`{'tp': 26, 'fp': 0, 'fn': 2}`, Windows 3.13.7) are the author's; on the D9 venv they are UNMEASURED.

## 3. Owner questions still to ask

1. **S-C3-2.** "HC-M06 thresholds: the test measures precision and recall for analyte, unit and date on a synthetic golden set. Which rule sets the bar?"
   - A. Measured value − 0.05, floored to 2 decimals, never lowered afterwards. **(recommended; plan O-C3-1; precedent `test_visit_note_extraction.py:7-21`)**
   - B. Equal to the measured value (any regression fails).
   - C. Fixed numbers you give: ____.
   - Ask it at Task C3a.2 Step 3, with the D9 measurements on screen. The plan STOPS there if it is unsigned.
2. **GC3A-ORDER.** "G-C3a waits for W-4 only because both append one item to `docs/agentic/evals.md`. Run G-C3a earlier and let W-4 rebase?"
   - A. Keep the order P4 → W-4 → G-C3a. **(recommended; program shared-file rule)**
   - B. Run G-C3a now; W-4 rebases one list item.
3. **GC3A-LEDGER.** "After merge, may a follow-up commit set `feature_list.json` HC-M06 to `completed`?" A. Yes, separate commit after merge **(recommended; the plan leaves it as a follow-up)** · B. Leave `pending` until you review the eval card.

Ask-first touches: none. `modules/extract.py` is read-only in this phase (the break-it step monkeypatches it in-process). G-C3 "does NOT license" extractor changes to raise a score (plan `:127-132`).

Shared-slot note for dispatch: G-C3a changes collection (+5), so its commit rewrites `CLAUDE.md:30,34-35` and `AGENT.md:76` (ground rule 8) and merges serially with every other count-changing PR. W-10 edits other `CLAUDE.md` lines.

Next action: none until W-4 merges; then re-run §2 and ask S-C3-2 at Task C3a.2 Step 3.
