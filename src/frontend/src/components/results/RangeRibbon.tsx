/**
 * RangeRibbon: one analyte over time, against the reference range (UI-RIBBON;
 * plan §UI-RIBBON, motion §2.6 M10, data-t0 §2.7).
 *
 * - x is proportional to the date; straight segments between points.
 * - The band is the series-level ref_low..ref_high. TrendPoint carries no
 *   per-report range, and the backend may combine bounds from different reports
 *   (plan gap, escalated to L0). A null bound draws no edge and no triangle.
 * - The band places each point. A printed flag only gives a direction (H, HH,
 *   HIGH above; L, LL, LOW below). A flag that names no direction (null, A, *,
 *   CRITICAL, Normal) leaves the band's call in place. A directional flag that
 *   disagrees with the band, or a directional flag on a point the band calls
 *   within, is a conflict: no triangle and no out-of-range words. is_abnormal is
 *   not read.
 * - With no band on the series, a point gets no range words, whatever its flag.
 * - Unverified points (user_verified is not true, D4) are hollow and dashed;
 *   verified points are filled.
 * - Slider semantics. ← → step and Home/End jump with no transition. A pointer
 *   press picks the nearest point and the cursor glides for --dur-sm; the glide
 *   is a FLIP that ends at identity, so no element keeps a CSS transform.
 * - M10 reveal, once per analyte per session: the line draws in 640 ms and the
 *   points rise from .6 to 1 at 40 ms intervals. The reveal is value-blind, no
 *   number tweens, and reduced motion shows the final frame.
 * - The text layer carries data-t0 (§2.7). Colours are CSS tokens;
 *   serializeRangeRibbonSvg resolves them for export.
 */
import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type ReactElement,
} from 'react';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { duration, ease } from '@/motion/tokens';
import type { TrendData, TrendPoint } from '@/services/types';

const VIEW_W = 320;
const VIEW_H = 160;
const PAD_X = 16;
const PLOT_TOP = 24;
const PLOT_BOTTOM = 136;
const PLOT_W = VIEW_W - PAD_X * 2;
const MARK_R = 5;
const STEP_MS = 40;
const POINT_MS = Math.round(duration.sm * 1000);
const DRAW_MS = Math.round(duration.draw * 1000);
const EASE_OUT = `cubic-bezier(${ease.out.join(', ')})`;
const REVEAL_KEY = 'hc:range-ribbon:revealed:';

type Side = 'above' | 'below' | 'within' | 'none' | 'conflict';
type Move = 'start' | 'pointer' | 'key';

const SIDE_WORDS: Record<Side, string> = {
  above: 'Above the range used for this chart',
  below: 'Below the range used for this chart',
  within: 'Within the range used for this chart',
  none: 'No reference range for this chart',
  conflict: "The report's flag and this chart's range disagree",
};

const SIDE_PHRASE: Record<Side, string> = {
  above: "above this chart's range",
  below: "below this chart's range",
  within: "within this chart's range",
  none: '',
  conflict: "the report's flag and this chart's range disagree",
};

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})/;

interface DateParts {
  year: number;
  month: number;
  day: number;
}

// Dates come from the API as ISO datetimes. The calendar day is read from the
// string itself, so a timezone shift cannot move a point to the day before.
function parseDate(raw: string): DateParts | null {
  const match = ISO_DATE.exec(raw);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  return { year, month, day };
}

function formatDate(parts: DateParts): string {
  return `${MONTHS[parts.month - 1]} ${parts.day}, ${parts.year}`;
}

interface LayoutPoint {
  order: number;
  label: string;
  value: number;
  unit: string;
  verified: boolean;
  side: Side;
  x: number;
  y: number;
}

interface Layout {
  points: LayoutPoint[];
  highY: number | null;
  lowY: number | null;
  band: { top: number; height: number } | null;
}

type BandSide = 'above' | 'below' | 'within' | 'none';

