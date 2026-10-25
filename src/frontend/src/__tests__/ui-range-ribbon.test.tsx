/**
 * UI-RIBBON: RangeRibbon and RangeTick (HC-UIRR-001..008).
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md (UI-RIBBON; §2.6 M10; §2.7 data-t0).
 *
 * The components are loaded with a dynamic import inside each test, so before
 * they exist every id fails on its own line instead of the whole file failing
 * to load.
 *
 * Review round 1 added cases for data-t0 (G10), a cursor with no CSS transform
 * (G5), the band-versus-report conflict, the range caption, the date labels,
 * nearest-point pointer selection, the keyed reveal and the export size.
 *
 * Review round 2 added cases for flag direction (a null, non-directional or
 * absent flag does not decide the side), the caption wording, triangles kept
 * outside animated groups, clean number text and the glide keyframes.
 */
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
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

const ABOVE_WORDS = 'Above the reference range (per report)';
const BELOW_WORDS = 'Below the reference range (per report)';
const CONFLICT_WORDS = "The report's flag and this range disagree";
const REVEAL_KEY = 'hc:range-ribbon:revealed:glucose';

// `abnormal` is the report's is_abnormal, which the backend sets to flag !== null
// (api/documents.py). `flag` is the printed flag text. It defaults to the flag a
// flagged point would carry, and an explicit null or other text overrides it.
function point(
  date: string,
  value: number,
  verified?: boolean,
  abnormal: boolean = value < 70 || value > 99,
  flag: string | null = abnormal ? (value < 70 ? 'L' : 'H') : null
): TrendPoint {
  return {
    date,
    value,
    unit: 'mg/dL',
    is_abnormal: abnormal,
    flag,
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

// Records every Element.animate call with its target, so the reveal and the
// glide can be inspected. jsdom has no Web Animations API.
interface AnimateCall {
  target: Element;
  keyframes: unknown;
  options: Record<string, unknown>;
}
let animateCalls: AnimateCall[] = [];

let hadPointerEvent = false;
beforeAll(() => {
  // jsdom has no PointerEvent. MouseEvent takes the same clientX init.
  hadPointerEvent = 'PointerEvent' in window;
  if (!hadPointerEvent) {
    Object.defineProperty(window, 'PointerEvent', { configurable: true, value: MouseEvent });
  }
});

afterAll(() => {
  if (!hadPointerEvent) {
    delete (window as unknown as { PointerEvent?: unknown }).PointerEvent;
  }
});

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
  vi.restoreAllMocks();
});

function pointGroup(container: HTMLElement, index: number): Element {
  const group = container.querySelector(`[data-point-index="${index}"]`);
  if (!group) throw new Error(`no point group ${index}`);
  return group;
}

function markerOf(container: HTMLElement, index: number): Element {
  const marker = container.querySelector(`[data-point-index="${index}"] [data-marker]`);
  if (!marker) throw new Error(`no marker ${index}`);
  return marker;
}

// The triangle sits beside its point, not inside the animated point group.
function triangleFor(container: HTMLElement, index: number): HTMLElement {
  const triangle = container.querySelector(`[data-triangle-for="${index}"]`);
  if (!triangle) throw new Error(`no triangle for point ${index}`);
  return triangle as HTMLElement;
}

function cxOf(container: HTMLElement, index: number): number {
  return Number(markerOf(container, index).getAttribute('cx'));
}

function cyOf(container: HTMLElement, index: number): number {
  return Number(markerOf(container, index).getAttribute('cy'));
}

function cursorOf(container: HTMLElement): SVGLineElement {
  const cursor = container.querySelector<SVGLineElement>('[data-cursor]');
  if (!cursor) throw new Error('no cursor');
  return cursor;
}

function sliderOf(): SVGSVGElement {
  return screen.getByRole('slider') as unknown as SVGSVGElement;
}

function selectedOf(): number {
  return Number(sliderOf().getAttribute('aria-valuenow'));
}

// Puts a pointerdown at `clientX` on the slider. The SVG is 320 units wide and
// its rect is mocked to 320 px, so a client x is also a user-unit x.
function pointerAt(clientX: number): void {
  const svg = sliderOf();
  vi.spyOn(svg, 'getBoundingClientRect').mockReturnValue({
    left: 0,
    top: 0,
    right: 320,
    bottom: 160,
    width: 320,
    height: 160,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  } as DOMRect);
  fireEvent.pointerDown(svg, { clientX });
}

