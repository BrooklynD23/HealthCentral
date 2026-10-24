/**
 * UI-GATES acceptance helpers (plan section 6, gates G1-G10).
 *
 * Each helper measures one gate. Helpers return data and throw on probe
 * failure; the caller asserts on the result, so a test can name the exact
 * value that failed. See e2e/README.md for when to use each one.
 *
 * Helpers that read the route fade need the product's `data-route-container`
 * contract, which no row has added yet. Until one does, routeOpacitySamples
 * falls back to the PageTransition element (`main > div`); see its docs.
 */

import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

export type Theme = 'light' | 'dark';

/** WCAG 2.0 / 2.1 / 2.2 A and AA (plan G1). */
export const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

/** G10: the route fade must finish within this many ms of the new container. */
export const ROUTE_FADE_MS = 240;
/** G10: stillness window after the trigger (extended for lazy first visits). */
export const STILLNESS_WINDOW_MS = 800;
/** G10: sampling interval (plan says 16-40 ms). */
export const STILLNESS_SAMPLE_MS = 20;
/** G10: bounding-rect tolerance in CSS pixels. */
export const RECT_TOLERANCE_PX = 0.5;

/** The product's route container: `data-route-container` = pathname (plan G10). */
export const ROUTE_CONTAINER_SELECTOR = '[data-route-container]';
/** Today's fallback: PageTransition is the only element directly inside `<main>`. */
export const ROUTE_FALLBACK_SELECTOR = 'main > div';
/** The Safety Rail carries this attribute once UI-SHELL lands (plan G9). */
export const SAFETY_RAIL_SELECTOR = '[data-safety-rail]';

const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);
const SETTLED_OPACITY = 0.99;
const OPACITY_EPSILON = 0.01;
const IDENTITY_TRANSFORM =
  /^(none|matrix\(\s*1,\s*0,\s*0,\s*1,\s*0,\s*0\s*\)|matrix3d\(\s*1,\s*0,\s*0,\s*0,\s*0,\s*1,\s*0,\s*0,\s*0,\s*0,\s*1,\s*0,\s*0,\s*0,\s*0,\s*1\s*\))$/;

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));
const round1 = (value: number) => Math.round(value * 10) / 10;

// ---------------------------------------------------------------------------
// G1: axe, WCAG 2.0-2.2 A and AA.
// ---------------------------------------------------------------------------

export type AxeViolation = Awaited<ReturnType<AxeBuilder['analyze']>>['violations'][number];

export interface AxeGateResult {
  violations: AxeViolation[];
  /** Every violated rule id, in axe's order (e.g. `color-contrast`). */
  ruleIds: string[];
  /** The serious and critical subset (G1 requires none). */
  blocking: AxeViolation[];
}

/** Runs axe with the WCAG tags. Pass `theme` to apply it first (G1 runs light and dark). */
export async function axeGate(page: Page, options: { theme?: Theme } = {}): Promise<AxeGateResult> {
  if (options.theme) await setTheme(page, options.theme);
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  return {
    violations: results.violations,
    ruleIds: results.violations.map((violation) => violation.id),
    blocking: results.violations.filter(
      (violation) => violation.impact === 'serious' || violation.impact === 'critical'
    ),
  };
}

/**
 * Applies a theme after load. The product stays light until UI-DARK-FLIP, so
 * until then this only sets the attributes a dark-aware stylesheet would read.
 */
export async function setTheme(page: Page, theme: Theme): Promise<void> {
  await page.emulateMedia({ colorScheme: theme });
  await page.evaluate((next) => {
    const root = document.documentElement;
    root.dataset.theme = next;
    root.classList.toggle('dark', next === 'dark');
    root.style.colorScheme = next;
  }, theme);
}

// ---------------------------------------------------------------------------
// G6: no horizontal scroll at the viewport the caller set (390x844 or 320x640).
// ---------------------------------------------------------------------------

export interface ScrollGateResult {
  scrollWidth: number;
  innerWidth: number;
  ok: boolean;
}

export async function noHorizontalScroll(page: Page): Promise<ScrollGateResult> {
  const measured = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  return { ...measured, ok: measured.scrollWidth <= measured.innerWidth };
}

