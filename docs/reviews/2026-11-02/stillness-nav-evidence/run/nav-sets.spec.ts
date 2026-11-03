// STILLNESS-NAV-LATE Task 1 (MEASURE). Measurement spec, not a product check: it never asserts a bound.
//
// One test per case in the plan file (env MEAS_PLAN_FILE). Each case is one fresh page (Playwright gives every
// test a new context) and writes one RESULT line (stdout, and the file MEAS_OUT when set).
//
//   set 'probe': today's HC-UISH-009 (e2e/ui-shell.spec.ts:319-333) with the instrumented stillnessProbe:
//                openRoute(startPageFor(route)), wait for RAIL, document.fonts.ready, then
//                stillnessProbe({ trigger: navigateTo, expected: [RAIL, TOGGLE_NOTE], kind: 'navigation', lazyRoute: true }).
//   set 'bare' : L0's bare timer (2026-10-27 baretimer.spec.ts) on the same start pages, trigger, mock API and
//                viewport: a 20 ms setInterval pushing performance.now(), 100 ms wait, trigger, 1500 ms, max gap.
//
// Flags (case.flags) change ONE thing each from the baseline of their set; the plan's candidate numbers in brackets:
//   gates:<name>  use e2e/support/gates.<name>.ts (make_variants.py): v1 [1], v4a/v4b [4], v5 [5]; nosettle [Task 2 mutant: the navigation settle removed]
//   lazy:false    probe without lazyRoute: no trackRequests listeners, no network-idle wait [2]
//   noguard       probe without the consoleAndNetworkGuard listeners that openRoute attaches [3]
//   guard         bare timer WITH those guard listeners [3, supplementary]
//   track         bare timer with trackRequests' three listeners (request, requestfinished, requestfailed) [2]
//   nowait        bare timer without the 100 ms wait: timer start, t0 read and trigger back to back [1, supplementary]
//   mockdelay:N   every /api/v1 mock response fulfilled N ms late [6]
//   preload       the route's lazy chunk imported before the sampler starts (diagnostic only) [8]
//   reduced       page.emulateMedia({ reducedMotion: 'reduce' }) [9]
//   trace         CDP Tracing (devtools.timeline) around the probe; the trace is kept only if maxGap > 40 [step 4]
//   cdpcount      writes SNL-MARK lines to stderr around the probe so DEBUG=pw:protocol output can be counted [3]
import { expect, test, type Page } from '@playwright/test';
import * as fs from 'fs';
import * as gatesBase from './e2e/support/gates';
import * as gatesV1 from './e2e/support/gates.v1';
import * as gatesV4a from './e2e/support/gates.v4a';
import * as gatesV4b from './e2e/support/gates.v4b';
import * as gatesV5 from './e2e/support/gates.v5';
import * as gatesNosettle from './e2e/support/gates.nosettle';
const { consoleAndNetworkGuard } = gatesBase;
import { installMockApi, seedMockSession } from './e2e/support/mockApi';

type Case = {
  id: string;
  set: 'probe' | 'bare';
  unit: string;
  role: string; // warmup | base | control | variant
  batch: number;
  route: string;
  base: string;
  flags: string[];
};

const PLAN: Case[] = JSON.parse(fs.readFileSync(process.env.MEAS_PLAN_FILE || '/dev/null', 'utf8') || '[]');
const OUT = process.env.MEAS_OUT || '';
const TRACE_DIR = process.env.MEAS_TRACE_DIR || '';
const TRACE_KEEP_MAX = Number(process.env.MEAS_TRACE_KEEP_MAX || '3');
/** A trace is kept only when the run's maximum gap is over this (ms). Lowered only by the harness smoke test. */
const TRACE_KEEP_OVER_MS = Number(process.env.MEAS_TRACE_KEEP_OVER_MS || '40');
let tracesKept = 0;
const TRACE_CATEGORIES = ['-*', 'devtools.timeline', 'disabled-by-default-devtools.timeline', 'v8.execute', 'blink.user_timing', 'toplevel'];
let configPrinted = false;

// ---- helpers copied from e2e/ui-shell.spec.ts (not imported: importing that spec would register its tests) ----
const RAIL = '[data-safety-rail]';
const TOGGLE_NOTE = '[data-safety-toggle-note]';
const NAV_LABEL: Record<string, string> = {
  '/timeline': 'Timeline',
  '/notifications': 'Reminders',
  '/care-tasks': 'Follow-ups',
};

