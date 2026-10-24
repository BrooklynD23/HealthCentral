import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { DocumentInbox } from '@/pages/DocumentInbox';
import { ApiError } from '@/services';
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

  it('FE-HC-DUP-002: retains independently dismissible warnings for multi-file imports', async () => {
    const user = userEvent.setup();
    const importResponse = (id: string, source: string, prior: string) => ({
      document: {
        id,
        profile_id: 'profile-123',
        doc_type: 'lab_pdf',
        source,
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
        document_id: `existing-${id}`,
        title: prior,
      },
    });
    mutateAsync
      .mockResolvedValueOnce(importResponse('new-a', 'copy-a.pdf', 'prior-a.pdf'))
      .mockResolvedValueOnce(importResponse('new-b', 'copy-b.pdf', 'prior-b.pdf'));

    render(<BrowserRouter><DocumentInbox /></BrowserRouter>);
    await user.upload(
      screen.getByLabelText(/upload medical documents/i),
      [
        new File(['%PDF-1.4 a'], 'copy-a.pdf', { type: 'application/pdf' }),
        new File(['%PDF-1.4 b'], 'copy-b.pdf', { type: 'application/pdf' }),
      ]
    );

    await waitFor(() => {
      expect(screen.getByText(/prior-a\.pdf/i)).toBeInTheDocument();
      expect(screen.getByText(/prior-b\.pdf/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', {
      name: /dismiss duplicate warning for prior-a\.pdf/i,
    }));
    expect(screen.queryByText(/prior-a\.pdf/i)).not.toBeInTheDocument();
    expect(screen.getByText(/prior-b\.pdf/i)).toBeInTheDocument();
  });

  it('FE-FIMP-001: shows an import summary line for a structured (CSV/FHIR) import', async () => {
    const user = userEvent.setup();
    mutateAsync.mockResolvedValue({
      document: {
        id: 'new-doc-csv',
        profile_id: 'profile-123',
        doc_type: 'lab_csv',
        source: 'labs.csv',
        status: 'parsed',
        page_count: null,
        collection_date: '2026-07-01T00:00:00',
        imported_at: '2026-07-13T10:00:00',
        parsed_at: '2026-07-13T10:00:01',
        verified_at: null,
        extraction_confidence: 0.6,
      },
      observations_extracted: 3,
      needs_verification: true,
      duplicate_warning: null,
      import_summary: {
        source_kind: 'lab_csv',
        observations_imported: 3,
        entities_imported: 1,
        skipped: [],
      },
    });

    render(<BrowserRouter><DocumentInbox /></BrowserRouter>);
    await user.upload(
      screen.getByLabelText(/upload medical documents/i),
      new File(['Analyte,Value\nGlucose,100\n'], 'labs.csv', { type: 'text/csv' })
    );

    await waitFor(() => {
      expect(
        screen.getByText(/imported 3 lab results and 1 record mentions.*pending your verification/i)
      ).toBeInTheDocument();
    });
  });
});

describe('DocumentInbox import failure alert', () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
  });

  const uploadFile = async (user: ReturnType<typeof userEvent.setup>, name: string) => {
    await user.upload(
      screen.getByLabelText(/upload medical documents/i),
      new File(['x'], name, { type: 'application/pdf' })
    );
  };

  it('HC-FIE-001: shows the server message and file name when an import fails', async () => {
    const user = userEvent.setup();
    mutateAsync.mockRejectedValue(new ApiError(400, 'Bad Request', 'Unsupported file type'));
    render(<BrowserRouter><DocumentInbox /></BrowserRouter>);
    await uploadFile(user, 'bad.pdf');

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Unsupported file type');
    expect(alert).toHaveTextContent('bad.pdf');
  });

  it('HC-FIE-002: shows fixed too-large copy for a 413', async () => {
    const user = userEvent.setup();
    mutateAsync.mockRejectedValue(new ApiError(413, 'Payload Too Large', 'raw server detail'));
    render(<BrowserRouter><DocumentInbox /></BrowserRouter>);
    await uploadFile(user, 'huge.pdf');

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('This file is too large to import.');
    expect(alert).not.toHaveTextContent('raw server detail');
  });

  it('HC-FIE-003: a successful import after a failure removes the alert', async () => {
    const user = userEvent.setup();
    mutateAsync
      .mockRejectedValueOnce(new ApiError(400, 'Bad Request', 'Unsupported file type'))
      .mockResolvedValueOnce({
        document: {
          id: 'ok-doc',
          profile_id: 'profile-123',
          doc_type: 'lab_pdf',
          source: 'ok.pdf',
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
        duplicate_warning: null,
      });
    render(<BrowserRouter><DocumentInbox /></BrowserRouter>);
    await uploadFile(user, 'bad.pdf');
    await screen.findByRole('alert');

    await uploadFile(user, 'ok.pdf');
    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });
});

