# Workflow optimization: the quiet box and long-running tests

**Last Updated:** 2026-11-11
**Owner:** repository owner
**Status:** DRAFT (Phase 1 input). A read-only consultant review (Fable 5.2); the figures are as dated in the body, measured against `origin/main` @ `c79b7fd1`. No option here is adopted until the owner answers section 8.
**Refresh Trigger:** an owner answer to any question in section 8; a change to the CI cycle time, `PYSLOTS` or the quiet-box rules; a change to a number cited from [report-draft.md](report-draft.md) section 6.5.

**Date:** 2026-11-11 (PST). **Author:** PM consultant review (Fable 5.2), read-only. **For:** the repository owner; cited by the senior project report, section on optimizing workflows.
**Base read:** `origin/main` @ `c79b7fd1`. No repo edit, no Playwright run and no test run was made for this report.
**Source tags:** [M] = measured by me today with the command named; [L] = read from a log or repo file; [O] = operator memory or session report (a lead, not re-measured); [E] = my estimate.

## 1. Executive summary

One machine does five jobs: it builds, runs pytest, runs the timing gates, drives Playwright and hosts the local models. The quiet box makes timing measurements trustworthy by stopping everything else. That is sound for measurement and expensive for throughput.

**The three biggest sinks**

| # | Sink | Numbers |
|---|---|---|
| 1 | The quiet box freezes all pytest work while it runs | On 2026-11-11 it held every pytest slot for about 7 h: quiet batch 22 ran 00:31 to 05:28 (4 h 57 min, 41 lines) [L: `batch22-1111.out`], and the MEDS-G diagnosis ran 16:56 to 19:02 (2 h 06 min) [L: `meds-g-diag/logs` timestamps]. Agents reported pytest waits of about 90 min behind it [O: planner and docs batch, this session]. |
| 2 | Every PR and every merge pays a 41-minute CI cycle | Median 40.8 min over 157 green first-attempt runs (p10 37.2, p90 44.1); 99 runs on 2026-11-11 alone; 83 of the last 200 runs are pushes to `main` [M: `gh run list --limit 200`]. E2E Smoke is the long pole at 25.9 to 31.4 min; Backend Tests take 11.4 to 13.8 min [M: `gh run view`, 4 runs]. |
| 3 | Flakes are diagnosed by repetition, and block unrelated PRs meanwhile | MEDS-G: 333 runs by its evidence table, cause harness timing, first hypothesis refuted [L: `meds-g-diagnosis.md`]. UIDOC-006A: about 360 runs [L: its evidence table, my count]. 15 of the last 30 failed CI runs failed in E2E Smoke (9) or G3 (6) [M]; I did not triage each one as flake or real. |

**Top three recommendations**

1. **Shorten the CI cycle this week:** shard the E2E job, cancel superseded runs, and run ruff before push. Estimated cycle 41 min to about 24 min [E].
2. **Bound the quiet box:** fixed quiet windows, a run budget on every diagnosis, and a visible cap on how long pytest may wait. Then re-size the slot rules for the hardware the box actually has.
3. **Fix the two timing flakes at the harness (MEDS-G option A) before making G3 required,** and decide after the presentation whether timing gates get their own runner.

Recommendations 1 and 3 need an owner decision. Part of 2 does (see section 4).

## 2. Current-state map

### What the machine is (all [M], 2026-11-11 21:50 PST)

| Resource | Measured | What the docs assume |
|---|---|---|
| CPU | 24 logical CPUs, Ryzen 9 5900X (`nproc`, `/proc/cpuinfo`) | "6-vCPU box" (RUNBOOK §10.1; memory `wall-clock-tests-mnt-e`) |
| RAM | 37 GiB total, 32 GiB free; 49 GiB swap (`free -h`) | "22 GiB WSL box", about 2 GB per pytest slot (`scripts/pyslot.sh` comment) |
| GPU | RTX 3080, 10 GB; 3.4 GB in use, 8 % utilization, no Ollama model loaded (`nvidia-smi`, `/api/ps`) | Model host for 4 pulled models [O] |
| Load | 3.28 / 3.66 / 2.72, up 2 h 23 min (`uptime`) | Quiet threshold is 1-minute load below 1.5 (`quiet_run.sh`) |
| Disk | I/O pressure 0.00 (`/proc/pressure/io`); all 44 worktrees are under `/mnt/e` (`git worktree list`) | `/mnt/e` and slow fsync are known hazards [O] |

Two findings matter here. First, **the sizing rules are calibrated to a smaller box than the one I measured.** Three slots, a workflow cap of `min(16, CPUs - 2)` = 4, and "about 7 builds" as a ceiling all date from the 6-vCPU figure. `.wslconfig` sets only memory and swap. I could not tell when the CPU count changed, so this is an open question, not a conclusion. Second, **the GPU is blocked, not strained, by the quiet box.** In my one snapshot it was near idle. The cost is indirect: no model-host row may run while the quiet-box lock is held (RUNBOOK §10.1), and model runs must not share the box with pytest, because the 60 s generation timeout skews abstain counts [O: `local-model-host-wsl`].

