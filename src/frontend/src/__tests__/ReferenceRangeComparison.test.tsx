/**
 * ReferenceRangeComparison gauge tests (HC-GZW-001..003, GAUGE-ZERO-WIDTH)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ReferenceRangeComparison } from '@/components/lab-interpreter/ReferenceRangeComparison';

// Track is `inset-x-0`; every other absolutely-positioned element is a
// marker/highlight that must carry a finite `left`. jsdom silently drops an
// invalid `left: NaN%`, so a missing left is treated as a failure too.
function markerLefts(container: HTMLElement): number[] {
  const nodes = container.querySelectorAll<HTMLElement>('.absolute:not(.inset-x-0)');
  return Array.from(nodes).map((el) => parseFloat(el.style.left));
}

function expectNoNaN(container: HTMLElement) {
  expect(container.innerHTML).not.toContain('NaN');
  for (const left of markerLefts(container)) {
    expect(Number.isFinite(left)).toBe(true);
  }
}

describe('ReferenceRangeComparison zero-width range', () => {
  it('HC-GZW-001: low = high = value (5) produces no NaN', () => {
    const { container } = render(
      <ReferenceRangeComparison value={5} refLow={5} refHigh={5} unit="mg/dL" />
    );
    expectNoNaN(container);
    expect(screen.getByText(/5 - 5 mg\/dL/)).toBeInTheDocument();
    expect(screen.getByText(/5 mg\/dL \(Normal\)/)).toBeInTheDocument();
  });

  it('HC-GZW-002: low = high = value (0) produces no NaN', () => {
    const { container } = render(
      <ReferenceRangeComparison value={0} refLow={0} refHigh={0} unit="mg/dL" />
    );
    expectNoNaN(container);
    expect(screen.getByText(/0 - 0 mg\/dL/)).toBeInTheDocument();
    expect(screen.getByText(/0 mg\/dL \(Normal\)/)).toBeInTheDocument();
  });

  it('HC-GZW-003: a normal range renders unchanged (labels and left%)', () => {
    const { container } = render(
      <ReferenceRangeComparison value={80} refLow={70} refHigh={99} unit="mg/dL" />
    );
    expect(screen.getByText('61.3')).toBeInTheDocument();
    expect(screen.getByText('107.7')).toBeInTheDocument();
    const lefts = markerLefts(container);
    // highlight, low marker, high marker, value indicator
    expect(lefts).toHaveLength(4);
    expect(lefts[0]).toBeCloseTo(18.75, 1);
    expect(lefts[1]).toBeCloseTo(18.75, 1);
    expect(lefts[2]).toBeCloseTo(81.25, 1);
    expect(lefts[3]).toBeCloseTo(40.3, 1);
  });
});