// TW4-HOVER-TOUCH: jsdom does not evaluate media queries, so this is a class
// contract. Row actions may only be hidden behind a hover-capable media gate,
// and must reveal on keyboard focus.
describe('DocumentInbox row actions on touch and keyboard', () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
  });

  const actionsContainer = () => {
    const view = screen.getByRole('button', { name: 'View document' });
    const more = screen.getByRole('button', { name: 'More options' });
    let el = view.parentElement;
    while (el && !el.contains(more)) el = el.parentElement;
    if (!el) throw new Error('row actions container not found');
    return el;
  };

  it('FE-TW4-HOVER-001: hides row actions only on hover-capable devices', () => {
    render(<BrowserRouter><DocumentInbox /></BrowserRouter>);

    const hidingTokens = actionsContainer().className.split(/\s+/)
      .filter((t) => /(^|:)(opacity-0|invisible)$/.test(t));
    const ungated = hidingTokens.filter((t) => !t.includes('[@media(hover:hover)]'));
    expect(ungated).toEqual([]);
  });

  it('FE-TW4-HOVER-002: reveals row actions when a keyboard user focuses into them', async () => {
    const user = userEvent.setup();
    render(<BrowserRouter><DocumentInbox /></BrowserRouter>);

    const container = actionsContainer();
    expect(container.className.split(/\s+/)).toContain('focus-within:opacity-100');
    for (let i = 0; i < 50 && !container.contains(document.activeElement); i++) {
      await user.tab();
    }
    expect(container).toContainElement(document.activeElement as HTMLElement);
  });
});

// IMPORT-SCANNED-PAGE: a page with no readable text is named on the last-import card.
describe('DocumentInbox scanned-page notice', () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
  });

  const importResponse = (id: string, source: string, pagesWithoutText: number[]) => ({
    document: {
      id,
      profile_id: 'profile-123',
      doc_type: 'lab_pdf',
      source,
      status: 'parsed',
      page_count: 3,
      collection_date: '2026-07-01T00:00:00',
      imported_at: '2026-07-13T10:00:00',
      parsed_at: '2026-07-13T10:00:01',
      verified_at: null,
      extraction_confidence: 0.6,
    },
    observations_extracted: 4,
    needs_verification: true,
    duplicate_warning: null,
    import_summary: null,
    pages_without_text: pagesWithoutText,
  });

  it('HC-ISP-004: the last-import card names the pages whose values were not read', async () => {
    const user = userEvent.setup();
    mutateAsync
      .mockResolvedValueOnce(importResponse('scan-one', 'one-scan.pdf', [2]))
      .mockResolvedValueOnce(importResponse('scan-two', 'two-scan.pdf', [2, 3]))
      .mockResolvedValueOnce(importResponse('text-only', 'text.pdf', []));
    render(<BrowserRouter><DocumentInbox /></BrowserRouter>);
    const input = screen.getByLabelText(/upload medical documents/i);

    await user.upload(input, new File(['%PDF-1.4 a'], 'one-scan.pdf', { type: 'application/pdf' }));
    const single = await screen.findByText(
      'Page 2 has no readable text, so its values were not read. Check the original report.'
    );
    expect(single).toHaveAttribute('role', 'status');

    await user.upload(input, new File(['%PDF-1.4 b'], 'two-scan.pdf', { type: 'application/pdf' }));
    const plural = await screen.findByText(
      'Pages 2 and 3 have no readable text, so their values were not read. Check the original report.'
    );
    expect(plural).toHaveAttribute('role', 'status');

    await user.upload(input, new File(['%PDF-1.4 c'], 'text.pdf', { type: 'application/pdf' }));
    await waitFor(() => {
      expect(screen.getByText(/document imported: text\.pdf/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/no readable text/i)).not.toBeInTheDocument();
  });
});
