/**
 * UI-RIBBON: RangeRibbon and RangeTick (HC-UIRR-001..008).
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md (UI-RIBBON; §2.6 M10).
 *
 * The components are loaded with a dynamic import inside each test, so before
 * they exist every id fails on its own line instead of the whole file failing
 * to load.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import type { TrendData, TrendPoint } from '@/services/types';

// Variable specifiers keep Vite from resolving the modules at transform time.
const RIBBON_MODULE = '@/components/results/RangeRibbon';
const TICK_MODULE = '@/components/results/RangeTick';
const RIBBON_SOURCE = '@/components/results/RangeRibbon.tsx?raw';
const TICK_SOURCE = '@/components/results/RangeTick.tsx?raw';
const loadRibbon = () =>
  import(/* @vite-ignore */ RIBBON_MODULE) as Promise<typeof import('@/components/results/RangeRibbon')>;
const loadTick = () =>
  import(/* @vite-ignore */ TICK_MODULE) as Promise<typeof import('@/components/results/RangeTick')>;
const loadRibbonSource = () =>
  import(/* @vite-ignore */ RIBBON_SOURCE) as Promise<{ default: string }>;
const loadTickSource = () =>
  import(/* @vite-ignore */ TICK_SOURCE) as Promise<{ default: string }>;

const APR_1 = '2026-04-01T00:00:00';
const APR_10 = '2026-04-10T00:00:00';
const APR_20 = '2026-04-20T00:00:00';

function point(date: string, value: number, verified?: boolean): TrendPoint {
  return {
    date,
    value,
    unit: 'mg/dL',
    is_abnormal: false,
    flag: null,
    doc_id: `doc-${date.slice(0, 10)}`,
    extraction_confidence: null,
    // A missing flag is unverified (I-13), so the key is left out when undefined.
    ...(verified === undefined ? {} : { user_verified: verified }),
  };
}

function series(points: TrendPoint[], overrides: Partial<TrendData> = {}): TrendData {
  return {
    analyte_canonical: 'glucose',
    analyte_display_name: 'Glucose',
    unit: 'mg/dL',
    ref_low: 70,
    ref_high: 99,
    data_points: points,
    summary: '',
    ...overrides,
  };
}

// Records every Element.animate call with its target, so the reveal can be
// inspected. jsdom has no Web Animations API.
interface AnimateCall {
  target: Element;
  keyframes: unknown;
  options: Record<string, unknown>;
}
let animateCalls: AnimateCall[] = [];

beforeEach(() => {
  sessionStorage.clear();
  animateCalls = [];
  Object.defineProperty(Element.prototype, 'animate', {
    configurable: true,
    writable: true,
    value(this: Element, keyframes: unknown, options: Record<string, unknown>) {
      animateCalls.push({ target: this, keyframes, options });
      return { cancel: () => undefined, finish: () => undefined, finished: Promise.resolve() };
    },
  });
});

afterEach(() => {
  delete (Element.prototype as unknown as { animate?: unknown }).animate;
  vi.useRealTimers();
});

function pointGroup(container: HTMLElement, index: number): Element {
  const group = container.querySelector(`[data-point-index="${index}"]`);
  if (!group) throw new Error(`no point group ${index}`);
  return group;
}

function hitOf(container: HTMLElement, index: number): Element {
  const hit = container.querySelector(`[data-point-index="${index}"] [data-hit]`);
  if (!hit) throw new Error(`no hit target ${index}`);
  return hit;
}

function cxOf(container: HTMLElement, index: number): number {
  return Number(hitOf(container, index).getAttribute('cx'));
}

function cyOf(container: HTMLElement, index: number): number {
  return Number(hitOf(container, index).getAttribute('cy'));
}

function cursorOf(container: HTMLElement): HTMLElement {
  const cursor = container.querySelector<HTMLElement>('[data-cursor]');
  if (!cursor) throw new Error('no cursor');
  return cursor;
}

// textContent runs adjacent cells together ("Apr 1, 2026" + "85" reads as
// "202685"), so the text nodes are joined with a space instead.
function textNodesOf(root: HTMLElement): string {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const parts: string[] = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    parts.push(node.textContent ?? '');
  }
  return parts.join(' ');
}

function animationsFor(index: number): AnimateCall[] {
  return animateCalls.filter((call) => call.target.getAttribute('data-point-index') === String(index));
}