function cursorAnimations(): AnimateCall[] {
  return animateCalls.filter((call) => call.target.hasAttribute('data-cursor'));
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
    expect(container.querySelector('[data-triangle-for="0"]')).toBeNull();
    expect(within(triangleFor(container, 1)).getByText(ABOVE_WORDS)).toBeInTheDocument();
    expect(within(triangleFor(container, 2)).getByText(BELOW_WORDS)).toBeInTheDocument();

    // The words are visible in the readout and the table, not only in the hover title.
    expect(container.querySelector('[data-readout]')?.textContent).toContain(BELOW_WORDS);
    const table = screen.getByRole('table');
    expect(within(table).getByText(ABOVE_WORDS)).toBeInTheDocument();
    expect(within(table).getByText(BELOW_WORDS)).toBeInTheDocument();
  });

  it('HC-UIRR-002: a null bound draws no band edge on that side and no triangle against it', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(
      <RangeRibbon
        trend={series(
          [point(APR_1, 0.5, true, false), point(APR_10, 118, true)],
          { ref_low: null, ref_high: 99 }
        )}
      />
    );
    expect(container.querySelector('[data-band-edge="high"]')).not.toBeNull();
    expect(container.querySelector('[data-band-edge="low"]')).toBeNull();
    expect(container.querySelector('[data-band]')).toBeNull();
    expect(container.querySelector('[data-triangle-for="0"]')).toBeNull();
    expect(container.querySelector('[data-triangle-for="1"][data-triangle="above"]')).not.toBeNull();
  });

  it('HC-UIRR-002: the range is printed as numbers in a caption outside the chart, for both, one and no bounds', async () => {
    const { RangeRibbon } = await loadRibbon();
    // The caption names the range without a source rule: the backend prefers one
    // observation with both limits, and otherwise combines the latest per limit.
    const cases: Array<{ overrides: Partial<TrendData>; words: string }> = [
      {
        overrides: {},
        words: 'Reference range used for this chart: 70-99 mg/dL',
      },
      {
        overrides: { ref_low: null },
        words: 'Upper limit used for this chart: 99 mg/dL',
      },
      {
        overrides: { ref_high: null },
        words: 'Lower limit used for this chart: 70 mg/dL',
      },
      {
        overrides: { ref_low: null, ref_high: null },
        words: 'No reference range on the reports',
      },
    ];
    for (const testCase of cases) {
      const { container, unmount } = render(
        <RangeRibbon trend={series([point(APR_1, 85, true), point(APR_10, 90, true)], testCase.overrides)} />
      );
      const caption = container.querySelector('figcaption');
      expect(caption?.textContent).toBe(testCase.words);
      expect(caption?.closest('svg')).toBeNull();
      unmount();
    }
  });

  it('HC-UIRR-002: a directional flag that disagrees with the band is a conflict, with no triangle and no out-of-range words', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(
      <RangeRibbon
        trend={series([
          // Inside the band, but the report flagged it high.
          point(APR_1, 85, true, true, 'H'),
          // Above the band, but the report flagged it low: the report's own range differs.
          point(APR_10, 118, true, true, 'L'),
        ])}
      />
    );
    expect(pointGroup(container, 0).getAttribute('data-side')).toBe('conflict');
    expect(pointGroup(container, 1).getAttribute('data-side')).toBe('conflict');
    expect(container.querySelectorAll('[data-triangle]')).toHaveLength(0);
    expect(screen.queryByText(ABOVE_WORDS)).toBeNull();
    expect(screen.queryByText(BELOW_WORDS)).toBeNull();
    expect(sliderOf()).toHaveAttribute(
      'aria-valuetext',
      "Apr 10, 2026: 118 mg/dL, the report's flag and this range disagree, checked by you"
    );
    expect(within(screen.getByRole('table')).getAllByText(CONFLICT_WORDS)).toHaveLength(2);
  });

  it('HC-UIRR-002: a null, "A" or "Normal" flag names no direction, so the band still places the point', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(
      <RangeRibbon
        trend={series([
          // Above the band with no flag captured: the band still places it.
          point(APR_1, 118, true, false, null),
          // Inside the band, with a FHIR "Normal" interpretation: no conflict.
          point(APR_10, 85, true, true, 'Normal'),
          // Above the band, with a flag that gives no direction.
          point(APR_20, 120, true, true, 'A'),
        ])}
      />
    );
    expect(pointGroup(container, 0).getAttribute('data-side')).toBe('above');
    expect(pointGroup(container, 1).getAttribute('data-side')).toBe('within');
    expect(pointGroup(container, 2).getAttribute('data-side')).toBe('above');
    expect(container.querySelectorAll('[data-triangle]')).toHaveLength(2);
    expect(within(triangleFor(container, 0)).getByText(ABOVE_WORDS)).toBeInTheDocument();
    expect(container.querySelector('[data-triangle-for="1"]')).toBeNull();
    expect(screen.queryByText(CONFLICT_WORDS)).toBeNull();
  });

  it('HC-UIRR-002: H, HH and HIGH read above the band and LOW and Low read below it, whatever is_abnormal says', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(
      <RangeRibbon
        trend={series([
          point(APR_1, 118, true, false, 'HH'),
          point(APR_10, 60, true, false, 'Low'),
          point(APR_20, 118, true, false, 'High'),
        ])}
      />
    );
    expect(pointGroup(container, 0).getAttribute('data-side')).toBe('above');
    expect(pointGroup(container, 1).getAttribute('data-side')).toBe('below');
    expect(pointGroup(container, 2).getAttribute('data-side')).toBe('above');
    expect(container.querySelectorAll('[data-triangle]')).toHaveLength(3);
  });

  it('HC-UIRR-002: with no band on the series, a flag gives no range words and no triangle', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(
      <RangeRibbon
        trend={series(
          [point(APR_1, 85, true, false, null), point(APR_10, 118, true, true, 'H')],
          { ref_low: null, ref_high: null }
        )}
      />
    );
    expect(pointGroup(container, 1).getAttribute('data-side')).toBe('none');
    expect(container.querySelectorAll('[data-triangle]')).toHaveLength(0);
    expect(screen.queryByText(CONFLICT_WORDS)).toBeNull();
    expect(screen.queryByText(ABOVE_WORDS)).toBeNull();
    expect(sliderOf()).toHaveAttribute('aria-valuetext', 'Apr 10, 2026: 118 mg/dL, checked by you');
  });

  it('HC-UIRR-004: no triangle sits inside an animated point, so an out-of-range point scales about its marker like an in-range one', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(
      <RangeRibbon
        trend={series([point(APR_1, 85, true), point(APR_10, 118, true), point(APR_20, 60, true)])}
      />
    );
    expect(animateCalls.some((call) => call.target.hasAttribute('data-point-index'))).toBe(true);
    for (const call of animateCalls) {
      expect(call.target.querySelector('[data-triangle]')).toBeNull();
      expect(call.target.closest('[data-triangle]')).toBeNull();
    }
    // The triangles still exist, drawn beside their points.
    expect(container.querySelectorAll('[data-triangle]')).toHaveLength(2);
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
    const marker = (index: number) => markerOf(container, index);

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
      pointerAt(cxOf(container, 0));
      expect(selectedOf()).toBe(0);
      expect(cursorAnimations()).toHaveLength(0);
      expect(cursorOf(container).style.transform).toBe('');
      expect(Number(cursorOf(container).getAttribute('x1'))).toBeCloseTo(cxOf(container, 0), 3);
    } finally {
      window.matchMedia = original;
    }
  });

  it('HC-UIRR-005: ArrowLeft, ArrowRight, Home and End move the selection, clamp at the ends, and the cursor never has a CSS transform', async () => {
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
    const slider = sliderOf();
    // The default selection is the latest point.
    expect(slider).toHaveAttribute(
      'aria-valuetext',
      "Apr 20, 2026: 60 mg/dL, below the report's range, checked by you"
    );
    // The cursor is a line placed at the selected point's x: no transform, so G5 can pass.
    const cursorAt = (index: number) => {
      expect(cursorOf(container).style.transform).toBe('');
      expect(Number(cursorOf(container).getAttribute('x1'))).toBeCloseTo(cxOf(container, index), 3);
      expect(Number(cursorOf(container).getAttribute('x2'))).toBeCloseTo(cxOf(container, index), 3);
    };
    cursorAt(2);

    fireEvent.keyDown(slider, { key: 'Home' });
    expect(selectedOf()).toBe(0);
    cursorAt(0);
    fireEvent.keyDown(slider, { key: 'ArrowLeft' });
    expect(selectedOf()).toBe(0);

    fireEvent.keyDown(slider, { key: 'ArrowRight' });
    expect(selectedOf()).toBe(1);
    expect(slider).toHaveAttribute(
      'aria-valuetext',
      "Apr 10, 2026: 118 mg/dL, above the report's range, not yet checked"
    );
    cursorAt(1);

    fireEvent.keyDown(slider, { key: 'End' });
    expect(selectedOf()).toBe(2);
    fireEvent.keyDown(slider, { key: 'ArrowRight' });
    expect(selectedOf()).toBe(2);
    cursorAt(2);

    fireEvent.keyDown(slider, { key: 'ArrowLeft' });
    expect(selectedOf()).toBe(1);
    cursorAt(1);

    // No transition runs on any keyboard move.
    expect(cursorAnimations()).toHaveLength(0);
  });

  it('HC-UIRR-005: a pointer selection picks the nearest point and glides the cursor for --dur-sm (180 ms)', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(
      <RangeRibbon trend={series([point(APR_1, 85, true), point(APR_10, 118, false), point(APR_20, 60, true)])} />
    );
    // Two user units from point 1 is still nearest to point 1, not to a 12-unit hit area.
    pointerAt(cxOf(container, 1) - 2);
    expect(selectedOf()).toBe(1);
    expect(cursorOf(container).style.transform).toBe('');
    expect(Number(cursorOf(container).getAttribute('x1'))).toBeCloseTo(cxOf(container, 1), 3);

    const glides = cursorAnimations();
    expect(glides).toHaveLength(1);
    expect(glides[0].options.duration).toBe(180);
    // The glide starts one step back, at the previous x, and ends at identity with no fill.
    const keyframes = glides[0].keyframes as Array<{ transform: string }>;
    expect(keyframes).toHaveLength(2);
    expect(keyframes[keyframes.length - 1].transform).toBe('translateX(0px)');
    expect(glides[0].options).not.toHaveProperty('fill');
    const offset = Number(/^translateX\((-?[\d.e+-]+)px\)$/.exec(keyframes[0].transform)?.[1]);
    expect(offset).toBeCloseTo(cxOf(container, 2) - cxOf(container, 1), 6);

    // A keyboard move after a pointer move does not glide.
    fireEvent.keyDown(sliderOf(), { key: 'ArrowRight' });
    expect(selectedOf()).toBe(2);
    expect(cursorAnimations()).toHaveLength(1);
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
      ['Apr 10, 2026', '118 mg/dL', ABOVE_WORDS, 'Not yet checked'],
      ['Apr 20, 2026', '96.5 mg/dL', 'Within the reference range (per report)', 'Checked by you'],
    ]);
  });

  it('HC-UIRR-006: the text layer carries data-t0 (readout, table cells, caption, date labels); the line, points and cursor do not', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(
      <RangeRibbon
        trend={series([point(APR_1, 85, true), point(APR_10, 118, false), point(APR_20, 96.5, true)])}
      />
    );
    expect(container.querySelector('[data-readout]')).toHaveAttribute('data-t0');
    expect(container.querySelector('figcaption')).toHaveAttribute('data-t0');
    expect(container.querySelector('[data-axis="first"]')).toHaveAttribute('data-t0');
    expect(container.querySelector('[data-axis="first"]')?.textContent).toBe('Apr 1, 2026');
    expect(container.querySelector('[data-axis="last"]')).toHaveAttribute('data-t0');
    expect(container.querySelector('[data-axis="last"]')?.textContent).toBe('Apr 20, 2026');

    const cells = Array.from(screen.getByRole('table').querySelectorAll('th, td'));
    expect(cells.length).toBeGreaterThan(0);
    for (const cell of cells) {
      expect(cell).toHaveAttribute('data-t0');
    }

    expect(container.querySelector('polyline')).not.toBeNull();
    expect(container.querySelector('polyline')).not.toHaveAttribute('data-t0');
    expect(container.querySelector('[data-cursor]')).not.toHaveAttribute('data-t0');
    for (const marker of Array.from(container.querySelectorAll('[data-marker]'))) {
      expect(marker).not.toHaveAttribute('data-t0');
      expect(marker.closest('[data-t0]')).toBeNull();
    }
    for (const group of Array.from(container.querySelectorAll('[data-point-index]'))) {
      expect(group).not.toHaveAttribute('data-t0');
    }
  });

  it('HC-UIRR-006: a result whose date the ribbon cannot read is left out of the chart and the table, and the rest stay correct', async () => {
    const { RangeRibbon } = await loadRibbon();
    const { container } = render(
      <RangeRibbon
        trend={series([point(APR_1, 85, true), point('04/10/2026', 118, true), point(APR_20, 90, true)])}
      />
    );
    expect(container.querySelectorAll('[data-point-index]')).toHaveLength(2);
    const rows = within(screen.getByRole('table')).getAllByRole('row').slice(1);
    expect(rows.map((row) => row.querySelector('th')?.textContent)).toEqual(['Apr 1, 2026', 'Apr 20, 2026']);
    expect(screen.queryByText('118 mg/dL')).toBeNull();
  });

  it('HC-UIRR-006: a converted value with binary noise shows its clean number in the table, the readout and aria-valuetext', async () => {
    const { RangeRibbon } = await loadRibbon();
    // 99.10010000000001 is what a unit conversion can leave behind (normalize.py multiplies
    // without rounding). Its clean value is 99.1001.
    const { container } = render(
      <RangeRibbon trend={series([point(APR_1, 85, true), point(APR_10, 99.10010000000001, true, true)])} />
    );
    expect(sliderOf()).toHaveAttribute(
      'aria-valuetext',
      "Apr 10, 2026: 99.1001 mg/dL, above the report's range, checked by you"
    );
    const rows = within(screen.getByRole('table')).getAllByRole('row').slice(1);
    expect(rows[1].querySelectorAll('td')[0].textContent).toBe('99.1001 mg/dL');
    expect(textNodesOf(container)).not.toContain('99.10010000000001');
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

    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });
    const blocked = render(
      <RangeRibbon trend={series(data.data_points, { analyte_canonical: 'hdl' })} />
    );
    expect(screen.getByRole('slider')).toBeInTheDocument();
    expect(screen.getByRole('table')).toBeInTheDocument();
    blocked.unmount();
  });

  it('HC-UIRR-006: an empty first render does not use up the reveal, and a changed analyte reveals again', async () => {
    const { RangeRibbon } = await loadRibbon();
    const glucose = series([point(APR_1, 85, true), point(APR_10, 118, true)]);
    const { rerender } = render(<RangeRibbon trend={series([])} />);
    expect(animateCalls).toHaveLength(0);
    expect(sessionStorage.getItem(REVEAL_KEY)).toBeNull();

    // Data arrives after the empty first render: it draws, and selects the latest point.
    rerender(<RangeRibbon trend={glucose} />);
    expect(animateCalls.length).toBeGreaterThan(0);
    expect(selectedOf()).toBe(1);

    animateCalls = [];
    rerender(
      <RangeRibbon
        trend={series([point(APR_1, 90, true), point(APR_10, 100, true)], {
          analyte_canonical: 'hdl',
          analyte_display_name: 'HDL',
        })}
      />
    );
    expect(animateCalls.length).toBeGreaterThan(0);
    expect(selectedOf()).toBe(1);
    expect(sliderOf()).toHaveAttribute('aria-label', 'HDL: results over time');
  });

  it('HC-UIRR-007: no hex literal in either component source', async () => {
    const ribbon = (await loadRibbonSource()).default;
    const tick = (await loadTickSource()).default;
    for (const source of [ribbon, tick]) {
      expect(source).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    }
  });

  it('HC-UIRR-007: XMLSerializer output carries every token colour, a fixed size, and no currentColor fallback', async () => {
    const { RangeRibbon, serializeRangeRibbonSvg } = await loadRibbon();
    const root = document.documentElement;
    // Every token the ribbon uses. An unset token would fall back to currentColor.
    const tokens: Record<string, string> = {
      '--band': '#0a0a0a',
      '--line-strong': '#1a1a1a',
      '--pencil': '#2a2a2a',
      '--ink-1': '#123456',
      '--outside': '#654321',
    };
    for (const [name, value] of Object.entries(tokens)) root.style.setProperty(name, value);
    try {
      const { container } = render(
        <RangeRibbon
          trend={series([point(APR_1, 85, true), point(APR_10, 118, true), point(APR_20, 90, false)])}
        />
      );
      const svg = container.querySelector('svg');
      expect(svg).not.toBeNull();
      const out = serializeRangeRibbonSvg(svg as SVGSVGElement);
      expect(out).not.toMatch(/var\(--/);
      expect(out).not.toContain('currentColor');
      for (const value of Object.values(tokens)) {
        expect(out).toContain(value);
      }
      // The export must be well-formed XML, or a viewer refuses the file.
      const parsed = new DOMParser().parseFromString(out, 'image/svg+xml');
      expect(parsed.getElementsByTagName('parsererror')).toHaveLength(0);
      expect(parsed.documentElement.getAttribute('width')).toBe('320');
      expect(parsed.documentElement.getAttribute('height')).toBe('160');
    } finally {
      for (const name of Object.keys(tokens)) root.style.removeProperty(name);
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
