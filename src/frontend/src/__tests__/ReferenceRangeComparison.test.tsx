/**
 * ReferenceRangeComparison gauge tests (HC-GZW-001..003, GAUGE-ZERO-WIDTH)
 *
 * UI-PG-RESULTS (L0 ruling 6600985053 Q3): the gauge became a RangeTick, an svg with its own scale. The checks keep
 * their ids and their meaning (no NaN for a zero-width range; a normal range renders at fixed positions); the
 * positions are now the tick's x values, and the two axis labels went with the gauge.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ReferenceRangeComparison } from '@/components/lab-interpreter/ReferenceRangeComparison';

// The tick draws the band (x), two edge lines (x1) and the marker (cx). A tick that is missing, or has lost a part,
// is a failure: the count is asserted here, so an empty list can never pass the finite check below. jsdom drops an
// invalid attribute silently, so a missing coordinate is read as NaN and fails the same way.
function markerLefts(container: HTMLElement): number[] {
  const nodes = container.querySelectorAll<SVGElement>('[data-band], [data-band-edge], [data-marker]');
  // band, low edge, high edge, marker
  expect(nodes).toHaveLength(4);
  return Array.from(nodes).map((el) =>
    parseFloat(el.getAttribute('cx') ?? el.getAttribute('x1') ?? el.getAttribute('x') ?? 'NaN')
  );
}

function expectNoNaN(container: HTMLElement) {
  expect(container.innerHTML).not.toContain('NaN');
  for (const left of markerLefts(container)) {
    expect(Number.isFinite(left)).toBe(true);
  }
}

// With no span every number sits at the glyph's centre (x = 32 of 64): finite is not enough, the position is checked too.
function expectCentred(container: HTMLElement) {
  for (const x of markerLefts(container)) expect(x).toBeCloseTo(32, 1);
}

describe('ReferenceRangeComparison zero-width range', () => {
  it('HC-GZW-001: low = high = value (5) produces no NaN', () => {
    const { container } = render(
      <ReferenceRangeComparison value={5} refLow={5} refHigh={5} unit="mg/dL" />
    );
    expectNoNaN(container);
    expectCentred(container);
    expect(screen.getByText(/5 - 5 mg\/dL/)).toBeInTheDocument();
    expect(screen.getByText(/5 mg\/dL \(Normal\)/)).toBeInTheDocument();
  });

  it('HC-GZW-002: low = high = value (0) produces no NaN', () => {
    const { container } = render(
      <ReferenceRangeComparison value={0} refLow={0} refHigh={0} unit="mg/dL" />
    );
    expectNoNaN(container);
    expectCentred(container);
    expect(screen.getByText(/0 - 0 mg\/dL/)).toBeInTheDocument();
    expect(screen.getByText(/0 mg\/dL \(Normal\)/)).toBeInTheDocument();
  });

  it('HC-GZW-003: a normal range renders at fixed tick positions (band, low edge, high edge, marker)', () => {
    const { container } = render(
      <ReferenceRangeComparison value={80} refLow={70} refHigh={99} unit="mg/dL" />
    );
    // The gauge's padded axis labels (61.3, 107.7) are gone: the tick prints no scale.
    expect(screen.queryByText('61.3')).not.toBeInTheDocument();
    expect(screen.queryByText('107.7')).not.toBeInTheDocument();
    const xs = markerLefts(container);
    // x = 4 + (v - 70) / 29 * 56: band starts at the low edge (4), low edge 4, high edge 60, value 80 -> 23.3
    expect(xs[0]).toBeCloseTo(4, 1);
    expect(xs[1]).toBeCloseTo(4, 1);
    expect(xs[2]).toBeCloseTo(60, 1);
    expect(xs[3]).toBeCloseTo(23.3, 1);
  });
});