describe('RangeRibbon', () => {
  it('HC-UIRR-001: x positions are proportional to time for unequal gaps', async () => {
    const { RangeRibbon } = await loadRibbon();
    // Gaps of 2 days and 28 days. Spacing by index would put the middle point at 0.5.
    const { container } = render(
      <RangeRibbon
        trend={series([
          point(APR_1, 80, true),
          point('2026-04-03T00:00:00', 85, true),
          point('2026-05-01T00:00:00', 90, true),
        ])}
      />
    );
    const first = cxOf(container, 0);
    const middle = cxOf(container, 1);
    const last = cxOf(container, 2);
    expect(Number.isFinite(first) && Number.isFinite(middle) && Number.isFinite(last)).toBe(true);
    expect((middle - first) / (last - first)).toBeCloseTo(2 / 30, 4);
  });

  it('HC-UIRR-002: the band spans ref_low..ref_high; an out-of-range point has the triangle and the words', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(
      <RangeRibbon
        trend={series([
          point(APR_1, 85, true),
          point(APR_10, 118, true),
          point(APR_20, 60, true),
        ])}
      />
    );
    const band = container.querySelector('[data-band]');
    const high = container.querySelector('[data-band-edge="high"]');
    const low = container.querySelector('[data-band-edge="low"]');
    expect(band).not.toBeNull();
    expect(high).not.toBeNull();
    expect(low).not.toBeNull();

    const top = Number(band?.getAttribute('y'));
    const bottom = top + Number(band?.getAttribute('height'));
    expect(Number(high?.getAttribute('y1'))).toBeCloseTo(top, 6);
    expect(Number(low?.getAttribute('y1'))).toBeCloseTo(bottom, 6);

    // Linear value-to-y mapping from the first two points: 99 must sit on the
    // high edge and 70 on the low edge.
    const slope = (cyOf(container, 1) - cyOf(container, 0)) / (118 - 85);
    const yAt = (value: number) => cyOf(container, 0) + (value - 85) * slope;
    expect(Number(high?.getAttribute('y1'))).toBeCloseTo(yAt(99), 3);
    expect(Number(low?.getAttribute('y1'))).toBeCloseTo(yAt(70), 3);

    // In range sits inside the band; above sits over it; below sits under it.
    expect(cyOf(container, 0)).toBeGreaterThan(top);
    expect(cyOf(container, 0)).toBeLessThan(bottom);
    expect(cyOf(container, 1)).toBeLessThan(top);
    expect(cyOf(container, 2)).toBeGreaterThan(bottom);

    expect(container.querySelectorAll('[data-triangle]')).toHaveLength(2);
    expect(pointGroup(container, 0).querySelector('[data-triangle]')).toBeNull();
    expect(
      within(pointGroup(container, 1) as HTMLElement).getByText('Above the reference range (per report)')
    ).toBeInTheDocument();
    expect(
      within(pointGroup(container, 2) as HTMLElement).getByText('Below the reference range (per report)')
    ).toBeInTheDocument();
  });

  it('HC-UIRR-002: a null bound draws no band edge on that side and no triangle against it', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(
      <RangeRibbon
        trend={series(
          [point(APR_1, 0.5, true), point(APR_10, 118, true)],
          { ref_low: null, ref_high: 99 }
        )}
      />
    );
    expect(container.querySelector('[data-band-edge="high"]')).not.toBeNull();
    expect(container.querySelector('[data-band-edge="low"]')).toBeNull();
    expect(container.querySelector('[data-band]')).toBeNull();
    expect(pointGroup(container, 0).querySelector('[data-triangle]')).toBeNull();
    expect(pointGroup(container, 1).querySelector('[data-triangle="above"]')).not.toBeNull();
  });

  it('HC-UIRR-003: unverified points are hollow and dashed; verified points are filled', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(
      <RangeRibbon
        trend={series([
          point(APR_1, 85, false),
          point(APR_10, 90, true),
          point(APR_20, 92),
        ])}
      />
    );
    const marker = (index: number) => {
      const el = pointGroup(container, index).querySelector('[data-marker]');
      if (!el) throw new Error(`no marker ${index}`);
      return el;
    };

    // Explicit false and a missing flag are both unverified (I-13).
    for (const index of [0, 2]) {
      expect(marker(index).getAttribute('fill')).toBe('none');
      expect(marker(index).getAttribute('stroke-dasharray')).toBeTruthy();
    }
    expect(marker(1).getAttribute('fill')).not.toBe('none');
    expect(marker(1).getAttribute('stroke-dasharray')).toBeNull();
  });

  it('HC-UIRR-004: value-blind: an out-of-range and an in-range point get identical animation attributes', async () => {
    const { RangeRibbon } = await loadRibbon();
    const inRange = series([point(APR_1, 85, true), point(APR_10, 90, true), point(APR_20, 95, true)]);
    const outOfRange = series([point(APR_1, 85, true), point(APR_10, 118, true), point(APR_20, 95, true)]);

    const first = render(<RangeRibbon trend={inRange} />);
    const inAnimations = animationsFor(1);
    first.unmount();

    // Same date and same index, but the value is out of range.
    sessionStorage.clear();
    animateCalls = [];
    render(<RangeRibbon trend={outOfRange} />);
    const outAnimations = animationsFor(1);

    expect(inAnimations.length).toBeGreaterThan(0);
    expect(outAnimations).toHaveLength(inAnimations.length);
    for (let i = 0; i < inAnimations.length; i += 1) {
      expect(outAnimations[i].keyframes).toEqual(inAnimations[i].keyframes);
      expect(outAnimations[i].options).toEqual(inAnimations[i].options);
    }
    // Points rise from .6 to 1 at 40 ms intervals.
    expect(inAnimations[0].options.delay).toBe(40);
    expect(inAnimations[0].keyframes).toEqual([
      { transform: 'scale(0.6)' },
      { transform: 'scale(1)' },
    ]);
  });

  it('HC-UIRR-004: reduced motion shows the final frame, with no draw and no glide', async () => {
    const { RangeRibbon } = await loadRibbon();
    const original = window.matchMedia;
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query.includes('reduce'),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })) as unknown as typeof window.matchMedia;
    try {
      const { container } = render(
        <RangeRibbon trend={series([point(APR_1, 85, true), point(APR_10, 118, false)])} />
      );
      expect(animateCalls).toHaveLength(0);
      fireEvent.click(hitOf(container, 0));
      expect(cursorOf(container).style.transition).toBe('none');
    } finally {
      window.matchMedia = original;
    }
  });

  it('HC-UIRR-005: ArrowRight moves the selection and updates aria-valuetext; no transition runs on a keyboard move', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(
      <RangeRibbon
        trend={series([
          point(APR_1, 85, true),
          point(APR_10, 118, false),
          point(APR_20, 60, true),
        ])}
      />
    );
    const slider = screen.getByRole('slider');
    // The default selection is the latest point.
    expect(slider).toHaveAttribute(
      'aria-valuetext',
      "Apr 20, 2026: 60 mg/dL, below the report's range, checked by you"
    );

    fireEvent.keyDown(slider, { key: 'Home' });
    expect(slider).toHaveAttribute('aria-valuenow', '0');
    fireEvent.keyDown(slider, { key: 'ArrowRight' });
    expect(slider).toHaveAttribute('aria-valuenow', '1');
    expect(slider).toHaveAttribute(
      'aria-valuetext',
      "Apr 10, 2026: 118 mg/dL, above the report's range, not yet checked"
    );
    expect(cursorOf(container).style.transition).toBe('none');
    const moved = Number(cursorOf(container).style.transform.match(/translateX\(([-\d.]+)px\)/)?.[1]);
    expect(moved).toBeCloseTo(cxOf(container, 1), 3);

    // A pointer selection glides for --dur-sm; the keyboard move right after it does not.
    fireEvent.click(hitOf(container, 0));
    expect(cursorOf(container).style.transition).toContain('--dur-sm');
    fireEvent.keyDown(slider, { key: 'ArrowRight' });
    expect(slider).toHaveAttribute('aria-valuenow', '1');
    expect(cursorOf(container).style.transition).toBe('none');
  });

  it('HC-UIRR-006: the table fallback lists the same dates and values', async () => {
    const { RangeRibbon } = await loadRibbon();
    render(
      <RangeRibbon
        trend={series([
          point(APR_1, 85, true),
          point(APR_10, 118, false),
          point(APR_20, 96.5, true),
        ])}
      />
    );
    const table = screen.getByRole('table');
    const rows = within(table).getAllByRole('row').slice(1);
    expect(
      rows.map((row) => Array.from(row.querySelectorAll('th, td'), (cell) => cell.textContent))
    ).toEqual([
      ['Apr 1, 2026', '85 mg/dL', 'Within the reference range (per report)', 'Checked by you'],
      ['Apr 10, 2026', '118 mg/dL', 'Above the reference range (per report)', 'Not yet checked'],
      ['Apr 20, 2026', '96.5 mg/dL', 'Within the reference range (per report)', 'Checked by you'],
    ]);
  });

  it('HC-UIRR-006: no value is ever tweened; every number in every frame of the reveal is a data value', async () => {
    const { RangeRibbon } = await loadRibbon();
    vi.useFakeTimers();
    const { container } = render(
      <RangeRibbon
        trend={series([
          point(APR_1, 85, true),
          point(APR_10, 118, false),
          point(APR_20, 96.5, true),
        ])}
      />
    );
    expect(animateCalls.length).toBeGreaterThan(0);

    // Data values, the band bounds, and the day and year of each date.
    const allowed = new Set(['85', '118', '96.5', '70', '99', '1', '10', '20', '2026']);
    const slider = screen.getByRole('slider');
    const frames: string[] = [];
    for (let elapsed = 0; elapsed <= 640; elapsed += 40) {
      if (elapsed > 0) vi.advanceTimersByTime(40);
      frames.push(`${textNodesOf(container)} ${slider.getAttribute('aria-valuetext') ?? ''}`);
    }

    expect(frames[0]).toContain('96.5 mg/dL');
    for (const frame of frames) {
      for (const token of frame.match(/\d+(?:\.\d+)?/g) ?? []) {
        expect(allowed.has(token)).toBe(true);
      }
    }
  });

  it('HC-UIRR-006: the reveal runs once per analyte per session, and the ribbon renders when sessionStorage throws', async () => {
    const { RangeRibbon } = await loadRibbon();
    const data = series([point(APR_1, 85, true), point(APR_10, 118, false)]);

    const first = render(<RangeRibbon trend={data} />);
    expect(animateCalls.length).toBeGreaterThan(0);
    first.unmount();

    animateCalls = [];
    const second = render(<RangeRibbon trend={data} />);
    expect(animateCalls).toHaveLength(0);
    second.unmount();

    const getSpy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });
    const setSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });
    try {
      const blocked = render(
        <RangeRibbon trend={series(data.data_points, { analyte_canonical: 'hdl' })} />
      );
      expect(screen.getByRole('slider')).toBeInTheDocument();
      expect(screen.getByRole('table')).toBeInTheDocument();
      blocked.unmount();
    } finally {
      getSpy.mockRestore();
      setSpy.mockRestore();
    }
  });

  it('HC-UIRR-007: no hex literal in either component source', async () => {
    const ribbon = (await loadRibbonSource()).default;
    const tick = (await loadTickSource()).default;
    for (const source of [ribbon, tick]) {
      expect(source).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    }
  });

  it('HC-UIRR-007: XMLSerializer output contains the computed token colours', async () => {
    const { RangeRibbon, serializeRangeRibbonSvg } = await loadRibbon();
    const root = document.documentElement;
    root.style.setProperty('--ink-1', '#123456');
    root.style.setProperty('--outside', '#654321');
    try {
      const { container } = render(
        <RangeRibbon trend={series([point(APR_1, 85, true), point(APR_10, 118, true)])} />
      );
      const svg = container.querySelector('svg');
      expect(svg).not.toBeNull();
      const out = serializeRangeRibbonSvg(svg as SVGSVGElement);
      expect(out).toContain('<svg');
      expect(out).toContain('#123456'); // verified (ink) points
      expect(out).toContain('#654321'); // out-of-range triangle
      expect(out).not.toMatch(/var\(--/);
    } finally {
      root.style.removeProperty('--ink-1');
      root.style.removeProperty('--outside');
    }
  });
});

describe('RangeTick', () => {
  const cases = [
    { name: 'low = high = value (5)', value: 5, refLow: 5, refHigh: 5 },
    { name: 'low = high = value (0)', value: 0, refLow: 0, refHigh: 0 },
    { name: 'all zero with both bounds null', value: 0, refLow: null, refHigh: null },
  ];

  for (const testCase of cases) {
    it(`HC-UIRR-008: ${testCase.name} renders no NaN`, async () => {
      const { RangeTick } = await loadTick();
      const { container } = render(
        <RangeTick value={testCase.value} refLow={testCase.refLow} refHigh={testCase.refHigh} />
      );
      expect(container.innerHTML).not.toMatch(/NaN|Infinity/);
      expect(container.querySelector('svg')).not.toBeNull();
      expect(container.querySelector('[data-marker]')).not.toBeNull();
      for (const el of Array.from(container.querySelectorAll('*'))) {
        for (const attr of ['x', 'y', 'cx', 'cy', 'r', 'width', 'height', 'x1', 'x2', 'y1', 'y2']) {
          if (el.hasAttribute(attr)) {
            expect(Number.isFinite(Number(el.getAttribute(attr)))).toBe(true);
          }
        }
      }
    });
  }
});