// ---------------------------------------------------------------------------
// G2: cumulative layout shift.
// ---------------------------------------------------------------------------

/**
 * CLS of the current document, from load plus whatever `action` does. The
 * observer is an init script, so it watches navigations made inside `action`;
 * on a page that was already loaded before this call, the result is NaN.
 */
export async function measureCls(
  page: Page,
  action: () => Promise<void>,
  settleMs = 500
): Promise<number> {
  await page.addInitScript(() => {
    const w = window as unknown as { __hcCls?: number };
    w.__hcCls = 0;
    try {
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries() as Array<PerformanceEntry & { value: number; hadRecentInput: boolean }>) {
          if (!entry.hadRecentInput) w.__hcCls = (w.__hcCls ?? 0) + entry.value;
        }
      }).observe({ type: 'layout-shift', buffered: true } as PerformanceObserverInit);
    } catch {
      // layout-shift is unsupported: the total stays 0 for this document.
    }
  });
  await action();
  await page.waitForTimeout(settleMs);
  return page.evaluate(() => {
    const value = (window as unknown as { __hcCls?: number }).__hcCls;
    return typeof value === 'number' ? value : NaN;
  });
}

// ---------------------------------------------------------------------------
// G3: INP proxy under CPU x4.
// ---------------------------------------------------------------------------

/**
 * Largest Event Timing duration (ms, threshold 16) for the events `action`
 * causes, with the CPU throttled (default x4). Returns 0 when no event reached
 * the threshold. Chromium only (CDP).
 */
export async function maxEventDuration(
  page: Page,
  action: () => Promise<void>,
  options: { cpuRate?: number; settleMs?: number } = {}
): Promise<number> {
  const session = await page.context().newCDPSession(page);
  await session.send('Emulation.setCPUThrottlingRate', { rate: options.cpuRate ?? 4 });
  try {
    await page.evaluate(() => {
      const w = window as unknown as { __hcEventDurations?: number[] };
      w.__hcEventDurations = [];
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) w.__hcEventDurations?.push(entry.duration);
      }).observe({ type: 'event', durationThreshold: 16, buffered: true } as PerformanceObserverInit);
    });
    await action();
    await page.waitForTimeout(options.settleMs ?? 200);
    const durations = await page.evaluate(
      () => (window as unknown as { __hcEventDurations?: number[] }).__hcEventDurations ?? []
    );
    return durations.length > 0 ? Math.max(...durations) : 0;
  } finally {
    await session.send('Emulation.setCPUThrottlingRate', { rate: 1 }).catch(() => undefined);
    await session.detach().catch(() => undefined);
  }
}

// ---------------------------------------------------------------------------
// G5: reduced motion.
// ---------------------------------------------------------------------------

/**
 * Emulates reduced motion, runs `action`, waits 50 ms, and returns the
 * elements whose computed transform is not the identity. An empty array passes.
 */
export async function reducedMotionSnapshot(page: Page, action: () => Promise<void>): Promise<string[]> {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await action();
  await page.waitForTimeout(50);
  return page.evaluate((identitySource) => {
    const identity = new RegExp(identitySource);
    const offenders: string[] = [];
    for (const el of Array.from(document.querySelectorAll('body *'))) {
      const transform = getComputedStyle(el).transform;
      if (!identity.test(transform)) {
        const id = el.id ? `#${el.id}` : '';
        const cls = (el.getAttribute('class') ?? '').trim().replace(/\s+/g, '.').slice(0, 60);
        offenders.push(`${el.tagName.toLowerCase()}${id}${cls ? `.${cls}` : ''} transform=${transform}`);
      }
    }
    return offenders;
  }, IDENTITY_TRANSFORM.source);
}

// ---------------------------------------------------------------------------
// DF-6 / HC-UISH-003: route container opacity during a navigation.
// ---------------------------------------------------------------------------

export interface RouteOpacitySample {
  /** ms since sampling began (page clock) */
  t: number;
  /** computed opacity of the route element; NaN when no element matched */
  opacity: number;
  /** which element was read */
  source: 'route-container' | 'fallback' | 'missing';
}

