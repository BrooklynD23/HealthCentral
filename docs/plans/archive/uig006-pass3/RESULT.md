# UIG006-PASS3-FLAKE quiet-box result (2026-11-13)

**Cause found: the box's wall clock steps back about 1.05 s every ~31 s, and stillnessProbe's lazy-route wait and `elapsedMs` use Node `Date.now()`.**
A step that lands inside the probe window shrinks the measured `elapsedMs` by about 1 s (2627 -> ~1500), so `expect(elapsedMs >= 2000)` fails.
The flake still reproduces on current origin/main. It is not a fixture or fetch-timing bug.

Base: origin/main `f386e5cc`, worktree `~/wt/hc-uig006-quiet` (detached).
Spec: verbatim copy of `e2e/ui-gates.spec.ts` plus `scripts/diag-kit/diag-hooks.ts` plus a file-level timing and route hook (`zz-uig006-diag.spec.ts` here).
Flags: `-g "pass-3"`, `--retries=0`, 1 worker, `PLAYWRIGHT_ASSISTANT_CATEGORY_PROOF=1`, TMPDIR=/dev/shm.
Every Playwright run went through `scripts/quiet_run.sh --max-wait 1800` (`run.sh`).

## Runs

| Line | What | Result | Log |
|---|---|---|---|
| 1 | 20 runs, traced (`HC_DIAG_TRACE=1`) | 20/20 passed | l1-traced20.log |
| 2 | 150 runs, untraced | **4 failed** / 146 passed (`elapsedMs` 1487, 1489, 1515, 1521) | l2-quiet150.log |
| 3 | 150 runs + route/response hooks | **8 failed** / 142 passed (min `elapsedMs` 1552) | l3-quiet150-routes.log |
| 4 | A/B: same spec, scratch `gates.ts` with every Node `Date.now()` replaced by `performance.now()` (monotonic) | **150/150 passed**; 22 clock steps occurred during the line (clockstep-l4.log) | l4-ab-monotonic150.log |

Origin/main total: 12 failures in 320 runs (3.75%). Monotonic clock: 0 in 150 under the same steps.
Run-minutes used: about 37 of 60.

## Evidence

- In every failing run, the `/gates/slow` route handler is entered and its Node `setTimeout(1200)` resolves after only **128-161 ms of `Date.now()` time**. The fixture fetch starts 50-59 ms after `__start`, the same as in passing runs. The Playwright request event lags by 1-3 ms. Neither the fetch nor the event delivery is late.
  - One run shows 1203 ms because the step fell after "done" and before the response was logged.
- `clockstep.js` compares `Date.now()` deltas with `process.hrtime` every 50 ms. It logs `step=-1040..-1069 ms` about every 31.2 s, with nothing in between: clockstep-1.log and clockstep-l4.log.
- `dmesg`: `systemd-journald: Time jumped backwards, rotating.` 41 times since boot, from about uptime hour 17.
- `systemd-timesyncd` is active and `timedatectl` reports NTP synchronized. Two clock-sync sources may be fighting: WSL host time sync and timesyncd. That is inferred, not proven.
- The arithmetic matches: a ~1.05 s step during the ~1.3 s fetch-plus-idle phase leaves 2627 - 1050 ≈ 1500 ms. GATES-PASS3-ELAPSED's 1657 ms is one step. The 741 ms reading fits two steps, or a step plus a delayed wait. The row text already said "barring a wall-clock step (`Date.now()`)".
- A backward step can only make `elapsedMs` read low. It cannot make a broken page pass, so this failure is a harness false failure, never a false pass.

## Distributions (origin/main lines 1-3, n=320 reports)

| Line | elapsedMs min / median / p95 / max | maxGapMs median / p95 / max | timerMaxGap max | rafMaxGap max |
|---|---|---|---|---|
| 1 (traced, 20) | 2620 / 2627.5 / 2639 / 2641 | 18 / 33 / 39 | 42 | 53 |
| 2 (150) | 1487 / 2625 / 2631 / 2640 | 22 / 29 / 37 | 41 | 37 |
| 3 (150) | 1552 / 2626 / 2636 / 2675 | 23 / 37 / 40 | 51 | 53 |
| 4 A/B (150) | 2619 / 2627 / 2636 / 2660 | 23 / 33 / 40 | 52 | 47 |

`fetchDelayMs` (`__start` to `fetch()`, page clock): median 55-56, max 66, on every line.
`withInfraRetry` absorbed sampling-starvation retries on some lines: 1, 1, 9 and 1 runs. Those are the separate G10 sampling-gap class, not this row.

## Proposal (not pushed: outside the row's licence)

The row licenses `e2e/ui-gates.spec.ts` only and requires `git diff origin/main -- e2e/support/gates.ts` to be empty. The cause is in `gates.ts`, so the fix needs an `L0 ruling:` that names `gates.ts`. The row's planned candidate (a Node-side timer to start the fetch) would not fix this.
Diff: `proposed-gates-monotonic.diff` replaces all 14 Node-side `Date.now()` calls in `gates.ts` (waitUntil, trackRequests, settleStartPage, stillnessProbe) with `performance.now()`. No bound, constant or test changes.
Before committing:
- round `elapsedMs` with `Math.round`, since `performance.now()` is fractional;
- update the NetworkTracker comment "ms since epoch".

Separately, the owner may want to check WSL time sync on this box, for example whether `systemd-timesyncd` should run under WSL at all. That is a box change and was not touched. It also affects every other `Date.now()`-timed local test.

## Not done

- No CI log search for recent pass-3 failures.
- The A/B was run on pass-3 only, not the whole ui-gates spec.
- `diag-kit/gap_attrib.py` was run on line 1 only; the gaps are unrelated to this cause.
- Mutants m1-m4 were not run against the monotonic variant.