### Who competes for what

| Consumer | CPU | RAM | GPU/VRAM | Disk I/O | Ports and locks |
|---|---|---|---|---|---|
| pytest (full suite) | 1 core per slot (no xdist in `requirements.txt`) | about 2 GB per slot | none | heavy on `/mnt/e` | 3 slots by default (`pyslot.sh`) |
| Quiet box (`quiet_run.sh`) | needs load below 1.5 | low | none | uses `/dev/shm` | hold lock plus slots 1 to 8; ports 3000, 4173, 5173, 8000 must be free |
| Playwright | 1 worker (`playwright.config.ts:64`) | Chromium | none seen | fsync-heavy temp profile | 3000 and 8000; one agent at a time [O] |
| Ollama / model runs | some | model-sized | up to 10 GB | low | 11434; excluded by the quiet-box lock |
| vite dev / preview | low | low | none | low | leaks hold ports and, once, a slot lock |
| Agents (Claude, Codex) | low each | about 0.5 GB each | none | git on `/mnt/e` | workflow agent cap |

### Observed waits and run times

| What | Time | Source |
|---|---|---|
| CI, whole run, green first attempt | median 40.8 min (n=157) | [M] `gh run list --limit 200` |
| CI E2E Smoke / Backend / Security / G3 / Frontend | 25.9-31.4 / 11.4-13.8 / 4.9-6.3 / 5.1-5.2 / 3.6-4.2 min | [M] `gh run view`, runs 43151317148, 43145323413, 43115474154, 43133329498 |
| CI runs with a re-run | 11 of 200 runs, 14 extra attempts | [M] |
| Docs PRs that still ran the full cycle | `docs/batch-1111d` 44.3 min, E2E 31.4 min | [M] run 43115474154 |
| Full backend suite, local, `/mnt/e` worktree | 28 min 08 s (4811 passed) | [L] `537-fullsuite-e966.log`, 2026-11-09 |
| Full backend suite, local, today | 11-20 min | [O] session reports |
| pytest wait for a slot behind quiet runs | about 90 min | [O] two agents, this session |
| Quiet batch 22 (all slots held) | 4 h 57 min | [L] `batch22-1111.out` |
| One full gates line, dev or production | 21.6 min for 490 tests | [L] `batch22-1111.out` |
| MEDS-G diagnosis runs | 2 h 06 min, 333 runs | [L] logs, evidence table |
| Quiet run stalled on a leaked lock | about 4 h, nothing done | [O] `quiet-run-stall-leaked-lock`, 2026-11-03 |
| Quiet run stalled on a leaked preview | 1061 s; 20 min; exit 75 three times | [L] `recurring-failures.md` mode 5 |
| Playwright page load, default `/tmp` vs `/dev/shm` | 35-150 s vs 265 ms | [O] `wsl-disk-fsync-playwright` |
| Timing tests from `/mnt/e` vs `/dev/shm`, same code and load | 3 failed in 99.9 s vs 87 passed in 34-40 s | [O] `wall-clock-tests-mnt-e` |
| 18 build items | 12.7 agent-hours, 10.8M tokens; a 1-line fix cost 382k tokens | [L] `2026-11-01-harness-speedup-plan.md` |
| Share of agent tool calls spent waiting / on rework | 18 % / 29 % | [O] `cheaper-l0-fixes` |

## 3. Root causes