/**
 * Samples the route element's computed opacity every `intervalMs` (default 40)
 * while `navigate` runs and for `durationMs` after it (default 800).
 *
 * The element is `[data-route-container]` when a row has added it. Until then
 * it falls back to `main > div`: AppLayout puts the keyed PageTransition
 * motion.div directly inside `<main>`, and that element is the one whose
 * opacity runs 1 -> 0 (exit) -> 0 -> 1 (enter). `main` itself never animates,
 * so sampling it would read 1 and miss the defect.
 *
 * The sampler lives in the page, so it covers SPA navigation only (a click
 * that changes the route without a document load).
 */
export async function routeOpacitySamples(
  page: Page,
  options: { navigate: () => Promise<void>; durationMs?: number; intervalMs?: number }
): Promise<RouteOpacitySample[]> {
  await page.evaluate(
    ({ container, fallback, interval }) => {
      type Raw = { t: number; opacity: number; source: string };
      const w = window as unknown as { __hcRouteSamples?: Raw[]; __hcRouteTimer?: number };
      const start = performance.now();
      w.__hcRouteSamples = [];
      w.__hcRouteTimer = window.setInterval(() => {
        const primary = document.querySelector(container);
        const el = primary ?? document.querySelector(fallback);
        const source = primary ? 'route-container' : el ? 'fallback' : 'missing';
        const opacity = el ? parseFloat(getComputedStyle(el).opacity) : NaN;
        w.__hcRouteSamples?.push({ t: Math.round(performance.now() - start), opacity, source });
      }, interval);
    },
    {
      container: ROUTE_CONTAINER_SELECTOR,
      fallback: ROUTE_FALLBACK_SELECTOR,
      interval: options.intervalMs ?? 40,
    }
  );
  try {
    await options.navigate();
    await page.waitForTimeout(options.durationMs ?? 800);
  } finally {
    // Stop the sampler even when navigate throws; the error still propagates.
    await page.evaluate(() => {
      const w = window as unknown as { __hcRouteTimer?: number };
      if (w.__hcRouteTimer !== undefined) window.clearInterval(w.__hcRouteTimer);
    });
  }
  const raw = await page.evaluate(
    () => (window as unknown as { __hcRouteSamples?: Array<{ t: number; opacity: number; source: string }> }).__hcRouteSamples ?? []
  );
  return raw.map((sample) => ({
    t: sample.t,
    opacity: sample.opacity,
    source: sample.source as RouteOpacitySample['source'],
  }));
}

// ---------------------------------------------------------------------------
// G7: zero console errors and no non-localhost request.
// ---------------------------------------------------------------------------

export interface GuardReport {
  consoleErrors: string[];
  externalRequests: string[];
  unmockedApi: string[];
}

export interface NetworkGuard {
  report(): GuardReport;
  /** Throws, listing every problem, if the page logged an error, made a non-localhost request, or reached an unmocked API. */
  assertClean(): void;
}

/**
 * Attaches listeners at call time, so create it before the navigation under
 * test. Pass the `installMockApi` result as `mock` to fail on any /api/v1 call
 * the mock did not answer.
 */
export function consoleAndNetworkGuard(
  page: Page,
  options: { mock?: { readonly unmocked: string[] } } = {}
): NetworkGuard {
  const consoleErrors: string[] = [];
  const externalRequests: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => {
    consoleErrors.push(`pageerror: ${error.message}`);
  });
  page.on('request', (request) => {
    if (isExternal(request.url())) externalRequests.push(request.url());
  });

  const report = (): GuardReport => ({
    consoleErrors: [...consoleErrors],
    externalRequests: [...externalRequests],
    unmockedApi: [...(options.mock?.unmocked ?? [])],
  });

  return {
    report,
    assertClean() {
      const current = report();
      const problems = [
        ...current.consoleErrors.map((text) => `console error: ${text}`),
        ...current.externalRequests.map((url) => `non-localhost request: ${url}`),
        ...current.unmockedApi.map((call) => `unmocked API request: ${call}`),
      ];
      if (problems.length > 0) {
        throw new Error(`consoleAndNetworkGuard: ${problems.length} problem(s)\n  ${problems.join('\n  ')}`);
      }
    },
  };
}

