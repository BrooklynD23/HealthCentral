/**
 * Medication Reconciliation Service Contract Tests (HC-M19 / HC-MREC)
 *
 * Verifies the reconciliation hook calls the expected read-only backend
 * route. There is no apply/accept mutation in this service by design —
 * list changes go through the existing medications endpoints only.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as api from '@/services/api';
import * as medReconcile from '@/services/medReconcile';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
}));

const SUGGESTION = {
  suggestion_type: 'new_medication',
  source_entity_id: 'entity-1',
  source_quote: 'Start metformin 500 mg twice daily',
  entity_value: 'start metformin 500 mg twice daily',
  drug_name: 'metformin',
  matched_medication_id: null,
  current_list_summary: 'not on your list',
  confidence: 0.8,
  reason: null,
};

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>{component}</QueryClientProvider>
  );
}

function ReconcileProbe({ docId }: { docId?: string }) {
  medReconcile.useMedReconciliation(docId);
  return <div>reconcile-probe</div>;
}

describe('Medication reconciliation service contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.apiGet).mockResolvedValue([SUGGESTION]);
  });

  it('FE-MREC-API-001: hook uses GET /med-reconciliation/?doc_id=', async () => {
    renderWithProviders(<ReconcileProbe docId="doc-1" />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalled();
    });

    expect(api.apiGet).toHaveBeenCalledWith('/med-reconciliation/', {
      doc_id: 'doc-1',
    });
  });

  it('FE-MREC-API-002: hook is disabled without a document id', async () => {
    renderWithProviders(<ReconcileProbe />);

    // Give the query client a tick; no request may be issued.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(api.apiGet).not.toHaveBeenCalled();
  });

  it('FE-MREC-API-003: service exposes no mutation that writes the list', () => {
    // Read-only by design: the module must export only the query hook and
    // types — applying a change happens via the medications service.
    const exported = Object.keys(medReconcile);
    expect(exported).toEqual(['useMedReconciliation']);
  });
});