function bandSideOf(value: number, low: number | null, high: number | null): BandSide {
  if (low === null && high === null) return 'none';
  if (high !== null && value > high) return 'above';
  if (low !== null && value < low) return 'below';
  return 'within';
}

type FlagDirection = 'above' | 'below' | 'unknown';

// H, HH and HIGH print above the range; L, LL and LOW below. Any other text (A,
// *, CRITICAL, Normal, null) gives no direction, so it neither confirms nor
// contradicts the band.
function flagDirectionOf(flag: string | null): FlagDirection {
  const code = (flag ?? '').trim().toUpperCase();
  if (code === 'H' || code === 'HH' || code === 'HIGH') return 'above';
  if (code === 'L' || code === 'LL' || code === 'LOW') return 'below';
  return 'unknown';
}

// The band places the point. A directional flag must agree with it, and a flag
// that names no direction leaves the band's call in place.
function sideOf(value: number, flag: FlagDirection, low: number | null, high: number | null): Side {
  const band = bandSideOf(value, low, high);
  if (band === 'none') return 'none';
  if (flag === 'unknown' || flag === band) return band;
  return 'conflict';
}

// Converted values can carry binary noise (normalize.py multiplies without
// rounding, so 99.1 can arrive as 99.10010000000001). Twelve significant digits
// keep every lab value exact and drop the noise.
function cleanNumber(n: number): number {
  return Number(n.toPrecision(12));
}

function finiteOrNull(n: number | null): number | null {
  return typeof n === 'number' && Number.isFinite(n) ? cleanNumber(n) : null;
}

function buildLayout(trend: TrendData): Layout {
  const low = finiteOrNull(trend.ref_low);
  const high = finiteOrNull(trend.ref_high);

  const parsed = trend.data_points.flatMap((raw: TrendPoint, index) => {
    const parts = parseDate(raw.date);
    if (!parts || !Number.isFinite(raw.value)) return [];
    return [
      {
        raw,
        index,
        parts,
        value: cleanNumber(raw.value),
        time: Date.UTC(parts.year, parts.month - 1, parts.day),
      },
    ];
  });
  if (parsed.length === 0) return { points: [], highY: null, lowY: null, band: null };
  parsed.sort((a, b) => a.time - b.time || a.index - b.index);

  const tMin = parsed[0].time;
  const tMax = parsed[parsed.length - 1].time;
  const xOf = (time: number): number =>
    tMax > tMin ? PAD_X + ((time - tMin) / (tMax - tMin)) * PLOT_W : PAD_X + PLOT_W / 2;

  const domain = [
    ...parsed.map((p) => p.value),
    ...(low !== null ? [low] : []),
    ...(high !== null ? [high] : []),
  ];
  let lo = Math.min(...domain);
  let hi = Math.max(...domain);
  const span = hi - lo;
  const pad = span > 0 ? span * 0.15 : Math.max(Math.abs(hi) * 0.2, 1);
  lo -= pad;
  hi += pad;
  const yOf = (value: number): number =>
    PLOT_BOTTOM - ((value - lo) / (hi - lo)) * (PLOT_BOTTOM - PLOT_TOP);

  const points: LayoutPoint[] = parsed.map((p, order) => ({
    order,
    label: formatDate(p.parts),
    value: p.value,
    unit: p.raw.unit,
    verified: p.raw.user_verified === true,
    side: sideOf(p.value, flagDirectionOf(p.raw.flag), low, high),
    x: xOf(p.time),
    y: yOf(p.value),
  }));

  const highY = high !== null ? yOf(high) : null;
  const lowY = low !== null ? yOf(low) : null;
  const band =
    highY !== null && lowY !== null
      ? { top: Math.min(highY, lowY), height: Math.abs(lowY - highY) }
      : null;
  return { points, highY, lowY, band };
}

