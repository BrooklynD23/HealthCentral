/**
 * RangeRibbon: one analyte over time, against the reference range printed on
 * the reports (UI-RIBBON; plan §UI-RIBBON, motion §2.6 M10).
 *
 * - x is proportional to the date; straight segments between points.
 * - The band is the series-level ref_low..ref_high (TrendPoint carries no
 *   per-report range). A null bound draws no edge and no triangle on that side.
 * - Out of range means value > ref_high or value < ref_low, never the flag.
 *   An out-of-range point gets a static triangle and the words "(per report)".
 * - Unverified points (user_verified is not true, D4) are hollow and dashed;
 *   verified points are filled.
 * - Slider semantics. ← → step and Home/End jump with no transition; a pointer
 *   selection glides for --dur-sm. A table gives the same dates and values.
 * - M10 reveal, once per analyte per session: the line draws in 640 ms and the
 *   points rise from .6 to 1 at 40 ms intervals. The reveal is value-blind, no
 *   number tweens, and reduced motion shows the final frame.
 * - Colours are CSS tokens. serializeRangeRibbonSvg resolves them for export.
 */
import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
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
const HIT_R = 12;
const MARK_R = 5;
const STEP_MS = 40;
const POINT_MS = Math.round(duration.sm * 1000);
const DRAW_MS = Math.round(duration.draw * 1000);
const EASE_OUT = `cubic-bezier(${ease.out.join(', ')})`;
const GLIDE = 'transform var(--dur-sm) var(--ease-out)';
const REVEAL_KEY = 'hc:range-ribbon:revealed:';

type Side = 'above' | 'below' | 'within' | 'none';

const SIDE_WORDS: Record<Side, string> = {
  above: 'Above the reference range (per report)',
  below: 'Below the reference range (per report)',
  within: 'Within the reference range (per report)',
  none: 'No reference range on the report',
};

const SIDE_PHRASE: Record<Side, string> = {
  above: "above the report's range",
  below: "below the report's range",
  within: "within the report's range",
  none: '',
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

function sideOf(value: number, low: number | null, high: number | null): Side {
  if (low === null && high === null) return 'none';
  if (high !== null && value > high) return 'above';
  if (low !== null && value < low) return 'below';
  return 'within';
}

function finiteOrNull(n: number | null): number | null {
  return typeof n === 'number' && Number.isFinite(n) ? n : null;
}

function buildLayout(trend: TrendData): Layout {
  const low = finiteOrNull(trend.ref_low);
  const high = finiteOrNull(trend.ref_high);

  const parsed = trend.data_points.flatMap((raw: TrendPoint, index) => {
    const parts = parseDate(raw.date);
    if (!parts || !Number.isFinite(raw.value)) return [];
    return [{ raw, index, parts, time: Date.UTC(parts.year, parts.month - 1, parts.day) }];
  });
  if (parsed.length === 0) return { points: [], highY: null, lowY: null, band: null };
  parsed.sort((a, b) => a.time - b.time || a.index - b.index);

  const tMin = parsed[0].time;
  const tMax = parsed[parsed.length - 1].time;
  const xOf = (time: number): number =>
    tMax > tMin ? PAD_X + ((time - tMin) / (tMax - tMin)) * PLOT_W : PAD_X + PLOT_W / 2;

  const domain = [
    ...parsed.map((p) => p.raw.value),
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
    value: p.raw.value,
    unit: p.raw.unit,
    verified: p.raw.user_verified === true,
    side: sideOf(p.raw.value, low, high),
    x: xOf(p.time),
    y: yOf(p.raw.value),
  }));

  const highY = high !== null ? yOf(high) : null;
  const lowY = low !== null ? yOf(low) : null;
  const band =
    highY !== null && lowY !== null
      ? { top: Math.min(highY, lowY), height: Math.abs(lowY - highY) }
      : null;
  return { points, highY, lowY, band };
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
  const { points } = layout;
  const count = points.length;
  const reduced = useReducedMotion();
  const analyte = trend.analyte_canonical;

  // Decided once per mount. The reveal is written in an effect, so StrictMode's
  // double render cannot see its own write and skip the reveal.
  const [revealing] = useState(() => !reduced && !hasRevealed(analyte));
  const [selected, setSelected] = useState(() => Math.max(0, count - 1));
  const [move, setMove] = useState<'start' | 'pointer' | 'key'>('start');

  const svgRef = useRef<SVGSVGElement>(null);
  const lineRef = useRef<SVGGElement>(null);

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

  if (count === 0) {
    return <p className="text-sm text-ink-secondary">No values to chart yet.</p>;
  }

  const active = Math.min(Math.max(selected, 0), count - 1);
  const current = points[active];
  const glide = move === 'pointer' && !reduced;

  const choose = (index: number, how: 'pointer' | 'key') => {
    setMove(how);
    setSelected(index);
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
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        width="100%"
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
            <circle
              data-hit
              cx={p.x}
              cy={p.y}
              r={HIT_R}
              fill="transparent"
              style={{ cursor: 'pointer' }}
              onClick={() => choose(p.order, 'pointer')}
            />
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
            {(p.side === 'above' || p.side === 'below') && (
              <path data-triangle={p.side} d={triangleD(p.x, p.y, p.side)} fill="var(--outside)">
                <title>{SIDE_WORDS[p.side]}</title>
              </path>
            )}
          </g>
        ))}

        <g
          data-cursor
          aria-hidden="true"
          style={{ transform: `translateX(${current.x}px)`, transition: glide ? GLIDE : 'none' }}
        >
          <line
            x1={0}
            x2={0}
            y1={PLOT_TOP - 6}
            y2={PLOT_BOTTOM + 6}
            stroke="var(--ink-1)"
            strokeWidth={1}
            strokeDasharray="2 2"
          />
        </g>
      </svg>

      <p data-readout className="text-sm text-ink-secondary">
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
            <th scope="col" className="font-normal">Date</th>
            <th scope="col" className="font-normal">Result</th>
            <th scope="col" className="font-normal">{"Against the report's range"}</th>
            <th scope="col" className="font-normal">Checked</th>
          </tr>
        </thead>
        <tbody>
          {points.map((p) => (
            <tr key={p.order}>
              <th scope="row" className="text-left font-normal">{p.label}</th>
              <td>{valueLabel(p)}</td>
              <td>{SIDE_WORDS[p.side]}</td>
              <td>{p.verified ? 'Checked by you' : 'Not yet checked'}</td>
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
 * unset). Output then carries real colours in light and dark mode.
 */
export function serializeRangeRibbonSvg(svg: SVGSVGElement): string {
  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  const computed = window.getComputedStyle(document.documentElement);
  const markup = new XMLSerializer().serializeToString(clone);
  return markup.replace(/var\((--[\w-]+)\)/g, (_match, token: string) => {
    return computed.getPropertyValue(token).trim() || 'currentColor';
  });
}
