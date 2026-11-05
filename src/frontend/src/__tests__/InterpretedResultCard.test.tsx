/**
 * InterpretedResultCard render tests (HC-IRC-001..006, INTERP-RENDER;
 * HC-IRC-007..009, INTERP-RENDER-2)
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InterpretedResultCard } from '@/components/lab-interpreter/InterpretedResultCard';
import { PanelInterpretationDashboard } from '@/components/lab-interpreter/PanelInterpretationDashboard';
import type { InterpretationResponse, PanelInterpretationResponse } from '@/services/types';

vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  const filter = (props: React.PropsWithChildren<Record<string, unknown>>) => {
    const dom: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(props)) {
      if (
        !['initial', 'animate', 'exit', 'transition', 'variants', 'whileHover', 'whileTap', 'whileInView', 'layout', 'layoutId'].includes(k)
      ) {
        dom[k] = v;
      }
    }
    return dom;
  };
  const make = (Tag: 'div' | 'button' | 'tr' | 'p' | 'span' | 'li' | 'ul' | 'section') =>
    function MotionStub(props: React.PropsWithChildren<Record<string, unknown>>) {
      return <Tag {...filter(props)}>{props.children}</Tag>;
    };
  const motionStubs = {
    div: make('div'),
    button: make('button'),
    tr: make('tr'),
    p: make('p'),
    span: make('span'),
    li: make('li'),
    ul: make('ul'),
    section: make('section'),
  };
  return {
    ...actual,
    motion: motionStubs,
    m: motionStubs,
    AnimatePresence: ({ children }: React.PropsWithChildren) => <>{children}</>,
  };
});

function makeInterpretation(
  overrides: Partial<InterpretationResponse> = {}
): InterpretationResponse {
  return {
    id: 'interp-1',
    observation_id: 'obs-1',
    interpretation_text: 'Plain text.',
    severity_level: 'mild',
    advice_text: null,
    citations: [],
    context: null,
    model_id: 'template-v1',
    model_tier: 'template',
    confidence_score: 0.9,
    requires_physician_review: false,
    physician_review_reason: null,
    viewed_at: null,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('InterpretedResultCard', () => {
  it('HC-IRC-001: strips [KB:] and [INT:] markers from the whole card, keeps citation buttons', () => {
    const { container } = render(
      <InterpretedResultCard
        interpretation={makeInterpretation({
          interpretation_text:
            'High. [KB:3f2a1b2c-0000-4000-8000-000000000001] More [INT:9c1e1b2c-0000-4000-8000-000000000002].',
          citations: [
            { type: 'kb', id: '3f2a1b2c-0000-4000-8000-000000000001', text: 'LDL guidance' },
            { type: 'int', id: '9c1e1b2c-0000-4000-8000-000000000002', text: 'Prior result' },
          ],
        })}
      />
    );
    const text = container.textContent ?? '';
    expect(text).not.toContain('[KB:');
    expect(text).not.toContain('[INT:');
    expect(text).toContain('High.');
    expect(text).toContain('More');
    expect(screen.getByLabelText(/^Citation 1: /)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Citation 2: /)).toBeInTheDocument();
  });

  it('HC-IRC-002: renders **bold** as <strong> with no literal asterisks', () => {
    const { container } = render(
      <InterpretedResultCard
        interpretation={makeInterpretation({
          interpretation_text: '\n\n**What this test measures:** LDL carries cholesterol.',
        })}
      />
    );
    const strong = screen.getByText('What this test measures:');
    expect(strong.tagName).toBe('STRONG');
    expect(container.textContent ?? '').not.toContain('**');
  });

  it('HC-IRC-003: advice_text has [KB:] markers stripped and keeps one paragraph per line', () => {
    render(
      <InterpretedResultCard
        interpretation={makeInterpretation({
          advice_text:
            'Eat more fibre. [KB:3f2a1b2c-0000-4000-8000-000000000001]\nWalk daily.',
        })}
      />
    );
    const heading = screen.getByText('Questions you could ask your clinician');
    const section = heading.closest('div')!.parentElement!;
    const text = section.textContent ?? '';
    expect(text).not.toContain('[KB:');
    expect(screen.getByText('Eat more fibre.')).toBeInTheDocument();
    expect(screen.getByText('Walk daily.')).toBeInTheDocument();
  });

  // The gauge became a RangeTick (UI-PG-RESULTS, L0 ruling 6600985053 Q3). The tick is a 64 px svg with its own scale
  // (x = 4 + (v - min) / (max - min) * 56, min and max over the range and the value) and no axis labels, so the axis
  // numbers HC-IRC-004/005/007/008 pinned are gone and their expected values are the tick's x positions.
  const tickX = (container: HTMLElement) => ({
    low: Number(container.querySelector('[data-band-edge="low"]')?.getAttribute('x1')),
    high: Number(container.querySelector('[data-band-edge="high"]')?.getAttribute('x1')),
    marker: Number(container.querySelector('[data-marker]')?.getAttribute('cx')),
  });

  it('HC-IRC-004: the tick for a non-negative range starts at the range low (no padded negative axis)', () => {
    const { container } = render(
      <InterpretedResultCard
        interpretation={makeInterpretation()}
        value={120}
        refLow={0}
        refHigh={99}
        unit="mg/dL"
      />
    );
    expect(screen.queryByText('0.0')).not.toBeInTheDocument();
    expect(screen.queryByText('-29.7')).not.toBeInTheDocument();
    const x = tickX(container);
    expect(x.low).toBeCloseTo(4, 1);
    expect(x.high).toBeCloseTo(4 + (99 / 120) * 56, 1);
    expect(x.marker).toBeCloseTo(60, 1);
  });

  it('HC-IRC-005: the tick for a negative range spans it (low edge at the left, high edge at the right, value in between)', () => {
    const { container } = render(
      <InterpretedResultCard
        interpretation={makeInterpretation()}
        value={0}
        refLow={-5}
        refHigh={5}
        unit="mmol/L"
      />
    );
    expect(screen.queryByText('-8.0')).not.toBeInTheDocument();
    expect(screen.getByText(/-5 - 5 mmol\/L/)).toBeInTheDocument();
    const x = tickX(container);
    expect(x.low).toBeCloseTo(4, 1);
    expect(x.high).toBeCloseTo(60, 1);
    expect(x.marker).toBeCloseTo(32, 1);
  });

  it('HC-IRC-006: footer shows a plain source label, not "Model:"', () => {
    const { container, rerender } = render(
      <InterpretedResultCard interpretation={makeInterpretation({ model_tier: 'template' })} />
    );
    expect(screen.getByText('Source: knowledge-base template')).toBeInTheDocument();
    expect(container.textContent ?? '').not.toContain('Model:');

    rerender(
      <InterpretedResultCard interpretation={makeInterpretation({ model_tier: 'local' })} />
    );
    expect(screen.getByText('Source: local model (local)')).toBeInTheDocument();
    expect(container.textContent ?? '').not.toContain('Model:');
  });

  it('HC-IRC-007: the tick scale includes an out-of-range value above the range, marker stays inside the glyph', () => {
    const { container } = render(
      <InterpretedResultCard
        interpretation={makeInterpretation()}
        value={118}
        refLow={70}
        refHigh={99}
        unit="mg/dL"
      />
    );
    expect(screen.queryByText('126.7')).not.toBeInTheDocument();
    expect(screen.queryByText('107.7')).not.toBeInTheDocument();
    const x = tickX(container);
    expect(x.low).toBeCloseTo(4, 1);
    expect(x.high).toBeCloseTo(4 + (29 / 48) * 56, 1);
    expect(x.marker).toBeCloseTo(60, 1);
    expect(x.marker).toBeLessThan(64);
  });

  it('HC-IRC-008: the tick scale follows a high value, and the low edge keeps the left end', () => {
    const { container } = render(
      <InterpretedResultCard
        interpretation={makeInterpretation()}
        value={162}
        refLow={0}
        refHigh={100}
        unit="mg/dL"
      />
    );
    for (const gone of ['192.0', '0.0', '-30.0']) expect(screen.queryByText(gone)).not.toBeInTheDocument();
    const x = tickX(container);
    expect(x.low).toBeCloseTo(4, 1);
    expect(x.high).toBeCloseTo(4 + (100 / 162) * 56, 1);
    expect(x.marker).toBeCloseTo(60, 1);
  });
});

describe('citations with an empty id do not collide on React keys', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function makePanel(): PanelInterpretationResponse {
    return {
      id: 'panel-1',
      panel_name: 'lipid',
      collected_at: '2026-01-01T00:00:00Z',
      observation_ids: ['obs-1'],
      summary_text: 'Panel summary.',
      overall_status: 'normal',
      relationship_insights: null,
      advice_text: null,
      citations: [
        { type: 'source', id: '', text: 'First source' },
        { type: 'source', id: '', text: 'Second source' },
      ],
      confidence_score: 0.9,
      requires_physician_review: false,
      created_at: '2026-01-01T00:00:00Z',
    };
  }

  function sameKeyErrors(spy: { mock: { calls: unknown[][] } }): string[] {
    return spy.mock.calls
      .map((args) => args.map(String).join(' '))
      .filter((line) => line.includes('same key'));
  }

  it('HC-IRC-009: InterpretedResultCard has no duplicate-key warning for two empty-id citations', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <InterpretedResultCard
        interpretation={makeInterpretation({
          citations: [
            { type: 'source', id: '', text: 'First source' },
            { type: 'source', id: '', text: 'Second source' },
          ],
        })}
      />
    );
    expect(screen.getByLabelText(/^Citation 1: /)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Citation 2: /)).toBeInTheDocument();
    expect(sameKeyErrors(spy)).toEqual([]);
  });

  it('HC-IRC-009: PanelInterpretationDashboard has no duplicate-key warning for two empty-id citations', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <PanelInterpretationDashboard interpretation={makePanel()} isLoading={false} isError={false} />
    );
    expect(screen.getByLabelText(/^Citation 1: /)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Citation 2: /)).toBeInTheDocument();
    expect(sameKeyErrors(spy)).toEqual([]);
  });
});