// No source rule in the words: the backend prefers one observation with both
// limits and otherwise combines the latest per limit (api/observations.py).
function rangeCaption(low: number | null, high: number | null, unit: string): string {
  const suffix = unit.trim() === '' ? '' : ` ${unit}`;
  if (low !== null && high !== null) return `Reference range used for this chart: ${low}-${high}${suffix}`;
  if (high !== null) return `Upper limit used for this chart: ${high}${suffix}`;
  if (low !== null) return `Lower limit used for this chart: ${low}${suffix}`;
  return 'No reference range on the reports';
}

function valueLabel(point: LayoutPoint): string {
  return [point.value, point.unit].filter((part) => part !== '').join(' ');
}

function valueTextOf(point: LayoutPoint): string {
  const parts = [`${point.label}: ${valueLabel(point)}`];
  const phrase = SIDE_PHRASE[point.side];
  if (phrase !== '') parts.push(phrase);
  parts.push(point.verified ? 'checked by you' : 'not yet checked');
  return parts.join(', ');
}

function nearestIndex(points: LayoutPoint[], x: number): number {
  let best = 0;
  for (let i = 1; i < points.length; i += 1) {
    if (Math.abs(points[i].x - x) < Math.abs(points[best].x - x)) best = i;
  }
  return best;
}

// A view that cannot read or write sessionStorage still renders. The reveal then
// may replay on the next mount, which is cosmetic only.
function hasRevealed(analyte: string): boolean {
  try {
    return window.sessionStorage.getItem(REVEAL_KEY + analyte) === '1';
  } catch {
    return false;
  }
}

function markRevealed(analyte: string): void {
  try {
    window.sessionStorage.setItem(REVEAL_KEY + analyte, '1');
  } catch {
    // Storage is blocked. The reveal may replay on the next mount.
  }
}

function triangleD(x: number, y: number, side: 'above' | 'below'): string {
  return side === 'above'
    ? `M ${x - 5} ${y - 9} L ${x + 5} ${y - 9} L ${x} ${y - 15} Z`
    : `M ${x - 5} ${y + 9} L ${x + 5} ${y + 9} L ${x} ${y + 15} Z`;
}

interface RangeRibbonProps {
  trend: TrendData;
}

export function RangeRibbon({ trend }: RangeRibbonProps): ReactElement {
  const layout = useMemo(() => buildLayout(trend), [trend]);
  if (layout.points.length === 0) {
    return <p className="text-sm text-ink-secondary">No values to chart yet.</p>;
  }
  // Keyed by analyte: a different analyte gets fresh selection and reveal state.
  return <RangeChart key={trend.analyte_canonical} trend={trend} layout={layout} />;
}

interface RangeChartProps {
  trend: TrendData;
  layout: Layout;
}

