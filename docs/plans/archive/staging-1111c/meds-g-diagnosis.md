# MEDS-G-FLAKE: diagnosis (no fix)

**Result.** Two separate harness-timing failures share the one test `e2e/ui-meds.spec.ts:254`. Neither is ICU, and
neither is a G3 (INP) failure. CI's job is named "G3 on Production Build", but the assertions that fail are G10 and G1:

1. **G10 sampling gap on `/medications?tab=reminders` (5 of the 6 CI hits).** The Reminders tab click runs 8-20 ms of
   synchronous main-thread work: Radix Tabs activates on `mousedown`, then `setSearchParams` triggers a react-router
   navigation and a React discrete-lane render of the tab panel. That work lands right when the probe's 20 ms
   `setInterval` tick is due, so the tick runs late. On the quiet box the largest gap has a median of **30 ms** and a p90
   of 38 ms, against a bound of **40 ms** (`kind: 'interaction'`). CI's 41/44/41 ms are the tail of that distribution.
   No stillness property ever failed. Only the sampler's coverage check fails.
2. **G1 axe colour-contrast in dark (1 of the 6 CI hits, `med-fixture-1`).** `setTheme` flips `.dark` and axe starts at
   once. 33 CSS colour transitions (150/200 ms, `transition-colors duration-200`) are still running, so axe's
   colour-contrast rule reads a blend of the two themes.

**Product or harness:** harness, for both. The G10 work is real product work, but it is short (longest task median
6.9 ms). It misses only because a 20 ms timer sampler has 20 ms of headroom under a 40 ms bound. The G1 failure is a
reading taken mid-transition, which is not a steady-state contrast failure.

## Prior hypothesis (first `toLocaleTimeString` paying for ICU data, as in UIDOC-006A): **refuted**

- `logs/icu-search-line515.txt`: in 22 traced runs, 20 have **0.0 ms** of `toLocale*` time inside the gap window. The
  other 2 have 0.2 ms, at +129 and +176 ms, which is outside their gaps (they end at +78 and +141).
- The warm-up A/B (`HC_DIAG_WARM=1`, which warms `new Date(0).toLocaleString()` on load, as for `RemindersPanel.tsx:515`)
  does not move the gap:

| Pair | Gap median, no warm-up → warm-up | Over 40 ms |
|---|---|---|
| prod x1: p1 → pw1 | 30 → 30 | 1/40 → 6/40 (pw1 started at load 3.39, not quiet) |
| prod x2: p2 → pw2 | 32 → 32 | 1/20 → 0/20 |
| dev x1: d1 → dw1 | 32 → 31 | 0/20 → 0/20 |

- Hot frames in the gaps (`logs/hot-frames-pt1-mapped.txt`, ms summed over 12 traced runs): react-dom
  (251/257/225/52/160/24: about 33 ms), react-router `chunk-OB3PAWPO.mjs:311` (11.2), `@radix-ui/react-presence` (8.0),
  scheduler `unstable_now` (2.6), `api.ts:86` fetch (1.8), tailwind-merge (2.4). There is no ICU frame and no single
  product hotspot. Unlike UIDOC-006A, there is no one call to warm.

## Evidence

All lines ran on the quiet box with `prod` = vite preview + mocked API, which matches CI. They used `--workers=1
--retries=0`, `HEAD 15b03eb1`, and spec hooks only (`tools/diag-hooks.ts`; no test body or bound changed). Gap = the
largest post-trigger gap per run, parsed from the `DIAG` lines in `meds-g-diag/logs/*.log`.

