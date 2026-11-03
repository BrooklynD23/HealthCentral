# STILLNESS-NAV-LATE Task 1: why page changes run late under the stillness probe (MEASURE)

Row: STILLNESS-NAV-LATE (docs/plans/2026-10-23-frontend-revamp-plan.md, "STILLNESS-NAV-LATE", Task 1) with NAV70-CI-MISS folded in
(docs/plans/2026-10-30-followups-plan.md). Draft PR #469, branch `fix/stillness-nav-late-nav-gap-cause`.
Task 1 only: no product or harness change, nothing under `src/` edited. Task 2 and Task 3 are not started.

- Measured tree: `origin/main` `3325f387` plus the empty claim commit `0c6ce81f`. `git diff 3325f387 HEAD -- src` is empty, so `src/` is exactly main's.
  `origin/main` has since moved (it read `4f29bd6a`, then `7052ae8d` during the runs); it was not merged.
- Heads the wraps ran from (the committed `run/` copy): wrap A `46f2808f`, wrap B `f942c6ea`, wrap C `e40decdb`, wrap D `e46459e7`, wrap E `4cd89670`. The SHA of the commit that adds this README is in the PR comment.
- Every quiet Playwright run went through `/tmp/claude-1000/quiet_run.sh --max-wait 7200`. quiet_run's precheck passed and the wrap exited 0 each time; it never exited 75.
- Bounds: none lowered, raised or touched. A miss in this document means a run's maximum gap is over 40 ms (the row's measure), not that the probe failed at the effective 70 ms.
  No run was repeated to get a pass; no check was marked fixme, skip or fail.

## Result in brief

1. **Reproduced, at the edge of the rule.** Baseline (wrap A): probe set 5 of 15 over 40 ms, bare timer 0 of 15. The rule says "5 or more" with "3 or fewer", so it is met, with no margin, and 3 of the 5 misses fell in batch A3 where the box load rose from 1.2 to 5.8 during the batch. The 13 probe controls in wrap B (195 more baseline probe runs) show the same effect with more power: **66 of 195 over 40 ms (34 %)**, so 71 of 210 baseline probe runs miss. The bare timer: 1 of 60 baseline runs misses (44 ms). `/search` is the worst route: 28 of 39 control runs (72 %) plus 3 of 3 in wrap A.
2. **Decision rule, applied as fixed before the runs: candidate 1 (sampler start to trigger) is the cause.** Removing it alone (a 100 ms wait between `startSampler` and the trigger) brings the probe set from 6 of 15 to **0 of 15, maximum 40 ms**. The plan's table gives candidate 1 no bottom-up variant, so rule (ii) does not apply to it. No other candidate meets the rule. Candidates 6a (mock responses 50 ms late) and 8 (route chunk imported first) also reach 0 of 15 but do not meet the letter of the rule (6a: its control missed 4 of 15, under 5; 8: diagnostic only, never a cause). A supplementary bare-timer variant without the 100 ms wait (not in the plan's table) misses 4 of 15 against 0 of 15 for its control: in the same direction, one short of 5.
3. **The trace says what the "late" gap is, and it is not the page change.** In six traced baseline misses (three click routes: 43, 42, 42 ms; three `/search`: 56, 44, 44 ms) the main thread is 77 to 99 % busy for the whole gap window, which opens 8 to 9 ms before the trigger (49 ms in one run) and closes at +33 to +37 ms (+7 in that run). The work is the **start page's own pending render**: a 19 to 26 ms React `flushSyncCallbacks` microtask (react-dom, with a react-query notify nested in it), with 3 to 4 ms of layout before it and about 6 ms of layout, paint, framer-motion and scheduler work after it. The trigger's own events are not in the window: the `click` dispatches at +64 to +71 ms in the three click-route misses (+40 to +46 ms in the runs that did not miss), and the `/search` input events at +24 to +51 ms. The target route's chunk is requested at about +90 ms. The start page's `/api/v1/documents/` and `/documents/highlights/summary` responses (`DocumentInbox.tsx:68`) land at -26 to +2 ms in these runs. With the 100 ms wait, or on the bare timer, that work is finished before the trigger.
4. **Proposed Task 2: PRODUCT (e2e harness), no app code.** Make the probe start from a settled start page. Files: see "Proposed Task 2". The L0 ruling picks the kind and files; nothing is proposed in `src/` app code.
5. **The CI misses (71 to 77 ms, `/search`, dev server)** are consistent with this cause in route and mechanism, but the cause is not shown to produce 71 ms or more: the largest local gap in 431 probe runs is 65 ms. See the NAV70-CI-MISS table.

## What was run

### Evidence copy and recovery (step 1)

The L0 2026-10-27 scripts and logs are copied to `l0-2026-10-27/` (see `l0-2026-10-27/RECOVERY.md` for the full note and the raw `sha256sum` output).
L0's session scratchpad was wiped before this row started. L1 recovered 16 of the 18 files byte-exact from the old session transcript; the implementer ran `sha256sum` on the committed copies itself.
**16 of 18 match the plan table. `baretimer/t4-preview.log` (`91e3cf6fa569`) and `probecost/probe-runs.log` (`c139049e251b`) are lost.** Only filtered views survive; they are committed as
`t4-preview.FILTERED-not-original.log` and `probe-runs.FILTERED-not-original.log`. They are not the originals and their hashes cannot be checked. The plan's table rows that cite them rest on those views.

| File | Plan table | sha256 of the committed copy | Result |
|---|---|---|---|
| `baretimer/baretimer.spec.ts` | `95c225c36f8a` | `95c225c36f8a` | match |
| `baretimer/playwright.config.ts` | `6ed971971960` | `6ed971971960` | match |
| `baretimer/run_batch.sh` | `4d3506bcf645` | `4d3506bcf645` | match |
| `baretimer/wait_quiet.sh` | `3008f372b0fd` | `3008f372b0fd` | match |
| `baretimer/t4_preview.sh` | `91916bb4ecc1` | `91916bb4ecc1` | match |
| `baretimer/batch0.log` | `8bc42a492c2c` | `8bc42a492c2c` | match |
| `baretimer/batch1.log` | `bacc5213b3b8` | `bacc5213b3b8` | match |
| `baretimer/batch2.log` | `04a872243e9b` | `04a872243e9b` | match |
| `baretimer/batch3.log` | `9f3e239a9c6a` | `9f3e239a9c6a` | match |
| `baretimer/batch4.log` | `b89f4d07aa63` | `b89f4d07aa63` | match |
| `baretimer/batch5.log` | `ee72cd494c3d` | `ee72cd494c3d` | match |
| `baretimer/probe-control.log` | `94e867b7b087` | `94e867b7b087` | match |
| `baretimer/t4-preview.log` | `91e3cf6fa569` | not recovered (committed instead as `baretimer/t4-preview.FILTERED-not-original.log`, `24511fcf9bf3`) | LOST, cannot be checked |
| `probecost/gates.instrumented.ts` | `b49473df8217` | `b49473df8217` | match |
| `probecost/main-probe.spec.ts` | `59af43d9db7c` | `59af43d9db7c` | match |
| `probecost/playwright.config.ts` | `e253e44fa2bb` | `e253e44fa2bb` | match |
| `probecost/run_probe.sh` | `0736ce5bd83d` | `0736ce5bd83d` | match |
| `probecost/probe-runs.log` | `c139049e251b` | not recovered (committed instead as `probecost/probe-runs.FILTERED-not-original.log`, `9302fce73d4c`) | LOST, cannot be checked |