function isExternal(raw: string): boolean {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return false;
  }
  if (!['http:', 'https:', 'ws:', 'wss:'].includes(url.protocol)) return false;
  return !LOCAL_HOSTS.has(url.hostname);
}

// ---------------------------------------------------------------------------
// G9: Safety Rail visibility.
// ---------------------------------------------------------------------------

export interface SafetyVisibility {
  found: boolean;
  /** the rect overlaps the viewport */
  inViewport: boolean;
  /** product of the element's and every ancestor's computed opacity (must be 1) */
  effectiveOpacity: number;
}

export async function safetyVisible(page: Page, selector = SAFETY_RAIL_SELECTOR): Promise<SafetyVisibility> {
  return page.evaluate((target) => {
    const el = document.querySelector(target);
    if (!(el instanceof HTMLElement)) return { found: false, inViewport: false, effectiveOpacity: 0 };
    const rect = el.getBoundingClientRect();
    let effectiveOpacity = 1;
    for (let node: Element | null = el; node; node = node.parentElement) {
      effectiveOpacity *= parseFloat(getComputedStyle(node).opacity);
    }
    const inViewport =
      rect.width > 0 &&
      rect.height > 0 &&
      rect.bottom > 0 &&
      rect.right > 0 &&
      rect.top < window.innerHeight &&
      rect.left < window.innerWidth;
    return { found: true, inViewport, effectiveOpacity };
  }, selector);
}

// ---------------------------------------------------------------------------
// G10: stillness probe.
// ---------------------------------------------------------------------------

export interface StillnessOptions {
  /** Runs the interaction or navigation. Called after the first sample. */
  trigger: () => Promise<void>;
  /** Selectors that must each match at least one [data-t0] node (the route's §2.7 components). */
  expected: string[];
  /** A navigation enables the route-fade rules; an interaction (including an overlay) has no fade window. Default `interaction`. */
  kind?: 'interaction' | 'navigation';
  /** First visit to a lazy route: extend the window until network idle, then 800 ms more. */
  lazyRoute?: boolean;
  /** Window after the trigger. Default STILLNESS_WINDOW_MS (800). */
  windowMs?: number;
}

export interface StillnessReport {
  samples: number;
  /** [data-t0] nodes in the last sample */
  nodes: number;
  /** key of the route container in the last sample, if any */
  routeKey: string | null;
}

export class StillnessError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'StillnessError';
  }
}

interface NodeSnap {
  id: number;
  label: string;
  text: string;
  color: string;
  bg: string;
  clip: string;
  filter: string;
  transform: string;
  rect: [number, number, number, number];
  opacity: number;
}

interface RouteSnap {
  key: string;
  opacity: number;
  transform: string;
}

interface Snap {
  t: number;
  doc: string;
  pathname: string;
  route: RouteSnap | null;
  nodes: NodeSnap[];
  expectedHits: boolean[];
}

/**
 * Samples every [data-t0] node, the route container, and the expected
 * selectors. Runs inside the page, so it must not reference module scope.
 */