| Line | Condition | Runs | Gap min/p50/p90/max ms | Over 40 | Other failures |
|---|---|---|---|---|---|
| p1-rem | prod x1 | 40 | 24/30/38/41 | **1** | |
| p2-rem | prod x2 (CDP) | 20 | 26/32/38/44 | 1 | |
| d1-rem | dev x1 | 20 | 26/32/37/38 | 0 | |
| pw1-rem | prod x1 + ICU warm | 40 | 21/30/42/63 | 6 | load 3.39 at start |
| pw2-rem | prod x2 + ICU warm | 20 | 26/32/36/38 | 0 | |
| dw1-rem | dev x1 + ICU warm | 20 | 26/31/37/38 | 0 | |
| **pr1-rem** | **prod x1 + rAF samples** | 40 | **17/17/20/27** | **0** | |
| pr2-rem | prod x2 + rAF samples | 8 (cut off when the session died) | 17/18/28/33 | 0 | |
| p1-det | prod x1, `med-fixture-1` (navigation, 70 bound) | 40 | 23/29/35/39 | n/a | 0 G1 |
| pt1-rem / pt1b-rem | prod x1 + trace | 12 + 23 with dumps | 26/31/37/40 | 0 | **G1 dark: 15/25** (`.bg-status-verified-subtle`) |
| pt2-rem | prod x2 + trace | 10 | 35/40/48/61 | 4 | |
| CI | GitHub runner | 3 G10 hits | 41, 44, 41 | | 1 G1 dark, `med-fixture-1` |

**G10 mechanism** (`logs/tick-delay-x1-all.txt`, 35 traced x1 runs; `logs/timeline-pt1.txt`): the next tick is due at
gap start + 20 ms. It runs a median of **11 ms late** (max 20). Of that lateness, a median of **8.5 ms** is main-thread
busy time from tasks that ran ahead of the tick: the `mousedown`/`pointerout` input task (Radix `onMouseDown` →
react-router at `:311`), then React scheduler tasks (`FunctionCall(ae)`, 5-13 ms each), then a frame. Example (dark r3):
the tick was due at +20; the React tasks ran at +19.4 (5.0 ms) and +24.8 (13.0 ms), a frame at +37.9, and the tick at
+39.9. The main thread was busy 30.9 of 40 ms. The sampler's own ticks cost 0.3-0.7 ms. CPU x2 (pt2) moves the median
gap to 40 ms, so a slower CI runner sits right on the bound.

**Why rAF sampling closes it (pr1):** frames still run between the React tasks ("frame" appears in `ran_ahead_of_tick`
in 22/35 runs). A sample taken on each animation frame lands at every point a user could see a new state, so the
largest gap falls to the frame interval: median 30 → 17 ms, max 41 → 27 ms, 1/40 → 0/40. The bound does not move.

**G1 mechanism** (`tools/axe-transition-diag.ts`, lines `pa0`/`pa1`, 20 runs each on `med-fixture-1` dark): at the flip,
33 transitions are running (`color`/`background-color`/`border-*-color`, 150 and 200 ms). With axe started at once
(pa0, axe begins 23-42 ms after the flip), color-contrast was blocking in **10/20** runs, on `.bg-status-verified-subtle`
and `.bg-accent` (`#4e5b58 on #59ad9c`, a light-to-dark blend). Waiting for `document.getAnimations()` to finish first
(pa1, axe begins 218-261 ms after the flip): **0/20**. Tracing slows the run and raised the gate's own dark G1 failure
rate to 15/25 (pt1/pt1b). Untraced gate lines: 0 G1 failures in 120 runs (p1-rem, p1-det, pr1-rem).

## Fix options

| # | Change | Files | Expected effect | Owner gate |
|---|---|---|---|---|
| **A (Recommended)** | Harness: (1) G1 waits for finite animations after `setTheme`, then one frame, before axe. This is the `settleTheme`/`settleFiniteAnimations` already in `ui-dark-primitives.spec.ts:15-32` (HC-DPC-003), moved into `gates.ts`. (2) The G10 sampler also samples on every `requestAnimationFrame` while running, and keeps the 20 ms interval. No bound moves. | `e2e/support/gates.ts` only | G10: **measured** 1/40 → 0/40 at x1, median 30 → 17, max 41 → 27; x2 max 33 (n=8, partial). G1: **measured** 10/20 → 0/20 (diag order). | Not required by rule (no bound, no product UI). Owner ack advised: it changes how two shared gates measure on every UI gate spec. |
| B | Bound: classify the Reminders tab trigger as a page change (70 ms under STILLNESS-NAV-70, or a new row), plus A(1) for G1. | `ui-meds.spec.ts`, plus `gates.ts` for G1 | G10: estimated 0 misses. Every measured gap is ≤ 63 ms, including the loaded and traced x2 runs. CI max 44. | **Yes** (bound) |
| C | Product: wrap the tab change (`MedicationCoach.tsx:196` `setSearchParams`) in `startTransition`, so React renders in yielding 5 ms slices. G1 still needs A(1); the product cannot affect the harness's attribute flip. | `MedicationCoach.tsx` + `gates.ts` | **Not measured.** Estimate: the 8.5 ms busy-while-late falls to ≤ 5 ms and the median gap to about 25 ms. Risk: the old panel stays up during the transition, which G10/G5 would need to re-check. | **Yes** (product UI) |
| D | Known flake: re-run on red (the /export UIDOC-006A precedent). | none | No change: the CI rate stays at 6 hits in a few days. **Blocks making G3 required** (HANDOFF line 84). | Yes |

