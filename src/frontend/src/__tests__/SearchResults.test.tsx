import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { SearchResults } from '@/components/SearchResults';
import type { SearchResultItem } from '@/services/search';

describe('SearchResults', () => {
  it('renders snippets as plain text without executing html', () => {
    const results: SearchResultItem[] = [
      {
        id: 'chunk-1',
        type: 'chunk',
        title: 'Document content',
        score: 0.42,
        snippet: '<b>Injected</b> text',
        highlight: '',
        collected_at: null,
        analyte: null,
        value: null,
        unit: null,
        explanation: '',
      },
    ];

    const { container } = render(<SearchResults results={results} />);

    expect(screen.getByText('<b>Injected</b> text')).toBeInTheDocument();
    expect(container.querySelector('b')).toBeNull();
    expect(screen.getByText('Relevance: 42.0%')).toBeInTheDocument();
  });

  it('renders result explanation text when present', () => {
    const results: SearchResultItem[] = [
      {
        id: 'obs-1',
        type: 'observation',
        title: 'Glucose',
        score: 0.9,
        snippet: 'Glucose result',
        highlight: '',
        collected_at: null,
        analyte: 'glucose',
        value: 95,
        unit: 'mg/dL',
        explanation: 'Full-text match on observation',
      },
    ];

    render(<SearchResults results={results} />);
    expect(screen.getByText(/why this result:/i)).toHaveTextContent(
      'Why this result: Full-text match on observation',
    );
  });
});
