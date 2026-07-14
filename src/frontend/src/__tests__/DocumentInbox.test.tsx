import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { DocumentInbox } from '@/pages/DocumentInbox';
import { useAuthStore } from '@/stores/authStore';

const mutateAsync = vi.fn();

vi.mock('@/services', () => ({
  ApiError: class ApiError extends Error {
    constructor(public status: number, public statusText: string, message: string) {
      super(message);
    }
  },
  useDocuments: vi.fn(() => ({
    data: [{
      id: 'doc-zero',
      profile_id: 'profile-123',
      doc_type: 'lab_pdf',
      source: 'zero.pdf',
      status: 'parsed',
      page_count: 1,
      collection_date: '2026-07-01T00:00:00',
      imported_at: '2026-07-13T09:00:00',
      parsed_at: '2026-07-13T09:00:01',
      verified_at: null,
      extraction_confidence: 0.0,
    }],
    isLoading: false,
    error: null,
  })),
  useImportDocument: vi.fn(() => ({ mutateAsync, isPending: false })),
  useDeleteDocument: vi.fn(() => ({ mutate: vi.fn() })),
  useReprocessDocument: vi.fn(() => ({ mutate: vi.fn() })),
  useHighlightsSummary: vi.fn(() => ({ data: [] })),
  usePinboards: vi.fn(() => ({ data: [] })),
  useAddPinboardItem: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock('@/components/PageImageOverlay', () => ({
  PageImageOverlay: () => <div>Document preview</div>,
}));

describe('DocumentInbox Phase C warnings and confidence', () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
  });

  it('HC-CONF-004: displays a document 0.0 confidence as low, not missing', () => {
    render(<BrowserRouter><DocumentInbox /></BrowserRouter>);

    expect(screen.getByText(/0%.*low.*lowest extraction confidence/i)).toBeInTheDocument();
    expect(screen.queryByText(/extraction confidence unavailable/i)).not.toBeInTheDocument();
  });

  it('FE-HC-DUP-001: shows and dismisses a warn-only duplicate upload notice', async () => {
    const user = userEvent.setup();
    mutateAsync.mockResolvedValue({
      document: {
        id: 'new-doc',
        profile_id: 'profile-123',
        doc_type: 'lab_pdf',
        source: 'new-copy.pdf',
        status: 'parsed',
        page_count: 1,
        collection_date: '2026-07-01T00:00:00',
        imported_at: '2026-07-13T10:00:00',
        parsed_at: '2026-07-13T10:00:01',
        verified_at: null,
        extraction_confidence: 0.9,
      },
      observations_extracted: 1,
      needs_verification: true,
      duplicate_warning: {
        match_type: 'content_hash',
        document_id: 'existing-doc',
        title: 'prior.pdf',
      },
    });

    render(<BrowserRouter><DocumentInbox /></BrowserRouter>);
    await user.upload(
      screen.getByLabelText(/upload medical documents/i),
      new File(['%PDF-1.4'], 'new-copy.pdf', { type: 'application/pdf' })
    );

    await waitFor(() => {
      expect(screen.getByText(/possible duplicate upload/i)).toBeInTheDocument();
      expect(screen.getByText(/prior\.pdf/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /dismiss duplicate warning/i }));
    expect(screen.queryByText(/possible duplicate upload/i)).not.toBeInTheDocument();
    expect(screen.getByText(/document imported: new-copy\.pdf/i)).toBeInTheDocument();
  });
});
