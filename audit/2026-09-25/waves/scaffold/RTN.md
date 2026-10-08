**GATED** — its dependencies are on `origin/main`; the spec's §9 owner confirmation (Q1-Q6) is unsigned, so the routine must not be created.

# RTN — Nightly doc-drift routine (short readiness pack)

**Measured:** 2026-10-07, worktree `hc-scaffold` @ `8d6f02e`, `origin/main` = `6b4dd84`.
**Spec:** `docs/plans/2026-09-27-nightly-doc-drift-routine-spec.md` (§6 guardrails `:75-85`, §9 `:156-167`).
**Kind:** OWNER (routine configuration; no repository edit, no code).

## 1. Readiness verdict

| Item | State |
|---|---|
| P0-B + P0-B2 on `origin/main` (the cloud routine checks out `origin/main`) | merged, PR #19 |
| P1 (`scripts/harness_drift_check.py` on main) | merged |
| Spec §9 "Owner sign-off" | UNSIGNED (`:167`) |
| Q6 (what to do if the session can push) | UNSIGNED (`:165`; default "do not enable") |
| Routine | not created |

## 2. Task 0 evidence (measured)

| Check | Command | Output |
|---|---|---|
| P0-B / P0-B2 | `git merge-base --is-ancestor 36b2ff2 origin/main; echo $?` | 0 |
| P1 | `git merge-base --is-ancestor 7b2ff1f origin/main; echo $?` / `… 692fdf3 …` | 0 / 0 |
| Spec on main | `git cat-file -e origin/main:docs/plans/2026-09-27-nightly-doc-drift-routine-spec.md` | exit 0 |
| Drift script on main | `git cat-file -e origin/main:scripts/harness_drift_check.py` | exit 0 |
| Gates the routine would run, on this tree | `docs_lint.py`, `generate_docs_index.py --check`, `harness_drift_check.py`, `repo_hygiene_check.py` | all pass, exit 0 |
| Collected (check C5's subject) | collect-only, D9 venv, `HF_HUB_OFFLINE=1` | `1370 tests collected` = `CLAUDE.md:30` = `AGENT.md:76` |
| Repository visibility | `gh repo view --json visibility -q .visibility` | `PUBLIC` (the owner made it public on 2026-10-06, wave-3 report) |
| §9 sign-off | `sed -n 167p` of the spec | `- [ ] Owner sign-off: ______ (date)` |

Stale lines in the spec (it was written before PR #19 merged; not edited here):

| Spec line | Says | Now |
|---|---|---|
| `:7` | "Until P0-B2 is signed and merged it is untracked on `main`" | merged; the spec is on main |
| `:171` | "Until P0-B and P0-B2 merge, `main` lacks `audit/`, `docs/capstone-report/` …; `harness_drift_check.py` is absent until P1 merges, so C3 reports `SKIPPED`" | all present on main |

UNMEASURED: whether the cloud session can push (the §6.2 dry-run probe is an owner-run step after creation with `enabled: false`); whether the cloud image has `libsqlcipher-dev` (C5).

No 2026-10-07 owner row concerns RTN.

## 3. Owner questions still to ask (spec §9, ready to ask)

1. **RTN-Q1.** "Create the nightly doc-drift routine as specified: a Claude Routine that runs the docs gates on `origin/main`, writes a report, and never commits?" A. Yes, create it disabled first and run the push probe **(recommended; required for anything else)** · B. Not now.
2. **RTN-Q6.** "If the probe shows the cloud session **can** push to GitHub:" A. Do not enable **(recommended; spec default — read-only would rest on the prompt alone)** · B. Enable anyway, accepting a prompt-only guarantee · C. Use another environment without push credentials: ____.
3. **RTN-Q4 / Q2.** "Model and schedule?" A. `claude-sonnet-5`, `0 7 * * *` UTC all year (00:00 PDT, 23:00 PST) **(recommended; spec defaults)** · B. `claude-opus-5-5`, same schedule · C. Switch the cron at each DST change.
4. **RTN-Q3 / Q5.** "Report destination and smoke run?" A. Run log only; one smoke run right after creation, audited per §6.2 **(recommended; spec defaults)** · B. Also write each report to a dated Claude Docs page (adds the Claude-Docs connector and a write tool).

Before asking, tell the owner: the repository is now public, so the routine reads nothing private; and the two stale spec lines above need a one-line refresh in a docs PR (not part of the routine).

Ask-first touches: none. No file in the repository is edited by RTN.

Next action: ask RTN-Q1 and RTN-Q6 together.