### Set-ups (step 2)

Both sets: one fresh page per run (Playwright's per-test context), 1440 x 900, the mock API (`installMockApi`, `seedMockSession`), start page `/inbox` (`/verify` for `/inbox`, as `startPageFor`),
wait for `[data-safety-rail]`, `await document.fonts.ready`, then the route's trigger (`navigateTo`, copied from `e2e/ui-shell.spec.ts:163`). Routes: `/timeline`, `/search`, `/medications/med-fixture-1`, `/notifications`, `/care-tasks`.
A `longtask` and a `long-animation-frame` observer is installed in both sets. Config (`run/playwright.config.ts`): workers 1, retries 0, trace, video and screenshot off. The spec prints its own proof, pasted from the batch logs:

```
CONFIG	trace="off"	video="off"	screenshot="off"	workers=1	retries=0	viewport={"width":1280,"height":720}
```
(The 1280 x 720 is the device default; the spec's `test.use({ viewport: 1440 x 900 })` overrides it for every case, as in HC-UISH-009's describe.)

- **Probe set** mirrors today's HC-UISH-009 (`e2e/ui-shell.spec.ts:319-333`): `openRoute` (mock, session, `consoleAndNetworkGuard`, goto), RAIL visible, `fonts.ready`, then `stillnessProbe` with `expected: [RAIL, TOGGLE_NOTE]`, `kind: 'navigation'`, `lazyRoute: true`, using `gates.instrumented.ts` (today's `gates.ts` plus logging lines only). Maximum gap = the `PROBECOST` line's `maxGap`.
- **Bare timer set** is L0's: a 20 ms `setInterval` pushing `performance.now()`, 100 ms wait, `t0` read in a second `evaluate`, trigger, 1500 ms, maximum gap from the trigger. It carries no guard listeners and no `trackRequests` listeners (as L0's did). The guard is candidate 3's factor.
- **Instrumented gates** `run/gates.instrumented.ts` is built by `run/build_instrumented.py` from `src/frontend/e2e/support/gates.ts` (every anchor matched exactly once). Pasted diff, logging lines only (L0's PROBECOST patch re-applied, plus `gapStartsAtMs`, `triggeredAt` and the request timeline `REQLOG` that candidate 6 asks for):

```
### diff src/frontend/e2e/support/gates.ts run/gates.instrumented.ts (head 6d3c25b9; logging lines only)
480a481,483
>   /** MEASUREMENT ONLY: snapshot() duration in ms and [data-t0] nodes visited */
>   dur?: number;
>   n?: number;
538c541,542
<     const t = Math.round(performance.now());
---
>     const tx = performance.now(); // MEASUREMENT ONLY
>     const t = Math.round(tx);
573c577
<     return { t, pathname: location.pathname, route, nodes, expectedHits };
---
>     return { t, pathname: location.pathname, route, nodes, expectedHits, dur: performance.now() - tx, n: nodes.length };
785a790,791
>   /** MEASUREMENT ONLY: [kind, Date.now(), url path] for every request event */
>   events: Array<[string, number, string]>;
794c800
<   const tracker: NetworkTracker = { inFlight, lastEventAt: Date.now(), stop: () => undefined };
---
>   const tracker: NetworkTracker = { inFlight, lastEventAt: Date.now(), events: [], stop: () => undefined };
796a803
>     tracker.events.push(['start', tracker.lastEventAt, new URL(request.url()).pathname]); // MEASUREMENT ONLY
800a808
>     tracker.events.push(['end', tracker.lastEventAt, new URL(request.url()).pathname]); // MEASUREMENT ONLY
830a839,840
>   let measWall = 0; // MEASUREMENT ONLY
>   let measEvents: Array<[string, number, string]> = []; // MEASUREMENT ONLY
836a847
>       measWall = triggeredWall; // MEASUREMENT ONLY
852a864
>       measEvents = network?.events ?? []; // MEASUREMENT ONLY
863a876,888
>   // MEASUREMENT ONLY: probe cost per run.
>   {
>     let mg = 0, gi = -1, maxDur = 0, maxN = 0, sumDur = 0, cnt = 0;
>     snaps.forEach((s, i) => {
>       if (s.t < triggeredAt) return;
>       cnt++; sumDur += s.dur ?? 0;
>       maxDur = Math.max(maxDur, s.dur ?? 0); maxN = Math.max(maxN, s.n ?? 0);
>       if (i > 0 && s.t - snaps[i - 1].t > mg) { mg = s.t - snaps[i - 1].t; gi = i; }
>     });
>     const f = (x: number | undefined) => (x ?? NaN).toFixed(1);
>     console.log(`PROBECOST\t${snaps[snaps.length - 1]?.pathname}\tmaxGap=${mg}\tdurBeforeGap=${f(gi > 0 ? snaps[gi - 1].dur : undefined)}\tdurAtGap=${f(gi >= 0 ? snaps[gi].dur : undefined)}\tmaxDur=${f(maxDur)}\tmeanDur=${f(cnt ? sumDur / cnt : 0)}\tnodesMax=${maxN}\tnodesAtGap=${gi >= 0 ? snaps[gi].n : -1}\tpostSamples=${cnt}\tgapStartsAtMs=${gi > 0 ? snaps[gi - 1].t - triggeredAt : -1}\tgapEndsAtMs=${gi >= 0 ? snaps[gi].t - triggeredAt : -1}\twindowMs=${snaps[snaps.length - 1].t - triggeredAt}\ttriggeredAt=${triggeredAt}`);
>     console.log(`REQLOG\t${measEvents.map(([k, at, p]) => `${k}:${at - measWall}:${p}`).join(' ')}`);
>   }
```

Reading of "of 15" (named, as the brief asked): one batch holds only 5 probe runs, so "misses 5 or more of 15" is read as the **pooled three-batch tally**. Per-batch tallies are reported next to it.

### Baseline (step 2, wrap A): RED

Wrap A: warm-up first (declared, own log `logs/wrap-A/warmA.*`, 5 probe + 5 bare, not counted: probe 0 of 5 over 40 ms, max 33; bare 0 of 5, max 36), then 3 batches of the probe set and the bare-timer set back to back, alternating which goes first (A1 probe first, A2 bare first, A3 probe first).

| | A1 | A2 | A3 | pooled |
|---|---|---|---|---|
| probe set over 40 ms | 1 of 5 | 1 of 5 | 3 of 5 | **5 of 15** |
| bare timer over 40 ms | 0 of 5 | 0 of 5 | 0 of 5 | **0 of 15** |

Rule: probe 5 or more of 15 and bare 3 or fewer = reproduced. Met (5 and 0). Not reproduced would have been "fewer than 5 of 15"; the variants therefore ran.
Raw per-run lines (also `logs/wrap-A/tally.txt`):

```
batch set   route     maxGap  gap window after trigger (ms)  long tasks  load1 start/end   miss(>40)
A1    probe timeline     31     77..108                        -           1.28/1.28      
A1    probe search       48     -8..40                         -           1.28/1.34      MISS
A1    probe med          27     61..88                         -           1.34/1.34      
A1    probe notif        32     23..55                         -           1.34/1.23      
A1    probe care         33     18..51                         -           1.23/1.23      
A1    bare  timeline     35     18..53                         -           1.23/1.23      
A1    bare  search       27     -2..25                         -           1.23/1.37      
A1    bare  med          30     58..87                         -           1.37/1.37      
A1    bare  notif        32     18..50                         -           1.37/1.26      
A1    bare  care         27     38..65                         -           1.26/1.26      
A2    bare  timeline     30     36..66                         -           1.69/1.69      
A2    bare  search       30     16..46                         -           1.69/1.55      
A2    bare  med          28     -4..25                         -           1.55/1.55      
A2    bare  notif        36     17..53                         -           1.55/1.43      
A2    bare  care         33     18..51                         -           1.43/1.43      
A2    probe timeline     32     18..50                         -           1.43/1.43      
A2    probe search       43     18..61                         -           1.43/1.31      MISS
A2    probe med          28     61..89                         -           1.31/1.31      
A2    probe notif        30     19..49                         -           1.31/1.21      
A2    probe care         32     20..52                         -           1.21/1.21      
A3    probe timeline     45     20..65                         -           3.09/3.09      MISS
A3    probe search       58     -3..55                         -           3.09/2.84      MISS
A3    probe med          33     -6..27                         -           2.84/2.84      
A3    probe notif        42     25..67                         -           2.84/3.90      MISS
A3    probe care         34     17..51                         -           3.90/3.90      
A3    bare  timeline     27     36..63                         -           3.90/3.90      
A3    bare  search       26     17..43                         -           3.90/4.87      
A3    bare  med          37     57..94                         -           4.87/4.87      
A3    bare  notif        30     36..65                         -           4.87/5.84      
A3    bare  care         31     37..68                         -           5.84/5.84      
```

Long tasks: the observer recorded none in any of the 539 counted runs (the same as L0's bare-timer result). It saw 489 `long-animation-frame` entries (in `logs/**/*.jsonl`).
The gap window is signed: a negative start means the last sample before the trigger came before it, so the gap spans the trigger (the probe and the bare timer both count it, as `checkSampling` does).

## Candidate variants (steps 3 and 5, wrap B): RED and GREEN for every candidate

Wrap B: warm-up first (30 uncounted runs on the three servers; probe 2 of 15 over 40 ms, bare 0 of 15; the page opened 1 WebSocket on the dev server and on the HMR-off server), then 3 batches. Each batch has 16 units; each unit is 5 control runs and 5 variant runs (one per route), control and variant adjacent, alternating which goes first, the unit order rotating by batch. 480 counted runs.
A probe unit's control is the baseline probe; a bare unit's control is the baseline bare timer. Candidate 7a's control is the dev server. The first attempt at wrap B was stopped (see "Deviations"); its 88 runs are disclosed, not used.

Variant definitions, one variable each (gates-level diffs pasted below; the rest are spec flags in `run/nav-sets.spec.ts`):

| Unit | Plan # | Variant | Role |
|---|---|---|---|
| c1-wait100 | 1 | probe with `await sleep(100)` between `startSampler` and the trigger | decision rule (i) |
| c2a-lazy-false | 2 | probe with `lazyRoute: false` (no `trackRequests`, no network-idle wait) | (i) |
| c2b-bare-track | 2 | bare timer with `trackRequests`' three listeners attached | the bottom-up variant for (ii) |
| c3a-noguard | 3 | probe without the `consoleAndNetworkGuard` listeners | (i) |
| c3b-nolisteners | 3 | probe without the guard and with `lazyRoute: false`: no Node-side `page.on` listener at all | (i) |
| c4a-raf | 4 | sampler ticks from `requestAnimationFrame` instead of `setInterval` | diagnostic only |
| c4b-unrounded | 4 | unrounded stamps | diagnostic only |
| c5-barestamp | 5 | `snapshot()` replaced by a bare stamp push | (i) |
| c6a-mock50, c6b-mock150 | 6 | every `/api/v1` mock response fulfilled 50 ms or 150 ms late (a later route that waits, then `route.fallback()`) | (i) |
| c7a-preview | 7 | the probe on a `vite preview` build of this tree (`npm run build`, output outside the tree) | (i) |
| c7b-hmr-off | 7 | the probe on a dev server started with `server.hmr: false` | (i), see Deviations |
| c8-preload | 8 | the target route's lazy page module imported in the page before the sampler starts | diagnostic only |
| c9-reduced | 9 | `emulateMedia({ reducedMotion: 'reduce' })` | (i) |
| s1-bare-nowait | 1 (supplementary) | bare timer with no 100 ms wait | not in the plan's table; not part of (ii) |
| s3-bare-guard | 3 (supplementary) | bare timer with the guard listeners | not in the plan's table; not part of (ii) |

Candidate 3's other parts: trace, video and screenshot off (CONFIG line above); the CDP message count in the probe window (`DEBUG=pw:protocol`, wrap D, messages in both directions between the probe's start and end, includes the `trackRequests` and guard traffic):

```
CDPCOUNT	Ccdp.b1.cdpcount.base.probe.timeline	total=105	send=26	recv=79
CDPCOUNT	Ccdp.b1.cdpcount.base.probe.search	total=104	send=20	recv=84
CDPCOUNT	Ccdp.b1.cdpcount.base.probe.med	total=250	send=25	recv=225
CDPCOUNT	Ccdp.b1.cdpcount.base.probe.notif	total=334	send=46	recv=288
CDPCOUNT	Ccdp.b1.cdpcount.base.probe.care	total=105	send=26	recv=79
CDPCOUNT	protocol lines in the whole batch	7239
```

Gates-level variant diffs (`run/make_variants.py`, `run/variants.diff.txt`):

```
### diff gates.instrumented.ts gates.v1.ts
834a835
>   await sleep(100); // VARIANT v1: 100 ms between startSampler and the trigger

### diff gates.instrumented.ts gates.v4a.ts
590c590,595
<   state.timer = window.setInterval(tick, config.intervalMs);
---
>   // VARIANT v4a: rAF-driven ticks instead of setInterval (diagnostic only)
>   const raf = () => {
>     tick();
>     if (state.running) requestAnimationFrame(raf);
>   };
>   requestAnimationFrame(raf);

### diff gates.instrumented.ts gates.v4b.ts
542c542
<     const t = Math.round(tx);
---
>     const t = tx; // VARIANT v4b: unrounded stamp (diagnostic only)

### diff gates.instrumented.ts gates.v5.ts
542a543,544
>     // VARIANT v5: a bare stamp push; no style, layout or DOM read
>     if (t >= 0) return { t, pathname: '', route: null, nodes: [], expectedHits: config.expected.map(() => false), dur: performance.now() - tx, n: 0 };

```

### Tally and decision-rule verdict

Rule, fixed before any run: a candidate is the cause when (i) removing it alone brings the probe set to 15 of 15 at 40 ms or less, in batches where the baseline probe misses 5 or more of 15 (read as the unit's own pooled control); and (ii) where a bottom-up variant exists, adding it alone to the bare timer brings the bare timer to 5 or more of 15.
Output of `run/verdict.py` (also `logs/wrap-B/verdict.txt`); per batch in brackets:

| unit | set | control misses (pooled; per batch) | variant misses (pooled; per batch) | control max | variant max | (i) | (ii) | note |
|---|---|---|---|---|---|---|---|---|
| c1-wait100 | probe | 6/15 (b1:2/5 b2:3/5 b3:1/5) | 0/15 (b1:0/5 b2:0/5 b3:0/5) | 65 | 40 | yes | |  |
| c2a-lazy-false | probe | 7/15 (b1:2/5 b2:2/5 b3:3/5) | 4/15 (b1:1/5 b2:1/5 b3:2/5) | 57 | 49 | no | |  |
| c2b-bare-track | bare | 1/15 (b1:1/5 b2:0/5 b3:0/5) | 0/15 (b1:0/5 b2:0/5 b3:0/5) | 44 | 39 | n/a (bare) | |  |
| c3a-noguard | probe | 7/15 (b1:3/5 b2:1/5 b3:3/5) | 3/15 (b1:1/5 b2:1/5 b3:1/5) | 48 | 53 | no | |  |
| c3b-nolisteners | probe | 8/15 (b1:4/5 b2:2/5 b3:2/5) | 5/15 (b1:0/5 b2:3/5 b3:2/5) | 59 | 55 | no | |  |
| c4a-raf | probe | 6/15 (b1:2/5 b2:1/5 b3:3/5) | 1/15 (b1:0/5 b2:0/5 b3:1/5) | 55 | 41 | no | | diagnostic only |
| c4b-unrounded | probe | 7/15 (b1:2/5 b2:4/5 b3:1/5) | 7/15 (b1:2/5 b2:3/5 b3:2/5) | 52 | 52 | no | | diagnostic only |
| c5-barestamp | probe | 4/15 (b1:1/5 b2:3/5 b3:0/5) | 5/15 (b1:2/5 b2:2/5 b3:1/5) | 50 | 65 | no | |  |
| c6a-mock50 | probe | 4/15 (b1:2/5 b2:1/5 b3:1/5) | 0/15 (b1:0/5 b2:0/5 b3:0/5) | 45 | 37 | no | |  |
| c6b-mock150 | probe | 4/15 (b1:1/5 b2:2/5 b3:1/5) | 1/15 (b1:1/5 b2:0/5 b3:0/5) | 48 | 45 | no | |  |
| c7a-preview | probe | 5/15 (b1:2/5 b2:1/5 b3:2/5) | 3/15 (b1:2/5 b2:0/5 b3:1/5) | 60 | 47 | no | |  |
| c7b-hmr-off | probe | 4/15 (b1:1/5 b2:2/5 b3:1/5) | 5/15 (b1:1/5 b2:1/5 b3:3/5) | 53 | 52 | no | |  |
| c8-preload | probe | 3/15 (b1:2/5 b2:1/5 b3:0/5) | 0/15 (b1:0/5 b2:0/5 b3:0/5) | 54 | 35 | no | | diagnostic only |
| c9-reduced | probe | 1/15 (b1:0/5 b2:1/5 b3:0/5) | 6/15 (b1:2/5 b2:2/5 b3:2/5) | 53 | 58 | no | |  |
| s1-bare-nowait | bare | 0/15 (b1:0/5 b2:0/5 b3:0/5) | 4/15 (b1:2/5 b2:1/5 b3:1/5) | 38 | 51 | n/a (bare) | |  |
| s3-bare-guard | bare | 0/15 (b1:0/5 b2:0/5 b3:0/5) | 0/15 (b1:0/5 b2:0/5 b3:0/5) | 36 | 36 | n/a (bare) | |  |

(ii) for c2a-lazy-false: bottom-up c2b-bare-track: bare timer with the factor added misses 0/15; needs >= 5 -> NOT met

Reading the table, candidate by candidate:

- **1 meets (i)**: control 6 of 15 (at least 5), variant 15 of 15 at 40 ms or less (maximum exactly 40). The plan's table lists no bottom-up variant for candidate 1, so (ii) does not apply. By the fixed rule, **candidate 1 is the cause.** The supplementary bare variant s1 (no wait) misses 4 of 15 against 0 of 15; if (ii) were applied to it, it would fall one short of 5.
- 2: variant 4 of 15 (not 0), and the bare timer with `trackRequests` misses 0 of 15, so neither (i) nor (ii).
- 3: 3 of 15 and 5 of 15, not 0.
- 4 (diagnostic only): rAF 1 of 15, unrounded 7 of 15. Neither is a fix by definition.
- 5: 5 of 15 (control 4 of 15). The per-tick reads are not the cause.
- 6a: 0 of 15, but its control missed 4 of 15, so (i) is not met by the letter; 6b: 1 of 15. Both are in the direction of 1.
- 7a: 3 of 15; 7b: 5 of 15. Not a dev-server effect (and see Deviations on 7b).
- 8 (diagnostic only): 0 of 15, control 3 of 15. Never a cause by the plan's own rule.
- 9: 6 of 15 against a control of 1 of 15: no.

The control rate itself varied from 1 of 15 to 8 of 15 between units. Time of run moves the baseline, which is why every unit has its own adjacent control, and why 6a (control 4 of 15) and 8 (control 3 of 15) are not read as causes.

**Combination.** Candidates 1, 6a and 8 each reach 0 of 15, 4a and 6b reach 1 of 15. What they share, from the trace below, is that each moves the trigger away from the moment the start page finishes starting up. Candidate 1 does it by waiting, 8 by spending time in an `import()` before the sampler starts, 6a/6b by moving the start page's data response in time. This is a reading of the pattern, not a separate measurement.

Per-candidate raw RED (control) and GREEN (variant) gaps, in ms, in run order (5 routes per batch; the full per-run lines with gap windows, long tasks and load are in `logs/wrap-B/tally.txt`):

**c1-wait100**
```
RED   control  (probe, baseline)  6 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=34 search=47 med=41 notif=32 care=34  |  timeline=43 search=62 med=30 notif=29 care=45  |  timeline=33 search=65 med=32 notif=38 care=29
GREEN variant  0 of 15 over 40 ms
      timeline=26 search=32 med=31 notif=38 care=29  |  timeline=34 search=40 med=23 notif=37 care=34  |  timeline=28 search=33 med=29 notif=30 care=34
```

**c2a-lazy-false**
```
RED   control  (probe, baseline)  7 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=54 search=44 med=28 notif=30 care=32  |  timeline=29 search=45 med=28 notif=53 care=28  |  timeline=49 search=57 med=36 notif=47 care=29
GREEN variant  4 of 15 over 40 ms
      timeline=29 search=48 med=36 notif=31 care=39  |  timeline=38 search=33 med=33 notif=43 care=29  |  timeline=29 search=49 med=39 notif=41 care=40
```

**c2b-bare-track**
```
RED   control  (bare, baseline)  1 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=31 search=44 med=28 notif=30 care=31  |  timeline=35 search=29 med=22 notif=35 care=31  |  timeline=28 search=27 med=30 notif=31 care=26
GREEN variant  0 of 15 over 40 ms
      timeline=30 search=39 med=24 notif=34 care=32  |  timeline=36 search=28 med=31 notif=32 care=35  |  timeline=25 search=37 med=35 notif=35 care=33
```

**c3a-noguard**
```
RED   control  (probe, baseline)  7 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=41 search=48 med=32 notif=45 care=27  |  timeline=26 search=39 med=34 notif=41 care=26  |  timeline=29 search=42 med=42 notif=33 care=46
GREEN variant  3 of 15 over 40 ms
      timeline=27 search=53 med=37 notif=33 care=31  |  timeline=37 search=41 med=35 notif=31 care=34  |  timeline=33 search=31 med=41 notif=28 care=31
```

**c3b-nolisteners**
```
RED   control  (probe, baseline)  8 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=42 search=55 med=43 notif=45 care=32  |  timeline=32 search=59 med=30 notif=31 care=44  |  timeline=28 search=35 med=33 notif=42 care=47
GREEN variant  5 of 15 over 40 ms
      timeline=27 search=27 med=31 notif=37 care=31  |  timeline=26 search=55 med=29 notif=42 care=51  |  timeline=28 search=42 med=43 notif=36 care=35
```

**c4a-raf**
```
RED   control  (probe, baseline)  6 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=49 search=46 med=35 notif=34 care=30  |  timeline=43 search=35 med=28 notif=28 care=30  |  timeline=33 search=49 med=34 notif=55 care=49
GREEN variant  1 of 15 over 40 ms
      timeline=32 search=40 med=32 notif=34 care=23  |  timeline=30 search=36 med=30 notif=30 care=33  |  timeline=28 search=38 med=41 notif=25 care=22
```

**c4b-unrounded**
```
RED   control  (probe, baseline)  7 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=40 search=52 med=31 notif=27 care=44  |  timeline=42 search=44 med=41 notif=38 care=44  |  timeline=35 search=42 med=29 notif=33 care=28
GREEN variant  7 of 15 over 40 ms
      timeline=29.4 search=49.3 med=36.3 notif=33.8 care=41.5  |  timeline=42.9 search=52 med=24.2 notif=46.5 care=28.6  |  timeline=32.1 search=48.3 med=33.9 notif=46.8 care=33.5
```

**c5-barestamp**
```
RED   control  (probe, baseline)  4 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=28 search=42 med=30 notif=30 care=30  |  timeline=29 search=45 med=42 notif=50 care=27  |  timeline=28 search=28 med=33 notif=29 care=34
GREEN variant  5 of 15 over 40 ms
      timeline=38 search=51 med=32 notif=49 care=34  |  timeline=39 search=54 med=28 notif=44 care=32  |  timeline=39 search=65 med=31 notif=28 care=28
```

**c6a-mock50**
```
RED   control  (probe, baseline)  4 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=28 search=42 med=34 notif=27 care=45  |  timeline=32 search=39 med=41 notif=28 care=32  |  timeline=31 search=42 med=29 notif=32 care=31
GREEN variant  0 of 15 over 40 ms
      timeline=28 search=28 med=33 notif=29 care=30  |  timeline=31 search=28 med=37 notif=32 care=27  |  timeline=37 search=30 med=34 notif=33 care=30
```

**c6b-mock150**
```
RED   control  (probe, baseline)  4 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=47 search=32 med=31 notif=31 care=27  |  timeline=27 search=48 med=42 notif=36 care=35  |  timeline=27 search=45 med=27 notif=32 care=40
GREEN variant  1 of 15 over 40 ms
      timeline=30 search=30 med=45 notif=27 care=33  |  timeline=26 search=28 med=34 notif=30 care=30  |  timeline=32 search=29 med=35 notif=28 care=28
```

**c7a-preview**
```
RED   control  (probe, baseline)  5 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=33 search=42 med=36 notif=44 care=33  |  timeline=27 search=48 med=31 notif=31 care=36  |  timeline=33 search=60 med=45 notif=33 care=31
GREEN variant  3 of 15 over 40 ms
      timeline=41 search=40 med=36 notif=33 care=47  |  timeline=28 search=30 med=35 notif=35 care=31  |  timeline=38 search=44 med=36 notif=27 care=39
```

**c7b-hmr-off**
```
RED   control  (probe, baseline)  4 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=39 search=44 med=35 notif=30 care=31  |  timeline=28 search=42 med=36 notif=32 care=53  |  timeline=33 search=40 med=34 notif=45 care=34
GREEN variant  5 of 15 over 40 ms
      timeline=41 search=40 med=30 notif=26 care=39  |  timeline=36 search=30 med=33 notif=48 care=26  |  timeline=30 search=52 med=41 notif=34 care=42
```

**c8-preload**
```
RED   control  (probe, baseline)  3 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=31 search=54 med=30 notif=46 care=28  |  timeline=44 search=33 med=29 notif=36 care=35  |  timeline=27 search=34 med=30 notif=30 care=32
GREEN variant  0 of 15 over 40 ms
      timeline=34 search=27 med=32 notif=33 care=35  |  timeline=30 search=29 med=25 notif=31 care=27  |  timeline=35 search=31 med=25 notif=30 care=25
```

**c9-reduced**
```
RED   control  (probe, baseline)  1 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=29 search=36 med=40 notif=40 care=40  |  timeline=31 search=53 med=33 notif=29 care=32  |  timeline=31 search=34 med=39 notif=28 care=33
GREEN variant  6 of 15 over 40 ms
      timeline=29 search=44 med=42 notif=40 care=28  |  timeline=40 search=44 med=31 notif=48 care=28  |  timeline=40 search=58 med=35 notif=29 care=49
```

**s1-bare-nowait**
```
RED   control  (bare, baseline)  0 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=30 search=30 med=26 notif=30 care=38  |  timeline=26 search=36 med=24 notif=31 care=32  |  timeline=36 search=37 med=26 notif=33 care=32
GREEN variant  4 of 15 over 40 ms
      timeline=32 search=51 med=44 notif=29 care=28  |  timeline=29 search=34 med=42 notif=31 care=28  |  timeline=33 search=20 med=42 notif=27 care=39
```

**s3-bare-guard**
```
RED   control  (bare, baseline)  0 of 15 over 40 ms   batch 1 | batch 2 | batch 3
      timeline=32 search=29 med=28 notif=25 care=36  |  timeline=35 search=31 med=24 notif=30 care=33  |  timeline=30 search=33 med=25 notif=35 care=36
GREEN variant  0 of 15 over 40 ms
      timeline=36 search=27 med=25 notif=33 care=27  |  timeline=33 search=33 med=35 notif=26 care=33  |  timeline=35 search=26 med=22 notif=33 care=33
```

## Trace finding (step 4, wraps C, D and E)

Chromium CDP Tracing (`browser.startTracing`; categories `devtools.timeline`, `disabled-by-default-devtools.timeline`, `v8.execute`, `blink.user_timing`, `toplevel`) of the baseline probe. A trace adds overhead: it names the work and counts no misses. The page clock is mapped to the trace with a `performance.mark('snl-anchor')` inside the traced page (`run/trace_summary.py`).

- **Wrap C** (the brief's step): 10 baseline probe runs over the 5 routes, the first 3 misses kept: `care` 43 ms, `notif` 42 ms, `care` 42 ms (3 of 10 over 40 ms under tracing). All three are click routes.
- **Wrap E** (added by the implementer after reading wrap C): `/search` is the route of 31 of the 71 baseline misses and of every CI miss, and wrap C kept no `/search` miss. 5 baseline probe runs on `/search` traced, 3 misses (56, 44, 44 ms), all kept.
- **Wrap D** (added): 9 comparison traces of runs that were kept whatever their gap: the baseline probe, the probe with candidate 1's wait, and the bare timer, on `/search`, `/timeline` and `/care-tasks`.

The six miss traces are committed gzipped (`logs/wrap-C/*.json.gz`, `logs/wrap-E/*.json.gz`, 0.23 to 0.35 MB each); the nine wrap-D traces (2.7 to 3.2 MB raw each) are not committed, only their summary. Summaries: `logs/trace-summary-3-baseline-misses.txt` (wrap C), `logs/trace-summary-search-misses.txt` (wrap E), `logs/trace-summary-comparison.txt` (wrap D).

**What fills the gap.** The gap window is `[-9, 34]`, `[-9, 33]` and `[-8, 34]` ms around the trigger for the three click-route misses (main-thread `RunTask` time is 99 % of it), `[-8, 36]` and `[-9, 35]` for two `/search` misses (99 %), and `[-49, 7]` for the third (77 %). In each, the same sequence:

1. a layout task, `Layout` 2.9 to 3.9 ms and `UpdateLayoutTree` 0.7 to 1.4 ms (browser work);
2. one task of 19 to 26 ms, an anonymous function in the react-dom dev prebundle `node_modules/.vite/deps/chunk-IZHK4E3M.js`, line 18676 (trace `lineNumber` 18675, zero-based). Reading the source, it is `scheduleMicrotask(function () {{ ... flushSyncCallbacks(); }})`, React's microtask that flushes a synchronous render. 17.5 to 23.9 ms is that function itself, and `@tanstack_react-query.js:618` (the notify batch) is nested in it: a react-query result set state that React rendered synchronously;
3. then `UpdateLayoutTree` 1.0 to 1.9 ms, `Layout` 1.1 to 1.7 ms, framer-motion `processBatch` (`framer-motion.js:1146`), `Paint`/`Layerize`, and React's scheduler `performWorkUntilDeadline` (`chunk-IZHK4E3M.js:377`) 1.2 to 2.5 ms.

**The trigger is not in the window.** First dispatch of the trigger's events, relative to the trigger stamp:

| Traced run | Max gap | Gap window | Trigger events dispatched at |
|---|---|---|---|
| miss, `care` (C) | 43 | -9..34 | `pointerover` +69, `click` +71 |
| miss, `notif` (C) | 42 | -9..33 | `pointerover` +62, `click` +64 |
| miss, `care` (C) | 42 | -8..34 | `pointerover` +62, `click` +65 |
| miss, `/search` (E) | 56 | -49..7 | `focusin` +24, `keydown` +34 |
| miss, `/search` (E) | 44 | -8..36 | `focusin` +42, `keydown` +51 |
| miss, `/search` (E) | 44 | -9..35 | `focusin` +37, `keydown` +50 |
| bare timer, `timeline` / `care` (D) | 32 / 30 | 18..50 / 38..67 | `pointerover` +37 / +43, `click` +40 / +46 |
| probe with the wait, `timeline` / `care` (D) | 30 / 30 | 39..69 / 38..68 | `pointerover` +41 / +40, `click` +43 / +43 |
| bare timer, `/search` (D) | 33 | 15..48 | `input` +11, `keydown` +20 |

In the runs that did not miss, the click dispatches 40 to 46 ms after the trigger stamp (Playwright's actionability steps) and the gap window holds light tasks only (24 to 77 % busy). In the misses the 20 ms render delays the click to +64 to +78 ms (the two D baseline runs on `timeline` and `care`, 40 and 47 ms, click at +77 and +78). The target route's chunk is requested at +84 to +93 ms in the click-route misses. So the maximum gap of a miss is the start page's render, which runs while the sampler waits for an input event that has not been dispatched yet.
One `/search` run with the 100 ms wait did miss under tracing (44 ms, D): its window `[-3, 41]` holds the `input`/`keydown`/`submit` events at +9 to +14 ms and `performWorkUntilDeadline` tasks of 4.6 and 8.2 ms. So the wait does not make the page change cost nothing; it removes the start page's render from the window, and `/search`, whose input events fire early, can still reach the bound with its own render work. Candidate 1's 15 runs reached 40 ms at the most (`/search` 32, 40, 33 against 47, 62, 65 for the control).

**What the work belongs to.** `useHighlightsSummary` is called by the start page, `pages/DocumentInbox.tsx:68`, and `/api/v1/documents/` is its list query. In the three traced click-route misses both responses end at -2, +2 and +2 ms relative to the trigger; in the three `/search` misses the documents response ends at -26, -1 and +2 ms (`REQLOG` in the `logs/wrap-*/*.jsonl` rows). Post hoc and only correlational, over the 210 baseline probe runs of waves A and B: where the documents response ended within 10 ms of the trigger, 16 of 20 runs missed; where it ended more than 10 ms after the trigger, 49 of 162 missed; where no documents request was seen after the tracker started (the start page had already settled), 6 of 28 missed. The documents response lands after the trigger in most runs (median 19 ms after it; 182 of 210 runs have one): at trigger time the start page is usually still loading its lazy chunk and its data. The page-change cost itself shows later (click at about +40 ms in a clean run, chunk request at about +90 ms), outside the maximum gap in these runs.

Compared with the bare timer: its 100 ms wait absorbs this work, and its gap window (15 to 67 ms) holds the input dispatch and a few 1 to 8 ms tasks.

This names the work and agrees with the HC-UIOV-007 finding folded into this row (Task 3's delta: "the stall is page startup", "the maximum gap starts 54-92 ms before the click"). It does not name a component inside DocumentInbox: the trace has no CPU profile.

## Cause (Task 1 verdict)

**By the fixed decision rule: candidate 1, the time between starting the sampler and triggering.** In mechanism: the probe starts the sampler and triggers in the same breath after the shell is visible, while the start page (a lazy route that fetches data) is still starting up. Its render, about 20 ms of synchronous React plus layout, lands in the window before the click is even dispatched, and the straddling gap is counted against the page change. It is not the sampler's per-tick cost (candidates 4b, 5), not the request tracking or the guard (2, 3), not the mock timing as such (6 shifts it), not HMR or the dev server (7a), not the route transition's reduced-motion path (9).
The row's wording "page changes run late" is, on this evidence, a harness readiness gap: the work in the maximum gap is the start page's, not the target page's.

## Proposed Task 2 (for the L0 ruling)

- **Kind: PRODUCT (e2e harness). No app code.** The trace points at no app file to change.
- **Fix shape: the probe must start from a settled start page.** Wait, before the sampler starts, for the start page to finish its own startup: no request in flight for `NETWORK_IDLE_MS` and the route container's entrance fade finished (`settleRoute`'s condition, opacity at least 0.99). The sampler still starts before the trigger and samples the whole page change, with the same window, interval, gap arithmetic and bounds. That makes the probe wait longer, not see less; it is the same idea as Task 3's `settleRoute` plus `fonts.ready` for HC-UIOV-007.
- **Files, two options for the ruling:**
  1. `src/frontend/e2e/support/gates.ts`, `stillnessProbe`, a pre-sampler settle step (covers every caller: HC-UISH-009, the phone variant, HC-UIOV-007, the HC-UIG self-tests' probes). Needs the L0 ruling to name it (plan Task 2 step 2) and must not touch `STILLNESS_SAMPLE_MS`, `STILLNESS_WINDOW_MS`, `NETWORK_IDLE_MS`, the lazy-route rule, `snapshot`'s `Math.round`, `checkSampling` or which samples count. The HC-UIG-006/007 self-tests and GATES-NAV-BOUND's navigation self-tests stay unchanged.
  2. `src/frontend/e2e/ui-shell.spec.ts`, HC-UISH-009 only (and the phone case at the same pattern), adding the settle before the probe. That file is held by UI-PALETTE #399 and UI-PG-ASK #453 (queue rule 2), and Task 3 edits it too.
- **A fixed 100 ms wait was measured (candidate 1) and is not proposed.** A condition-based settle is what the trace supports; it will be measured as Task 2's GREEN, not assumed from candidate 1.
- **Task 2's RED** is the unchanged instrumented set run from the committed copy: `/tmp/claude-1000/quiet_run.sh --max-wait 7200 bash docs/reviews/2026-11-02/stillness-nav-evidence/run/run_wrap.sh A <logdir>` (3 batches, 5 routes, probe and bare back to back), judged per run against 40 ms. A pooled baseline of 5 of 15 is thin; the wrap B controls (66 of 195) are the stronger RED, and Task 2 may want a larger RED. The fix is judged by 15 of 15 at 40 ms or less, on dev and on `vite preview`.
- Not proposed and not needed: any change to a bound, any `fixme`, any retry.

## NAV70-CI-MISS (CI evidence for this row)

From docs/plans/2026-10-30-followups-plan.md, CI misses of HC-UISH-009 at the 70 ms bound, `retries: 0`, dev server. This task did not run on CI, so "explained" here means: does the found cause account for the gap?

| Run, attempt | Branch (PR) | Failing case | Gap | Explained by the found cause? |
|---|---|---|---|---|
| 40729283791, 1 | `test/vitest-tz-pin-config-pin` (#396) | `ui-shell.spec.ts:318`, `/search` | 72 ms | Consistent, not shown. `/search` is the route where this cause bites most (local control 28 of 39 over 40 ms, maximum 65). No local run reached 70 ms, so a 72 ms gap needs a longer start-page render on the CI runner than any run here; there is no CI trace. |
| 40729283791, 2 | same | same | 77 ms | Same as above. A second miss on the same head, the same route. |
| 40845146715, 1 | **`main`**, push of `760655c7` (#409 merge) | same | 71 ms | Same as above. Shows it is not a PR-branch artefact. |
| 40920267687, 1 | `docs/post-merge-batch-1029` (#411) | same | 71 ms | Same as above. A docs post-merge batch branch (by its name) misses too, which fits a harness-start cause and not a branch change. |

What this supports: all four are `/search` on the dev server with a trigger that is `fill` plus Enter; this row finds `/search` the most exposed route (72 % over 40 ms locally). What it does not show: the size. Locally the maximum over 431 probe runs is 65 ms and none reached 70 ms. The CI runner "adds a pause the quiet box did not show" (followups plan); the likeliest reading is that the start page's startup takes longer there, but that is untested. A Task 2 fix that removes the start page's work from the window would remove these misses if that reading is right; the after-merge count of 60 E2E attempts is the test of it.

## Box state per batch

All wraps ran inside `quiet_run.sh` (hold_slots takes every test slot first, then waits for 1-minute load below 1.5, no foreign playwright/vite/pytest/uvicorn worker, no listener on 3000/4173/5173/8000). Before each batch `run_wrap.sh` waited (bounded at 30 minutes; never reached) for the 1-minute load to be below 1.5 and logged `uptime`, `pgrep -fa '[p]laywright|[v]ite|[p]ytest|[c]hrom|[c]argo|[r]ustc|[r]ust-lld'` and `ss -ltnp`, marking its own PIDs `[mine]`. The full text is in `logs/wrap-*/*.precheck.log`.
The `[FOREIGN]` lines in those prechecks were never a running worker: they are other sessions' tool shells whose command text contains one of the pgrep words, and `pyslot.sh ... pytest|vitest` wrappers queued on the slots that quiet_run held. No foreign chrome, playwright, vite, cargo or rustc process was listed in any precheck. The implementer's own tool shell is among the tool shells.

| Batch | Precheck at (PST) | Load 1/5/15 min at precheck | Foreign test/browser workers listed | Load 1 min, first to last run | Load 1 min at batch end |
|---|---|---|---|---|---|
| warm-up A (uncounted) | 17:27:04 | 1.38 / 2.93 / 5.39 | none | 2.16 to 2.79 (first 2.56, last 2.79) | 2.79 |
| A1 | 17:29:22 | 1.26 / 2.53 / 4.92 | none | 1.23 to 1.37 (first 1.28, last 1.26) | 1.26 |
| A2 | 17:29:56 | 1.26 / 2.39 / 4.79 | none | 1.21 to 1.69 (first 1.69, last 1.21) | 1.21 |
| A3 | 17:30:31 | 1.21 / 2.26 / 4.65 | none | 2.84 to 5.84 (first 3.09, last 5.84) | 5.84 |
| warm-up B (uncounted) | 17:49:23 | 1.39 / 2.56 / 4.67 | none | 1.27 to 3.23 (first 1.41, last 3.05) | 3.45 |
| B1 | 17:52:55 | 1.29 / 2.27 / 4.15 | none | 0.88 to 2.96 (first 1.32, last 2.22) | 2.22 |
| B2 | 17:58:54 | 1.34 / 1.73 / 3.31 | none | 0.73 to 1.99 (first 1.37, last 1.73) | 1.73 |
| B3 | 18:04:38 | 1.42 / 1.44 / 2.69 | none | 0.90 to 2.65 (first 1.48, last 1.11) | 1.11 |
| warm-up C (uncounted) | 18:14:57 | 1.15 / 2.47 / 2.67 | none | 1.34 to 1.63 (first 1.45, last 1.51) | 1.51 |
| C1 traces | 18:15:55 | 1.18 / 2.29 / 2.60 | none | 0.96 to 1.28 (first 1.14, last 1.18) | 1.33 |
| warm-up D (uncounted) | 18:44:20 | 1.44 / 12.73 / 13.07 | none | 1.08 to 1.55 (first 1.55, last 1.08) | 1.08 |
| D1 comparison traces | 18:45:02 | 1.08 / 11.24 / 12.55 | none | 1.06 to 1.43 (first 1.06, last 1.29) | 1.29 |
| D2 CDP count | 18:45:36 | 1.29 / 10.17 / 12.14 | none | 1.50 to 1.55 (first 1.55, last 1.50) | 1.50 |
| warm-up E (uncounted) | 19:15:07 | 1.15 / 2.32 / 5.74 | none | 1.15 to 1.62 (first 1.27, last 1.37) | 1.37 |
| E1 /search traces | 19:15:48 | 1.37 / 2.23 / 5.57 | none | 1.18 to 1.29 (first 1.29, last 1.18) | 1.09 |

Notes: the warm-up rows are uncounted. **A3**: the load rose from 1.21 (precheck) to 3.09 at its first run and 5.84 at its end, with no foreign worker listed at the precheck; the cause is not identified. The batch is kept as run; the bare timer, which ran second in that batch at load 3.9 to 5.8, still missed 0 of 5. The 5-minute and 15-minute loads at the D prechecks (10 to 13) are the residue of other sessions' work that finished before the wrap started.

## Deviations and things L0 should know

- **Counted runs: 539**: A 30, B 480, C 10 (traced baseline probe), D 9 (traced comparison) + 5 (CDP count), E 5 (traced `/search` baseline). Uncounted and declared warm-ups: 10 (A) + 30 (B) + 10 (C) + 10 (D) + 10 (E). Disclosed, not used in any tally: the aborted first wrap B (88 runs in `logs/wrap-B-attempt1-aborted/`).
- **Aborted wrap B.** The first wrap B's warm-up batch ran zero cases because `gen_plan.py` gave the three servers' warm-up cases the same test id ("duplicate test title"); B1 then started without a warm-up. The implementer stopped it (TERM to its own process group, then its own server PIDs) at 88 of B1's 160 runs, fixed the id (`f942c6ea`) and reran the whole wrap. The aborted runs' tally is in `logs/wrap-B-attempt1-aborted/tally.txt`; they show the same pattern (controls 1 to 4 of 5 over 40 ms, c1 variant 0 of 5).
- **Wrap C's CDP message count failed** (an unquoted path in `run_wrap.sh`'s awk filter; 0 runs executed in C2). It is redone in wrap D (`D2`). Wrap D also added the nine comparison traces (baseline probe, probe with candidate 1's wait, bare timer; 3 routes each; kept whatever their gap), and wrap E added the `/search` miss traces (20 planned, 5 run, the first 3 misses kept; the other 15 were not run). These were not in the brief and are diagnostics; they add runs, they do not change any tally above.
- **Harness smoke runs (uncounted, discarded).** While building `run/`, 4 invocations (about 30 cases in all) ran under `scripts/pyslot.sh` on a private dev server (port 3190), on a box that was not quiet, to check the spec ran end to end. Their numbers were not used.
- **Candidate 7b did not show a closed HMR socket.** The server was started with `server.hmr: false`, but the page still opened one WebSocket (the warm-up counts 1 on 3000 and 1 on 3001), so whether it was closed or merely failing is not shown. Read 7b as "dev server with HMR configured off", not as proof of an idle or closed socket. 7a (preview) carries the dev-server question.
- **Candidate 6's request timing** is in every probe run's `REQLOG` (request start and end relative to the trigger, from `trackRequests`' own listeners; it needs `lazyRoute`, so it is absent in c2a, c3b and for bare runs). The page and wall clocks are aligned by two reads a few ms apart.
- **Probe and bare timer differ by the guard.** The bare timer has no guard listeners (as L0's); the probe has them (`openRoute`). That is candidate 3's factor, measured by c3a, c3b and s3.
- **Instrumented gates are not identical to `gates.ts` in one respect beyond the PROBECOST line:** `trackRequests` also records each request's start and end for `REQLOG`. It adds an array push to listeners that already ran.
- **Mock delay (candidate 6)** is a second `page.route` for `/api/v1/` registered after the mock that sleeps and calls `route.fallback()`. It adds one hop per request, not only the delay.
- **Raw traces:** only the six miss traces are committed (gzipped). The nine wrap-D traces, and the raw copies of the six, were moved out of the tree to `/tmp/claude-1000/snl-traces/` (volatile).
- **Aggregates of 1 and 3 misses are small** and the baseline rate drifts between units (1 of 15 to 8 of 15). The conclusions rest on the 195-run control pool, the adjacent controls, and the trace, not on any single 15.

## Files in this directory

- `l0-2026-10-27/`: the recovered L0 evidence and `RECOVERY.md`.
- `run/`: `nav-sets.spec.ts` (both sets and all flags), `gates.instrumented.ts`, `build_instrumented.py`, `make_variants.py`, `gen_plan.py`, `run_wrap.sh`, `playwright.config.ts`, `tally.py`, `verdict.py`, `trace_summary.py`, `cdp_count.awk`, and the diff pastes. Task 2's RED runs from here: the script copies `run/` to a scratch directory with `node_modules` and `src` symlinked, and writes only to its log directory.
- `logs/`: per wrap, per batch `*.jsonl` (one JSON row per run), `*.log` (Playwright output, `PROBECOST`/`REQLOG`/`RESULT` lines), `*.precheck.log`, `tally.txt`, plus `wrap-B/verdict.txt`, the trace summaries and the six gzipped miss traces.