function snapshotDocument(expected: string[]): Omit<Snap, 't'> {
  type State = { doc: string; next: number; ids: WeakMap<Element, number> };
  const w = window as unknown as { __hcStill?: State };
  if (!w.__hcStill) {
    w.__hcStill = { doc: Math.random().toString(36).slice(2), next: 1, ids: new WeakMap() };
  }
  const state = w.__hcStill;
  const idOf = (el: Element): number => {
    let id = state.ids.get(el);
    if (id === undefined) {
      id = state.next++;
      state.ids.set(el, id);
    }
    return id;
  };
  const effectiveOpacity = (el: Element): number => {
    let value = 1;
    for (let node: Element | null = el; node; node = node.parentElement) {
      value *= parseFloat(getComputedStyle(node).opacity);
    }
    return value;
  };

  const routeEl = document.querySelector('[data-route-container]');
  let route: RouteSnap | null = null;
  if (routeEl) {
    const cs = getComputedStyle(routeEl);
    route = {
      key: routeEl.getAttribute('data-route-container') ?? '',
      opacity: parseFloat(cs.opacity),
      transform: cs.transform,
    };
  }

  const nodes: NodeSnap[] = Array.from(document.querySelectorAll('[data-t0]')).map((el): NodeSnap => {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const text = el.textContent ?? '';
    return {
      id: idOf(el),
      label: `${el.tagName.toLowerCase()} "${text.trim().slice(0, 40)}"`,
      text,
      color: cs.color,
      bg: cs.backgroundColor,
      clip: cs.clipPath,
      filter: cs.filter,
      transform: cs.transform,
      rect: [r.x, r.y, r.width, r.height],
      opacity: effectiveOpacity(el),
    };
  });

  const expectedHits = expected.map((selector) =>
    Array.from(document.querySelectorAll(selector)).some((el) => el.matches('[data-t0]'))
  );

  return { doc: state.doc, pathname: location.pathname, route, nodes, expectedHits };
}

async function takeSnapshot(page: Page, expected: string[]): Promise<Snap> {
  const t = Date.now();
  const snap = await page.evaluate(snapshotDocument, expected);
  return { t, ...snap };
}

/**
 * Pure analysis of the samples. Returns one message per failure; each names
 * the property that moved so a caller can match on it.
 */
function analyse(snaps: Snap[], kind: 'interaction' | 'navigation', expected: string[]): string[] {
  const failures: string[] = [];
  const seen = new Set<string>();
  const fail = (key: string, message: string) => {
    if (seen.has(key)) return;
    seen.add(key);
    failures.push(message);
  };
  const origin = snaps[0].t;
  const last = snaps[snaps.length - 1];

  if (last.nodes.length === 0) {
    fail('zero-nodes', 'found zero [data-t0] nodes (the probe needs at least one)');
  }
  expected.forEach((selector, index) => {
    if (!last.expectedHits[index]) {
      fail(`expected:${selector}`, `expected selector "${selector}" matched no [data-t0] node`);
    }
  });

  // Per-node stillness: the baseline is the first sample in which the node exists.
  const baselines = new Map<string, NodeSnap>();
  for (const snap of snaps) {
    for (const node of snap.nodes) {
      const key = `${snap.doc}:${node.id}`;
      const base = baselines.get(key);
      if (!base) {
        baselines.set(key, node);
        continue;
      }
      const at = snap.t - origin;
      const who = `[data-t0] ${base.label}`;
      const compare = (prop: string, before: string, after: string) => {
        if (before !== after) {
          fail(`${key}:${prop}`, `${prop} changed on ${who}: "${before}" -> "${after}" at ${at} ms`);
        }
      };
      compare('textContent', base.text, node.text);
      compare('computed color', base.color, node.color);
      compare('computed background-color', base.bg, node.bg);
      compare('computed clip-path', base.clip, node.clip);
      compare('computed filter', base.filter, node.filter);
      compare('computed transform', base.transform, node.transform);
      if (node.rect.some((value, index) => Math.abs(value - base.rect[index]) > RECT_TOLERANCE_PX)) {
        fail(
          `${key}:rect`,
          `getBoundingClientRect changed on ${who}: [${base.rect.map(round1)}] -> [${node.rect.map(round1)}] at ${at} ms`
        );
      }
    }
  }

  // Route fade (navigation only). The new keyed container is the first sample
  // whose key matches the pathname and was not the container before the trigger.
  let i0 = -1;
  let t0 = 0;
  if (kind === 'navigation') {
    const oldKey = snaps[0].route?.key ?? null;
    i0 = snaps.findIndex((s) => s.route !== null && s.route.key === s.pathname && s.route.key !== oldKey);
    if (i0 < 0) {
      fail('no-route', `no new keyed route container for ${last.pathname} appeared (data-route-container must equal the pathname)`);
    } else {
      t0 = snaps[i0].t;
      let settledAt = -1;
      for (let index = i0; index < snaps.length; index++) {
        const route = snaps[index].route;
        if (!route) continue;
        const at = snaps[index].t - t0;
        if (!IDENTITY_TRANSFORM.test(route.transform)) {
          fail('route-transform', `route container transform ${route.transform} at ${at} ms (must stay none)`);
        }
        if (settledAt < 0 && route.opacity >= SETTLED_OPACITY) {
          settledAt = index;
        } else if (settledAt >= 0 && route.opacity < SETTLED_OPACITY) {
          fail('route-reopacity', `route container opacity changed after settling (1 -> ${route.opacity.toFixed(2)}) at ${at} ms`);
        }
      }
      if (settledAt < 0 || snaps[settledAt].t - t0 > ROUTE_FADE_MS) {
        const reached = settledAt < 0 ? 'never' : `at ${snaps[settledAt].t - t0} ms`;
        fail('route-240', `route container did not reach opacity 1 within ${ROUTE_FADE_MS} ms (reached ${reached})`);
      }
    }
  }

  // Effective opacity: 1, except that during the navigation fade window each
  // node must equal the route container's own opacity (plan G10).
  for (let index = 0; index < snaps.length; index++) {
    const snap = snaps[index];
    const inWindow =
      kind === 'navigation' &&
      i0 >= 0 &&
      index >= i0 &&
      snap.t - t0 <= ROUTE_FADE_MS &&
      snap.route !== null;
    const allowed = inWindow && snap.route ? snap.route.opacity : 1;
    for (const node of snap.nodes) {
      if (Math.abs(node.opacity - allowed) > OPACITY_EPSILON) {
        const at = snap.t - origin;
        const message = inWindow
          ? `effective opacity ${node.opacity.toFixed(2)} must equal the route container's ${allowed.toFixed(2)} during the fade on [data-t0] ${node.label} at ${at} ms`
          : `effective opacity ${node.opacity.toFixed(2)} (must be 1) on [data-t0] ${node.label} at ${at} ms`;
        fail(`${snap.doc}:${node.id}:opacity`, message);
      }
    }
  }

  return failures;
}