function visibleNav(page: Page) {
  return page.getByRole('navigation', { name: 'Main navigation' });
}

async function navigateTo(page: Page, route: string): Promise<void> {
  if (route === '/search') {
    await page.getByRole('banner').getByRole('searchbox').fill('migraine');
    await page.keyboard.press('Enter');
    return;
  }
  if (route === '/medications/med-fixture-1') {
    // No nav item leads here; the detail page is reached from a medication row, which the mock does not list.
    await page.evaluate(() => {
      window.history.pushState({}, '', '/medications/med-fixture-1');
      window.dispatchEvent(new PopStateEvent('popstate', { state: {} }));
    });
    return;
  }
  await visibleNav(page).getByRole('link', { name: NAV_LABEL[route], exact: true }).click();
}

/** A route is always reached from a different page, so the click is a real route change. */
function startPageFor(route: string): string {
  return route === '/inbox' ? '/verify' : '/inbox';
}

/** The lazy page module each route renders (src/App.tsx), for the `preload` flag. */
const CHUNK: Record<string, string> = {
  '/timeline': '/src/pages/TimelinePage.tsx',
  '/search': '/src/pages/SearchPage.tsx',
  '/medications/med-fixture-1': '/src/pages/MedicationDetail.tsx',
  '/notifications': '/src/pages/NotificationSettings.tsx',
  '/care-tasks': '/src/pages/CareTasksPage.tsx',
};
// ---------------------------------------------------------------------------------------------------------------

const has = (c: Case, flag: string) => c.flags.includes(flag);
const val = (c: Case, prefix: string) => c.flags.find((f) => f.startsWith(prefix))?.slice(prefix.length);
const load1 = () => Number(fs.readFileSync('/proc/loadavg', 'utf8').split(' ')[0]);
const sleepMs = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

function loadGates(name: string | undefined) {
  switch (name) {
    case 'v1':
      return gatesV1;
    case 'v4a':
      return gatesV4a;
    case 'v4b':
      return gatesV4b;
    case 'v5':
      return gatesV5;
    case 'nosettle':
      return gatesNosettle;
    case undefined:
      return gatesBase;
    default:
      throw new Error(`unknown gates variant ${name}`);
  }
}

/** Same long-task observer in both sets (the bare timer had it; the long-animation-frame one adds script attribution). */
async function installObservers(page: Page) {
  await page.evaluate(() => {
    const w = window as unknown as { __lt: number[][]; __loaf: unknown[] };
    w.__lt = [];
    w.__loaf = [];
    try {
      new PerformanceObserver((list) => {
        for (const e of list.getEntries()) w.__lt.push([Math.round(e.startTime), Math.round(e.duration)]);
      }).observe({ type: 'longtask', buffered: false });
    } catch {
      /* unsupported */
    }
    try {
      new PerformanceObserver((list) => {
        for (const e of list.getEntries() as unknown as Array<Record<string, any>>) {
          w.__loaf.push({
            s: Math.round(e.startTime),
            d: Math.round(e.duration),
            blocking: Math.round(e.blockingDuration ?? 0),
            scripts: (e.scripts ?? []).map(
              (x: Record<string, any>) =>
                `${x.invokerType}|${String(x.sourceURL ?? '').split('/').slice(-2).join('/')}|${x.sourceFunctionName ?? ''}|${Math.round(x.duration)}`
            ),
          });
        }
      }).observe({ type: 'long-animation-frame', buffered: false });
    } catch {
      /* unsupported */
    }
  });
}

async function readObservers(page: Page, triggeredAt: number) {
  const raw = await page.evaluate(() => {
    const w = window as unknown as { __lt: number[][]; __loaf: Array<Record<string, any>> };
    return { lt: w.__lt, loaf: w.__loaf };
  });
  return {
    longtasks: raw.lt.map(([s, d]) => ({ startMs: s - triggeredAt, durMs: d })),
    loaf: raw.loaf.map((e) => ({ ...e, s: e.s - triggeredAt })),
  };
}

function emit(result: Record<string, unknown>) {
  const line = JSON.stringify(result);
  console.log(`RESULT\t${line}`);
  if (OUT) fs.appendFileSync(OUT, line + '\n');
}

test.use({ viewport: { width: 1440, height: 900 } });

