/**
 * TREND-POINT-RANGE: each trend point is compared with its own report's range when it carries one.
 *
 * HC-TPR-101 own ranges: a point is placed against its own range, in "this report's range" words, the table header
 *            says "Against each report's range", and different ranges get the caption
 * HC-TPR-102 a point with no own range keeps the chart's words, against the series band
 * HC-TPR-103 a flag on a point inside its own range is a conflict: its own words, no triangle
 * HC-TPR-104 no own range anywhere: today's header, no caption, no "this report's range" words
 * HC-TPR-105 the triangle follows the per-point side, and the drawn band stays the series band
 * HC-TPR-106 the caption shows when any visible own range differs from the series pair (also after hideUnverified)
 * HC-TPR-107 the own range's numbers are in the words, and in aria-valuetext and the readout
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import { RangeRibbon } from '@/components/results/RangeRibbon';
import type { TrendData, TrendPoint } from '@/services/types';

const HEADER_OWN = "Against each report's range";
const HEADER_CHART = "Against this chart's range";
const CAPTION =
  'Your reports show different ranges. Each result is compared with the range on its own report, not the shaded band, so a point can be inside the band and still be marked above or below.';

function point(date: string, value: number, extra: Partial<TrendPoint> = {}): TrendPoint {
  return {
    date,
    value,
    unit: 'g/dL',
    is_abnormal: false,
    flag: null,
    doc_id: `doc-${date.slice(0, 10)}`,
    extraction_confidence: null,
    user_verified: true,
    ...extra,
  };
}

function trend(points: TrendPoint[], over: Partial<TrendData> = {}): TrendData {
  return {
    analyte_canonical: 'hemoglobin',
    analyte_display_name: 'Hemoglobin',
    unit: 'g/dL',
    ref_low: 13.5,
    ref_high: 17.5,
    data_points: points,
    summary: '',
    ...over,
  };
}

function rowFor(label: string): HTMLElement {
  return screen.getByRole('row', { name: new RegExp(label) });
}

afterEach(cleanup);

describe('HC-TPR-101 a point is compared with its own report range', () => {
  const data = trend([
    point('2026-01-05T00:00:00', 13.0, { ref_low: 12, ref_high: 16 }),
    point('2026-03-05T00:00:00', 14.0, { ref_low: 13.5, ref_high: 17.5 }),
  ]);

  it('HC-TPR-101: 13.0 is within its own 12-16 although the chart band 13.5-17.5 would call it below', () => {
    render(<RangeRibbon trend={data} />);
    expect(within(rowFor('Jan 5, 2026')).getByText("Within this report's range (12-16 g/dL)")).toBeInTheDocument();
    expect(within(rowFor('Mar 5, 2026')).getByText("Within this report's range (13.5-17.5 g/dL)")).toBeInTheDocument();
    expect(screen.queryByText('Below the range used for this chart')).toBeNull();
  });

  it('HC-TPR-101: the table header names each report and the different-ranges caption shows once', () => {
    render(<RangeRibbon trend={data} />);
    expect(screen.getByRole('columnheader', { name: HEADER_OWN })).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: HEADER_CHART })).toBeNull();
    expect(screen.getAllByText(CAPTION)).toHaveLength(1);
  });

  it('HC-TPR-101: own ranges equal to each other and to the series pair get no caption, but still the own header', () => {
    render(
      <RangeRibbon
        trend={trend(
          [
            point('2026-01-05T00:00:00', 14, { ref_low: 12, ref_high: 16 }),
            point('2026-03-05T00:00:00', 15, { ref_low: 12, ref_high: 16 }),
          ],
          { ref_low: 12, ref_high: 16 }
        )}
      />
    );
    expect(screen.getByRole('columnheader', { name: HEADER_OWN })).toBeInTheDocument();
    expect(screen.queryByText(CAPTION)).toBeNull();
  });

  it('HC-TPR-101: above and below an own range read "Above / Below this report\'s range"', () => {
    render(
      <RangeRibbon
        trend={trend([
          point('2026-01-05T00:00:00', 17, { ref_low: 12, ref_high: 16 }),
          point('2026-03-05T00:00:00', 11, { ref_low: 12, ref_high: 16 }),
        ])}
      />
    );
    expect(within(rowFor('Jan 5, 2026')).getByText("Above this report's range (12-16 g/dL)")).toBeInTheDocument();
    expect(within(rowFor('Mar 5, 2026')).getByText("Below this report's range (12-16 g/dL)")).toBeInTheDocument();
  });

  it('HC-TPR-101: a point with only an upper bound is compared with that bound', () => {
    render(<RangeRibbon trend={trend([point('2026-01-05T00:00:00', 17, { ref_low: null, ref_high: 16 })])} />);
    expect(within(rowFor('Jan 5, 2026')).getByText("Above this report's range (up to 16 g/dL)")).toBeInTheDocument();
  });

  it('HC-TPR-101: a point with only a lower bound is compared with that bound', () => {
    render(<RangeRibbon trend={trend([point('2026-01-05T00:00:00', 11, { ref_low: 12, ref_high: null })])} />);
    expect(within(rowFor('Jan 5, 2026')).getByText("Below this report's range (from 12 g/dL)")).toBeInTheDocument();
  });
});

describe('HC-TPR-102 a point with no own range keeps the chart words', () => {
  it('HC-TPR-102: falls back to the series band in today\'s words', () => {
    render(
      <RangeRibbon
        trend={trend([
          point('2026-01-05T00:00:00', 13.0),
          point('2026-03-05T00:00:00', 14.0, { ref_low: 13.5, ref_high: 17.5 }),
        ])}
      />
    );
    expect(within(rowFor('Jan 5, 2026')).getByText('Below the range used for this chart')).toBeInTheDocument();
    expect(within(rowFor('Mar 5, 2026')).getByText("Within this report's range (13.5-17.5 g/dL)")).toBeInTheDocument();
    // the one own range equals the series pair, so it is not "different ranges"
    expect(screen.queryByText(CAPTION)).toBeNull();
    expect(screen.getByRole('columnheader', { name: HEADER_OWN })).toBeInTheDocument();
  });

  it('HC-TPR-102: null own bounds are no own range', () => {
    render(<RangeRibbon trend={trend([point('2026-01-05T00:00:00', 13.0, { ref_low: null, ref_high: null })])} />);
    expect(within(rowFor('Jan 5, 2026')).getByText('Below the range used for this chart')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: HEADER_CHART })).toBeInTheDocument();
  });
});

describe('HC-TPR-103 flag against the point\'s own range', () => {
  it('HC-TPR-103: H on a value inside its own range is a conflict in its own words, with no triangle', () => {
    const { container } = render(
      <RangeRibbon
        trend={trend([point('2026-01-05T00:00:00', 14, { ref_low: 12, ref_high: 16, flag: 'H', is_abnormal: true })])}
      />
    );
    expect(within(rowFor('Jan 5, 2026')).getByText("This report's flag and its range disagree")).toBeInTheDocument();
    expect(container.querySelector('[data-triangle]')).toBeNull();
  });
});

describe('HC-TPR-104 no own range anywhere is today\'s chart', () => {
  it('HC-TPR-104: chart header, chart words, no caption', () => {
    render(<RangeRibbon trend={trend([point('2026-01-05T00:00:00', 13.0), point('2026-03-05T00:00:00', 14.0)])} />);
    expect(screen.getByRole('columnheader', { name: HEADER_CHART })).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: HEADER_OWN })).toBeNull();
    expect(screen.queryByText(CAPTION)).toBeNull();
    expect(screen.queryByText(/this report's range/)).toBeNull();
    expect(within(rowFor('Jan 5, 2026')).getByText('Below the range used for this chart')).toBeInTheDocument();
  });
});

describe('HC-TPR-106 the caption follows the series pair', () => {
  it('HC-TPR-106: a single point whose own range differs from the series pair gets the caption', () => {
    render(<RangeRibbon trend={trend([point('2026-01-05T00:00:00', 14, { ref_low: 12, ref_high: 16 })])} />);
    expect(screen.getAllByText(CAPTION)).toHaveLength(1);
  });

  it('HC-TPR-106: hideUnverified leaves one visible own range that differs from the series pair: caption', () => {
    render(
      <RangeRibbon
        hideUnverified
        trend={trend([
          point('2026-01-05T00:00:00', 14, { ref_low: 12, ref_high: 16, user_verified: true }),
          point('2026-03-05T00:00:00', 14, { ref_low: 13.5, ref_high: 17.5, user_verified: false }),
        ])}
      />
    );
    expect(screen.getAllByRole('row')).toHaveLength(2); // header + the one visible point
    expect(screen.getAllByText(CAPTION)).toHaveLength(1);
  });

  it('HC-TPR-106: a visible own range equal to the series pair gets no caption', () => {
    render(<RangeRibbon trend={trend([point('2026-03-05T00:00:00', 14, { ref_low: 13.5, ref_high: 17.5 })])} />);
    expect(screen.queryByText(CAPTION)).toBeNull();
  });
});

describe('HC-TPR-107 the own range reaches the screen reader and the readout', () => {
  it('HC-TPR-107: aria-valuetext and the readout carry the own-range phrase with its numbers', () => {
    const { container } = render(
      <RangeRibbon
        trend={trend([
          point('2026-01-05T00:00:00', 13, { ref_low: 12, ref_high: 16 }),
          point('2026-03-05T00:00:00', 17, { ref_low: 12, ref_high: 16 }),
        ])}
      />
    );
    const slider = screen.getByRole('slider');
    expect(slider.getAttribute('aria-valuetext')).toContain("above this report's range (12-16 g/dL)");
    expect(slider.getAttribute('aria-valuetext')).not.toContain("this chart's range");
    const readout = container.querySelector('[data-readout]');
    expect(readout?.textContent).toContain("Above this report's range (12-16 g/dL)");
  });

  it('HC-TPR-107: a conflict reads in the lowercase phrase for the screen reader', () => {
    render(
      <RangeRibbon
        trend={trend([point('2026-01-05T00:00:00', 14, { ref_low: 12, ref_high: 16, flag: 'H', is_abnormal: true })])}
      />
    );
    expect(screen.getByRole('slider').getAttribute('aria-valuetext')).toContain(
      "this report's flag and its range disagree"
    );
  });

  it('HC-TPR-107: a series-fallback point keeps today\'s words in the slider and readout', () => {
    const { container } = render(<RangeRibbon trend={trend([point('2026-01-05T00:00:00', 13.0)])} />);
    expect(screen.getByRole('slider').getAttribute('aria-valuetext')).toContain("below this chart's range");
    expect(container.querySelector('[data-readout]')?.textContent).toContain('Below the range used for this chart');
  });
});

describe('HC-TPR-105 drawing', () => {
  it('HC-TPR-105: the triangle follows the point\'s own side and the band is still the series band', () => {
    const { container } = render(
      <RangeRibbon
        trend={trend([
          point('2026-01-05T00:00:00', 15.5, { ref_low: 12, ref_high: 15 }),
          point('2026-03-05T00:00:00', 14.0, { ref_low: 13.5, ref_high: 17.5 }),
        ])}
      />
    );
    // 15.5 is above its own 12-15 (a triangle) although it is within the series band 13.5-17.5
    const triangle = container.querySelector('[data-triangle-for="0"]');
    expect(triangle?.getAttribute('data-triangle')).toBe('above');
    expect(container.querySelector('[data-triangle-for="1"]')).toBeNull();
    expect(container.querySelectorAll('[data-band]')).toHaveLength(1);
    expect(screen.getByText('Reference range used for this chart: 13.5-17.5 g/dL')).toBeInTheDocument();
  });
});