## Draft owner question (MEDS-G-X1)

> Q: "MEDS-G-FLAKE, measured: `ui-meds:254` fails CI for two harness-timing reasons, not ICU (the warm-up A/B made no
> difference). (1) On the Reminders tab the stillness sampler's 20 ms timer is delayed by the tab-switch render
> (8-20 ms), so its largest gap is 30 ms median against a 40 ms bound; CI's 41-44 ms are the tail. Nothing on screen
> moved. (2) In dark, axe runs while the theme's 150-200 ms colour transitions are still blending (10/20 when axe
> starts at once, 0/20 after they finish). Which fix?"
>
> - **"Harness: rAF samples + settle theme (Recommended)"**: "`gates.ts` only. The stillness sampler also samples on
>   each animation frame (the 40 ms bound stays), and axe waits for running transitions after a theme change (the
>   HC-DPC-003 pattern). Measured 1/40 → 0/40 and 10/20 → 0/20. Applies to every UI gate spec; Task 2 re-runs them all."
> - **"Tab switch counts as a page change (70 ms)"**: "Reminders tab uses the STILLNESS-NAV-70 bound; axe settle as
>   above. Every measured gap ≤ 63 ms."
> - **"Product: startTransition on the tab switch"**: "Makes the render yield; unmeasured (estimate median ~25 ms);
>   axe settle as above. Product UI change."
> - **"Known flake, re-run on red"**: "No change; G3 cannot be made a required check."

## What this would not notice / skipped

- **No new Playwright runs in this pass.** The existing data answered every question. Ports 3000/4173/5173/8000 were
  free and no leftover playwright or vite process was found.
- Option A was measured as an init-script A/B (`HC_DIAG_RAF=1` wraps the 20 ms `setInterval` with an rAF loop), not as
  the real `gates.ts` change. pr2 (x2) has only 8 runs; the session died mid-line. Task 2 must re-measure the real
  change at x1 and x2, and run the **other** G10/G1 gate specs. None of them were measured with rAF sampling or the
  theme settle.
- The G1 A/B used a diag test, not the gate body. Its own rAF colour sampler plus an extra `getAnimations()` round trip
  gives a much higher hit rate (10/20) than the untraced gate (0/120 locally; 1 CI hit). The mechanism is shown; the
  gate's own rate is not.
- An rAF sample costs a forced style read every frame (pr1 took 161-163 samples against about 71). It ran clean here.
  Its cost on heavier pages is unmeasured.
- Traced runs inflate timings. Rates come from the untraced lines only, and the traces were used for attribution only.
- `RemindersPanel.tsx`/`MedicationCoach.tsx`/`gates.ts` were checked unchanged between `15b03eb1` (measured) and
  origin/main `c79b7fd1` (`git diff --stat`: only `medication-detail.spec.ts` changed under the medication paths).
- Hit #591 x2, #602 and #616 logs were not in `ci/`. Four CI job logs were read (3 G10, 1 G1).

## Files

- Driver, hooks, parsers: `~/hc-quiet-logs/staging-1111c/meds-g-diag/tools/` (`run_diag.sh`, `pw_line.sh`,
  `diag-hooks.ts`, `axe-transition-diag.ts`, `tick_delay.py`, `gap_attrib.py`, `icu_search.py`)
- Logs and parser outputs: `~/hc-quiet-logs/staging-1111c/meds-g-diag/logs/`; run list: `driver-main.out`, `driver-2.out`
- CI logs: `~/hc-quiet-logs/staging-1111c/meds-g-diag/ci/`
- Diag worktree (spec hooks appended, uncommitted): `/mnt/e/Programming/Github Repo/hc-meds-g-diag` at `15b03eb1`