function RangeChart({ trend, layout }: RangeChartProps): ReactElement {
  const { points } = layout;
  const count = points.length;
  const reduced = useReducedMotion();
  const analyte = trend.analyte_canonical;

  // Decided once per mount. The reveal is written in an effect, so StrictMode's
  // double render cannot see its own write and skip the reveal.
  const [revealing] = useState(() => !reduced && !hasRevealed(analyte));
  const [selected, setSelected] = useState(() => count - 1);
  const [move, setMove] = useState<Move>('start');

  const svgRef = useRef<SVGSVGElement>(null);
  const lineRef = useRef<SVGGElement>(null);
  const cursorRef = useRef<SVGLineElement>(null);
  const lastX = useRef<number | null>(null);

  useEffect(() => {
    if (revealing) markRevealed(analyte);
  }, [revealing, analyte]);

  useLayoutEffect(() => {
    if (!revealing) return undefined;
    const svg = svgRef.current;
    const line = lineRef.current;
    if (!svg || !line || typeof line.animate !== 'function') return undefined;
    const running: Animation[] = [
      line.animate([{ clipPath: 'inset(0 100% 0 0)' }, { clipPath: 'inset(0)' }], {
        duration: DRAW_MS,
        easing: EASE_OUT,
        fill: 'both',
      }),
    ];
    svg.querySelectorAll<SVGGElement>('[data-point-index]').forEach((group) => {
      const index = Number(group.getAttribute('data-point-index'));
      running.push(
        group.animate([{ transform: 'scale(0.6)' }, { transform: 'scale(1)' }], {
          duration: POINT_MS,
          delay: index * STEP_MS,
          easing: EASE_OUT,
          fill: 'backwards',
        })
      );
    });
    return () => running.forEach((animation) => animation.cancel());
  }, [revealing]);

  const active = Math.min(Math.max(selected, 0), count - 1);
  const current = points[active];
  const currentX = current.x;

  // The cursor is placed by its x1/x2, so it never holds a CSS transform (G5).
  // A pointer move glides it with a FLIP that ends at identity. A keyboard move
  // and reduced motion skip the glide.
  useLayoutEffect(() => {
    const previous = lastX.current;
    lastX.current = currentX;
    if (previous === null || previous === currentX || move !== 'pointer' || reduced) {
      return undefined;
    }
    const cursor = cursorRef.current;
    if (!cursor || typeof cursor.animate !== 'function') return undefined;
    const glide = cursor.animate(
      [{ transform: `translateX(${previous - currentX}px)` }, { transform: 'translateX(0px)' }],
      { duration: POINT_MS, easing: EASE_OUT }
    );
    return () => glide.cancel();
  }, [currentX, move, reduced]);

  const choose = (index: number, how: 'pointer' | 'key') => {
    setMove(how);
    setSelected(index);
  };

  // The pointer picks the nearest point to its x, so a press between two close
  // dates lands on the nearer one, with no small hit target to miss.
  const onPointerDown = (event: PointerEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    if (rect.width <= 0) return;
    const x = ((event.clientX - rect.left) / rect.width) * VIEW_W;
    choose(nearestIndex(points, x), 'pointer');
  };

  const onKeyDown = (event: KeyboardEvent<SVGSVGElement>) => {
    const last = count - 1;
    let next: number;
    switch (event.key) {
      case 'ArrowLeft':
        next = Math.max(0, active - 1);
        break;
      case 'ArrowRight':
        next = Math.min(last, active + 1);
        break;
      case 'Home':
        next = 0;
        break;
      case 'End':
        next = last;
        break;
      default:
        return;
    }
    event.preventDefault();
    choose(next, 'key');
  };

  const firstPoint = points[0];
  const lastPoint = points[count - 1];

  return (
    <figure className="space-y-2">
      <svg
        ref={svgRef}
        role="slider"
        tabIndex={0}
        aria-label={`${trend.analyte_display_name}: results over time`}
        aria-valuemin={0}
        aria-valuemax={count - 1}
        aria-valuenow={active}
        aria-valuetext={valueTextOf(current)}
        onKeyDown={onKeyDown}
        onPointerDown={onPointerDown}
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        width="100%"
        style={{ cursor: 'pointer' }}
        className="block h-auto w-full rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        {layout.band && (
          <rect
            data-band
            x={PAD_X}
            y={layout.band.top}
            width={PLOT_W}
            height={layout.band.height}
            fill="var(--band)"
          />
        )}
        {layout.highY !== null && (
          <line
            data-band-edge="high"
            x1={PAD_X}
            x2={PAD_X + PLOT_W}
            y1={layout.highY}
            y2={layout.highY}
            stroke="var(--line-strong)"
            strokeWidth={1}
          />
        )}
        {layout.lowY !== null && (
          <line
            data-band-edge="low"
            x1={PAD_X}
            x2={PAD_X + PLOT_W}
            y1={layout.lowY}
            y2={layout.lowY}
            stroke="var(--line-strong)"
            strokeWidth={1}
          />
        )}

        <g ref={lineRef} data-line>
          <polyline
            points={points.map((p) => `${p.x},${p.y}`).join(' ')}
            fill="none"
            stroke="var(--line-strong)"
            strokeWidth={1.5}
            strokeLinejoin="round"
          />
        </g>

        {points.map((p) => (
          <g
            key={p.order}
            data-point-index={p.order}
            data-verified={String(p.verified)}
            data-side={p.side}
            style={{ transformBox: 'fill-box', transformOrigin: 'center' }}
          >
            {p.verified ? (
              <circle data-marker cx={p.x} cy={p.y} r={MARK_R} fill="var(--ink-1)" stroke="none" />
            ) : (
              <circle
                data-marker
                cx={p.x}
                cy={p.y}
                r={MARK_R}
                fill="none"
                stroke="var(--pencil)"
                strokeWidth={1.5}
                strokeDasharray="3 2"
              />
            )}
          </g>
        ))}

        {/* Outside the animated groups: the triangle is static, and a point's reveal scales only its marker. */}
        {points.map((p) =>
          p.side === 'above' || p.side === 'below' ? (
            <path
              key={p.order}
              data-triangle={p.side}
              data-triangle-for={p.order}
              d={triangleD(p.x, p.y, p.side)}
              fill="var(--outside)"
            >
              <title>{SIDE_WORDS[p.side]}</title>
            </path>
          ) : null
        )}

        <line
          ref={cursorRef}
          data-cursor
          aria-hidden="true"
          x1={currentX}
          x2={currentX}
          y1={PLOT_TOP - 6}
          y2={PLOT_BOTTOM + 6}
          stroke="var(--ink-1)"
          strokeWidth={1}
          strokeDasharray="2 2"
        />
      </svg>

      <figcaption data-t0 className="text-sm text-ink-secondary">
        {rangeCaption(
          finiteOrNull(trend.ref_low),
          finiteOrNull(trend.ref_high),
          trend.unit
        )}
      </figcaption>

      <div className="flex justify-between text-xs text-ink-secondary">
        <span data-axis="first" data-t0>{firstPoint.label}</span>
        {count > 1 && <span data-axis="last" data-t0>{lastPoint.label}</span>}
      </div>

      <p data-readout data-t0 className="text-sm text-ink-secondary">
        <span className="font-medium text-ink">
          {current.label}: {valueLabel(current)}
        </span>
        {current.side !== 'none' && <span> · {SIDE_WORDS[current.side]}</span>}
        <span> · {current.verified ? 'Checked by you' : 'Not yet checked'}</span>
      </p>

      <table className="w-full text-sm">
        <caption className="sr-only">{`${trend.analyte_display_name} results by date`}</caption>
        <thead>
          <tr className="text-left text-ink-secondary">
            <th data-t0 scope="col" className="font-normal">Date</th>
            <th data-t0 scope="col" className="font-normal">Result</th>
            <th data-t0 scope="col" className="font-normal">{"Against the report's range"}</th>
            <th data-t0 scope="col" className="font-normal">Checked</th>
          </tr>
        </thead>
        <tbody>
          {points.map((p) => (
            <tr key={p.order}>
              <th data-t0 scope="row" className="text-left font-normal">{p.label}</th>
              <td data-t0>{valueLabel(p)}</td>
              <td data-t0>{SIDE_WORDS[p.side]}</td>
              <td data-t0>{p.verified ? 'Checked by you' : 'Not yet checked'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

/**
 * Serialises the ribbon SVG for export. A standalone SVG has no page CSS, so each
 * var(--token) is replaced with its computed value (currentColor if the token is
 * unset). The size is fixed to the viewBox, because the on-screen width is 100%.
 */
export function serializeRangeRibbonSvg(svg: SVGSVGElement): string {
  // XMLSerializer adds the SVG namespace itself. A setAttribute('xmlns') here
  // would duplicate it, and the output would not be well-formed XML.
  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute('width', String(VIEW_W));
  clone.setAttribute('height', String(VIEW_H));
  const computed = window.getComputedStyle(document.documentElement);
  const markup = new XMLSerializer().serializeToString(clone);
  return markup.replace(/var\((--[\w-]+)\)/g, (_match, token: string) => {
    return computed.getPropertyValue(token).trim() || 'currentColor';
  });
}
