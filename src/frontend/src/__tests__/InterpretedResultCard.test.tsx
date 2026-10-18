/**
 * InterpretedResultCard render tests (HC-IRC-001..006, INTERP-RENDER)
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InterpretedResultCard } from '@/components/lab-interpreter/InterpretedResultCard';
import type { InterpretationResponse } from '@/services/types';

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
  return {
    ...actual,
    motion: {
      div: make('div'),
      button: make('button'),
      tr: make('tr'),
      p: make('p'),
      span: make('span'),
      li: make('li'),
      ul: make('ul'),
      section: make('section'),
    },
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
    const heading = screen.getByText('Recommendations');
    const section = heading.closest('div')!.parentElement!;
    const text = section.textContent ?? '';
    expect(text).not.toContain('[KB:');
    expect(screen.getByText('Eat more fibre.')).toBeInTheDocument();
    expect(screen.getByText('Walk daily.')).toBeInTheDocument();
  });

  it('HC-IRC-004: gauge min label clamps at 0 for a non-negative range', () => {
    render(
      <InterpretedResultCard
        interpretation={makeInterpretation()}
        value={120}
        refLow={0}
        refHigh={99}
        unit="mg/dL"
      />
    );
    expect(screen.getByText('0.0')).toBeInTheDocument();
    expect(screen.queryByText('-29.7')).not.toBeInTheDocument();
  });

  it('HC-IRC-005: gauge keeps the padded formula when the range is negative (pins current behaviour)', () => {
    render(
      <InterpretedResultCard
        interpretation={makeInterpretation()}
        value={0}
        refLow={-5}
        refHigh={5}
        unit="mmol/L"
      />
    );
    expect(screen.getByText('-8.0')).toBeInTheDocument();
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
});
