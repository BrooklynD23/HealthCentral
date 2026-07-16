/**
 * Smart Highlights Service Contract Tests (HC-M16 / HC-HLT)
 *
 * Verifies the highlight hooks call the expected backend routes.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as api from '@/services/api';
import { useDocumentHighlights, useHighlightsSummary } from '@/services/highlights';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
}));

const HIGHLIGHT = {
  highlight_type: 'medication_started',
  doc_id: 'doc-1',
  source_kind: 'entity',
  source_id: 'entity-1',
  quote: 'Start Lisinopril 10 mg daily',
  confidence: 0.8,
  verification_state: 'unreviewed',
};

const SUMMARY = [
  {
    doc_id: 'doc-1',
    counts: { medication_started: 1, needs_verification: 2 },
  },
];

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>{component}</QueryClientProvider>
  );
}

function DocumentHighlightsProbe({ docId }: { docId?: string }) {
  useDocumentHighlights(docId);
  return <div>doc-highlights-probe</div>;
}

function SummaryProbe({ limit }: { limit?: number }) {
  useHighlightsSummary(limit);
  return <div>summary-probe</div>;
}

describe('Highlights service contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.apiGet).mockResolvedValue([HIGHLIGHT]);
  });

  it('FE-HLT-API-001: document hook uses GET /documents/{id}/highlights', async () => {
    renderWithProviders(<DocumentHighlightsProbe docId="doc-1" />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalled();
    });

    expect(api.apiGet).toHaveBeenCalledWith('/documents/doc-1/highlights');
  });

  it('FE-HLT-API-002: document hook is disabled without a doc id', async () => {
    renderWithProviders(<DocumentHighlightsProbe />);

    await new Promise((resolve) => setTimeout(resolve, 25));
    expect(api.apiGet).not.toHaveBeenCalled();
  });

  it('FE-HLT-API-003: summary hook uses GET /documents/highlights/summary', async () => {
    vi.mocked(api.apiGet).mockResolvedValue(SUMMARY);
    renderWithProviders(<SummaryProbe />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalled();
    });

    expect(api.apiGet).toHaveBeenCalledWith('/documents/highlights/summary', undefined);
  });

  it('FE-HLT-API-004: summary hook passes a string limit param', async () => {
    vi.mocked(api.apiGet).mockResolvedValue(SUMMARY);
    renderWithProviders(<SummaryProbe limit={10} />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalled();
    });

    expect(api.apiGet).toHaveBeenCalledWith('/documents/highlights/summary', {
      limit: '10',
    });
  });
});