async function waitUntil(predicate: () => boolean, timeoutMs: number, what: string): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (!predicate()) {
    if (Date.now() > deadline) throw new StillnessError(`timed out waiting for ${what}`);
    await sleep(5);
  }
}

/**
 * Samples every STILLNESS_SAMPLE_MS while `trigger` runs and for the window
 * after it, then throws a StillnessError listing every failure. Resolves with
 * a summary when the page stays still.
 */
export async function stillnessProbe(page: Page, options: StillnessOptions): Promise<StillnessReport> {
  const kind = options.kind ?? 'interaction';
  const windowMs = options.windowMs ?? STILLNESS_WINDOW_MS;
  const snaps: Snap[] = [];
  let lastError: unknown = null;
  let running = true;

  const sampler = (async () => {
    while (running) {
      try {
        snaps.push(await takeSnapshot(page, options.expected));
      } catch (error) {
        // The document may be navigating, or a selector may be invalid; the next sample retries.
        lastError = error;
      }
      if (running) await sleep(STILLNESS_SAMPLE_MS);
    }
  })();

  try {
    await waitUntil(() => snaps.length > 0, 10_000, 'the first stillness sample');
    const triggeredAt = Date.now();
    await options.trigger();
    if (options.lazyRoute) {
      await page.waitForLoadState('networkidle').catch(() => undefined);
    }
    const windowStart = options.lazyRoute ? Date.now() : triggeredAt;
    const end = windowStart + windowMs;
    while (Date.now() < end) await sleep(10);
  } finally {
    running = false;
    await sampler;
  }

  if (snaps.length === 0) {
    throw new StillnessError(`stillnessProbe took no sample: ${String(lastError)}`);
  }
  const failures = analyse(snaps, kind, options.expected);
  if (failures.length > 0) {
    throw new StillnessError(`stillnessProbe failed (${failures.length}):\n  - ${failures.join('\n  - ')}`);
  }
  const last = snaps[snaps.length - 1];
  return { samples: snaps.length, nodes: last.nodes.length, routeKey: last.route?.key ?? null };
}
