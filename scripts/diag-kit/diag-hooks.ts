// ---- MEDS-G diagnosis hooks (from UIDOC-006A-FLAKE Task 1). This is the committed kit copy; it is appended to a spec only in a throwaway diag worktree, never committed into a spec. ----
// ---- MEDS-G diagnosis hooks (copied from UIDOC-006A-FLAKE Task 1) (scratch, NOT committed). Appended to a spec in the diag worktree. ----
// File-level hooks: they do not change any test body or bound. HC_PROBE_CPU=<n> sets CDP CPU throttling for the whole
// test (re-applied on every load); HC_DIAG_TRACE=1 records a Chromium trace with the V8 sampling profiler.
// afterEach dumps every stillnessProbe sampler state (window.__hcStill is archived by an init-script setter) with
// its largest sample gaps, plus long-task and long-animation-frame entries, to $HC_DIAG_OUT/<test>-r<repeat>.json.
test.beforeEach(async ({ page, browser }, testInfo) => {
  const cpu = Number(process.env.HC_PROBE_CPU ?? '1');
  await page.addInitScript(() => {
    const w = window as unknown as Record<string, unknown>;
    const all: unknown[] = [];
    let cur: unknown;
    Object.defineProperty(w, '__hcStillAll', { value: all });
    Object.defineProperty(w, '__hcStill', { configurable: true, get: () => cur, set: (v) => { cur = v; all.push(v); } });
    const lt: unknown[] = [];
    const loaf: unknown[] = [];
    Object.defineProperty(w, '__hcLT', { value: lt });
    Object.defineProperty(w, '__hcLoAF', { value: loaf });
    try {
      new PerformanceObserver((l) => { for (const e of l.getEntries()) lt.push({ s: e.startTime, d: e.duration }); }).observe({ type: 'longtask', buffered: true });
    } catch { /* unsupported */ }
    try {
      new PerformanceObserver((l) => {
        for (const e of l.getEntries() as unknown as { startTime: number; duration: number; blockingDuration: number; renderStart: number; styleAndLayoutStart: number; scripts: { invoker: string; sourceFunctionName: string; sourceURL: string; duration: number; forcedStyleAndLayoutDuration: number; startTime: number }[] }[]) {
          loaf.push({ s: e.startTime, d: e.duration, block: e.blockingDuration, renderStart: e.renderStart, styleAndLayoutStart: e.styleAndLayoutStart,
            scripts: e.scripts.map((x) => ({ inv: x.invoker, fn: x.sourceFunctionName, url: x.sourceURL.split('/').pop(), s: x.startTime, d: x.duration, forced: x.forcedStyleAndLayoutDuration })) });
        }
      }).observe({ type: 'long-animation-frame', buffered: true });
    } catch { /* unsupported */ }
  });
  if (process.env.HC_DIAG_WARM === '1') {
    // A/B only: what a product-side idle warm-up of the ICU date/time formatters would do (ResultsPage.tsx warmExplainClick pattern).
    await page.addInitScript(() => {
      addEventListener('load', () => setTimeout(() => {
        // RemindersPanel.tsx:515 formats with toLocaleString() and no arguments; warm exactly that formatter.
        void new Date(0).toLocaleString();
      }, 0));
    });
  }
  if (cpu > 1) {
    const cdp = await page.context().newCDPSession(page);
    const apply = () => cdp.send('Emulation.setCPUThrottlingRate', { rate: cpu }).catch(() => undefined);
    await apply();
    page.on('load', () => void apply());
  }
  if (process.env.HC_DIAG_TRACE === '1') {
    await browser.startTracing(page, {
      path: `${process.env.HC_DIAG_OUT ?? '/dev/shm/uidoc-diag'}/L${testInfo.line}_${testInfo.title.replace(/[^A-Za-z0-9]+/g, '_').slice(0, 24)}_${testInfo.title.replace(/[^A-Za-z0-9]+/g, '_').slice(-24)}-r${testInfo.repeatEachIndex}.trace.json`,
      categories: ['devtools.timeline', 'disabled-by-default-devtools.timeline', 'blink.user_timing', 'toplevel', 'v8.execute', 'disabled-by-default-v8.cpu_profiler', 'blink', 'loading', 'v8'],
    });
  }
});

test.afterEach(async ({ page, browser }, testInfo) => {
  const fs = await import('node:fs');
  const out = process.env.HC_DIAG_OUT ?? '/dev/shm/uidoc-diag';
  fs.mkdirSync(out, { recursive: true });
  const name = `L${testInfo.line}_${testInfo.title.replace(/[^A-Za-z0-9]+/g, '_').slice(0, 24)}_${testInfo.title.replace(/[^A-Za-z0-9]+/g, '_').slice(-24)}-r${testInfo.repeatEachIndex}`;
  const data = await page
    .evaluate(() => {
      performance.mark('hc-align');
      const w = window as unknown as { __hcStillAll?: { snaps: { t: number; nodes: unknown[] }[] }[]; __hcLT?: unknown[]; __hcLoAF?: unknown[] };
      const calls = (w.__hcStillAll ?? []).map((st) => {
        const t = st.snaps.map((s) => s.t);
        const gaps = t.slice(1).map((v, i) => ({ a: t[i], b: v, g: v - t[i], nodes: st.snaps[i + 1].nodes.length })).sort((x, y) => y.g - x.g);
        return { first: t[0], last: t[t.length - 1], samples: t.length, maxNodes: Math.max(...st.snaps.map((s) => s.nodes.length)), top: gaps.slice(0, 4) };
      });
      const align = performance.getEntriesByName('hc-align').pop()?.startTime ?? null;
      return { calls, lt: w.__hcLT ?? [], loaf: w.__hcLoAF ?? [], align, marks: performance.getEntriesByType('mark').map((m) => ({ n: m.name, s: m.startTime })) };
    })
    .catch((e) => ({ error: String(e) }));
  if (process.env.HC_DIAG_TRACE === '1') await browser.stopTracing().catch(() => undefined);
  const rec = { name, status: testInfo.status, error: testInfo.error?.message?.split('\n').slice(0, 3).join(' | ') ?? null, cpu: process.env.HC_PROBE_CPU ?? '1', ...data };
  fs.writeFileSync(`${out}/${name}.json`, JSON.stringify(rec));
  const calls = (data as { calls?: { top: { g: number; a: number }[]; samples: number; maxNodes: number }[] }).calls ?? [];
  console.log(`DIAG ${name} status=${testInfo.status} cpu=${rec.cpu} gaps=[${calls.map((c) => `${c.top[0]?.g}@${c.top[0]?.a}(n${c.maxNodes},s${c.samples})`).join(' ')}] err=${rec.error ?? ''}`);
});