1. **One host, one lock, five jobs.** `quiet_run.sh` claims the hold lock and slots 1 to 8 before it waits for quiet. That fixed the starvation of 2026-11-02, and it means a long quiet campaign stops every pytest on the machine. The design has no upper bound on campaign length.
2. **Serial Playwright everywhere.** One worker locally, one agent at a time, and one worker on a single CI runner for 39 spec files.
3. **Full pipeline for small changes.** `change_scope.py` already skips the local backend suite for non-backend diffs. Docs PRs that touch the owner-decisions file are still not docs-only (the speedup plan's "known consequence"), so docs batches pay the full 41 minutes.
4. **Diagnosis by brute force.** Both diagnoses were rigorous and both found a harness-side or first-call cost. Neither had a stop rule. The first MEDS-G hypothesis was refuted by 22 traced runs; the campaign ran 333 in all.
5. **Flakes block merges of unrelated work.** G3 failed on PRs that did not touch the page, at least 5 re-runs [O]. A re-run costs another full cycle.
6. **Cheap failures found late.** 9 of the last 30 failed runs failed ruff, a job that takes about 0.1 min [M]. Each was found after a push.
7. **`/mnt/e` I/O.** All worktrees sit on the Windows mount. The two worst incidents in the table above trace to it.
8. **Fragile waiting.** A session restart killed background waiters and two agents today [O]. Modes 13, 15 and 21 are all the same shape: something returned before its work finished.

## 4. Options

Savings marked [E] are estimates and need measuring on the first use.

| # | Option | Effort | Expected saving | Risk to verification | Owner decision |
|---|---|---|---|---|---|
| A | **Shard CI E2E** into 4 jobs (`--shard=i/4`), each still 1 worker | 0.5 day | E2E 28 min to about 10 min [E]; cycle 41 to about 24 min [E], since Backend Tests then gates it | Low: same tests, same worker count per runner. Check that shards do not change timing-gate results | **Yes** (`ci.yml` diff) |
| B | **Cancel superseded CI runs** (`concurrency` group per PR; none exists today [M]) | 1 hour | Frees queue on a 99-run day; not measured | None for PRs. Do not cancel `main` pushes | **Yes** (`ci.yml` diff) |
| C | **Ruff before push** in the builder brief or a pre-push hook | 1 hour | Up to 9 wasted cycles in the last 200 runs [M] | None; it adds a check | No |
| D | **Time-box diagnoses:** stop at 60 run-minutes or 3 lines of 20 runs, write what is known, then decide | Rule text only | MEDS-G would have saved about 1 h of its 2 h [E] | Low if "continue" stays an option with a stated reason | No (L0 rule); owner informed |
| E | **Quiet windows:** timing batches run in a fixed overnight window; daytime quiet runs capped at 30 min; pytest wait above 20 min is reported, not sat through | Rule text plus a wait line in `pyslot.sh` | Removes most of the 90-min daytime waits [E] | None; same gates, different hour | **Yes** (changes QUIET-PARALLEL-1107 practice) |
| F | **Re-size for the real box:** raise `PYSLOTS`, revisit the build ceiling | Minutes, after a check | 3 slots to 6-8 [E]; queueing drops accordingly | Low. More load means quiet runs wait longer unless E is in place | No, after the CPU question in section 8 is answered |
| G | **Worktrees on the Linux filesystem** (`~/wt/...`), main checkout stays | 0.5 day plus habit | Local suite 28 min toward CI's 11-14 min [E]; removes a class of false timing failures | Raises quality: fewer environment-caused results | No |
| H | **Timing gates judged in CI, quiet box for diagnosis only.** Add a nightly scheduled job that runs the gate specs N times on `main` and records the miss rate | 1-2 days | Removes routine 21.6-min acceptance lines from the box [L]; gives a flake-rate trend | Medium: a regression is seen up to a day late unless the per-PR pass stays. Keep the per-PR pass | **Yes** |
| I | **Make flaky gates non-blocking until fixed.** G3 is already not a required check [L: HANDOFF 2026-11-11 line 84] | None | Already banked | Do not make G3 required before MEDS-G is fixed | **Yes** (already pending as B3) |
| J | **Fix the flakes at the harness:** MEDS-G option A, rAF sampling plus theme settle; no bound moves | 1 build row | Measured 1/40 to 0/40 and 10/20 to 0/20 [L] | It changes how two shared gates measure, so every gate spec must be re-run | **Yes** (MEDS-G-X1 is drafted) |
| K | **A second runner** for timing gates and Playwright | 1-3 days, plus cost | Frees the GPU host for models and builds; size unmeasured | See the warning below | **Yes** (cost, security) |
| L | **GPU windows:** model rows run in a named window with no quiet run and no full suite | Rule text | Stops model work being starved or skewed | None | No |
| M | **Affected-test selection locally** (focused tests locally; CI runs the full suite, as it always does) | 1 day in `build-item.js` | 11-28 min per test round on backend rows [E] | Medium: failures surface 40 min later in CI. The full suite still runs before merge | **Yes** (changes the definition of done) |
| N | **Cheaper diagnosis instruments:** keep `diag-hooks.ts`, `gap_attrib.py` and `tick_delay.py` as a reusable kit; start with a bare timer and 20 traced runs (mode 14's recheck) | 0.5 day | Fewer runs per diagnosis [E] | None | No |

**Warning on K.** The repository is public [M: `gh repo view`]. A self-hosted runner on a public repository can be made to run code from a fork's pull request. This machine holds a test vault and the model host. If the owner wants a second runner, use a hosted larger runner or a separate machine with no patient-shaped data, and restrict it to trusted branches.

**Why A does not weaken anything.** Sharding splits the same test list across runners. Retries, bounds and worker count per runner stay as they are.

## 5. The role of the RSI loop

**What it is today.** The loop mines tool-call metadata, reflects, proposes small edits, gates them and opens PRs for the owner. It has merged two rules (#230, #341). Its last two archived runs promoted nothing, and the capstone section says plainly that the failure-rate changes between runs are not causal evidence [L: `rsi-in-development-and-application.md` §6, `rsi-runs/README.md`]. That honesty should carry into the report.

**Why it has not seen this problem.** It clusters tool *failures*. A 90-minute wait is not a failure; it is a successful command that took 90 minutes. The costs in this report are invisible to it.

**What it could do, within its existing limits:**

- **Mine waits, not only failures.** The rsi-log already records durations. Add three fixed classes: slot wait, quiet-run precheck wait (`quiet_run.sh` already prints "prechecks passed after N s"), and CI re-run. `pyslot.sh` prints nothing when it waits, so one log line there is the missing input.
- **Report through `owner_notes`.** The gate's allow-list is `rules.ts`, `cases.ts` and `recurring-failures.md`; `scripts/` and `.github/` are denied. So scheduling rules cannot arrive as RSI PRs. They can arrive as owner notes using the existing `add-precheck` and `add-stop-rule` suggestions, which L0 turns into queue rows.
- **Give it a measurable target.** "Median slot wait per build item" is a number that should move when option E or F lands. That would be the loop's first before-and-after measurement tied to a named change. It would still be an observation across different workloads unless the owner runs a deliberate A/B.

This is a proposal. Nothing here has been built or measured.

## 6. Roadmap to the MVP stakeholder presentation

**This week (small, reversible, mostly rule text)**

1. C: ruff before push.
2. D and N: the diagnosis budget and the instrument kit.
3. E and L: quiet windows overnight, a GPU window by day. Ask the owner first.
4. A and B: one `ci.yml` PR, shown to the owner as a diff (the SPEEDUP-CI-DIFF precedent).
5. J: answer MEDS-G-X1 and build the harness fix.
6. Answer the CPU question, then F.

**After the presentation**

- G: move worktrees to the Linux filesystem (it touches every agent brief, so not mid-sprint).
- H: nightly timing job, then retire routine quiet-box acceptance lines.
- M and K: both change how "done" is defined or cost money; decide with a week of wait data in hand.
- RSI wait mining (section 5).

**Stop doing**

- Starting a diagnosis without a run budget.
- Holding all slots for a multi-hour batch in working hours.
- Re-running a red CI job before reading which job failed.
- Planning against "6 vCPU, 22 GiB" without checking `nproc`.
- Making G3 required before its flake is fixed.

## 7. Guardrails: what must not be cut

- **No bound moves.** The 40 ms stillness bound, the 70 ms navigation bound, the 74 % coverage floor and the 0.7 embedding threshold stay. Speed comes from scheduling, sharding and location, never from a looser check (CLAUDE.md §3).
- **The full backend suite and every eval gate still run before merge.** Option M moves where the full suite runs; it does not remove it.
- **Review rounds stay.** Review rework often caught real safety bugs [O: `cheaper-l0-fixes`].
- **One Playwright measurer at a time** on a shared host. Parallel agents measured each other's builds [O].
- **A pass under load counts; a miss is re-run on a quiet box before anyone diagnoses it** (QUIET-PARALLEL-1107 as recorded in HANDOFF 2026-11-10).
- **A time-boxed diagnosis ends in a written decision,** never in "known flake" by default. Mode 14 records a real defect hidden behind a flake label.
- **Non-blocking is temporary and named.** Each non-required gate has an owner row and a fix row.

## 8. Open questions for the owner

1. Is the box permanently 24 logical CPUs and 37 GiB? If so, may L0 re-size `PYSLOTS` and the build ceiling?
2. May timing batches move to a fixed overnight window, with a 30-minute cap on daytime quiet runs?
3. Do you approve a `ci.yml` change for E2E sharding and run cancellation, reviewed as a diff?
4. MEDS-G-X1: harness fix (option A), as recommended in the diagnosis?
5. Should per-PR timing gates be judged in CI, with a nightly repeat job for the flake rate?
6. Is a second runner worth paying for before the presentation, given the public-repository risk?
7. May the local full suite be skipped on backend rows when CI runs it (option M)?
8. What is the presentation date? The split between "this week" and "after" depends on it.

## Checks skipped

- No Playwright, pytest or model run was made (read-only brief; the quiet box was in use).
- The 90-minute waits, the 11-20 min local suite, the 5 G3 re-runs and the session restart are session reports, not re-measured.
- The 15 E2E and G3 failures were counted by job name, not triaged as flake or real.
- Why `docs/batch-1111d` was not classified docs-only was not traced.
- I found the label QUIET-PARALLEL-1107 in handoffs and two plans, not in RUNBOOK §10.1 on `origin/main` (`git grep`).
- GPU state is one snapshot; no model was loaded at the time.
- All savings marked [E] are estimates.
- No Haiku scan agents were used; every figure tagged [M] or [L] was read directly.