for (const c of PLAN) {
  test(c.id, async ({ page }, testInfo) => {
    if (!configPrinted) {
      configPrinted = true;
      const use = testInfo.project.use as Record<string, unknown>;
      console.log(
        `CONFIG\ttrace=${JSON.stringify(use.trace)}\tvideo=${JSON.stringify(use.video)}\tscreenshot=${JSON.stringify(use.screenshot)}\tworkers=${testInfo.config.workers}\tretries=${testInfo.project.retries}\tviewport=${JSON.stringify(use.viewport)}`
      );
    }
    const traced = has(c, 'trace');
    if (traced && tracesKept >= TRACE_KEEP_MAX) {
      emit({ id: c.id, skippedBecause: `${TRACE_KEEP_MAX} traces already kept`, set: c.set, unit: c.unit, role: c.role, route: c.route });
      return;
    }
    const result: Record<string, unknown> = {
      id: c.id, set: c.set, unit: c.unit, role: c.role, batch: c.batch, route: c.route, base: c.base, flags: c.flags,
      load1Start: load1(),
    };
    try {
      if (has(c, 'reduced')) await page.emulateMedia({ reducedMotion: 'reduce' });
      const mock = await installMockApi(page);
      await seedMockSession(page);
      const delay = val(c, 'mockdelay:');
      if (delay) {
        // Registered after the mock, so it runs first (newest route wins) and hands over with fallback() after N ms.
        await page.route(/\/api\/v1\//, async (route) => {
          await sleepMs(Number(delay));
          await route.fallback();
        });
      }
      const guardOn = c.set === 'probe' ? !has(c, 'noguard') : has(c, 'guard');
      const guard = guardOn ? consoleAndNetworkGuard(page, { mock }) : null;
      if (c.set === 'bare' && has(c, 'track')) {
        // The same three listeners and bookkeeping as gates.ts trackRequests, with nothing waiting on them.
        const tracker = { inFlight: new Set<unknown>(), lastEventAt: Date.now() };
        page.on('request', (r) => {
          tracker.lastEventAt = Date.now();
          if (!['eventsource', 'websocket'].includes(r.resourceType())) tracker.inFlight.add(r);
        });
        page.on('requestfinished', (r) => { tracker.lastEventAt = Date.now(); tracker.inFlight.delete(r); });
        page.on('requestfailed', (r) => { tracker.lastEventAt = Date.now(); tracker.inFlight.delete(r); });
      }
      let websockets = 0;
      if (has(c, 'wscount')) page.on('websocket', () => { websockets += 1; });
      await page.goto(c.base + startPageFor(c.route));
      await expect(page.locator(RAIL)).toBeVisible({ timeout: 15_000 });
      // The first font load is not a route change: wait for it, as HC-UISH-009 does.
      await page.evaluate(() => document.fonts.ready);
      if (has(c, 'wscount')) {
        await page.waitForTimeout(1000);
        result.websockets = websockets;
      }
      if (has(c, 'preload')) {
        const url = CHUNK[c.route];
        // new Function keeps import() a real dynamic import in the page (Playwright's transform would rewrite a literal one).
        result.preload = await page.evaluate(
          (u) => (new Function('u', 'return import(u)') as (x: string) => Promise<unknown>)(u).then(() => 'ok', (e: unknown) => `error: ${String(e)}`),
          url
        );
      }
      await installObservers(page);

      if (c.set === 'probe') {
        const gates = loadGates(val(c, 'gates:'));
        let probecost = '';
        let reqlog = '';
        const origLog = console.log;
        console.log = (...args: unknown[]) => {
          const first = typeof args[0] === 'string' ? args[0] : '';
          if (first.startsWith('PROBECOST')) probecost = first;
          if (first.startsWith('REQLOG')) reqlog = first;
          origLog(...args);
        };
        const browser = page.context().browser();
        let anchorPage = -1;
        const tracePath = traced ? `${TRACE_DIR}/${c.id.replace(/[^A-Za-z0-9_.-]/g, '_')}.json` : '';
        if (traced && browser) {
          await browser.startTracing(page, {
            path: tracePath,
            screenshots: false,
            categories: TRACE_CATEGORIES,
          });
          anchorPage = await page.evaluate(() => { performance.mark('snl-anchor'); return performance.now(); });
        }
        let probeError = '';
        if (has(c, 'cdpcount')) process.stderr.write(`SNL-MARK start ${c.id}\n`);
        try {
          await gates.stillnessProbe(page, {
            trigger: () => navigateTo(page, c.route),
            expected: [RAIL, TOGGLE_NOTE],
            kind: 'navigation',
            lazyRoute: !has(c, 'lazy:false'),
          });
        } catch (e) {
          probeError = String(e).split('\n').slice(0, 3).join(' | ');
        } finally {
          console.log = origLog;
          if (has(c, 'cdpcount')) process.stderr.write(`SNL-MARK end ${c.id}\n`);
        }
        if (traced && browser) await browser.stopTracing();
        const kv: Record<string, string> = {};
        for (const part of probecost.split('\t').slice(2)) {
          const [k, v] = part.split('=');
          kv[k] = v;
        }
        const triggeredAt = Number(kv.triggeredAt ?? NaN);
        const obs = Number.isFinite(triggeredAt) ? await readObservers(page, triggeredAt) : { longtasks: [], loaf: [] };
        Object.assign(result, {
          measured: probecost !== '',
          maxGap: Number(kv.maxGap ?? NaN),
          gapStartMs: Number(kv.gapStartsAtMs ?? NaN),
          gapEndMs: Number(kv.gapEndsAtMs ?? NaN),
          windowMs: Number(kv.windowMs ?? NaN),
          postSamples: Number(kv.postSamples ?? NaN),
          meanDur: Number(kv.meanDur ?? NaN),
          maxDur: Number(kv.maxDur ?? NaN),
          triggeredAt,
          anchorPage,
          ...obs,
          reqlog: reqlog.slice('REQLOG\t'.length),
          probeError,
          guardProblems: guard ? guard.report().consoleErrors.length + guard.report().externalRequests.length + guard.report().unmockedApi.length : null,
        });
        if (traced) {
          const gap = Number(kv.maxGap ?? 0);
          if (gap > TRACE_KEEP_OVER_MS) {
            tracesKept += 1;
            result.tracePath = tracePath;
          } else {
            fs.rmSync(tracePath, { force: true });
            result.tracePath = null;
          }
        }
      } else {
        // L0's bare timer, with an observer and the gap end added.
        const bBrowser = page.context().browser();
        const bTracePath = traced ? `${TRACE_DIR}/${c.id.replace(/[^A-Za-z0-9_.-]/g, '_')}.json` : '';
        let bAnchor = -1;
        if (traced && bBrowser) {
          await bBrowser.startTracing(page, { path: bTracePath, screenshots: false, categories: TRACE_CATEGORIES });
          bAnchor = await page.evaluate(() => { performance.mark('snl-anchor'); return performance.now(); });
        }
        await page.evaluate(() => {
          const w = window as unknown as { __ticks: number[]; __timer: number };
          w.__ticks = [];
          w.__timer = window.setInterval(() => w.__ticks.push(performance.now()), 20);
        });
        if (!has(c, 'nowait')) await page.waitForTimeout(100);
        const t0 = await page.evaluate(() => performance.now());
        await navigateTo(page, c.route);
        await page.waitForTimeout(1500);
        const r = await page.evaluate((trig) => {
          const w = window as unknown as { __ticks: number[]; __timer: number };
          window.clearInterval(w.__timer);
          const t = w.__ticks;
          let max = 0;
          let at = -1;
          for (let i = 1; i < t.length; i++) {
            if (t[i] >= trig && t[i] - t[i - 1] > max) { max = t[i] - t[i - 1]; at = i; }
          }
          return {
            maxGap: Math.round(max),
            gapStartMs: at > 0 ? Math.round(t[at - 1] - trig) : -1,
            gapEndMs: at >= 0 ? Math.round(t[at] - trig) : -1,
            ticks: t.filter((x) => x >= trig).length,
            path: location.pathname,
          };
        }, t0);
        if (traced && bBrowser) await bBrowser.stopTracing();
        const obs = await readObservers(page, t0);
        Object.assign(result, { measured: true, ...r, triggeredAt: Math.round(t0), anchorPage: bAnchor, ...obs, guardProblems: guard ? guard.report().consoleErrors.length + guard.report().externalRequests.length + guard.report().unmockedApi.length : null });
        if (traced) {
          if (r.maxGap > TRACE_KEEP_OVER_MS) {
            tracesKept += 1;
            result.tracePath = bTracePath;
          } else {
            fs.rmSync(bTracePath, { force: true });
            result.tracePath = null;
          }
        }
      }
    } catch (e) {
      result.measured = false;
      result.error = String(e).split('\n').slice(0, 4).join(' | ');
    }
    result.load1End = load1();
    emit(result);
  });
}
